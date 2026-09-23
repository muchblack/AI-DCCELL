#!/usr/bin/env node
// fetch-page.js — 用 Playwright 直接抓網頁實際渲染後的文字內容
// 用途：/obs compile 遇到裸網址筆記時，取得真實頁面內容餵給摘要步驟
// 不透過任何 LLM 做工具呼叫順序判斷——純腳本，輸出可決定性驗證，不會有幻覺風險
//
// 用法：node fetch-page.js <url>
// 輸出：單行 JSON { ok, title, url, text } 或 { ok: false, error }

const { chromium } = require('/Users/huai-chitzeng/srv/node_modules/playwright');

(async () => {
  const url = process.argv[2];
  if (!url) {
    console.log(JSON.stringify({ ok: false, error: 'no url provided' }));
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent:
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
  });
  const page = await context.newPage();
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);
    const text = await page.evaluate(() => document.body.innerText);
    console.log(JSON.stringify({ ok: true, title: await page.title(), url: page.url(), text }));
  } catch (err) {
    console.log(JSON.stringify({ ok: false, error: String(err) }));
  } finally {
    await browser.close();
  }
})();
