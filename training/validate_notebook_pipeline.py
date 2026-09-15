"""Offline notebook pipeline smoke test with tiny random weights, not a quality benchmark."""
from pathlib import Path
import tempfile, sys, json, hashlib, re, unicodedata
from unittest.mock import patch
import nbformat
import numpy as np
import pandas as pd
import torch
from datasets import Dataset, DatasetDict
from transformers import BertTokenizer, ElectraConfig, ElectraForSequenceClassification, set_seed

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'training'), str(ROOT / 'ocr-service')]

def main():
    torch.set_num_threads(2)
    notebook = nbformat.read(ROOT / 'smishing-checker.ipynb', as_version=4)
    nbformat.validate(notebook)
    for cell in notebook.cells:
        if cell.cell_type == 'code':
            compile(cell.source, 'notebook-cell', 'exec')
    cells = {tag: c.source for c in notebook.cells for tag in c.metadata.get('tags', [])}
    with tempfile.TemporaryDirectory(prefix='smishing-notebook-smoke-') as directory:
        root = Path(directory)
        initial = root / 'initial'
        initial.mkdir()
        (initial / 'vocab.txt').write_text('[PAD]\n[UNK]\n[CLS]\n[SEP]\n[MASK]\n안내\n정보\n', encoding='utf-8')
        tokenizer = BertTokenizer(vocab_file=str(initial / 'vocab.txt'))
        tokenizer.save_pretrained(initial)
        config = ElectraConfig(vocab_size=len(tokenizer), embedding_size=16, hidden_size=16,
            intermediate_size=32, num_attention_heads=2, num_hidden_layers=1,
            num_labels=2, id2label={0:'NORMAL',1:'RISK'}, label2id={'NORMAL':0,'RISK':1})
        ElectraForSequenceClassification(config).save_pretrained(initial)
        # Distinct templates with both labels; no downloaded or private messages.
        rows = [{'content': f'샘플 {chr(0xAC00+i)} 문자 안내', 'class': 2 if i % 2 else (1 if i % 4 == 0 else 3)} for i in range(80)]
        raw = DatasetDict(train=Dataset.from_list(rows))
        run = root / 'run'
        run.mkdir()
        splits = run / 'splits'
        splits.mkdir()
        ns = dict(PROJECT_DIR=ROOT, RUN_DIR=run, RUN_ID='offline-smoke', SPLIT_DIR=splits,
            MODEL_DIR=run/'candidate', MODEL_ID=str(initial), MODEL_REVISION='local',
            DATASET_ID='offline-synthetic', DATASET_REVISION='local',
            SEED=42, EPOCHS=.01, TRAIN_BATCH_SIZE=16, EVAL_BATCH_SIZE=32, LEARNING_RATE=1e-5,
            USE_CPU=True, USE_KR_CURATED=True, MAX_FPR=.01, TRAIN_COLLECTION_CUTOFF=None, EXTERNAL_DIR=root/'external', MAX_LENGTH=256, ID2LABEL={0:'NORMAL',1:'RISK'},
            LABEL_MAP={1:0,2:1,3:0}, environment={}, torch=torch, np=np,pd=pd,
            json=json,hashlib=hashlib,re=re,unicodedata=unicodedata,set_seed=set_seed, display=lambda *_: None)
        def local_dataset(name, **kwargs):
            assert kwargs.get('revision') == 'local', 'Dataset revision was not pinned'
            return raw
        with patch('datasets.load_dataset', side_effect=local_dataset):
            exec(cells['clean'],ns)
        for name in ['split','merge','quality','encode','train','evaluate']:
            exec(compile(cells[name],f'notebook-{name}','exec'),ns)
        from smishing_api.message_context import encode_message
        message = '이름과 생년월일을 알려주세요.'
        plain = encode_message(ns['tokenizer'], message)
        batched = encode_message(ns['tokenizer'], message, return_tensors='pt')
        for key, value in batched.items():
            assert value.ndim == 2 and value.shape[0] == 1
            assert value[0].tolist() == plain[key]
        from run_ablations import run_ablations
        ablations = run_ablations(str(initial), 'local', ns['splits'], root/'ablations', use_cpu=True, epochs=.01)
        assert set(ablations['modes']) == {'none','url','digit','prefix','shuffle'}
        assert ns['model'].config.smishing_input_schema == 'message-domain-v1'
        assert (run/'candidate/config.json').exists()
        assert (run/'slice_metrics.json').exists()
        assert (run/'threshold.json').exists()
        assert (run/'external_metrics.json').exists()
        import smishing_api.text_model as serving
        with patch.object(serving, 'resolve_model_dir', return_value=run/'candidate'), patch('torch.cuda.is_available', return_value=False):
            result = serving.predict_text('이름과 생년월일을 알려주세요.')
            assert result.contextModel
            serving._model.config.smishing_risk_threshold = 0.0
            assert serving.predict_text(message).label == 'RISK'
            serving._model.config.smishing_risk_threshold = 1.1
            assert serving.predict_text(message).label == 'NORMAL'

            assert 0 <= result.riskScore <= 1
        serving._model = serving._tokenizer = serving._device = None
        print('PASS: notebook clean/split/merge/encode/train/evaluate/save and serving load (tiny random model only)')

if __name__ == '__main__':
    main()
