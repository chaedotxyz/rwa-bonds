import json
import tempfile
import unittest
from pathlib import Path
from src.empirical import generate, route_bound

class EmpiricalTests(unittest.TestCase):
    def test_route_bound_does_not_invent_cash_or_ignore_pause(self):
        self.assertIsNone(route_bound(False, 20, None))
        self.assertIsNone(route_bound(None, 20, 30))
        self.assertEqual(route_bound(True, 20, 30), 0)
        self.assertEqual(route_bound(False, 20, 30), 20)
        self.assertEqual(route_bound(False, 20, 4), 4)

    def test_historical_credit_data_and_unidentified_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            generate(out)
            d=json.loads((out/'empirical_manifest.json').read_text())
            self.assertFalse(d['assumption_sampling'])
            rows=[r for r in d['observations'] if r['product']=='Lend East' and r['metric']=='credit_line_principalOwed()']
            self.assertEqual(len(rows),4)
            self.assertEqual(rows[0]['value'],0)
            self.assertAlmostEqual(rows[1]['value'],10149999.830483)
            unknown=[r for r in d['findings'] if r['status']=='not_identified']
            self.assertEqual(len(unknown),6)
            self.assertTrue(all(r['value'] is None for r in unknown))
            routes=d['buidl_routes']
            self.assertEqual(routes[0]['necessary_condition_ceiling_usdc'],19500000)
            self.assertEqual(routes[-1]['necessary_condition_ceiling_usdc'],0)
            self.assertTrue(all(r['executable_quote_usdc'] is None for r in routes))
            self.assertTrue(all(r['as_of'] for r in routes))
