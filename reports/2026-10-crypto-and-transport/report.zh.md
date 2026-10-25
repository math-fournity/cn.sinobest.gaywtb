# 公安一网通办（cn.sinobest.gaywtb v1.2.28）密码学使用与传输安全调查报告

**独立静态安全调查 · 报告自包含 · 全部主张可用公开工具复算**

> **本文件是综述与索引。** 光读本文件即可了解全貌；想深入某一点，
> 沿每节末尾的链接进对应专题文档、可运行代码与原始证据。

---

## 一句话总结

一款由公安部科技信息化局在 App Store 上架的部级政务服务应用，把一把 **AES-256
密钥以明文硬编码在应用包内**，用 **ECB 工作模式**加密用户的**登录密码、手机号、
验证码**；同一把密钥服务**登录、重置密码、修改密码**三个业务入口；应用
**全局关闭了 iOS 的传输层安全策略（ATS）**；包内另含云从 SDK **自述的"测试密钥"**。

以上每一条都落到可复算的代码位置。**本报告同时记录了我们自己推翻的 5 个结论。**

---

## 调查对象身份（引用前请先核对指纹）

| 项 | 值 |
|---|---|
| 官方名称 | 公安一网通办（`CFBundleDisplayName` 直读） |
| Bundle ID / 版本 | `cn.sinobest.gaywtb` / **1.2.28**（`CFBundleVersion` 2） |
| App Store | trackId **1597440048**，seller **公安部科技信息化局**，2021-12-06 上架 |
| 签名主体 | `TeamIdentifier=JWX2DN7S4Z`；`application-identifier` = `JWX2DN7S4Z.cn.sinobest.gaywtb` |
| 签名证书链 | Apple iPhone OS Application Signing ← Apple iPhone CA ← Apple Root CA（**Apple 分发签名**） |
| CDHash | `f5f3dbaf479ff6ec909b0ebccfd296c49d0d4e2e` |
| **IPA SHA-256** | `d46aaec36700a85b5d1a14834d46e645e145149c8416d94aa294b5975f84f3ad` |
| IPA 字节数 | 64,281,491 |
| 主二进制 | 4,659,328 B（arm64 thin） |
| 架构 | Cordova 混合：native 主二进制 + `www/` 下 310 个 H5 资源 |

> **样本口径**：社区渠道提供的**解密 dump 重打包 IPA**（`cryptid=0`、无
> `embedded.mobileprovision`）。本报告**不主张**任何关于 Apple FairPlay 加密
> 或 App Store 分发链路的内容，只对上表 SHA-256 负责，**不自动适用于其他版本**。

**消歧义**：`cn.sinobest` 对应**北京中科江南信息技术股份有限公司**（创业板上市）。
其与运营方（公安部科技信息化局）的具体关系**本报告不作认定**（见 §7）。

---

## 核心主张速览

| # | 主张 | 证据强度 | 详见 |
|---|---|---|---|
| **A1** | 一把 **AES-256 密钥明文硬编码在 H5 层**，用于加密**登录密码、手机号、验证码**；模式 **ECB**（无 IV） | 代码级（纯文本 JS） | §2 |
| **A2** | 同一把密钥服务**三个业务入口**：登录（加密 password）、重置密码、修改密码（各加密三字段） | 代码级（逐 effect 核对） | §2 |
| **A3** | **全局关闭 ATS**（`NSAllowsArbitraryLoads=true`，无任何更窄的键）⇒ 允许明文 HTTP，**并移除 TLS 1.2 下限、前向保密要求、证书强度检查** | 配置级 + Apple 文档 | §3 · [深度](analysis/01-ATS-深度调查.md) |
| **A4** | 包内含云从 SDK **自述测试密钥**，且被 `checkKey:` **实际取用** | 指令级（xref 经 `__cfstring`，对照 PASS） | §4 |
| **A5** | ECB 的三种后果（同明文同密文 / 枚举字段可还原 / 结构泄露）在**本 App 的真实密钥与模式**下可复现 | 机制级（可运行演示） | §2.5 · [深度](analysis/03-ECB-工作模式.md) |

---

## 目录

### 主报告（本文件）

- [1. 方法与证据等级](#1-方法与证据等级)
- [2. A1 / A2 / A5：硬编码 AES-256-ECB 密钥](#2-a1--a2--a5硬编码-aes-256-ecb-密钥)
- [3. A3：全局关闭 ATS](#3-a3全局关闭-ats)
- [4. A4：厂商自述测试密钥](#4-a4厂商自述测试密钥)
- [5. 密钥普查](#5-密钥普查)
- [6. 明确不主张的事项](#6-明确不主张的事项)
- [7. 责任主体](#7-责任主体)
- [8. 开放问题](#8-开放问题)
- [9. 复现指南](#9-复现指南)
- [10. 引用规范](#10-引用规范)
- [11. 版本](#11-版本)

### 深度专题

| 文档 | 回答什么问题 |
|---|---|
| [**01 · ATS 深度调查**](analysis/01-ATS-深度调查.md) | ATS 是不是美国人的私货？关掉它到底关掉了什么？「密码主权」抗辩成立吗？ |
| [**02 · 方法论与自我推翻记录**](analysis/02-方法论与自我推翻记录.md) | 这次调查怎么做的？我们犯了哪些错、怎么发现的、转化成了什么判据？ |
| [**03 · ECB 工作模式**](analysis/03-ECB-工作模式.md) | AES-256 到底有没有问题？为什么密钥长度救不了 ECB？ |

### 可运行代码

| 脚本 | 作用 |
|---|---|
| [`code/ecb_demo.py`](code/ecb_demo.py) | **亲眼看到 ECB 的三个后果**——用本 App 的真实密钥与模式 |
| [`code/xref_check.py`](code/xref_check.py) | 字符串是否真被代码取用（**强制阳性对照**，防工具静默失明） |

### 原始证据

| 文件 | 内容 |
|---|---|
| [`evidence/ats-research-raw.json`](evidence/ats-research-raw.json) | ATS 研究的原始记录（含未能核实项与置信度） |

---

## 1. 方法与证据等级

| 等级 | 含义 | 本报告用于 |
|---|---|---|
| L1 串在场 | 字符串存在于包内 | A4 的定位 |
| L3 指令级 | 反汇编取址指令 + 调用点 | A4 的「实际取用」 |
| **L3′ 代码级（H5）** | 纯文本 JS 的调用点与端点 | **A1、A2** |
| L4 配置级 | 配置文件直读 | A3 |
| L5 机制级 | 可复算的密码学演示 | A5 |

> **为什么 A1/A2 用 L3′**：本 App 是 Cordova 混合架构，加密逻辑全在 `www/`
> 下的**纯文本 JavaScript** 中，无混淆、无字节码。读源码比反汇编更直接、
> 更可复核——第三方用文本编辑器与 `grep` 即可独立验证。

### 1.1 三条方法纪律

1. **阳性对照是硬要求**。任何阴性/计数结论，先证明工具能看见东西。
   本报告的工具找不回已知项就**退出非零、不出结论**。
2. **计数必须给口径**。「几把密钥」要能复算：扫了哪些成员、几个通道、怎么去重。
3. **最强替代假说必须显式排除**，并给出判别性特征。

> **本报告在成稿中推翻了自己 5 次**，其中 2 次是主报告级错误。
> 完整记录见 [**02 · 方法论与自我推翻记录**](analysis/02-方法论与自我推翻记录.md)。

---

## 2. A1 / A2 / A5：硬编码 AES-256-ECB 密钥

### 2.1 密钥与加密函数

`www/p__login__Login.js` @9465：

```js
Q = e => {
  var r = O.a.enc.Utf8.parse("385f33cb…9081ab7"),
      o = O.a.AES.encrypt(e, r, {mode: O.a.mode.ECB, padding: O.a.pad.Pkcs7});
  return o.ciphertext.toString()
}
```

- `Utf8.parse` 传 32 个 ASCII 字符 ⇒ 32 字节 ⇒ CryptoJS 自动选 **AES-256**；
- `mode: ECB` ⇒ **无 IV**，同一明文恒定产生同一密文。

**同一把密钥共 3 处代码实例**（全包普查）：

| # | 文件 | 偏移 | 服务的功能 |
|---|---|---|---|
| 1 | `www/p__login__Login.js` | 9485（+9465 parse） | **登录**（加密 password） |
| 2 | `www/umi.js` | **423347** | **重置密码**（加密三字段） |
| 3 | `www/umi.js` | **769557** | **修改密码**（加密三字段） |

### 2.2 三个业务入口（A2）

| 入口 | 调用链 | 端点 | 加密字段 |
|---|---|---|---|
| **登录** | `Login.js` @9617 `X` handler → `o.password = Q(o.password)` → `login/tryLogin` | `POST /api/fwmh/mobile/login` | **仅 password** |
| **重置密码** | `umi.js` `resetPossword` @425347 → `S(phone)/S(validateCode)/S(password)` + `encryption:"1"` | `POST /api/user/password` | 三字段 |
| **修改密码** | `p__grzx__Xgmm.js` @10827 → `grzx/changePass` → `umi.js` @771557 `Y(...)` + `encryption:"1"` | `POST /api/user/password` | 三字段 |

> **一处容易搞错的地方**：`login` model 里的 `tryLogin` effect **不加密**，
> 它把 payload 原样透传给 service。加密发生在**组件层**的 `X` handler。
> 本报告早期草稿曾误以为加密在框架层且加密三字段——已更正（见 02 号文档 §2.5）。

**`encryption:"1"` 的含义**：后两个入口在请求体显式携带该标记，表明**服务端按约定
识别并解密该模式**——「客户端藏钥」是该应用的**设计选择**，不是工程疏漏。

### 2.3 最强替代假说已排除：这不是 SSL pinning

| 判别维度 | 若为 pinning 应见 | 本 App 实测 |
|---|---|---|
| 被验值去向 | 参与比对，**永不进密钥编排** | 直接作为 `AES.encrypt` 的**密钥参数** |
| 输出形态 | 布尔 / 抛错 | `o.ciphertext.toString()` —— **产出密文** |
| IV | 不涉及 | ECB 无 IV |
| 请求标记 | 无 | `encryption:"1"` |

### 2.4 密钥的公开性

- **已证**：密钥明文存在于随包发布的资源中，任何取得该 IPA 的人可在数秒内读出；
- **不主张**：「已在真实攻击中被利用」。密钥自 2021-12 首个版本起随每个安装包公开，
  这是**公开性**事实，不是**被利用**事实。

### 2.5 ECB 到底错在哪（A5）

> 完整版：[**03 · ECB 工作模式**](analysis/03-ECB-工作模式.md)
> 亲手复现：`python3 code/ecb_demo.py`

**三个可复现的后果**（用本 App 的真实密钥与模式）：

| 后果 | 实测 |
|---|---|
| **同明文 → 同密文** | `"Passw0rd!2024"` 两个用户 → 都是 `3e29a482…aa57` ⇒ 看日志的人立刻知道两人同密码 |
| **枚举字段可还原** | `"13800138000"` → `cd641daa…4add`，离线穷举 **1001 个候选内命中** |
| **结构泄露** | 明文 `[A*16][B*16][A*16]` → 密文第 1 块 == 第 3 块 |

**正面回答「AES-256 这么长还不够吗」**：

| 攻击 | 需要破解 AES-256 | 受密钥长度影响 |
|---|---|---|
| 同明文比对 | ❌ 不需要 | ❌ 不受 |
| 枚举字段还原 | ❌ 不需要（只需一次加密运算） | ❌ 不受 |
| 结构泄露 | ❌ 不需要 | ❌ 不受 |

**ECB 的弱点全部绕开了「密钥多长」这个问题。** 256 位密钥保护的是「从密文反推
密钥」，而这些攻击根本不需要密钥。

NIST SP 800-38A §6.1 原文：

> "In the ECB mode, under a given key, any given plaintext block always gets encrypted
> to the same ciphertext block. **If this property is undesirable in a particular
> application, the ECB mode should not be used.**"

> **引用边界**：SP 800-38A 自述 *"neither a standard nor a guideline, and as such, is
> neither mandatory nor binding on Federal agencies"* —— **建议性文献**。
> 本报告只写「NIST 建议此类场景不应使用 ECB」，**不写「违反 NIST 标准」**。
> 另：该文件全文**不含** "diffusion"/"short" 等表述（独立验证者全文 grep 零命中），
> 「ECB 缺乏扩散」是教科书通说，**不挂在该文件名下**。

---

## 3. A3：全局关闭 ATS

> 完整版：[**01 · ATS 深度调查**](analysis/01-ATS-深度调查.md)

`Info.plist`：

```xml
<key>NSAppTransportSecurity</key>
<dict><key>NSAllowsArbitraryLoads</key><true/></dict>
```

**是全局开关**：整个字典只有这一个键，**没有** `NSExceptionDomains`、
没有 `NSAllowsArbitraryLoadsInWebContent`、没有 `NSAllowsLocalNetworking`、
没有 `NSPinnedDomains`。`MinimumOSVersion=11.0`。

> **一个大多数分析会搞错的点**：iOS 10+ 若同时存在上述更窄的键，
> `NSAllowsArbitraryLoads` 会被**静默忽略**（ATS 实际是开着的）。
> 本样本**四键全无**，故忽略陷阱不适用，该键完全生效。

### 3.1 关掉它意味着什么（比「只允许明文」更重）

| 被移除的保护 | 后果 |
|---|---|
| 允许明文 HTTP | 任何明文连接不被拦截 |
| **TLS 1.2 下限** | 可协商 TLS 1.0 / 1.1 |
| **前向保密（PFS）要求** | 可协商非 PFS 套件（长期密钥泄露 ⇒ 历史流量可解） |
| **证书强度检查** | 可接受更弱证书 |

**证书校验仍在**（无效证书仍是硬失败）——移除的是**护栏**，不是**校验**。

### 3.2 生产流量实际走 HTTPS

`www/umi.js` @968752：

```js
"test" === h ? (n.url = testurl + e) : ("dev" !== h && (n.url = url + e))
```

`h` = `{…, REACT_APP_ENV: "prod", …}.REACT_APP_ENV` ⇒ **`h === "prod"`**
⇒ 走 `https://ywtb.mps.gov.cn/mobileBack`。**`testurl`（明文 IP）不可达。**

**意义**：应用**并不需要**明文能力。既然生产流量全走 HTTPS，ATS 全局关闭
**没有任何功能性必要**——它不解决任何问题，只降低下限。

### 3.3 「密码主权」抗辩：已检验，不成立

| # | 若主权抗辩成立，应见 | 实测 |
|---|---|---|
| 1 | 改用国密 TLS | 主二进制 `SM2/SM3/SM4/GMTLS/gmssl/TLCP` **全零命中**；H5 层 `SM2/SM3` 命中经核对**全是 Base64 数据流里的随机子串** |
| 2 | 不信任境外 PKI | 生产域名证书链仍锚 **Certum（波兰，EU）** |
| 3 | 不对自有服务器留明文通道 | 同一台 `36.112.134.71` 同时保留 `https://` 与 `http://…:38888` |

**最致命**：**关闭 ATS 在技术上不可能带来国密能力**——ATS 是策略层，位于密码层
之上，且不适用于 TLCP 协议栈所用的底层 API。关掉它换来的唯一能力是「可以发明文」。

**诚实边界**：本报告**不主张**已知关闭 ATS 的**真实原因**（动机不可由静态证据判定）。
可能是历史遗留、模板复制、或某个已下线接口的兼容——**无法排除**。

---

## 4. A4：厂商自述测试密钥

| 值 | 偏移 | 长度 |
|---|---|---|
| `cw_test_aes_key_` | **3735557** | 16 B |
| `cw_test_sm4_key_` | **3735574** | 16 B |

### 4.1 确实被代码取用（指令级）

经 `__DATA,__cfstring` 中转：

```
0x100170868  adrp x1,0x1003f0000 ; add x1,#0x748 → __cfstring @0x1003f0748
                                                     └ +16 → 0x100390005 = "cw_test_aes_key_"
0x100170884  adrp x1,0x1003f0000 ; add x1,#0x768 → __cfstring @0x1003f0768
                                                     └ +16 → 0x100390016 = "cw_test_sm4_key_"
```

两分支均在 `-[CWDataProcessUtil checkKey:encryptStyle:]`（IMP 0x100170808）内，
形态为「若当前钥为空则装载该测试钥」的回退逻辑。

> 复核：`python3 code/xref_check.py <binary> 'cw_test_aes_key_' --control 'cw_test_sm4_key_'`

### 4.2 为什么这构成问题

NIST SP 800-57 Part 1 Rev. 5 §8.1.4（印刷页 92）：

> "Many applications or systems are provided by the manufacturer with keying material
> that is used to test that the newly installed application/system is functioning
> properly. **This test keying material shall not be used operationally.**"

> **引用边界**：SP 800-57 是**美国联邦密钥管理指引**，不是移动应用安全标准，
> 也不针对 iOS。它**没有**「禁止在源码中硬编码密钥」的条文（全文 `hardcod` /
> `source code` / `compil*` 零命中）。本报告引用它**只为一件事**：§8.1.4 明确
> 指出测试密钥材料不得用于生产。

---

## 5. 密钥普查

**口径**：IPA 全部 **1013 个成员**逐字节扫描，六个通道。

| 通道 | 方法 | 命中 |
|---|---|---|
| C1 | CryptoJS `…parse("<payload>")` | 1 |
| C2 | 裸 hex 常量（按上下文分类） | 17 → 3 处密码学绑定 |
| C3 | key 语义 C 字符串 | 264（绝大多数是 SDK 的 key 路径，非密钥值） |
| C4 | 字符串 section 内 16 字节 ASCII | 146（候选池，**不构成密钥判定**） |
| C5 | `.bundle` 资源 | 2（CWResource=纯图片/模型） |
| C6 | 高熵 Base64 常量 | **0**（首版曾误报 2，见下） |

**阳性对照 3/3 PASS** —— 这是阴性结论可信的前提。

**结果：1 个不同值 / 4 个实例**（`385f33cb…ab7`）。

### 5.1 撤回：那个 64 字符 Base64 串不是密钥

早期草稿把主二进制 @3793688 的 `adQOeq…ugF5C` 列为「48 字节密钥材料（熵 5.543）」。
**撤回**。反汇编证实它是 **Base64 编码器的查表字母表**：

```asm
adr   x25, literal pool for "adQOeq…"
ldrsb w1, [x25, x8]        ← 6-bit 分组索引查表
bl    basic_string::push_back
...
adr   x1, literal pool for "="    ← 补位串
```

配合 `lsr #2/#4/#6` + `and #0x3f`，且该串 64 字符与 `A-Za-z0-9+/` **完全同集**。

**熵为什么会骗人**：把 64 个互异字符当 Base64 解码，**必然**得到熵 ≈5.5 的
伪随机字节。**熵高是「解码一个字母表」的数学必然，不是随机性证据。**

### 5.2 其他被排除的假阳性

| 候选 | 为何像密钥 | 如何排除 |
|---|---|---|
| `p__home__Zone.js` 6 个 `ff8080…` 32-hex | 长度符合 AES-256 | 是业务卡片 `id:` 数据；首版因 `des` 命中 JSX 属性 `des:` 而误判 |
| `h%D-j-E-l5F-n=G-` @2444880 | 16 可打印字节、熵 3.27 | 前后是 AArch64 指令编码——`__text` 被误读成 ASCII |
| 55 个「高熵 Base64」 | 解码熵达 5.06 | 是 ObjC 选择子/框架路径。**熵不是判据** |
| `aes256EncryptWithKey:data:` | 方法名直指 AES | 属 **BLYHelper**（腾讯 Bugly），非本应用加密面 |

---

## 6. 明确不主张的事项

1. **「无加固壳」本身不是缺陷**。OWASP MASVS 原文：纵深防御措施缺失
   *"does not in itself constitute a vulnerability"*，混淆
   *"aren't considered mandatory"*。本 App 无壳，**不构成 MASVS 违规**。
2. **明文 HTTP 端点 `36.112.134.71:38888` 不是生产地址**（配置中的 `testurl`）。
   保留的主张仅为：测试端点随包发布，且 ATS 全局关闭使其可被实际使用。
3. **`cn.sinobest` 与公安部的关系未认定**。
4. **未主张任何「已被攻击/已被利用」的事实**。
5. **未主张 `Assets.car`、`.mnn` 模型文件内的内容**（未解包）。
6. **未做运行期观测**——全部为静态证据。
7. **不主张云从 native 组件使用正式密钥**（其 API 为参数化设计）。
8. **不主张 ATS 被降级到 TLS 1.0/非 PFS 套件曾实际发生**——这是被解锁的**能力**，
   不是已观测事件。

---

## 7. 责任主体

| 层面 | 事实 | 来源 |
|---|---|---|
| 上架主体 | 公安部科技信息化局 | App Store lookup API |
| 签名主体 | `TeamIdentifier=JWX2DN7S4Z` | `codesign -dvvv` + entitlements |
| 命名空间 | `cn.sinobest` → 北京中科江南（创业板上市） | bundleId 前缀 |
| 厂商 SDK | 云从科技（`cw_*` 符号族、`CWResource.bundle`） | 二进制符号与路径 |
| 崩溃上报 | 腾讯 Bugly（`BLY*` 类族） | 二进制类名 |

### 待共同确认（不裁断）

1. 北京中科江南与公安部科技信息化局的具体关系（承建／运维／仅命名空间复用）；
2. H5 层代码的实际编写方（`umi.js` 内含 `/Users/wulingjie/IdeaProjects/gazwfw/…`）；
3. 主二进制内 `/Users/zhangdanfeng/workspace/dpnet-ios…`（MNN 分支）的归属。

---

## 8. 开放问题

| # | 问题 | 为何未答 |
|---|---|---|
| 1 | 服务端是否确实按 `encryption:"1"` 解密？ | 需服务端行为 |
| 2 | 云从 native 组件在生产中是否传入正式密钥？ | API 参数化，静态不可见 |
| 3 | 其他版本是否同样？ | 只对 SHA-256 `d46aaec3…` 负责 |
| 4 | ATS 关闭的**真实原因**？ | 动机不可由静态证据判定 |
| 5 | 是否实际发生过 TLS 降级或 https→http 重定向？ | 需运行期观测 |

---

## 9. 复现指南

前置：取得 SHA-256 为 `d46aaec36700a85b5d1a14834d46e645e145149c8416d94aa294b5975f84f3ad`
的同一 IPA。**先核对指纹**，不符则结论不适用。

### 9.1 A1 / A2（硬编码密钥 + 三个入口）

```bash
unzip -q cn.sinobest.gaywtb-1.2.28-Decrypted.ipa -d out/
APP="out/Payload/公安一网通办.app"

# 密钥的 3 处代码实例。
# 必须用 grep -o | wc -l 统计出现次数，不能用 grep -c ——
# 压缩后的 umi.js 整个文件只有一行，grep -c 数的是行数，会恒为 1。
echo -n "Login.js: "; grep -o "385f33cb…9081ab7" \
    "$APP/www/p__login__Login.js" | wc -l    # 期望 1
echo -n "umi.js:   "; grep -o "385f33cb…9081ab7" \
    "$APP/www/umi.js" | wc -l                # 期望 2

# 加密函数与 ECB 模式
grep -o 'Utf8.parse("385f33cb…9081ab7")[^;]*' \
     "$APP/www/p__login__Login.js"

# 入口一：登录（只加密 password）
grep -o 'o\.password=Q(o\.password)' "$APP/www/p__login__Login.js"
grep -o '/api/fwmh/mobile/login' "$APP/www/umi.js"

# 入口二：重置密码（三字段 + encryption:"1"）
grep -o 'resetPossword' "$APP/www/umi.js"
grep -o 'o\.phone=S(c)),l&&(o\.validateCode=S(l)),d&&(o\.password=S(d))' "$APP/www/umi.js"

# 入口三：修改密码（三字段 + encryption:"1"）
grep -o 'grzx/changePass' "$APP/www/p__grzx__Xgmm.js"
grep -o 'o\.phone=Y(c)),l&&(o\.validateCode=Y(l)),d&&(o\.password=Y(d))' "$APP/www/umi.js"

# 两个加密入口共用的端点
grep -o '/api/user/password' "$APP/www/umi.js"
```

### 9.2 A3（ATS 全局关闭）

```bash
plutil -p "$APP/Info.plist" | grep -A3 NSAppTransportSecurity
# 期望：{ "NSAllowsArbitraryLoads" => 1 }，且无 NSExceptionDomains

# 确认「忽略陷阱」不适用（四个更窄的键都不存在）
plutil -p "$APP/Info.plist" | grep -E "NSAllowsArbitraryLoadsInWebContent|NSAllowsLocalNetworking|NSExceptionDomains|NSPinnedDomains" \
  || echo "四键全无 → 该键完全生效"
```

### 9.3 A4（测试密钥及其取用）

```bash
BIN="$APP/公安一网通办"

# 串在场（偏移应为 3735557 / 3735574）
grep -abo 'cw_test_aes_key_' "$BIN"
grep -abo 'cw_test_sm4_key_' "$BIN"

# 取用点：adrp+add 指向 __cfstring 结构。
# 注意：otool -tV 会把这两个 CFString 显示成 @"bad cfstring ref"（未重定位），
# 必须自己解结构才能看到真值 —— 用本 repo 的脚本：
python3 code/xref_check.py "$BIN" 'cw_test_aes_key_' --control 'cw_test_sm4_key_'
# 期望：TARGET 经 __cfstring 命中 1 处；对照 PASS
```

### 9.4 A5（ECB 后果）

```bash
python3 code/ecb_demo.py
# 或手工：
KEYHEX=$(printf '%s' '385f33cb…9081ab7' | xxd -p -c 256)
printf 'Passw0rd!2024' | openssl enc -aes-256-ecb -K "$KEYHEX" -nosalt | xxd -p -c 256
# 期望 3e29a48221c4faf1b685ec5b5e5eaa57（连跑两次相同）
```

### 9.5 复核 §5.1 的撤回

```bash
python3 - <<'EOF'
s = b"adQOeqjWNAU1rJTSpts/zvk367Eb2ZmLVi8n+hHPYG9cxlDw0IMKoyfR4BXugF5C"
std = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")
print("len:", len(s), "distinct:", len(set(s)))
print("charset == standard base64 alphabet:", set(s) == std)
EOF
# 期望：len 64，distinct 64，charset == True ⇒ 是字母表，不是密钥
```

---

## 10. 引用规范

1. 注明所核验样本的 **SHA-256**（`d46aaec3…f3ad`）与版本（1.2.28）；
2. 区分**本报告的主张**与**被引规范的主张**——尤其注意 §2.5、§3.3、§4.2 的引用边界；
3. 不得将 §6「明确不主张的事项」改写成缺陷主张；
4. 不得引用**已撤回**的内容（§5.1）。

---

## 11. 版本

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0 | 2026-10-25 | 首版 |
| 1.1 | 2026-10-25 | 撤回 A5（Base64 字母表非密钥）；修正 A2（三字段属重置/修改密码）；补 A4 指令级证据 |
| 1.2 | 2026-10-25 | 新增 ECB 人话讲解；新增明文 HTTP 成因分析；新增主权抗辩检验 |
| **1.3** | 2026-10-25 | **重构为「综述 + 索引」**：深度内容拆为 `analysis/`（ATS 深度调查、方法论与自我推翻记录、ECB 工作模式），可运行代码入 `code/`，原始证据入 `evidence/`；**修正 A3**（关 ATS 不止放行明文，还移除 TLS 1.2 下限/PFS/证书强度检查） |

---

**本报告为独立静态安全调查，基于公开可获取的样本与公开规范文献。每一条主张均
给出可复算的文件与字节偏移。报告作者与所涉任何主体无利益关联。**
