import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from receiver import Receiver, parse

GOOD = b'K2,123,demo,0.2,0.3,1,0,0,0\n'


class ReceiverTests(unittest.TestCase):
    def test_fragmented_and_combined(self):
        r = Receiver()
        r.feed(GOOD[:15], 0)
        self.assertEqual(r.count, 0)
        r.feed(GOOD[15:]+GOOD, .1)
        self.assertEqual(r.count, 2)
        self.assertEqual(r.snapshot(.2)['right'], .2)

    def test_timeout_and_recovery(self):
        r = Receiver(.5)
        r.feed(GOOD, 1)
        self.assertEqual(r.snapshot(1.5)['right'], 0)
        self.assertFalse(r.snapshot(1.5)['orientation_valid'])
        r.feed(GOOD, 2)
        self.assertTrue(r.snapshot(2.1)['orientation_valid'])

    def test_invalid_does_not_refresh(self):
        r = Receiver()
        r.feed(GOOD, 0)
        r.feed(GOOD.replace(b'0.2', b'nan'), .4)
        self.assertEqual(r.invalid, 1)
        self.assertEqual(r.snapshot(.6)['state'], 'stale')

    def test_overflow_recovers(self):
        r = Receiver()
        r.feed(b'x'*1000+b'\n'+GOOD, 0)
        self.assertEqual((r.invalid, r.count), (1, 1))
        self.assertLessEqual(len(r.buffer), 256)

    def test_comments_states_and_ranges(self):
        self.assertIsNone(parse('# hello'))
        for line in ['K2,1,bogus,0,0,1,0,0,0', 'K2,1,demo,2,0,1,0,0,0',
                     'K2,1,demo,0,0,0,0,0,0', 'K2,-1,demo,0,0,1,0,0,0']:
            with self.assertRaises(ValueError):
                parse(line)
        r = Receiver()
        r.feed(GOOD.replace(b'demo', b'calibrating'), 0)
        self.assertEqual(r.snapshot(.1)['right'], 0)
        self.assertFalse(r.snapshot(.1)['orientation_valid'])


if __name__ == '__main__':
    unittest.main()
