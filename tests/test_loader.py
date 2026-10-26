"""Offline input-integrity tests; these do not claim a PostgreSQL load succeeded."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from generate import generate, summarize
from load import read_dataset
import hashlib


class LoaderInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        tables, config = generate(20, 200, 42, '2026-10-25')
        config['sha256'] = {}
        for name, frame in tables.items():
            path = self.folder / f'{name}.csv'
            frame.to_csv(path, index=False, date_format='%Y-%m-%dT%H:%M:%SZ', lineterminator='\n')
            config['sha256'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        (self.folder / 'manifest.json').write_text(json.dumps(config), encoding='utf-8')
        (self.folder / 'summary.json').write_text(json.dumps(summarize(tables, config)), encoding='utf-8')

    def test_valid_source_and_stable_fingerprint(self):
        first = read_dataset(self.folder)
        second = read_dataset(self.folder)
        self.assertEqual(first[4], second[4])
        self.assertEqual(first[3]['row_counts']['transactions'], 200)

    def test_changed_csv_rejected_before_connection(self):
        path = self.folder / 'customers.csv'
        path.write_bytes(path.read_bytes().replace(b'C000001', b'C999999'))
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            read_dataset(self.folder)

    def test_changed_summary_rejected_before_connection(self):
        path = self.folder / 'summary.json'
        summary = json.loads(path.read_text())
        summary['net_fee_revenue_minor'] += 1
        path.write_text(json.dumps(summary), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'summary mismatch'):
            read_dataset(self.folder)


if __name__ == '__main__':
    unittest.main()
