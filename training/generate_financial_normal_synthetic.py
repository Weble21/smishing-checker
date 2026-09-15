"""Generate benign card-notification SMS from reviewed message patterns.

Dacon transaction data is excluded because V1-V30 have no SMS semantics.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, random
from collections import Counter
from pathlib import Path

SEED=42
OUTPUT="training/financial_normal_synthetic.csv"
MANIFEST="training/financial_normal_synthetic_manifest.json"
ISSUERS=[
{"name":"현대카드","domain":"https://www.hyundaicard.com/","source":"https://www.hyundaicard.com/upload/card/T_AOB-20260403-1734-28_%EA%B0%80%EC%9D%B4%EB%93%9C%EB%B6%81_SKT_M%20Ed3_%ED%86%B5%EC%8B%A02.0_V3_%EA%B3%B5%EC%8B%A4%EC%9A%A9.pdf"},
{"name":"하나카드","domain":"https://www.hanacard.co.kr/","source":"https://www.hanacard.co.kr/contents/popup/club_sk/enclean/OPY15000000M.web?mID=OPY15000000M&schID=pcd"},
{"name":"KB국민카드","domain":"https://card.kbcard.com/","source":"https://github.com/kakao/credit-card-sms-parser/blob/master/test/test_credit_card_sms_parser.rb"},
{"name":"NH농협카드","domain":"https://card.nonghyup.com/","source":"https://github.com/kakao/credit-card-sms-parser/blob/master/test/test_credit_card_sms_parser.rb"},
{"name":"BC카드","domain":"https://www.bccard.com/","source":"https://www.bccard.com/app/card/ContentsLinkActn.do?pgm_id=ind1074"},
{"name":"롯데카드","domain":"https://www.lottecard.co.kr/","source":"https://www.lottecard.co.kr/app/LPBNFBD_V500.lc"}]
MERCHANTS=["편의점","온라인서점","동네마트","커피전문점","주유소","대중교통","음식점","약국","생활용품점","온라인쇼핑","통신요금","보험료"]
EVENTS=["domestic_approval","approval_with_total","check_withdrawal","approval_cancelled","sale_cancelled","overseas_approval","online_approval","installment_approval","recurring_approval","transit_payment","payment_deposit_completed","approval_declined"]

def render(n:int)->dict[str,str]:
    fp=hashlib.sha256(f"financial-normal-synthetic-v2|{SEED}|{n}".encode()).hexdigest()
    seed=int(fp[:16],16); r=random.Random(seed)
    issuer=ISSUERS[seed%len(ISSUERS)]; event=EVENTS[(seed//len(ISSUERS))%len(EVENTS)]
    merchant=r.choice(MERCHANTS); amount=r.randrange(10,9001)*100
    total=amount+r.randrange(10,30001)*100
    date=f"{r.randint(1,12):02d}/{r.randint(1,28):02d}"; time=f"{r.randint(0,23):02d}:{r.randint(0,59):02d}"
    card=f"{r.randint(0,99):02d}**"; prefix="[Web발신] " if r.random()<.55 else ""
    name=issuer["name"]; won=f"{amount:,}원"; cumulative=f"{total:,}원"
    usd="US$"+f"{r.randint(5,900):,}.{r.randint(0,99):02d}"; months=r.choice([2,3,5,6,10,12])
    messages={
    "domestic_approval":f"{name} {card} 승인 {date} {time} {won} {merchant} 일시불",
    "approval_with_total":f"[{name}]-승인 {card} {date} {time} {won} {merchant} 누적 {cumulative}",
    "check_withdrawal":f"[{name}] {date} {time} {card} {merchant} 체크카드출금 {won} 잔액 {cumulative}",
    "approval_cancelled":f"{name} {card} 승인취소 {date} {time} {won} {merchant} 취소 완료",
    "sale_cancelled":f"[{name}] {merchant} {won} 매출취소가 처리되었습니다. {date} {time}",
    "overseas_approval":f"{name} 해외승인 {card} {date} {time} {usd} 해외가맹점",
    "online_approval":f"{name} 온라인승인 {card} {date} {time} {won} {merchant}",
    "installment_approval":f"{name} 승인 {card} {date} {time} {won} {months}개월 할부 {merchant}",
    "recurring_approval":f"[{name}] 정기결제 승인 {date} {time} {won} {merchant}",
    "transit_payment":f"[{name}] 후불교통 이용금액 {won} 처리 완료 {date}",
    "payment_deposit_completed":f"[{name}] 카드 결제대금 {won} 입금 처리가 완료되었습니다. {date} {time}",
    "approval_declined":f"{name} {card} 승인거절 {date} {time} {won} {merchant}"}
    text=prefix+messages[event]
    if seed%9==0: text+=f" 이용내역 {issuer['domain']}"
    return {"id":f"financial-syn-{n:04d}","text":text,"issuer":issuer["name"],"label":"0","source":issuer["source"],"reviewed":"true","collected_at":"","category":"payment_status","source_family":"financial_normal_synthetic_v2","origin":"rule_synthetic_from_reviewed_sms_patterns","review_method":"generator_rule_and_source_review","retrieved_at":"2026-09-15","split":"train","generator_seed":str(seed),"seed_fingerprint":fp,"template_key":event}

def generate(root:Path,count:int)->None:
    rows=[render(i) for i in range(1,count+1)]; out=root/OUTPUT; out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    issuers=Counter(row["issuer"] for row in rows)
    manifest={"version":"financial-normal-synthetic-v2","count":len(rows),"label":0,"seed":SEED,"input_datasets":[],"dacon_open_data_used":False,"reason_dacon_excluded":"Anonymized V1-V30 transaction features have no SMS text or message-context semantics.","source_families_excluded_to_protect_evaluation":["신한카드","삼성카드"],"template_counts":dict(sorted(Counter(x["template_key"] for x in rows).items())),"issuer_counts":dict(sorted(issuers.items())),"official_url_rows":sum("https://" in x["text"] for x in rows),"issuer_sources":[{"issuer":i["name"],"url":i["source"],"official_domain":i["domain"]} for i in ISSUERS],"limitations":["Synthetic normal notifications, not received SMS","Training-only data; not a temporal or independent evaluation set","Amounts, dates, card suffixes and merchants are artificial"]}
    (root/MANIFEST).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"count":len(rows),"templates":manifest["template_counts"],"issuers":manifest["issuer_counts"],"official_url_rows":manifest["official_url_rows"],"dacon_open_data_used":False},ensure_ascii=False,indent=2))

def main()->None:
    p=argparse.ArgumentParser(); p.add_argument("--count",type=int,default=300); a=p.parse_args()
    if not 1<=a.count<=5000: raise SystemExit("count must be between 1 and 5000")
    generate(Path(__file__).resolve().parents[1],a.count)
if __name__=="__main__": main()
