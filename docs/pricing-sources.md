# 价格与订阅估算依据

核对日期：2026-10-11。应用以离线快照计算，不承诺价格自动更新、模型可购买或账户有对应额度。每条预设保留币种、来源、核对日期和说明。

## API 官方资料

| 供应商 | 本程序覆盖 | 来源 |
|---|---|---|
| OpenAI | GPT-6 Astra、GPT-6.1 Sol、GPT-6 Luna，Standard 长/短上下文档 | [API Pricing](https://developers.openai.com/api/docs/pricing) |
| Anthropic | Claude Opus/Sonnet 5.5、Haiku 4.5，全球标准档、5 分钟缓存写入 | [Claude Pricing](https://platform.claude.com/docs/en/about-claude/pricing) |
| Google | Gemini 3.5 Flash-Lite、3.8 Flash，Standard 文本 | [Gemini Pricing](https://ai.google.dev/gemini-api/docs/pricing) |
| DeepSeek | V4.1 Flash、V4 Pro，高峰/低谷 | [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/) |
| Kimi | K3 国内/国际、K2.7 Code 国内 | [国内](https://platform.kimi.com/) · [国际](https://platform.kimi.ai/) · [缓存规则](https://www.kimi.com/academy/best-practices-for-context-caching) |
| 智谱 / Z.ai | GLM-5.3 国内/国际、5.3-Flash 国内 | [国内](https://docs.bigmodel.cn/cn/guide/start/pricing) · [国际](https://docs.z.ai/guides/overview/pricing) |
| Cursor | Grok 4.6、Composer 2.5 的模型用量价格 | [Models & Pricing](https://cursor.com/docs/models-and-pricing) |

单位全部为每百万 token。缓存命中、缓存写入、普通输入互斥并合计为总输入。填写缓存写入时使用对应账单分类，不能同时再计入普通输入。

OpenAI 的长短上下文、DeepSeek 峰谷档由用户明确选择，不根据累计 token 猜测。累计多次请求跨档位时，应分开计算。Claude 1 小时缓存写入可自行修改单价。Gemini 3.8 Flash 2026 年优惠和 2027 年常规价分成两个预设，按实际使用日期选择。

不包含税费、缓存存储时间、服务器工具调用、地区加价、Batch/Fast 折扣/加价、音视频生成或其他非文本费用。第三方平台转售与直连厂商的价格可能不同。Cursor API 页的金额是模型用量标价，不是订阅追加扣款。

## 订阅：实际月支出与每次摊销

```text
预计月支出 = 订阅月费 + 手动估计的额外费用
平均每百万成本 = 预计月支出 / 预计实际月 token × 1,000,000
本次分摊成本 = 预计月支出 × 本次 token / 预计实际月 token
```

月 token 含输入、输出及缓存（缓存只算一次）。这是费用分摊模型，不预测额外扣款，不把订阅当成无限额度。缓存比例和输入输出比例差别很大时，平均摊销不能作为不同任务的精确资源成本比较。

### GLM Coding Plan（Z.ai 国际版）

[官方积分规则](https://docs.z.ai/devpack/overview)：Lite/Pro/Max 每周分别 10,000/60,000/140,000 积分，5 小时分别 2,000/12,000/28,000。GLM-5.3 的普通输入、缓存、输出倍率分别为 6.9、1.7、24，除以 10,000 得积分；工作日北京时间 14–18 时为高峰，其余时段模型积分减半。

应用根据你输入的组成计算积分。点击“按 GLM 周额度估算月 token”时，按当前组成推算 `周额度 × 30/7` 的均匀使用量。这个值不是真实的月度额度，周额度不结转，5 小时限制独立存在，MCP 调用也会消耗积分但未计入此计算。

Lite 起价 18 美元/月来自官方文档。Pro 80、Max 168 美元/月为[2026 年 9 月公开价格记录](https://yatofix.com/articles/news/glm-coding-plan-credits-18-80-168-septembre-2026)的参考值，本次未能从动态购买页重新核实，**明确标记为月费参考**，允许按实际订单修改。这里没有把国际版套餐冒充国内人民币套餐。

### Kimi

[官方帮助中心](https://www.kimi.com/en/help/membership/membership-pricing)列出人民币月费 49、99、199、699 元。会员和 API 独立计费；功能共享额度，Kimi Code 另有限额。没有据此编造固定 token 配额。

“使用网上历史估算”仅在 Allegretto 档提供一个可选样本：[2026-07-17 原始社区帖子](https://locdd.com/t/topic/71380)。作者从进度反推约 950M/月，作者自己也不确定；这不是完整月账单实测，也不是官方承诺。当前配额可能已经改变，默认不会自动套用该样本。

### Cursor

[当前官方文档](https://cursor.com/docs/models-and-pricing)列出 Pro/Pro+/Ultra 为 20/60/200 美元月费，有 Cursor Models 和 Other Models 两个独立池。本程序不沿用旧文档中的固定美元额度作为现行保证。

可选历史样本来自[用户自己发布的三档账户记录](https://www.reddit.com/r/cursor/comments/1wjzc8n/pro_20_vs_pro_60_vs_ultra_200_real_included_usage/)：

| 档位 | 记录周期（2026） | Cursor Models | Other Models | 应用采用的两池合计 |
|---|---|---:|---:|---:|
| Pro | 06-27 至 07-27 | 130.4M | 159.8M | 290.2M |
| Pro+ | 07-13 至 08-13 | 1,100M | 465.1M | 1,565.1M |
| Ultra | 08-16 至 09-16 | 4,200M | 2,400M | 6,600M |

前两档作者称两池用满；Ultra 分别用了 81.1% 与 99.8%。这些数字是不同月份、模型混用的单用户记录，两池合计只用于相同使用组合下的整月平均摊销，不是单模型额度、倍率对照或官方上限。模型组合与缓存行为改变后，不应直接复用结果。
