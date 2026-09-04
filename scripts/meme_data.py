#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""meme_data.py — data.json 紧凑摘要工具（2026-08-30 议题实验：少喂无关材料）
用法:
  python3 scripts/meme_data.py digest             # 打印全库紧凑摘要（供日报模型阅读）
  python3 scripts/meme_data.py entry "梗名"       # 打印单条 wikiEntry 完整字段
  python3 scripts/meme_data.py report "2026-08-2x" # 打印某天日报完整内容
  python3 scripts/meme_data.py stats              # 只打印各表成员名单+计数
数据文件位置可在命令行 --data 覆盖。
"""
import argparse, json, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE, "data.json")

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def compact_item(d, fields):
    parts = []
    for k in fields:
        v = d.get(k)
        if v is None or v == "":
            continue
        s = str(v)
        if len(s) > 160:
            s = s[:157] + "…"
        parts.append(f"{k}={s}")
    return " | ".join(parts)

def digest(d):
    out = []
    out.append(f"# data.json 摘要（{d.get('lastUpdated','?')}，共 {len(d.get('availableDates',[]))} 天日报）")
    mt = d.get("masterTable", {})
    for table in ("hotChart", "timeChart", "potentialChart"):
        items = mt.get(table, [])
        out.append(f"\n## {table}（{len(items)}条）")
        for it in items:
            out.append("- " + compact_item(it, ["rank", "name", "heat", "fresh", "trend", "time", "source"]))
    classic = mt.get("classic", [])
    out.append(f"\n## classic 经典区（{len(classic)}条）")
    for it in classic:
        out.append("- " + compact_item(it, ["name", "peakTime", "status"]))
    pg = mt.get("parentGuide", {})
    if pg:
        out.append(f"\n## parentGuide\n{json.dumps(pg, ensure_ascii=False)}")
    we = d.get("wikiEntries", [])
    out.append(f"\n## wikiEntries 梗百科（{len(we)}条）")
    for it in we:
        out.append("- " + compact_item(it, ["name", "what", "memeType", "verified", "heat", "peakTime"]))
    dr = d.get("dailyReports", {})
    out.append(f"\n## dailyReports（{len(dr)}天：{'、'.join(sorted(dr.keys()))}）")
    return "\n".join(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["digest", "entry", "report", "stats"])
    ap.add_argument("arg", nargs="?", default=None)
    ap.add_argument("--data", default=DATA_PATH)
    a = ap.parse_args()
    d = load(a.data)
    if a.mode == "digest":
        print(digest(d))
    elif a.mode == "stats":
        mt = d.get("masterTable", {})
        for table in ("hotChart", "timeChart", "potentialChart", "classic"):
            items = mt.get(table, [])
            names = "、".join(x.get("name", "?") for x in items)
            print(f"{table}({len(items)}): {names}")
        we = d.get("wikiEntries", [])
        print(f"wikiEntries({len(we)}): " + "、".join(x["name"] for x in we))
        print(f"dailyReports({len(d.get('dailyReports', {}))}天): " + "、".join(sorted(d.get("dailyReports", {}).keys())))
    elif a.mode == "entry":
        name = a.arg
        for it in d.get("wikiEntries", []):
            if it["name"] == name:
                print(json.dumps(it, ensure_ascii=False, indent=1))
                return
        print(f"❌ 未找到 wikiEntry: {name}")
        sys.exit(1)
    elif a.mode == "report":
        date = a.arg
        dr = d.get("dailyReports", {})
        if date in dr:
            print(json.dumps(dr[date], ensure_ascii=False, indent=1))
        else:
            print(f"❌ 未找到日报: {date}（可用：{'、'.join(sorted(dr.keys()))}）")
            sys.exit(1)

if __name__ == "__main__":
    main()