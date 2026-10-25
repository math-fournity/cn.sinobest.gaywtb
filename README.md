# cn.sinobest.gaywtb —「公安一网通办」iOS App 安全调查

独立静态安全调查 · 报告自包含 · 全部主张可独立复算

---

## 调查对象身份（引用本 repo 结论前请先核对指纹）

| 项 | 值 |
|---|---|
| 官方名称 | 公安一网通办 |
| Bundle ID / 版本 | `cn.sinobest.gaywtb` / **1.2.28** |
| App Store | trackId `1597440048`，seller **公安部科技信息化局**（Science and Technology Information Bureau of the Public Security Ministry of China） |
| 签名主体 | team-identifier `JWX2DN7S4Z` |
| **IPA SHA-256** | `d46aaec36700a85b5d1a14834d46e645e145149c8416d94aa294b5975f84f3ad` |
| 架构 | Cordova 混合应用（native 主二进制 4,659,328 B + `www/` 310 个 H5 资源） |

> **样本口径**：解密 dump 重打包 IPA（`cryptid=0`、无 `embedded.mobileprovision`）。
> 本 repo **不主张**任何关于 Apple FairPlay 加密或 App Store 分发链路的内容，
> 只对上表 SHA-256 的样本负责，**结论不自动适用于其他版本**。

## 报告

| 目录 | 内容 |
|---|---|
| [`reports/2026-10-crypto-and-transport/`](reports/2026-10-crypto-and-transport/report.zh.md) | **2026-10：密码学使用与传输安全调查报告**（中文）——五项主张、逐条文件+字节偏移、规范原文引用、明确不主张清单、公开工具复现指南 |

## 核心结论速览

| # | 主张 | 证据强度 |
|---|---|---|
| A1 | 登录与改密的**手机号、验证码、密码**三字段用**硬编码 AES-256 密钥**加密上传，工作模式 **ECB**（无 IV） | 代码级（纯文本 JS，逐行可读） |
| A2 | 同一把密钥用于**两条独立业务链**：登录 `/api/fwmh/mobile/login` 与改密 `/api/user/password` | 代码级（两条链各自的调用点与端点） |
| A3 | 应用**全局关闭 ATS**（`NSAllowsArbitraryLoads=true`），无域名例外白名单 | 配置级（Info.plist 直读） |
| A4 | 包内含云从 SDK **自述测试密钥** `cw_test_aes_key_` / `cw_test_sm4_key_` | 字符串级（偏移可读） |
| A5 | 包内含 **48 字节 Base64 密钥材料**（熵 5.543 bit/B），位于活体检测消息生成代码邻域 | 材料级（值+位置+邻域）；**用途未证** |

**明确不作为缺陷主张的事项**（防夸大）：无加固壳本身不是缺陷（OWASP MASVS 明文
「缺失不构成漏洞」）；明文 HTTP 端点 `36.112.134.71:38888` 是配置中的 `testurl`
而非生产地址；48 字节材料「加密什么」未证；`cn.sinobest` 与公安部的关系未认定。
完整清单见报告 §6。

## 复现

仅依赖公开工具（`unzip` / `grep` / `plutil` / `python3` 标准库），逐步命令见
[报告 §9](reports/2026-10-crypto-and-transport/report.zh.md#9-复现指南仅用公开工具)。
**先核对 SHA-256**，不符则结论不适用。

## 方法

- 每条主张给出**文件 + 字节偏移 + 期望字节**；
- 密钥普查内置**阳性对照**（找不到已知钥即判通道失明、普查作废），本次 3/3 通过；
- **计数型主张先算噪声基线**；本轮记录并排除了 4 类假阳性（业务记录 ID、
  ARM64 指令流误读为 ASCII、ObjC 选择子被当高熵材料、第三方 SDK 方法被当本应用加密面）；
- **最强替代假说必须排除**：A1 的「这是 SSL pinning 而非加密」已逐特征排除。

## 引用

引用请注明所核验样本的 SHA-256 与版本，并区分本报告的主张与被引规范的主张。
详见 [CITATION.cff](CITATION.cff)。

## 许可

报告文本：CC-BY-4.0。详见 [LICENSE](LICENSE)。
