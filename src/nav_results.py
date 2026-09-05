"""Public NAV readings and verified payment evidence; do not invent independent NAV."""
import csv
import json
from datetime import datetime,timezone
from .inputs import ROOT,verify_evidence
from .empirical import write_csv

POOL='0xb26b42dd5771689d0a7faeea32825ff9710b9c11'
CREDIT='0x5424b911d04f71357468743b24b868db0706048c'
USDC='0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
SENIOR='0x8481a6ebaf5c7dabc3f7e09e44a89531fd31f822'
PAYMENT='0xd1055dc2c2a003a83dfacb1c38db776eab5ef89d77a8f05a3512e8cf57f953ce'
TRANSFER='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

def words(raw,count):
    if not isinstance(raw,str) or not raw.startswith('0x') or len(raw)!=2+64*count:return None
    try:return [int(raw[2+i*64:2+(i+1)*64],16) for i in range(count)]
    except ValueError:return None

def uint(response):
    if response.get('error'):return None
    w=words(response.get('result'),1)
    return w[0] if w else None

def decode_nav(snap):
    header=snap['header'].get('result')
    result=dict(block=snap['block_number'],as_of=None,nav_usd=None,updated_at=None,age_hours=None,status='unavailable',independent_nav_usd=None,actual_nav_gap_pct=None)
    if not header or snap['header'].get('error'):return result
    ts=int(header['timestamp'],16);result['as_of']=datetime.fromtimestamp(ts,timezone.utc).isoformat()
    vals=words(snap['nav'].get('result'),5);dec=uint(snap['decimals'])
    if snap['nav'].get('error') or not vals or dec is None:return result
    _,answer,_,updated,_=vals
    # uint decoding of int256 rejects negative values using sign-bit guard.
    if answer<=0 or answer>=2**255 or updated<=0 or updated>ts or dec>36:
        result['status']='invalid';return result
    result.update(nav_usd=answer/10**dec,updated_at=datetime.fromtimestamp(updated,timezone.utc).isoformat(),age_hours=(ts-updated)/3600,status='observed_issuer_related_feed')
    return result

def payment_values(receipt):
    if not receipt or receipt.get('status')!='0x1':raise ValueError('Successful transaction required')
    matching=[l for l in receipt['logs'] if l['address'].lower()==POOL and l['topics'][0]==PAYMENT]
    if len(matching)!=1:raise ValueError('Expected exactly one pool payment event')
    w=words(matching[0]['data'],4)
    if w is None:raise ValueError('Malformed payment event')
    transfers=[]
    for l in receipt['logs']:
        if l['address'].lower()==USDC and l['topics'][0]==TRANSFER and len(l['topics'])==3:
            amount=words(l['data'],1)
            if amount is None:raise ValueError('Malformed USDC transfer')
            transfers.append(dict(sender='0x'+l['topics'][1][-40:],recipient='0x'+l['topics'][2][-40:],amount_usdc=amount[0]/1e6))
    inward=sum(x['amount_usdc'] for x in transfers if x['recipient']==CREDIT)
    to_senior=sum(x['amount_usdc'] for x in transfers if x['sender']==POOL and x['recipient']==SENIOR)
    return dict(tx_hash=receipt['transactionHash'],block=int(receipt['blockNumber'],16),
        interest_applied_usdc=w[0]/1e6,principal_applied_usdc=w[1]/1e6,remaining_usdc=w[2]/1e6,
        reserve_usdc=w[3]/1e6,credit_line_cash_in_usdc=inward,senior_pool_cash_received_usdc=to_senior,
        transfers=transfers,attribution='Amount and timing consistent with GIP-67 backstop; not classified as borrower-originated recovery',
        completeness='One verified transaction, not full cashflow history')

def generate(out):
    verify_evidence()
    public=json.loads((ROOT/'data/nav-public.json').read_text())
    nav=[decode_nav(s) for s in public['snapshots']]
    valid=[r for r in nav if r['nav_usd'] is not None]
    if not valid:raise ValueError('No valid NAV readings; cannot produce a measured range')
    evidence=json.loads((ROOT/'data/verified-payment.json').read_text())
    pay=payment_values(evidence['receipt']['result'])
    pay['as_of']=datetime.fromtimestamp(int(evidence['header']['result']['timestamp'],16),timezone.utc).isoformat()
    latest=max(public['snapshots'],key=lambda s:s['block_number'])
    balance=uint(latest['balance']);owed=uint(latest['principal_owed'])
    original=uint(min(public['snapshots'],key=lambda s:s['block_number'])['balance'])
    outstanding=owed/1e6 if owed is not None else None
    # Use raw integer units for reconciliation.
    reduction=(original-balance) if original is not None and balance is not None else None
    pay['matches_endpoint_balance_reduction']=reduction==round(pay['principal_applied_usdc']*1e6) if reduction is not None else None
    pay['endpoint_balance_reduction_usdc']=reduction/1e6 if reduction is not None else None
    matched_maps=[s for s in public['snapshots'] if uint(s['pool_credit_line'])==int(CREDIT,16)]
    backstop=dict(total_reported_usd=1158025,senior_reported_usd=759585.89,backers_reported_usd=398439.11,
        status='official_reported_claimable_not_all_claims_verified',source='https://gov.goldfinch.finance/t/gip-67-new-proposal-for-using-gfi-to-help-with-principal-loss/2010/27')
    data=dict(nav_observations=nav,payment=pay,backstop=backstop,latest_outstanding_principal_usdc=outstanding,
        latest_block=latest['block_number'],latest_as_of=nav[-1]['as_of'],verified_pool_mapping_blocks=[s['block_number'] for s in matched_maps],
        valid_nav_observations=len(valid),independent_nav_matched_pairs=0,buidl_actual_nav_gap_pct=None,lendeast_actual_nav_gap_pct=None,
        realized_investor_loss_usd=None,actual_attack_profit_usd=None,event_period_pos_normality=None,
        conclusion='Public evidence supports feed readings and a backstop-linked payment; actual economic NAV gap remains unidentified.',
        source_audit=json.loads((ROOT/'data/nav-source-audit.json').read_text()),
        evidence_sha256=json.loads((ROOT/'data/checksums.json').read_text()))
    write_csv(out/'nav_observations.csv',nav)
    write_csv(out/'verified_payment.csv',[{k:v for k,v in pay.items() if k!='transfers'}])
    (out/'nav_verification.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    fmt=lambda v:'미확인' if v is None else f'{v:,.6f}'
    text=f'''# 공개자료 추가 수집 후 최종 판정

**실제 경제적 NAV 괴리: BUIDL·Lend East 모두 판정 불가. 독립 평가값과 온체인 가격을 같은 시점에 연결한 자료가 0쌍입니다.**

이는 괴리 0% 또는 손실 없음이라는 결과가 아닙니다. 현재 확보한 데이터로 답할 수 없는 항목이라는 결과입니다.

## 새로 확보한 결과

| 항목 | 결과 | 의미 |
|---|---:|---|
| BUIDL 유효 NAV 피드 관측 | {len(valid)}개 | 온체인 발행사 관련 NAV 피드; 독립 시장평가 아님 |
| BUIDL 피드 범위 | {min(r['nav_usd'] for r in valid):.6f} ~ {max(r['nav_usd'] for r in valid):.6f} USD | 수집한 관측점만의 범위 |
| 피드 갱신 후 경과 | {min(r['age_hours'] for r in valid):.2f} ~ {max(r['age_hours'] for r in valid):.2f}시간 | 관측 시각 - updatedAt; 경제적 NAV 지연의 길이 아님 |
| Lend East 최근 미지급 원금 | {fmt(outstanding)} USDC | 블록 {latest['block_number']}, {data['latest_as_of']} |
| 확인한 거래의 유입 USDC | {fmt(pay['credit_line_cash_in_usdc'])} | CreditLine으로 실제 이동한 금액 |
| 그 거래의 원금 반영 | {fmt(pay['principal_applied_usdc'])} USDC | PaymentApplied 이벤트 |
| 그 거래의 이자 반영 | {fmt(pay['interest_applied_usdc'])} USDC | 준비금은 이자와 별도 합산하면 이중계산 위험 |
| 그 거래의 Senior Pool 수령 | {fmt(pay['senior_pool_cash_received_usdc'])} USDC | 실제 토큰 이전 |
| 공지된 전체 보전금 | 1,158,025 USD | 전체 청구·수령 완료를 뜻하지 않음 |

NAV 관측 기간: {valid[0]['as_of']} ~ {valid[-1]['as_of']}. 2024년 3개 선택 블록은 피드 호출이 빈 값이어서 NAV 관측에서 제외했습니다. 수집 블록은 finalized 태그에서 선택했지만, 사건 전체의 PoS 정상성을 입증하는 자료는 아닙니다.

## Lend East에서 달라진 해석

{pay['as_of']} 거래에서 원금 {pay['principal_applied_usdc']:,.6f} USDC와 이자 {pay['interest_applied_usdc']:,.6f} USDC가 반영됐습니다. 원금 반영액은 최초·최근 장부 잔액 차이와 일치합니다: {pay['matches_endpoint_balance_reduction']}.

동일 거래의 Senior Pool 지급액은 GIP-67 공식 공지의 759,585.89달러와 소수 둘째 자리까지 일치하며, 거래 시각도 공지 직전입니다. 이는 커뮤니티 보전금과 연결되는 근거입니다. 이 잔액 감소를 차입자 자체 회수 실적으로 분류하지 않습니다. 공지와 거래의 연결은 금액·시점에 근거한 해석이며 전체 자금 원천 감사를 뜻하지 않습니다.

[검증한 거래](https://etherscan.io/tx/{pay['tx_hash']}) · [공식 보전금 공지]({backstop['source']})

USD 공지와 USDC 거래는 단위를 구분합니다. 두 금액의 숫자 일치가 USDC/USD 환율 관측을 대체하지 않습니다. 보전금 전체와 이 거래의 일부 지급액을 더해 회수액으로 계산하지 않습니다. 부분 거래 검증이므로 투자자별 최종 손실·IRR·총회수액은 계산하지 않습니다.

## 아직 필요한 자료

1. BUIDL: 동일 평가일의 전체 보유 내역·시장평가·현금·부채·해당 지분 수, 분석할 실제 프로토콜의 참조가격 및 실행 호가.
2. Lend East: 대출별 독립 평가·실제 회수·비용·청구권 우선순위, 투자자별 분배 내역 및 거래가격.
3. 양쪽 모두: 사건 기간의 합의 정상성 자료와 손실의 원인을 연결할 분석.

상세 보유 내역은 Securitize의 공개 제출문에서 보유자 요청 자료로 안내됩니다. 공개 검색에서 완전한 독립 평가 시계열은 확보하지 못했습니다. 실제 경제적 가치 괴리를 숫자로 채우려면 이 비공개 자료가 필요합니다. 다른 국채·다른 펀드의 수치로 대체하지 않았습니다.

원문 출처와 수집 한계: data/nav-source-audit.json. 원시 RPC와 해시: data/nav-public.json 및 data/checksums.json. NAV·지급 계산 결과: nav_observations.csv, verified_payment.csv, nav_verification.json.
'''
    (out/'final_verification.md').write_text(text)
    return text
