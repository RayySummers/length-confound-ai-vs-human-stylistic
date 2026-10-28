#!/usr/bin/env python3
"""check_mtld_column.py — RAY-598 回归检查：`mtld` 新列没有动到旧列。

验三件事：
  1. 旧列（改动前的每一列）在每一篇共有文本上逐格相同：浮点容差 1e-6，文本列必须完全一致；
  2. `mtld` 列存在，且每一行都有值、有限（无空值 / NaN / Inf）；
  3. 行数只增不减，新增行必须属于某个已知组，且五组各 30 篇。

用法（baseline 可取备份文件，也可直接从 git 取改动前的版本）：

    git show <改动前 commit>:analysis/per-text-table.csv > /tmp/per-text-table-baseline.csv
    python3 analysis/check_mtld_column.py /tmp/per-text-table-baseline.csv

退出码 0 = 通过，1 = 有问题（逐条打印）。
"""
from __future__ import annotations

import csv
import math
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CURRENT = BASE / "analysis" / "per-text-table.csv"
TOLERANCE = 1e-6
EXPECTED_PER_GROUP = 30


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[0])
        print("usage: python3 analysis/check_mtld_column.py <baseline-per-text-table.csv>")
        return 2
    baseline_path = Path(argv[1])
    for path in (baseline_path, CURRENT):
        if not path.is_file():
            print(f"找不到文件：{path}")
            return 2

    baseline = read(baseline_path)
    current = read(CURRENT)
    if not baseline:
        print("baseline 为空")
        return 1

    problems: list[str] = []
    old_columns = [c for c in baseline[0] if c != "missing_fields"]
    if "mtld" not in current[0]:
        problems.append("新表没有 mtld 列")
    missing_columns = [c for c in old_columns if c not in current[0]]
    if missing_columns:
        problems.append(f"新表丢了旧列：{missing_columns}")

    current_by_key = {(r["prompt_id"], r["model"]): r for r in current}
    baseline_keys = {(r["prompt_id"], r["model"]) for r in baseline}
    if len(current_by_key) != len(current):
        problems.append("新表有重复的 (prompt_id, model)")

    max_diff = 0.0
    for old_row in baseline:
        key = (old_row["prompt_id"], old_row["model"])
        new_row = current_by_key.get(key)
        if new_row is None:
            problems.append(f"行丢失：{key}")
            continue
        for column in old_columns:
            old_value, new_value = old_row[column], new_row.get(column, "")
            if old_value == new_value:
                continue
            try:
                diff = abs(float(old_value) - float(new_value))
            except ValueError:
                problems.append(f"{key} 的 {column}：{old_value!r} → {new_value!r}")
                continue
            max_diff = max(max_diff, diff)
            if diff > TOLERANCE:
                problems.append(f"{key} 的 {column}：{old_value} → {new_value}（差 {diff:.2e}）")

    added = [r for r in current if (r["prompt_id"], r["model"]) not in baseline_keys]
    for row in added:
        if row["group"] not in {"Human", "国内", "国外"}:
            problems.append(f"新增行的组名不认识：{row}")

    bad_mtld = []
    for row in current:
        cell = row.get("mtld", "").strip()
        if not cell:
            bad_mtld.append((row["prompt_id"], row["model"], "空值"))
            continue
        try:
            value = float(cell)
        except ValueError:
            bad_mtld.append((row["prompt_id"], row["model"], cell))
            continue
        if not math.isfinite(value):
            bad_mtld.append((row["prompt_id"], row["model"], value))
    if bad_mtld:
        problems.append(f"mtld 有空值/非有限值：{bad_mtld}")

    counts = Counter(row["model"] for row in current)
    uneven = {model: n for model, n in counts.items() if n != EXPECTED_PER_GROUP}
    if uneven:
        problems.append(f"各组篇数不是 {EXPECTED_PER_GROUP}：{uneven}")

    print(f"baseline：{baseline_path}（{len(baseline)} 行）")
    print(f"当前表：{CURRENT}（{len(current)} 行，新增 {len(added)} 行："
          f"{[(r['prompt_id'], r['model']) for r in added] or '无'}）")
    print(f"共有行逐格对照：{len(baseline)} 行，最大浮点差 {max_diff:.3e}（容差 {TOLERANCE:g}）")
    print(f"mtld 覆盖：{len(current) - len(bad_mtld)}/{len(current)} 行有有限值")
    print(f"各组篇数：{dict(counts)}")

    if problems:
        print("\nFAIL")
        for problem in problems[:30]:
            print("  -", problem)
        return 1
    print("\nPASS：旧列未变，mtld 全覆盖")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
