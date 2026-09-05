"""Independent uniform-marginal Latin hypercube; parameter-space coverage only."""
import copy
import random
import statistics
from .model import evaluate

def lhs(n,ranges,seed):
    if n<1:raise ValueError('Positive sample count required')
    rng=random.Random(seed);columns=[]
    for low,high in ranges:
        col=[low+(high-low)*(i+rng.random())/n for i in range(n)]
        rng.shuffle(col);columns.append(col)
    return zip(*columns)

def sample(g,n=None):
    s=g['sampling'];n=n or s['samples']
    names=['credit_recovery_range','exposure_range','nav_gap_range_bps','action_day_range','permissioned_share_range']
    rows=[]
    for index,(recovery,exposure,gap,day,permission) in enumerate(lhs(n,[s[k] for k in names],s['seed'])):
        p=copy.deepcopy(g)
        p['credit']['expected_repayment_usd']=recovery*p['credit']['principal_usd']
        p['common']['exposure_usd']=exposure;p['treasury']['exposure_usd']=exposure
        p['treasury']['nav_gap_bps']=gap;p['credit']['action_day']=day
        p['common']['permissioned_share']=permission
        for scenario in ['B-1','B-2','B-3']:
            z=evaluate(p,scenario)
            rows.append(dict(sample_id=index,recovery_ratio=recovery,requested_exposure_usd=exposure,
                treasury_gap_bps=gap,credit_action_day=day,permissioned_share=permission,scenario=scenario,
                executed_face_usd=z['executed_face_usd'],pfc_usd=z['pfc_usd'],coc_usd=z['coc_usd'],
                net_profit_usd=z['net_profit_usd'],open=z['profitable_under_assumptions']))
    summaries=[]
    for scenario in ['B-1','B-2','B-3']:
        subset=[z for z in rows if z['scenario']==scenario]
        summaries.append(dict(scenario=scenario,samples=n,positive_sample_fraction=sum(z['open'] for z in subset)/n,
            median_net_profit_usd=statistics.median(z['net_profit_usd'] for z in subset),
            interpretation='declared_parameter_space_fraction_not_attack_probability',
            original_report_percentage_reproduced=False))
    return rows,summaries
