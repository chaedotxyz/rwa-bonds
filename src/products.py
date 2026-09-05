"""Product-focused evidence inventory; missing market data never becomes model profit."""
import csv
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from .inputs import ROOT,verify_evidence
TOKEN='0x7712c34205737192402172409a8f7ccef8aa2aec'
LEND='0xb26b42dd5771689d0a7faeea32825ff9710b9c11'
SENIOR='0x8481a6ebaf5c7dabc3f7e09e44a89531fd31f822'
LEND_CREDIT='0x5424b911d04f71357468743b24b868db0706048c'

def reading(snap,address,signature):
    rows=[r for r in snap['calls'] if r['address'].lower()==address.lower() and r['signature']==signature]
    if len(rows)!=1 or rows[0].get('error') or not rows[0].get('result') or rows[0]['result']=='0x':return None
    return int(rows[0]['result'],16)

def generate_products(out=ROOT/'results'):
    verify_evidence();out=Path(out);out.mkdir(parents=True,exist_ok=True)
    current=json.loads((ROOT/'data/chain.json').read_text())
    history=json.loads((ROOT/'data/history.json').read_text())['snapshots']
    event=json.loads((ROOT/'data/credit-event.json').read_text())
    extra_path=ROOT/'data/nav-public.json'
    extra=json.loads(extra_path.read_text())['snapshots'] if extra_path.exists() else []
    rows=[]
    for snap in [*history,current]:
        def add(product,metric,value,unit,scope):
            rows.append(dict(product=product,metric=metric,value=value,unit=unit,kind='observed',
                as_of=datetime.fromtimestamp(snap['block_timestamp'],timezone.utc).isoformat(),
                block=snap['block_number'],scope=scope,status='unavailable' if value is None else 'observed'))
        v=reading(snap,TOKEN,'totalSupply()')
        add('BUIDL Ethereum','token_supply',v/1e6 if v is not None else None,'BUIDL','Ethereum only; not all-chain AUM or market NAV')
        cl=reading(snap,LEND,'creditLine()')
        verified_later=False
        if cl is None:
            matching=[s for s in extra if s['block_number']==snap['block_number']]
            if len(matching)==1:
                response=matching[0]['pool_credit_line']
                if not response.get('error') and response.get('result') not in (None,'0x'):
                    cl=int(response['result'],16);verified_later=True
        address='0x'+format(cl,'040x') if cl is not None else LEND_CREDIT
        for sig in ['balance()','principalOwed()']:
            v=reading(snap,address,sig)
            add('Lend East','credit_line_'+sig,v/1e6 if v is not None else None,'USDC',
                'contract accounting; not cash recovery or NAV; '+('same-block mapping re-collected in data/nav-public.json' if verified_later else 'same-block pool mapping' if cl is not None else 'historical address attributed using 2026 pool mapping; historical mapping not independently verified'))
        for sig,scale,unit in [('sharePrice()',1e18,'USDC/FIDU'),('usdcAvailable()',1e6,'USDC'),('totalWritedowns()',1e6,'USDC')]:
            v=reading(snap,SENIOR,sig)
            add('Goldfinch Senior Pool context',sig,v/scale if v is not None else None,unit,'aggregate pool; not Lend East alone')
    with (out/'product_observations.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    principal=event['principal_usd'];expected=event['expected_repayment_usd']
    claims={'buidl_actual_market_nav_gap':None,'buidl_realized_trade_profit':None,
            'lendeast_actual_portfolio_nav':None,'lendeast_final_realized_recovery':None,
            'lendeast_nav_recognition_delay_days':None,'lendeast_realized_trade_profit':None}
    report=['# BUIDL · Lend East: 상품별 근거 중심 분석','',
        '실제 상품을 분석 대상으로 고정했습니다. 아래 관측과 공지를 실제 NAV·실현 손익으로 바꾸지 않습니다.',
        '저장된 체인 관측은 2024년 선택 블록과 2026-09-05 스냅샷입니다. 2026-09-06 실시간 갱신은 수행하지 않았습니다.','',
        '| 상품 | 지금 확인한 자료 | 아직 식별하지 못한 핵심 값 |','|---|---|---|',
        '| BUIDL | Ethereum 발행량, 공식 거래 경로 안내 | 실제 포트폴리오 시장 NAV, 체결 가능한 RFQ와 거래비용 |',
        '| Lend East | 당시 예상 회수 공지, 대출 계약 장부 | 실제 NAV, 최종 회수, NAV 반영 지연, 거래 가능한 청구권 가격 |',
        '| Senior Pool | 전체 지분가격·가용 USDC | Lend East 단독 손실 또는 개별 투자자 회수액 |','',
        f'2024-04-02 공지: 원금 ${principal:,.0f}, 당시 예상 회수 약 ${expected:,.0f}. 예상 부족분 약 ${principal-expected:,.0f}, {1-expected/principal:.2%}. 최종 손실이 아닙니다.',
        '', '## 직접 확인한 후속 자료',
        '- BUIDL: 2026-02-11 Uniswap Labs 발표는 Securitize를 통한 승인 참여자 RFQ와 온체인 정산 경로를 설명한다. 경로 존재만으로 공개 호가·개별 투자자 접근·수익성을 입증하지 않는다.',
        '- Lend East: 2024-05-10 Warbler Labs 답변은 포트폴리오 NAV를 알지 못한다고 밝힌다. 425만 달러를 실제 NAV로 사용하지 않는다.',
        '- Lend East: 2024-10-25 Goldfinch Foundation의 추가 채무불이행·상환 요구 공지가 있다. 이 공지만으로 이후 최종 회수 상태를 판정하지 않는다.',
        '', '## 다음 검증의 기준',
        'BUIDL은 같은 시점의 NAV/평가 자료와 실제 RFQ·체결·상환 조건을 연결한다. Lend East는 공지·대출 장부·실제 회수 흐름·펀드 상각을 시간별로 연결한다. NAV가 없으면 잔액을 NAV로 바꾸지 않는다.',
        '공통 질문은 “경제적 가치 변화가 온체인 평가와 출구에 어떻게 반영되는가”다. 반드시 손실 또는 공격 구간이 나타나야 한다는 결론을 미리 두지 않는다.',
        '', '현재 실측 자료만으로 두 상품의 실제 NAV 괴리·실현 거래이익을 확정할 수 없습니다. 미확인 항목은 product_manifest.json에 null로 저장합니다.',
        '공식 출처: docs/product-focus.md. 이전 B-1/B-2/B-3 모델은 --conditional 옵션으로만 실행하는 가정 분석이며 주 실측 결과가 아닙니다.']
    text='\n'.join(report)+'\n';(out/'product_report.md').write_text(text)
    manifest=dict(primary_products=['BlackRock BUIDL','Goldfinch Lend East'],observations=rows,
        event=event,identified_claims=claims,reviewed_sources=json.loads((ROOT/'data/product-source-notes.json').read_text()),
        evidence_sha256=json.loads((ROOT/'data/checksums.json').read_text()),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'product_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    return text
