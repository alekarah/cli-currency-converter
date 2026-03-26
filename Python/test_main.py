#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from io import StringIO

sys.path.insert(0, os.path.dirname(__file__))
from main import (
    convert_currency,
    format_time_ago,
    load_config,
    output_csv,
    filter_history,
    CONFIG_FILE,
)


class TestConvertCurrency(unittest.TestCase):
    def setUp(self):
        self.rates_data = {
            "rates": {"RUB": 83.63, "EUR": 0.87, "CNY": 6.91}
        }

    def test_success(self):
        result, rate = convert_currency(100, "USD", "RUB", self.rates_data)
        self.assertAlmostEqual(result, 8363.0)
        self.assertAlmostEqual(rate, 83.63)

    def test_unknown_currency(self):
        with self.assertRaises(SystemExit):
            convert_currency(100, "USD", "XYZ", self.rates_data)

    def test_zero_amount(self):
        result, rate = convert_currency(0, "USD", "EUR", self.rates_data)
        self.assertEqual(result, 0.0)

    def test_fractional_amount(self):
        result, rate = convert_currency(1.5, "USD", "EUR", self.rates_data)
        self.assertAlmostEqual(result, 1.5 * 0.87)


class TestFormatTimeAgo(unittest.TestCase):
    def test_just_now(self):
        result = format_time_ago(timedelta(seconds=30))
        self.assertEqual(result, "только что")

    def test_minutes(self):
        result = format_time_ago(timedelta(minutes=5))
        self.assertIn("минут", result)

    def test_one_minute(self):
        result = format_time_ago(timedelta(minutes=1))
        self.assertIn("минут", result)

    def test_hours(self):
        result = format_time_ago(timedelta(hours=3))
        self.assertIn("час", result)

    def test_one_hour(self):
        result = format_time_ago(timedelta(hours=1))
        self.assertIn("час", result)

    def test_days(self):
        result = format_time_ago(timedelta(days=2))
        self.assertIn("дн", result)


class TestLoadConfig(unittest.TestCase):
    def test_defaults_when_no_file(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            cfg = load_config()
        self.assertEqual(cfg["default_from"], "USD")
        self.assertEqual(cfg["default_to"], "RUB")
        self.assertEqual(cfg["output_format"], "text")

    def test_from_file(self):
        config_data = {
            "default_from": "eur",
            "default_to": "cny",
            "output_format": "JSON"
        }
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(config_data, f)
            tmp_path = f.name

        try:
            import main as m
            orig = m.CONFIG_FILE
            m.CONFIG_FILE = tmp_path
            cfg = m.load_config()
            m.CONFIG_FILE = orig
        finally:
            os.unlink(tmp_path)

        self.assertEqual(cfg["default_from"], "EUR")
        self.assertEqual(cfg["default_to"], "CNY")
        self.assertEqual(cfg["output_format"], "json")

    def test_uppercase_normalization(self):
        config_data = {"default_from": "gbp", "default_to": "jpy", "output_format": "CSV"}
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(config_data, f)
            tmp_path = f.name

        try:
            import main as m
            orig = m.CONFIG_FILE
            m.CONFIG_FILE = tmp_path
            cfg = m.load_config()
            m.CONFIG_FILE = orig
        finally:
            os.unlink(tmp_path)

        self.assertEqual(cfg["default_from"], "GBP")
        self.assertEqual(cfg["default_to"], "JPY")
        self.assertEqual(cfg["output_format"], "csv")


class TestOutputCSV(unittest.TestCase):
    def test_format(self):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            output_csv("USD", "RUB", 100, 8363.0, 83.63)
            output = mock_stdout.getvalue().strip()

        parts = output.split(",")
        self.assertEqual(len(parts), 6)
        self.assertEqual(parts[1], "USD")
        self.assertEqual(parts[2], "RUB")
        self.assertEqual(parts[3], "100.00")
        self.assertEqual(parts[4], "8363.00")

    def test_rate_precision(self):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            output_csv("USD", "EUR", 1, 0.87, 0.87)
            output = mock_stdout.getvalue().strip()

        parts = output.split(",")
        self.assertIn("0.870000", parts[5])


class TestFilterHistory(unittest.TestCase):
    def setUp(self):
        self.history = [
            {"from_currency": "USD", "to_currency": "RUB", "exchange_rate": 83.0},
            {"from_currency": "USD", "to_currency": "EUR", "exchange_rate": 0.87},
            {"from_currency": "EUR", "to_currency": "RUB", "exchange_rate": 95.0},
            {"from_currency": "GBP", "to_currency": "CNY", "exchange_rate": 8.5},
        ]

    def test_filter_by_pair(self):
        result = filter_history(self.history, "USD/RUB")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["to_currency"], "RUB")
        self.assertEqual(result[0]["from_currency"], "USD")

    def test_filter_by_single_currency(self):
        result = filter_history(self.history, "USD")
        self.assertEqual(len(result), 2)

    def test_filter_by_single_currency_as_target(self):
        result = filter_history(self.history, "RUB")
        self.assertEqual(len(result), 2)

    def test_no_filter(self):
        result = filter_history(self.history, "")
        self.assertEqual(len(result), 4)

    def test_no_matches(self):
        result = filter_history(self.history, "JPY/CNY")
        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main()
