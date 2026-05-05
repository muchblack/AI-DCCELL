# Mandi 架構參考 — 三專案歸納

從 longrock、hello-static、tokyo-statis 三個展覽網站歸納的共通架構模式。

## 1. 頁面骨架（Universal Page Skeleton）

所有頁面共享同一骨架結構：

```
<body data-page="{page-id}">

  <!-- A. 載入動畫（可選） -->
  <div class="loader">...</div>

  <!-- B. 固定框架層（裝飾邊框、火焰邊框等） -->
  <div class="frame fixed inset-0 pointer-events-none z-50">
    <!-- 品牌裝飾邊框 -->
  </div>

  <!-- C. 導航系統 -->
  <header class="site-header">
    <!-- 桌面版：固定頂部水平導航 -->
    <!-- 行動版：漢堡按鈕 + 全螢幕選單覆蓋 -->
  </header>

  <!-- D. Hero 區塊 -->
  <section class="hero">
    <!-- 主視覺圖/影片 + 展覽標題 + 日期場地 -->
  </section>

  <!-- E. 主內容區 -->
  <main class="content">
    <!-- 頁面特定內容區塊 -->
  </main>

  <!-- F. 浮動按鈕（預約 + 回頂部） -->
  <div class="float-buttons fixed right-4 bottom-4 z-40">...</div>

  <!-- G. Footer -->
  <footer>...</footer>

  <!-- H. Modal 覆蓋層（商品頁用） -->
  <div class="modal-overlay" id="modal">...</div>

</body>
```

### data-page 驅動機制

`<body data-page="...">` 屬性用於：
- CSS：`[data-page="goods"] .nav-item--goods { ... }` 控制導航高亮
- JS：`document.body.dataset.page` 條件初始化不同模組

**來源**：tokyo-statis 全面使用、longrock 使用 `data-area` 滾動追蹤。

---

## 2. 導航系統（Navigation）

### 三專案對照

| 面向 | longrock | hello-static | tokyo-statis |
|------|----------|-------------|-------------|
| 桌面導航位置 | 固定右上 | 黏性頂部 | 固定頂部白底 |
| 行動版選單 | 全螢幕覆蓋 | 全螢幕紅底覆蓋 | 側滑紅底面板 |
| 導航項目形式 | 文字連結 | 圖片按鈕 | SVG/PNG 圖片 |
| 漢堡觸發 | `.is-open` toggle | `.show` + `hidden` toggle | `hidden` toggle |
| 頁面連結 | 錨點 `#section` | 混合（錨點 + goods.html） | 獨立頁面 |
| Dropdown | 無 | 無 | Goods/Ticket 有 hover dropdown |

### 推薦模式

```html
<!-- 桌面版固定導航 -->
<nav class="nav hidden md:flex fixed top-0 w-full z-50 bg-white/80 backdrop-blur">
  <a href="/" class="nav__logo"><img src="assets/common/logo.svg" alt="Logo"></a>
  <div class="nav__links">
    <a href="index.html" class="nav__link" data-nav="top">TOP</a>
    <a href="highlights.html" class="nav__link" data-nav="highlights">亮點</a>
    <a href="goods.html" class="nav__link" data-nav="goods">商品</a>
    <a href="ticket.html" class="nav__link" data-nav="ticket">票券</a>
    <a href="faq.html" class="nav__link" data-nav="faq">FAQ</a>
  </div>
</nav>

<!-- 行動版漢堡 + 全螢幕選單 -->
<button class="menu-btn md:hidden fixed top-4 right-4 z-50" id="menu-btn">
  <span class="menu-btn__bar"></span>
  <span class="menu-btn__bar"></span>
  <span class="menu-btn__bar"></span>
</button>

<div class="mobile-menu hidden fixed inset-0 z-40 bg-[var(--color-primary)]" id="mobile-menu">
  <button class="mobile-menu__close" id="menu-close">&times;</button>
  <nav class="mobile-menu__nav">
    <!-- 與桌面版相同連結 -->
  </nav>
</div>
<div class="mobile-overlay hidden fixed inset-0 z-30 bg-black/50" id="mobile-overlay"></div>
```

### 漢堡選單 JS 模式

```javascript
function toggleMobileMenu() {
  const menu = document.getElementById('mobile-menu');
  const overlay = document.getElementById('mobile-overlay');
  const isOpen = !menu.classList.contains('hidden');

  if (isOpen) {
    menu.classList.add('hidden');
    overlay.classList.add('hidden');
    document.body.style.overflow = '';
  } else {
    menu.classList.remove('hidden');
    overlay.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }
}

document.getElementById('menu-btn').addEventListener('click', toggleMobileMenu);
document.getElementById('menu-close').addEventListener('click', toggleMobileMenu);
document.getElementById('mobile-overlay').addEventListener('click', toggleMobileMenu);

// 自動關閉：視窗放大到桌面尺寸時
window.addEventListener('resize', () => {
  if (window.innerWidth >= 768) {
    document.getElementById('mobile-menu').classList.add('hidden');
    document.getElementById('mobile-overlay').classList.add('hidden');
    document.body.style.overflow = '';
  }
});
```

---

## 3. Hero 區塊

### 三專案對照

| 面向 | longrock | hello-static | tokyo-statis |
|------|----------|-------------|-------------|
| 類型 | 固定背景 + 視差滾動 | 影片背景 + 圖片覆蓋 | 靜態圖片 + 火焰邊框 |
| 高度 | `100vh` (CSS var `--svh`) | 自適應影片比例 | `h-[405px] md:h-[600px]` |
| 動畫 | GSAP ScrollTrigger | 無 | 無 |
| 角色圖 | 4 角色獨立視差 | 無 | 無 |

### 推薦模式（漸進增強）

```html
<section class="hero" id="hero">
  <!-- 基礎：靜態主視覺圖 -->
  <img src="assets/hero/main-mobile.png" class="hero__img hero__img--mobile md:hidden" alt="展覽主視覺">
  <img src="assets/hero/main-desktop.png" class="hero__img hero__img--desktop hidden md:block" alt="展覽主視覺">

  <!-- 可選：影片背景 -->
  <!-- <video class="hero__video" autoplay muted loop playsinline>
    <source src="assets/hero/bg.mp4" type="video/mp4">
  </video> -->

  <!-- 覆蓋資訊 -->
  <div class="hero__overlay">
    <img src="assets/common/logo.png" class="hero__logo" alt="展覽Logo">
    <p class="hero__info">2026.XX.XX — XX.XX ｜ 展覽場地名稱</p>
  </div>
</section>
```

---

## 4. 商品系統（Goods System）

這是三個專案中最複雜且最一致的模組。

### 資料結構（統一 Schema）

```javascript
// js/items/jpItems.js
const japanGoods = [
  {
    name: '商品名稱（繁體中文）',
    price: 'NT.630',                    // 字串格式，含貨幣符號
    isNew: false,                       // boolean — 是否顯示 NEW 徽章
    note: '限購1個',                    // 購買備註（可為空字串）
    batch: 'regular',                   // 'regular' | 'taipei-only' — 場次限定篩選
    thumbnail: 'assets/goods/JP-001/thumb.jpg',  // 格狀縮圖
    images: [                           // Modal 展示圖（1張=單圖模式，多張=Swiper）
      'assets/goods/JP-001/01.jpg',
      'assets/goods/JP-001/02.jpg'
    ],
    description: '材質：聚酯纖維\n尺寸：約 H10 × W8 cm'  // \n 換行
  }
];
```

**三專案 Schema 差異**：
- longrock: 無 `batch` 欄位（單場次）
- hello-static: `images` 是單一字串（不支援多圖 Swiper）
- tokyo-statis: 有 `batch` + `VISIBILITY_CONFIG` 控制顯示

**推薦**：統一用陣列 `images`，即使只有一張圖也用 `['path.jpg']`。

### 文字轉義工具

商品資料雖來自本地 JS 常數，但為養成安全習慣，所有動態文字一律透過轉義函式輸出：

```javascript
/** 轉義 HTML 特殊字元，防止 XSS */
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/** 將 \n 轉為 <br>（先轉義再替換，確保安全） */
function nl2br(str) {
  return escapeHtml(str).replace(/\n/g, '<br>');
}
```

### 渲染函式

```javascript
function renderGoods(items, containerId) {
  const grid = document.getElementById(containerId);
  grid.innerHTML = items.map((item, index) => `
    <button class="goods-card" type="button" onclick="openModal(${index})"
            aria-label="查看商品：${escapeHtml(item.name)}">
      <div class="goods-card__image">
        <img src="${escapeHtml(item.thumbnail)}" alt="${escapeHtml(item.name)}" loading="lazy">
      </div>
      <div class="goods-card__info">
        ${item.isNew ? '<span class="goods-card__badge">NEW</span>' : ''}
        <p class="goods-card__name">${escapeHtml(item.name)}</p>
        <p class="goods-card__price">${escapeHtml(item.price)}</p>
        ${item.note ? `<p class="goods-card__note">${escapeHtml(item.note)}</p>` : ''}
      </div>
    </button>
  `).join('');
}
```

### 商品卡 CSS

```css
.goods-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);   /* 行動版 2 欄 */
  gap: 1rem;
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
}

@media (min-width: 768px) {
  .goods-grid {
    grid-template-columns: repeat(4, 1fr); /* 桌面版 4 欄 */
    gap: 1.5rem;
    padding: 2rem;
  }
}

.goods-card {
  background: white;
  border-radius: 0.5rem;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s;
}
.goods-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.goods-card__image {
  aspect-ratio: 1;
  overflow: hidden;
}
.goods-card__image img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.goods-card__info {
  padding: 0.75rem;
}
.goods-card__badge {
  display: inline-block;
  color: var(--color-accent);
  font-weight: bold;
  font-size: 0.75rem;
}
.goods-card__name {
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.3;
}
.goods-card__price {
  font-size: 0.85rem;
  font-weight: bold;
  margin-top: 0.25rem;
}
.goods-card__note {
  font-size: 0.65rem;
  color: var(--color-gray);
  margin-top: 0.25rem;
}
```

### Tab 切換（分類篩選）

```javascript
let currentTab = 'japan';

function switchTab(tabId) {
  if (tabId === currentTab) return;
  currentTab = tabId;

  // 切換 Tab 按鈕狀態
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });

  // 切換商品區塊
  document.querySelectorAll('.goods-section').forEach(section => {
    section.style.display = section.id === tabId ? 'block' : 'none';
  });

  // URL hash 同步（不觸發 popstate）
  history.replaceState(null, '', `#goods-${tabId}`);
}

// 從 URL hash 初始化
function initFromHash() {
  const hash = window.location.hash;
  if (hash.startsWith('#goods-')) {
    switchTab(hash.replace('#goods-', ''));
  }
}

document.addEventListener('DOMContentLoaded', initFromHash);
window.addEventListener('popstate', initFromHash);
```

### Modal 燈箱

使用 `role="dialog"` + `aria-modal` + `aria-labelledby` 確保無障礙。
所有動態文字使用 `textContent` 或 `nl2br()` 輸出，避免 XSS。

```html
<div class="modal" id="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" onclick="closeModal(event)">
  <div class="modal__content" onclick="event.stopPropagation()">
    <button class="modal__close" onclick="closeModal()" aria-label="關閉商品詳情">&times;</button>

    <!-- 單圖模式 -->
    <div class="modal__single" id="modal-single">
      <img id="modal-single-img" src="" alt="">
    </div>

    <!-- 多圖 Swiper 模式 -->
    <div class="modal__swiper" id="modal-swiper-container" style="display:none">
      <div class="swiper modal-swiper">
        <div class="swiper-wrapper" id="modal-swiper-wrapper"></div>
        <div class="swiper-pagination"></div>
        <div class="swiper-button-prev"></div>
        <div class="swiper-button-next"></div>
      </div>
    </div>

    <!-- 商品資訊 -->
    <div class="modal__info">
      <h3 id="modal-title"></h3>
      <p id="modal-price"></p>
      <p id="modal-desc"></p>
    </div>
  </div>
</div>
```

```javascript
let modalSwiper = null;
let modalTriggerEl = null; // 記住觸發元素，關閉後回歸焦點

function openModal(index) {
  const item = currentGoods[index];
  const modal = document.getElementById('modal');
  const single = document.getElementById('modal-single');
  const swiperContainer = document.getElementById('modal-swiper-container');

  // 記住觸發元素
  modalTriggerEl = document.activeElement;

  // 填入資訊（使用 textContent 防 XSS）
  document.getElementById('modal-title').textContent = item.name;
  document.getElementById('modal-price').textContent = item.price;
  document.getElementById('modal-desc').innerHTML = nl2br(item.description);

  // 圖片模式分支
  if (item.images.length === 1) {
    single.style.display = 'block';
    swiperContainer.style.display = 'none';
    document.getElementById('modal-single-img').src = item.images[0];
    document.getElementById('modal-single-img').alt = item.name;
    if (modalSwiper) { modalSwiper.destroy(true, true); modalSwiper = null; }
  } else {
    single.style.display = 'none';
    swiperContainer.style.display = 'block';
    document.getElementById('modal-swiper-wrapper').innerHTML =
      item.images.map(img => `
        <div class="swiper-slide">
          <img src="${escapeHtml(img)}" alt="${escapeHtml(item.name)}">
        </div>
      `).join('');
    if (modalSwiper) { modalSwiper.destroy(true, true); }
    setTimeout(() => {
      modalSwiper = new Swiper('.modal-swiper', {
        loop: true,
        pagination: { el: '.swiper-pagination', clickable: true },
        navigation: { nextEl: '.swiper-button-next', prevEl: '.swiper-button-prev' }
      });
    }, 50);
  }

  modal.classList.add('active');
  document.body.style.overflow = 'hidden';

  // Focus trap：聚焦到關閉按鈕
  modal.querySelector('.modal__close').focus();
}

function closeModal(event) {
  if (event && event.target.closest('.modal__content') && !event.target.closest('.modal__close')) return;
  const modal = document.getElementById('modal');
  modal.classList.remove('active');
  document.body.style.overflow = '';
  if (modalSwiper) { modalSwiper.destroy(true, true); modalSwiper = null; }

  // 焦點回歸觸發元素
  if (modalTriggerEl) { modalTriggerEl.focus(); modalTriggerEl = null; }
}

// ESC 關閉
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// Focus trap：Tab 鍵限制在 Modal 內
document.addEventListener('keydown', e => {
  const modal = document.getElementById('modal');
  if (!modal.classList.contains('active') || e.key !== 'Tab') return;

  const focusable = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
  const first = focusable[0];
  const last = focusable[focusable.length - 1];

  if (e.shiftKey) {
    if (document.activeElement === first) { e.preventDefault(); last.focus(); }
  } else {
    if (document.activeElement === last) { e.preventDefault(); first.focus(); }
  }
});
```

### Modal CSS

```css
.modal {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.7);
  justify-content: center;
  align-items: center;
}
.modal.active {
  display: flex;
}
.modal__content {
  position: relative;
  background: white;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  border-radius: 1rem;
}
.modal__close {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  width: 2rem;
  height: 2rem;
  border: none;
  background: var(--color-primary);
  color: white;
  border-radius: 50%;
  font-size: 1.2rem;
  cursor: pointer;
  z-index: 10;
}
.modal__single img,
.modal__swiper img {
  width: 100%;
  max-height: 50vh;
  object-fit: contain;
}
.modal__info {
  padding: 1.5rem;
  background: var(--color-black, #000);
  color: white;
}
.modal__info h3 { font-size: 1rem; font-weight: 700; }
.modal__price-text { font-size: 0.9rem; opacity: 0.9; }
.modal__info p { font-size: 0.85rem; line-height: 1.6; margin-top: 0.75rem; }

/* 隱藏捲軸但保留滾動 */
.modal__content::-webkit-scrollbar { display: none; }
.modal__content { -ms-overflow-style: none; scrollbar-width: none; }
```

---

## 5. FAQ 頁面

三個專案的 FAQ 都是**靜態全展開**，無手風琴收合。

### 推薦結構

```html
<section class="faq-section">
  <h2 class="faq-section__title">入場須知</h2>
  <div class="faq-section__content">
    <ul class="notice-list">
      <li>禁止攝影及錄影（特定區域除外）。</li>
      <li>禁止攜帶外食及飲料入場。</li>
      <!-- ... -->
    </ul>
  </div>
</section>

<section class="faq-section">
  <h2 class="faq-section__title">常見問題</h2>
  <div class="faq-section__content">
    <div class="faq-item">
      <p class="faq-item__q">Q：商品有限購數量嗎？</p>
      <p class="faq-item__a">A：部分熱門商品設有限購數量，詳見各商品標示。</p>
    </div>
    <!-- ... -->
  </div>
</section>
```

若需要手風琴功能，添加 JS：

```javascript
document.querySelectorAll('.faq-item__q').forEach(q => {
  q.addEventListener('click', () => {
    const item = q.closest('.faq-item');
    item.classList.toggle('is-open');
  });
});
```

---

## 6. 票券頁面

### 場次切換模式（from tokyo-statis）

```javascript
const venueData = {
  kaohsiung: {
    title: '高雄場',
    dates: '2026.XX.XX — XX.XX',
    venue: '駁二藝術特區',
    ticketImg: 'assets/ticket/ticket-kh.png'
  },
  taipei: {
    title: '台北場',
    dates: '2026.XX.XX — XX.XX',
    venue: '松山文創園區',
    ticketImg: 'assets/ticket/ticket-tp.png'
  }
};

let currentVenue = 'kaohsiung';

function switchVenue(venue) {
  currentVenue = venue;
  const data = venueData[venue];

  // 更新 UI
  document.getElementById('venue-title').textContent = data.title;
  document.getElementById('venue-dates').textContent = data.dates;
  document.getElementById('venue-img').src = data.ticketImg;

  // Tab 按鈕狀態
  document.querySelectorAll('.venue-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.venue === venue);
  });

  // 購票連結啟用/停用
  document.querySelectorAll('.ticket-link').forEach(link => {
    const url = link.dataset[`${venue}Url`];
    if (url) {
      link.href = url;
      link.style.opacity = '1';
      link.style.pointerEvents = 'auto';
    } else {
      link.removeAttribute('href');
      link.style.opacity = '0.5';
      link.style.pointerEvents = 'none';
    }
  });
}
```

### 票價表結構

桌面版用 `<table>`，行動版用 Swiper 卡片（from tokyo-statis）或直接堆疊（from hello-static）。

---

## 7. CSS 策略

### 方案 A：Tailwind CDN（推薦新專案）

```html
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {
    theme: {
      extend: {
        colors: {
          primary: 'var(--color-primary)',
          accent: 'var(--color-accent)',
        },
        fontFamily: {
          display: ['展覽標題字型', 'serif'],
          body: ['展覽內文字型', 'sans-serif'],
        }
      }
    }
  }
</script>
```

搭配極薄的 `style.css` 覆寫（< 100 行），處理 @font-face、動畫、Swiper 自訂。

**來源**：hello-static（93 行 CSS）、tokyo-statis（僅 inline `<style>`）。

### 方案 B：Vanilla CSS（設計感強的專案）

完整手寫 CSS，BEM 命名：
- `l-` 佈局、`p-` 頁面元件、`c-` 通用元件、`--` 修飾符、`js-` JS hook

**來源**：longrock（3425 行，高度客製設計）。

### CSS 變數（兩方案通用）

```css
:root {
  /* 品牌色 */
  --color-primary: #FF0000;
  --color-accent: #FFD700;
  --color-bg: #F4F4F4;
  --color-text: #333;
  --color-black: #000;
  --color-white: #fff;
  --color-gray: #999;

  /* 佈局 */
  --header-height: 64px;
  --content-max-width: 1200px;
  --content-padding: 2rem;

  /* 動態值（JS 設定） */
  --svh: 100vh;
}
```

---

## 8. 外部依賴 CDN 清單

| 依賴 | 用途 | CDN |
|------|------|-----|
| Swiper 11 | 商品 Modal 多圖、票券行動版 | `cdn.jsdelivr.net/npm/swiper@11` |
| GSAP + ScrollTrigger | 視差滾動（進階） | `cdn.jsdelivr.net/npm/gsap` |
| Keen Slider 6.8 | 角色/展品輪播（替代方案） | `cdn.jsdelivr.net/npm/keen-slider@6.8.6` |
| Tailwind CSS | 工具類 CSS | `cdn.tailwindcss.com` |
| Google Fonts | 雲端字型 | `fonts.googleapis.com` |

**最小依賴組合**：Swiper + Tailwind（或 Swiper + vanilla CSS）。

---

## 9. 響應式策略

### 斷點選擇

| 專案 | 主斷點 | 次要斷點 |
|------|--------|----------|
| longrock | 960px | 768px, 1100px, 1900px |
| hello-static | 768px (Tailwind `md`) | 820px |
| tokyo-statis | 768px (Tailwind `md`) | 820px, 1024px, 1200px |

**推薦**：`768px` 作為主斷點（符合 Tailwind `md`），`1024px` 作為大螢幕增強斷點。

### 桌面優先策略

CSS 預設為桌面版佈局，透過 `max-width` media query 適配行動版 RWD。先確保桌面版精準還原設計稿，再調整行動版的間距、欄數與字級。兩版都必須通過視覺驗證。

---

## 10. 圖片預載策略（from hello-static）

```javascript
function preloadImages(srcs) {
  srcs.forEach(src => { const img = new Image(); img.src = src; });
}

// 立即載入：前 12 張商品縮圖 + 導航/Hero 素材
preloadImages(criticalImages);

// 延遲載入：其餘商品圖（1.5 秒後）
setTimeout(() => preloadImages(deferredImages), 1500);
```

---

## 11. Footer 模式

### 三專案對照

| 專案 | Footer 類型 | 特色 |
|------|------------|------|
| longrock | 跑馬燈 + Logo + 主辦資訊 + 回頂部 | `@keyframes marquee` 無限滾動 |
| hello-static | 背景圖 + Logo + 版權圖 | 靜態，最簡單 |
| tokyo-statis | 三態機（flame → default → full） | 滾動位置驅動，最複雜 |

### 推薦：簡單版（適合大多數展覽）

```html
<footer class="footer">
  <div class="footer__inner">
    <img src="assets/common/logo-white.svg" class="footer__logo" alt="Logo">
    <p class="footer__org">主辦單位名稱</p>
    <p class="footer__copyright">&copy; 2026 展覽名稱. All Rights Reserved.</p>
  </div>
</footer>
```

---

## 12. 載入動畫（Loader）

### longrock 模式（彩色彈跳球）

```css
.loader { position: fixed; inset: 0; z-index: 9999; background: white;
          display: flex; align-items: center; justify-content: center;
          transition: opacity 0.5s; }
body.is-loaded .loader { opacity: 0; pointer-events: none; }

.loader__dot { width: 16px; height: 16px; border-radius: 50%; margin: 0 6px;
               animation: bounce 1.4s infinite ease-in-out; }
.loader__dot:nth-child(1) { background: var(--color-primary); animation-delay: 0s; }
.loader__dot:nth-child(2) { background: var(--color-accent); animation-delay: 0.08s; }
.loader__dot:nth-child(3) { background: #0083c4; animation-delay: 0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0) translateY(0); }
  40% { transform: scale(1) translateY(-20px); }
}
```

```javascript
window.addEventListener('load', () => {
  document.body.classList.add('is-loaded');
});
```
