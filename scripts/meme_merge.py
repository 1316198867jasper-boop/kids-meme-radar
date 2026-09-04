#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""meme_merge.py — data.json 增量合并器（2026-08-30 议题实验：少让AI从头再来）

模型不再整体重写 data.json（~90KB/41.5k tokens），只输出当天变更清单 delta，
本脚本负责应用 + 强制 R6 同步（timeChart==hotChart 成员集与 heat 一致、newMemes
必须进 hotChart）+ 排序重写 rank + fresh/heat 沿用 + 校验 + 原子写入 + 失败回滚。

用法:
  python3 scripts/meme_merge.py --data data.json --delta /tmp/meme_delta_YYYY-MM-DD.json --today YYYY-MM-DD

delta JSON 结构（全部字段可选，脚本只应用出现的字段）:
{
  "newMemes":   [{"name","heat","fresh","trend","firstBurst"(Y-M-D), "memeType","verified"}],
  "heatChanges":[{"name","heat","fresh"(可选)","trend"(可选)}],
  "addWiki":    [{完整 wikiEntry 对象}],
  "updateWiki": [{name + 需要合并的字段}],
  "classicMoves": ["梗名"],
  "continuing": [{"name","note"}],
  "radar":      [{"name","detail","probability"}],
  "date":       "YYYY-MM-DD"
}
未覆盖的验证: heat 合理性、卡 C6/P1-P4 内容判断由模型在上游负责（本脚本不做内容判断）。
"""
import argparse, json, os, shutil, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(BASE, "data.json"))
    ap.add_argument("--delta", required=True)
    ap.add_argument("--today", required=True)
    a = ap.parse_args()

    errors = []
    warn = lambda m: print(f"⚠️  {m}")
    fail = lambda m: errors.append(m) or print(f"❌  {m}")

    d = load(a.data)
    delta = load(a.delta)
    today = a.today

    # 备份（保留 2 份，轮换：bak1→bak2，data.json→bak1）
    if os.path.exists(a.data + ".bak1"):
        shutil.copy2(a.data + ".bak1", a.data + ".bak2")
    shutil.copy2(a.data, a.data + ".bak1")

    mt = d.setdefault("masterTable", {})
    hot = mt.setdefault("hotChart", [])
    time_chart = mt.setdefault("timeChart", [])
    wiki = d.setdefault("wikiEntries", [])
    reports = d.setdefault("dailyReports", {})
    classic = mt.setdefault("classic", [])
    by_name = lambda lst: {it["name"]: it for it in lst}

    hot_idx = by_name(hot)
    tc_idx = by_name(time_chart)
    wiki_idx = by_name(wiki)
    hot_set = set(hot_idx)
    tc_set = set(tc_idx)

    date = delta.get("date", today)
    if date != today:
        warn(f"delta.date={date} ≠ --today={today}，以 --today 为准")

    # 1) newMemes → hotChart + timeChart 同步（R6：newMemes 必须进 hotChart）
    new_names = []
    for m in delta.get("newMemes", []):
        name = m["name"]
        new_names.append(name)
        entry = {"rank": 0, "name": name, "heat": m.get("heat"),
                 "fresh": m.get("fresh"), "trend": m.get("trend", "up"),
                 "source": f"{date}日报", "sourceFile": date}
        if "firstBurst" in m:
            entry["time"] = m["firstBurst"]
        for tbl, idx in ((hot, hot_idx), (time_chart, tc_idx)):
            if name in idx:
                old = idx[name]
                for k in ("heat", "fresh", "trend"):
                    if entry.get(k) is not None:
                        old[k] = entry[k]
                old["source"] = entry["source"]
                old["sourceFile"] = entry["sourceFile"]
            else:
                tbl.append(dict(entry))
                idx[name] = tbl[-1]

    # 2) heatChanges → hotChart/timeChart（含新增的 newMemes）
    for c in delta.get("heatChanges", []):
        name = c["name"]
        for idx in (hot_idx, tc_idx):
            if name in idx:
                for k in ("heat", "fresh", "trend"):
                    if c.get(k) is not None:
                        idx[name][k] = c[k]
                # 当日评估过的条目，热度来源同步指向当日日报
                if idx[name].get("source") != f"{date}日报":
                    idx[name]["source"] = f"{date}日报"
                    idx[name]["sourceFile"] = date
            else:
                fail(f"heatChanges 目标 {name} 不在 hotChart/timeChart 中")

    # 3) classicMoves：从两榜移除，进入经典区
    for name in delta.get("classicMoves", []):
        for lst, idx in ((hot, hot_idx), (time_chart, tc_idx)):
            if name in idx:
                lst.remove(idx[name])
                del idx[name]
        if not any(c["name"] == name for c in classic):
            classic.append({"name": name, "peakTime": today, "status": f"已流转经典区（{date}）"})

    # 4) wikiEntries 增/改
    for w in delta.get("addWiki", []):
        if w["name"] in wiki_idx:
            wiki_idx[w["name"]].update(w)
            warn(f"addWiki 的 {w['name']} 已存在 → 已改为合并更新")
        else:
            wiki.append(w)
    for w in delta.get("updateWiki", []):
        if w["name"] in wiki_idx:
            wiki_idx[w["name"]].update(w)
        else:
            fail(f"updateWiki 目标 {w['name']} 不在 wikiEntries 中")

    # 5) dailyReport（覆盖当天）
    reports[date] = {"date": date,
                     "newMemes": delta.get("newMemes", []),
                     "continuing": delta.get("continuing", []),
                     "radar": delta.get("radar", [])}
    d["dailyReports"] = dict(sorted(reports.items()))
    d["availableDates"] = sorted(reports.keys())

    # 6) 排序 + rank 重写（R1/R6）
    hot.sort(key=lambda x: (-x["heat"], -x["fresh"]))
    time_chart.sort(key=lambda x: (-x["fresh"], -x["heat"]))
    for i, it in enumerate(hot, 1):
        it["rank"] = i
    for i, it in enumerate(time_chart, 1):
        it["rank"] = i
    d["lastUpdated"] = date

    # 7) 校验（R6 强制）
    hot_set2 = {it["name"] for it in hot}
    tc_set2 = {it["name"] for it in time_chart}
    if hot_set2 != tc_set2:
        fail(f"R6: timeChart 与 hotChart 成员集不一致 — 仅在hotChart:{hot_set2-tc_set2} 仅在timeChart:{tc_set2-hot_set2}")
    else:
        for it in hot:
            t = tc_idx[it["name"]]
            if t["heat"] != it["heat"]:
                fail(f"R6: {it['name']} heat 不一致 hotChart={it['heat']} timeChart={t['heat']}")
    for i, it in enumerate(hot, 1):
        if it["rank"] != i:
            fail("rank 非顺序")
    for nm in new_names:
        if nm not in hot_set2:
            fail(f"newMemes {nm} 未同步进 hotChart（R6）")

    if errors:
        shutil.copy2(a.data + ".bak1", a.data)
        print(f"❌ 校验失败（{len(errors)} 项），data.json 已回滚到备份。请修复 delta 后重跑。")
        sys.exit(1)

    save_atomic(a.data, d)
    print(f"""✅ 合并完成（{date}）
- hotChart {len(hot)} 条 / timeChart {len(time_chart)} 条（成员与 heat 已校验一致）
- newMemes {len(new_names)} 条（{'、'.join(new_names) or '无'}）已同步进两榜
- wikiEntries {len(wiki)} 条（+{len(delta.get('addWiki',[]))} 新增 / {len(delta.get('updateWiki',[]))} 更新）
- classic 流转 {len(delta.get('classicMoves',[]))} 条（{'、'.join(delta.get('classicMoves',[])) or '无'}）
- dailyReports 更新 {date}，availableDates {len(d['availableDates'])} 天
- 备份: {os.path.basename(a.data)}.bak1""")

if __name__ == "__main__":
    main()