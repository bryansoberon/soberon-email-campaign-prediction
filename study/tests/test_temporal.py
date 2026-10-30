import unittest
import numpy as np
import pandas as pd
from experiment.core import history_features, FEATURES, MESSAGE, HORIZON, clean_campaigns, TARGETS


class TemporalIntegrity(unittest.TestCase):
    def setUp(self):
        self.history = pd.DataFrame({'client_id':['a','a','a','b'], 'campaign_id':['1','2','3','4'],
            'campaign_sent_time':pd.to_datetime(['2023-01-01Z'.replace('Z','T00:00Z'), '2023-01-03T00:00Z',
                                                '2023-01-10T00:00Z','2023-01-01T00:00Z'], utc=True),
            'campaign_subscribers_count':[100,200,100,100], 'y_clicks':[10.,20.,90.,80.],
            'y_unsubscribes':[1.,2.,9.,8.]})

    def test_strict_maturation_and_company_isolation(self):
        q = pd.DataFrame({'client_id':['a','a','a','new'], 'campaign_sent_time':pd.to_datetime([
            '2023-01-04T00:00Z','2023-01-04T00:01Z','2023-01-07T00:00Z','2023-01-07T00:00Z'], utc=True)})
        f = history_features(self.history,q)
        np.testing.assert_array_equal(f.history_n, [0,1,2,0])
        self.assertEqual(f.loc[2,'history_clicks_mean'],15.)
        self.assertAlmostEqual(f.loc[2,'history_clicks_weighted'], 50/3)

    def test_future_response_cannot_change_earlier_features(self):
        q = self.history.iloc[[1]].copy()
        q['campaign_sent_time'] = pd.Timestamp('2023-01-07T00:00Z')
        before = history_features(self.history,q)
        self.assertEqual(before.iloc[0].history_n, 2)
        changed = self.history.copy()
        changed.loc[2,'y_clicks'] = 0
        pd.testing.assert_frame_equal(before, history_features(changed,q))

    def test_unsorted_queries_keep_index_and_last_five(self):
        h = pd.DataFrame({'client_id':['x']*7, 'campaign_id':list(map(str,range(7))),
            'campaign_sent_time':pd.date_range('2023-01-01',periods=7,freq='4D',tz='UTC'),
            'campaign_subscribers_count':[100]*7, 'y_clicks':[0,1,2,3,4,5,6],
            'y_unsubscribes':[0]*7})
        q = pd.DataFrame({'client_id':['x','x'],'campaign_sent_time':pd.to_datetime([
            '2023-02-01T00:00Z','2023-01-08T00:00Z'],utc=True)},index=[99,42])
        f = history_features(h,q)
        self.assertEqual(f.loc[99,'history_clicks_last5_median'],4)
        self.assertEqual(f.loc[42,'history_n'],1)

    def test_no_current_response_or_volume_in_features(self):
        for col in FEATURES:
            self.assertFalse(col.startswith('campaign_'))
            self.assertFalse(col.startswith('y_'))
        self.assertNotIn('message_links_blocked_count', MESSAGE)

    def test_all_duplicate_ids_excluded(self):
        d = self.history.copy()
        for c in MESSAGE: d[c] = 0
        d['campaign_test_type']='0'
        for c in TARGETS.values(): d[c]=1
        d.loc[1,'campaign_id']='1'
        cleaned, _ = clean_campaigns(d)
        self.assertEqual(set(cleaned.campaign_id), {'3','4'})


if __name__=='__main__': unittest.main()
