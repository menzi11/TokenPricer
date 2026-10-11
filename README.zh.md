<div align="center">

# TokenPricer · Token计价器

[English](README.md) | 中文

**输入 token，算出费用；价格可以自己改。**

![Windows](https://img.shields.io/badge/Windows-desktop-2563eb)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776ab)
![License](https://img.shields.io/badge/license-MIT-eab308)

[**下载 Windows 程序**](https://github.com/menzi11/TokenPricer/releases/latest) · [价格来源与估算依据](docs/pricing-sources.md) · [自定义价格格式](docs/configuration.md)

</div>

Token计价器是一个离线中文桌面小程序。输入输入、输出 token 数，可以估算 API 费用，也可以把订阅月费分摊到这次用量。内置 OpenAI、Claude、Gemini、DeepSeek、Kimi、GLM 和 Cursor 的价格档位。

官方价格页提供单价，本程序把单价、token 数、缓存用量和汇率放在同一个窗口里计算。对于订阅，GLM 官方积分规则与 Kimi、Cursor 社区历史估算分开展示；每条预设都有来源和核对日期，方便检查数字依据。

![API 计价界面](docs/api.png)

## 计算 API 费用

填写用量后点击 **定位最便宜模型**，按当前汇率比较已保存的 API 价格档位，自动选中最低价；并列时列出全部结果。缺少所需缓存写入价格的档位会跳过。请核对地区、时段、上下文与优惠条件；临时单价需先另存模型，订阅摊销不参与此比较。

普通输入、缓存命中、缓存写入、输出分别计价，使用十进制运算。缓存命中和写入是总输入的子集，不重复相加。长短上下文、峰谷时段需要选择对应价格档；输出应包含实际计费的推理 token。

## 估算订阅成本

显示预计整月支出、平均每百万 token 成本、本次用量分摊成本。你可以填写预计月用量，按 GLM 周积分额度推算，或者点击按钮采用网上找到的历史样本。**分摊成本不等于追加扣款，也不证明套餐额度足够。**

![采用历史样本的订阅估算](docs/subscription.png)

## 自定义价格

在界面修改单价后，另存为自己的模型；内置 JSON 编辑器也能修改订阅月费和假设。导入、导出支持 UTF-8 `.json`，或者内容为 JSON 的 `.txt`。无效文件不会覆盖当前价格表，保存成功后下次启动自动加载。

## 美元、人民币同时看

预设保留厂商原始标价币种，结果按手动汇率显示 USD 和 CNY。默认的 **1 美元 = 7 元是演示值，不是实时汇率**。国内、国际 API 价格分别列出，不把它们混成一套单价。

## 查看数字依据

初始价格快照核对日期为 **2026-10-11**，程序不会自动联网更新。单价、优惠期、订阅规则和社区估计都可能变化。GLM 国际 Pro/Max 月费已明确标注为参考值，需要到订阅页复核。订阅估算的具体限制见[来源说明](docs/pricing-sources.md)。

其他便利：支持 `10k`、`1M`、`1B`、`1.5B`、`1万` 等写法，大小写通用（`1B` = 10 亿），所有 token 输入框均支持；修改即计算；复制结果；恢复内置价格；较小窗口和高 DPI 环境可滚动查看。计算不需要 API Key、不连接账户、不发送网络请求；点击来源链接才会打开浏览器。

## 开始使用

在 [Releases](https://github.com/menzi11/TokenPricer/releases/latest) 下载 `TokenPricer.exe`，双击运行即可，无需安装 Python。首版提供 Windows x64 程序，未做代码签名。

源码运行需要 Python 3.11+ 和 Tk：

```powershell
python app.py
```

运行时只使用 Python 标准库；其他操作系统尚未验证。

<details>
<summary>开发与构建</summary>

```powershell
python -m unittest discover -s tests -v
powershell -ExecutionPolicy Bypass -File build.ps1
```

GUI 测试需要桌面/Tk 环境。构建脚本创建本地虚拟环境，安装固定版本 PyInstaller，测试后生成 `dist/TokenPricer.exe`。开发环境安装 Pillow 后，可运行 `tools/capture_preview.py` 重新生成界面截图。

</details>

[MIT 许可证](LICENSE)
