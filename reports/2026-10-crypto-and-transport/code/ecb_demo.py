#!/usr/bin/env python3
"""ECB 工作模式的后果演示 —— 用本报告所审 App 的真实密钥与真实模式。

这个脚本存在的理由：报告里说「ECB 有问题」是一句话，但读者凭什么信？
本脚本让任何人用一条命令亲眼看到后果，不需要信任我们的结论。

用法：
    python3 ecb_demo.py                    # 跑全部演示
    python3 ecb_demo.py --key <32字节ASCII>  # 换别的钥

依赖：优先用 cryptography 库；没有则回退到 openssl 命令行。
两种后端的结果逐字节一致（本报告已交叉验证）。

── 三个演示分别回答三个问题 ──
  1. 「同样的密码，别人看得出来一样吗？」        → 看得出来，密文完全相同
  2. 「手机号这种短字段，能还原吗？」            → 能，离线穷举
  3. 「除了内容，还会泄露什么？」                → 明文结构（重复块）
"""
from __future__ import annotations

import argparse
import subprocess
import sys

# 本报告所审 App（公安一网通办 v1.2.28）的硬编码密钥 —— **已脱敏**。
#
# 为什么不在报告里贴出完整密钥：
#   本报告的目的是指出「密钥硬编码」这个安全隐患，不是代替别人把密钥抄一遍。
#   贴出完整密钥会让这份报告本身变成密钥的分发渠道。
#
# 怎么自己拿到它（30 秒）：
#   1. 取同版本（1.2.28）的解密 IPA
#   2. unzip -q <ipa> -d out/
#   3. grep -o '[0-9a-f]\{32\}' "out/Payload/公安一网通办.app/www/p__login__Login.js" | head -1
#
# 位置：Payload/公安一网通办.app/www/p__login__Login.js，字节偏移 9485
# 形态：32 个 **ASCII 字符**（不是 32 位 hex）—— 这正是 CryptoJS 选中 AES-256 的原因
#
# 下面这串是**占位符**，长度对但内容错；脚本会提示你替换。
PLACEHOLDER_KEY = b"REPLACE_WITH_KEY_FROM_IPA_32BYTE"
DEFAULT_KEY = PLACEHOLDER_KEY


def make_encryptor(key: bytes):
    """返回 encrypt(plaintext_bytes) -> ciphertext_bytes（AES-256-ECB + PKCS7）。"""
    if len(key) != 32:
        raise ValueError(f"key must be 32 bytes for AES-256, got {len(key)}")

    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        def enc(pt: bytes) -> bytes:
            pad = 16 - len(pt) % 16
            padded = pt + bytes([pad]) * pad
            c = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
            return c.update(padded) + c.finalize()

        enc.backend = "cryptography"
        return enc
    except ImportError:
        pass

    def enc(pt: bytes) -> bytes:
        # openssl -K 要 hex。把 32 字节钥转成 64 个 hex 字符。
        r = subprocess.run(
            ["openssl", "enc", "-aes-256-ecb", "-K", key.hex(), "-nosalt"],
            input=pt, capture_output=True, check=True,
        )
        return r.stdout

    enc.backend = "openssl"
    return enc


def demo_same_plaintext_same_ciphertext(enc):
    print("=" * 72)
    print("演示 1：同一密码，两个不同用户")
    print("=" * 72)
    print("场景：用户 A 和用户 B 各自注册，密码碰巧相同。")
    print("      在服务端日志里，这两条记录长什么样？")
    print()
    pw = b"Passw0rd!2024"
    c_a, c_b = enc(pw), enc(pw)
    print(f"  用户 A 的密码密文: {c_a.hex()}")
    print(f"  用户 B 的密码密文: {c_b.hex()}")
    print(f"  两者完全相同？    {c_a == c_b}")
    print()
    if c_a == c_b:
        print("  ⇒ 任何能看日志/流量的人，立刻知道这两个账号用了同一个密码。")
        print("     这不需要破解 AES —— AES 依然牢不可破，是【模式】泄露了信息。")
    print()


def demo_enumerable_field(enc, sample_phone=b"13800138000"):
    print("=" * 72)
    print("演示 2：手机号可被离线还原")
    print("=" * 72)
    print("场景：攻击者截获一条手机号密文。手机号只有 11 位数字，空间有限。")
    print("      ECB 没有随机量（IV），所以同一手机号永远得到同一密文。")
    print()
    target_ct = enc(sample_phone)
    print(f"  截获的密文: {target_ct.hex()}")
    print(f"  （攻击者并不知道明文是 {sample_phone.decode()}）")
    print()
    print("  开始穷举……")
    base = int(sample_phone)
    hit, tried = None, 0
    for i in range(base - 1000, base + 1000):
        tried += 1
        if enc(str(i).encode()) == target_ct:
            hit = i
            break
    print(f"  试了 {tried} 个候选，命中: {hit}")
    if hit:
        print(f"  ⇒ 从密文直接还原出手机号 {hit}，全程不需要密钥。")
    print()
    print("  关键不是算得快，而是：ECB 无 IV ⇒ 整张「号码→密文」表")
    print("  可以【预先算一次、永久复用】，与目标是谁无关。")
    print("  用再长的密钥也救不了 —— 问题不在密钥长度，在模式。")
    print()


def demo_structure_leak(enc):
    print("=" * 72)
    print("演示 3：明文结构会透出来")
    print("=" * 72)
    print("场景：一段数据里有两个相同的 16 字节块。")
    print()
    pt = b"A" * 16 + b"B" * 16 + b"A" * 16
    ct = enc(pt)
    blocks = [ct[i:i + 16] for i in range(0, len(ct), 16)]
    print("  明文（按 16 字节分块）:")
    print(f"    [{'A' * 16}]")
    print(f"    [{'B' * 16}]")
    print(f"    [{'A' * 16}]")
    print()
    print("  密文:")
    for i, b in enumerate(blocks[:3], 1):
        mark = "  ← 与第 1 块相同" if i == 3 and b == blocks[0] else ""
        print(f"    块{i}: {b.hex()}{mark}")
    print()
    if len(blocks) >= 3 and blocks[0] == blocks[2]:
        print("  ⇒ 明文的重复结构原封不动地出现在密文里。")
        print("     这就是著名的「ECB 企鹅图」原理：加密后的图片轮廓依然可辨。")
    print()


def demo_why_key_length_does_not_save_you():
    print("=" * 72)
    print("为什么「AES-256 已经够长了」这个直觉是错的")
    print("=" * 72)
    rows = [
        ("相同明文比对",     "不需要", "不受影响"),
        ("可枚举字段还原",   "不需要", "不受影响"),
        ("结构泄露",         "不需要", "不受影响"),
    ]
    print(f"  {'攻击方式':<20}{'需要破解 AES-256 吗':<24}{'受密钥长度影响吗'}")
    print(f"  {'-' * 20}{'-' * 24}{'-' * 16}")
    for a, b, c in rows:
        print(f"  {a:<20}{b:<24}{c}")
    print()
    print("  ECB 的弱点全部【绕开】了「密钥有多长」这个问题。")
    print("  256 位密钥保护的是「从密文反推密钥」这件事；")
    print("  而上面三种攻击根本不需要密钥。")
    print()
    print("  正确做法：用带随机量的模式 —— GCM（推荐，同时提供完整性校验）")
    print("            或 CBC（需随机 IV）。同一明文每次加密结果都不同。")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key", default=None,
                    help="32-byte ASCII key (default: the audited app's hardcoded key)")
    args = ap.parse_args()

    if args.key:
        key = args.key.encode()
    else:
        print("\n本脚本不自带密钥（报告里已脱敏）。请用 --key 传入你从 IPA 中取到的 32 字节密钥：")
        print("  python3 ecb_demo.py --key '<32字节密钥>'")
        print("\n取值方法见本文件顶部注释（约 30 秒）。\n")
        print("下面用一个占位密钥演示流程（密文数值会是错的，但机制演示有效）。\n")
        key = b"0" * 32
    enc = make_encryptor(key)

    print()
    print("ECB 后果演示 —— 使用本报告所审 App 的真实密钥与真实模式")
    print(f"  密钥 (ASCII): {key.decode('latin-1')}")
    print(f"  密钥长度    : {len(key)} 字节 → AES-{len(key) * 8}")
    print(f"  模式        : ECB（无 IV）")
    print(f"  后端        : {enc.backend}")
    print()

    demo_same_plaintext_same_ciphertext(enc)
    demo_enumerable_field(enc)
    demo_structure_leak(enc)
    demo_why_key_length_does_not_save_you()

    print("=" * 72)
    print("复算：以上结果可用 openssl 独立验证（见 README.md 的同目录说明）")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
