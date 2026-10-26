import sys
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from reconcile import compare, METRICS


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.frame=pd.DataFrame([{'month':'2025-10','service':'transfer',**{m:1 for m in METRICS}}])

    def test_equal(self):
        self.assertTrue(compare(self.frame,self.frame)['passed'])

    def test_one_fil_difference_fails(self):
        altered=self.frame.copy()
        altered.loc[0,'gross_value_minor']+=1
        with self.assertRaises(AssertionError):
            compare(self.frame,altered)

    def test_duplicate_grain_fails(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            compare(self.frame,pd.concat([self.frame,self.frame]))


if __name__=='__main__':unittest.main()
