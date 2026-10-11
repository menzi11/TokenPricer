# 自定义价格文件

可以用记事本打开 JSON，保存为 UTF-8。扩展名 `.json` 或 `.txt` 均可。建议先从 GUI **导出**，修改后再**导入**；也可以直接用 GUI 的“编辑价格 JSON”。导入替换整张表，不做隐式合并。

应用保存的配置位于 Windows `%LOCALAPPDATA%\TokenPricer\prices.json`。源码或 EXE 自带内置价格，用户文件不存在时使用内置表；损坏时提示并回退，保留损坏文件。编辑外部文件后重启应用或重新导入即可，没有后台文件监控。

单价统一为**每 1,000,000 token**，支持 USD/CNY。数字推荐写成字符串，避免编辑工具更改精度。`write: null` 表示未配置缓存写入，**不是免费**。若填写 `"0"` 则是明确的免费单价。

下面是最小完整示例，文件也可以包含更多模型和套餐：

```json
{
  "version": 1,
  "models": [
    {
      "id": "my-model",
      "name": "我的模型",
      "currency": "CNY",
      "rates": {"input": "2", "cached": "0.2", "output": "8", "write": null},
      "source": "",
      "checked": "2026-10-11",
      "note": "自定义单价，每百万 token。"
    }
  ],
  "plans": [
    {
      "id": "my-plan",
      "name": "我的订阅",
      "monthly": "99",
      "currency": "CNY",
      "source": "",
      "checked": "2026-10-11",
      "note": "按账单填写的月费；月 token 由使用者估计。"
    }
  ]
}
```

`id` 和 `name` 在各自列表中必须唯一。`source` 可以为空，非空时必须是 HTTPS 链接。日期使用 `YYYY-MM-DD`。文件拒绝重复 JSON 字段、未知字段、负价、非有限数字和超大文件；大小上限 2 MB，每组最多 500 条。

订阅可附加 `sample`：包含 `monthly_tokens`、`source`、`note`，用于明确标注的历史网上估计。`note` 必须说明日期和局限。不要把社区样本写成保证额度。

GLM 类型订阅还可以使用 `weekly`、`window`、`weights`；分别表示每周积分、5 小时积分、输入/缓存/输出倍率。三者一起提供时计算：

```text
积分 = (普通输入 × input + 缓存命中 × cached + 输出 × output) / 10,000
低谷积分 = 高峰积分 × 0.5
```

这组字段用于当前 GLM 规则，不能套给使用其他分母或不同峰谷折扣的厂商。临时修改 API 单价后，点“另存自定义模型”才会持久保存；订阅月费的临时修改，要通过 JSON 编辑器写回套餐才能持久保存。
