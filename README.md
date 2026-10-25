# cn.sinobest.gaywtb —「公安一网通办」iOS App 安全调查

独立静态安全调查 · 报告自包含 · 全部主张可独立复算 · **含可运行代码**

---

## 调查对象身份（引用前请先核对指纹）

| 项 | 值 |
|---|---|
| 官方名称 | 公安一网通办 |
| Bundle ID / 版本 | `cn.sinobest.gaywtb` / **1.2.28** |
| App Store | trackId `1597440048`，seller **公安部科技信息化局** |
| 签名主体 | `TeamIdentifier=JWX2DN7S4Z` |
| **IPA SHA-256** | `d46aaec36700a85b5d1a14834d46e645e145149c8416d94aa294b5975f84f3ad` |
| 架构 | Cordova 混合（native 主二进制 4,659,328 B + `www/` 310 个 H5 资源） |

> **样本口径**：解密 dump 重打包 IPA（`cryptid=0`、无 `embedded.mobileprovision`）。
> 本 repo **不主张**任何关于 Apple FairPlay 加密或 App Store 分发链路的内容，
> 只对上表 SHA-256 负责，**不自动适用于其他版本**。

---

## 怎么读这个 repo

**只想了解发生了什么** → 读 [主报告](reports/2026-10-crypto-and-transport/report.zh.md)（综述 + 索引，一篇看完）。

**想深入某一点** → 沿主报告的链接进 `analysis/` 的专题文档。

**想亲手验证** → 跑 `code/` 里的脚本；主报告 §9 有全部复现命令。

**想知道我们的结论有多可信** → 读 [方法论与自我推翻记录](reports/2026-10-crypto-and-transport/analysis/02-方法论与自我推翻记录.md)（我们推翻了自己 5 次）。

---

## 核心结论速览

| # | 主张 | 证据强度 |
|---|---|---|
| A1 | 一把 **AES-256 密钥明文硬编码在 H5 层**，用于加密**登录密码、手机号、验证码**，模式 **ECB**（无 IV） | 代码级（纯文本 JS，逐行可读） |
| A2 | 同一把密钥服务**三个业务入口**：登录（加密 password）、重置密码、修改密码（各加密三字段） | 代码级（逐 effect 核对） |
| A3 | **全局关闭 ATS**（`NSAllowsArbitraryLoads=true`，无任何更窄的键）⇒ 允许明文 HTTP，**并移除 TLS 1.2 下限、前向保密要求、证书强度检查** | 配置级 + Apple 官方文档 |
| A4 | 包内含云从 SDK **自述测试密钥**，且被 `checkKey:` **实际取用** | 指令级（xref 经 `__cfstring`，阳性对照 PASS） |
| A5 | ECB 的三种后果（同明文同密文 / 枚举字段可还原 / 结构泄露）在**本 App 的真实密钥与模式**下可复现 | 机制级（可运行演示） |

---

## 目录结构

```
reports/2026-10-crypto-and-transport/
├── report.zh.md                    ← 主报告：综述 + 索引
├── analysis/                       ← 深度专题
│   ├── 01-ATS-深度调查.md           ATS 是什么？关掉它意味着什么？主权抗辩成立吗？
│   ├── 02-方法论与自我推翻记录.md    我们犯了哪些错、怎么发现的、转化成了什么判据
│   └── 03-ECB-工作模式.md           AES-256 有没有问题？为什么密钥长度救不了 ECB
├── code/                           ← 可运行代码
│   ├── ecb_demo.py                 亲眼看到 ECB 的三个后果
│   └── xref_check.py               字符串是否真被代码取用（强制阳性对照）
└── evidence/
    └── ats-research-raw.json       ATS 研究原始记录（含未能核实项）
```

---

## 快速上手

```bash
# 1. 看 ECB 的后果（用本 App 的真实密钥与真实模式）
python3 reports/2026-10-crypto-and-transport/code/ecb_demo.py

# 2. 验证一个字符串是否真被代码取用（带强制阳性对照）
python3 reports/2026-10-crypto-and-transport/code/xref_check.py \
    "<解包后的主二进制>" 'cw_test_aes_key_' --control 'cw_test_sm4_key_'
```

依赖：`ecb_demo.py` 优先用 `cryptography` 库，没有则回退 `openssl` 命令行；
`xref_check.py` 只用 Python 标准库。

---

## 明确不作为缺陷主张的事项（防夸大）

- **「无加固壳」本身不是缺陷**——OWASP MASVS 原文：纵深防御措施缺失
  *"does not in itself constitute a vulnerability"*，混淆 *"aren't considered mandatory"*；
- **明文 HTTP 端点 `36.112.134.71:38888` 不是生产地址**——它是配置中的 `testurl`，
  生产走 `https://ywtb.mps.gov.cn/mobileBack`（`REACT_APP_ENV="prod"` 已证）；
- **`cn.sinobest` 与公安部的关系未认定**；
- **未主张任何「已被攻击/已被利用」的事实**；
- **未主张 ATS 降级曾实际发生**——这是被解锁的**能力**，不是已观测事件。

完整清单见主报告 §6。

**已撤回**：早期草稿曾把二进制中一处 64 字符 Base64 串列为「48 字节密钥材料」。
经反汇编核实它是 **Base64 编码器的查表字母表**，不是密钥。详见主报告 §5.1。

---

## 方法

- 每条主张给出**文件 + 字节偏移 + 期望字节**；
- 所有工具内置**阳性对照**（找不回已知项就退非零、不出结论）；
- **计数型主张先算噪声基线**；本轮记录并排除了 5 类假阳性（业务记录 ID、
  ARM64 指令流误读为 ASCII、ObjC 选择子被当高熵材料、Base64 字母表被当密钥材料、
  第三方 SDK 方法被当本应用加密面）；
- **最强替代假说必须排除**：A1 的「这是 SSL pinning 而非加密」已逐特征排除；
- **本报告在成稿中推翻了自己 5 次**，其中 2 次是主报告级错误，全部记录在案。

---

## 引用

引用请注明所核验样本的 SHA-256 与版本，并区分本报告的主张与被引规范的主张。
详见 [CITATION.cff](CITATION.cff)。

## 许可

报告文本：CC-BY-4.0。详见 [LICENSE](LICENSE)。
