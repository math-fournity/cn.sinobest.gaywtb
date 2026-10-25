# ECB 跨端普查：两家互不相关的公司，同一个教科书级错误

> 这是本报告**最重要的发现**，也是与 Android 篇
> [cn.cyberIdentity.certification](https://github.com/math-fournity/cn.cyberIdentity.certification)
> 合起来才看得出的东西。
>
> **一句话**：Android 端的人脸 SDK（云从科技）和 iOS 端的 H5 代码（中科江南），
> 两家技术上毫无关系的公司，**各自独立地**用 ECB 模式加密用户凭据。

---

## 0. 为什么这值得单独立一章

单个 App 用错 ECB，可以解释为「一个团队的水平问题」。

**但两家公司、两个平台、两套完全不同的技术栈、两拨互不认识的程序员，
独立地犯同一个教科书第一课就警告的错误**——这个概率低到需要用别的原因解释。

本文件先**把事实钉死**（包括我们排除掉的假阳性），再讨论可能的解释，
并明确标出**哪些是证据、哪些是推测**。

---

## 1. 先把证据做扎实：三级判据与假阳性排除

「用了 ECB」这句话，在静态分析里有三种强度完全不同的证据。**混淆它们
是这类调查最常见的错误**，所以本节把三级判据与排除过程全部写出来。

### 1.1 三级判据

| 级别 | 形态 | 能否作为「使用 ECB」的证据 |
|---|---|---|
| **L1 字符串在场** | 二进制里出现 `ECB` 三个字节 | ❌ **不能**。OpenSSL 等库内置算法名表，几乎每个链接了 OpenSSL 的 App 都有 |
| **L2 符号在场** | 存在 `EVP_aes_256_ecb` 等符号 | ❌ **不能**。符号在 LINKEDIT 里只说明「链接进来了」，不说明「调用了」 |
| **L3 代码级调用** | `AES.encrypt(..., {mode: ECB})` 这类**实际调用点** | ✅ **能**。这是唯一够格的证据 |

### 1.2 我们踩到的三个假阳性（全部记录在案）

#### 假阳性 A：裸 `ECB` 字符串 → 49/50 命中

第一轮普查用「二进制里含 `ECB`」作判据，得到 **49/50**。
这个数字**几乎肯定是假的**——它把 OpenSSL 算法名表全算进去了。

**排除方法**：要求出现具体的 ECB 函数符号（`EVP_aes_256_ecb`、`sm4_crypt_ecb` 等）。
结果降到 **11/50**。

#### 假阳性 B：符号有 xref，但地址在 `__cstring`

第二轮对那 11 个做指令级 xref 扫描，民生银行 `EVP_aes_256_ecb` 有 **6 个引用点**、
北京银行有 **2 个**——看起来是铁证。

**但查地址落在哪个 section 后发现：两个地址都在 `__TEXT,__cstring`。**

⇒ 那 6 个「引用点」是代码在**查 OpenSSL 的算法名字表**（`EVP_get_cipherbyname("EVP_aes_256_ecb")` 这类），
**不是调用 ECB 加密函数**。

**教训**：xref 数量本身不是证据，**必须确认被引用的地址是代码还是字符串**。

#### 假阳性 C：crypto-js 算法注册表 → 交管12123

交管12123 有 3 处 `mode:"ECB"`，看起来是实锤。

**但上下文是**：
```js
e.exports={"aes-128-ecb":{cipher:"AES",key:128,iv:0,mode:"ECB",type:"block"},
           "aes-192-ecb":{...},"aes-256-ecb":{...}}
```

这是 **crypto-js 库自带的算法注册表**——库支持 ECB 不等于应用用了 ECB。
该文件里 `CryptoJS.AES.encrypt` 调用数为 **0**。

⇒ **判为假阳性，排除。**

### 1.3 严判据下的结果：3 / 50

要求同时满足：
1. `mode` 指向 `ECB`（字面量或 `xxx.ECB` 属性）；
2. **同一上下文里存在真实的 `encrypt`/`decrypt` 调用**；
3. **不在**算法注册表形态里。

| App | 命中 | 性质 |
|---|---|---|
| **公安一网通办**（本报告对象） | 3 处 | ✅ **真实加密调用** |
| **中国银行** | 18 处 | ✅ **真实加解密工具**（见 §2.2） |
| 交管12123 | 3 处 | ⚠️ 需人工复核（见 §1.2 C，倾向注册表） |

> **这个 3/50 才是可信的基线。** 之前那些 49、11 都是判据太松的产物。
> 我们把它写出来，是因为**别人很容易得出 49/50 这种惊人但错误的数字**。

---

## 2. 两家公司，同一个错误

### 2.1 Android 端：云从科技（人脸 SDK 厂商）

来自 Android 篇（[cn.cyberIdentity.certification](https://github.com/math-fournity/cn.cyberIdentity.certification)），
`libcloudwalk_sdk.so` 内**指令级实证**：

```
0x7dea8  cbz  x24              ← 调用方未传钥分支
0x7deac  adrp x1, 0x4a0000
0x7deb0  ldr  x1, [x1, #0xd90] ← 从 GOT 取硬编码钥 key_bodgl
0x7deb8  bl   sm4_setkey_enc   ← 密钥编排
0x7df5c  bl   sm4_crypt_ecb    ← 对数据执行 ECB 加密
```

- 技术栈：**C/C++ native（JNI）**
- 语言：C++
- 厂商：云从科技（科创板 688327）
- 用途：人脸活体检测的数据加解密

### 2.2 iOS 端：中科江南（H5 应用开发商）

本报告对象 `cn.sinobest.gaywtb`：

```js
// www/p__login__Login.js @9453
Q = e => {
  var r = O.a.enc.Utf8.parse("385f33cb…9081ab7"),
      o = O.a.AES.encrypt(e, r, {mode: O.a.mode.ECB, padding: O.a.pad.Pkcs7});
  return o.ciphertext.toString()
}
```

- 技术栈：**JavaScript（CryptoJS）**
- 语言：JS
- 厂商：中科江南（创业板上市）
- 用途：登录密码 / 重置密码 / 修改密码

**另有一个更强的旁证**：中国银行 iOS 端的 H5 代码里，有一个**通用加解密工具**：

```js
switch (mode) {
  case "sm4_cbc": … SM4.encrypt(n, p, {iv:A, mode:SM4.constants.CBC, …})
  case "sm4_ecb": … SM4.encrypt(n, p, {mode:SM4.constants.ECB, …})   ← 也提供了 ECB
  case "aes_cbc": … CryptoJS.AES.encrypt(n, …, {iv:…, mode:CryptoJS.mode.CBC, …})
}
```

**这个 switch 本身就是证据**：同一个文件里 CBC 和 ECB 并排提供，
说明**开发者明确知道有 CBC 这个选项**，仍然把 ECB 保留在可用模式列表里。
这削弱了「不知道 ECB 有问题」的辩解——至少对中行这一例。

### 2.3 两张表并排看

| 维度 | Android（云从） | iOS（中科江南） |
|---|---|---|
| 平台 | Android | iOS |
| 语言 | C++ / JNI | JavaScript |
| 加密库 | 自研/OpenSSL 系 | CryptoJS |
| 厂商 | 云从科技（688327） | 中科江南 |
| 行业 | 人脸识别 SDK | 政务应用开发 |
| **用的模式** | **SM4-ECB** | **AES-ECB** |
| 证据强度 | 指令级（`bl sm4_crypt_ecb`） | 代码级（`mode: ECB`） |
| 有无 CBC 可选 | — | 中行版明确有 |

**两家公司在技术栈、语言、行业、平台四个维度上都没有交集。**

---

## 3. 这个巧合有多大？——把「不可思议」变成可讨论的问题

### 3.1 先算一个粗概率（明确标注：这是估算，不是测量）

如果「选 ECB」在开发者中是独立随机事件，概率为 *p*，那么两家独立公司
都选 ECB 的概率是 *p²*。

*那 p 是多少？* 我们无法直接测量，但可以用本 repo 的 50 个样本给一个**下界参考**：

- 严判据下**确认调用 ECB** 的：3 个（含本报告对象）
- 其中属于「用户凭据加密」场景的：本报告对象 1 个（中行是通用工具）

⇒ 在 50 个主流 App 里，**明确用 ECB 加密用户凭据的只有 1 个（2%）**。

如果把这个 2% 当作 *p* 的粗略参考，两家独立公司都这么做的概率约 **0.04%**。

> **这个估算的三个明显弱点**（必须说明）：
> ① 样本只有 50 个，且不是随机抽样（含大量银行 App）；
> ② *p* 在「人脸 SDK 厂商」和「政务 H5 开发商」两个子群里可能不同；
> ③ 静态分析只能看到「代码里有」，看不到「线上真在用」。
>
> **所以这不是一个统计结论，只是一个数量级感受：这件事确实不寻常。**

### 3.2 三种可能的解释（按可检验性排序）

#### 解释一：**搜索投毒 / 教程污染**（可部分检验）

程序员的实际工作方式：搜「Java AES encryption example」或
「JavaScript AES 加密 示例」，复制排名靠前的结果。

**如果搜索结果的前排代码普遍用 ECB**，那么「独立地犯同一个错」就不再是巧合——
**它们抄的是同一个源**。

**这条可以检验**：去搜这些关键词，看前排结果的 ECB 比例。
**本报告未做这个检验**（需要联网检索并逐一核对代码，属于独立课题）。
**列为开放问题。**

#### 解释二：**工程便利 / 历史遗留**（部分可检验）

ECB 是**最简单的模式**：不需要 IV、不需要随机数、加密结果确定（便于比对）。
在很多「先跑通再说」的项目里，ECB 是默认选择。

**支持这条的证据**：CryptoJS 的默认模式是 CBC 而非 ECB，
但网上教程大量使用 ECB——因为它代码最短。

**这条与本报告 §5b 反驳三的处理一致**：我们不主张恶意，只主张「这个选择是错的」。

#### 解释三：**有意为之**（**不可由静态证据检验**）

即「方便在服务端拿到明文密码」。

**本报告明确不主张这一条**，理由：

1. **静态分析看不到动机**；
2. **有更简单的解释**（解释一、二）尚未排除；
3. **主张它需要证据，而证据不存在**——按本报告的方法纪律，这属于
   「未证，列开放问题」。

> **但有一条相关的事实值得记录**：ECB 的确定性确实**使得**「服务端可比对
> 相同密码」成为可能（见主报告 §2.6 演示一）。这是**能力的客观存在**，
> 不等于**意图的存在**。二者不可混淆。

---

## 4. 下一步：怎么把这个命题真正检验出来

「是不是巧合」这个问题，**光靠这两个样本回答不了**。要回答它，需要：

### 4.1 扩大样本到「公安部系全部 App」

Android 篇已有公安部研究所名录
（`evidence/mps-apps/01-研究所名录与App清单`）：现役 5 家研究所，
对应 App 包括《国家网络身份认证》、交管12123、网证CTID 等。

**检验设计**：
- **实验组**：公安部系全部 App（Android + iOS）
- **对照组**：同等数量的非公安政务 App、商业银行 App、非中国 App
- **判据**：严判据（§1.3 的三条），逐个人工复核
- **要回答的问题**：ECB 使用率在实验组是否**显著高于**对照组

**如果显著更高** → 「这不是巧合」获得统计支持；
**如果不显著** → 说明是行业普遍问题，与公安部无关。

### 4.2 检验「搜索投毒」假说

搜「AES 加密 示例」「Java AES encryption」「JavaScript AES 加密」等关键词，
统计前排结果的 ECB 使用比例，并核对代码相似度。

**如果前排结果高度雷同且普遍用 ECB** → 解释一获得支持。

### 4.3 本报告的立场

**§5 已经报告了我们实际做到哪一步。**在补齐 4.5.4 那些缺口之前，本报告不主张任何关于「系统性」的结论。

我们主张的只有已经钉死的事实：
- Android 端云从 SDK **在指令级调用 SM4-ECB**；
- iOS 端中科江南 H5 **在代码级调用 AES-ECB**；
- 两家公司在技术栈、语言、行业上无交集；
- 在 50 个样本里，明确用 ECB 加密用户凭据的只有 1 个（2%）。

**「这说明什么」——留给读者，也留给我们下一步的调查。**

---

## 5. 我们已经做了这一步：Android 侧 29 个 APK 的普查（含削弱命题的发现）

拿到公安部系 29 个 APK（`/Volumes/D/mps-apps/`，4.4GB）后，用**与 iOS 侧同源的严判据**
做了普查。**结果比预期复杂，其中两条削弱了我们的命题，如实记录。**

### 5.1 结果

| App | 对称 ECB 变换名（dex 级） | 有无壳 |
|---|---|---|
| **交管12123**（19 个历史版本） | `AES/ECB/NoPadding`、`AES/ECB/PKCS5Padding` | **有壳** |
| **《国家网络身份认证》** | `SM4/ECB/PKCS5PADDING` | **有壳** |
| **电子证件**（`com.ctid.open`） | `AES/ECB/PKCS5Padding`、`AES/ECB/PKCS7Padding` | 无壳 |
| **国家政务服务平台** | `AES/ECB/NoPadding`、`AES/ECB/PKCS5Padding` | 无壳 |
| **公安110**（`chinaonekey`） | `AES/ECB/PKCS5Padding` | 无壳 |
| 出入境、微警、反诈、国门公安、国家反诈AI | 仅 `RSA/ECB/*` 或 `DES/ECB/*`（库自带） | — |

**11 个不同 App 中，5 个有 AES/SM4 对称 ECB 的 dex 级痕迹。**

### 5.1b 重要修正：《国家网络身份认证》的 ECB **是真实调用**（指令级已证）

§5.1 的表格把《国家网络身份认证》列为「有壳，证不了调用」。**这条要修正。**

壳保护的是 **dex 层**（Java 代码）。但 ECB 的实际调用发生在 **native 层**——
`WHClient` 主二进制（31.9 MB，**无壳**）里。

#### 证据：`CCCrypt` 的 options 参数到达定值分析

iOS 侧没有 `EVP_aes_256_ecb` 这类符号——CommonCrypto 的 ECB 是通过
**options 位**表达的。判据：

| 常量 | 值 | 含义 |
|---|---|---|
| `kCCOptionPKCS7Padding` | `0x0001` | PKCS7 填充 |
| `kCCOptionECBMode` | `0x0002` | **ECB 模式** |

所以 `x2 == 0x3` ⇒ `PKCS7 | ECB`。

**对 `WHClient` 做寄存器到达定值分析**（从每个 `bl _CCCrypt` 向上回溯，
追踪 `x2` 的真实来源）：

```
0x100be3934  mov  w0, #0x0
0x100be3938  mov  w1, #0x1        ← 算法参数
0x100be393c  mov  w2, #0x3        ← options = PKCS7 | ECB   ★
0x100be3940  mov  x3, x25
0x100be3944  mov  w4, #0x8
0x100be3948  mov  x5, #0x0
0x100be394c  mov  x6, x26
0x100be3950  bl   0x10178a13c ; symbol stub for: _CCCrypt   ★
```

**`otool -tV` 独立核验一致**（本报告作者复核，非转抄）。

#### 全量结果

| 项 | 数量 |
|---|---|
| `_CCCrypt` 调用点 | 38 |
| `_CCCryptorCreate` 调用点 | 2 |
| `_CCCryptorCreateWithMode` 调用点 | 5 |
| **合计调用点** | **45** |
| **其中 ECB（`is_ecb=True`）** | **9** |

按算法分（另一并行取证线的结论，本报告复核了其中的 ECB 判定逻辑）：
DES-ECB 6 处、AES-ECB 1 处、算法运行期决定 2 处。

#### 这条修正意味着什么

| 之前 | 现在 |
|---|---|
| 《国家网络身份认证》「有壳，ECB 调用未证」 | **native 层 9 处 ECB 调用点，指令级已证** |
| 「5 个 App 含 ECB 变换名，但实际调用未证」 | **至少 1 个（NIA）已证实际调用** |

**⇒ 命题从「本样本不支持」修正为「至少有 1 个公安部系 App 在 native 层实际调用 ECB」。**

**但仍然要如实说**：
- 这 9 处调用点里，**6 处是 DES-ECB**（DES 本身已不安全，且 DES 的 ECB 更弱）；
- **AES-ECB 只有 1 处**；
- 这 9 处**加密的是什么数据**（密码？报文？活体？）——**未证**，
  需要追调用方语义（本报告未做）。

### 5.2 三条削弱命题的发现（必须写出来）

#### 削弱一：多数样本有壳，静态证不了「真的被调用」

| App | 壳状态 | 能否验证调用 |
|---|---|---|
| 交管12123 | **有壳**（17.5MB dex 只有 5 个 class_defs，data 区仅 14KB） | ❌ 代码在加密岛内 |
| 《国家网络身份认证》 | **有壳** | ❌ 同上 |
| 电子证件 | 无壳 | ✅ 可验证 |
| 国家政务服务平台 | 无壳 | ✅ 可验证 |

**「dex 字符串池里有 `SM4/ECB/PKCS5PADDING`」≠「代码真的用了它」。**
对 6 个有壳样本，本报告**只能主张「该变换名存在于包内」**，不能主张「实际调用」。

#### 削弱二：唯一能验证的那个，恰好是**死代码**

`com.ctid.open`（电子证件）无壳，可以真正反编译验证。结果：

```smali
# com/ctid/open/captcha/utils/AESUtil.smali
.field private static final ALGORITHMSTR:Ljava/lang/String; = "AES/ECB/PKCS7Padding"

.method private static encrypt(Ljava/lang/String;Ljava/lang/String;)[B
    .locals 2
    const/4 v0, 0x0
    return-object v0        ← 方法体被掏空，直接返回 null
    nop
    nop
    ...
.end method
```

**这个 AES 工具类的方法体是空的**（混淆器/加固工具常见的「掏空」处理）。
⇒ 该样本的 ECB 痕迹是**死代码**，不能作为「实际使用」的证据。

#### 削弱三：一部分 ECB 是标准库自带，不是应用自选

| 变换名 | 归属 |
|---|---|
| `RSA/ECB/PKCS1Padding` | **Alipay SDK / AMap SDK 自带**。且 **RSA 的 "ECB" 只是 Java 填充模式命名，与分组密码的 ECB 弱点无关** |
| `DES/ECB/NoPadding` | **Apache HttpClient 的 NTLM 认证实现**（`NTLMEngineImpl`）自带 |

这两类**不能算作「应用自己选择了 ECB」**。

### 5.3 校准后的结论

| 主张 | 强度 |
|---|---|
| Android 端**云从 SDK 在指令级调用 SM4-ECB** | ✅ **已证**（Android 篇，反汇编 `bl sm4_crypt_ecb`） |
| iOS 端**中科江南 H5 在代码级调用 AES-ECB** | ✅ **已证**（本报告 §2.1） |
| 公安部系 29 个 APK 中 **5 个含 AES/SM4 对称 ECB 变换名** | ✅ **已证（串在场）** |
| 这 5 个中**实际调用** ECB 的 | ✅ **至少 1 个已证**——《国家网络身份认证》native 层 9 处（§5.1b） |
| 「公安部系普遍使用 ECB」 | ⚠️ **弱支持**——11 个 App 中 5 个有 ECB 痕迹，其中 1 个已证实际调用；其余 4 个仍受壳或死代码阻挡 |

**所以，「系统性使用弱加密」这个命题，在我们目前的证据下不成立。**
能成立的是更窄的一条：**两家互不相关的厂商（云从、中科江南）各自独立地在
用户凭据加密上用了 ECB**，且这两例都是**可验证的真实调用**。

### 5.4 要真正检验命题，还缺什么

| 缺口 | 说明 |
|---|---|
| **动态验证有壳样本** | 4 个有壳 App 需要在 vPhone/真机上运行并 hook `Cipher.getInstance`，才能确认 ECB 是否被调用 |
| **扩大无壳样本** | 目前只有 5 个无壳样本可静态验证，其中 1 个是死代码 |
| **对照组的 APK** | 现有 29 个全是公安部系，缺商业银行/非中国 App 的 APK 对照（iOS 侧有，Android 侧没有） |

## 6. 复现

```bash
# 严判据普查（本文件的 §1.3 结果）
python3 - <<'EOF'
import zipfile, glob, os, re
for p in sorted(glob.glob('ipa/*.ipa')):
    zf = zipfile.ZipFile(p)
    for n in zf.namelist():
        if not n.lower().endswith(('.js','.html')): continue
        t = zf.read(n).decode('utf-8','replace')
        for m in re.finditer(r'mode\s*:\s*[\w$.]*\.ECB\b|mode\s*:\s*["\']ECB["\']', t):
            ctx = t[max(0,m.start()-300):m.start()+220]
            if re.search(r'\.(encrypt|decrypt)\s*\(', ctx) \
               and not re.search(r'"(aes|des|sm4)-\d+-(ecb|cbc)"\s*:\s*\{', ctx):
                print(f"{os.path.basename(p)}: {n}@{m.start()}")
EOF
```

```bash
# 确认一个 ECB 符号是「代码」还是「字符串」（§1.2 B 的关键检查）
python3 /tmp/_ecbx2.py ipa/com.cmbc.cn.iphone-10.61-Decrypted.ipa EVP_aes_256_ecb
# 再用 section 归属确认：地址若在 __TEXT,__cstring 则为字符串，不是函数
```

---

## 7. 相关文档

| 文档 | 内容 |
|---|---|
| [03 · ECB 工作模式](03-ECB-工作模式.md) | ECB 的机制、三个可复现后果、为什么密钥长度救不了 |
| [04 · 规范依据](04-规范依据.md) | NIST / OWASP 的原文与引用边界 |
| [02 · 方法论与自我推翻记录](02-方法论与自我推翻记录.md) | 本文件 §1.2 那三个假阳性的方法论教训 |
| **Android 篇** | https://github.com/math-fournity/cn.cyberIdentity.certification |
