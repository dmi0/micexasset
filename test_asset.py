import asset
import unittest
from unittest.mock import Mock
from datetime import date


class TestPortfolio(unittest.TestCase):

    def test_accrued_interest(self):
        client = Mock()
        client.get_history.return_value = [
            {"TRADEDATE": "2018-08-29", "ACCINT": 121, "COUPONPERCENT": 1},
            {"TRADEDATE": "2018-08-30", "ACCINT": 122, "COUPONPERCENT": 1},
            {"TRADEDATE": "2018-08-31", "ACCINT": 123, "COUPONPERCENT": 1},
        ]
        a = asset.MicexISSAsset(client, 'XXX')
        self.assertEqual(a.accrued_interest(date(2018, 8, 31)), 123)

        client.get_history.return_value = [
            {"TRADEDATE": "2018-08-20", "ACCINT": 30.03, "COUPONPERCENT": 8.84}
        ]
        self.assertLess(
            abs(a.accrued_interest(date(2018, 9, 1)) - 32.94),
            0.01
        )

    def test_get_history(self):
        client = Mock()
        client.get_history.return_value = [
            {"TRADEDATE": "2018-08-26", "ACCINT": 1},
            {"TRADEDATE": "2018-08-27", "ACCINT": 2},
            {"TRADEDATE": "2018-08-28", "ACCINT": 3},
            {"TRADEDATE": "2018-08-29", "ACCINT": 4},
            {"TRADEDATE": "2018-08-30", "ACCINT": 5},
            {"TRADEDATE": "2018-08-31", "ACCINT": 6},
            {"TRADEDATE": "2018-09-01", "ACCINT": 7},
        ]
        a = asset.MicexISSAsset(client, 'XXX')
        r = []
        for i in a._get_history(date(2018, 8, 30), date(2018, 8, 31)):
            r.append(i['TRADEDATE'])
        self.assertEqual(r, [date(2018, 8, 30), date(2018, 8, 31)])

        r = []
        for i in a._get_history(date(2018, 8, 31), date(2018, 9, 3)):
            r.append(i['TRADEDATE'])
        self.assertEqual(r, [date(2018, 8, 31), date(2018, 9, 1)])

        client.get_history.return_value = [
            {"TRADEDATE": "2018-08-26", "ACCINT": 1},
            {"TRADEDATE": "2018-08-27", "ACCINT": 2},
            {"TRADEDATE": "2018-08-28", "ACCINT": 3},
            {"TRADEDATE": "2018-08-29", "ACCINT": 4},
            {"TRADEDATE": "2018-08-30", "ACCINT": 5},
            {"TRADEDATE": "2018-08-31", "ACCINT": 6},
            {"TRADEDATE": "2018-09-01", "ACCINT": 7},
        ]
        r = []
        for i in a._get_history(date(2018, 8, 20), date(2018, 8, 26)):
            r.append(i['TRADEDATE'])
        self.assertEqual(r, [date(2018, 8, 26)])


if __name__ == '__main__':
    unittest.main()
