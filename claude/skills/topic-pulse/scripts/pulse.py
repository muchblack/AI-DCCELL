#!/usr/bin/env python3
"""topic-pulse 輔助腳本。

  pulse.py check <run_dir> [--spot N]   檢查 raw/*.json，印 FAIL/WARN 與抽查網址；有 FAIL 則 exit 1
  pulse.py html <report.md> [--hue N]  把 report.md 轉成同目錄 report.html；N＝配色色相 0–359（預設 210）
  pulse.py trends <run_dir> [--provider serpapi|google]  取得搜尋熱度並寫入 trends.json
  pulse.py selftest                     自我檢查
"""
import json
import os
import random
import re
import sys
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen
from urllib.error import HTTPError

# 平台名 → 允許的網域（後綴比對）。媒體類（kind=media）不比對網域。
PLATFORM_DOMAINS = {
    "巴哈姆特": ["gamer.com.tw"],
    "PTT": ["ptt.cc"],
    "Dcard": ["dcard.tw"],
    "Mobile01": ["mobile01.com"],
    "Plurk": ["plurk.com"],
    "Threads": ["threads.net", "threads.com"],
    "Facebook": ["facebook.com", "fb.com"],
    "Instagram": ["instagram.com"],
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
BARE_URL = re.compile(r"(`[^`\n]*`)|(?<![(<])(https?://[A-Za-z0-9\-._~:/?#\[\]@!$&'*+,;=%\u3400-\u9fff]+)")


# 清單緊接在一般段落後（如「**第一手**\n- ...」）時，Python-Markdown 會併成同一段；補空行
LIST_AFTER_PARA = re.compile(r"(?m)^(?![-*] |\s*$)(.+)\n(?=[-*] )")


# Python-Markdown 的巢狀清單要縮排 4 格；2–3 格（常見寫法）會被攤平成同一層
NESTED_LIST = re.compile(r"(?m)^ {2,3}(?=[-*] )")


def autolink(text):
    text = NESTED_LIST.sub("    ", LIST_AFTER_PARA.sub(r"\1\n\n", text))
    return BARE_URL.sub(lambda m: m.group(1) or f"<{m.group(2)}>", text)


# 報告樣式：整套顏色由單一色相 --h 推出（主色、淺底、帶色偏的灰），配色跟著話題換，版面不變
HTML_CSS = """
:root{--h:210;--bg:hsl(var(--h) 30% 98%);--sf:#fff;--fg:hsl(var(--h) 14% 15%);--mut:hsl(var(--h) 8% 42%);
--line:hsl(var(--h) 25% 89%);--acc:hsl(var(--h) 55% 42%);--acc-soft:hsl(var(--h) 60% 94%);
--ok:#3f7350;--ok-soft:#e3efe6;--warn:#8a5f10;--warn-soft:#fbf0d9;--bad:#a33a3a;--bad-soft:#f7e1e1;
--f-d:"Huninn","Noto Sans TC","PingFang TC",sans-serif;--f-b:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;
--f-m:"IBM Plex Mono",ui-monospace,Menlo,monospace}
@media (prefers-color-scheme:dark){:root{--bg:hsl(var(--h) 12% 9%);--sf:hsl(var(--h) 10% 13%);--fg:hsl(var(--h) 20% 93%);
--mut:hsl(var(--h) 8% 64%);--line:hsl(var(--h) 10% 22%);--acc:hsl(var(--h) 75% 74%);--acc-soft:hsl(var(--h) 30% 20%);
--ok:#8fc29d;--ok-soft:#1f3326;--warn:#e6b85c;--warn-soft:#3a2f17;--bad:#ec8f8f;--bad-soft:#3d2121;color-scheme:dark}}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);margin:0;font:16px/1.75 var(--f-b);padding:40px max(16px,env(safe-area-inset-right)) 64px max(16px,env(safe-area-inset-left))}
main{max-width:760px;margin:0 auto}
h1,h2{font-family:var(--f-d);font-weight:400;text-wrap:balance;line-height:1.35}
h1{font-size:clamp(1.7rem,4.6vw,2.4rem);margin:0 0 16px}
h2{font-size:1.35rem;margin:48px 0 14px;padding-top:20px;border-top:1px solid var(--line)}
h3{font-size:1rem;margin:24px 0 8px}
a{color:var(--acc);text-underline-offset:3px;word-break:break-all}
blockquote{margin:12px 0;padding:12px 16px;background:var(--sf);border:1px solid var(--line);border-left:3px solid var(--acc);border-radius:0 10px 10px 0}
blockquote p{margin:0}
table{border-collapse:collapse;display:block;overflow-x:auto;background:var(--sf);border:1px solid var(--line);border-radius:10px;font-size:.9rem}
th,td{text-align:left;padding:9px 14px;border-top:1px solid var(--line);vertical-align:top}
thead th{border-top:0;font-weight:500;color:var(--mut);font-size:.8rem;white-space:nowrap}
td:first-child{white-space:nowrap;font-variant-numeric:tabular-nums}
code{font-family:var(--f-m);font-size:.85em;background:var(--acc-soft);padding:1px 5px;border-radius:4px}
li{margin:4px 0}
.chip{font-size:.8rem;padding:2px 10px;border-radius:99px;white-space:nowrap}
.full{background:var(--ok-soft);color:var(--ok)}.partial{background:var(--warn-soft);color:var(--warn)}.blocked{background:var(--bad-soft);color:var(--bad)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin:20px 0 8px}
.cards div{background:var(--sf);padding:14px 16px;display:grid;gap:4px;align-content:start}
.cards small{color:var(--mut);font-size:.78rem}.cards b{font-family:var(--f-d);font-weight:400;font-size:1.2rem}.cards span{font-size:.82rem;color:var(--mut)}
figure.chart{margin:12px 0;background:var(--sf);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.chart svg{width:100%;height:auto;display:block}.chart figcaption{font-size:.82rem;color:var(--mut)}
.n{font-family:var(--f-m);font-size:.8rem;color:var(--acc);margin-right:10px}
.lede{font-size:1.08rem}
.callout{border-left:3px solid var(--warn);background:var(--warn-soft);padding:12px 16px;border-radius:0 8px 8px 0;margin:12px 0}
.callout h3{margin:0 0 6px}.callout ul{margin:0;padding-left:1.2em}
.facts{display:grid;grid-template-columns:7.5em 1fr;gap:8px 16px}.facts dt{color:var(--mut);font-size:.9rem}.facts dd{margin:0;min-width:0}
.tl{list-style:none;margin:0;padding:0}
.tl li,.watch li{display:grid;grid-template-columns:6.2em 1fr;gap:16px;margin:0;padding:10px 0;border-top:1px dashed var(--line)}
.tl li:first-child,.watch li:first-child{border-top:0}
.tl time,.watch time{font-family:var(--f-m);font-size:.85rem;color:var(--mut);font-variant-numeric:tabular-nums;padding-top:2px}
.watch{list-style:none;margin:0;padding:0}.watch time{color:var(--acc)}
.src{font-size:.82rem}
li.q{list-style:none;margin-left:-1.2em}
figure.quote{margin:12px 0;padding:14px 16px;background:var(--sf);border:1px solid var(--line);border-radius:10px}
figure.quote blockquote{margin:0 0 8px;padding:0;border:0;background:none;font-size:1.02rem}
figure.quote figcaption{font-size:.82rem;color:var(--mut)}
figure.quote .tr{margin:0 0 8px;font-size:.92rem;color:var(--mut)}
.groups{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.groups div{border-top:2px solid var(--acc);padding-top:10px}.groups h3{margin:0 0 4px}.groups p{margin:0;font-size:.92rem;color:var(--mut)}
.path{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:6px 4px;align-items:center;font-size:.9rem}
.path li{margin:0;background:var(--sf);border:1px solid var(--line);border-radius:8px;padding:4px 10px}
.path li.arrow{border:0;background:none;padding:0;color:var(--mut)}.path li span{font-family:var(--f-m);font-size:.75rem;color:var(--mut);margin-right:6px}
details{border:1px solid var(--line);border-radius:10px;background:var(--sf);padding:12px 16px}summary{cursor:pointer;font-weight:500}details ul{font-size:.85rem}
@media (max-width:480px){.tl li,.watch li,.facts{grid-template-columns:1fr;gap:2px}}
.chart text{font:11px var(--f-m);fill:var(--mut)}.chart .v{fill:var(--fg)}.chart .grid{stroke:var(--line)}
.chart .bar{fill:var(--line)}.chart .bar.on{fill:var(--acc)}.chart .ev{stroke:var(--acc);stroke-dasharray:3 3;opacity:.6}
"""


REGION_NAMES = {"zh-tw": "台灣", "zh-cn": "中國", "en": "美國", "ja": "日本", "ko": "韓國"}


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def summary_cards(run, md_text):
    """報告開頭的總結卡片：數字全取自 RUN 內的檔案，缺檔就少一張，不臆測。"""
    from html import escape
    cards = []
    status = (load_json(run / "verify.json") or {}).get("status")
    label = {"confirmed": ("屬實", "full"), "partial": ("部分屬實", "partial"), "not_found": ("查無此事", "blocked")}.get(status)
    if label:
        cards.append(("事件查證", label[0], f'<em class="chip {label[1]}">{escape(status)}</em>'))
    raws = [d for f in sorted((run / "raw").glob("*.json")) if (d := load_json(f))]
    if raws:
        items = [i for d in raws for i in d.get("items", [])]
        media = sum(i.get("kind") == "media" for i in items)
        cards.append(("取樣", f"{len(items)} 則", f"媒體 {media}・社群 {len(items) - media}"))
        cov = [pl.get("coverage") for d in raws if d.get("region") != "media" for pl in d.get("platforms", [])]
        trends = (load_json(run / "trends.json") or {}).get("status")
        if trends:
            cov.append({"ok": "full", "partial": "partial", "unavailable": "blocked"}.get(trends))
        cards.append(("平台覆蓋", f"{len(cov)} 個", "・".join(f"{k} {cov.count(k)}" for k in ("full", "partial", "blocked") if k in cov)))
    m = re.search(r"未證實條目（(\d+)）", md_text)
    if m:
        cards.append(("未證實", f"{m.group(1)} 條", "見附錄"))
    if not cards:
        return ""
    cells = "".join(f"<div><small>{a}</small><b>{b}</b><span>{c}</span></div>" for a, b, c in cards)
    return f'<div class="cards">{cells}</div>'


def trend_chart(series, events, title):
    """series: [(YYYY-MM-DD, 0–100)]；events: 落在期間內的時間軸日期。回傳 inline SVG。"""
    from html import escape
    W, H, L, R, T, B = 720, 170, 34, 8, 12, 30
    n = len(series)
    cw, ch = (W - L - R) / n, H - T - B
    idx = {d: i for i, (d, _) in enumerate(series)}
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{escape(title)}">']
    for y in (0, 50, 100):
        py = T + ch - y / 100 * ch
        out.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{py:.1f}" y2="{py:.1f}"/>'
                   f'<text x="{L - 6}" y="{py + 4:.1f}" text-anchor="end">{y}</text>')
    for d in events:
        x = L + cw * (idx[d] + .5)
        out.append(f'<line class="ev" x1="{x:.1f}" x2="{x:.1f}" y1="{T}" y2="{T + ch}"><title>{d}</title></line>')
    for i, (d, v) in enumerate(series):
        h = max(v / 100 * ch, 1.5)
        x = L + cw * i
        out.append(f'<rect class="bar{" on" if v else ""}" x="{x + cw * .1:.1f}" y="{T + ch - h:.1f}" '
                   f'width="{cw * .8:.1f}" height="{h:.1f}" rx="1.5"><title>{d}：{v}</title></rect>')
        if v == 100 or (v and n <= 45):
            out.append(f'<text class="v" x="{x + cw / 2:.1f}" y="{T + ch - h - 4:.1f}" text-anchor="middle">{v}</text>')
    for i in sorted({0, n // 3, 2 * n // 3, n - 1}):
        out.append(f'<text x="{L + cw * (i + .5):.1f}" y="{H - 10}" text-anchor="middle">{series[i][0][5:].replace("-", "/")}</text>')
    return "".join(out) + "</svg>"


def trend_figures(run):
    """各區一張熱度長條圖：畫出高峰所屬關鍵字的時間序列，虛線為 verify.json 時間軸事件。"""
    from html import escape
    trends = load_json(run / "trends.json") or {}
    timeline = (load_json(run / "verify.json") or {}).get("timeline", [])
    figs = []
    for region, r in (trends.get("regions") or {}).items():
        peak, tl = r.get("peak"), r.get("timeline") or []
        if not peak or not tl:
            continue
        kw = peak["keyword"]
        series = [(t["date"], int(t.get("values", {}).get(kw) or 0)) for t in tl]
        dates = {d for d, _ in series}
        events = sorted({e.get("date") for e in timeline} & dates)
        name = REGION_NAMES.get(region, region)
        cap = f"「{escape(kw)}」{name} Google 搜尋熱度（0–100 相對指數）"
        if events:
            cap += "。虛線：" + "、".join(d[5:].replace("-", "/") for d in events)
        figs.append(f'<figure class="chart">{trend_chart(series, events, cap)}<figcaption>{cap}</figcaption></figure>')
    return "".join(figs)


def _link_label(m):
    from urllib.parse import unquote
    href, text = m.group(1), m.group(2)
    return f'<a href="{href}">{unquote(text) if text == href else text}</a>'


def _timeline(sec):
    def row(m):
        date, event, src = m.groups()
        src = re.sub(r'(<a href="([^"]+)">)[^<]*</a>', lambda a: a.group(1) + urlparse(a.group(2)).netloc.removeprefix("www.") + "</a>", src)
        return f'<li><time>{date}</time><div>{event}<div class="src">{src}</div></div></li>'
    return re.sub(r"<table>\s*<thead>\s*<tr>\s*<th>日期</th>.*?</thead>\s*<tbody>(.*?)</tbody>\s*</table>",
                  lambda t: '<ol class="tl">' + re.sub(r"<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>\s*", row, t.group(1)) + "</ol>",
                  sec, flags=re.S)


def _quotes(sec):
    # 「- 來源（平台）：「原文」譯：譯文 [連結](url)」單引文條目 → 引用卡片（譯文可省）；一條多段引文的維持原樣
    def card(m):
        src, quote, tr, url = m.groups()
        tr = f'<p class="tr">譯：{tr}</p>' if tr else ""
        return (f'<li class="q"><figure class="quote"><blockquote>{quote}</blockquote>{tr}'
                f'<figcaption>{src}・<a href="{url}">原文</a></figcaption></figure></li>')
    return re.sub(r'<li>([^<：「]{1,60})：「(.+?)」\s*(?:譯：([^<]*?)\s*)?<a href="([^"]+)">[^<]*</a></li>', card, sec)


def _groups(sec):
    def cards(m):
        items = re.findall(r"<li><strong>(.*?)</strong>：(.*?)</li>", m.group(1))
        if len(items) != m.group(1).count("<li>"):
            return m.group(0)
        return '<div class="groups">' + "".join(f"<div><h3>{a}</h3><p>{b}</p></div>" for a, b in items) + "</div>"
    return re.sub(r"<ul>(.*?)</ul>", cards, sec, count=1, flags=re.S)


def _facts(sec):
    def dl(m):
        items = re.findall(r"<li>([^<：]{2,10})：(.*?)</li>", m.group(1))
        if not items or len(items) != m.group(1).count("<li>"):
            return m.group(0)
        return '<dl class="facts">' + "".join(f"<dt>{a}</dt><dd>{b}</dd>" for a, b in items) + "</dl>"
    return re.sub(r"<ul>(.*?)</ul>", dl, sec, count=1, flags=re.S)


def _path(sec):
    def chips(m):
        text, _, tail = m.group(1).partition("。")
        steps = []
        for piece in text.split("→"):
            d = re.search(r"（([^）]+)）\s*$", piece)
            label = piece[:d.start()] if d else piece
            steps.append(f'<li>{f"<span>{d.group(1)}</span>" if d else ""}{label.strip()}</li>')
        out = '<ol class="path">' + '<li class="arrow" aria-hidden="true">→</li>'.join(steps) + "</ol>"
        return out + (f'<p class="muted">{tail}</p>' if tail.strip() else "")
    return re.sub(r"<p>([^<]*→[^<]*)</p>", chips, sec, count=1)


def _watch(sec):
    def rows(m):
        lis = re.findall(r"<li>(.*?)</li>", m.group(1), flags=re.S)
        out = []
        for li in lis:
            d = re.match(r"(\d[^：<]{3,20}|未定[^：<]{0,10})：(.*)", li, flags=re.S)
            out.append(f"<li><time>{d.group(1)}</time><span>{d.group(2)}</span></li>" if d else f"<li><time>持續</time><span>{li}</span></li>")
        return '<ul class="watch">' + "".join(out) + "</ul>"
    return re.sub(r"<ul>(.*?)</ul>", rows, sec, count=1, flags=re.S)


def _appendix(sec):
    return re.sub(r"<h3>((?:來源清單|搜尋指令)[^<]*)</h3>\s*<ul>(.*?)</ul>",
                  lambda m: f'<details><summary>{m.group(1)}（{m.group(2).count("<li>")}）</summary><ul>{m.group(2)}</ul></details>',
                  sec, flags=re.S)


SECTION_STYLES = [("一句話總結", lambda s: s.replace("<p>", '<p class="lede">', 1)), ("事件查證", _facts),
                  ("時間軸", _timeline), ("媒體", _quotes), ("社群反應", _quotes), ("族群", _groups),
                  ("擴散路徑", _path), ("待觀察", _watch), ("附錄", _appendix)]


def enhance(body):
    """把 report.md 固定格式的各節轉成對應版面元件；不符合預期格式的段落原樣保留。"""
    body = re.sub(r'<a href="([^"]+)">([^<]*)</a>', _link_label, body)
    body = re.sub(r"<p>⚠️\s*([^<]*?)：?</p>\s*(<ul>.*?</ul>)",
                  r'<div class="callout"><h3>&#9888;&#65039; \1</h3>\2</div>', body, flags=re.S)
    body = re.sub(r"⚠️ ?(未證實|無法驗證)", r'<span class="chip partial">\1</span>', body)
    parts = re.split(r"(?=<h2>)", body)
    for i, sec in enumerate(parts):
        title = re.match(r"<h2>(.*?)</h2>", sec)
        if not title:
            continue
        for key, fn in SECTION_STYLES:
            if key in title.group(1):
                sec = fn(sec)
                break
        parts[i] = re.sub(r"^<h2>(\d+)\. ", lambda m: f'<h2><span class="n">{int(m.group(1)):02d}</span>', sec)
    return "".join(parts)


def cmd_html(md_path, hue=210):
    import markdown

    md = Path(md_path)
    text = md.read_text(encoding="utf-8")
    body = markdown.markdown(autolink(text), extensions=["tables", "fenced_code"])
    run = md.parent
    body = body.replace("</h1>", "</h1>" + summary_cards(run, text), 1)
    body = re.sub(r"(<h2>[^<]*搜尋熱度[^<]*</h2>)", lambda m: m.group(1) + trend_figures(run), body, count=1)
    body = re.sub(r"<td>(full|partial|blocked)</td>", r'<td><span class="chip \1">\1</span></td>', body)
    body = enhance(body)
    title = re.search(r"<h1>(.*?)</h1>", body)
    fonts = "https://fonts.googleapis.com/css2?family=Huninn&family=Noto+Sans+TC:wght@400;500;700&family=IBM+Plex+Mono&display=swap"
    out = md.with_suffix(".html")
    out.write_text(
        f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        f"<title>{re.sub('<[^>]+>', '', title.group(1)) if title else md.stem}</title>"
        f'<link rel="stylesheet" href="{fonts}"><style>{HTML_CSS}:root{{--h:{hue}}}</style></head>'
        f"<body><main>{body}</main></body></html>",
        encoding="utf-8",
    )
    print(out)
    return 0


TREND_REGIONS = {"zh-tw": "TW", "zh-cn": "", "en": "US", "ja": "JP", "ko": "KR"}


def send_serpapi(params):
    with urlopen("https://serpapi.com/search.json?" + urlencode(params), timeout=30) as response:
        return json.load(response)


def explore_url(data, params):
    url = data.get("search_metadata", {}).get("google_trends_url", "")
    if urlparse(url).path == "/trends/explore":
        return url
    query = {k: params[k] for k in ("date", "geo", "q") if params.get(k)}
    return "https://trends.google.com/trends/explore?" + urlencode(query)


def normalize_trends(data, kind, words):
    if kind == "TIMESERIES":
        timeline = [{
            "date": datetime.fromtimestamp(int(p["timestamp"]), timezone.utc).date().isoformat(),
            "values": {v["query"]: int(v["extracted_value"]) for v in p.get("values", [])},
            "partial": bool(p.get("partial_data"))}
            for p in data.get("interest_over_time", {}).get("timeline_data", [])]
        peaks = [{"date": p["date"], "keyword": word, "value": p["values"][word]}
                 for p in timeline for word in words if word in p["values"]]
        peak = min(peaks, key=lambda p: (-p["value"], p["date"], words.index(p["keyword"]))) if peaks else None
        return {"timeline": timeline, "peak": peak}
    if kind == "RELATED_QUERIES":
        related = data.get("related_queries", {})
        rising, top = related.get("rising", []), related.get("top", [])
        return {
            "rising": None if rising is None else [{"query": v["query"], "value": v["value"]} for v in rising[:10]],
            "top": None if top is None else [{"query": v["query"], "value": int(v["extracted_value"])} for v in top[:10]]}
    countries = data.get("interest_by_region", [])
    return {"top_countries": None if countries is None else [
        {"country": v["location"], "value": int(v["extracted_value"])}
        for v in sorted(countries, key=lambda v: -int(v["extracted_value"]))[:10]]}


def fetch_serpapi(verify, timeframe, key, send):
    regions = {}
    keywords = verify.get("keywords", {})
    selected = {r: keywords[r][:5] for r in TREND_REGIONS if isinstance(keywords.get(r), list) and keywords[r]}
    primary = (selected.get("en") or next(iter(selected.values())))[0]

    def request(kind, q, geo, unit, words=()):
        params = {"engine": "google_trends", "q": q, "data_type": kind, "date": timeframe, "api_key": key}
        if geo:
            params["geo"] = geo
        if kind in ("TIMESERIES", "GEO_MAP_0"):
            unit["explore_url"] = explore_url({}, params)
        for attempt in range(2):
            try:
                data = send(params)
                break
            except Exception as e:
                reason = str(e)
                if isinstance(e, HTTPError):
                    try:
                        reason = json.load(e).get("error", reason)
                    except Exception:
                        pass
                if attempt == 1:
                    data = {"error": reason}
        try:
            if "error" in data:
                raise ValueError(data["error"])
            fields = normalize_trends(data, kind, words)
            search_id = data.get("search_metadata", {}).get("id")
            if kind in ("TIMESERIES", "GEO_MAP_0"):
                fields["explore_url"] = explore_url(data, params)
            if search_id:
                unit["search_ids"].append(search_id)
            unit.update(fields)
        except Exception as e:
            unit["status"] = "error"
            unit["reason"] += ("；" if unit["reason"] else "") + f"{kind}：{e}"

    for region, words in selected.items():
        unit = {"geo": TREND_REGIONS[region], "keywords": words, "status": "ok", "reason": "",
                "search_ids": [], "explore_url": "", "timeline": [], "peak": None, "rising": [], "top": []}
        regions[region] = unit
        if region == "zh-cn":
            unit.update(status="skipped", reason="Google 在中國無資料")
            continue
        request("TIMESERIES", ",".join(words), unit["geo"], unit, words)
        request("RELATED_QUERIES", words[0], unit["geo"], unit)
    worldwide = {"keyword": primary, "status": "ok", "reason": "", "search_ids": [], "explore_url": "", "top_countries": []}
    request("GEO_MAP_0", primary, "", worldwide)
    units = [u for u in regions.values() if u["status"] != "skipped"] + [worldwide]
    successes = sum(u["status"] == "ok" for u in units)
    status = "ok" if successes == len(units) else "partial" if successes else "unavailable"
    reason = "" if successes else "所有查詢都失敗：" + units[0]["reason"]
    return {"status": status, "reason": reason, "regions": regions, "worldwide": worldwide}


def fetch_google(verify, timeframe, key, send):
    return {"status": "unavailable", "reason": "官方 API 尚未實作"}


TREND_PROVIDERS = {"serpapi": fetch_serpapi, "google": fetch_google}


def redact_trends(value, key):
    if isinstance(value, str):
        value = re.sub(r"([?&])api_key=[^&\s\"'<>]*&?", lambda m: m[1] if m[0].endswith("&") else "", value)
        return value.replace(key, "[REDACTED]") if key else value
    if isinstance(value, dict):
        return {redact_trends(k, key): redact_trends(v, key) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_trends(v, key) for v in value]
    return value


def cmd_trends(run_dir, provider="serpapi", key=None, send=None):
    key = os.environ.get("SERPAPI_API_KEY", "") if key is None else key
    out = Path(run_dir, "trends.json")
    result = {"status": "unavailable", "reason": "", "source": provider, "scale": "per_request_0_100",
              "fetched_at": datetime.now().astimezone().isoformat(), "timeframe": "today 3-m", "regions": {}, "worldwide": {}}
    if provider == "google":
        result.update(TREND_PROVIDERS[provider]({}, result["timeframe"], key, send))
    elif not key:
        result["reason"] = "未設定 SERPAPI_API_KEY"
    else:
        try:
            verify = json.loads(Path(run_dir, "verify.json").read_text(encoding="utf-8"))
            if not isinstance(verify, dict):
                raise ValueError("verify.json 必須是物件")
            if not isinstance(verify.get("keywords", {}), dict):
                raise ValueError("verify.json keywords 必須是物件")
        except (OSError, ValueError) as e:
            result["reason"] = f"verify.json 無法讀取或 JSON 無效：{e}"
        else:
            try:
                event = verify.get("event_date", "")
                if not DATE_RE.fullmatch(event):
                    raise ValueError
                # 事件日在未來（如尚未開幕的活動）時以今天為基準，避免起始日晚於結束日
                start = min(date.fromisoformat(event), date.today()) - timedelta(days=30)
                result["timeframe"] = f"{start} {date.today()}"
            except (TypeError, ValueError):
                pass
            if not any(isinstance(verify.get("keywords", {}).get(r), list) and verify["keywords"][r] for r in TREND_REGIONS):
                result["reason"] = "verify.json 沒有關鍵字"
            else:
                result.update(TREND_PROVIDERS[provider](verify, result["timeframe"], key, send or send_serpapi))
    try:
        out.write_text(json.dumps(redact_trends(result, key), ensure_ascii=False), encoding="utf-8")
    except OSError as e:
        print(redact_trends(f"無法寫入 trends.json：{e}", key))
        return 1
    print(redact_trends(f"{result['status']}: {out}", key))
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
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        calls = []
        assert cmd_trends(tmp, key="", send=lambda p: calls.append(p)) == 0
        result = json.loads(Path(tmp, "trends.json").read_text())
        assert result["status"] == "unavailable" and result["reason"] == "未設定 SERPAPI_API_KEY" and not calls
        verify = {"event_date": "2026-10-01", "keywords": {
            "zh-tw": ["甲", "乙"], "zh-cn": ["甲"], "en": ["A"], "ja": ["あ"], "ko": ["가"]}}
        Path(tmp, "verify.json").write_text(json.dumps(verify), encoding="utf-8")
        def fake(params):
            calls.append(params)
            return {
                "search_metadata": {"id": str(len(calls)), "google_trends_url": "https://trends.google.com/trends/explore?test=1"},
                "interest_over_time": {"timeline_data": [
                    {"timestamp": "1790899200", "values": [{"query": "甲", "extracted_value": 100}, {"query": "乙", "extracted_value": 100}]},
                    {"timestamp": "1790812800", "partial_data": True, "values": [{"query": "甲", "extracted_value": 100}]}]},
                "related_queries": {"rising": [{"query": "新詞", "value": "Breakout"}, {"query": "詞", "value": "+110%"}],
                                    "top": [{"query": "熱門", "extracted_value": 99}]},
                "interest_by_region": [{"location": str(i), "extracted_value": i} for i in range(12)]}
        cmd_trends(tmp, key="secret-marker", send=fake)
        result = json.loads(Path(tmp, "trends.json").read_text())
        assert result["status"] == "ok", "正常假資料應成功"
        tw = result["regions"]["zh-tw"]
        assert tw["timeline"] == [
            {"date": "2026-10-02", "values": {"甲": 100, "乙": 100}, "partial": False},
            {"date": "2026-10-01", "values": {"甲": 100}, "partial": True}]
        assert tw["peak"] == {"date": "2026-10-01", "keyword": "甲", "value": 100}
        assert tw["rising"] == [{"query": "新詞", "value": "Breakout"}, {"query": "詞", "value": "+110%"}]
        assert tw["top"] == [{"query": "熱門", "value": 99}]
        assert result["worldwide"]["top_countries"] == [{"country": str(i), "value": i} for i in range(11, 1, -1)]
        assert tw["search_ids"] == ["1", "2"] and result["worldwide"]["search_ids"] == ["9"]
        assert tw["explore_url"] == "https://trends.google.com/trends/explore?test=1"
        assert result["regions"]["zh-cn"]["status"] == "skipped" and result["regions"]["zh-cn"]["reason"] == "Google 在中國無資料"
        assert len(calls) == 9 and [p.get("geo") for p in calls] == ["TW", "TW", "US", "US", "JP", "JP", "KR", "KR", None]
        assert calls[-1]["q"] == "A" and calls[0]["q"] == "甲,乙"
        assert result["timeframe"] == f"2026-09-01 {date.today()}"
        def failing(params):
            if params.get("geo") == "TW" and params["data_type"] == "TIMESERIES":
                return {"error": "額度不足"}
            return fake(params)
        cmd_trends(tmp, key="secret-marker", send=failing)
        result = json.loads(Path(tmp, "trends.json").read_text())
        assert result["status"] == "partial" and result["regions"]["zh-tw"]["reason"] == "TIMESERIES：額度不足", "失敗需保留原文"
        attempts = []
        def timeout(params):
            if params.get("geo") == "TW" and params["data_type"] == "TIMESERIES":
                attempts.append(params)
                raise TimeoutError("逾時 https://serpapi.com/search.json?api_key=secret-marker&q=test")
            return fake(params)
        cmd_trends(tmp, key="secret-marker", send=timeout)
        result = json.loads(Path(tmp, "trends.json").read_text())
        assert len(attempts) == 2 and result["regions"]["zh-tw"]["status"] == "error"
        assert "secret-marker" not in Path(tmp, "trends.json").read_text(), "輸出必須遮蔽金鑰"
        def unsupported(params):
            data = fake(params)
            data["related_queries"] = {"rising": None, "top": None}
            data["interest_by_region"] = None
            data["search_metadata"]["google_trends_url"] = "https://trends.google.com/trends/api/explore?internal=1"
            return data
        cmd_trends(tmp, key="secret-marker", send=unsupported)
        result = json.loads(Path(tmp, "trends.json").read_text())
        assert result["regions"]["zh-tw"]["rising"] is None and result["regions"]["zh-tw"]["top"] is None and result["worldwide"]["top_countries"] is None
        import subprocess
        completed = subprocess.run([sys.executable, __file__, "trends", tmp, "--provider", "google"], capture_output=True, text=True)
        assert completed.returncode == 0, "google 指令入口應成功寫檔"
        result = json.loads(Path(tmp, "trends.json").read_text())
        assert result["status"] == "unavailable" and result["reason"] == "官方 API 尚未實作" and result["source"] == "google"
        from urllib.parse import parse_qs
        expected = {"date": [f"2026-09-01 {date.today()}"], "geo": ["TW"], "q": ["甲,乙"]}
        cmd_trends(tmp, key="secret-marker", send=unsupported)
        result = json.loads(Path(tmp, "trends.json").read_text())
        assert parse_qs(urlparse(result["regions"]["zh-tw"]["explore_url"]).query) == expected
        assert urlparse(result["worldwide"]["explore_url"]).path == "/trends/explore"
        assert parse_qs(urlparse(result["worldwide"]["explore_url"]).query) == {"date": expected["date"], "q": ["A"]}
        def absent_url(params):
            data = fake(params)
            del data["search_metadata"]["google_trends_url"]
            return data
        cmd_trends(tmp, key="secret-marker", send=absent_url)
        result = json.loads(Path(tmp, "trends.json").read_text())
        assert parse_qs(urlparse(result["regions"]["zh-tw"]["explore_url"]).query) == expected
        assert redact_trends("https://a.test/?q=x&api_key=other&date=y secret-marker", "secret-marker") == "https://a.test/?q=x&date=y [REDACTED]"
        assert result["regions"]["zh-tw"]["peak"]["keyword"] == "甲"
        verify.pop("event_date")
        verify["keywords"] = {"zh-tw": ["甲", "乙", "丙", "丁", "戊", "己"]}
        Path(tmp, "verify.json").write_text(json.dumps(verify), encoding="utf-8")
        calls.clear()
        cmd_trends(tmp, key="secret-marker", send=fake)
        result = json.loads(Path(tmp, "trends.json").read_text())
        assert result["timeframe"] == "today 3-m" and calls[0]["q"] == "甲,乙,丙,丁,戊" and calls[-1]["q"] == "甲"
        assert list(result["regions"]) == ["zh-tw"]
        assert result["regions"]["zh-tw"]["peak"]["keyword"] == "甲"
        calls.clear()
        def all_fail(params):
            calls.append(params)
            return {"error": "金鑰無效 secret-marker"}
        cmd_trends(tmp, key="secret-marker", send=all_fail)
        result = json.loads(Path(tmp, "trends.json").read_text())
        assert result["status"] == "unavailable" and result["reason"].startswith("所有查詢都失敗：") and len(calls) == 3
        tw = result["regions"]["zh-tw"]
        assert tw["timeline"] == [] and tw["peak"] is None and tw["rising"] == [] and tw["top"] == [] and tw["search_ids"] == []
        assert "secret-marker" not in Path(tmp, "trends.json").read_text()
        for unit, expected_query in (
            (tw, {"date": ["today 3-m"], "geo": ["TW"], "q": ["甲,乙,丙,丁,戊"]}),
            (result["worldwide"], {"date": ["today 3-m"], "q": ["甲"]}),
        ):
            assert urlparse(unit["explore_url"]).path == "/trends/explore", "失敗請求仍需 explore 連結"
            assert parse_qs(urlparse(unit["explore_url"]).query) == expected_query
        import io
        def http_error(params):
            calls.append(params)
            raise HTTPError("https://a.test/?api_key=secret-marker", 429, "quota", {}, io.BytesIO(b'{"error":"quota secret-marker"}'))
        calls.clear()
        cmd_trends(tmp, key="secret-marker", send=http_error)
        result = json.loads(Path(tmp, "trends.json").read_text())
        assert len(calls) == 6 and "quota [REDACTED]" in result["reason"]
        assert "secret-marker" not in Path(tmp, "trends.json").read_text()
        from http.client import IncompleteRead
        attempts.clear()
        def incomplete(params):
            if params.get("geo") == "TW" and params["data_type"] == "TIMESERIES":
                attempts.append(params)
                raise IncompleteRead(b"")
            return fake(params)
        assert cmd_trends(tmp, key="secret-marker", send=incomplete) == 0
        result = json.loads(Path(tmp, "trends.json").read_text())
        assert len(attempts) == 2 and result["regions"]["zh-tw"]["status"] == "error"
        assert result["status"] == "partial" and "TIMESERIES" in result["regions"]["zh-tw"]["reason"]
        for kind, payload in (
            ("RELATED_QUERIES", {"related_queries": None}),
            ("TIMESERIES", {"interest_over_time": {"timeline_data": [{}]}}),
            ("RELATED_QUERIES", {"related_queries": {"top": [{"query": "缺數值"}]}}),
            ("GEO_MAP_0", {"interest_by_region": [{"location": "缺數值"}]}),
        ):
            attempts.clear()
            def malformed(params):
                if params["data_type"] == kind:
                    attempts.append(params)
                    return payload
                return fake(params)
            assert cmd_trends(tmp, key="secret-marker", send=malformed) == 0
            result = json.loads(Path(tmp, "trends.json").read_text())
            unit = result["worldwide"] if kind == "GEO_MAP_0" else result["regions"]["zh-tw"]
            assert len(attempts) == 1 and unit["status"] == "error" and kind in unit["reason"]
            assert result["status"] == "partial"
            if kind == "RELATED_QUERIES":
                assert unit["rising"] == [] and unit["top"] == [] and unit["peak"] is not None
            elif kind == "TIMESERIES":
                assert unit["timeline"] == [] and unit["peak"] is None and unit["rising"]
            else:
                assert unit["top_countries"] == []
        calls.clear()
        for content in ('{}', '{', '[]'):
            Path(tmp, "verify.json").write_text(content)
            assert cmd_trends(tmp, key="secret-marker", send=fake) == 0
            result = json.loads(Path(tmp, "trends.json").read_text())
            assert result["status"] == "unavailable" and not calls
        Path(tmp, "verify.json").unlink()
        assert cmd_trends(tmp, key="secret-marker", send=fake) == 0 and not calls
        assert cmd_trends(tmp, provider="google", key="secret-marker", send=fake) == 0 and not calls
        for args in (["trends"], ["trends", tmp, "--provider", "unknown"], ["trends", "--provider", "google"]):
            completed = subprocess.run([sys.executable, __file__, *args], capture_output=True, text=True)
            assert completed.returncode == 2 and "pulse.py trends" in completed.stdout
        assert cmd_trends(Path(tmp, "missing"), key="secret-marker", send=fake) != 0
    svg = trend_chart([("2026-10-01", 0), ("2026-10-02", 100)], ["2026-10-02"], "t")
    assert svg.count("<rect") == 2 and svg.count('class="ev"') == 1 and ">100<" in svg
    html_ = enhance('<h2>3. 時間軸</h2><table><thead><tr><th>日期</th><th>事件</th><th>來源</th></tr></thead>'
                    '<tbody><tr><td>2026-10-01</td><td>e ⚠️ 未證實</td><td><a href="https://www.x.com/a">https://www.x.com/a</a></td></tr></tbody></table>'
                    '<h2>9. 擴散路徑</h2><p>A（6/1）→ B。尾巴</p>')
    q = _quotes('<li>官方（YouTube）：「A「B」C」譯：甲 <a href="https://y.tv/1">https://y.tv/1</a></li>')
    assert '<blockquote>A「B」C</blockquote><p class="tr">譯：甲</p>' in q, q
    assert '<time>2026-11（未定）</time>' in _watch('<ul><li>2026-11（未定）：x</li></ul>')
    for needle in ('<span class="n">03</span>', '<ol class="tl">', '>x.com</a>', 'chip partial', '<span>6/1</span>A', '<p class="muted">尾巴'):
        assert needle in html_, needle
    print("selftest OK")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["check"] and len(a) >= 2:
        spot = int(a[a.index("--spot") + 1]) if "--spot" in a else 5
        sys.exit(cmd_check(a[1], spot))
    if a[:1] == ["html"] and len(a) in (2, 4) and a[2:3] in ([], ["--hue"]):
        sys.exit(cmd_html(a[1], *(int(a[3]) % 360,) if len(a) == 4 else ()))
    if a[:1] == ["trends"]:
        if len(a) == 2 and not a[1].startswith("--"):
            sys.exit(cmd_trends(a[1]))
        if len(a) == 4 and not a[1].startswith("--") and a[2] == "--provider" and a[3] in TREND_PROVIDERS:
            sys.exit(cmd_trends(a[1], a[3]))
        print(__doc__)
        sys.exit(2)
    if a[:1] == ["selftest"]:
        sys.exit(selftest())
    print(__doc__)
    sys.exit(2)
