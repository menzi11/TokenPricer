import copy
import json
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch

from pricing import (calculate, cheapest_models, convert, credits, number, parse_catalog,
                     read_catalog, save_catalog, subscription, tokens, usage)


class PricingTests(unittest.TestCase):
    def test_token_formats(self):
        for value, expected in [("1,000", 1000), ("1.5k", 1500), ("2M", 2000000), ("1.2万", 12000), ("0.01亿", 1000000), ("0", 0)]:
            self.assertEqual(tokens(value), expected)
        for value in ("-1", "1.5", "1,2", "NaN", "inf", "", "1e6", "1 m", "1,0000", "1000000000000001"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                tokens(value)

    def test_decimal_is_exact(self):
        counts = usage("1m", "900k", "100k", "50k")
        result = calculate(dict(input="2", cached="0.1", output="10", write="2.5"), counts)
        # 50k regular + 900k cache hits + 50k writes + 100k output.
        self.assertEqual(result["total"], D("1.315"))
        self.assertEqual(convert(result["total"], "USD", "7.2"), (D("1.315"), D("9.4680")))
        self.assertEqual(convert(D("7.2"), "CNY", "7.2"), (D(1), D("7.2")))

    def test_billion_token_formats_and_limits(self):
        for value, expected in [("1B", 10**9), ("1b", 10**9), ("1.5B", 1500000000), ("0.000000001B", 1), ("1,000,000B", 10**15)]:
            with self.subTest(value=value):
                self.assertEqual(tokens(value), expected)
        for value in ("0.0000000001B", "1000001B", "1BB"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                tokens(value)

    def test_invalid_cache_and_unsupported_write(self):
        with self.assertRaises(ValueError):
            usage(100, 90, 10, 11)
        with self.assertRaises(ValueError):
            calculate(dict(input=1, cached=0, output=1, write=None), usage(100, 0, 0, 1))
        self.assertEqual(calculate(dict(input=0, cached=0, output=0, write=None), usage(100, 0, 10))["total"], 0)

    def test_nonfinite_and_limits(self):
        for value in ("NaN", "Infinity", "-1", True, None, "1e16", "1e-50"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                number(value)
        with self.assertRaises(ValueError):
            convert(D(1), "USD", "0")

    def test_subscription_allocation(self):
        result = subscription(20, "10m", usage("900k", "500k", "100k"), extra=5)
        self.assertEqual(result, dict(monthly=D(25), per_million=D("2.5"), allocated=D("2.5")))
        with self.assertRaises(ValueError):
            subscription(20, 0, usage(0, 0, 0))
        with self.assertRaises(ValueError):
            subscription(20, 100, usage(101, 0, 0))

    def test_glm_formula(self):
        plan = dict(weights=dict(input="6.9", cached="1.7", output="24"))
        counts = usage("1m", "900k", "100k")
        self.assertEqual(credits(plan, counts), D(462))
        self.assertEqual(credits(plan, counts, True), D(231))
        self.assertIsNone(credits({}, counts))

    def test_subscription_cache_writes_only_restricted_for_glm(self):
        counts = usage(100, 50, 10, 20)
        self.assertIsNone(credits({}, counts))
        self.assertEqual(subscription(10, 110, counts)["allocated"], 10)
        with self.assertRaises(ValueError):
            credits(dict(weights=dict(input="6.9", cached="1.7", output="24")), counts)

    def test_cheapest_currency_ties_and_missing_write(self):
        models = [dict(name="USD", currency="USD", rates=dict(input="2", cached="1", output="3", write=None)),
                  dict(name="CNY", currency="CNY", rates=dict(input="7", cached="7", output="21", write="7"))]
        winners, compared, skipped = cheapest_models(models, usage("1m", 0, 0), "7")
        self.assertEqual([w[0]["name"] for w in winners], ["CNY"])
        self.assertEqual((compared, skipped), (2, 0))
        self.assertEqual(len(cheapest_models(models, usage("1m", "1m", 0), "7")[0]), 2)
        self.assertEqual(cheapest_models(models, usage(1, 0, 0, 1), "7")[1:], (1, 1))
        with self.assertRaises(ValueError):
            cheapest_models(models[:1], usage(1, 0, 0, 1), "7")
        with self.assertRaises(ValueError):
            cheapest_models(models, usage(1, 0, 0), "0")

    def test_catalog_roundtrip_and_atomic_failure(self):
        data = read_catalog(Path(__file__).parents[1] / "prices.json")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "prices.json"
            save_catalog(path, data)
            self.assertEqual(read_catalog(path), data)
            original = path.read_bytes()
            changed = copy.deepcopy(data)
            changed["models"][0]["rates"]["input"] = "42"
            with patch("pricing.os.replace", side_effect=OSError("disk failure")), self.assertRaises(OSError):
                save_catalog(path, changed)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(folder).glob("*.tmp")), [])

    def test_catalog_rejects_bad_data(self):
        data = read_catalog(Path(__file__).parents[1] / "prices.json")
        for mutate in (lambda d: d.update(version=True),
                       lambda d: d["models"][0].update(currency="EUR"),
                       lambda d: d["models"][0]["rates"].update(input="NaN"),
                       lambda d: d["models"].append(d["models"][0]),
                       lambda d: d["plans"][0].update(monthly=-1),
                       lambda d: d["models"][0].update(source="file:///a")):
            altered = copy.deepcopy(data)
            mutate(altered)
            with self.assertRaises(ValueError):
                parse_catalog(json.dumps(altered))
        with self.assertRaises(ValueError):
            parse_catalog('{"version":1,"version":1}')


if __name__ == "__main__":
    unittest.main()
