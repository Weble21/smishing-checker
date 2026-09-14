#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KR-MOB-SMISHING 참조 탐지 엔진 v2 (전체 100건 스키마 반영)"""
import json, glob, sys
from datetime import datetime

CONFIG = {
    "REDIRECT_WINDOW_SEC": 180,   # SMS->리다이렉트 완성 윈도우
    "DOMAIN_AGE_MAX_DAYS": 7,     # 신생 도메인
    "FORM_WINDOW_SEC": 900,       # 체인->민감폼 윈도우
    "FINANCIAL_WINDOW_SEC": 1800,  # 체인->금융위험 윈도우
    "DIVERGENCE_WINDOW_SEC": 900, # 플랫폼 교차 윈도우
    "DWELL_MIN_MS": 20000,        # 폼 상호작용 최소 체류
    "MFA_BURST_MIN": 3,
    "REDIRECT_HOPS_MIN": 2,
}
REDIRECT_STATUS = {301, 302, 303, 307, 308}

def pt(s): return datetime.fromisoformat(s)
def g(d, *ks, default=None):
    for k in ks:
        if not isinstance(d, dict): return default
        d = d.get(k)
        if d is None: return default
    return d
def active(inc):
    return [e for e in inc.get("event_stream", []) if not g(e,"noise_metadata","duplicate_of")]

# ---- 규칙 ----
def r_chain(ev):
    """SMS(url+긴급) 이후, 신생도메인 DNS -> 다중홉 redirect가 DNS 기준 180초 내.
    윈도우는 '웹 상호작용 시작(DNS)'부터 측정(지연 클릭/멀티세션 대응). 완성시각 반환."""
    sms=next((a for a in ev if a["event_type"]=="sms.received"
              and g(a,"object","contains_url") and g(a,"object","message_features","urgency_language")),None)
    if not sms: return False, None, None
    t_sms=pt(sms["time"])
    for dns in ev:
        if dns["event_type"]!="dns.query" or pt(dns["time"])<t_sms: continue
        if g(dns,"network","domain_age_days",default=999)>CONFIG["DOMAIN_AGE_MAX_DAYS"]: continue
        t1=pt(dns["time"])
        hop=next((c for c in ev if c["event_type"] in ("http.redirect","http.request") and pt(c["time"])>=t1
                  and (g(c,"network","domain_age_days",default=999)<=CONFIG["DOMAIN_AGE_MAX_DAYS"])
                  and ((g(c,"object","redirect_hops_total",default=0)>=CONFIG["REDIRECT_HOPS_MIN"])
                       or (g(c,"network","http","status_code") in REDIRECT_STATUS)
                       or (g(c,"network","http","status_code",default=0)//100==2))),None)
        if not hop: continue
        tc=pt(hop["time"])
        if (tc-t1).total_seconds()<=CONFIG["REDIRECT_WINDOW_SEC"]:
            return True, tc, f'{sms["_event_index"]}->{dns["_event_index"]}->{hop["_event_index"]}'
    return False, None, None

def r_warning_bypass(ev):
    for a in ev:
        w=g(a,"object","warning",default={}) or {}
        if w.get("ui_warning_shown") and w.get("user_bypassed_warning"):
            return True, a["_event_index"]
    return False, None

def r_form(ev, chain_ok, tc):
    if not chain_ok: return False, None
    for a in ev:
        t=pt(a["time"])
        if not (tc <= t <= tc.__class__.fromtimestamp(tc.timestamp()+CONFIG["FORM_WINDOW_SEC"], tc.tzinfo)):
            # 윈도우: 체인 완성 이후 FORM_WINDOW_SEC 이내
            if (t-tc).total_seconds()>CONFIG["FORM_WINDOW_SEC"] or t<tc: continue
        beh=g(a,"object","behavior",default={}) or {}
        form=g(a,"object","form",default={}) or {}
        if a["event_type"]=="ios.web.behavior" and beh.get("form_focus_detected") and beh.get("dwell_time_ms",0)>=CONFIG["DWELL_MIN_MS"]:
            return True, a["_event_index"]
        if a["event_type"]=="form.interaction" and form.get("submission_attempted"):
            return True, a["_event_index"]
        if a["event_type"]=="android.web_submission.blocked":
            return True, a["_event_index"]
    return False, None

def r_divergence(ev):
    blk=[a for a in ev if a["event_type"]=="android.web_submission.blocked"]
    cont=[a for a in ev if a["event_type"]=="ios.web.behavior" and g(a,"object","behavior","user_interaction")=="continued"]
    for b in blk:
        for c in cont:
            if abs((pt(b["time"])-pt(c["time"])).total_seconds())<=CONFIG["DIVERGENCE_WINDOW_SEC"]:
                return True, f'{b["_event_index"]}+{c["_event_index"]}'
    return False, None

def r_financial(ev, chain_ok, tc):
    if not chain_ok: return False, None
    win=[a for a in ev if 0<=(pt(a["time"])-tc).total_seconds()<=CONFIG["FINANCIAL_WINDOW_SEC"]]
    bursts=[g(a,"object","auth","burst_counter_count",default=0) for a in win if a["event_type"]=="auth.step_up_challenge"]
    n_mfa=sum(1 for a in win if a["event_type"]=="auth.step_up_challenge")
    mfa_ok = (max(bursts) if bursts else 0)>=CONFIG["MFA_BURST_MIN"] or n_mfa>=CONFIG["MFA_BURST_MIN"]
    fds=next((a for a in win if a["event_type"]=="bank.transfer_attempt_flagged"
              and g(a,"object","risk_decision")=="BLOCKED"),None)
    if mfa_ok or fds:
        return True, f'MFA_ok={mfa_ok},FDS={"y" if fds else "n"}'
    return False, None

def eval_inc(inc):
    ev=active(inc)
    ch,tc,cp=r_chain(ev)
    return {
        "SMISH_REDIRECT_CHAIN":(ch,cp),
        "PHISH_WARNING_BYPASS":r_warning_bypass(ev),
        "SENSITIVE_FORM_SEQUENCE":r_form(ev,ch,tc),
        "PLATFORM_DIVERGENCE":r_divergence(ev),
        "POST_LURE_FINANCIAL_RISK_SIGNAL":r_financial(ev,ch,tc),
    }

def main(path):
    files=sorted(glob.glob(f"{path}/*.json"))
    RULES=["SMISH_REDIRECT_CHAIN","PHISH_WARNING_BYPASS","SENSITIVE_FORM_SEQUENCE","PLATFORM_DIVERGENCE","POST_LURE_FINANCIAL_RISK_SIGNAL"]
    per={r:{"m":0,"t":0,"mis":[]} for r in RULES}
    rows=[]
    for fp in files:
        inc=json.load(open(fp,encoding="utf-8"))
        pred=eval_inc(inc); gt=inc.get("rule_fire_verification",{})
        for r in RULES:
            if r in gt:
                per[r]["t"]+=1
                if bool(pred[r][0])==bool(gt[r]["fires"]): per[r]["m"]+=1
                else: per[r]["mis"].append((inc["incident_id"],bool(pred[r][0]),bool(gt[r]["fires"])))
        det=any(pred[r][0] for r in RULES)
        rows.append((inc["incident_id"],inc["case_type"],inc.get("difficulty_tier"),det))
    print("="*64); print(f"인시던트: {len(files)}건\n")
    print("[1] 규칙 재현 정확도 (엔진 vs 파일 정답 fires)")
    tot_m=tot_t=0
    for r in RULES:
        d=per[r]; tot_m+=d["m"]; tot_t+=d["t"]
        print(f"  {r:32s} {d['m']}/{d['t']} ({100*d['m']/d['t']:.0f}%)")
        for mm in d["mis"][:6]: print(f"      불일치 {mm[0]}: pred={mm[1]} gt={mm[2]}")
    print(f"  {'전체':32s} {tot_m}/{tot_t} ({100*tot_m/tot_t:.1f}%)")
    # 탐지 성능
    def metric(rows_sub):
        TP=sum(1 for _,ct,_,d in rows_sub if ct=="malicious" and d)
        FN=sum(1 for _,ct,_,d in rows_sub if ct=="malicious" and not d)
        FP=sum(1 for _,ct,_,d in rows_sub if ct=="benign" and d)
        TN=sum(1 for _,ct,_,d in rows_sub if ct=="benign" and not d)
        return TP,FN,FP,TN
    TP,FN,FP,TN=metric(rows)
    tpr=TP/(TP+FN) if TP+FN else float('nan'); fpr=FP/(FP+TN) if FP+TN else float('nan')
    prec=TP/(TP+FP) if TP+FP else float('nan'); f1=2*prec*tpr/(prec+tpr) if prec+tpr else float('nan')
    print("\n[2] 인시던트 단위 탐지 성능 (malicious=양성, benign=음성)")
    print(f"  TP={TP} FN={FN} FP={FP} TN={TN}")
    print(f"  TPR={tpr:.3f}  FPR={fpr:.3f}  정밀도={prec:.3f}  F1={f1:.3f}")
    print(f"  목표: TPR>=0.95 {'PASS' if tpr>=0.95 else 'CHECK'} / FPR<=0.05 {'PASS' if fpr<=0.05 else 'CHECK'}")
    # lookalike 별도
    lk=[r for r in rows if r[1]=="benign_lookalike"]; lk_det=sum(1 for r in lk if r[3])
    print(f"  benign_lookalike 탐지: {lk_det}/{len(lk)} (회색지대, 참고용)")
    print("\n[3] 난이도별 malicious 탐지율(TPR)")
    for tier in ["DT-HIGH","DT-MEDIUM","DT-LOW"]:
        sub=[r for r in rows if r[2]==tier and r[1]=="malicious"]
        if sub: print(f"  {tier:10s} {sum(1 for r in sub if r[3])}/{len(sub)} ({100*sum(1 for r in sub if r[3])/len(sub):.0f}%)")

if __name__=="__main__":
    main(sys.argv[1] if len(sys.argv)>1 else "incidents")
