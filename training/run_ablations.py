"""Fresh-initialization ablations on frozen train/valid splits; never use test."""
import json
from pathlib import Path
import numpy as np
from evaluation_protocol import mask_text, score_metrics

def run_ablations(model_id, revision, splits, output, use_cpu=False, seed=42, epochs=1):
    from datasets import Dataset
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments, DataCollatorWithPadding, set_seed
    from smishing_api.message_context import encode_message, INPUT_SCHEMA
    import torch, gc, hashlib
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    tokenizer=AutoTokenizer.from_pretrained(model_id,revision=revision)
    report={'model_id':str(model_id),'revision':revision,'seed':seed,'epochs':epochs,
        'input_schema':INPUT_SCHEMA,'split_sha256':{s:hashlib.sha256(splits[s][['text','label']].to_csv(index=False).encode()).hexdigest() for s in ['train','valid']},
        'note':'Each mode starts from the same pretrained initialization. Fixed splits, valid only. Unchanged scores do not prove leakage.', 'modes':{}}
    for mode in ['none','url','digit','prefix','shuffle']:
        set_seed(seed)
        model=AutoModelForSequenceClassification.from_pretrained(model_id,revision=revision,num_labels=2,
            id2label={0:'NORMAL',1:'RISK'},label2id={'NORMAL':0,'RISK':1})
        model.config.smishing_input_schema=INPUT_SCHEMA
        encoded={}
        for split in ['train','valid']:
            dataset=Dataset.from_list([{'text':mask_text(row.text,mode,seed),'labels':int(row.label)} for row in splits[split].itertuples()])
            # Recompute domain features AFTER masking; no hidden URL side channel.
            encoded[split]=dataset.map(lambda row:encode_message(tokenizer,row['text']),remove_columns=['text'])
        trainer=Trainer(model=model,processing_class=tokenizer,data_collator=DataCollatorWithPadding(tokenizer),
            train_dataset=encoded['train'],eval_dataset=encoded['valid'],args=TrainingArguments(
                output_dir=str(output/mode),learning_rate=1e-5,num_train_epochs=epochs,
                per_device_train_batch_size=16,per_device_eval_batch_size=32,
                save_strategy='no',eval_strategy='no',report_to='none',seed=seed,data_seed=seed,
                use_cpu=use_cpu,fp16=not use_cpu and torch.cuda.is_available()))
        trainer.train()
        prediction=trainer.predict(encoded['valid'])
        probabilities=torch.softmax(torch.as_tensor(prediction.predictions),dim=-1)[:,1].numpy()
        report['modes'][mode]=score_metrics(prediction.label_ids,probabilities)
        (output/'ablation_results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        del trainer,model,encoded,prediction
        gc.collect()
        if not use_cpu:torch.cuda.empty_cache()
    return report
