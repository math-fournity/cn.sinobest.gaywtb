#!/usr/bin/env python3
"""字符串交叉引用（xref）检查器 —— 带强制阳性对照。

## 这个脚本为什么存在

本报告 §5.3 记录了一个教训：我写的第一个 xref 扫描器返回「0 个引用」，
看起来像一个有力的阴性结论，**但它是坏的**——漏了两类取址形态。

这个脚本是修复版，并且**强制要求阳性对照**：如果找不回一个已知被引用的字符串，
脚本就退出非零、不让你得出任何结论。

## 两个已知的静默失明模式（本脚本已处理）

1. **`__cfstring` 中转**：ObjC 的 `@"..."` 不直接 `adrp+add` 到 `__cstring`，
   而是先指向 `__DATA,__cfstring` 结构：
       +0  isa（未重定位时为 0）
       +8  flags
       +16 字符串指针  → 指向 __cstring
       +24 长度
   只找「adrp+add 直接命中 __cstring」的扫描器，对 ObjC 字符串**全部报 0**。

2. **`adr` 单条取址**：小范围取址编译器用单条 `adr`，不拆成 adrp+add。
   只扫 adrp 的扫描器会漏掉这些引用点。

## 用法

    python3 xref_check.py <binary> <target-string> --control <known-referenced-string>

    # 本报告用到的实际查询：
    python3 xref_check.py "Payload/公安一网通办.app/公安一网通办" \
        'cw_test_aes_key_' --control 'cw_test_sm4_key_'

退出码：
    0  查询成功且所有对照 PASS
    1  对照 FAIL（扫描器可能失明，结论不可采信）
    2  参数/解析错误
    3  未提供对照（拒绝在无对照情况下出结论）

## 依赖

仅 Python 标准库。
"""
from __future__ import annotations

import argparse
import struct
import sys


def parse_sections(data: bytes):
    """解析 arm64 Mach-O 的 section 表。返回 [(seg, sect, addr, size, fileoff)]。"""
    secs = []
    if len(data) < 32:
        return secs
    magic = struct.unpack("<I", data[:4])[0]
    if magic != 0xFEEDFACF:          # 只支持 64-bit little-endian Mach-O
        return secs
    ncmds = struct.unpack("<I", data[16:20])[0]
    off = 32
    for _ in range(ncmds):
        if off + 8 > len(data):
            break
        cmd, cmdsize = struct.unpack("<II", data[off:off + 8])
        if cmdsize == 0:
            break
        if cmd == 0x19:              # LC_SEGMENT_64
            if off + 72 > len(data):
                break
            nsects = struct.unpack("<I", data[off + 64:off + 68])[0]
            soff = off + 72
            for _s in range(nsects):
                if soff + 80 > len(data):
                    break
                sn = data[soff:soff + 16].rstrip(b"\x00").decode("ascii", "replace")
                sg = data[soff + 16:soff + 32].rstrip(b"\x00").decode("ascii", "replace")
                addr = struct.unpack("<Q", data[soff + 32:soff + 40])[0]
                size = struct.unpack("<Q", data[soff + 40:soff + 48])[0]
                fo = struct.unpack("<I", data[soff + 48:soff + 52])[0]
                secs.append((sg, sn, addr, size, fo))
                soff += 80
        off += cmdsize
    return secs


def build_cfstring_index(data: bytes, secs):
    """string_vaddr -> [cfstring 结构 vaddr]"""
    idx = {}
    for sg, sn, a, z, fo in secs:
        if sn != "__cfstring" or z <= 0:
            continue
        for k in range(0, z - 31, 8):
            p = fo + k
            if p + 32 > len(data):
                break
            sp = struct.unpack("<Q", data[p + 16:p + 24])[0]
            ln = struct.unpack("<Q", data[p + 24:p + 32])[0]
            if 0 < ln < 4096 and sp:
                idx.setdefault(sp, []).append(a + k)
    return idx


def find_xrefs(code: bytes, text_va: int, target_va: int, span: int = 40):
    """在 __text 中找取 target_va 的指令。返回 [(insn_addr_hex, form)]。"""
    hits = []
    n = len(code)
    for i in range(0, n - 4, 4):
        w = struct.unpack("<I", code[i:i + 4])[0]

        # ADR：单条取址
        if (w & 0x9F000000) == 0x10000000:
            immlo = (w >> 29) & 3
            immhi = (w >> 5) & 0x7FFFF
            imm = (immhi << 2) | immlo
            if imm & (1 << 20):
                imm -= (1 << 21)
            if text_va + i + imm == target_va:
                hits.append((hex(text_va + i), "adr"))
            continue

        # ADRP：页取址，需配对 add/ldr
        if (w & 0x9F000000) == 0x90000000:
            rd = w & 0x1F
            immlo = (w >> 29) & 3
            immhi = (w >> 5) & 0x7FFFF
            imm = (immhi << 2) | immlo
            if imm & (1 << 20):
                imm -= (1 << 21)
            page = ((text_va + i) & ~0xFFF) + (imm << 12)
            for j in range(4, span, 4):
                k = i + j
                if k + 4 > n:
                    break
                w2 = struct.unpack("<I", code[k:k + 4])[0]
                # add xd, xn, #imm12
                if (w2 & 0xFFC00000) == 0x91000000 and (w2 & 0x1F) == rd:
                    imm12 = (w2 >> 10) & 0xFFF
                    if (w2 >> 22) & 1:
                        imm12 <<= 12
                    if page + imm12 == target_va:
                        hits.append((hex(text_va + i), "adrp+add"))
                # ldr xt, [xn, #imm12*8]
                elif (w2 & 0xFFC00000) == 0xF9400000 and (w2 & 0x1F) == rd:
                    imm12 = ((w2 >> 10) & 0xFFF) * 8
                    if page + imm12 == target_va:
                        hits.append((hex(text_va + i), "adrp+ldr"))
    return hits


def locate(data: bytes, secs, needle: bytes):
    fo = data.find(needle)
    if fo < 0:
        return None, None, None
    for sg, sn, a, z, f in secs:
        if z > 0 and f <= fo < f + z:
            return fo, a + (fo - f), f"{sg},{sn}"
    return fo, None, None


def scan(data, secs, cfidx, code, text_va, needle: bytes):
    fo, va, sec = locate(data, secs, needle)
    if va is None:
        return {"needle": needle.decode("latin-1", "replace"), "found": False}
    direct = find_xrefs(code, text_va, va)
    via = []
    for cs in cfidx.get(va, []):
        for h in find_xrefs(code, text_va, cs):
            via.append((h[0], h[1], hex(cs)))
    return {
        "needle": needle.decode("latin-1", "replace"),
        "found": True,
        "fileoff": fo,
        "vaddr": hex(va),
        "section": sec,
        "direct": direct,
        "via_cfstring": via,
        "total": len(direct) + len(via),
    }


def show(r):
    if not r.get("found"):
        print(f"  {r['needle']!r}: NOT FOUND in binary")
        return
    print(f"  {r['needle']!r}")
    print(f"    {r['section']}  fileoff={r['fileoff']}  vaddr={r['vaddr']}")
    print(f"    直接引用={len(r['direct'])}  经__cfstring={len(r['via_cfstring'])}  "
          f"合计={r['total']}")
    for h in r["direct"][:8]:
        print(f"      direct    @{h[0]}  ({h[1]})")
    for h in r["via_cfstring"][:8]:
        print(f"      cfstring  @{h[0]}  ({h[1]})  via {h[2]}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="arm64 Mach-O string xref checker (mandatory positive control)")
    ap.add_argument("binary")
    ap.add_argument("target")
    ap.add_argument("--control", action="append", default=[],
                    help="已知被引用的字符串，用作阳性对照（可重复）")
    args = ap.parse_args()

    try:
        data = open(args.binary, "rb").read()
    except OSError as e:
        print(f"ERROR: 无法读取 {args.binary}: {e}", file=sys.stderr)
        return 2

    secs = parse_sections(data)
    if not secs:
        print("ERROR: 不是 64-bit little-endian Mach-O，或 section 表解析失败",
              file=sys.stderr)
        return 2

    text = next(((a, z, fo) for sg, sn, a, z, fo in secs if sn == "__text"), None)
    if not text:
        print("ERROR: 找不到 __text section", file=sys.stderr)
        return 2
    text_va, text_sz, text_fo = text
    code = data[text_fo:text_fo + text_sz]

    cfidx = build_cfstring_index(data, secs)

    target = scan(data, secs, cfidx, code, text_va, args.target.encode())

    print("=" * 70)
    print("TARGET")
    print("=" * 70)
    show(target)

    if not args.control:
        print()
        print("=" * 70)
        print("拒绝出结论：未提供阳性对照", file=sys.stderr)
        print("=" * 70)
        print(
            "\n本扫描器有两个已知的静默失明模式（漏 __cfstring 中转、漏 adr）。\n"
            "没有阳性对照时，它返回的「0 个引用」无法区分于「工具坏了」。\n"
            "请用 --control 提供一个**已知被引用**的字符串，例如：\n"
            "  --control 'cw_test_sm4_key_'",
            file=sys.stderr,
        )
        return 3

    print()
    print("=" * 70)
    print("POSITIVE CONTROLS")
    print("=" * 70)
    all_pass = True
    for c in args.control:
        r = scan(data, secs, cfidx, code, text_va, c.encode())
        show(r)
        ok = r.get("found") and r.get("total", 0) > 0
        print(f"    → {'PASS' if ok else 'FAIL（扫描器可能失明，本结论不可采信）'}")
        print()
        all_pass = all_pass and ok

    print("=" * 70)
    print(f"CONTROL VERDICT: {'PASS' if all_pass else 'FAIL'}")
    print("=" * 70)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
