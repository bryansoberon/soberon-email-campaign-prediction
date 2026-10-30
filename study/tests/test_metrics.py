import unittest
import pandas as pd
import numpy as np
from experiment.core import metrics
from experiment.evaluate import interval

class EvaluationTests(unittest.TestCase):
    def test_macro_and_weighted_differ(self):
        m=metrics([0,10],[2,9],[1,9],['a','b'])
        self.assertEqual(m['mae_pp'],1.5)
        self.assertAlmostEqual(m['weighted_mae_pp'],1.1)
        self.assertEqual(m['bias_pp'],.5)

    def test_paired_interval_preserves_zero_and_constant_shift(self):
        f=pd.DataFrame({'client_id':['a','b']*8,
            'campaign_sent_time':pd.date_range('2024-01-01',periods=16,freq='7D',tz='UTC')})
        zero=interval(f,np.zeros(16),repeats=20)
        shift=interval(f,np.full(16,-2.),repeats=20)
        self.assertEqual(zero['lower_pp'],0.)
        self.assertEqual(zero['upper_pp'],0.)
        self.assertEqual(shift['lower_pp'],-2.)
        self.assertEqual(shift['upper_pp'],-2.)

if __name__=='__main__':unittest.main()
