"""Reproduce observations and narrowly identified findings, without sampled assumptions."""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from .inputs import ROOT
from .products import generate_products, reading, LEND, SENIOR


def route_bound(paused, allowance, cash):
    """Necessary-condition ceiling only; a positive ceiling is not an executable quote."""
    if paused is True:
        return 0.0
    if paused is None or allowance is None or cash is None:
        return None
    return min(allowance, cash)


def write_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def generate(out=ROOT/'results'):
    out = Path(out)
    generate_products(out)
    product = json.loads((out/'product_manifest.json').read_text())
    current = json.loads((ROOT/'data/chain.json').read_text())
    history = json.loads((ROOT/'data/history.json').read_text())['snapshots']
    route_raw = json.loads((ROOT/'data/buidl-route-state.json').read_text())
    header = json.loads((ROOT/'data/buidl-verified-state.json').read_text())['header']
    timestamps = {s['block_number']: s['block_timestamp'] for s in history+[current]}
    timestamps[int(header['number'], 16)] = int(header['timestamp'], 16)
    routes = []
    for block, r in route_raw.items():
        if not block.isdigit():
            continue
        allowance = int(r['allowance'])/1e6
        cash = int(r['usdcHolderBalance'])/1e6
        timestamp = timestamps.get(int(block))
        routes.append(dict(block=int(block), as_of=datetime.fromtimestamp(timestamp, timezone.utc).isoformat() if timestamp else None,
            settlement_paused=r['paused'], allowance_usdc=allowance, holder_cash_usdc=cash,
            necessary_condition_ceiling_usdc=route_bound(r['paused'], allowance, cash),
            executable_quote_usdc=None, scope='Circle route only; not all BUIDL exits',
            source='data/buidl-route-state.json', status='observed_state_and_derived_upper_bound'))
    routes.sort(key=lambda r:r['block'])
    write_csv(out/'buidl_route_observations.csv', routes)
    observations=product['observations']
    def series(product_name, metric):
        return sorted([r for r in observations if r['product']==product_name and r['metric']==metric and r['value'] is not None], key=lambda r:r['block'])
    balances=series('Lend East','credit_line_balance()')
    owed=series('Lend East','credit_line_principalOwed()')
    shares=series('Goldfinch Senior Pool context','sharePrice()')
    event=product['event']
    cl=reading(current,LEND,'creditLine()')
    maturity=reading(current,'0x'+format(cl,'040x'),'termEndTime()') if cl is not None else None
    latest_owed=next((r['value'] for r in owed if r['block']==current['block_number']), None)
    days=(current['block_timestamp']-maturity)/86400 if maturity is not None and latest_owed is not None and latest_owed>0 and current['block_timestamp']>=maturity else None
    # Change in accounting stock is deliberately not classified as cash repayment.
    change=balances[-1]['value']-balances[0]['value'] if len(balances)>1 else None
    findings=[
        dict(id='LE_EXPECTED_SHORTFALL', product='Lend East', value=event['principal_usd']-event['expected_repayment_usd'], unit='USD', status='derived_from_official_report', interpretation='2024-04-02 expected shortfall, not realized loss', source=event['source']),
        dict(id='LE_EXPECTED_SHORTFALL_PCT', product='Lend East', value=100*(1-event['expected_repayment_usd']/event['principal_usd']), unit='percent', status='derived_from_official_report', interpretation='Expected shortfall / reported principal; not actual NAV discount', source=event['source']),
        dict(id='LE_OUTSTANDING_PRINCIPAL', product='Lend East', value=latest_owed, unit='USDC', status='observed' if latest_owed is not None else 'unavailable', interpretation='Unpaid principal recorded at latest saved block', source='data/chain.json'),
        dict(id='LE_DAYS_AFTER_TERM_END', product='Lend East', value=days, unit='days', status='derived_from_observations' if days is not None else 'unavailable', interpretation='Time since contract term end at snapshot with unpaid principal; not NAV lag or continuous default proof', source='data/chain.json'),
        dict(id='LE_BALANCE_CHANGE', product='Lend East', value=change, unit='USDC', status='derived_from_observations' if change is not None else 'unavailable', interpretation='Last minus first recorded credit-line balance; not verified cash recovery', source='data/history.json; data/chain.json'),
    ]
    for r in routes:
        findings.append(dict(id='BUIDL_ROUTE_CEILING_'+str(r['block']), product='BUIDL', value=r['necessary_condition_ceiling_usdc'], unit='USDC', status='derived_from_observations', interpretation='Necessary-condition ceiling at block '+str(r['block'])+'; eligible access and executable price not established', source=r['source']))
    for name in ['BUIDL', 'Lend East']:
        for claim in ['actual_nav_gap','realized_trade_profit','normal_pos_during_event']:
            findings.append(dict(id=name+'_'+claim,product=name,value=None,unit='USD' if claim!='normal_pos_during_event' else 'boolean',status='not_identified',interpretation='Missing matched valuation/execution data or consensus health evidence; not zero',source='docs/empirical-method.md'))
    write_csv(out/'empirical_findings.csv', findings)
    matrix=[
        dict(product='BUIDL', observed='Token supply; specific Circle route pause, allowance and cash', loss_evidence='No identified realized loss', exit_evidence='Necessary-condition bound for a specific route; no executable RFQ', nav_gap='not identified', pos_normality='not independently tested', attack_profit='not identified'),
        dict(product='Lend East', observed='Credit-line balance, principal owed and term end', loss_evidence='Reported expected shortfall; final recovery unverified', exit_evidence='No verified claim-sale price or redemption execution', nav_gap='not identified', pos_normality='not independently tested', attack_profit='not identified'),
    ]
    write_csv(out/'empirical_comparison.csv',matrix)
    manifest=dict(analysis='empirical_observations_v1', assumption_sampling=False, latest_observation_utc=product['observations'][-1]['as_of'],
        observations=observations, buidl_routes=routes, findings=findings, comparison=matrix,
        evidence_sha256=product['evidence_sha256'], source_notes=product['reviewed_sources'],
        identification='Observed credit distress and route constraints do not identify actual NAV gap, attacker profit, or PoS normality.')
    (out/'empirical_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    fmt=lambda v: '미확인' if v is None else f'{v:,.2f}'
    report=['# BUIDL · Lend East 실측 검증 결과','',
        '**관측 자료에서 확인한 것은 Lend East의 미지급 원금과 BUIDL 특정 상환 경로의 제약입니다. 실제 NAV 괴리와 공격 이익은 아직 식별되지 않았습니다.**','',
        '저장된 2024년 선택 블록과 2026-09-05 관측을 재계산했습니다. 실행일의 실시간 자료가 아닙니다. 몬테카를로·가정 NAV·가정 합의 비용은 사용하지 않습니다.','',
        '| 상품 | 계산 결과 | 해석 |','|---|---:|---|',
        f'| Lend East | 미지급 원금 {fmt(latest_owed)} USDC | 최근 저장 블록의 계약 장부 |',
        f'| Lend East | 만기 후 {fmt(days)}일 | 미지급 원금이 기록된 관측 시점; NAV 반영 지연 일수 아님 |',
        f'| Lend East | 잔액 변화 {fmt(change)} USDC | 최초·최종 관측 차이; 현금 회수액 아님 |',
        f'| Lend East | 예상 부족분 {fmt(findings[0]["value"])} USD ({findings[1]["value"]:.2f}%) | 2024-04-02 공지에 근거한 당시 예상; 최종 실현 손실 아님 |',
        *[f'| BUIDL · 블록 {r["block"]} | 특정 경로 상한 {fmt(r["necessary_condition_ceiling_usdc"])} USDC | 중지={r["settlement_paused"]}; 승인·자금의 필요조건, 실제 체결 가능 금액 아님 |' for r in routes],
        '', '## 그래프 읽기',
        '- 01: BUIDL 특정 Circle 경로의 승인 한도·보유 USDC·중지 조건을 반영한 상한. 0은 해당 경로의 관측 상태에만 적용됩니다.',
        '- 02: Lend East 대출 잔액과 미지급 원금의 관측점. 관측 사이를 보간하지 않으며 예상 회수액을 실제 NAV 선으로 표시하지 않습니다.',
        '- 03: 두 상품에서 확인한 지표와 미확인 핵심 지표 비교. 미확인을 손실 0이나 안전 판정으로 표시하지 않습니다.',
        '', '## 이 결과가 답하는 범위',
        '토큰 장부가 존재하는 상황에서 오프체인 신용 문제와 특정 출구의 제약을 관찰했습니다. 그러나 “PoS가 정상임에도 NAV 괴리로 경제적 손실이 발생했다”는 전체 명제를 확정하려면 같은 사건 기간의 합의 정상성, 실제 가치 평가, 거래·회수 자료를 추가로 연결해야 합니다.',
        'BUIDL과 Lend East는 동일 사건에 대한 처리군·대조군이 아닙니다. 이 비교는 관측 가능성과 출구 제약의 비교이며 상대적 안전성 또는 수익률 순위가 아닙니다.',
        '추가 수집 자료가 있는 경우 과거 블록의 creditLine() 연결도 재확인합니다. 각 관측의 주소 귀속 근거는 관측 CSV에 표시합니다. 최신 추가 검증 결과는 final_verification.md를 확인하세요.',
        '', '공식 공지와 출처는 [상품 출처](../docs/product-focus.md), 식별 기준은 [검증 방법](../docs/empirical-method.md)을 참조하세요.',
        '관측 원문·블록·계산 결과는 empirical_manifest.json, empirical_findings.csv에 포함됩니다.']
    text='\n'.join(report)+'\n'
    (out/'empirical_report.md').write_text(text)
    return text
