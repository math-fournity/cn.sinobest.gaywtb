# cn.sinobest.gaywtb —「公安一网通办」iOS App 安全调查

独立静态安全调查 · 报告自包含 · 全部主张可独立复算 · **含可运行代码**

天道好轮回，壮哥放过谁？

 👉 https://0x10010.com/?Sepolia=0xbe6dd4ba0fcd16ffe06f68014fd175cfa96d231aab055ecd2e5bd596536461a0

---

## 关于密钥：我们报告位置，不报告密钥

**先说清楚我们没做什么**：没有破解任何加固壳（分析的是社区已公开流通的解密 dump）、
没有上传任何 IPA、**没有公布完整密钥**、没有接触任何服务器。

### 报告里的密钥是脱敏的

```
385f33cb…9081ab7
```

保留前 8 位与后 7 位——**足够定位，不足以直接使用**。

### 但复核能力不受影响

任何拿到同版本（1.2.28）解密 IPA 的人，30 秒内可自己取到：

```bash
unzip -q cn.sinobest.gaywtb-1.2.28-Decrypted.ipa -d out/
grep -o '[0-9a-f]\{32\}' \
  "out/Payload/公安一网通办.app/www/p__login__Login.js" | head -1
```

**我们提供的是「怎么找到它」，不是「它就是什么」。前者是审计方法，后者是泄露。**

### 为什么这件事该被说出来：「两年」是怎么算出来的

**这不是估计，是推导。**

**第一段 — 版本两年多没变。** 2026-10-25 实时查 iTunes API：

```
version                   = 1.2.28
currentVersionReleaseDate = 2023-11-20T20:49:23Z
```

`2023-11-20 → 2026-10-25 = 1069 天 ≈ 2.93 年`

**第二段 — 手上的包确实是 1.2.28。** 三重印证：`CFBundleShortVersionString = 1.2.28`、
`CFBundleVersion = 2`、App 内资源时间戳 **2023-11-17**（比发布日早 3 天，
符合「打包→送审→发布」的正常时间差）。

**第三段 — 为什么「版本没变」能推出「密钥暴露了这么久」。**
关键在于**这个密钥硬编码在包里，不是服务端下发的**：

```
密钥写死在 www/p__login__Login.js
  → 每次有人下载 1.2.28，拿到的都是同一个包、同一个密钥
  → 这个状态持续多久 = 这个版本存在多久 = 1069 天
```

**⇒「两年」不是「密钥是两年前生成的」，而是「这个版本两年多没更新，
所以这个明文密钥在这两年多里持续可被任何人取得」。**

**边界**：1.2.28 之前的版本是否同样——**未证**（无更早样本，公开渠道也检索不到）。
本报告所用样本的**获取渠道未留档**，按取证纪律如实标注。

它在该版本上是**早已存在的公开信息**：

- 它就在明文 JavaScript 里（无混淆、无加密）；
- 包在全球分发（美/港/日/新 App Store 均在架）；
- 解密 dump 在第三方站点公开流通，搜索即可得。

**⇒ 如果这把密钥原本被有效保护、需要破壳才能取得，那我们不该公开。
但它不是。它一直躺在明文里。**

> 完整说明：[**08 · 本报告的界限与责任**](reports/2026-10-crypto-and-transport/analysis/08-本报告的界限与责任.md)

---

## 一个讽刺的事实：它在美国区 App Store 也能下载

核实（2026-10-25，iTunes lookup API，`country=us`）：

| 项 | 值 |
|---|---|
| 美区上架 | **是**（`resultCount=1`） |
| 版本 | **1.2.28** —— 与本报告分析的样本**同版** |
| seller | Science and Technology Information Bureau of the Public Security Ministry of China |
| 商店页 | https://apps.apple.com/us/app/id1597440048 |
| 可用设备 | 130 个 |
| 港/日/新 | **同样在架** |

**换句话说**：把用户密码的加密密钥以明文写在包里的这个应用，**不需要切换中国区账号，
在美国区就能直接下载**。任何人——包括在美国的安全研究者、也包括不怀好意的
人——都可以拿到它，然后看它用的是什么密钥、什么模式。

> **必须说清的一个技术限定**（否则会夸大）：美区商店分发的是 **App Store 加密包**
> （`fileSizeBytes` 92.8 MB），受 FairPlay 保护，**不能直接解包看密钥**。
> 本报告分析的样本是解密 dump（61.3 MB，为商店包的 66%，符合 dump 口径）。
> 所以准确的说法是：**获取门槛不是「零」，而是「一次公开的解密工具链」**——
> 这在越狱设备与公开工具链上早已是常规操作。**这仍然远低于「密钥应当保密」的前提。**

---

## 相关调查（同一系列的 Android 篇）

本报告是**双端调查的 iOS 篇**。Android 篇已发布：

👉 **https://github.com/math-fournity/cn.cyberIdentity.certification**

两份报告各自独立自包含，但**指向同一个跨平台发现**：
两家互不相关的厂商（Android 端的人脸 SDK 厂商云从科技、iOS 端的中科江南）
**各自独立地**在加密用户凭据时使用了 **ECB 工作模式**。
详见本报告 [§2.6](reports/2026-10-crypto-and-transport/report.zh.md#26-ecb-到底错在哪a5)
与跨样本分析 [§6 · ECB 跨端普查](reports/2026-10-crypto-and-transport/analysis/06-ECB跨端普查.md)。

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

**只想快速了解发生了什么** → 读主报告的
[**给管理层的摘要（人话版）**](reports/2026-10-crypto-and-transport/report.zh.md#给管理层的摘要人话版)
——条分缕析讲清四个问题，不需要任何技术背景。

**有计算机背景但不是密码学方向** → 主报告从头读；密码学部分（ECB、ATS）
都有机制解释，[03 号文档](reports/2026-10-crypto-and-transport/analysis/03-ECB-工作模式.md)
还有零基础铺垫。

**想质疑我们** → 直接跳到
[**§5b 对预期反驳的回应**](reports/2026-10-crypto-and-transport/report.zh.md#5b-对预期反驳的回应)
——七条最强反驳（含「这是公安系统不该用美国加密」「有 HTTPS 就够了」
「这是死代码」「这是测试用的」）逐条回应。

**想亲手验证** → 跑 `code/` 里的脚本；主报告 §9 有全部复现命令。

**想知道我们的结论有多可信** → 读
[方法论与自我推翻记录](reports/2026-10-crypto-and-transport/analysis/02-方法论与自我推翻记录.md)
（我们推翻了自己 5 次）。

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

## 作者

**Math Fournity**、**Step-5-Preview**、**GLM-5.3**、**Deepseek-V4.1-Flash**（AI 协作研究）

## 引用

本 repo 提供 [`CITATION.cff`](CITATION.cff)（GitHub 会在仓库首页显示"引用本仓库"按钮，
引用信息以该文件为准）。BibTeX：

```bibtex
@misc{gaywtb-audit-2026,
  author       = {Math Fournity and Step-5-Preview and GLM-5.3 and Deepseek-V4.1-Flash},
  title        = {「公安一网通办」iOS App（cn.sinobest.gaywtb v1.2.28）
                  密码学使用与传输安全调查报告},
  year         = {2026},
  month        = {10},
  howpublished = {\url{https://github.com/math-fournity/cn.sinobest.gaywtb}},
  note         = {静态分析；IPA SHA-256
                  d46aaec36700a85b5d1a14834d46e645e145149c8416d94aa294b5975f84f3ad}
}
```

引用规范要求：注明出处（作者 + URL + 版本日期），并**同时注明所核验的 IPA 指纹**——
本 repo 的结论仅对上述指纹的样本负责。

同时请区分**本报告的主张**与**被引规范的主张**（见报告 §10 引用规范）。

## 许可

报告文本：CC-BY-4.0。详见 [LICENSE](LICENSE)。
