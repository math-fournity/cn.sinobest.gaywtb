# ATS 深度调查：它是什么、关掉它意味着什么、以及「密码主权」这一抗辩

> 配套：主报告 §3 / §3.2 / §3.3。本文件是主报告那三节的完整论证与原始引文。
> 起因：读者提出一个必须认真对待的反驳——**「公安系统自用 App，会不会本来就
> 不想走美国人的这套安全传输？」**
> 本文件不回避这个问题，先把它当成一个**可能成立的正当理由**去检验。

---

## 0. 先纠正一个我自己犯过的错

在深入调查前，本报告曾写过一句话：

> 「ATS 是 Apple 的策略层——关掉它只是**允许明文 HTTP**，不会让应用获得国密能力。」

**「只允许明文 HTTP」这半句是不完整的。** 完整事实是：关掉 ATS 还会
**移除 TLS 1.2 下限、前向保密（PFS）要求、以及证书强度检查**。

这让 A3 的指控**更重**，不是更轻——详见 §3。

**为什么把这个错误写进报告**：它恰好说明了「看起来很有力的简洁论断」有多危险。
如果我只写那一句，读者（尤其是懂 TLS 的人）会立刻发现它不完整，然后
**合理地怀疑整份报告**。

---

## 1. ATS 到底是不是「美国人的私货」？

### 1.1 结论：不是。它是**策略门**，不是密码学实现

ATS（App Transport Security）是 Apple 在 `URLSession` / `CFNetwork` 层实施的一道
**策略检查**：不符合下述最低要求的连接会被拒绝。它**不发明任何密码学**。

### 1.2 ATS 要求的全部内容（Apple 官方文档逐条）

| 要求 | 具体内容 | 是否 Apple 私有 |
|---|---|---|
| 协议版本 | TLS **1.2** 及以上（RFC 5246；TLS 1.3 为 RFC 8446） | ❌ IETF 标准 |
| 对称加密 | **AES-128 或 AES-256** | ❌ FIPS/NIST 标准 |
| 密钥交换 | **ECDHE 前向保密** | ❌ IETF 标准 |
| 叶证书密钥 | **RSA ≥ 2048 位 或 ECC ≥ 256 位** | ❌ 主流最低强度 |
| 签名哈希 | **SHA-256 或更强** | ❌ NIST 标准 |
| 信任锚 | X.509 链到 OS 信任库中的根 | ❌ 标准 PKI |

Apple 官方原文（`Preventing Insecure Network Connections`）：

> "a networking security feature called App Transport Security (ATS) improves privacy
> and data integrity for all apps and app extensions. It does this by requiring that
> network connections made by your app are secure"

Info.plist Key Reference（归档文档）明确点名 RFC：

> "With ATS enabled, HTTP connections must use HTTPS (**RFC 2818**). … ATS employs the
> Transport Layer Security (TLS) protocol version 1.2 (**RFC 5246**)."

### 1.3 ATS 接受的每一个密码套件都是 IANA 注册的 IETF 套件

ATS 白名单共 11 个套件，全部来自 **RFC 5289 / RFC 8422**，例如：

```
TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA384
```

在 IANA TLS 参数注册表（`tls-parameters-4.csv`）中逐个可查，均为
`0xC0,0x2C` 之类的标准分配值。**没有一个是 Apple 自定义的。**

### 1.4 ATS 没有后门、没有密钥托管、没有强制美国 CA

- **没有专有密码算法**：ATS 的完整要求集就是上表那六条，无其他；
- **没有密钥托管/恢复密钥**：ATS 规范中不存在此类机制；
- **不强制美国 CA**：ATS 用的是 **iOS 全局信任库**，该库**已包含中国 CA**——
  例如 `CFCA EV ROOT`（中国金融认证中心）、`GDCA TrustAUTH R5 ROOT`（广东数字证书认证中心），
  见 Apple 官方根证书列表 `support.apple.com/zh-cn/126047`。
- **默认不做证书固定（pinning）**：pinning 是可选的 `NSPinnedDomains` 子键。

> **唯一的真实保留意见（治理层面，非密码学层面）**：Apple 单方面维护信任库，
> 并保留随时收紧 ATS 要求的权利。但这是**每个操作系统厂商都握有的杠杆**，
> 且它不是一条秘密拦截通道。本报告如实记录这一点，不把它说成「没有」，
> 也不把它夸大成「有后门」。

### 1.5 一个诚实的缺口

**ATS 实际运行的 TLS 栈（`Network.framework` / `libnetwork.dylib`）不是开源的。**
Apple 开源的 `apple-oss-distributions/Security` 里确实有 `libsecurity_ssl`
（SecureTransport），但那个 API **已废弃且不支持 TLS 1.3**，不是 ATS 走的路。

⇒ 本报告**不能**主张「ATS 的实现代码可被独立审计」。能主张的是：
**它要求的协议、套件、强度阈值全部是公开标准，且与 Chrome/Firefox/Android
实施的是同一套。**

---

## 2. 关掉 ATS 到底关掉了什么？

### 2.1 关键澄清：`NSAllowsArbitraryLoads=true` **不等于**「关掉 TLS」

Apple 官方原文（同一段里把两半都说了）：

> "Disabling ATS means that unsecured HTTP connections are allowed. **HTTPS
> connections are also allowed, and are still subject to default server trust
> evaluation**."
>
> "**Invalid certificates always result in a hard failure and no connection.**"

⇒ 它是**加法**（多允许了明文），不是**减法**（没有关掉 TLS）。

### 2.2 但它确实移除了三道下限

| 被移除的保护 | 后果 |
|---|---|
| **TLS 1.2 下限** | 可协商 TLS 1.0 / 1.1（iOS 15 起废弃，但仍受支持） |
| **前向保密（PFS）要求** | 可协商非 PFS 的 `RSA_AES`（RSA 密钥传输）套件 |
| **证书强度检查** | SHA-256 / RSA-2048 / ECC-256 的下限不再强制 |

Apple 原文：

> "…extended security checks—like requiring a minimum Transport Layer Security (TLS)
> protocol version—are disabled."

> "By default, ATS limits cipher selection to include only suites that provide forward
> secrecy" —— 具体为 "ECDHE_ECDSA_AES and ECDHE_RSA_AES in either GCM or CBC mode"。
> "If an app disables the forward secrecy requirement…"

### 2.3 但**没有**掉到 SSL 3 / RC4 那么低

有些保护在 ATS **之下**的操作系统栈里，关 ATS 也不会消失：

> "CFNetwork disallows SSL 3, and apps that use WebKit (such as Safari) are prohibited
> from making an SSL 3 connection."
>
> "From iOS 11 … SHA-1 certificates are no longer allowed for TLS connections unless
> trusted by the [user]"

⇒ 准确表述是：**关 ATS 重新打开了 TLS 1.0/1.1 与非 PFS 套件，不是打开 SSLv3/RC4。**

### 2.4 对本样本的适用性：**iOS 10+ 的「静默忽略」陷阱不适用**

这是一个**大多数分析会搞错**的点。Apple 文档：

> "In iOS 10 and later and macOS 10.12 and later, the value of the
> `NSAllowsArbitraryLoads` key is **ignored**—and the default value of `NO` used
> instead—if any of the following keys are present in your app's Information Property
> List: `NSAllowsArbitraryLoadsForMedia`, `NSAllowsArbitraryLoadsInWebContent`,
> `NSAllowsLocalNetworking`."

**即：如果 App 同时写了那些更窄的键，`NSAllowsArbitraryLoads` 会被系统忽略，
ATS 实际上是开着的。** 很多报告在这里出错。

**本样本实测**（`plutil -p Info.plist`）：`NSAppTransportSecurity` 字典下
**只有** `NSAllowsArbitraryLoads` 一个键，没有 `NSExceptionDomains`、
没有 `NSAllowsArbitraryLoadsInWebContent`、没有 `NSAllowsLocalNetworking`、
没有 `NSPinnedDomains`。`MinimumOSVersion=11.0`。

⇒ **忽略陷阱不适用，该键完全生效**，且对其 Cordova/WKWebView 层同样生效。

### 2.5 证书校验**没有**被关掉

> "HTTPS connections are also allowed, and are still subject to default server trust
> evaluation." / "Invalid certificates always result in a hard failure."

准确说法：关 ATS **移除的是护栏，不是校验**。App 从此**可以**在代码里自行放宽
信任（手动 server-trust 认证）而不被 ATS 阻止，但校验本身不会因为这个键而关闭。

### 2.6 与证书固定（pinning）的关系

- 声明式 pinning（`NSPinnedDomains`）**本身是 ATS 的子键**；
- 代码级 pinning（`URLSessionDelegate` 里做）**与 ATS 无关**，ATS 关着也能用。
- **本样本两种 pinning 都没有**（主二进制内无 pinning 相关实现）。

---

## 3. 修正后的 A3 指控（比原版更重）

原报告写「ATS 全局关闭 ⇒ 允许明文 HTTP」。**修正为**：

> `NSAllowsArbitraryLoads=true` 且无任何更窄的键 ⇒
> ① 允许明文 HTTP；
> ② **移除 TLS 1.2 下限** ⇒ 可协商 TLS 1.0/1.1；
> ③ **移除前向保密要求** ⇒ 可协商非 PFS 套件（一旦长期密钥泄露，历史流量可被解密）；
> ④ **移除证书强度检查** ⇒ 可接受更弱的证书。
> 证书校验仍在（无效证书仍是硬失败），但**护栏已被移除**。

**对本 App 的实际意义**：结合 §2 的密钥公开与 ECB 模式，即使生产流量走 HTTPS
（主报告 §3.2 已证），攻击者仍可能把连接**降级**到 TLS 1.0 或非 PFS 套件——
**而这不需要伪造证书**。

> **诚实边界**：这是**能力**，不是**已观测事件**。静态分析证明「可以降级」，
> 未证明「实际发生过降级」。运行期观测属 0e 动态窗口，本报告不做。

---

## 4. 「密码主权」抗辩：逐条检验

### 4.1 这个怀疑**不是无稽之谈**——中国法规确实推动国密

必须承认这一点，否则就是不诚实：

- **《中华人民共和国密码法》第二十七条**：关键信息基础设施应当使用商用密码进行保护；
- **《商用密码管理条例》**：对商用密码的应用与管理提出要求；
- **GB/T 38636-2020**：定义 TLCP（Transport Layer Cryptographic Protocol，国密 TLS）；
- **GB/T 39786-2021**：信息系统密码应用基本要求（密评基线）。

⇒ **「关键信息基础设施应当用国密」在原则上是有法规支撑的。** 用户的直觉有合理内核。

### 4.2 但 ATS 关闭**无法实现**这个目标

这是决定性的技术事实：

> **ATS 位于密码层之上，且它根本不适用于 TLCP 协议栈所使用的底层 API。**

具体说：
1. 若要用国密 TLS，App 必须**自行捆绑** GmSSL / 铜锁（Tongsuo）之类的协议栈；
2. 该协议栈走的是**底层 socket / BoringSSL 接口**，**不经过** ATS 管辖的
   `URLSession` / `CFNetwork` 路径；
3. 因此：**开 ATS 不会阻止国密，关 ATS 也不会启用国密。**
4. Apple 的 `CryptoKit` / `Security` 框架**不提供任何 SM2/SM3/SM4 原语**。

⇒ **关闭 ATS 换来的唯一能力，就是「可以发明文 HTTP」。** 它与密码主权无关。

### 4.3 三条独立事实，否掉本样本的「主权抗辩」

| # | 若主权抗辩成立，应见 | 本样本实测 | 判定 |
|---|---|---|---|
| 1 | 改用国密 TLS | 主二进制 `SM2`/`SM3`/`SM4`/`GMTLS`/`gmssl`/`TLCP`/`GB-T 38636` **全零命中**；H5 层 5 个文件的 `SM2`/`SM3` 命中经上下文核对**全是 Base64 数据流里的随机子串** | ❌ |
| 2 | 不信任境外 PKI | 生产域名证书链：`ywtb.mps.gov.cn` ← TrustAsia（中国）← **Certum（C=PL，波兰，EU）** | ❌ 仍锚境外根 |
| 3 | 至少不对自有服务器留明文通道 | 同一台 `36.112.134.71` 同时保留 `https://` 与 `http://…:38888` | ❌ 自相矛盾 |

### 4.4 舰队实测：ATS 关闭与国密**完全解耦**（决定性反证）

单看一个 App 无法判断「关 ATS 是不是为了国密」。所以我们做了**对照实验**——
在本 repo 的 50 个 iOS 样本上直接读 `Info.plist` 与二进制。

#### 4.4.1 ATS 全局关闭是市场常态，不是异常

| 范围 | ATS 全局关闭 |
|---|---|
| 全部 50 个样本 | **38 / 50（76%）** |
| 其中政府/官媒类 | **14 / 15** |

⇒ 若「关 ATS = 表达主权立场」，那 76% 的样本（含 Chrome、Bitdefender、
Kaspersky、Twitter 这些**非中国** App）都在表达同一个立场——显然不成立。

#### 4.4.2 关键对照：ATS 与国密**没有相关性**

| App | ATS 状态 | 是否含国密 TLS |
|---|---|---|
| **国家网络身份认证**（NIA） | **全开**（`NSAppTransportSecurity` 为空） | **有**（`sm2_`） |
| **农业银行** | **全局关闭** | **有**（`SM4_GCM`、`sm2_`） |
| **本报告对象（公安一网通办）** | **全局关闭** | **无** |

**这张表是决定性的**：

- 国密用得最彻底的 NIA，**ATS 是全开的**——说明「要国密」完全不需要关 ATS；
- 农行**既有国密又关了 ATS**——说明两者可以并存但无因果关系；
- 本 App **关了 ATS 却没有国密**——说明关 ATS 并未换来任何国密能力。

⇒ **ATS 开关与国密采用是两个正交的维度。** 「关 ATS 是为了走国密」在
机制上不成立，在实测上也不成立。

#### 4.4.3 一个平淡但更可能的解释

`NSExceptionDomains`（按域名开例外）**只接受域名，不接受裸 IP**。
而本 App 的配置里恰好有一个裸 IP 端点 `http://36.112.134.71:38888`。
要让它可用，开发者**只能**退回到全局开关 `NSAllowsArbitraryLoads`。

⇒ **这解释了「为什么会用全局开关而不是窄例外」**，但它**不解释「为什么需要那个
明文端点」**——尤其当生产流量实际全走 HTTPS 时（§3.2 已证）。

> **这条我们如实写入**：它是对「为什么是全局而不是窄例外」的一个合理技术解释，
> 也是「动机可能是工程便利而非主权立场」的支持性证据。

### 4.5 结论与措辞

**本报告主张**：
> 「密码主权」这一可能的正当理由已被认真检验，**在本样本中不成立**，
> 依据是上述三条互相独立的技术事实，其中两条来自应用自身的行为。

**本报告不主张**：
> 我们已知关闭 ATS 的**真实原因**。动机不可由静态证据判定。
> 真实原因可能是历史遗留、模板复制、或某个已下线接口的兼容——这些**无法排除**。

**本报告明确不说**：
> ❌「ATS 是美国人的私货」——它是 IETF 标准的策略门。
> ❌「关 ATS 让他们用上了中国密码学」——他们一个国密符号都没有。

---

## 5. 那 Apple 认可的**正当**理由有哪些？

为公平起见，列出 Apple 文档承认的合法 ATS 例外场景，并逐一对照本样本：

| Apple 认可的正当理由 | 本样本是否符合 |
|---|---|
| 需连接**第三方服务器**，而该服务器无法提供安全连接 | ❌ 生产域名支持 TLS 1.3 |
| 需支持**无法升级的设备**，且通过公共主机名访问 | ❌ `MinimumOSVersion=11.0`，全支持 TLS 1.2+ |
| 需连接**本地网络设备**（用 `NSAllowsLocalNetworking`） | ❌ 未使用该键 |
| 需加载**媒体内容**（用 `NSAllowsArbitraryLoadsForMedia`） | ❌ 未使用该键 |

**本样本用的是最宽的全局开关，而不是任何一项窄例外。**

> **另一条诚实记录**：Apple 的 App Review 对 `NSAllowsArbitraryLoads` 要求
> 提交理由说明，且可能触发额外审查。**本 App 已在 App Store 上架**——
> 说明 Apple 接受了它提交的理由。**该理由的具体文本不可从 IPA 或公开元数据观测。**

---

## 6. 覆盖面与边界

| 项 | 状态 |
|---|---|
| ATS 要求的协议/套件/阈值 | ✅ Apple 官方文档逐条核对 |
| 本样本 Info.plist 实际配置 | ✅ 直读，含「忽略陷阱」四键逐一排查 |
| ATS 实现代码是否可审计 | ❌ **不可**——`Network.framework` 未开源；Apple 开源的 SecureTransport 已废弃且不支持 TLS 1.3 |
| 生产域名实际 TLS 配置 | ✅ 2026-10-25 实时 `openssl s_client`（**证书会轮换，有时效**） |
| 本 App 是否曾实际协商 TLS 1.0/1.1 或非 PFS 套件 | ❌ **未证**——需运行期观测（0e 动态窗口） |
| 是否发生过 https→http 重定向 | ❌ **未证**——这是被允许的能力，不是已观测事件 |
| App Review 提交的理由文本 | ❌ **不可观测** |

---

## 7. 引文来源

| 主张 | 来源 |
|---|---|
| ATS 是策略层、要求 TLS 1.2+ | `developer.apple.com/documentation/security/preventing-insecure-network-connections` |
| ATS 具体阈值（AES-128/256、ECDHE、RSA≥2048、SHA-256+） | Info.plist Key Reference（归档）`…/InformationPropertyList/NSAppTransportSecurity` |
| `NSAllowsArbitraryLoads` 语义与「忽略陷阱」 | `…/information-property-list/nsapptransportsecurity/nsallowsarbitraryloads` |
| 证书校验仍在、无效证书硬失败 | 同上 |
| 前向保密与套件白名单 | `support.apple.com/guide/security/tls-security-sec100a75d12/web` |
| iOS 信任库含中国 CA（CFCA / GDCA） | `support.apple.com/zh-cn/126047` |
| 套件为 IANA 注册 | `iana.org/assignments/tls-parameters/tls-parameters-4.csv` |
| 中国密码法规推动国密 | 《密码法》第 27 条、《商用密码管理条例》、GB/T 38636-2020、GB/T 39786-2021 |

> **原始研究记录**（含未能核实的项目与置信度标注）：
> [`../evidence/ats-research-raw.json`](../evidence/ats-research-raw.json)
