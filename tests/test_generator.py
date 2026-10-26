import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from generate import generate, validate


class GeneratorTests(unittest.TestCase):
    def setUp(self):
        self.tables, self.config = generate(30, 500, 42, '2026-10-25')

    def test_deterministic_and_valid(self):
        other, config = generate(30, 500, 42, '2026-10-25')
        self.assertEqual(config, self.config)
        for name in other:
            self.assertTrue(other[name].equals(self.tables[name]))
        self.assertTrue(validate(self.tables, self.config)['passed'])

    def test_reject_corruptions(self):
        def duplicate(t):
            t['transactions'].loc[1, 'id'] = t['transactions'].loc[0, 'id']
        def missing_reference(t):
            t['transactions'].loc[0, 'sender_id'] = 'UNKNOWN'
        def invalid_date(t):
            t['transactions'].loc[0, 'occurred_at'] = 'not-a-date'
        def future_account(t):
            t['customers']['created_at'] = '2030-01-01T00:00:00Z'
        def negative_amount(t):
            t['transactions'].loc[0, 'amount_minor'] = -1
        def incorrect_refund(t):
            t['reversals'].loc[0, 'fee_refund_minor'] = 999999
        def missing_participant(t):
            index = t['transactions'].index[t['transactions']['type'].eq('transfer')][0]
            t['transactions'].loc[index, 'recipient_id'] = ''
        def failed_original(t):
            original = t['reversals'].loc[0, 'original_id']
            t['transactions'].loc[t['transactions']['id'].eq(original), 'status'] = 'failed'
        def invalid_reversal_time(t):
            t['reversals']['occurred_at'] = 'invalid'
        def duplicate_reversal(t):
            t['reversals'].loc[1, 'original_id'] = t['reversals'].loc[0, 'original_id']
        for corrupt in [duplicate, missing_reference, invalid_date, future_account, negative_amount,
                        incorrect_refund, missing_participant, failed_original, invalid_reversal_time, duplicate_reversal]:
            with self.subTest(corruption=corrupt.__name__):
                tables = {name: frame.copy() for name, frame in self.tables.items()}
                # Object dtype permits intentional malformed timestamp injection.
                tables['transactions']['occurred_at'] = tables['transactions']['occurred_at'].astype(object)
                corrupt(tables)
                self.assertFalse(validate(tables, self.config)['passed'])

    def test_small_dataset_with_no_reversals(self):
        tables, config = generate(2, 12, 1, '2024-03-15')
        tables['reversals'] = tables['reversals'].iloc[:0]
        self.assertTrue(validate(tables, config)['passed'])


if __name__ == '__main__':
    unittest.main()
