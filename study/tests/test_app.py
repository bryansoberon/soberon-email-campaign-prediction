"""Pruebas funcionales contra campañas reales y contratos inválidos."""
import io
import json
import unittest
import copy
import tempfile
import pandas as pd
from app.server import create_app
from experiment.core import ROOT, REQUIRED


class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace=tempfile.TemporaryDirectory()
        cls.app=create_app(cls.workspace.name)
        cls.app.config['TESTING']=True
        cls.client=cls.app.test_client()
        cls.token=cls.client.get('/api/summary').json['token']
        cls.headers={'X-Workspace-Token':cls.token}
        cls.comparison=pd.read_parquet(ROOT/'runtime/comparison.parquet')

    @classmethod
    def tearDownClass(cls):cls.workspace.cleanup()

    def setUp(self):
        self.client.post('/api/demo',headers=self.headers)
        self.example=self.client.get('/api/example').json

    def predict(self,payload=None):
        return self.client.post('/api/predict',json=self.example if payload is None else payload,headers=self.headers)

    def test_real_campaign_reproduces_reserved_prediction(self):
        result=self.predict()
        self.assertEqual(result.status_code,200)
        row=self.comparison.loc[self.comparison.campaign_id.eq(self.example['campaign_id'])].iloc[0]
        for target in ['clicks','unsubscribes']:
            self.assertAlmostEqual(result.json['outputs'][target]['rate_pct'],float(row['product_'+target]),places=9)
        self.assertGreaterEqual(result.json['mature_campaigns'],5)

    def test_import_real_history_preserves_prediction(self):
        before=self.predict().json
        with (ROOT/'runtime/historial_real_ejemplo.csv').open('rb') as f:
            response=self.client.post('/api/import',data={'file':(io.BytesIO(f.read()),'historial.csv')},headers=self.headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['accepted'],1758)
        after=self.predict().json
        self.assertEqual(before['outputs'],after['outputs'])
        self.assertTrue(any('validación externa' in x for x in after['warnings']))

    def test_new_company_uses_explicit_fallback(self):
        self.example['client_id']='empresa_nueva'
        result=self.predict().json
        selection=json.loads((ROOT/'results/selection.json').read_text(encoding='utf-8'))
        self.assertEqual(result['mature_campaigns'],0)
        for target in ['clicks','unsubscribes']:
            self.assertEqual(result['outputs'][target]['rate_pct'],selection['targets'][target]['global_median'])
        self.assertTrue(result['warnings'])

    def test_invalid_prediction_contract(self):
        bad=[[],{}, {'fields':[]},dict(self.example,when='2024-01-01'),dict(self.example,when=None)]
        for value in [-1,'NaN',1.5,None]:
            p=copy.deepcopy(self.example);p['fields']['message_links_count']=value;bad.append(p)
        for payload in bad:
            with self.subTest(payload=payload):self.assertEqual(self.predict(payload).status_code,400)

    def test_bad_import_does_not_replace_workspace(self):
        before=self.client.get('/api/summary').json
        for content in [b'a,b\n1,2\n',(','.join(REQUIRED)+'\n').encode()]:
            response=self.client.post('/api/import',data={'file':(io.BytesIO(content),'invalid.csv')},headers=self.headers)
            self.assertEqual(response.status_code,400)
        after=self.client.get('/api/summary').json
        self.assertEqual(before['rows'],after['rows']);self.assertTrue(after['is_demo'])

    def test_export_preserves_result(self):
        before=self.predict().json
        response=self.client.get('/download/prediction.json')
        self.assertEqual(response.status_code,200)
        self.assertEqual(json.loads(response.data),before)
        template=self.client.get('/download/template.csv').data.decode('utf-8-sig').strip().split(',')
        self.assertEqual(template,list(REQUIRED))

    def test_saved_prediction_matches_observation_and_survives_restart(self):
        result=self.predict().json
        records=self.client.get('/api/saved').json['rows']
        self.assertEqual(records[0]['registered_at'],result['registered_at'])
        row=self.comparison.loc[self.comparison.campaign_id.eq(self.example['campaign_id'])].iloc[0]
        self.assertAlmostEqual(records[0]['observed']['clicks'],row.observed_clicks,places=10)
        self.assertEqual(records[0]['mode'],'Reproducción histórica')
        restarted=create_app(self.workspace.name).test_client()
        self.assertEqual(restarted.get('/api/saved').json['rows'][0]['registered_at'],result['registered_at'])
        self.assertEqual(restarted.get('/api/summary').json['rows'],1758)

    def test_changed_message_does_not_inherit_observation(self):
        self.example['fields']['message_links_count']+=1
        self.predict()
        record=self.client.get('/api/saved').json['rows'][0]
        self.assertIsNone(record['observed'])
        self.assertIn('no coinciden',record['status'])

    def test_write_guard(self):
        self.assertEqual(self.client.post('/api/demo').status_code,403)
        self.assertEqual(self.client.post('/api/predict',json=self.example).status_code,403)

    def test_views_and_archived_results(self):
        for path in ['/','/static/style.css','/static/app.js','/api/evaluation','/api/comparison','/api/history?client='+self.example['client_id'],'/figures/01_error_final.png']:
            with self.subTest(path=path):self.assertEqual(self.client.get(path).status_code,200)
        self.assertEqual(self.client.get('/api/evaluation').json['primary_n'],275535)


if __name__=='__main__':unittest.main()
