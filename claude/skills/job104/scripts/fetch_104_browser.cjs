// fetch_104.py 的備援：curl 被 Cloudflare 擋時，用真瀏覽器開職缺頁，
// 過了 challenge 之後在同源下呼叫 ajax/content，把 JSON 印到 stdout。
//
// 用法：node fetch_104_browser.cjs <playwright 套件目錄> <job id>
// 套件目錄由 fetch_104.py 解析（pnpm 全域安裝的路徑帶 hash，NODE_PATH 用不了）。

const [pwDir, jid] = process.argv.slice(2);
const { chromium } = require(pwDir);

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36";

(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ userAgent: UA, locale: "zh-TW" });
    await page.goto(`https://www.104.com.tw/job/${jid}`, { waitUntil: "domcontentloaded", timeout: 30000 });
    // Cloudflare challenge 頁的 title 是 "Just a moment..."，等它自己跳走
    await page.waitForFunction(() => !document.title.includes("Just a moment"), null, { timeout: 20000 });
    const body = await page.evaluate(async (id) => {
      const r = await fetch(`/job/ajax/content/${id}`, { headers: { Accept: "application/json" } });
      return r.text();
    }, jid);
    process.stdout.write(body);
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(`playwright 備援失敗：${e.message.split("\n")[0]}`);
  process.exit(1);
});
