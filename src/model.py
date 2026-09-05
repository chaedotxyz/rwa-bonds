"""Report-aligned economic scenarios, not a consensus/network attack simulator."""
import copy
import math


def nav_path(fair, day, grace, write_down, extension=0):
    """Book NAV starts at 1 and converges to fair; does NOT delay recovery cashflows."""
    progress=min(1,max(0,(day-extension-grace)/write_down))
    return 1-(1-fair)*progress


def capital_cost(p):
    total=p['staked_eth']*p['eth_usd'];f=p['control_fraction']
    capital=total*f if p['acquisition_mode']=='existing' else total*f/(1-f)
    funding=capital*p['funding_apr']*p['attack_days']/365
    penalty=capital*p['penalty_probability']*p['penalty_fraction']
    return dict(stake_capital_usd=capital,stake_funding_usd=funding,
                expected_stake_loss_usd=penalty,consensus_coordination_usd=p['coordination_usd'],
                consensus_cost_usd=funding+penalty+p['coordination_usd'])


def evaluate(g, scenario, exit_type=None):
    if scenario not in ['B-1','B-2','B-3']:raise ValueError('Unknown scenario')
    if exit_type is None:exit_type='lending' if scenario=='B-1' else g['sampling']['credit_exit']
    if exit_type not in ['redemption','lending']:raise ValueError('Unknown exit')
    c=g['common'];cr=g['credit'];t=g['treasury']
    consensus=scenario!='B-2'
    face=t['exposure_usd'] if scenario=='B-1' else c['exposure_usd']
    if scenario=='B-1':
        fair=1-t['nav_gap_bps']/10000
        mark=1 if c['execution_days']<=t['window_days'] else fair
        day=None
    else:
        recovery=cr['expected_repayment_usd']/cr['principal_usd']
        fair=1-cr['exposure_share']*(1-recovery)
        day=cr['action_day']+c['execution_days']
        mark=nav_path(fair,day,cr['grace_days'],cr['write_down_days'],cr['paid_extension_days'])
    exit_price=mark*(c['ltv'] if exit_type=='lending' else 1)
    cap=min(c['market_depth_usd'],c['exit_capacity_usd']/exit_price) if exit_price>0 else 0
    quantity=min(face,cap)
    blocked=[k for k in ['eligible','quote_available','exit_open'] if c[k] is False]
    if exit_type=='lending' and not c['nonrecourse']:blocked.append('recourse_not_modelled')
    if quantity<=0:blocked.append('no_capacity')
    if blocked:quantity=0
    a=quantity*fair*(1+c['slippage_bps']/10000)
    payout=quantity*exit_price
    pfc=payout-a  # Capital acquired and surrendered/seized; not omitted from PfC.
    fees=payout*c['fee_bps']/10000
    funding=a*c['capital_apr']*c['execution_days']/365
    enforcement=max(pfc,0)*c['permissioned_share']*c['legal_probability']*c['legal_loss_fraction']
    app_fixed=c['fixed_usd'] if quantity else 0
    stake=capital_cost(g['consensus'])
    if consensus:
        route=stake['consensus_cost_usd'] if quantity else 0
    else:
        route=(cr['coordination_usd']+cr['paid_extension_days']*cr['delay_cost_per_day']) if quantity else 0
    coc=fees+funding+enforcement+app_fixed+route
    net=pfc-coc
    optimistic=quantity*max(mark-fair,0)
    # Unit margin excludes non-scaling costs; capacities can prevent reaching this threshold.
    per_pfc=exit_price-fair*(1+c['slippage_bps']/10000)
    per_cost=exit_price*c['fee_bps']/10000+fair*(1+c['slippage_bps']/10000)*c['capital_apr']*c['execution_days']/365+max(per_pfc,0)*c['permissioned_share']*c['legal_probability']*c['legal_loss_fraction']
    unit_margin=per_pfc-per_cost
    fixed=c['fixed_usd']+(stake['consensus_cost_usd'] if consensus else cr['coordination_usd']+cr['paid_extension_days']*cr['delay_cost_per_day'])
    threshold=fixed/unit_margin if unit_margin>0 else None
    return dict(scenario=scenario,exit_type=exit_type,requested_face_usd=face,executed_face_usd=quantity,
        fair_value_per_face=fair,consumer_mark_per_face=mark,nav_gap_bps=(mark-fair)*10000,
        nav_evaluation_day=day,market_value_gap_usd=face*max(mark-fair,0),
        acquisition_usd=a,payout_usd=payout,pfc_usd=pfc,execution_fees_usd=fees,
        asset_financing_usd=funding,expected_enforcement_usd=enforcement,
        application_fixed_usd=app_fixed,route_cost_usd=route,coc_usd=coc,net_profit_usd=net,
        cost_profit_ratio=coc/pfc if pfc>0 else None,
        profitable_under_assumptions=quantity>0 and net>0,
        model_verdict='blocked_before_attempt' if blocked else 'open_under_assumptions' if net>0 else 'closed_under_assumptions',
        blocked_reason=';'.join(blocked),
        evidence_verdict='not_empirically_identified',
        **(stake if consensus else {k:0 for k in stake}),capital_is_not_expense=True,
        capital_required_usd=a+(stake['stake_capital_usd'] if consensus else 0),
        optimistic_nav_capture_bound_usd=optimistic,
        bound_below_consensus_cost=optimistic<stake['consensus_cost_usd'] if consensus else None,
        capital_profit_ratio=stake['stake_capital_usd']/pfc if consensus and pfc>0 else None,
        break_even_face_usd=threshold,break_even_reachable_with_caps=threshold is not None and threshold<=cap and not blocked,
        exit_capacity_face_usd=cap,
        finality_status='assumed_normal_not_simulated' if scenario=='B-2' else 'consensus_counterfactual_not_simulated',
        residual_loss_locus='lender_after_collateral_seizure' if exit_type=='lending' else 'redemption_counterparty_mark_loss',
        counterparty_loss_before_fees_usd=quantity*max(exit_price-fair,0))


def with_change(g,group,key,value):
    out=copy.deepcopy(g);out[group][key]=value;return out


def threshold_bisection(g,scenario,group,key,lo,hi,exit_type=None):
    """Continuous conditional profit root; no target fit to report percentages."""
    def f(v):return evaluate(with_change(g,group,key,v),scenario,exit_type)['net_profit_usd']
    fl,fh=f(lo),f(hi)
    if fl==0 and fh==0:return None
    if fl*fh>0:return None
    for _ in range(70):
        mid=(lo+hi)/2;fm=f(mid)
        if fl*fm<=0:hi=mid
        else:lo=mid;fl=fm
    return (lo+hi)/2
