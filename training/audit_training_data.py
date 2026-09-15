from pathlib import Path
import json, re, hashlib, unicodedata
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.metrics import accuracy_score, f1_score
from sklearn.feature_extraction.text import TfidfVectorizer

RUN=Path('C:/Users/SSAFY/smishing-checker/experiments/koelectra-baseline-v2-20260915T052433606061Z')
def norm(text):
    text=unicodedata.normalize('NFKC',text).lower()
    text=re.sub(r'(?:https?://|hxxps?://|www\.)\S+','<URL>',text)
    return re.sub(r'\s+','',re.sub(r'\d+(?:[,.:/-]\d+)*','<NUM>',text))
def features(frame):
    text=frame.text.astype(str)
    return pd.DataFrame({'length':text.str.len(), 'url':text.str.contains(r'https?://|www\.',regex=True).astype(int),
        'ad':text.str.contains(r'광고|무료수신거부|수신거부').astype(int),
        'delivery':text.str.contains(r'배송|택배|배달').astype(int),
        'digits':text.str.count(r'\d'), 'brackets':text.str.count(r'\['),
        'newlines':text.str.count('\n')})
def audit(run=RUN):
    parts={s:pd.read_csv(run/'splits'/f'{s}.csv').fillna('') for s in ('train','valid','test')}
    report={'run':str(run),'split_sha256':{s:hashlib.sha256((run/'splits'/f'{s}.csv').read_bytes()).hexdigest() for s in parts},'profiles':{},'overlap':{},'baselines':{}}
    for name,frame in parts.items():
        stats={}
        for label,group in frame.groupby('label'):
            x=features(group)
            stats[str(label)]={'count':len(group),'length_median':float(x.length.median()),'length_min':int(x.length.min()),'length_max':int(x.length.max()),'url_rate':float(x.url.mean()),'ad_rate':float(x.ad.mean()),'delivery_rate':float(x.delivery.mean()),'example_prefixes':group.text.head(3).str[:160].tolist()}
        report['profiles'][name]=stats
    for left,right in [('train','valid'),('train','test'),('valid','test')]:
        report['overlap'][left+'_'+right]={'exact':len(set(parts[left].text)&set(parts[right].text)), 'normalized':len(set(parts[left].text.map(norm))&set(parts[right].text.map(norm)))}
    for name,cols in [('length_only',['length']),('surface_features',list(features(parts['train']).columns))]:
        model=DecisionTreeClassifier(max_depth=3,min_samples_leaf=10,random_state=42).fit(features(parts['train'])[cols],parts['train'].label)
        report['baselines'][name]={'rule':export_text(model,feature_names=cols)}
        for split in ['valid','test']:
            predicted=model.predict(features(parts[split])[cols])
            report['baselines'][name][split]={'accuracy':accuracy_score(parts[split].label,predicted),'macro_f1':f1_score(parts[split].label,predicted,average='macro')}
    # Vectors fitted on train only; compare normalized character patterns.
    vec=TfidfVectorizer(analyzer='char',ngram_range=(3,5),min_df=2,max_features=50000)
    train=vec.fit_transform(parts['train'].text.map(norm))
    report['near_duplicates']={}
    for split in ['valid','test']:
        other=vec.transform(parts[split].text.map(norm));maxima=[]
        for start in range(0,len(parts[split]),128):
            maxima.extend((other[start:start+128]@train.T).max(axis=1).toarray().ravel().tolist())
        report['near_duplicates'][split]={'method':'train-fitted normalized char TF-IDF cosine; similarity is not proof of duplication','rows':len(maxima),'at_least_0.9':sum(v>=.9 for v in maxima),'at_least_0.95':sum(v>=.95 for v in maxima),'median':float(np.median(maxima))}
    state=json.loads((run/'checkpoints/checkpoint-1491/trainer_state.json').read_text())
    report['validation_logs']=[x for x in state['log_history'] if 'eval_loss' in x]
    config=json.loads((run/'checkpoints/checkpoint-497/config.json').read_text())
    report['input_schema']=config.get('smishing_input_schema','legacy body-only')
    return report
if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    result=audit()
    out=Path(__file__).with_name('data_quality_audit.json')
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
