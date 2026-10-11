"""TokenPricer desktop application. Runtime dependencies: Python + Tk only."""
from __future__ import annotations

import copy
import json
import os
import sys
import tkinter as tk
import webbrowser
from datetime import date
from decimal import Decimal
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from pricing import (MILLION, RATE_KEYS, calculate, cheapest_models, convert, credits, money,
                     number, parse_catalog, read_catalog, save_catalog,
                     subscription, usage)

BUILTIN = Path(__file__).with_name("prices.json")
USER_FILE = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".config")) / "TokenPricer" / "prices.json"


class App(tk.Tk):
    def __init__(self, user_file=USER_FILE):
        super().__init__()
        self.title("Token计价器 · TokenPricer")
        self.geometry("1080x820")
        self.minsize(980, 740)
        self.configure(bg="#f3f5fa")
        self.user_file = Path(user_file)
        self.catalog = read_catalog(BUILTIN)
        self.ready = False
        self.last_result = ""
        self.sample_month = None
        problem = None
        if self.user_file.exists():
            try:
                self.catalog = read_catalog(self.user_file)
            except (OSError, ValueError) as exc:
                problem = f"自定义价格读取失败，已使用内置价格；原文件未改动。\n{exc}"
        self._style()
        self._build()
        self.refresh_lists()
        self.ready = True
        self.recalculate()
        if problem:
            self.after(100, lambda: messagebox.showwarning("价格文件未载入", problem, parent=self))

    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", font=("Microsoft YaHei UI", 10))
        s.configure("TFrame", background="#f3f5fa")
        s.configure("TLabel", background="#f3f5fa", foreground="#19243b", font=("Microsoft YaHei UI", 10))
        s.configure("Muted.TLabel", foreground="#63718a")
        s.configure("Title.TLabel", font=("Microsoft YaHei UI", 24, "bold"))
        s.configure("TButton", padding=(12, 7), font=("Microsoft YaHei UI", 10))
        s.configure("TEntry", padding=7, fieldbackground="white")
        s.configure("TCombobox", padding=7, fieldbackground="white")
        s.configure("TLabelframe", background="#f3f5fa", bordercolor="#d7deea")
        s.configure("TLabelframe.Label", background="#f3f5fa", font=("Microsoft YaHei UI", 10, "bold"))
        s.configure("TNotebook", background="#f3f5fa", borderwidth=0)
        s.configure("TNotebook.Tab", padding=(22, 10))
        s.map("TNotebook.Tab", background=[("selected", "#dce7ff")])

    def var(self, value):
        var = tk.StringVar(self, value)
        var.trace_add("write", self.recalculate)
        return var

    def field(self, parent, label, var, row, column=0, width=19):
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=column, sticky="ew", padx=8, pady=6)
        ttk.Label(frame, text=label).pack(anchor="w", pady=(0, 5))
        entry = ttk.Entry(frame, textvariable=var, width=width)
        entry.pack(fill="x")
        return entry

    def _build(self):
        # Let high-DPI and shorter displays scroll instead of hiding sources/buttons.
        shell = ttk.Frame(self)
        shell.pack(fill="both", expand=True)
        canvas = tk.Canvas(shell, bg="#f3f5fa", highlightthickness=0)
        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        body = ttk.Frame(canvas, padding=22)
        window = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        self.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-int(e.delta / 120), "units") if e.widget.winfo_toplevel() == self else None)
        self.scroll_canvas = canvas
        top = ttk.Frame(body)
        top.pack(fill="x")
        ttk.Label(top, text="Token计价器", style="Title.TLabel").pack(side="left")
        ttk.Label(top, text="API 成本  /  订阅摊销", style="Muted.TLabel").pack(side="left", padx=18)
        ttk.Button(top, text="编辑价格 JSON", command=self.edit_catalog).pack(side="right")
        ttk.Button(top, text="导出", command=self.export_catalog).pack(side="right", padx=6)
        ttk.Button(top, text="导入", command=self.import_catalog).pack(side="right")
        ttk.Label(body, text="离线计算 · 不调用模型 · 不需要 API Key    |    价格快照：2026-10-11，非实时更新", style="Muted.TLabel").pack(anchor="w", pady=(8, 15))

        box = ttk.LabelFrame(body, text="这次要计算多少 token？", padding=8)
        box.pack(fill="x")
        self.total = self.var("1m")
        self.cached = self.var("0")
        self.output = self.var("100k")
        self.write = self.var("0")
        for col, (label, var) in enumerate((("总输入（含缓存部分）", self.total), ("其中缓存命中", self.cached), ("输出（含计费推理）", self.output), ("其中缓存写入", self.write))):
            box.columnconfigure(col, weight=1)
            self.field(box, label, var, 0, col)
        ttk.Label(box, text="支持 10k / 1M / 1B（10亿）/ 1万，大小写通用。缓存命中、写入是总输入的子集。", style="Muted.TLabel").grid(row=1, column=0, columnspan=4, sticky="w", padx=8, pady=5)

        fxrow = ttk.Frame(body)
        fxrow.pack(fill="x", pady=10)
        ttk.Label(fxrow, text="换算汇率  1 USD =").pack(side="left")
        self.fx = self.var("7")
        ttk.Entry(fxrow, textvariable=self.fx, width=8).pack(side="left", padx=8)
        ttk.Label(fxrow, text="CNY  （7 是演示值，请按实际汇率修改）", style="Muted.TLabel").pack(side="left")
        self.cheapest_button = ttk.Button(fxrow, text="定位最便宜模型", command=self.find_cheapest)
        self.cheapest_button.pack(side="right")

        self.tabs = ttk.Notebook(body)
        self.tabs.pack(fill="both", expand=True)
        api = ttk.Frame(self.tabs, padding=14)
        sub = ttk.Frame(self.tabs, padding=14)
        self.tabs.add(api, text="API 按量计价")
        self.tabs.add(sub, text="订阅成本估算")
        self.tabs.bind("<<NotebookTabChanged>>", self.recalculate)
        self._api(api)
        self._subscription(sub)
        bottom = ttk.Frame(self, padding=(22, 8))
        bottom.pack(fill="x")
        self.status = tk.StringVar(self, "就绪")
        ttk.Label(bottom, textvariable=self.status, style="Muted.TLabel").pack(side="left")
        ttk.Button(bottom, text="复制结果", command=self.copy_result).pack(side="right")
        ttk.Button(bottom, text="恢复内置价格", command=self.restore).pack(side="right", padx=8)

    def _api(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        self.model = tk.StringVar(self)
        self.model_combo = ttk.Combobox(parent, textvariable=self.model, state="readonly", width=52)
        self.model_combo.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.model_combo.bind("<<ComboboxSelected>>", self.select_model)
        left = ttk.Frame(parent)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        left.columnconfigure(0, weight=1)
        left.columnconfigure(1, weight=1)
        self.currency = self.var("USD")
        self.rate_vars = {k: self.var("0") for k in RATE_KEYS}
        ttk.Label(left, text="单价 / 每 1,000,000 token（可直接修改）").grid(row=0, column=0, columnspan=2, sticky="w", padx=8)
        for n, (key, label) in enumerate((("input", "普通输入"), ("cached", "缓存命中"), ("output", "输出"), ("write", "缓存写入（空白 = 未配置）"))):
            self.field(left, label, self.rate_vars[key], n // 2 + 1, n % 2)
        controls = ttk.Frame(left)
        controls.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        ttk.Combobox(controls, textvariable=self.currency, values=("USD", "CNY"), state="readonly", width=7).pack(side="left")
        ttk.Button(controls, text="另存自定义模型", command=self.save_model).pack(side="right")
        self.api_result = self.result_panel(parent, 1, 1)
        self.model_note = tk.StringVar(self)
        ttk.Label(parent, textvariable=self.model_note, wraplength=960, style="Muted.TLabel").grid(row=2, column=0, columnspan=2, sticky="w", pady=10)
        ttk.Label(parent, text="估算范围：文本 token。未包含税费、工具调用、缓存存储时长、音视频生成或地区附加费。", wraplength=960, style="Muted.TLabel").grid(row=3, column=0, columnspan=2, sticky="w")
        ttk.Button(parent, text="打开所选价格来源", command=lambda: self.open_source("models")).grid(row=4, column=0, sticky="w", pady=10)

    def _subscription(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        self.plan = tk.StringVar(self)
        self.plan_combo = ttk.Combobox(parent, textvariable=self.plan, state="readonly", width=52)
        self.plan_combo.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.plan_combo.bind("<<ComboboxSelected>>", self.select_plan)
        left = ttk.Frame(parent)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        left.columnconfigure(0, weight=1)
        left.columnconfigure(1, weight=1)
        self.fee = self.var("20")
        self.extra = self.var("0")
        self.month = self.var("10m")
        self.sub_currency = self.var("USD")
        self.field(left, "月费（可改为实付价）", self.fee, 0, 0)
        self.field(left, "预计每月额外费用", self.extra, 0, 1)
        self.field(left, "预计每月实际总 token", self.month, 1, 0)
        currency_frame = ttk.Frame(left)
        currency_frame.grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(currency_frame, text="月费及额外费用币种").pack(anchor="w", pady=(0, 5))
        ttk.Combobox(currency_frame, textvariable=self.sub_currency, values=("USD", "CNY"), state="readonly", width=10).pack(fill="x")
        self.off_peak = tk.BooleanVar(self, False)
        self.off_peak.trace_add("write", self.recalculate)
        self.off_check = ttk.Checkbutton(left, text="GLM：按低谷积分倍率估算", variable=self.off_peak)
        self.off_check.grid(row=2, column=0, columnspan=2, sticky="w", padx=8, pady=6)
        self.capacity_button = ttk.Button(left, text="按 GLM 周额度估算月 token", command=self.use_capacity)
        self.capacity_button.grid(row=3, column=0, columnspan=2, sticky="w", padx=8)
        self.sample_button = ttk.Button(left, text="使用网上历史估算", command=self.use_sample)
        self.sample_button.grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=6)
        self.sub_result = self.result_panel(parent, 1, 1)
        self.quota_note = tk.StringVar(self)
        ttk.Label(parent, textvariable=self.quota_note, wraplength=960).grid(row=2, column=0, columnspan=2, sticky="w", pady=8)
        self.plan_note = tk.StringVar(self)
        ttk.Label(parent, textvariable=self.plan_note, wraplength=960, style="Muted.TLabel").grid(row=3, column=0, columnspan=2, sticky="w", pady=6)
        row = ttk.Frame(parent)
        row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Button(row, text="打开套餐来源", command=lambda: self.open_source("plans")).pack(side="left")
        self.sample_source_button = ttk.Button(row, text="打开历史样本来源", command=self.open_sample)
        self.sample_source_button.pack(side="left", padx=8)
        ttk.Label(parent, text="10m 是演示用量；摊销成本不等于追加扣款，也不证明额度够用。", style="Muted.TLabel").grid(row=5, column=0, columnspan=2, sticky="w", pady=5)

    def result_panel(self, parent, row, col):
        panel = tk.Label(parent, text="", bg="#e4edff", fg="#174381", font=("Microsoft YaHei UI", 12), anchor="nw", justify="left", padx=20, pady=20, wraplength=420)
        panel.grid(row=row, column=col, sticky="nsew")
        return panel

    def selected(self, group):
        name = self.model.get() if group == "models" else self.plan.get()
        return next(row for row in self.catalog[group] if row["name"] == name)

    def refresh_lists(self):
        for group, combo, var in (("models", self.model_combo, self.model), ("plans", self.plan_combo, self.plan)):
            values = [row["name"] for row in self.catalog[group]]
            combo.configure(values=values)
            if var.get() not in values:
                var.set(values[0])
        self.select_model()
        self.select_plan()

    def select_model(self, _event=None):
        row = self.selected("models")
        self.currency.set(row["currency"])
        for key in RATE_KEYS:
            value = row["rates"][key]
            self.rate_vars[key].set("" if value is None else str(value))
        self.recalculate()

    def select_plan(self, _event=None):
        row = self.selected("plans")
        self.sample_month = None
        self.month.set("10m")
        self.fee.set(row["monthly"])
        self.sub_currency.set(row["currency"])
        self.extra.set("0")
        self.off_peak.set(False)
        state = "normal" if "weights" in row else "disabled"
        self.off_check.configure(state=state)
        self.capacity_button.configure(state=state)
        for button in (self.sample_button, self.sample_source_button):
            button.configure(state="normal" if "sample" in row else "disabled")
        self.recalculate()

    def counts(self):
        return usage(self.total.get(), self.cached.get(), self.output.get(), self.write.get())

    def rates(self):
        return {key: (None if key == "write" and not self.rate_vars[key].get().strip() else number(self.rate_vars[key].get(), "单价")) for key in RATE_KEYS}

    def recalculate(self, *_args):
        if not self.ready:
            return
        self.last_result = ""
        for panel in (self.api_result, self.sub_result):
            panel.configure(text="请检查输入", fg="#a63b36")
        self.quota_note.set("")
        model = self.selected("models")
        plan = self.selected("plans")
        if self.sample_month != self.month.get():
            self.sample_month = None
        self.model_note.set(f"价格核对：{model['checked']}  |  {model['note']}")
        self.plan_note.set(f"价格核对：{plan['checked']}  |  {plan['note']}")
        try:
            counts = self.counts()
            number(self.fx.get(), "换算汇率", positive=True)
        except ValueError as exc:
            self.status.set(str(exc))
            return
        api_text = sub_text = ""
        api_error = sub_error = None
        try:
            rates = self.rates()
            result = calculate(rates, counts)
            usd, cny = convert(result["total"], self.currency.get(), self.fx.get())
            changed = self.currency.get() != model["currency"] or any(
                rates[k] != (None if model["rates"][k] is None else number(model["rates"][k])) for k in RATE_KEYS)
            label = "自定义单价 · 尚未保存" if changed else "所选档位估算"
            api_text = f"{label}\n\nUSD  {money(usd)}\nCNY  {money(cny)}\n\n普通输入  {money(result['input'])}    缓存命中  {money(result['cached'])}\n输出  {money(result['output'])}    缓存写入  {money(result['write'])}\n明细币种：{self.currency.get()}"
            self.api_result.configure(text=api_text, fg="#174381")
        except ValueError as exc:
            api_error = str(exc)
            self.api_result.configure(text=api_error)
        try:
            result = subscription(self.fee.get(), self.month.get(), counts, self.extra.get())
            currency = self.sub_currency.get()
            usd, cny = convert(result["allocated"], currency, self.fx.get())
            basis = "历史样本，可能已过时" if self.sample_month else "使用假设"
            sub_text = f"本次分摊成本（{basis}）\n\nUSD  {money(usd)}    /    CNY  {money(cny)}\n\n预计整月支出  {money(result['monthly'])} {currency}\n每百万平均成本  {money(result['per_million'])} {currency}\n月用量：{self.month.get()}（输入 + 输出）"
            self.sub_result.configure(text=sub_text, fg="#174381")
            credit_cost = credits(plan, counts, self.off_peak.get())
            if credit_cost is not None:
                weekly, window = number(plan["weekly"]), number(plan["window"])
                quota = f"本次约 {money(credit_cost)} 积分，占周额度 {money(credit_cost / weekly * 100)}%。每周 {money(weekly)} / 5 小时 {money(window)} 积分。"
                if credit_cost > weekly:
                    quota += " 本次超过整周额度，不能视为套餐内可完成。"
                elif credit_cost > window:
                    quota += " 本次超过 5 小时额度，需跨刷新窗口安排。"
                quota += " 月用量折算采用周额度 × 30/7；仅为均匀使用估计，不是月度额度。"
                self.quota_note.set(quota)
            else:
                self.quota_note.set(("历史样本：" + plan["sample"]["note"] if self.sample_month else "没有可靠固定 token 配额。可试填不同月用量比较摊销；是否够用、额外扣款以账户额度与账单为准。"))
        except ValueError as exc:
            sub_error = str(exc)
            self.sub_result.configure(text=sub_error)
        active_api = self.tabs.index(self.tabs.select()) == 0
        error = api_error if active_api else sub_error
        self.status.set(error or "已按当前输入计算 · 改动立即生效")
        if not error:
            name = model["name"] if active_api else plan["name"]
            self.last_result = f"Token计价器 | {name}\n总输入 {self.total.get()} / 缓存命中 {self.cached.get()} / 输出 {self.output.get()} / 缓存写入 {self.write.get()}\n" + (api_text if active_api else sub_text + "\n" + self.quota_note.get()) + f"\n换算汇率：1 USD = {self.fx.get()} CNY（手动值）\n" + (self.model_note.get() if active_api else self.plan_note.get())

    def use_capacity(self):
        try:
            counts = self.counts()
            plan = self.selected("plans")
            cost = credits(plan, counts, self.off_peak.get())
            if not cost:
                raise ValueError("请先输入非零 token 数，并选择 GLM 积分套餐")
            capacity = int(number(plan["weekly"]) * Decimal(30) / 7 / cost * sum(counts.values()))
            self.month.set(str(capacity))
        except ValueError as exc:
            messagebox.showerror("无法估算月用量", str(exc), parent=self)

    def find_cheapest(self):
        try:
            winners, compared, skipped = cheapest_models(self.catalog["models"], self.counts(), self.fx.get())
        except ValueError as exc:
            messagebox.showerror("无法比较价格", str(exc), parent=self)
            return
        model, usd, cny = winners[0]
        self.tabs.select(0)
        self.model.set(model["name"])
        self.select_model()
        self.scroll_canvas.yview_moveto(0)
        names = "\n".join(item[0]["name"] for item in winners)
        messagebox.showinfo("当前用量的最低 API 费用",
                            f"{names}\n\nUSD {money(usd)} / CNY {money(cny)}\n"
                            f"已比较 {compared} 个已保存档位；跳过 {skipped} 个缺少缓存写入单价的档位。\n"
                            + (f"共 {len(winners)} 个并列最低，已定位第一个。\n" if len(winners) > 1 else "已自动选中该档位。\n")
                            + "按价格表和当前汇率比较，临时修改的单价需先另存模型。\n"
                            "请核对所选档位的地区、时段、上下文和优惠条件；订阅摊销不参与 API 比价。",
                            parent=self)

    def use_sample(self):
        sample = self.selected("plans").get("sample")
        if sample:
            self.month.set(str(sample["monthly_tokens"]))
            self.sample_month = self.month.get()
            self.recalculate()

    def open_sample(self):
        sample = self.selected("plans").get("sample")
        if sample:
            webbrowser.open(sample["source"])

    def commit_catalog(self, data):
        # Persist first: a failed write must not change the active catalog.
        save_catalog(self.user_file, data)
        self.catalog = data
        self.refresh_lists()
        self.status.set("价格已保存，下次打开自动加载")

    def save_model(self):
        try:
            rates = self.rates()
            name = simpledialog.askstring("自定义模型", "模型名称（会新增，不覆盖现有模型）：", parent=self)
            if name is None:
                return
            if not name.strip():
                raise ValueError("请输入模型名称")
            data = copy.deepcopy(self.catalog)
            import uuid
            data["models"].append({"id": "custom-" + uuid.uuid4().hex, "name": name.strip(), "currency": self.currency.get(),
                                   "rates": {k: None if v is None else str(v) for k, v in rates.items()},
                                   "source": "", "checked": date.today().isoformat(), "note": "用户自定义价格，请确认适用范围。"})
            self.commit_catalog(data)
            self.model.set(name.strip())
            self.select_model()
        except (OSError, ValueError) as exc:
            messagebox.showerror("保存失败", str(exc), parent=self)

    def import_catalog(self):
        path = filedialog.askopenfilename(parent=self, title="导入价格 JSON（也接受内容为 JSON 的 txt）", filetypes=[("价格文本", "*.json *.txt"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            data = read_catalog(path)
            if messagebox.askyesno("替换价格表", "导入会替换当前模型和套餐列表。需要保留时请先导出。继续导入？", parent=self):
                self.commit_catalog(data)
        except (OSError, ValueError) as exc:
            messagebox.showerror("导入失败，原价格表未改动", str(exc), parent=self)

    def export_catalog(self):
        path = filedialog.asksaveasfilename(parent=self, initialfile="prices.json", defaultextension=".json", filetypes=[("JSON 文本", "*.json"), ("文本", "*.txt")])
        if path:
            try:
                save_catalog(path, self.catalog)
                self.status.set("价格表已导出（临时编辑的单价请先另存模型）")
            except (OSError, ValueError) as exc:
                messagebox.showerror("导出失败", str(exc), parent=self)

    def edit_catalog(self):
        dialog = tk.Toplevel(self)
        dialog.title("编辑价格 JSON · 模型与订阅")
        dialog.geometry("850x650")
        ttk.Label(dialog, text="编辑后点保存；无效内容不会覆盖现有价格。单价单位：每百万 token。", padding=12).pack(anchor="w")
        frame = ttk.Frame(dialog)
        frame.pack(fill="both", expand=True, padx=12)
        text = tk.Text(frame, wrap="none", undo=True, font=("Consolas", 11))
        scroll = ttk.Scrollbar(frame, command=text.yview)
        scroll.pack(side="right", fill="y")
        text.configure(yscrollcommand=scroll.set)
        text.pack(fill="both", expand=True)
        text.insert("1.0", json.dumps(self.catalog, ensure_ascii=False, indent=2))

        def save():
            try:
                self.commit_catalog(parse_catalog(text.get("1.0", "end-1c")))
                dialog.destroy()
            except (ValueError, OSError) as exc:
                messagebox.showerror("未保存", str(exc), parent=dialog)

        ttk.Button(dialog, text="校验并保存", command=save).pack(anchor="e", padx=12, pady=12)
        dialog.transient(self)
        dialog.grab_set()

    def restore(self):
        if messagebox.askyesno("恢复内置价格", "这会替换自定义价格。需要保留时请先导出。是否继续？", parent=self):
            try:
                self.commit_catalog(read_catalog(BUILTIN))
            except (ValueError, OSError) as exc:
                messagebox.showerror("恢复失败", str(exc), parent=self)

    def open_source(self, group):
        source = self.selected(group)["source"]
        if source:
            webbrowser.open(source)
        else:
            messagebox.showinfo("自定义价格", "这条价格没有填写来源网址。", parent=self)

    def copy_result(self):
        if not self.last_result:
            self.status.set("请先修正输入，再复制结果")
            return
        self.clipboard_clear()
        self.clipboard_append(self.last_result)
        self.status.set("结果已复制")


def main():
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    App().mainloop()


if __name__ == "__main__":
    main()
