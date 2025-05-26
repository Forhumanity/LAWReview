#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flatten LLM-analysis JSON files → one Excel sheet
Edit ONLY `JSON_DIR` and `OUTPUT_FILE` below, then run.
"""

from pathlib import Path
import json
import pandas as pd

# ───--------------------------  👉  EDIT THESE TWO LINES  👈  --------------------------──
JSON_DIR    = Path(r"Result/regulation_20250524_164148/关于进一步引导和规范境外投资方向指导意见")   # 文件夹路径，全部 *_综合分析结果.json 放这里
OUTPUT_FILE = Path(r"Result/regulation_20250524_164148/combined.xlsx")     # 想保存到哪里就填哪里
# ─────────────────────────────────────────────────────────────────────────────

def flatten_single_json(path: Path) -> list[dict]:
    """Return list-of-dict rows for one JSON file (条款级)."""
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)

    rows = []
    for provider, pdata in raw.get("LLM分析结果", {}).items():
        if not isinstance(pdata, dict):
            continue
        meta = {
            "DocumentTitle": pdata.get("文档标题") or pdata.get("文档名称"),
            "PubOrg"       : pdata.get("颁布机构"),
            "EffectiveDate": pdata.get("生效日期"),
            "AnalysisDate" : pdata.get("分析日期"),
            "Provider"     : provider,
        }
        for category, reqs in pdata.get("详细分析", {}).items():
            for req in reqs:
                base = {
                    **meta,
                    "Category"       : category,
                    "RequirementID"  : req.get("框架要求编号"),
                    "RequirementName": req.get("框架要求名称"),
                    "Coverage"       : req.get("法规覆盖情况"),
                    "Implementation" : req.get("实施要求"),
                    "Penalty"        : req.get("处罚措施"),
                }

                # requirement summary row
                rows.append({
                    **base,
                    "ClauseNo"           : None,
                    "SpecificRequirement": None,
                    "Strength"           : None,
                    "Subjects"           : None,
                    "OriginalText"       : None,
                    "RowType"            : "Requirement",
                })

                for c in req.get("法规要求内容", []):
                    rows.append({
                        **base,
                        "ClauseNo"           : c.get("条款编号"),
                        "SpecificRequirement": c.get("具体要求"),
                        "Strength"           : c.get("强制等级"),
                        "Subjects"           : c.get("适用对象"),
                        "OriginalText"       : c.get("原文内容"),
                        "RowType"            : "Finding",
                    })
                if not req.get("法规要求内容", []):
                    # requirement without detailed clauses
                    pass
    return rows


def main() -> None:
    json_files = sorted(JSON_DIR.glob("*_综合分析结果.json"))
    if not json_files:
        raise FileNotFoundError(f"No *_综合分析结果.json in {JSON_DIR}")

    all_rows = []
    for fp in json_files:
        all_rows.extend(flatten_single_json(fp))
        print(f"✓ {fp.name}")

    df = pd.DataFrame(all_rows)
    df.sort_values(by=["RequirementID", "Provider", "RowType", "ClauseNo"],
                   inplace=True, ignore_index=True)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(OUTPUT_FILE, index=False, engine="openpyxl")
    print(f"\nDone → {OUTPUT_FILE.resolve()}  ({len(df):,} rows)")


if __name__ == "__main__":
    main()