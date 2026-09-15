"""Leakage checks, independent evaluation and validation-only threshold selection."""
from __future__ import annotations
import re, random, hashlib, unicodedata
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, average_precision_score

def normalized_template(text):
    text = unicodedata.normalize('NFKC', str(text)).casefold()
    text = re.sub(r'[가-힣]{2,4}(?=\s*(?:고객님|회원님))', '<NAME>', text)
    text = re.sub(r'(?:https?://|hxxps?://|www\.)\S+', '<URL>', text)
    text = re.sub(r'\d+(?:[,.:/-]\d+)*', '<NUM>', text)
    return re.sub(r'\s+', '', text)

def near_duplicate_groups(texts, threshold=.9):
    """Exact char-trigram Jaccard edges; connected components, before splitting.

    Sparse block multiplication limits memory. Transitive chains intentionally
    stay together, even when component endpoints are less similar than threshold.
    No labels participate in grouping.
    """
    if not 0 < threshold <= 1: raise ValueError('Invalid similarity threshold')
    keys = [normalized_template(t) for t in texts]
    unique = sorted(set(keys))
    if not unique: return []
    vocabulary, indices, indptr = {}, [], [0]
    for text in unique:
        grams = {text[i:i+3] for i in range(max(0,len(text)-2))} or {text}
        indices.extend(sorted(vocabulary.setdefault(g,len(vocabulary)) for g in sorted(grams)))
        indptr.append(len(indices))
    matrix=csr_matrix((np.ones(len(indices),dtype=np.int32),indices,indptr),shape=(len(unique),len(vocabulary)))
    sizes=np.diff(indptr)
    parents=list(range(len(unique)))
    def find(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]]; i=parents[i]
        return i
    for start in range(0,len(unique),128):
        overlaps=(matrix[start:start+128]@matrix.T).tocoo()
        for local,j,intersection in zip(overlaps.row,overlaps.col,overlaps.data):
            i=start+int(local); j=int(j)
            if j<=i:continue
            if intersection/(sizes[i]+sizes[j]-intersection)>=threshold:
                a,b=find(i),find(j)
                if a!=b: parents[max(a,b)]=min(a,b)
    owners={text:hashlib.sha256(unique[find(i)].encode()).hexdigest() for i,text in enumerate(unique)}
    return [owners[key] for key in keys]

def assert_split_independence(parts):
    names=[];texts=[]
    family_owners={}
    for name,frame in parts.items():
        if 'source_family' in frame:
            for family in frame.source_family.fillna('').astype(str):
                if not family: continue
                previous=family_owners.setdefault(family,name)
                if previous!=name: raise ValueError(f'Source family crosses {previous}/{name}: {family}')
        if 'label' in frame:
            identity = frame.text.map(lambda t: re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(t))).strip())
            conflicts = frame.groupby(identity).label.nunique()
            if (conflicts > 1).any(): raise ValueError(f'Conflicting exact-text labels in {name}')
        names.extend([name]*len(frame));texts.extend(frame.text.tolist())
    owners={}
    for name,group in zip(names,near_duplicate_groups(texts)):
        previous=owners.setdefault(group,name)
        if previous!=name: raise ValueError(f'Near-duplicate group crosses {previous}/{name}')

def mask_text(text, mode, seed=42):
    if mode=='none': return text
    if mode=='url':
        # Use the production extractor, covering bare and wrapped domains too.
        from smishing_api.url_analysis import extract_urls
        for url in sorted(extract_urls(text),key=len,reverse=True): text=text.replace(url,' ')
        return text
    if mode=='digit':return re.sub(r'\d','0',text)
    if mode=='prefix':return text[20:]
    if mode=='shuffle':
        words=text.split()
        rng=random.Random(str(seed)+hashlib.sha256(text.encode()).hexdigest())
        rng.shuffle(words)
        return ' '.join(words)
    raise ValueError('Unknown ablation mode')

def score_metrics(labels, probabilities, threshold=.5):
    raw_y=np.asarray(labels)
    if not np.isin(raw_y,[0,1]).all(): raise ValueError('Invalid labels')
    y=raw_y.astype(int);p=np.asarray(probabilities,dtype=float)
    if len(y)!=len(p) or not len(y):raise ValueError('Empty or mismatched predictions')
    if not np.isfinite(p).all() or ((p<0)|(p>1)).any(): raise ValueError('Invalid probabilities')
    pred=p>=threshold
    tn=int(((y==0)&~pred).sum());fp=int(((y==0)&pred).sum())
    fn=int(((y==1)&~pred).sum());tp=int(((y==1)&pred).sum())
    binary=len(set(y))==2
    return {'count':len(y),'threshold':float(threshold),'tn':tn,'fp':fp,'fn':fn,'tp':tp,
        'accuracy':float(accuracy_score(y,pred)), 'macro_f1':float(f1_score(y,pred,average='macro',zero_division=0)),
        'risk_recall':tp/(tp+fn) if tp+fn else None,
        'risk_precision':tp/(tp+fp) if tp+fp else None,
        'normal_false_positive_rate':fp/(fp+tn) if fp+tn else None,
        'roc_auc':float(roc_auc_score(y,p)) if binary else None,
        'average_precision':float(average_precision_score(y,p)) if binary else None}

def select_threshold(labels, probabilities, max_fpr=.01, *, hard_probabilities=None,
                     hard_categories=None, max_hard_fpr=.01, min_recall=.95):
    y=np.asarray(labels);p=np.asarray(probabilities,dtype=float)
    if set(y)!={0,1}:raise ValueError('Threshold selection requires both classes in validation')
    if not 0<=max_fpr<=1 or not 0<=max_hard_fpr<=1:raise ValueError('Invalid FPR constraint')
    score_metrics(y,p)
    hard=np.asarray([] if hard_probabilities is None else hard_probabilities,dtype=float)
    if len(hard):score_metrics(np.zeros(len(hard),dtype=int),hard)
    categories=np.asarray(hard_categories if hard_categories is not None else ['all']*len(hard))
    if len(categories)!=len(hard):raise ValueError('Hard categories/predictions mismatch')
    positive=np.sort(p[y==1]);negative=np.sort(p[y==0]);hard_sorted=np.sort(hard)
    by_category={str(k):np.sort(hard[categories==k]) for k in set(categories)}
    thresholds=np.unique(np.concatenate([p,hard,[np.nextafter(1.,2.)]]))
    candidates=[]
    for threshold in thresholds:
        recall=(len(positive)-np.searchsorted(positive,threshold,side='left'))/len(positive)
        fpr=(len(negative)-np.searchsorted(negative,threshold,side='left'))/len(negative)
        if fpr>max_fpr:continue
        if len(hard):
            if recall<min_recall:continue
            if any((len(v)-np.searchsorted(v,threshold,side='left'))/len(v)>max_hard_fpr for v in by_category.values()):continue
        candidates.append((recall,-fpr,float(threshold)))
    result={'selection_split':'valid + valid-hard' if len(hard) else 'valid',
        'max_fpr':max_fpr,'max_hard_fpr':max_hard_fpr,'min_recall':min_recall if len(hard) else None,
        'normal_count':len(negative),'risk_count':len(positive),'hard_normal_count':len(hard),
        'note':'Empirical validation constraints only, not a production guarantee. Public paraphrases are not real received messages.'}
    if not candidates:
        return {**result,'status':'no_feasible_threshold','threshold':None,'abstain_all':False}
    _,_,threshold=max(candidates)
    result.update(status='selected',threshold=threshold,abstain_all=threshold>1,
                  validation=score_metrics(y,p,threshold))
    if len(hard):
        result['hard_validation']=score_metrics(np.zeros(len(hard),dtype=int),hard,threshold)
        result['hard_categories']={k:score_metrics(np.zeros(len(v),dtype=int),v,threshold) for k,v in by_category.items()}
    return result

def load_external(path, kind, cutoff=None):
    path=Path(path)
    if not path.exists():return None
    frame=pd.read_csv(path).fillna('')
    if frame.empty:return None
    required={'id','text','label','source','reviewed','collected_at','category'}
    if not required.issubset(frame.columns):raise ValueError(f'Missing columns: {required-set(frame.columns)}')
    if not frame.id.is_unique or frame.text.str.strip().eq('').any() or frame.source.str.strip().eq('').any():raise ValueError('Missing provenance or duplicate IDs')
    if not frame.reviewed.astype(str).str.lower().isin(['true','1']).all():raise ValueError('External labels must be human reviewed')
    frame['label']=pd.to_numeric(frame.label,errors='raise')
    if not frame.label.isin([0,1]).all():raise ValueError('Invalid external labels')
    frame['label']=frame.label.astype(int)
    if kind=='hard' and not frame.label.eq(0).all():raise ValueError('test-hard contains normal messages only')
    if kind=='temporal':
        if 'origin' in frame and not frame.origin.eq('real_received').all():raise ValueError('Temporal evaluation requires real received messages, not public examples')
        if cutoff is None:raise ValueError('Set a documented training collection cutoff for temporal evaluation')
        dates=pd.to_datetime(frame.collected_at,utc=True,errors='raise')
        if dates.isna().any() or not (dates>pd.to_datetime(cutoff,utc=True)).all():raise ValueError('Temporal test must be collected after training cutoff')
    return frame
