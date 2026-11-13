
## [10:20] topic-pulse Trends 資料來源決策
第一版用 SerpApi（urllib，不加 pytrends 依賴），官方 Trends API 已申請、核准後另開票。
trends.json 用 `source`/`scale` 欄位與 null=不支援／[]=無結果 隔離來源差異。需求：docs/topic-pulse-google-trends.md
