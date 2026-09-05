import hashlib
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def verify_evidence(root=ROOT):
    for name,digest in json.loads((root/'data/checksums.json').read_text()).items():
        if hashlib.sha256((root/'data'/name).read_bytes()).hexdigest()!=digest:raise ValueError('Evidence changed: '+name)

def load(path):
    doc=json.loads(Path(path).read_text());g={}
    for group,rows in doc['groups'].items():
        g[group]={}
        for name,item in rows.items():
            if item['kind'] not in ['assumption','report_anchor','official_reported','observed'] or not item['source'] or not item['note']:
                raise ValueError('Missing provenance: '+group+'.'+name)
            g[group][name]=item['value']
    validate(g)
    event=json.loads((ROOT/'data/credit-event.json').read_text())
    for key,field in [('principal_usd','principal_usd'),('expected_repayment_usd','expected_repayment_usd')]:
        if doc['groups']['credit'][key]['kind']=='official_reported' and g['credit'][key]!=event[field]:
            raise ValueError('Changed reported value must be classified assumption: '+key)
    return doc,g

def validate(g):
    for group,rows in g.items():
        for name,value in rows.items():
            if isinstance(value,(float,int)) and not isinstance(value,bool):
                if not math.isfinite(value) or value<0:raise ValueError('Negative/nonfinite '+name)
    c=g['common'];cr=g['credit'];s=g['consensus'];t=g['treasury'];sampling=g['sampling']
    for k in ['eligible','quote_available','exit_open','nonrecourse']:
        if type(c[k]) is not bool:raise ValueError('Boolean required: '+k)
    for k in ['ltv','legal_probability','legal_loss_fraction','permissioned_share']:
        if not 0<=c[k]<=1:raise ValueError('Fraction outside [0,1]: '+k)
    if cr['principal_usd']<=0 or not 0<=cr['expected_repayment_usd']<=cr['principal_usd']:raise ValueError('Invalid recovery')
    if not 0<=cr['exposure_share']<=1 or cr['write_down_days']<=0:raise ValueError('Invalid NAV path')
    if not 0<=t['nav_gap_bps']<10000:raise ValueError('Invalid NAV gap')
    if not 0<s['control_fraction']<1 or not 0<=s['penalty_probability']<=1 or not 0<=s['penalty_fraction']<=1:raise ValueError('Invalid consensus assumption')
    if s['acquisition_mode'] not in ['existing','new_stake']:raise ValueError('Invalid acquisition mode')
    if sampling['credit_exit'] not in ['redemption','lending']:raise ValueError('Invalid exit')
    if type(sampling['samples']) is not int or sampling['samples']<1 or type(sampling['seed']) is not int:raise ValueError('Invalid sampling')
    for k in ['credit_recovery_range','exposure_range','nav_gap_range_bps','action_day_range','permissioned_share_range']:
        v=sampling[k]
        if len(v)!=2 or any(not isinstance(x,(int,float)) or not math.isfinite(x) or x<0 for x in v) or v[0]>v[1]:raise ValueError('Invalid range '+k)
    if sampling['credit_recovery_range'][1]>1 or sampling['permissioned_share_range'][1]>1 or sampling['nav_gap_range_bps'][1]>=10000:raise ValueError('Invalid fractional grid')
