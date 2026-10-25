# 公安一网通办（cn.sinobest.gaywtb v1.2.28）密码学使用与传输安全调查报告

**独立静态安全调查 · 报告自包含 · 全部主张可用公开工具复算**

---

## 一句话总结

一款由公安部科技信息化局在 App Store 上架的部级政务服务应用，把用于加密用户
**登录密码、手机号、验证码**的 AES-256 密钥以明文硬编码在应用包内，且使用
ECB 工作模式；同一把密钥同时用于**登录**与**修改密码**两条独立业务链；应用
**全局关闭了 iOS 的传输层安全强制（ATS）**；包内另含厂商自述的"测试密钥"与
一枚 48 字节密钥材料。以上每一条都落到可复算的代码位置。

---

## 调查对象身份（引用本报告结论前请先核对指纹）

| 项 | 值 |
|---|---|
| 官方名称 | 公安一网通办（`CFBundleDisplayName` 直读） |
| Bundle ID / 版本 | `cn.sinobest.gaywtb` / `CFBundleShortVersionString` **1.2.28**（`CFBundleVersion` 2） |
| App Store | trackId **1597440048**，seller **Science and Technology Information Bureau of the Public Security Ministry of China**，artistName **公安部科技信息化局**，2021-12-06 上架，当前版本 2023-11-20 |
| 签名主体（entitlements） | `com.apple.developer.team-identifier` = **JWX2DN7S4Z**；`application-identifier` = `JWX2DN7S4Z.cn.sinobest.gaywtb` |
| IPA SHA-256 | `d46aaec36700a85b5d1a14834d46e645e145149c8416d94aa294b5975f84f3ad` |
| IPA 字节数 | 64,281,491 |
| 主二进制 | `Payload/公安一网通办.app/公安一网通办`，4,659,328 B（arm64） |
| 架构 | Cordova 混合应用：native 主二进制 + `www/` 下 310 个 H5 资源（136 JS / 88 HTML / 110 CSS） |

> **样本口径**：本次调查对象为社区渠道提供的**解密 dump 重打包 IPA**
> （`cryptid=0`、无 `embedded.mobileprovision`）。因此**本报告不主张任何关于
> Apple FairPlay 加密或 App Store 分发链路的内容**，只对上述 SHA-256 的样本负责。
> 结论**不自动适用于其他版本**。

**消歧义**：`cn.sinobest` 命名空间对应**北京中科江南信息技术股份有限公司**
（创业板上市）。该公司与本 App 的运营方（公安部科技信息化局）之间的具体关系
（开发承建／运维／仅命名空间复用）**本报告不作认定**，详见 §7「待共同确认」。

---

## 核心主张速览

| # | 主张 | 证据强度 | 规范依据 |
|---|---|---|---|
| **A1** | 登录与改密的**手机号、验证码、密码**三字段，用**硬编码在 H5 层的 AES-256 密钥**加密后上传；工作模式为 **ECB**（无 IV） | **代码级实证**（纯文本 JS，逐行可读） | NIST SP 800-38A §6.1（确定性）；OWASP MASVS 密钥管理 |
| **A2** | 同一把密钥用于**两条独立业务链**：登录 `POST /api/fwmh/mobile/login` 与改密 `POST /api/user/password` | **代码级实证**（两条链各自的调用点与端点） | 同上 |
| **A3** | 应用**全局关闭 ATS**（`NSAllowsArbitraryLoads = true`），无任何域名例外白名单 | **配置级实证**（Info.plist 直读） | Apple ATS 官方文档 |
| **A4** | 包内含云从 SDK 的**自述测试密钥** `cw_test_aes_key_` / `cw_test_sm4_key_` | **字符串级实证**（`__TEXT,__cstring` 偏移可读） | NIST SP 800-57 §8.1.4「测试密钥材料不得用于生产」 |
| **A5** | 包内含一枚 **48 字节 Base64 编码的密钥材料**（熵 5.543 bit/B），位于活体检测「消息生成」代码邻域 | **材料级实证**（值+位置+邻域）；**用途未证** | — |

**明确不主张的事项**（防夸大，完整清单见 §6）：本 App 无加固壳本身不是缺陷；
明文 HTTP 端点 `36.112.134.71:38888` 是配置中的测试地址而非生产地址；48 字节
密钥材料「用于加密什么」未证；`cn.sinobest` 与公安部的关系未认定。

---

## 1. 调查方法与证据等级

本报告对每条主张标注证据等级，取自公开可复算的静态证据：

| 等级 | 含义 | 本报告是否使用 |
|---|---|---|
| L1 串在场 | 字符串/常量存在于包内 | 用于 A4、A5 |
| L2 符号在场 | 符号表/导出面存在 | 未单独使用 |
| L3 指令级 | 反汇编调用链（分支/取数/调用点地址） | 未使用（本 App 关键证据在 H5 层，见下） |
| **L3′ 代码级（H5）** | **纯文本 JS 源码中的函数定义、调用点、网络端点** | **用于 A1、A2** |
| L4 配置级 | 配置文件直读 | 用于 A3 |

> **为什么 A1/A2 用 L3′ 而非 L3**：本 App 是 Cordova 混合架构，登录/改密的
> 加密逻辑**全部在 `www/` 下的纯文本 JavaScript 中**，无混淆、无压缩到不可读、
> 无字节码。对这类目标，读源码比反汇编更直接、更可复核——第三方用文本编辑器
> 与 `grep` 即可独立验证，不需要反汇编器。

**方法纪律**（本报告实际执行）：
1. **每条主张给出文件 + 偏移 + 期望字节**，偏移均为文件内字节偏移；
2. **阳性对照**：密钥普查工具内置三个已知钥作为对照，找不到即判定该扫描通道
   失明、普查作废（本次 3/3 通过）；
3. **噪声基线**：所有「计数型」主张都先算随机/背景基线（见 §5 假阳性记录）；
4. **最强替代假说必须被排除**：A1 的替代假说「这是 SSL pinning 而非加密」已
   逐特征排除（§2.3）。

---

## 2. 主张 A1 / A2：硬编码 AES-256-ECB 密钥，用于登录与改密

### 2.1 密钥与加密函数

文件 `Payload/公安一网通办.app/www/p__login__Login.js`，字节偏移 **9465**：

```js
O.a.enc.Utf8.parse("385f33cb…9081ab7"),
o = O.a.AES.encrypt(e, r, {mode: O.a.mode.ECB, padding: O.a.pad.Pkcs7});
return o.ciphertext.toString()
```

- `Utf8.parse` 传入 **32 个 ASCII 字符** ⇒ 32 字节密钥材料 ⇒ CryptoJS 按密钥
  长度自动选择 **AES-256**（CryptoJS 官方文档：「It will pick the variant by the
  size of the key you pass in」，见 `evidence` 引文）。
- `mode: ECB` ⇒ **无 IV**，同一明文在同一密钥下**恒定产生同一密文**。

**同一把密钥在包内共 3 处代码实例**（全包普查结果，非抽样）：

| # | 文件 | 字节偏移 | 所在模型 | 用途 |
|---|---|---|---|---|
| 1 | `www/p__login__Login.js` | 9485（+9465 `Utf8.parse`） | 登录页组件 | 登录 |
| 2 | `www/umi.js` | **423347** | `namespace:"login"` | 登录 |
| 3 | `www/umi.js` | **769557** | `namespace:"grzx"`（个人中心） | **修改密码** |

### 2.2 两条独立业务链（A2）

**链一 · 登录**

```
www/index.html                      <script src="./umi.js">
 └ umi.js 路由表                     {path:"/login", loader: 懒加载 p__login__Login chunk 族}
    └ p__login__Login.js @12194/@13769   onClick:X（两个「登录」按钮）
       └ @9617  X = () => { … }
          └ @9755  o.password = Q(o.password)
             └ @9450  Q = AES-256-ECB 加密
                └ umi.js @420661   POST /api/fwmh/mobile/login
```

**链二 · 修改密码**

```
www/p__grzx__Xgmm.js @10827         dispatch({type:"grzx/changePass",
                                              payload:{phone, validateCode, password, type:"chg"}})
 └ umi.js @771557                   c && (o.phone = Y(c)),
                                    l && (o.validateCode = Y(l)),
                                    d && (o.password = Y(d)),
                                    o = {...o, encryption:"1"}
                                    └ @769557  Y = AES-256-ECB（同一把密钥）
                                       └ umi.js @422451   POST /api/user/password
```

页面可达性：chunk 表 `39:"p__grzx__Xgmm"`（`umi.js` @2264），
`p__grzx__Xgmm.js` 在场（93,867 B）。

**三字段而非仅密码**：两条链都对 `phone`、`validateCode`、`password` 三个字段
分别调用同一加密函数，并在请求体加 `encryption:"1"` 标记——这表明**服务端按约定
识别并解密该模式**，即「客户端藏钥」是该应用的**设计选择**，不是工程疏漏或残留代码。

### 2.3 最强替代假说已排除：这不是 SSL pinning

| 判别维度 | 若为 pinning 应见 | 本 App 实测 |
|---|---|---|
| 被验值的去向 | 参与比对（memcmp / 哈希比较），**永不进入密钥编排** | 直接作为 `AES.encrypt` 的**密钥参数** |
| 输出形态 | 布尔值 / 抛错 | `o.ciphertext.toString()` —— **产出密文** |
| IV | 不涉及 | ECB 无 IV（`mode:ECB` 写在代码里） |
| 请求标记 | 无 | `encryption:"1"` 显式声明加密模式 |

### 2.4 ECB 的具体后果（为什么这构成问题而非风格偏好）

NIST SP 800-38A §6.1 原文（官方 PDF，印刷页 9-10）：

> "The Electronic Codebook (ECB) mode is a confidentiality mode that features, for a
> given key, the assignment of a fixed ciphertext block to each plaintext block,
> analogous to the assignment of code words in a codebook."
>
> "In the ECB mode, under a given key, any given plaintext block always gets encrypted
> to the same ciphertext block."
>
> "If this property is undesirable in a particular application, the ECB mode should
> not be used."

**落到本 App 的具体后果**：
1. 同一密码在不同用户、不同时间登录时，产生的密文**完全相同**——服务端日志、
   网络中间设备、任何能看到密文的一方，都可直接判断「这两个账号用了同一个密码」；
2. 手机号与验证码同样处理，且手机号取值空间小（号段+号），可被字典穷举反推；
3. 密钥公开后（见 §3），ECB 的确定性使「已知明文攻击」不再需要任何密码学投入。

> **引用边界（必须一并声明）**：SP 800-38A 在印刷页 1 自述
> "neither a standard nor a guideline, and as such, is neither mandatory nor binding
> on Federal agencies"。**它是建议性文献**。本报告因此只写「NIST 建议 ECB 在此
> 类场景下不应使用」，**不写「违反 NIST 标准」**。
> 另：SP 800-38A 全文**不含** "diffusion"、"short data" 等表述——「ECB 缺乏扩散、
> 只适合短数据」是密码学教科书通说，**不是该文件原句**，本报告不将其挂在该文件名下。

---

## 3. 主张 A3：全局关闭 App Transport Security

文件 `Payload/公安一网通办.app/Info.plist`：

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

**这是全局开关，不是逐域名例外**：整个 `NSAppTransportSecurity` 字典只有
`NSAllowsArbitraryLoads=true` 一个键，没有 `NSExceptionDomains` 白名单。
意味着该应用**任何**明文 HTTP 连接都不会被系统拦截。

Apple 官方文档原文：

> "ATS requires that all HTTP connections made with the URL Loading System—typically
> using the URLSession class—use HTTPS."（NSAppTransportSecurity — Discussion）
>
> "App Transport Security has blocked a cleartext HTTP (http://) resource load since
> it is insecure. Temporary exceptions can be configured via your app's Info.plist
> file."（Preventing Insecure Network Connections）

**与 A1 的叠加效应**：即使登录/改密的密文被中间人截获，由于密钥在包内公开（§3.1）、
模式为 ECB（§2.4），攻击者可直接解密或重放。ATS 关闭使这条路径**不需要任何证书
伪造**即可实施。

### 3.1 密钥公开性的说明（不夸大）

需要区分两件事：
- **本报告已证**：密钥以明文存在于随包发布的应用资源中，任何取得该 IPA 的人可
  在数秒内读出；
- **本报告不主张**：「已在真实攻击中被利用」。密钥自 2021-12 首个版本起即随每个
  安装包公开，这是**公开性**事实，不是**被利用**事实。

---

## 4. 主张 A4 / A5：包内其他密钥材料

### 4.1 厂商自述测试密钥（A4）

主二进制 `Payload/公安一网通办.app/公安一网通办`，`__TEXT,__cstring` 区：

| 值 | 字节偏移 | 长度 |
|---|---|---|
| `cw_test_aes_key_` | **3735557** | 16 B |
| `cw_test_sm4_key_` | **3735574** | 16 B |

二者相邻，位于云从（CloudWalk）活体检测 SDK 的常量区，作为密钥校验/回退路径
的装载来源。

NIST SP 800-57 Part 1 Rev. 5 §8.1.4（印刷页 92）原文：

> "Many applications or systems are provided by the manufacturer with keying material
> that is used to test that the newly installed application/system is functioning
> properly. **This test keying material shall not be used operationally.**"

> **引用边界**：SP 800-57 是**美国联邦密钥管理指引**，不是移动应用安全标准，
> 也不针对 iOS。它没有、本报告也不声称它有一条「禁止在源码中硬编码密钥」的条文
> （该文件全文 `hardcod` / `source code` / `compil*` 均零命中）。
> 本报告引用它**只为一件事**：其 §8.1.4 明确指出测试密钥材料不得用于生产——
> 这与本 App 随生产包发布 `cw_test_*_key_` 的事实直接相关。

### 4.2 48 字节密钥材料（A5）

主二进制两处（**同一值**）：字节偏移 **3793688** 与 **3794402**。

```
adQOeqjWNAU1rJTSpts/zvk367Eb2ZmLVi8n+hHPYG9cxlDw0IMKoyfR4BXugF5C
```

- Base64 解码 = **48 字节**，香农熵 **5.543 bit/byte**（随机材料特征，非编码文本）；
- 十六进制：`69d40e7aa8d6340535ac94d2a6db3fcef937ebb11bd9998b562f27fa11cf606f5cc650f0d0830aa327d1e015ee805e42`
- 48 = 32 + 16，符合「AES-256 密钥 + 16 字节 IV」的组合长度；
- 邻域上下文（@3794402 之后紧接）：`abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890123456789`
  （标准编码字母表）与 `m5sum` / `m5len` / `m5cross`（校验和字段），位于云从
  活体检测「消息生成」代码区。

> **证据边界（务必遵守）**：本报告**只主张**「该 48 字节随机材料以明文随包发布」。
> **不主张**它用于加密什么、由哪段代码取用——`adrp+add` 交叉引用扫描对该地址
> **零命中**，其取用路径静态未证。此项列为开放问题（§8）。

---

## 5. 密钥普查：2 个不同值 / 6 个实例

**普查口径**（可复算）：IPA 全部 **1013 个成员**逐字节扫描，六个通道：

| 通道 | 方法 | 命中 |
|---|---|---|
| C1 | CryptoJS `Utf8/Hex/…parse("<payload>")` | 1 |
| C2 | 裸 16/24/32 字节 hex 常量（按上下文分类） | 17 处 → 3 处密码学绑定 |
| C3 | 二进制中 key 语义 C 字符串 | 264 |
| C4 | 字符串 section 内恰好 16 字节 ASCII 串 | 146（候选池，非密钥判定） |
| C5 | `.bundle` 资源目录 | 2 |
| C6 | 高熵 Base64 内嵌常量（独立 NUL 串 + 非标识符形态） | 2（同值） |

**阳性对照 3/3 PASS**：`385f…ab7`（文本通道）、`cw_test_aes_key_`、
`cw_test_sm4_key_`（二进制通道）均被找回——这是阴性结论可信的前提。

**结果**：

| 值 | 形态 | 实例数 | 语义 |
|---|---|---|---|
| `385f33cb…9081ab7` | 32 hex（AES-256） | **4**（3 处代码 + 1 处 parse） | 登录/改密三字段加密 |
| `adQOeq…ugF5C`（48 B） | Base64 | **2**（二进制两处同值） | 未证（§4.2） |

### 5.1 本轮排除的假阳性（方法留痕）

诚实记录三个**一度被误判、后经反向验证排除**的候选，它们说明为什么本报告
不直接采信「扫描命中数」：

| 候选 | 为何像密钥 | 如何被排除 |
|---|---|---|
| `p__home__Zone.js` 中 6 个 `ff80808178ef68ae…` / `6c13c9b1…` 32-hex | 32 hex，长度与 AES-256 密钥一致 | 上下文是 `id:"…"` 紧跟 `title`/`des`/`icon`/`url` 的**业务卡片数据**——是政务系统业务记录 ID。首版分类器因子串 `des` 命中 JSX 属性名 `des:` 而误判为「密码学绑定」，已改为词边界匹配 |
| 主二进制 @2444880 `h%D-j-E-l5F-n=G-` | 恰好 16 个可打印字节，熵 3.27，四类字符齐全 | 前后字节为 `\xa0\x83\x11\xbc` / `\xeb_@\xf9`，是 **AArch64 指令编码**——`__text` 指令流被误读成 ASCII。已加「必须落在字符串 section」约束 |
| 55 个「高熵 Base64」候选 | 解码后熵最高达 5.06 | 解码后是 ObjC 选择子（如 `URLSessionDidFinishEventsForBackgroundURLSessionCompletionHandler`）、框架路径、编码字母表。已加「独立 NUL 分隔串 + 非合法标识符形态」约束。**熵不是判据，可读性才是** |
| `aes256EncryptWithKey:data:`（@3885487） | 方法名直指 AES 加密 | 归属类为 **BLYHelper**（腾讯 Bugly 崩溃上报 SDK，`otool -oV` 类归属可查），非本应用加密面。**不主张为失范** |

---

## 6. 明确不主张的事项

以下各项经审查后**不构成本报告的缺陷主张**，列出以防夸大：

1. **「无加固壳」本身不是缺陷**。OWASP MASVS 原文明确：纵深防御措施（含代码
   混淆）的缺失 "does not in itself constitute a vulnerability"，且
   "measures like string encryption, debugger detection or control flow obfuscation
   aren't considered mandatory"。本 App 无壳，**不构成 MASVS 违规**。
   （若以 MAS-R profile 评估，对应 MASWE-0059「Code Obfuscation Not Implemented」
   这一**弱点条目**，而非控制项失败。）
2. **明文 HTTP 端点 `http://36.112.134.71:38888` 不是生产地址**。它是配置对象
   `{url:"https://ywtb.mps.gov.cn/mobileBack", testurl:"http://36.112.134.71:38888",
   produrl:"https://ywtb.mps.gov.cn"}` 中的 **`testurl`** 字段。生产走 `url`/`produrl`
   的 HTTPS。**本报告不主张生产流量走明文 HTTP。**
   保留的主张仅为：**测试端点随生产包发布，且 ATS 全局关闭使其可被实际使用**。
3. **48 字节密钥材料的用途未证**（§4.2）。
4. **`cn.sinobest` 与公安部科技信息化局的关系未认定**（§7）。
5. **未主张任何「已被攻击/已被利用」的事实**。本报告只陈述静态可复算的代码事实。
6. **未主张 `Assets.car`、`.mnn` 模型文件内的内容**——未解包，不构成任何主张依据。
7. **未做运行期观测**。本报告全部为静态证据；运行期行为（实际网络请求、实际
   密钥取用）未观测，亦不作为主张依据。

---

## 7. 责任主体

| 层面 | 事实 | 来源 |
|---|---|---|
| 上架主体 | seller = Science and Technology Information Bureau of the Public Security Ministry of China；artistName = 公安部科技信息化局 | App Store lookup API（trackId 1597440048） |
| 签名主体 | team-identifier `JWX2DN7S4Z`；application-identifier `JWX2DN7S4Z.cn.sinobest.gaywtb` | 主二进制内嵌 entitlements（@4570040） |
| 命名空间 | `cn.sinobest` → 北京中科江南信息技术股份有限公司（创业板上市） | bundleId 前缀 |
| 厂商 SDK | 云从科技（CloudWalk）活体检测 SDK（`cw_*` 符号族、`CWResource.bundle`、`/Users/cloudwalk/…` 构建路径） | 二进制符号与路径 |
| 崩溃上报 SDK | 腾讯 Bugly（`BLY*` 类族） | 二进制类名 |

### 待共同确认（本报告不裁断）

1. **北京中科江南与公安部科技信息化局的具体关系**：开发承建方？运维方？仅
   bundleId 命名空间复用？公开材料未直接载明。本报告**不据此归责**。
2. **H5 层代码的实际编写方**：`www/umi.js` 内含构建期泄漏的路径
   `/Users/wulingjie/IdeaProjects/gazwfw/fwmh/fwmh_mobile_umi/…`（@17436 附近），
   该路径与 `sinobest`、`cloudwalk` 命名空间均不同。本报告仅记录该事实，
   **不主张其归属**。
3. **主二进制内另有第三方开发者路径** `/Users/zhangdanfeng/workspace/dpnet-ios…`
   （深度学习推理引擎 MNN 分支）——属供应链构成事实，不主张责任。

---

## 8. 开放问题

| # | 问题 | 为何未答 |
|---|---|---|
| 1 | 48 字节密钥材料用于加密什么？ | `adrp+add` 交叉引用零命中，静态无法确定取用点；需运行期观测 |
| 2 | 云从 native 组件是否使用正式密钥（而非仅测试钥回退）？ | 其 API 为参数化设计（`cw_aes_encodeContent:forKey:`），正式钥由调用方传入，不在 SDK 常量中 |
| 3 | 服务端是否确实按 `encryption:"1"` 解密？ | 需服务端行为，超出静态分析边界 |
| 4 | 其他版本（<1.2.28 或后续版本）是否同样？ | 本报告只对 SHA-256 `d46aaec3…f3ad` 负责 |

---

## 9. 复现指南（仅用公开工具）

前置：取得 SHA-256 为 `d46aaec36700a85b5d1a14834d46e645e145149c8416d94aa294b5975f84f3ad`
的同一 IPA。**先核对指纹**，不符则本报告结论不适用。

### 9.1 主张 A1 / A2（硬编码密钥 + 两条链）

```bash
# 解包
unzip -q cn.sinobest.gaywtb-1.2.28-Decrypted.ipa -d out/
APP="out/Payload/公安一网通办.app"

# 密钥的 3 处代码实例。
# 注意：必须用 grep -o | wc -l 统计「出现次数」，不能用 grep -c ——
# 压缩后的 umi.js 整个文件只有一行，grep -c 数的是行数，会恒为 1。
echo -n "Login.js: "; grep -o "385f33cb…9081ab7" \
    "$APP/www/p__login__Login.js" | wc -l    # 期望 1
echo -n "umi.js:   "; grep -o "385f33cb…9081ab7" \
    "$APP/www/umi.js" | wc -l                # 期望 2

# 加密函数与 ECB 模式（应看到 mode:...ECB 与 padding:...Pkcs7）
grep -o 'Utf8.parse("385f33cb…9081ab7")[^;]*' \
     "$APP/www/p__login__Login.js"

# 链一：登录端点
grep -o '/api/fwmh/mobile/login' "$APP/www/umi.js"
# 链二：改密端点 + 三字段加密
grep -o '/api/user/password' "$APP/www/umi.js"
grep -o 'o\.phone=Y(c)),l&&(o\.validateCode=Y(l)),d&&(o\.password=Y(d))' "$APP/www/umi.js"
# 改密页面入口
grep -o 'grzx/changePass' "$APP/www/p__grzx__Xgmm.js"
```

### 9.2 主张 A3（ATS 全局关闭）

```bash
plutil -p "$APP/Info.plist" | grep -A3 NSAppTransportSecurity
# 期望：{ "NSAllowsArbitraryLoads" => 1 }，且无 NSExceptionDomains
```

### 9.3 主张 A4 / A5（二进制内密钥材料）

```bash
BIN="$APP/公安一网通办"

# A4：测试密钥（偏移应为 3735557 / 3735574）
grep -abo 'cw_test_aes_key_' "$BIN"
grep -abo 'cw_test_sm4_key_' "$BIN"

# A5：48 字节 Base64 材料（应两处命中，偏移 3793688 / 3794402）
grep -abo 'adQOeqjWNAU1rJTSpts/zvk367Eb2ZmLVi8n+hHPYG9cxlDw0IMKoyfR4BXugF5C' "$BIN"

# 解码与熵核算
python3 - <<'EOF'
import base64, collections, math
s = "adQOeqjWNAU1rJTSpts/zvk367Eb2ZmLVi8n+hHPYG9cxlDw0IMKoyfR4BXugF5C"
d = base64.b64decode(s)
c = collections.Counter(d); n = len(d)
print("bytes:", len(d))
print("entropy:", -sum((v/n)*math.log2(v/n) for v in c.values()))
print("hex:", d.hex())
EOF
```

### 9.4 密钥普查全量复算（可选，需脚本）

本报告 §5 的普查由一个六通道脚本完成，逻辑与阈值全部写在脚本注释里
（含阳性对照与三处假阳性过滤的由来）。脚本不随本报告分发——本报告刻意只
分发**结论与可手工复算的偏移**，以便任何第三方用 `grep`/`plutil` 独立核对
而不必信任我们的代码。

---

## 10. 引用规范

引用本报告时请：
1. 注明所核验样本的 **SHA-256**（`d46aaec3…f3ad`）与版本（1.2.28）；
2. 区分**本报告的主张**与**被引规范的主张**——尤其注意 §2.4、§4.1 标注的
   「引用边界」；
3. 不得将 §6「明确不主张的事项」中的任何一条改写成缺陷主张。

---

## 11. 版本

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0 | 2026-10-25 | 首版 |

---

**本报告为独立静态安全调查，基于公开可获取的样本与公开规范文献。报告中的每一
主张均给出可复算的文件与字节偏移。报告作者与所涉任何主体无利益关联。**
