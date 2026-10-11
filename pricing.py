"""Decimal-based cost calculations and validated, portable price catalogs."""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

MILLION = Decimal(1_000_000)
RATE_KEYS = ("input", "cached", "output", "write")


def number(value, label="数值", *, positive=False) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{label}必须是数字")
    try:
        text = str(value).strip()
        if len(text) > 40:
            raise ValueError(f"{label}过长")
        result = Decimal(text)
    except (InvalidOperation, TypeError):
        raise ValueError(f"{label}必须是数字") from None
    if not result.is_finite() or result < 0 or result > Decimal("1e15"):
        raise ValueError(f"{label}必须在 0 到 10^15 之间")
    if positive and result == 0:
        raise ValueError(f"{label}必须大于 0")
    if result != 0 and result.as_tuple().exponent < -12:
        raise ValueError(f"{label}最多支持 12 位小数")
    return result


def tokens(value, label="Token 数") -> int:
    text = str(value).strip().lower().replace("，", ",")
    # Accept properly grouped numbers, k/m and Chinese 万/亿; never silently truncate.
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?|[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?)([km万亿]?)", text)
    if not match:
        raise ValueError(f"{label}请填非负整数，可用 1,000、10k、1m、1万")
    multiplier = {"": 1, "k": 1000, "m": 1000000, "万": 10000, "亿": 100000000}[match[2]]
    result = number(match[1].replace(",", ""), label) * multiplier
    if result != result.to_integral_value() or result > 10**15:
        raise ValueError(f"{label}必须是 0 到 10^15 之间的整数")
    return int(result)


def usage(total, cached, output, write=0):
    values = [tokens(v, label) for v, label in zip(
        (total, cached, output, write), ("总输入", "缓存命中", "输出", "缓存写入"))]
    total, cached, output, write = values
    if cached + write > total:
        raise ValueError("缓存命中 + 缓存写入不能超过总输入 token")
    return {"input": total - cached - write, "cached": cached, "output": output, "write": write}


def calculate(rates, counts):
    result = {}
    with localcontext() as ctx:
        ctx.prec = 60
        for key in RATE_KEYS:
            rate = rates.get(key)
            if rate is None and counts[key]:
                raise ValueError("当前档位没有缓存写入单价，请选择支持的档位或自定义单价")
            result[key] = Decimal(counts[key]) * number(rate or 0, "单价") / MILLION
        result["total"] = sum(result.values(), Decimal(0))
    return result


def convert(amount, currency, usd_cny):
    fx = number(usd_cny, "美元兑人民币汇率", positive=True)
    with localcontext() as ctx:
        ctx.prec = 60
        if currency == "USD":
            return amount, amount * fx
        if currency == "CNY":
            return amount / fx, amount
    raise ValueError("币种只能是 USD 或 CNY")


def subscription(monthly_fee, monthly_tokens, counts, extra=0):
    fee = number(monthly_fee, "月费")
    extra = number(extra, "每月额外费用")
    monthly = tokens(monthly_tokens, "预计每月实际 token")
    if not monthly:
        raise ValueError("预计每月实际 token 必须大于 0")
    target = sum(counts.values())
    if target > monthly:
        raise ValueError("本次 token 超过预计整月用量，请提高预计月用量")
    with localcontext() as ctx:
        ctx.prec = 60
        budget = fee + extra
        return {"monthly": budget, "per_million": budget * MILLION / monthly,
                "allocated": budget * target / monthly}


def credits(plan, counts, off_peak=False):
    if counts["write"]:
        raise ValueError("GLM 积分估算请将缓存写入计入普通输入，缓存写入栏填 0")
    weights = plan.get("weights")
    if weights is None:
        return None
    with localcontext() as ctx:
        ctx.prec = 60
        cost = sum(Decimal(counts[k]) * number(weights[k]) for k in ("input", "cached", "output")) / 10000
        return cost * (Decimal("0.5") if off_peak else 1)


def _unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError(f"JSON 存在重复字段：{k}")
        result[k] = v
    return result


def validate_catalog(data):
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("价格文件必须是 version 为 1 的 JSON 对象")
    if set(data) - {"version", "models", "plans"}:
        raise ValueError("价格文件包含未知顶层字段")
    for group in ("models", "plans"):
        rows = data.get(group)
        if not isinstance(rows, list) or not rows or len(rows) > 500:
            raise ValueError(f"{group} 必须包含 1 到 500 条记录")
        ids = set()
        names = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"{group} 的记录必须是对象")
            required = {"id", "name", "currency", "source", "checked", "note"}
            allowed = required | ({"rates"} if group == "models" else {"monthly", "weekly", "window", "weights", "sample"})
            if set(row) - allowed:
                raise ValueError(f"{group} 包含未知字段：{set(row) - allowed}")
            for key in required:
                if not isinstance(row.get(key), str) or (key != "source" and not row[key].strip()) or len(row[key]) > 2000:
                    raise ValueError(f"{group}.{key} 必须是有效文本")
            if row["id"] in ids or row["name"] in names:
                raise ValueError(f"{group} 中 id 或 name 重复")
            ids.add(row["id"])
            names.add(row["name"])
            if row["currency"] not in ("USD", "CNY"):
                raise ValueError("币种只能是 USD 或 CNY")
            date.fromisoformat(row["checked"])
            if row["source"] and not row["source"].startswith("https://"):
                raise ValueError("来源网址必须使用 https://，自定义价格可留空")
            if group == "models":
                rates = row.get("rates")
                if not isinstance(rates, dict) or set(rates) != set(RATE_KEYS):
                    raise ValueError("rates 必须包含 input、cached、output、write")
                for key, value in rates.items():
                    if key == "write" and value is None:
                        continue
                    number(value, f"{row['name']} 的 {key} 单价")
            else:
                number(row.get("monthly"), "月费")
                if "sample" in row:
                    sample = row["sample"]
                    if not isinstance(sample, dict) or set(sample) != {"monthly_tokens", "source", "note"}:
                        raise ValueError("sample 必须包含 monthly_tokens、source、note")
                    if not tokens(sample["monthly_tokens"]):
                        raise ValueError("历史样本用量必须大于 0")
                    if not isinstance(sample["source"], str) or not sample["source"].startswith("https://"):
                        raise ValueError("历史样本来源必须是 https:// 网址")
                    if not isinstance(sample["note"], str) or not sample["note"].strip() or len(sample["note"]) > 2000:
                        raise ValueError("历史样本必须说明日期与适用范围")
                if "weights" in row:
                    if not isinstance(row["weights"], dict) or set(row["weights"]) != {"input", "cached", "output"}:
                        raise ValueError("weights 必须包含 input、cached、output")
                    for value in row["weights"].values():
                        number(value, "积分倍率", positive=True)
                    number(row.get("weekly"), "每周积分", positive=True)
                    number(row.get("window"), "5 小时积分", positive=True)
                elif "weekly" in row or "window" in row:
                    raise ValueError("周额度与 5 小时额度必须与 weights 一起填写")
    return data


def parse_catalog(text):
    if len(text.encode("utf-8")) > 2_000_000:
        raise ValueError("价格文件不能超过 2 MB")
    try:
        data = json.loads(text.lstrip("\ufeff"), object_pairs_hook=_unique,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"无效数字：{value}")))
        return validate_catalog(data)
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError(f"价格文件格式不正确：{exc}") from None


def read_catalog(path):
    path = Path(path)
    if path.stat().st_size > 2_000_000:
        raise ValueError("价格文件不能超过 2 MB")
    return parse_catalog(path.read_text(encoding="utf-8-sig"))


def save_catalog(path, data):
    validate_catalog(data)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".prices-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def money(value):
    if value == 0:
        return "0.00"
    if abs(value) < Decimal("0.000001"):
        return format(value, ".3E")
    return format(value, ",.6f").rstrip("0").rstrip(".")
