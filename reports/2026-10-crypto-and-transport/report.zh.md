# 公安一网通办（cn.sinobest.gaywtb v1.2.28）密码学使用与传输安全调查报告

**独立静态安全调查 · 报告自包含 · 全部主张可用公开工具复算**

---

## 一句话总结

一款由公安部科技信息化局在 App Store 上架的部级政务服务应用，把一把 **AES-256
密钥以明文硬编码在应用包内**，并用 **ECB 工作模式**加密用户的**登录密码、手机号、
验证码**；同一把密钥同时服务**登录、重置密码、修改密码**三个业务入口；应用
**全局关闭了 iOS 的传输层安全强制（ATS）**；包内另含云从 SDK **自述的"测试密钥"**。
以上每一条都落到可复算的代码位置。

---

## 调查对象身份（引用本报告结论前请先核对指纹）

| 项 | 值 |
|---|---|
| 官方名称 | 公安一网通办（`CFBundleDisplayName` 直读） |
| Bundle ID / 版本 | `cn.sinobest.gaywtb` / `CFBundleShortVersionString` **1.2.28**（`CFBundleVersion` 2） |
| App Store | trackId **1597440048**，seller **Science and Technology Information Bureau of the Public Security Ministry of China**，artistName **公安部科技信息化局**，2021-12-06 上架，当前版本 2023-11-20 |
| 签名主体 | `TeamIdentifier=JWX2DN7S4Z`；entitlements `application-identifier` = `JWX2DN7S4Z.cn.sinobest.gaywtb` |
| 签名证书链 | `Apple iPhone OS Application Signing` ← `Apple iPhone Certification Authority` ← `Apple Root CA`（**Apple 分发签名，非开发者自签**；证书有效期 2023-05-09 至 2025-06-07） |
| CDHash | `f5f3dbaf479ff6ec909b0ebccfd296c49d0d4e2e` |
| **IPA SHA-256** | `d46aaec36700a85b5d1a14834d46e645e145149c8416d94aa294b5975f84f3ad` |
| IPA 字节数 | 64,281,491 |
| 主二进制 | `Payload/公安一网通办.app/公安一网通办`，4,659,328 B（arm64 thin） |
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
| **A1** | 一把 **AES-256 密钥明文硬编码在 H5 层**，用于加密用户的**登录密码、手机号、验证码**；工作模式 **ECB**（无 IV） | **代码级实证**（纯文本 JS，逐行可读） | NIST SP 800-38A §6.1（确定性） |
| **A2** | 同一把密钥服务**三个业务入口**：登录（`/api/fwmh/mobile/login`，加密 password）、重置密码与修改密码（`/api/user/password`，加密三字段） | **代码级实证**（逐 effect 核对调用与端点） | 同上 |
| **A3** | 应用**全局关闭 ATS**（`NSAllowsArbitraryLoads = true`），无任何域名例外白名单 | **配置级实证**（Info.plist 直读） | Apple ATS 官方文档 |
| **A4** | 包内含云从 SDK **自述测试密钥** `cw_test_aes_key_` / `cw_test_sm4_key_`，且被 `checkKey:` **实际取用** | **指令级实证**（xref 经 `__cfstring` 中转，阳性对照 PASS） | NIST SP 800-57 §8.1.4「测试密钥材料不得用于生产」 |

**明确不主张的事项**（防夸大，完整清单见 §6）：本 App 无加固壳本身不是缺陷；
明文 HTTP 端点 `36.112.134.71:38888` 是配置中的测试地址而非生产地址；
`cn.sinobest` 与公安部的关系未认定；不主张任何「已被攻击/已被利用」的事实。

> **本报告撤回的一条**：本报告早期草稿曾把二进制中一处 64 字符 Base64 串列为
> 「48 字节密钥材料」。经反汇编核实，它是 **Base64 编码器的查表字母表**，不是密钥。
> 详见 §5.2。

---

## 1. 调查方法与证据等级

本报告对每条主张标注证据等级，取自公开可复算的静态证据：

| 等级 | 含义 | 本报告是否使用 |
|---|---|---|
| L1 串在场 | 字符串/常量存在于包内 | 用于 A4 的定位 |
| L2 符号在场 | 符号表/导出面存在 | 未单独使用 |
| L3 指令级 | 反汇编调用链（取址指令 + 调用点地址） | 用于 A4 的「实际取用」 |
| **L3′ 代码级（H5）** | **纯文本 JS 源码中的函数定义、调用点、网络端点** | **用于 A1、A2** |
| L4 配置级 | 配置文件直读 | 用于 A3 |

> **为什么 A1/A2 用 L3′ 而非 L3**：本 App 是 Cordova 混合架构，登录/重置/改密的
> 加密逻辑**全部在 `www/` 下的纯文本 JavaScript 中**，无混淆、无字节码。对这类目标，
> 读源码比反汇编更直接、更可复核——第三方用文本编辑器与 `grep` 即可独立验证。

### 1.1 方法纪律（本报告实际执行）

1. **每条主张给出文件 + 偏移 + 期望字节**，偏移均为文件内字节偏移；
2. **阳性对照**：任何「阴性/计数型」结论都先证明工具没坏。密钥普查内置三个已知钥
   作对照（3/3 PASS）；字符串交叉引用扫描内置已知被引用的串作对照（2/2 PASS）。
   **找不回已知项即判工具失明、结论作废**；
3. **噪声基线**：计数型主张先算背景基线（见 §5.2 的熵陷阱）；
4. **最强替代假说必须被排除**：A1 的「这是 SSL pinning 而非加密」已逐特征排除（§2.4）。

> **为什么把工具自检写进方法节**：本轮实际踩到两次「工具静默失明」——扫描器
> 返回「0 个引用」，看起来像一个有力的阴性结论，实际是工具漏了两类取址形态。
> 详见 §5.3。**阴性结论的价值完全取决于工具是否被证明过能看见东西。**

---

## 2. 主张 A1 / A2：硬编码 AES-256-ECB 密钥

### 2.1 密钥与加密函数

文件 `Payload/公安一网通办.app/www/p__login__Login.js`，字节偏移 **9465**：

```js
Q = e => {
  var r = O.a.enc.Utf8.parse("385f33cb…9081ab7"),
      o = O.a.AES.encrypt(e, r, {mode: O.a.mode.ECB, padding: O.a.pad.Pkcs7});
  return o.ciphertext.toString()
}
```

- `Utf8.parse` 传入 **32 个 ASCII 字符** ⇒ 32 字节密钥材料 ⇒ CryptoJS 按密钥长度
  自动选择 **AES-256**（CryptoJS 官方文档：「It will pick the variant by the size
  of the key you pass in」）；
- `mode: ECB` ⇒ **无 IV**，同一明文在同一密钥下**恒定产生同一密文**。

**同一把密钥在包内共 3 处代码实例**（全包普查，非抽样）：

| # | 文件 | 字节偏移 | 所在位置 | 服务的功能 |
|---|---|---|---|---|
| 1 | `www/p__login__Login.js` | 9485（+9465 `Utf8.parse`） | 登录页组件函数 `Q` | **登录**（加密 password） |
| 2 | `www/umi.js` | **423347** | `namespace:"login"` 内函数 `S` | **重置密码**（加密三字段） |
| 3 | `www/umi.js` | **769557** | `namespace:"grzx"` 内函数 `Y` | **修改密码**（加密三字段） |

### 2.2 三个业务入口（A2）

**入口一 · 登录（只加密 password 一个字段）**

```
www/index.html                      <script src="./umi.js">
 └ umi.js 路由表                     {path:"/login", loader: 懒加载 p__login__Login chunk 族}
    └ p__login__Login.js @12194/@13769   onClick:X（两个「登录」按钮）
       └ @9617  X = () => { … }
          └ o.password = Q(o.password)          ← 只加密 password
             └ g({type:"login/tryLogin", payload:{…o, loginType:E, commonlyEnable:"1", …}})
                └ umi.js  effect tryLogin → service s
                   └ umi.js @420661   POST /api/fwmh/mobile/login
```

> **此处一个容易搞错的地方**：`login` model 里的 `tryLogin` effect **不加密**，
> 它把 payload 原样透传给 service（`i(s, r)`）。加密发生在**组件层**的 `X` handler。
> 本报告早期草稿曾误以为加密在框架层、且加密三字段——已更正（§5.4）。

**入口二 · 重置密码（加密三字段）**

```
umi.js  namespace:"login"  effect resetPossword @425347
 └ c && (o.phone = S(c)),  l && (o.validateCode = S(l)),  d && (o.password = S(d))
    o = {...o, encryption:"1"}                    ← 显式加密模式标记
    └ s(y, o)  → service y → @422451   POST /api/user/password
```

**入口三 · 修改密码（加密三字段）**

```
www/p__grzx__Xgmm.js @10827   dispatch({type:"grzx/changePass",
                                       payload:{phone, validateCode, password, type:"chg"}})
 └ umi.js  namespace:"grzx"  effect changePass @771557
    └ c && (o.phone = Y(c)),  l && (o.validateCode = Y(l)),  d && (o.password = Y(d))
       o = {...o, encryption:"1"}
       └ s(m, o)  → service m → POST /api/user/password
```

页面可达性：chunk 表 `39:"p__grzx__Xgmm"`（`umi.js` @2264），`p__grzx__Xgmm.js`
在场（93,867 B）。

**`encryption:"1"` 的含义**：三个加密入口中，后两个在请求体里显式携带该标记。
这表明**服务端按约定识别并解密该模式**——即「客户端藏钥」是该应用的**设计选择**，
不是工程疏漏或残留代码。

### 2.3 密钥的公开性

需要区分两件事：
- **本报告已证**：密钥以明文存在于随包发布的应用资源中，任何取得该 IPA 的人可在
  数秒内读出；
- **本报告不主张**：「已在真实攻击中被利用」。密钥自 2021-12 首个版本起即随每个
  安装包公开，这是**公开性**事实，不是**被利用**事实。

### 2.4 最强替代假说已排除：这不是 SSL pinning

| 判别维度 | 若为 pinning 应见 | 本 App 实测 |
|---|---|---|
| 被验值的去向 | 参与比对（memcmp / 哈希比较），**永不进入密钥编排** | 直接作为 `AES.encrypt` 的**密钥参数** |
| 输出形态 | 布尔值 / 抛错 | `o.ciphertext.toString()` —— **产出密文** |
| IV | 不涉及 | ECB 无 IV（`mode:ECB` 写在代码里） |
| 请求标记 | 无 | `encryption:"1"` 显式声明加密模式 |

### 2.5 ECB 的具体后果

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

1. **同一密码在不同用户、不同时间登录时，产生的密文完全相同**——服务端日志、
   网络中间设备、任何能看到密文的一方，都可直接判断「这两个账号用了同一个密码」；
2. **手机号**同样处理，且取值空间小（号段+号），可被字典穷举反推；
3. **密钥公开后**（§2.3），ECB 的确定性使「已知明文攻击」不再需要任何密码学投入；
4. **密码重置/修改链路把新密码也用同一把公开钥加密**——攻击者若截获该请求，
   可直接得到用户设置的新密码。

> **引用边界（必须一并声明）**：SP 800-38A 在印刷页 1 自述
> "neither a standard nor a guideline, and as such, is neither mandatory nor binding
> on Federal agencies"。**它是建议性文献**。本报告因此只写「NIST 建议 ECB 在此类
> 场景下不应使用」，**不写「违反 NIST 标准」**。
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
`NSAllowsArbitraryLoads=true` 一个键，**没有** `NSExceptionDomains` 白名单。
意味着该应用**任何**明文 HTTP 连接都不会被系统拦截。

Apple 官方文档原文：

> "ATS requires that all HTTP connections made with the URL Loading System—typically
> using the URLSession class—use HTTPS."（NSAppTransportSecurity — Discussion）
>
> "App Transport Security has blocked a cleartext HTTP (http://) resource load since
> it is insecure. Temporary exceptions can be configured via your app's Info.plist
> file."（Preventing Insecure Network Connections）

**与 A1/A2 的叠加效应**：即使登录/重置/改密的密文被中间人截获，由于密钥在包内
公开（§2.3）、模式为 ECB（§2.5），攻击者可直接解密或重放。ATS 关闭使这条路径
**不需要任何证书伪造**即可实施。

---

## 4. 主张 A4：包内的厂商自述测试密钥

主二进制 `Payload/公安一网通办.app/公安一网通办`，`__TEXT,__cstring` 区：

| 值 | 字节偏移 | 长度 |
|---|---|---|
| `cw_test_aes_key_` | **3735557** | 16 B |
| `cw_test_sm4_key_` | **3735574** | 16 B |

### 4.1 它们确实被代码取用（指令级）

不只「串在场」，而是被 `checkKey:encryptStyle:` 实际取用。取用路径经
`__DATA,__cfstring` 中转：

```
0x100170868   adrp x1, 0x1003f0000 ; add x1, #0x748   → __cfstring @0x1003f0748
                                                          └ +16 → 0x100390005 = "cw_test_aes_key_"
0x100170884   adrp x1, 0x1003f0000 ; add x1, #0x768   → __cfstring @0x1003f0768
                                                          └ +16 → 0x100390016 = "cw_test_sm4_key_"
```

两个分支都在 `-[CWDataProcessUtil checkKey:encryptStyle:]`（IMP 0x100170808）内，
形态为「若当前钥为空则装载该测试钥」的回退逻辑。

### 4.2 为什么这构成问题

NIST SP 800-57 Part 1 Rev. 5 §8.1.4（印刷页 92）原文：

> "Many applications or systems are provided by the manufacturer with keying material
> that is used to test that the newly installed application/system is functioning
> properly. **This test keying material shall not be used operationally.**"

**测试钥随生产包发布**，且代码保留了一条「装载测试钥」的回退路径——这与上述
要求直接相关。串名自带 `test` 是厂商自己的标注，不是本报告的推断。

> **引用边界**：SP 800-57 是**美国联邦密钥管理指引**，不是移动应用安全标准，
> 也不针对 iOS。它**没有**、本报告也不声称它有一条「禁止在源码中硬编码密钥」的
> 条文（该文件全文 `hardcod` / `source code` / `compil*` 均零命中）。
> 本报告引用它**只为一件事**：其 §8.1.4 明确指出测试密钥材料不得用于生产。

---

## 5. 密钥普查与假阳性记录

### 5.1 普查结果：1 个不同值 / 4 个实例

**普查口径**（可复算）：IPA 全部 **1013 个成员**逐字节扫描，六个通道：

| 通道 | 方法 | 命中 |
|---|---|---|
| C1 | CryptoJS `Utf8/Hex/…parse("<payload>")` | 1 |
| C2 | 裸 16/24/32 字节 hex 常量（按上下文分类） | 17 处 → 3 处密码学绑定 |
| C3 | 二进制中 key 语义 C 字符串 | 264（绝大多数是 SDK 的 key 路径/属性名，非密钥值） |
| C4 | 字符串 section 内恰好 16 字节 ASCII 串 | 146（候选池，**不构成密钥判定**） |
| C5 | `.bundle` 资源目录 | 2（CWResource=纯图片/模型，无钥） |
| C6 | 高熵 Base64 内嵌常量 | **0**（首版曾误报 2，见 §5.2） |

**阳性对照 3/3 PASS**：`385f…ab7`（文本通道）、`cw_test_aes_key_`、
`cw_test_sm4_key_`（二进制通道）均被找回——这是阴性结论可信的前提。

**结果**：全包**只有 1 个不同的密钥值**（`385f33cb…9081ab7`），
**4 个实例**（3 处代码 + 1 处 `Utf8.parse` 调用参数）。

### 5.2 撤回：那个 64 字符 Base64 串不是密钥

本报告早期草稿把主二进制 @3793688/@3794402 的

```
adQOeqjWNAU1rJTSpts/zvk367Eb2ZmLVi8n+hHPYG9cxlDw0IMKoyfR4BXugF5C
```

列为「48 字节 Base64 密钥材料（熵 5.543 bit/byte）」。**这是错的，撤回。**

**反汇编证据**（0x1003291cc / 0x10032926c / 0x1003292c0）：

```asm
adr   x25, literal pool for "adQOeqjWNAU1rJTSpts/zvk367Eb2ZmLVi8n+hHPYG9cxlDw0IMKoyfR4BXugF5C"
ldrb  w28, [x26, #0x1]
ldrb  w21, [x26]
lsr   x8, x21, #2
ldrsb w1, [x25, x8]              ← 6-bit 分组索引查表
bl    basic_string::push_back
...
adr   x1, literal pool for "="   ← Base64 补位串
adr   x1, literal pool for "=="
```

配合 `lsr #2` / `lsr #4` / `lsr #6` + `and #0x3f` 的 6-bit 分组——这是**标准
Base64 编码器**。该串 64 个字符与 `A-Za-z0-9+/` **完全同集**（仅顺序不同，
用于打乱编码输出）。

**为什么熵会骗人**：把 64 个互异字符当 Base64 解码，必然得到伪随机字节
（熵 5.5 左右）。**熵高是「解码一个字母表」的数学必然，不是随机性证据。**

### 5.3 工具的两个静默失明（本轮踩到并修复）

判断「字符串是否真被代码取用」时，手写的 `adrp+add` 扫描器有两个失败模式：

| 失明模式 | 表现 | 实测 |
|---|---|---|
| 漏 `__cfstring` 中转 | ObjC `@"..."` 先指向 `__DATA,__cfstring` 结构（+16 字符串指针 / +24 长度），再指向 `__cstring`。只找直接命中的扫描器对 ObjC 字符串**全部报 0** | `cw_test_aes_key_` 确实被 `checkKey:` 取用（0x100170868），直接扫描却报 0 |
| 漏 `adr` 单条取址 | 小范围取址编译器用单条 `adr`，不拆 adrp+add | Base64 表三处取用全是 `adr` |

**教训**：`0 个引用` 是最危险的阴性结论形态——**工具坏了和结论成立长得一模一样**。
修复后的扫描器**强制阳性对照**，找不回已知被引用的串就退非零、不出结论。

**用可信工具得到的阴性结论**：登录钥 `385f…ab7` 在主二进制中 **NOT FOUND**
（对照 PASS）——与「密钥只在 H5 层」一致。

### 5.4 其他被排除的假阳性

| 候选 | 为何像密钥 | 如何被排除 |
|---|---|---|
| `p__home__Zone.js` 中 6 个 `ff80808178ef68ae…` / `6c13c9b1…` 32-hex | 长度与 AES-256 密钥一致 | 上下文是 `id:"…"` 紧跟 `title`/`des`/`icon`/`url` 的**业务卡片数据**——政务系统业务记录 ID。首版分类器因子串 `des` 命中 JSX 属性名 `des:` 而误判 |
| 主二进制 @2444880 `h%D-j-E-l5F-n=G-` | 恰好 16 个可打印字节，熵 3.27，四类字符齐全 | 前后字节为 `\xa0\x83\x11\xbc` / `\xeb_@\xf9`，是 **AArch64 指令编码**——`__text` 指令流被误读成 ASCII |
| 55 个「高熵 Base64」候选 | 解码后熵最高达 5.06 | 解码后是 ObjC 选择子（如 `URLSessionDidFinishEventsForBackgroundURLSessionCompletionHandler`）、框架路径。**熵不是判据，可读性才是** |
| `aes256EncryptWithKey:data:`（@3885487） | 方法名直指 AES 加密 | 归属类为 **BLYHelper**（腾讯 Bugly 崩溃上报 SDK，`otool -oV` 类归属可查），非本应用加密面 |

---

## 6. 明确不主张的事项

以下各项经审查后**不构成本报告的缺陷主张**，列出以防夸大：

1. **「无加固壳」本身不是缺陷**。OWASP MASVS 原文明确：纵深防御措施（含代码混淆）
   的缺失 "does not in itself constitute a vulnerability"，且
   "measures like string encryption, debugger detection or control flow obfuscation
   aren't considered mandatory"。本 App 无壳，**不构成 MASVS 违规**。
   （若以 MAS-R profile 评估，对应 MASWE-0059「Code Obfuscation Not Implemented」
   这一**弱点条目**，而非控制项失败。）
2. **明文 HTTP 端点 `http://36.112.134.71:38888` 不是生产地址**。它是配置对象
   `{url:"https://ywtb.mps.gov.cn/mobileBack", testurl:"http://36.112.134.71:38888",
   produrl:"https://ywtb.mps.gov.cn"}` 中的 **`testurl`** 字段。生产走 `url`/`produrl`
   的 HTTPS。**本报告不主张生产流量走明文 HTTP。**
   保留的主张仅为：**测试端点随生产包发布，且 ATS 全局关闭使其可被实际使用**。
3. **`cn.sinobest` 与公安部科技信息化局的关系未认定**（§7）。
4. **未主张任何「已被攻击/已被利用」的事实**。本报告只陈述静态可复算的代码事实。
5. **未主张 `Assets.car`、`.mnn` 模型文件内的内容**——未解包，不构成任何主张依据。
6. **未做运行期观测**。本报告全部为静态证据；运行期行为（实际网络请求、实际密钥
   取用）未观测，亦不作为主张依据。
7. **不主张云从 native 组件使用正式密钥**。其 API 为参数化设计
   （`cw_aes_encodeContent:forKey:`），正式钥由调用方传入，不在 SDK 常量中。

---

## 7. 责任主体

| 层面 | 事实 | 来源 |
|---|---|---|
| 上架主体 | seller = Science and Technology Information Bureau of the Public Security Ministry of China；artistName = 公安部科技信息化局 | App Store lookup API（trackId 1597440048） |
| 签名主体 | `TeamIdentifier=JWX2DN7S4Z`；application-identifier `JWX2DN7S4Z.cn.sinobest.gaywtb` | `codesign -dvvv` + 内嵌 entitlements（@4570040） |
| 命名空间 | `cn.sinobest` → 北京中科江南信息技术股份有限公司（创业板上市） | bundleId 前缀 |
| 厂商 SDK | 云从科技（CloudWalk）活体检测 SDK（`cw_*` 符号族、`CWResource.bundle`、`/Users/cloudwalk/…` 构建路径） | 二进制符号与路径 |
| 崩溃上报 SDK | 腾讯 Bugly（`BLY*` 类族） | 二进制类名 |

### 待共同确认（本报告不裁断）

1. **北京中科江南与公安部科技信息化局的具体关系**：开发承建方？运维方？仅
   bundleId 命名空间复用？公开材料未直接载明。本报告**不据此归责**。
2. **H5 层代码的实际编写方**：`www/umi.js` 内含构建期泄漏的路径
   `/Users/wulingjie/IdeaProjects/gazwfw/fwmh/fwmh_mobile_umi/…`，该路径与
   `sinobest`、`cloudwalk` 命名空间均不同。本报告仅记录该事实，**不主张其归属**。
3. **主二进制内另有第三方开发者路径** `/Users/zhangdanfeng/workspace/dpnet-ios…`
   （深度学习推理引擎 MNN 分支）——属供应链构成事实，不主张责任。

---

## 8. 开放问题

| # | 问题 | 为何未答 |
|---|---|---|
| 1 | 服务端是否确实按 `encryption:"1"` 解密？ | 需服务端行为，超出静态分析边界 |
| 2 | 云从 native 组件在生产中是否传入正式密钥？ | API 为参数化设计，正式钥由调用方传入，静态不可见 |
| 3 | 其他版本（<1.2.28 或后续版本）是否同样？ | 本报告只对 SHA-256 `d46aaec3…f3ad` 负责 |
| 4 | 三个入口是否共用同一服务端密钥？ | 同一把客户端钥已证；服务端侧未知 |

---

## 9. 复现指南（仅用公开工具）

前置：取得 SHA-256 为 `d46aaec36700a85b5d1a14834d46e645e145149c8416d94aa294b5975f84f3ad`
的同一 IPA。**先核对指纹**，不符则本报告结论不适用。

### 9.1 主张 A1 / A2（硬编码密钥 + 三个入口）

```bash
unzip -q cn.sinobest.gaywtb-1.2.28-Decrypted.ipa -d out/
APP="out/Payload/公安一网通办.app"

# 密钥的 3 处代码实例。
# 注意：必须用 grep -o | wc -l 统计「出现次数」，不能用 grep -c ——
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

### 9.2 主张 A3（ATS 全局关闭）

```bash
plutil -p "$APP/Info.plist" | grep -A3 NSAppTransportSecurity
# 期望：{ "NSAllowsArbitraryLoads" => 1 }，且无 NSExceptionDomains
```

### 9.3 主张 A4（测试密钥及其取用）

```bash
BIN="$APP/公安一网通办"

# 串在场（偏移应为 3735557 / 3735574）
grep -abo 'cw_test_aes_key_' "$BIN"
grep -abo 'cw_test_sm4_key_' "$BIN"

# 取用点：两条 adrp+add 指向 __DATA,__cfstring 结构。
# 注意：otool -tV 会把这两个 CFString 显示成 @"bad cfstring ref"（未重定位），
# 所以必须自己解 __cfstring 结构（+16 = 字符串指针，+24 = 长度）才能看到真值。
otool -tV "$BIN" | grep -A1 '^0000000100170868\|^0000000100170884'
# 期望：adrp x1, 0x1003f0000 ; add x1, x1, #0x748（@0x100170868）
#       adrp x1, 0x1003f0000 ; add x1, x1, #0x768（@0x100170884）

# 解 __cfstring 结构，确认两个分支各自指向哪把测试钥
python3 - "$BIN" <<'EOF'
import struct, sys
d = open(sys.argv[1], 'rb').read()
ncmds = struct.unpack("<I", d[16:20])[0]; off = 32; secs = []
for _ in range(ncmds):
    cmd, cmdsize = struct.unpack("<II", d[off:off+8])
    if cmd == 0x19:
        ns = struct.unpack("<I", d[off+64:off+68])[0]; so = off + 72
        for _s in range(ns):
            sn = d[so:so+16].rstrip(b'\0').decode('ascii','replace')
            sg = d[so+16:so+32].rstrip(b'\0').decode('ascii','replace')
            a  = struct.unpack("<Q", d[so+32:so+40])[0]
            z  = struct.unpack("<Q", d[so+40:so+48])[0]
            fo = struct.unpack("<I", d[so+48:so+52])[0]
            secs.append((sg, sn, a, z, fo)); so += 80
    off += cmdsize
def fo_of(va):
    for sg, sn, a, z, f in secs:
        if z > 0 and a <= va < a + z:
            return f + (va - a)
for va in (0x1003f0748, 0x1003f0768):          # checkKey: 的两个分支
    fo = fo_of(va)
    sp = struct.unpack("<Q", d[fo+16:fo+24])[0]
    ln = struct.unpack("<Q", d[fo+24:fo+32])[0]
    print(hex(va), "->", d[fo_of(sp):fo_of(sp)+ln])
EOF
# 期望输出：
#   0x1003f0748 -> b'cw_test_aes_key_'
#   0x1003f0768 -> b'cw_test_sm4_key_'
```

### 9.4 复核 §5.2 的撤回（确认那串是 Base64 字母表）

```bash
python3 - <<'EOF'
s = b"adQOeqjWNAU1rJTSpts/zvk367Eb2ZmLVi8n+hHPYG9cxlDw0IMKoyfR4BXugF5C"
std = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")
print("len:", len(s), "distinct:", len(set(s)))
print("charset == standard base64 alphabet:", set(s) == std)
EOF
# 期望：len 64，distinct 64，charset == True ⇒ 是字母表，不是密钥

otool -tV "$BIN" | grep -A2 'adQOeq'
# 期望：adr x25, literal pool for "adQOeq…" 后接 ldrsb 查表 + push_back
```

---

## 10. 引用规范

引用本报告时请：
1. 注明所核验样本的 **SHA-256**（`d46aaec3…f3ad`）与版本（1.2.28）；
2. 区分**本报告的主张**与**被引规范的主张**——尤其注意 §2.5、§4.2 标注的
   「引用边界」；
3. 不得将 §6「明确不主张的事项」中的任何一条改写成缺陷主张；
4. 不得引用本报告**已撤回**的内容（§5.2）。

---

## 11. 版本

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0 | 2026-10-25 | 首版 |
| 1.1 | 2026-10-25 | **撤回 A5**（64 字符串是 Base64 字母表，非密钥）；**修正 A2**（三字段加密属重置/修改密码，登录只加密 password）；补签名证书链与 CDHash；补 A4 的指令级取用证据；新增 §5.3 工具静默失明记录 |

---

**本报告为独立静态安全调查，基于公开可获取的样本与公开规范文献。报告中的每一
主张均给出可复算的文件与字节偏移。报告作者与所涉任何主体无利益关联。**
