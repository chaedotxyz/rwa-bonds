import copy
import json
import unittest
from src.inputs import ROOT
from src.nav_results import decode_nav,payment_values,words

class NavTests(unittest.TestCase):
    def test_empty_is_unavailable_not_zero(self):
        d=json.loads((ROOT/'data/nav-public.json').read_text())
        r=decode_nav(d['snapshots'][0])
        self.assertEqual(r['status'],'unavailable')
        self.assertIsNone(r['nav_usd'])
        self.assertIsNone(r['actual_nav_gap_pct'])

    def test_valid_feed_is_not_independent_nav(self):
        d=json.loads((ROOT/'data/nav-public.json').read_text())
        r=decode_nav(d['snapshots'][-1])
        self.assertEqual(r['nav_usd'],1)
        self.assertGreaterEqual(r['age_hours'],0)
        self.assertIsNone(r['independent_nav_usd'])
        self.assertIsNone(r['actual_nav_gap_pct'])

    def test_future_update_rejected(self):
        d=json.loads((ROOT/'data/nav-public.json').read_text())['snapshots'][-1]
        d['header']['result']['timestamp']='0x1'
        self.assertEqual(decode_nav(d)['status'],'invalid')

    def test_payment_cash_and_principal_reconcile_without_double_count(self):
        r=json.loads((ROOT/'data/verified-payment.json').read_text())['receipt']['result']
        p=payment_values(r)
        self.assertAlmostEqual(p['principal_applied_usdc']+p['interest_applied_usdc'],p['credit_line_cash_in_usdc'],places=6)
        self.assertAlmostEqual(p['principal_applied_usdc'],673936.577076,places=6)
        self.assertAlmostEqual(p['senior_pool_cash_received_usdc'],759585.890714,places=6)
        r['status']='0x0'
        with self.assertRaises(ValueError):payment_values(r)
