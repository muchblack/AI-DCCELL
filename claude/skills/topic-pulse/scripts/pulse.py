#!/usr/bin/env python3
"""topic-pulse 輔助腳本。

  pulse.py check <run_dir> [--spot N]   檢查 raw/*.json，印 FAIL/WARN 與抽查網址；有 FAIL 則 exit 1
  pulse.py html <report.md>             把 report.md 轉成同目錄 report.html
  pulse.py selftest                     自我檢查
"""
import json
import random
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

# 平台名 → 允許的網域（後綴比對）。媒體類（kind=media）不比對網域。
PLATFORM_DOMAINS = {
    "巴哈姆特": ["gamer.com.tw"],
    "PTT": ["ptt.cc"],
    "Dcard": ["dcard.tw"],
    "Mobile01": ["mobile01.com"],
    "Plurk": ["plurk.com"],
    "Threads": ["threads.net", "threads.com"],
    "Facebook": ["facebook.com", "fb.com"],
    "LIHKG": ["lihkg.com"],
    "微博": ["weibo.com", "weibo.cn"],
    "百度貼吧": ["tieba.baidu.com"],
    "NGA": ["nga.cn", "ngabbs.com", "178.com"],
    "Bilibili": ["bilibili.com", "b23.tv"],
    "知乎": ["zhihu.com"],
    "小紅書": ["xiaohongshu.com", "xhslink.com"],
    "V2EX": ["v2ex.com"],
    "Reddit": ["reddit.com", "redd.it"],
    "X": ["x.com", "twitter.com"],
    "ResetEra": ["resetera.com"],
    "Hacker News": ["news.ycombinator.com"],
    "YouTube": ["youtube.com", "youtu.be"],
    "OpenCritic": ["opencritic.com"],
    "Metacritic": ["metacritic.com"],
    "Steam": ["steamcommunity.com", "store.steampowered.com"],
    "5ch": ["5ch.net", "5ch.io", "bbspink.com"],
    "はてなブックマーク": ["b.hatena.ne.jp"],
    "Yahoo!ニュース": ["news.yahoo.co.jp"],
    "Yahoo!リアルタイム検索": ["search.yahoo.co.jp"],
    "ニコニコ": ["nicovideo.jp"],
    "Ruliweb": ["ruliweb.com"],
    "DC Inside": ["dcinside.com"],
    "Inven": ["inven.co.kr"],
    "Naver": ["naver.com"],
    "theqoo": ["theqoo.net"],
    "Clien": ["clien.net"],
}
COVERAGE = {"full", "partial", "blocked"}
STANCE = {"正面", "負面", "分歧", "中立"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def url_problem(url):
    if not isinstance(url, str) or not url:
        return "缺網址"
    if "..." in url or "…" in url:
        return "網址被省略號截斷"
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.netloc:
        return "網址不完整"
    return None


def domain_ok(platform, url):
    host = urlparse(url).netloc.lower().split(":")[0]
    return any(host == d or host.endswith("." + d) for d in PLATFORM_DOMAINS[platform])


def check_region(data, name):
    """回傳 (fails, warns, urls)。"""
    fails, warns, urls = [], [], []
    listed = {p.get("platform") for p in data.get("platforms", [])}
    for p in data.get("platforms", []):
        if p.get("coverage") not in COVERAGE:
            fails.append(f"{name}: 平台 {p.get('platform')} coverage 不合法：{p.get('coverage')}")
        elif p["coverage"] != "full" and not p.get("reason"):
            fails.append(f"{name}: 平台 {p.get('platform')} 非 full 卻沒寫原因")
    if not data.get("queries"):
        fails.append(f"{name}: 缺 queries")
    for i, it in enumerate(data.get("items", [])):
        tag = f"{name}#{i} {it.get('platform', '?')}"
        url = it.get("url")
        prob = url_problem(url)
        if prob:
            fails.append(f"{tag}: {prob}：{url}")
            continue
        urls.append((tag, url, it.get("quote_orig", "")))
        if not DATE_RE.match(str(it.get("date", ""))):
            fails.append(f"{tag}: 日期需為 YYYY-MM-DD：{it.get('date')}")
        if not it.get("claim"):
            fails.append(f"{tag}: 缺 claim")
        if it.get("stance") not in STANCE:
            fails.append(f"{tag}: stance 不合法：{it.get('stance')}")
        count = it.get("count")
        if count is not None and not isinstance(count, int):
            fails.append(f"{tag}: count 必須是整數或 null：{count!r}")
        if it.get("count_estimated") and not it.get("count_note"):
            fails.append(f"{tag}: 估計值缺 count_note")
        if it.get("kind") == "media":
            continue
        if not it.get("quote_orig"):
            fails.append(f"{tag}: 社群條目缺原文引述")
        plat = it.get("platform")
        if plat not in PLATFORM_DOMAINS:
            warns.append(f"{tag}: 未知平台，無法比對網域：{url}")
        elif not domain_ok(plat, url):
            fails.append(f"{tag}: 平台與網域不符：{url}")
        if plat not in listed:
            warns.append(f"{tag}: 平台未列在 platforms 覆蓋清單")
    return fails, warns, urls


def cmd_check(run_dir, spot):
    raws = sorted(Path(run_dir, "raw").glob("*.json"))
    if not raws:
        print("FAIL: raw/ 底下沒有 *.json")
        return 1
    fails, warns, urls = [], [], []
    for f in raws:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            fails.append(f"{f.name}: JSON 解析失敗：{e}")
            continue
        a, b, c = check_region(data, f.stem)
        fails += a
        warns += b
        urls += c
    for m in fails:
        print("FAIL:", m)
    for m in warns:
        print("WARN:", m)
    for tag, url, quote in random.sample(urls, min(spot, len(urls))):
        print(f"SPOTCHECK: {tag} {url} || {quote[:80]}")
    print(f"SUMMARY: {len(urls)} 條網址，FAIL={len(fails)}，WARN={len(warns)}")
    return 1 if fails else 0


# 裸網址 → <url>（markdown 自動連結）；已在 [](...)、<...>、`...` 裡的不動
BARE_URL = re.compile(r"(`[^`\n]*`)|(?<![(<])(https?://[A-Za-z0-9\-._~:/?#\[\]@!$&'*+,;=%]+)")


# 清單緊接在一般段落後（如「**第一手**\n- ...」）時，Python-Markdown 會併成同一段；補空行
LIST_AFTER_PARA = re.compile(r"(?m)^(?![-*] |\s*$)(.+)\n(?=[-*] )")


def autolink(text):
    text = LIST_AFTER_PARA.sub(r"\1\n\n", text)
    return BARE_URL.sub(lambda m: m.group(1) or f"<{m.group(2)}>", text)


def cmd_html(md_path):
    import markdown

    md = Path(md_path)
    body = markdown.markdown(autolink(md.read_text(encoding="utf-8")), extensions=["tables", "fenced_code"])
    title = re.search(r"<h1>(.*?)</h1>", body)
    css = (
        ":root{--bg:#fff;--fg:#1f2328;--mut:#d0d7de;--acc:#0969da}"
        "@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--mut:#30363d;--acc:#4493f8}}"
        "body{background:var(--bg);color:var(--fg);max-width:880px;margin:0 auto;padding:16px;"
        "font:16px/1.7 -apple-system,'PingFang TC','Noto Sans TC',sans-serif}"
        "a{color:var(--acc);word-break:break-all}table{border-collapse:collapse;display:block;overflow-x:auto}"
        "th,td{border:1px solid var(--mut);padding:6px 10px}blockquote{border-left:3px solid var(--mut);"
        "margin:0;padding-left:12px}"
    )
    out = md.with_suffix(".html")
    out.write_text(
        f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{title.group(1) if title else md.stem}</title><style>{css}</style></head>"
        f"<body>{body}</body></html>",
        encoding="utf-8",
    )
    print(out)
    return 0


def selftest():
    good = {
        "platforms": [{"platform": "PTT", "coverage": "full"}, {"platform": "Plurk", "coverage": "blocked", "reason": "登入牆"}],
        "queries": ["q"],
        "items": [
            {"kind": "community", "platform": "PTT", "url": "https://www.ptt.cc/bbs/C_Chat/M.1.A.E69.html",
             "date": "2026-10-25", "count": 796, "claim": "c", "quote_orig": "q", "stance": "負面"},
            {"kind": "media", "platform": "4Gamers", "url": "https://www.4gamers.com.tw/news/detail/82853",
             "date": "2026-10-25", "count": None, "claim": "c", "stance": "中立"},
        ],
    }
    f, w, u = check_region(good, "t")
    assert not f and not w and len(u) == 2, (f, w)
    bad = {
        "platforms": [{"platform": "Plurk", "coverage": "partial"}],
        "queries": [],
        "items": [
            {"platform": "Plurk", "url": "https://www.ptt.cc/bbs/C_Chat/M.1.html", "date": "2026/10/25",
             "count": "約70", "claim": "c", "quote_orig": "q", "stance": "多數"},
            {"platform": "巴哈姆特", "url": "forum.gamer.com.tw/.../C.php", "date": "2026-10-25"},
        ],
    }
    f, _, _ = check_region(bad, "t")
    joined = "\n".join(f)
    for needle in ("沒寫原因", "缺 queries", "平台與網域不符", "日期需為", "count 必須", "stance 不合法", "省略號"):
        assert needle in joined, needle
    assert autolink("見 https://a.tw/x?y=1（796 推）") == "見 <https://a.tw/x?y=1>（796 推）"
    assert autolink("[t](https://a.tw/x) `site:https://b.tw`") == "[t](https://a.tw/x) `site:https://b.tw`"
    assert autolink("**A**\n- x\n- y") == "**A**\n\n- x\n- y"
    print("selftest OK")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["check"] and len(a) >= 2:
        spot = int(a[a.index("--spot") + 1]) if "--spot" in a else 5
        sys.exit(cmd_check(a[1], spot))
    if a[:1] == ["html"] and len(a) == 2:
        sys.exit(cmd_html(a[1]))
    if a[:1] == ["selftest"]:
        sys.exit(selftest())
    print(__doc__)
    sys.exit(2)
