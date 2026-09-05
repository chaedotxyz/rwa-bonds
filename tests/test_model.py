import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from src.inputs import ROOT,load,validate,verify_evidence
from src.model import nav_path,capital_cost,evaluate,threshold_bisection
from src.sampling import lhs,sample
from src.reporting import generate

class ModelTests(unittest.TestCase):
    def setUp(self):self.doc,self.g=load(ROOT/'config/scenarios.json')
    def test_nav_is_accounting_lag_not_recovery_discount(self):
        self.assertEqual(nav_path(.4,44,45,120),1)
        self.assertEqual(nav_path(.4,45,45,120),1)
        self.assertAlmostEqual(nav_path(.4,105,45,120),.7)
        self.assertAlmostEqual(nav_path(.4,165,45,120),.4)
        self.assertAlmostEqual(nav_path(.4,1000,45,120),.4)
        self.assertEqual(nav_path(.4,55,45,120,10),1)
    def test_same_credit_cashflows_different_cost(self):
        b2,b3=[evaluate(self.g,s) for s in ['B-2','B-3']]
        for k in ['fair_value_per_face','consumer_mark_per_face','executed_face_usd','acquisition_usd','payout_usd','pfc_usd']:
            self.assertEqual(b2[k],b3[k],k)
        self.assertGreater(b3['coc_usd'],b2['coc_usd'])
        self.assertEqual(b2['stake_capital_usd'],0)
    def test_no_double_counting_acquisition_or_stake(self):
        z=evaluate(self.g,'B-3')
        self.assertAlmostEqual(z['net_profit_usd'],z['payout_usd']-z['acquisition_usd']-z['coc_usd'])
        expected=sum(z[k] for k in ['execution_fees_usd','asset_financing_usd','expected_enforcement_usd','application_fixed_usd','route_cost_usd'])
        self.assertAlmostEqual(z['coc_usd'],expected)
        self.assertLess(z['coc_usd'],z['stake_capital_usd'])
    def test_capital_acquisition_modes(self):
        s=copy.deepcopy(self.g['consensus']);s.update(staked_eth=90,eth_usd=1,control_fraction=1/3)
        self.assertAlmostEqual(capital_cost(s)['stake_capital_usd'],30)
        s['acquisition_mode']='new_stake'
        self.assertAlmostEqual(capital_cost(s)['stake_capital_usd'],45)
    def test_zero_stake_loss_does_not_mean_zero_cost(self):
        s=copy.deepcopy(self.g['consensus']);s['penalty_probability']=0
        z=capital_cost(s);self.assertEqual(z['expected_stake_loss_usd'],0)
        self.assertGreater(z['consensus_cost_usd'],0)
    def test_closed_exit_zero_trade_not_zero_value_gap(self):
        self.g['common']['exit_open']=False
        z=evaluate(self.g,'B-2')
        self.assertEqual(z['model_verdict'],'blocked_before_attempt')
        self.assertEqual(z['net_profit_usd'],0)
        self.assertGreater(z['market_value_gap_usd'],0)
    def test_lending_needs_actual_surplus_above_ltv_haircut(self):
        z=evaluate(self.g,'B-1')
        self.assertLess(z['pfc_usd'],0)
        self.assertGreater(z['optimistic_nav_capture_bound_usd'],0)
        self.g['common']['nonrecourse']=False
        self.assertEqual(evaluate(self.g,'B-1')['model_verdict'],'blocked_before_attempt')
    def test_no_impairment_no_profit(self):
        self.g['credit']['expected_repayment_usd']=self.g['credit']['principal_usd']
        z=evaluate(self.g,'B-2');self.assertLess(z['net_profit_usd'],0)
    def test_updated_nav_closes_credit(self):
        self.g['credit']['action_day']=165
        z=evaluate(self.g,'B-2')
        self.assertAlmostEqual(z['consumer_mark_per_face'],z['fair_value_per_face'])
        self.assertLess(z['net_profit_usd'],0)
    def test_senior_pool_dilution_not_whole_loss(self):
        self.g['credit']['exposure_share']=.1
        z=evaluate(self.g,'B-2')
        self.assertAlmostEqual(z['fair_value_per_face'],1-.1*(1-4.25/10.15))
    def test_capacity_limits_payout(self):
        self.g['common']['exit_capacity_usd']=1000
        z=evaluate(self.g,'B-2')
        self.assertLessEqual(z['payout_usd'],1000.00000001)
        self.assertGreater(z['requested_face_usd'],z['executed_face_usd'])
    def test_enforcement_applies_to_positive_surplus_not_entire_principal(self):
        z=evaluate(self.g,'B-2')
        self.assertAlmostEqual(z['expected_enforcement_usd'],z['pfc_usd']*.5*.1*.5)
        self.assertEqual(evaluate(self.g,'B-1')['expected_enforcement_usd'],0)
    def test_break_even_root(self):
        root=threshold_bisection(self.g,'B-2','credit','expected_repayment_usd',0,self.g['credit']['principal_usd'])
        self.assertIsNotNone(root)
        self.g['credit']['expected_repayment_usd']=root
        self.assertAlmostEqual(evaluate(self.g,'B-2')['net_profit_usd'],0,places=5)
    def test_exposure_threshold_is_reachable_only_with_capacity(self):
        z=evaluate(self.g,'B-2');e=z['break_even_face_usd']
        self.g['common']['exposure_usd']=e
        self.assertAlmostEqual(evaluate(self.g,'B-2')['net_profit_usd'],0,places=5)
    def test_paid_delay_charged_once(self):
        self.g['credit']['paid_extension_days']=10
        self.assertEqual(evaluate(self.g,'B-2')['route_cost_usd'],110000)
    def test_lhs_each_stratum_once_and_deterministic(self):
        a=list(lhs(100,[(0,1),(0,1)],42))
        self.assertEqual(a,list(lhs(100,[(0,1),(0,1)],42)))
        for col in range(2):self.assertEqual(sorted(int(r[col]*100) for r in a),list(range(100)))
    def test_paired_samples_and_nonprobability_labels(self):
        rows,summary=sample(self.g,20)
        for i in range(20):
            b2,b3=[r for r in rows if r['sample_id']==i and r['scenario']!='B-1']
            self.assertEqual(b2['pfc_usd'],b3['pfc_usd'])
        self.assertTrue(all(s['original_report_percentage_reproduced'] is False for s in summary))
    def test_invalid_input(self):
        for group,key,value in [('consensus','control_fraction',1),('credit','write_down_days',0),('common','ltv',1.1),('treasury','nav_gap_bps',10000),('common','eligible',None)]:
            g=copy.deepcopy(self.g);g[group][key]=value
            with self.assertRaises(ValueError):validate(g)
    def test_evidence_and_reproducible_outputs(self):
        verify_evidence()
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            generate(out=Path(a),samples=8);generate(out=Path(b),samples=8)
            for name in ['manifest.json','samples.csv','scenarios.csv','report.md']:
                self.assertEqual((Path(a)/name).read_bytes(),(Path(b)/name).read_bytes())
            m=json.loads((Path(a)/'manifest.json').read_text())
            self.assertFalse(m['report_targets_used_for_calibration'])
    def test_checksum_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'data').mkdir()
            (root/'data/example').write_text('changed')
            (root/'data/checksums.json').write_text(json.dumps({'example':hashlib.sha256(b'original').hexdigest()}))
            with self.assertRaises(ValueError):verify_evidence(root)

if __name__=='__main__':unittest.main()
