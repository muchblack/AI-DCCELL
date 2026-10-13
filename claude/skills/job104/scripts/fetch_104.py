#!/usr/bin/env python3
"""抓 104 職缺 JD，輸出純文字，並可存成「公司-職位.txt」。

用法：
  fetch_104.py <url-or-id> [--save-dir DIR] [--name 公司-職位] [--browser]

104 的頁面有 Cloudflare：WebFetch 回 402、裸 curl 回 403 challenge。
ajax/content 端點帶完整瀏覽器 header 才拿得到 JSON，所以先走 curl；
curl 拿到的不是 JSON（被擋）時，改用 Playwright 開真瀏覽器抓
（fetch_104_browser.cjs）。--browser 直接走瀏覽器。
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


def job_id(arg):
    m = re.search(r"job/([0-9a-z]+)", arg)
    return m.group(1) if m else arg.strip()


def via_curl(jid):
    return subprocess.run(
        ["curl", "-s", f"https://www.104.com.tw/job/ajax/content/{jid}",
         "-H", f"User-Agent: {UA}",
         "-H", "Accept-Language: zh-TW,zh;q=0.9",
         "-H", "Accept: application/json, text/plain, */*",
         "-H", f"Referer: https://www.104.com.tw/job/{jid}"],
        capture_output=True, text=True).stdout


def playwright_dir():
    """pnpm／npm 全域安裝的 playwright 套件目錄（pnpm 11 的路徑帶 hash）。"""
    for tool, pattern in (("pnpm", "*/node_modules/playwright"), ("pnpm", "playwright"),
                          ("npm", "playwright")):
        if not shutil.which(tool):
            continue
        root = subprocess.run([tool, "root", "-g"], capture_output=True, text=True).stdout.strip()
        if root:
            hit = next(Path(root).glob(pattern), None)
            if hit and (hit / "package.json").exists():
                return hit
    return None


def via_browser(jid, reason):
    pw = playwright_dir()
    if not pw:
        sys.exit("找不到全域安裝的 playwright，無法用瀏覽器抓（pnpm add -g playwright）")
    print(f"[playwright] {reason}", file=sys.stderr)
    r = subprocess.run(["node", str(Path(__file__).with_name("fetch_104_browser.cjs")), str(pw), jid],
                       capture_output=True, text=True, timeout=90)
    if r.returncode:
        sys.exit(r.stderr.strip())
    return r.stdout


def fetch(jid, browser=False, reason="--browser 指定直接用瀏覽器"):
    body = via_browser(jid, reason) if browser else via_curl(jid)
    try:
        doc = json.loads(body)
    except json.JSONDecodeError:
        if browser:
            sys.exit(f"抓不到 {jid}：瀏覽器也拿不到 JSON，請改貼 JD 文字")
        return fetch(jid, browser=True, reason="curl 拿不到 JSON（多半是被 Cloudflare 擋），改用瀏覽器")
    if not doc.get("data"):
        sys.exit(f"抓不到 {jid}：104 回應沒有職缺資料（可能已關閉或代碼錯誤）")
    return doc["data"]


def descs(items):
    return [x["description"] for x in items or []]


REMOTE = {1: "完全遠端", 2: "部分遠端"}


def remote(j):
    r = j.get("remoteWork") or {}
    return " ".join(filter(None, [REMOTE.get(r.get("type"), "無"), r.get("description")]))


def render(jid, d):
    h, j, c = d["header"], d["jobDetail"], d["condition"]
    lines = [
        f"來源：https://www.104.com.tw/job/{jid}",
        f"===== {h['jobName']} | {h['custName']} | 更新 {h.get('appearDate')}",
        f"地點 {j.get('addressRegion')} {j.get('addressDetail')} | 薪資 {j.get('salary')}"
        f" | 遠端 {remote(j)}"
        f" | 人數 {j.get('needEmp')}",
        j["jobDescription"],
        f"--經歷 {c.get('workExp')} 學歷 {c.get('edu')}",
        f"技能 {descs(c.get('specialty'))}",
        f"工具 {descs(c.get('skill'))}",
        f"語言 {[(x['language'], x['ability']) for x in c.get('language') or []]}",
        f"其他 {c.get('other')}",
        f"產業 {d.get('industry')} | 職類 {descs(j.get('jobCategory'))}",
    ]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--save-dir")
    ap.add_argument("--name", help="檔名（不含副檔名），慣例為 公司簡稱-職位")
    ap.add_argument("--browser", action="store_true", help="跳過 curl，直接用 Playwright")
    a = ap.parse_args()

    jid = job_id(a.job)
    text = render(jid, fetch(jid, a.browser))
    print(text)
    if a.save_dir:
        if not a.name:
            sys.exit("--save-dir 需要搭配 --name（公司簡稱-職位）")
        path = Path(a.save_dir) / f"{a.name}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(f"[saved] {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
