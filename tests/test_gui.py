import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import App
from pricing import read_catalog


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = Path(self.tmp.name) / "prices.json"
        self.app = App(self.file)
        self.app.withdraw()
        self.app.update()

    def tearDown(self):
        self.app.update_idletasks()
        self.app.destroy()
        self.tmp.cleanup()

    def test_live_calculation_cache_and_error_clearing(self):
        app = self.app
        app.model.set("GPT-6.1 Sol / Standard 短上下文")
        app.select_model()
        app.cached.set("900k")
        app.write.set("50k")
        self.assertIn("USD  1.315", app.api_result.cget("text"))
        app.cached.set("2m")
        self.assertEqual(app.last_result, "")
        self.assertNotIn("1.315", app.api_result.cget("text"))
        app.cached.set("900k")
        app.rate_vars["input"].set("3")
        self.assertIn("自定义单价", app.api_result.cget("text"))

    def test_subscription_tab_glm_capacity_and_copy(self):
        app = self.app
        app.tabs.select(1)
        app.plan.set("GLM Coding Lite / Z.ai")
        app.select_plan()
        app.cached.set("900k")
        app.update()
        self.assertIn("462", app.quota_note.get())
        app.off_peak.set(True)
        self.assertIn("231", app.quota_note.get())
        app.capacity_button.invoke()
        self.assertGreater(int(app.month.get()), 200_000_000)
        app.copy_result()
        self.assertIn("GLM Coding Lite", app.clipboard_get())
        self.assertIn("使用假设", app.clipboard_get())
        app.month.set("0")
        self.assertEqual(app.last_result, "")

    def test_cheapest_button_selects_saved_model_and_rejects_invalid_usage(self):
        app = self.app
        app.total.set("1.09b")
        app.cached.set("1.04b")
        app.output.set("2.89m")
        app.tabs.select(1)
        expected = min(app.catalog["models"], key=lambda m: sum(
            float(m["rates"][k]) * count for k, count in
            (("input", 50), ("cached", 1040), ("output", 2.89))) / (7 if m["currency"] == "CNY" else 1))
        with patch("app.messagebox.showinfo") as info:
            app.cheapest_button.invoke()
        self.assertEqual(app.model.get(), expected["name"])
        self.assertEqual(app.tabs.index(app.tabs.select()), 0)
        self.assertIn(expected["name"], info.call_args.args[1])
        self.assertIn("USD", app.api_result.cget("text"))
        app.cached.set("2b")
        with patch("app.messagebox.showerror") as error:
            app.cheapest_button.invoke()
        error.assert_called_once()
        self.assertEqual(app.model.get(), expected["name"])

    def test_save_and_reload_custom_price(self):
        app = self.app
        app.rate_vars["input"].set("0.123")
        with patch("app.simpledialog.askstring", return_value="My custom model"):
            app.save_model()
        self.assertEqual(app.model.get(), "My custom model")
        self.assertEqual(read_catalog(self.file)["models"][-1]["rates"]["input"], "0.123")
        reloaded = App(self.file)
        reloaded.withdraw()
        reloaded.update()
        try:
            self.assertIn("My custom model", reloaded.model_combo["values"])
        finally:
            reloaded.destroy()

    def test_billion_inputs_across_api_and_subscription(self):
        app = self.app
        app.model.set("GPT-6.1 Sol / Standard 短上下文")
        app.select_model()
        app.total.set("1.5B")
        app.cached.set("1b")
        app.write.set("0.1B")
        app.output.set("0.2B")
        self.assertIn("USD  3150", app.api_result.cget("text").replace(",", ""))
        app.tabs.select(1)
        app.plan.set("Cursor Pro")
        app.select_plan()
        app.month.set("1.7B")
        app.update()
        self.assertIn("USD  20", app.sub_result.cget("text"))

    def test_historical_estimate_is_labeled_and_editable(self):
        app = self.app
        app.tabs.select(1)
        app.plan.set("Cursor Pro")
        app.select_plan()
        app.sample_button.invoke()
        self.assertEqual(app.month.get(), "290200000")
        self.assertIn("可能已过时", app.sub_result.cget("text"))
        self.assertIn("2026-06-27", app.quota_note.get())
        app.month.set("10m")
        self.assertNotIn("可能已过时", app.sub_result.cget("text"))
        app.plan.set("Kimi Allegretto / 帮助中心月费")
        app.select_plan()
        app.sample_button.invoke()
        self.assertEqual(app.month.get(), "950000000")
        self.assertIn("并非完整月账单", app.quota_note.get())

    def test_failed_persistence_keeps_active_data(self):
        original = copy.deepcopy(self.app.catalog)
        updated = copy.deepcopy(original)
        updated["models"][0]["rates"]["input"] = "99"
        with patch("app.save_catalog", side_effect=OSError("cannot write")), self.assertRaises(OSError):
            self.app.commit_catalog(updated)
        self.assertEqual(self.app.catalog, original)

    def test_import_export_buttons(self):
        app = self.app
        export = Path(self.tmp.name) / "export.txt"
        with patch("app.filedialog.asksaveasfilename", return_value=str(export)):
            app.export_catalog()
        self.assertEqual(read_catalog(export), app.catalog)
        with patch("app.filedialog.askopenfilename", return_value=str(export)), patch("app.messagebox.askyesno", return_value=True):
            app.import_catalog()
        self.assertEqual(read_catalog(self.file), app.catalog)


if __name__ == "__main__":
    unittest.main()
