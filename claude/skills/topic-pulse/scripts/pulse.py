#!/usr/bin/env python3
"""topic-pulse 輔助腳本。

  pulse.py check <run_dir> [--spot N]   檢查 raw/*.json，印 FAIL/WARN 與抽查網址；有 FAIL 則 exit 1
  pulse.py html <report.md>             把 report.md 轉成同目錄 report.html
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
from urllib.error import HTTPError, URLError

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


def fetch_serpapi(verify, timeframe, key, send):
    regions = {}
    keywords = verify.get("keywords", {})
    selected = {r: keywords[r][:5] for r in TREND_REGIONS if isinstance(keywords.get(r), list) and keywords[r]}
    primary = (selected.get("en") or next(iter(selected.values())))[0]

    def request(kind, q, geo, unit):
        params = {"engine": "google_trends", "q": q, "data_type": kind, "date": timeframe, "api_key": key}
        if geo:
            params["geo"] = geo
        for attempt in range(2):
            try:
                data = send(params)
                break
            except (OSError, URLError) as e:
                reason = str(e)
                if isinstance(e, HTTPError):
                    try:
                        reason = json.load(e).get("error", reason)
                    except (OSError, ValueError, AttributeError):
                        pass
                if attempt == 1:
                    data = {"error": reason}
            except ValueError as e:
                data = {"error": str(e)}
                break
        if "error" in data:
            unit["status"] = "error"
            unit["reason"] += ("；" if unit["reason"] else "") + f"{kind}：{data['error']}"
            return {}
        search_id = data.get("search_metadata", {}).get("id")
        if search_id:
            unit["search_ids"].append(search_id)
        if kind in ("TIMESERIES", "GEO_MAP_0"):
            unit["explore_url"] = explore_url(data, params)
        return data

    for region, words in selected.items():
        unit = {"geo": TREND_REGIONS[region], "keywords": words, "status": "ok", "reason": "",
                "search_ids": [], "explore_url": "", "timeline": [], "peak": None, "rising": [], "top": []}
        regions[region] = unit
        if region == "zh-cn":
            unit.update(status="skipped", reason="Google 在中國無資料")
            continue
        data = request("TIMESERIES", ",".join(words), unit["geo"], unit)
        for point in data.get("interest_over_time", {}).get("timeline_data", []):
            unit["timeline"].append({
                "date": datetime.fromtimestamp(int(point["timestamp"]), timezone.utc).date().isoformat(),
                "values": {v["query"]: int(v["extracted_value"]) for v in point.get("values", [])},
                "partial": bool(point.get("partial_data"))})
        peaks = [{"date": p["date"], "keyword": word, "value": p["values"][word]}
                 for p in unit["timeline"] for word in words if word in p["values"]]
        if peaks:
            unit["peak"] = min(peaks, key=lambda p: (-p["value"], p["date"], words.index(p["keyword"])))
        related = request("RELATED_QUERIES", words[0], unit["geo"], unit).get("related_queries", {})
        rising, top = related.get("rising", []), related.get("top", [])
        unit["rising"] = None if rising is None else [{"query": v["query"], "value": v["value"]} for v in rising[:10]]
        unit["top"] = None if top is None else [{"query": v["query"], "value": int(v["extracted_value"])} for v in top[:10]]
    worldwide = {"keyword": primary, "status": "ok", "reason": "", "search_ids": [], "explore_url": ""}
    countries = request("GEO_MAP_0", primary, "", worldwide).get("interest_by_region", [])
    worldwide["top_countries"] = None if countries is None else [{"country": v["location"], "value": int(v["extracted_value"])}
                                  for v in sorted(countries, key=lambda v: -int(v["extracted_value"]))[:10]]
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
                result["timeframe"] = f"{date.fromisoformat(event) - timedelta(days=30)} {date.today()}"
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
        import io
        def http_error(params):
            calls.append(params)
            raise HTTPError("https://a.test/?api_key=secret-marker", 429, "quota", {}, io.BytesIO(b'{"error":"quota secret-marker"}'))
        calls.clear()
        cmd_trends(tmp, key="secret-marker", send=http_error)
        result = json.loads(Path(tmp, "trends.json").read_text())
        assert len(calls) == 6 and "quota [REDACTED]" in result["reason"]
        assert "secret-marker" not in Path(tmp, "trends.json").read_text()
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
    print("selftest OK")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["check"] and len(a) >= 2:
        spot = int(a[a.index("--spot") + 1]) if "--spot" in a else 5
        sys.exit(cmd_check(a[1], spot))
    if a[:1] == ["html"] and len(a) == 2:
        sys.exit(cmd_html(a[1]))
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
