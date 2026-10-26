"""Validate the actual PBIR files, field bindings and intentional relationships."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'powerbi'


class ReportTests(unittest.TestCase):
    def test_pages_fields_and_layout(self):
        pages = PROJECT / 'Wallet.Report/definition/pages'
        metadata = json.loads((pages/'pages.json').read_text(encoding='utf-8'))
        self.assertEqual(len(metadata['pageOrder']), 4)
        for page_id in metadata['pageOrder']:
            page = json.loads((pages/page_id/'page.json').read_text(encoding='utf-8'))
            files = list((pages/page_id/'visuals').glob('*/visual.json'))
            self.assertGreaterEqual(len(files), 8)
            for path in files:
                v = json.loads(path.read_text(encoding='utf-8'))
                self.assertEqual(v['name'], path.parent.name)
                p = v['position']
                self.assertGreaterEqual(p['x'], 0)
                self.assertGreaterEqual(p['y'], 0)
                self.assertLessEqual(p['x']+p['width'], page['width'])
                self.assertLessEqual(p['y']+p['height'], page['height'])
                for role in v['visual'].get('query', {}).get('queryState', {}).values():
                    for item in role['projections']:
                        kind, ref = next(iter(item['field'].items()))
                        table, name = ref['Expression']['SourceRef']['Entity'], ref['Property']
                        definition = (PROJECT/'Wallet.SemanticModel/definition/tables'/f'{table}.tmdl').read_text(encoding='utf-8-sig')
                        pattern = rf"\b{kind.lower()} (?:'{re.escape(name)}'|{re.escape(name)})(?:\s|$)"
                        self.assertRegex(definition, pattern)

    def test_scope_and_synthetic_label(self):
        report = json.loads((PROJECT/'Wallet.Report/definition/report.json').read_text(encoding='utf-8'))
        scope = report['filterConfig']['filters'][0]
        self.assertEqual(scope['field']['Column']['Property'], 'is_in_reporting_window')
        self.assertEqual(scope['filter']['Where'][0]['Condition']['In']['Values'], [[{'Literal': {'Value':'true'}}]])
        for page in (PROJECT/'Wallet.Report/definition/pages').iterdir():
            if page.is_dir():
                text = '\n'.join(p.read_text(encoding='utf-8') for p in page.glob('visuals/*/visual.json'))
                self.assertIn('SYNTHETIC DATA', text)


if __name__ == '__main__':
    unittest.main()
