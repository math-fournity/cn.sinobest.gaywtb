#!/usr/bin/env python3
"""报告内部一致性检查。

## 为什么需要这个脚本

这份报告在多个文件里重复引用同一批事实数字：自我推翻次数、样本版本号、
密钥实例数、密钥脱敏形式、AST 关闭状态……改一处忘一处，就会出现
「README 说 5 次、报告说 6 次」这种自相矛盾。

实测案例（2026-10-25）：「自我推翻」在四个文件里分别写成 5 次与 6 次，
是靠人工 grep 才发现的。这类检查应该脚本化，不该靠记性。

## 检查什么

1. **密钥完整性**：完整密钥（32 hex）不得出现在任何被跟踪文件里。
   只允许脱敏形式 `385f33cb…9081ab7`。
2. **数字一致性**：同一事实在多个文件里必须写成同一个数字。
3. **版本一致性**：CITATION.cff 的 version 与 CHANGELOG 最新条目一致。
4. **作者一致性**：README / CITATION.cff / 报告作者行必须同名单。
5. **二进制泄漏**：不得有 .ipa/.apk/.dylib/.so/.pyc 等被跟踪。

## 用法

    python3 tools/consistency_check.py

退出码：0 全部通过；1 有问题。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 事实基准：这里的值是"唯一真值"，其他文件必须与之相符 ──────────────
FULL_KEY = "REDACTED"   # 不得出现（只允许脱敏形式）
MASKED_KEY = "385f33cb…9081ab7"                  # 允许的形式
IPA_SHA256 = "d46aaec36700a85b5d1a14834d46e645e145149c8416d94aa294b5975f84f3ad"
SAMPLE_VERSION = "1.2.28"
DAYS_EXPOSED = "1069"
SELF_RETRACTIONS = "6"

errors: list[str] = []
warnings: list[str] = []


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True).stdout


def tracked_files() -> list[str]:
    return [f for f in run(["git", "ls-files"]).splitlines() if f]


def read(path: str) -> str:
    try:
        with open(os.path.join(REPO, path), encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return ""


def check_key_not_leaked(files: list[str]) -> None:
    """完整密钥不得出现在任何被跟踪文件里。"""
    hits = []
    for f in files:
        if FULL_KEY in read(f):
            hits.append(f)
    if hits:
        errors.append(
            f"完整密钥泄漏在 {len(hits)} 个文件里：\n    " + "\n    ".join(hits)
        )
    else:
        n_masked = sum(read(f).count(MASKED_KEY) for f in files)
        print(f"  ✓ 密钥：完整形式 0 处，脱敏形式 {n_masked} 处")


def check_number_consistency(files: list[str]) -> None:
    """同一事实的数字必须一致。"""
    checks = [
        ("自我推翻次数", rf"推翻了自己\s*(\d+)\s*次", SELF_RETRACTIONS),
        ("已撤回次数", rf"已撤回\s*(\d+)\s*次", SELF_RETRACTIONS),
        ("暴露天数", rf"(\d{{3,4}})\s*天", DAYS_EXPOSED),
    ]
    for label, pattern, expected in checks:
        found: dict[str, list[str]] = {}
        for f in files:
            if not f.endswith(".md"):
                continue
            for m in re.finditer(pattern, read(f)):
                val = m.group(1)
                found.setdefault(val, []).append(f)
        if not found:
            warnings.append(f"{label}：未在任何文件中找到（检查正则是否失效）")
            continue
        # 「暴露天数」允许多个数字（如 2023 天等），只要求主数字存在
        if label == "暴露天数":
            if expected not in found:
                errors.append(f"{label}：未找到期望值 {expected}，实际见 {sorted(found)}")
            else:
                print(f"  ✓ {label}：{expected} 天（{len(found[expected])} 处）")
            continue
        if len(found) > 1:
            detail = "; ".join(f"{v} 次 → {', '.join(fs)}" for v, fs in sorted(found.items()))
            errors.append(f"{label}不一致：{detail}")
        elif expected not in found:
            errors.append(f"{label}：期望 {expected}，实际 {list(found)}")
        else:
            print(f"  ✓ {label}：{expected} 次（{len(found[expected])} 处）")


def check_version(files: list[str]) -> None:
    """版本号有两套体系，必须分开看：
       - CITATION.cff 的 version = 学术引用版本（1.0 首版，小幅修订才进位）
       - CHANGELOG 的 1.x = 内容迭代版本（每次实质修改都进位）
    它们不该相等。这里只检查各自内部是否自洽。
    """
    cit = read("CITATION.cff")
    m = re.search(r'^version:\s*"([\d.]+)"', cit, re.M)
    if not m:
        warnings.append("CITATION.cff 中未找到 version 字段")
        return
    cit_ver = m.group(1)

    changelog = next((f for f in files if f.endswith("CHANGELOG.md")), None)
    if not changelog:
        warnings.append("未找到 CHANGELOG.md")
        return
    cl = read(changelog)
    versions = [float(v) for v in re.findall(r"\|\s*\**([\d.]+)\**\s*\|", cl)]
    if not versions:
        warnings.append("CHANGELOG 中未解析到版本号")
        return
    latest = max(versions)

    # 检查：CHANGELOG 里应有 citation 版本对应的条目（或更高）
    if float(cit_ver) > latest:
        errors.append(
            f"版本倒挂：CITATION.cff 是 {cit_ver}，但 CHANGELOG 最新只到 {latest}"
        )
        return
    print(f"  ✓ 版本：CITATION.cff={cit_ver}（引用版） / CHANGELOG 最新={latest}（内容版）")
    if float(cit_ver) < latest:
        warnings.append(
            f"CITATION.cff 的引用版 {cit_ver} 落后于内容版 {latest}——"
            f"若有实质性结论变化，考虑同步更新引用版"
        )


def check_authors(files: list[str]) -> None:
    """作者名单在 README / CITATION / 报告作者行必须一致。"""
    cit = read("CITATION.cff")
    cit_authors = re.findall(r"^\s*-\s*name:\s*(.+?)\s*$", cit, re.M)

    readme = read("README.md")
    # README 形式：**Name A**、**Name B**、**Name C**（AI 协作研究）
    # 取「## 作者」之后第一段非空文本，去掉所有 ** 与括号注释，再按顿号切
    m = re.search(r"^## 作者\s*\n+(.+)$", readme, re.M)
    readme_authors = []
    if m:
        line = re.sub(r"\*\*", "", m.group(1))          # 去掉加粗标记
        line = re.sub(r"（.*?）|\(.*?\)", "", line)     # 去掉括号注释
        readme_authors = [a.strip() for a in re.split(r"[、,]", line) if a.strip()]

    report = next(
        (f for f in files if f.endswith("report.zh.md")), None
    )
    report_authors = []
    if report:
        rm = re.search(r"\|\s*\*\*作者\*\*\s*\|\s*(.+?)\s*\|", read(report))
        if rm:
            report_authors = [
                re.sub(r"（.*?）", "", a).strip()
                for a in re.split(r"[、,]", rm.group(1))
                if a.strip()
            ]

    sets = {
        "CITATION.cff": cit_authors,
        "README.md": readme_authors,
        "报告作者行": report_authors,
    }
    non_empty = {k: v for k, v in sets.items() if v}
    if len(non_empty) < 2:
        warnings.append(f"作者名单：只解析到 {list(non_empty)}，跳过比对")
        return
    ref = list(non_empty.values())[0]
    bad = {k: v for k, v in non_empty.items() if v != ref}
    if bad:
        detail = "; ".join(f"{k}={v}" for k, v in bad.items())
        errors.append(f"作者名单不一致（基准 {ref}）：{detail}")
    else:
        print(f"  ✓ 作者：{len(ref)} 位，{len(non_empty)} 处一致 → {'、'.join(ref)}")


def check_no_binaries(files: list[str]) -> None:
    """不得有二进制/派生物被跟踪。"""
    bad = [
        f for f in files
        if re.search(r"\.(ipa|apk|dylib|so|pyc|car|nib)$", f)
        or "__pycache__" in f
        or f.startswith(("tmp/", "work/"))
    ]
    if bad:
        errors.append(f"二进制/派生物被跟踪 {len(bad)} 个：\n    " + "\n    ".join(bad[:10]))
    else:
        print(f"  ✓ 无二进制：{len(files)} 个被跟踪文件全为文本")


def check_sha_reference(files: list[str]) -> None:
    """IPA 指纹若被引用，必须拼写正确。"""
    found = 0
    for f in files:
        t = read(f)
        if IPA_SHA256 in t:
            found += t.count(IPA_SHA256)
        # 检查是否有形似的错误 SHA（46-70 位 hex，且不是正确的那个）
        # 只在「提到 IPA / 样本指纹」的上下文里检查，避免误报
        # （evidence/*.json 里可能有 NIST PDF 等其他文件的 SHA-256）
        for m in re.finditer(r"\b[0-9a-f]{60,68}\b", t):
            if m.group(0) == IPA_SHA256:
                continue
            ctx = t[max(0, m.start() - 120):m.start()]
            if re.search(r"(IPA|样本|sample).{0,40}$", ctx, re.I):
                warnings.append(f"{f}：IPA 上下文里的 SHA 与基准不符 → {m.group(0)[:20]}…")
    if found:
        print(f"  ✓ IPA 指纹：{found} 处引用，拼写正确")


def main() -> int:
    files = tracked_files()
    print(f"检查 {len(files)} 个被跟踪文件\n")

    print("── 检查项 ──")
    check_key_not_leaked(files)
    check_number_consistency(files)
    check_version(files)
    check_authors(files)
    check_no_binaries(files)
    check_sha_reference(files)

    print()
    if warnings:
        print(f"⚠️  {len(warnings)} 个警告：")
        for w in warnings:
            print(f"    - {w}")
    if errors:
        print(f"\n❌ {len(errors)} 个错误：")
        for e in errors:
            print(f"    - {e}")
        return 1
    print("✅ 全部检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
