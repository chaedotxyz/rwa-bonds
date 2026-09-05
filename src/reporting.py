import copy
import csv
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from .inputs import ROOT,load,verify_evidence
from .model import evaluate,threshold_bisection
from .sampling import sample


def csv_write(path,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with Path(path).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def observations(root=ROOT):
    chain=json.loads((root/'data/chain.json').read_text())
    historical=json.loads((root/'data/history.json').read_text())['snapshots']
    rows=[]
    token='0x7712c34205737192402172409a8F7ccef8aA2AEc'.lower()
    senior='0x8481a6EbAf5c7DABc3F7e09e44A89531fd31F822'.lower()
    for snap in [*historical,chain]:
        for r in snap['calls']:
            key=(r['address'].lower(),r['signature'])
            selected={(token,'totalSupply()'):('BUIDL Ethereum','token_supply',1e6),
                (senior,'sharePrice()'):('Senior Pool, not Lend East NAV','share_price',1e18),
                (senior,'usdcAvailable()'):('Senior Pool, not guaranteed withdrawal','available_USDC',1e6),
                (senior,'epochDuration()'):('Senior Pool','epoch_seconds',1)}
            if key not in selected:continue
            asset,metric,scale=selected[key]
            val=None if r.get('error') or not r.get('result') or r['result']=='0x' else int(r['result'],16)/scale
            rows.append(dict(asset=asset,metric=metric,value=val,kind='observed',block=snap['block_number'],
                as_of=datetime.fromtimestamp(snap['block_timestamp'],timezone.utc).isoformat(),
                status='unavailable' if val is None else 'observed_not_execution_proof',block_hash=snap['block_hash']))
    return rows


def generate(config=ROOT/'config/scenarios.json',out=ROOT/'results',samples=None):
    verify_evidence();doc,g=load(config);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    n=g['sampling']['samples'] if samples is None else samples
    if type(n) is not int or n<1:raise ValueError('samples must be positive integer')
    base=[evaluate(g,s) for s in ['B-1','B-2','B-3']]
    variants=[]
    controls={
        'credit_lending':{'sampling.credit_exit':'lending'},
        'closed_exit':{'common.exit_open':False},
        'nav_fully_updated':{'credit.action_day':g['credit']['grace_days']+g['credit']['write_down_days']},
        'zero_stake_loss':{'consensus.penalty_probability':0},
        'two_thirds_control':{'consensus.control_fraction':2/3},
        'instant_credit_mark':{'credit.grace_days':0,'credit.write_down_days':.000001},
        'paid_10day_extension':{'credit.paid_extension_days':10},
        'ten_percent_credit_exposure':{'credit.exposure_share':.1}}
    for label,changes in controls.items():
        alt=copy.deepcopy(g)
        for path,v in changes.items():group,key=path.split('.');alt[group][key]=v
        for scenario in ['B-1','B-2','B-3']:
            variants.append(dict(control=label,**evaluate(alt,scenario)))
    # Time grid measures accounting-NAV lag, not time-value discounting of recovery.
    path=[]
    for day in range(0,int(g['credit']['grace_days']+g['credit']['write_down_days'])+31):
        p=copy.deepcopy(g);p['credit']['action_day']=day
        for scenario in ['B-2','B-3']:
            z=evaluate(p,scenario)
            path.append(dict(action_day=day,scenario=scenario,mark=z['consumer_mark_per_face'],fair=z['fair_value_per_face'],
                pfc_usd=z['pfc_usd'],coc_usd=z['coc_usd'],net_profit_usd=z['net_profit_usd']))
    trials,summary=sample(g,n)
    thresholds=[]
    for scenario in ['B-1','B-2','B-3']:
        v=next(z for z in base if z['scenario']==scenario)
        threshold=threshold_bisection(g,scenario,'treasury','nav_gap_bps',0,9999) if scenario=='B-1' else threshold_bisection(g,scenario,'credit','expected_repayment_usd',0,g['credit']['principal_usd'])
        thresholds.append(dict(scenario=scenario,break_even_face_usd=v['break_even_face_usd'],reachable_with_caps=v['break_even_reachable_with_caps'],
            break_even_nav_gap_bps=threshold if scenario=='B-1' else None,
            break_even_recovery_ratio=threshold/g['credit']['principal_usd'] if scenario!='B-1' and threshold is not None else None,
            meaning='No sign-changing root in the tested domain is null; not proof of universal safety'))
    csv_write(out/'scenarios.csv',base);csv_write(out/'controls.csv',variants)
    csv_write(out/'nav_path.csv',path);csv_write(out/'samples.csv',trials)
    csv_write(out/'sensitivity_summary.csv',summary);csv_write(out/'thresholds.csv',thresholds)
    csv_write(out/'observations.csv',observations())
    inputs=[dict(group=group,parameter=k,**item) for group,rows in doc['groups'].items() for k,item in rows.items()]
    csv_write(out/'inputs.csv',inputs)
    tracked=[ROOT/'run.py',*sorted((ROOT/'src').glob('*.py')),Path(config),*sorted((ROOT/'data').glob('*'))]
    manifest=dict(schema_version=1,inputs=doc,runtime_samples=n,seed=g['sampling']['seed'],
        interpretation='conditional_economic_model_not_report_percentage_replication',
        report_targets_used_for_calibration=False,control_overrides=controls,
        point_results=base,thresholds=thresholds,sample_summary=summary,
        parameter_distribution='independent uniform marginals; Latin hypercube; bounded by config',
        evidence_checksums=json.loads((ROOT/'data/checksums.json').read_text()),
        code_input_sha256={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked})
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    lines=['# B-1 / B-2 / B-3 · 보고서 대응 결과','',
        '**조건부 경제 계산입니다. 보고서의 0% / 61.7% / 0%를 재현한 결과가 아닙니다. 실제 출구·공격 성공·확정 상태는 별도 검증 대상입니다.**','',
        '| 시나리오 | PfC: 지급−매입원금($) | CoC: 실행·기대손실 비용($) | 순이익($) | 조건부 판정 |',
        '|---|---:|---:|---:|---|']
    for z in base:lines.append(f"| {z['scenario']} | {z['pfc_usd']:,.2f} | {z['coc_usd']:,.2f} | {z['net_profit_usd']:,.2f} | {z['model_verdict']} |")
    lines+=['','## 해석',
        '- B-1은 가상 국채 담보 대출의 합의 경로다. LTV·매입원금부터 계산하므로 NAV 차액 전부를 공격자 이익으로 넣지 않는다.',
        '- B-2는 부실 반영 전 NAV로 매입·상환 또는 담보대출을 실행하는 조건부 경로다. 기본 상환 출구는 가정이며 실제 Lend East/FIDU에서 검증되지 않았다.',
        '- B-3는 B-2의 동일 자산·노출·NAV·출구·PfC를 유지한 합의 비용 대조군이다. 합의가 NAV 조작 권한을 준다고 가정한 실증이 아니다.',
        '- 지분 확보 자본은 capital_required/stake_capital에 따로 표시한다. CoC에는 자본 전액이 아닌 가정한 조달비·기대 제재손실·조정비를 넣는다.',
        '- B-1/B-3의 합의 성공이나 확정 유지를 실험하지 않았다. 경제적 닫힘은 기술적 불가능 또는 모든 공격 경로의 안전성과 다르다.','',
        '## 선언한 파라미터 공간의 양의 순이익 표본 비율',
        '| 시나리오 | 표본 수 | 양의 순이익 비율 | 순이익 중앙값($) |','|---|---:|---:|---:|']
    for s in summary:lines.append(f"| {s['scenario']} | {s['samples']:,} | {s['positive_sample_fraction']:.2%} | {s['median_net_profit_usd']:,.2f} |")
    zero_penalty=next(z for z in variants if z['control']=='zero_stake_loss' and z['scenario']=='B-3')
    lines += ['',f"중요 대조: 기대 지분 제재손실을 0으로 두면 B-3 순이익은 {zero_penalty['net_profit_usd']:,.2f} USD ({zero_penalty['model_verdict']})다. 기본 닫힘은 제재손실 가정에 의존하며 보편적 안전성 결론이 아니다."]
    lines+=['','이 비율은 가정 범위·분포·재원 상한에 의존한다. 현실 공격 확률이나 보고서 원본 LHS 결과가 아니다. binomial 표본오차를 붙이지 않는다.',
        'B-2/B-3에는 매 표본 동일한 자산 조건을 사용했다. samples.csv에서 sample_id로 짝을 대조할 수 있다.',
        '', '## 근거와 가정',
        '국채 NAV 괴리·신용의 45+120일 경로·스테이킹 수치 중 일부는 초안 앵커 또는 시나리오 가정이다. 국채 입찰가의 금리 민감도를 이익으로 바꾸던 이전 모델은 제거했다.',
        '2024-04-02 신용 공지와 2024년/2026-09-05 체인 관측은 observations.csv 및 data에 보존했다. 서로 다른 날짜를 최신 동시점 자료로 취급하지 않는다.',
        '자격·매입호가·NAV 반영 시점·실제 재원·통제 행위의 성공은 미확인이다. 기본 가정의 open은 empirical open을 뜻하지 않는다.',
        '', '3장 설계는 docs/chapter3.md, 4장에 쓸 수 있는 주장과 수정 사항은 docs/report-alignment.md를 참고한다.']
    text='\n'.join(lines)+'\n';(out/'report.md').write_text(text)
    return text
