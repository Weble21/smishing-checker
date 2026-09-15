"""Local candidate-to-final-policy checks; no URL visiting or external messaging."""
import argparse,json,sys,os
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--model',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ocr-service'))
    os.environ['SMISHING_MODEL_DIR']=str(args.model.resolve())
    from smishing_api.text_model import predict_text
    from smishing_api.risk import combine_analysis
    from smishing_api.schemas import UrlAnalysisResult,ReputationResult
    cases=[
        ('인증번호를 알려주세요.',None,'MEDIUM'),
        ('이름과 생년월일을 알려주세요.',None,'MEDIUM'),
        ('계좌로 30만원 이체해 줘.',None,'MEDIUM'),
        ('인증번호를 알려주지 마세요.','none','LOW'),
        ('개인정보 입력이 완료되었습니다.',None,'LOW'),
        ('인증번호를 알려주지 마세요\n아래 계좌로 송금해주세요',None,'MEDIUM'),
        ('[국민은행] 기존 앱을 직접 열어 확인하세요.',None,'LOW'),
        ('[국민은행] 상품 만기 안내입니다. https://www.kbstar.com/','official','LOW'),
        ('[국민은행] 인증번호를 입력하세요. https://www.kbstar.com/','official','MEDIUM'),
        ('신원확인 미완료 시 서비스가 중단됩니다. https://unverified.example/','unknown','HIGH'),
        ('자료입니다. https://unverified.example/','unknown','MEDIUM'),
        ('공지입니다. https://unverified.example/','dangerous','HIGH')]
    results=[]
    for message,kind,expected in cases:
        text=predict_text(message)
        urls=[] if kind in [None,'none'] else [UrlAnalysisResult(url='https://www.kbstar.com/' if kind=='official' else 'https://unverified.example/',verdict='DANGEROUS' if kind=='dangerous' else 'UNKNOWN',riskScore=0.0,reputation=ReputationResult(status='NOT_FOUND'))]
        actual=combine_analysis(text,urls,message)[0]
        results.append(dict(text=message,text_label=text.label,text_score=text.riskScore,expected=expected,actual=actual,passed=actual==expected))
    args.output.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    assert all(r['passed'] for r in results), 'Candidate policy regression failed'
    print(f'{len(results)} candidate-to-policy cases passed')
if __name__=='__main__':main()
