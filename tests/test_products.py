import json
import tempfile
import unittest
from pathlib import Path
from src.products import generate_products,reading
class ProductTests(unittest.TestCase):
    def test_missing_is_not_zero(self):
        self.assertIsNone(reading({'calls':[]},'0x1','balance()'))
    def test_unmeasured_nav_and_profit_remain_null(self):
        with tempfile.TemporaryDirectory() as d:
            generate_products(Path(d))
            m=json.loads((Path(d)/'product_manifest.json').read_text())
            self.assertTrue(all(v is None for v in m['identified_claims'].values()))
            self.assertEqual(m['primary_products'],['BlackRock BUIDL','Goldfinch Lend East'])
            self.assertTrue(any(r['product']=='Lend East' for r in m['observations']))
            self.assertFalse((Path(d)/'samples.csv').exists())
if __name__=='__main__':unittest.main()
