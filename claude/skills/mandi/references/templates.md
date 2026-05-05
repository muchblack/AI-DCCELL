# Mandi 頁面模板

快速複製的程式碼模板，從三個展覽專案歸納。

## Template 1: 完整 index.html 骨架

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{展覽名稱}}</title>
  <meta name="description" content="{{展覽簡介}}">
  <meta property="og:title" content="{{展覽名稱}}">
  <meta property="og:description" content="{{展覽簡介}}">
  <meta property="og:image" content="assets/common/ogp.jpg">
  <link rel="icon" href="favicon.ico">

  <!-- 字型 -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family={{display-font}}&family=Noto+Sans+TC:wght@400;700&display=swap" rel="stylesheet">

  <!-- CSS -->
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
            display: ['"{{display-font}}"', 'serif'],
            body: ['"Noto Sans TC"', 'sans-serif'],
          }
        }
      }
    }
  </script>
  <link rel="stylesheet" href="css/style.css">

  <!-- Swiper（如需輪播） -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css">
</head>
<body data-page="index" class="font-body text-gray-900 bg-[var(--color-bg)]">

  <!-- 載入動畫 -->
  <div class="loader" id="loader">
    <div class="loader__dot"></div>
    <div class="loader__dot"></div>
    <div class="loader__dot"></div>
  </div>

  <!-- 桌面導航 -->
  <nav class="hidden md:flex fixed top-0 w-full z-50 bg-white/80 backdrop-blur-sm border-b border-gray-200 transition-all">
    <div class="max-w-[1200px] mx-auto w-full flex items-center justify-between px-6 h-16">
      <a href="index.html">
        <img src="assets/common/logo.svg" alt="{{展覽名稱}}" class="h-10">
      </a>
      <div class="flex items-center gap-8">
        <a href="#about" class="nav-link text-sm font-bold tracking-wider hover:text-primary transition">ABOUT</a>
        <a href="highlights.html" class="nav-link text-sm font-bold tracking-wider hover:text-primary transition">亮點</a>
        <a href="goods.html" class="nav-link text-sm font-bold tracking-wider hover:text-primary transition">商品</a>
        <a href="ticket.html" class="nav-link text-sm font-bold tracking-wider hover:text-primary transition">票券</a>
        <a href="faq.html" class="nav-link text-sm font-bold tracking-wider hover:text-primary transition">FAQ</a>
      </div>
    </div>
  </nav>

  <!-- 行動版漢堡按鈕 -->
  <button class="md:hidden fixed top-4 right-4 z-50 w-10 h-10 flex flex-col items-center justify-center gap-1.5 bg-black/80 rounded-full"
          id="menu-btn" aria-label="開啟選單" aria-expanded="false" aria-controls="mobile-menu">
    <span class="block w-5 h-0.5 bg-white transition-all"></span>
    <span class="block w-5 h-0.5 bg-white transition-all"></span>
    <span class="block w-5 h-0.5 bg-white transition-all"></span>
  </button>

  <!-- 行動版全螢幕選單 -->
  <div class="hidden fixed inset-0 z-40 bg-[var(--color-primary)] flex flex-col items-center justify-center gap-8" id="mobile-menu" role="dialog" aria-label="網站選單">
    <button class="absolute top-4 right-4 text-white text-3xl" id="menu-close" aria-label="關閉選單">&times;</button>
    <a href="index.html" class="text-white text-xl font-bold tracking-widest">TOP</a>
    <a href="highlights.html" class="text-white text-xl font-bold tracking-widest">亮點</a>
    <a href="goods.html" class="text-white text-xl font-bold tracking-widest">商品</a>
    <a href="ticket.html" class="text-white text-xl font-bold tracking-widest">票券</a>
    <a href="faq.html" class="text-white text-xl font-bold tracking-widest">FAQ</a>
  </div>
  <div class="hidden fixed inset-0 z-30 bg-black/50" id="mobile-overlay"></div>

  <!-- Hero -->
  <section class="hero relative overflow-hidden" id="top">
    <img src="assets/hero/main-mobile.png" alt="{{展覽主視覺}}" class="w-full md:hidden">
    <img src="assets/hero/main-desktop.png" alt="{{展覽主視覺}}" class="w-full hidden md:block">
    <div class="absolute bottom-8 left-1/2 -translate-x-1/2 text-center text-white">
      <p class="text-sm md:text-base tracking-widest">{{日期}} ｜ {{場地}}</p>
    </div>
  </section>

  <!-- About -->
  <section class="py-16 md:py-24" id="about">
    <div class="max-w-[800px] mx-auto px-6 text-center">
      <h2 class="font-display text-3xl md:text-4xl mb-8 text-primary">ABOUT</h2>
      <p class="leading-relaxed text-sm md:text-base">{{展覽介紹文字}}</p>
    </div>
  </section>

  <!-- Detail / 展區預覽（Swiper） -->
  <section class="py-16 bg-black" id="detail">
    <div class="max-w-[1200px] mx-auto">
      <h2 class="font-display text-3xl md:text-4xl mb-8 text-center text-white">EXHIBITION</h2>
      <div class="swiper detail-swiper">
        <div class="swiper-wrapper">
          <div class="swiper-slide"><img src="assets/hero/detail-01.jpg" alt="展區照片1" class="w-full rounded-lg"></div>
          <div class="swiper-slide"><img src="assets/hero/detail-02.jpg" alt="展區照片2" class="w-full rounded-lg"></div>
          <div class="swiper-slide"><img src="assets/hero/detail-03.jpg" alt="展區照片3" class="w-full rounded-lg"></div>
        </div>
        <div class="swiper-pagination"></div>
      </div>
    </div>
  </section>

  <!-- Ticket 摘要 -->
  <section class="py-16 md:py-24" id="ticket">
    <div class="max-w-[800px] mx-auto px-6">
      <h2 class="font-display text-3xl md:text-4xl mb-8 text-center text-primary">TICKET</h2>
      <!-- 簡要票價表 -->
      <div class="overflow-x-auto">
        <table class="w-full border-collapse text-sm">
          <thead>
            <tr class="bg-[var(--color-primary)] text-white">
              <th class="p-3 text-left">票種</th>
              <th class="p-3 text-left">價格</th>
              <th class="p-3 text-left">說明</th>
            </tr>
          </thead>
          <tbody>
            <tr class="border-b"><td class="p-3">全票</td><td class="p-3">NT$420</td><td class="p-3">一般民眾</td></tr>
            <tr class="border-b"><td class="p-3">優惠票</td><td class="p-3">NT$370</td><td class="p-3">學生、65 歲以上</td></tr>
            <tr class="border-b"><td class="p-3">愛心票</td><td class="p-3">NT$210</td><td class="p-3">身心障礙者及陪同者一人</td></tr>
          </tbody>
        </table>
      </div>
      <div class="mt-6 text-center">
        <a href="ticket.html" class="inline-block px-8 py-3 bg-[var(--color-primary)] text-white rounded-full font-bold hover:opacity-90 transition">查看完整票券資訊</a>
      </div>
    </div>
  </section>

  <!-- 注意事項摘要 -->
  <section class="py-16 bg-[var(--color-primary)] text-white" id="notice">
    <div class="max-w-[800px] mx-auto px-6">
      <h2 class="font-display text-3xl md:text-4xl mb-8 text-center">NOTICE</h2>
      <ul class="space-y-3 text-sm leading-relaxed">
        <li>・禁止攝影及錄影（特定區域除外）。</li>
        <li>・禁止攜帶外食及飲料入場。</li>
        <li>・展場內請勿奔跑或觸摸展品。</li>
      </ul>
      <div class="mt-6 text-center">
        <a href="faq.html" class="inline-block px-8 py-3 border-2 border-white text-white rounded-full font-bold hover:bg-white hover:text-[var(--color-primary)] transition">完整 FAQ</a>
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="bg-black text-white py-12">
    <div class="max-w-[800px] mx-auto px-6 text-center">
      <img src="assets/common/logo-white.svg" alt="{{展覽名稱}}" class="h-12 mx-auto mb-4">
      <p class="text-xs text-gray-400">主辦單位：{{主辦單位}}</p>
      <p class="text-xs text-gray-400 mt-2">&copy; 2026 {{展覽名稱}}. All Rights Reserved.</p>
    </div>
  </footer>

  <!-- 浮動回頂部按鈕 -->
  <button class="fixed right-4 bottom-4 z-40 w-12 h-12 bg-[var(--color-primary)] text-white rounded-full shadow-lg opacity-0 transition-opacity" id="to-top-btn">
    <svg class="w-5 h-5 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"></path>
    </svg>
  </button>

  <!-- Scripts -->
  <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
  <script src="js/main.js"></script>
  <script>
    // Detail Swiper
    new Swiper('.detail-swiper', {
      loop: true,
      slidesPerView: 'auto',
      centeredSlides: true,
      spaceBetween: 30,
      autoplay: { delay: 5000 },
      pagination: { el: '.swiper-pagination', clickable: true }
    });
  </script>
</body>
</html>
```

---

## Template 2: goods.html 骨架

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>商品一覽 — {{展覽名稱}}</title>
  <link rel="icon" href="favicon.ico">
  <!-- 同 index.html 的 fonts + tailwind + style.css -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css">
  <link rel="stylesheet" href="css/style.css">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body data-page="goods" class="font-body text-gray-900 bg-[var(--color-bg)]">

  <!-- 導航（同 index.html） -->
  <!-- ... -->

  <!-- 商品頁 Hero -->
  <section class="relative h-[200px] md:h-[300px] overflow-hidden bg-[var(--color-primary)]">
    <img src="assets/hero/goods-banner.png" alt="商品一覽" class="w-full h-full object-cover opacity-50">
    <h1 class="absolute inset-0 flex items-center justify-center text-white font-display text-4xl md:text-5xl">GOODS</h1>
  </section>

  <!-- Tab 切換 -->
  <div class="max-w-[1200px] mx-auto px-4 pt-8">
    <div class="flex justify-center gap-4 md:gap-8">
      <button class="tab-btn active px-6 py-2 rounded-full border-2 border-black font-bold text-sm transition"
              data-tab="japan" onclick="switchTab('japan')">日本特展商品</button>
      <button class="tab-btn px-6 py-2 rounded-full border-2 border-black font-bold text-sm transition"
              data-tab="taiwan" onclick="switchTab('taiwan')">台灣限定商品</button>
    </div>
  </div>

  <!-- 商品格 -->
  <div class="max-w-[1200px] mx-auto px-4 py-8">
    <div class="goods-section" id="japan">
      <div class="goods-grid" id="japan-grid"></div>
    </div>
    <div class="goods-section" id="taiwan" style="display:none">
      <div class="goods-grid" id="taiwan-grid"></div>
    </div>
  </div>

  <!-- Modal -->
  <div class="modal" id="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" onclick="closeModal(event)">
    <div class="modal__content" onclick="event.stopPropagation()">
      <button class="modal__close" onclick="closeModal()" aria-label="關閉商品詳情">&times;</button>
      <div class="modal__single" id="modal-single">
        <img id="modal-single-img" src="" alt="">
      </div>
      <div class="modal__swiper" id="modal-swiper-container" style="display:none">
        <div class="swiper modal-swiper">
          <div class="swiper-wrapper" id="modal-swiper-wrapper"></div>
          <div class="swiper-pagination"></div>
          <div class="swiper-button-prev"></div>
          <div class="swiper-button-next"></div>
        </div>
      </div>
      <div class="modal__info">
        <h3 id="modal-title"></h3>
        <p id="modal-price"></p>
        <p id="modal-desc"></p>
      </div>
    </div>
  </div>

  <!-- Footer（同 index.html） -->
  <!-- ... -->

  <!-- Scripts -->
  <script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
  <script src="js/items/jpItems.js"></script>
  <script src="js/items/twItems.js"></script>
  <script src="js/main.js"></script>
  <script src="js/goods.js"></script>
</body>
</html>
```

---

## Template 3: js/main.js 共用模組

```javascript
/**
 * 展覽網站共用模組
 * - 漢堡選單
 * - 平滑滾動
 * - 回頂部按鈕
 * - 載入動畫
 * - --svh CSS 變數
 */

// === 載入動畫 ===
window.addEventListener('load', () => {
  document.body.classList.add('is-loaded');
});

// === --svh CSS 變數（修正行動版 100vh 問題） ===
function updateSVH() {
  document.documentElement.style.setProperty('--svh', `${window.innerHeight}px`);
}
updateSVH();
window.addEventListener('resize', updateSVH);

// === 漢堡選單 ===
function toggleMobileMenu() {
  const menu = document.getElementById('mobile-menu');
  const overlay = document.getElementById('mobile-overlay');
  if (!menu || !overlay) return;

  const isOpen = !menu.classList.contains('hidden');
  menu.classList.toggle('hidden', isOpen);
  overlay.classList.toggle('hidden', isOpen);
  document.body.style.overflow = isOpen ? '' : 'hidden';
}

document.getElementById('menu-btn')?.addEventListener('click', toggleMobileMenu);
document.getElementById('menu-close')?.addEventListener('click', toggleMobileMenu);
document.getElementById('mobile-overlay')?.addEventListener('click', toggleMobileMenu);

// 桌面寬度時自動關閉行動選單
window.addEventListener('resize', () => {
  if (window.innerWidth >= 768) {
    const menu = document.getElementById('mobile-menu');
    const overlay = document.getElementById('mobile-overlay');
    if (menu && !menu.classList.contains('hidden')) {
      menu.classList.add('hidden');
      overlay?.classList.add('hidden');
      document.body.style.overflow = '';
    }
  }
});

// 選單內連結點擊後關閉
document.querySelectorAll('#mobile-menu a').forEach(link => {
  link.addEventListener('click', () => {
    setTimeout(toggleMobileMenu, 100);
  });
});

// === 平滑滾動 ===
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    const targetId = this.getAttribute('href');
    if (targetId === '#') return;
    const target = document.querySelector(targetId);
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth' });
    }
  });
});

// === 回頂部按鈕 ===
const toTopBtn = document.getElementById('to-top-btn');
if (toTopBtn) {
  window.addEventListener('scroll', () => {
    toTopBtn.style.opacity = window.scrollY > 300 ? '1' : '0';
    toTopBtn.style.pointerEvents = window.scrollY > 300 ? 'auto' : 'none';
  });
  toTopBtn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

// === 導航高亮（首頁滾動追蹤用） ===
if (document.body.dataset.page === 'index') {
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-link');

  window.addEventListener('scroll', () => {
    let current = '';
    sections.forEach(section => {
      const top = section.offsetTop - 100;
      if (window.scrollY >= top) {
        current = section.getAttribute('id');
      }
    });
    navLinks.forEach(link => {
      link.classList.toggle('text-primary',
        link.getAttribute('href') === `#${current}`);
    });
  });
}
```

---

## Template 4: js/goods.js 商品模組

```javascript
/**
 * 商品頁模組
 * - XSS 安全的商品渲染
 * - Tab 切換
 * - 無障礙 Modal 燈箱（focus trap + aria + 焦點回歸）
 */

let currentTab = 'japan';
let currentGoods = [];
let modalSwiper = null;
let modalTriggerEl = null;

// === XSS 防護工具 ===
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function nl2br(str) {
  return escapeHtml(str).replace(/\n/g, '<br>');
}

// === 渲染商品格 ===
function renderGoods(items, containerId) {
  const grid = document.getElementById(containerId);
  if (!grid) return;
  grid.innerHTML = items.map((item, index) => `
    <button class="goods-card" type="button" onclick="openModal('${containerId}', ${index})"
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

// === Tab 切換 ===
function switchTab(tabId) {
  if (tabId === currentTab) return;
  currentTab = tabId;

  document.querySelectorAll('.tab-btn').forEach(btn => {
    const isActive = btn.dataset.tab === tabId;
    btn.classList.toggle('active', isActive);
  });

  document.querySelectorAll('.goods-section').forEach(section => {
    section.style.display = section.id === tabId ? 'block' : 'none';
  });

  history.replaceState(null, '', `#goods-${tabId}`);
}

// === Modal ===
function openModal(gridId, index) {
  const items = gridId === 'japan-grid' ? japanGoods : taiwanGoods;
  const item = items[index];
  currentGoods = items;

  const modal = document.getElementById('modal');
  const single = document.getElementById('modal-single');
  const swiperContainer = document.getElementById('modal-swiper-container');

  // 記住觸發元素，關閉後回歸焦點
  modalTriggerEl = document.activeElement;

  // 填入資訊（textContent 防 XSS，nl2br 處理已知安全換行）
  document.getElementById('modal-title').textContent = item.name;
  document.getElementById('modal-price').textContent = item.price;
  document.getElementById('modal-desc').innerHTML = nl2br(item.description);

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
      item.images.map(img => `<div class="swiper-slide"><img src="${escapeHtml(img)}" alt="${escapeHtml(item.name)}"></div>`).join('');
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
  modal.querySelector('.modal__close').focus();
}

function closeModal(event) {
  if (event && event.target.closest('.modal__content') && !event.target.closest('.modal__close')) return;
  document.getElementById('modal').classList.remove('active');
  document.body.style.overflow = '';
  if (modalSwiper) { modalSwiper.destroy(true, true); modalSwiper = null; }
  if (modalTriggerEl) { modalTriggerEl.focus(); modalTriggerEl = null; }
}

// ESC 關閉
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// Focus trap
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

// === 初始化 ===
document.addEventListener('DOMContentLoaded', () => {
  if (typeof japanGoods !== 'undefined') renderGoods(japanGoods, 'japan-grid');
  if (typeof taiwanGoods !== 'undefined') renderGoods(taiwanGoods, 'taiwan-grid');

  const hash = window.location.hash;
  if (hash === '#goods-taiwan') {
    switchTab('taiwan');
  }
});

window.addEventListener('popstate', () => {
  const hash = window.location.hash;
  if (hash.startsWith('#goods-')) {
    currentTab = '';
    switchTab(hash.replace('#goods-', ''));
  }
});
```

---

## Template 5: js/items/jpItems.js 商品資料範本

```javascript
/**
 * 日本特展商品資料
 * 圖片放在 assets/goods/JP-{品號}/ 目錄下
 */
const japanGoods = [
  {
    name: '商品名稱',
    price: 'NT.630',
    isNew: false,
    note: '限購1個',
    thumbnail: 'assets/goods/JP-001/thumb.jpg',
    images: [
      'assets/goods/JP-001/01.jpg',
      'assets/goods/JP-001/02.jpg'
    ],
    description: '材質：聚酯纖維\n尺寸：約 H10 × W8 cm'
  }
  // ... 更多商品
];
```

---

## Template 6: css/style.css 基礎樣式

```css
/* === CSS Variables === */
:root {
  --color-primary: #FF0000;
  --color-accent: #FFD700;
  --color-bg: #F4F4F4;
  --color-text: #333;
  --color-black: #000;
  --color-white: #fff;
  --color-gray: #999;
  --svh: 100vh;
}

/* === @font-face（若使用本地字型） === */
/*
@font-face {
  font-family: 'CustomFont';
  src: url('../fonts/CustomFont-Regular.ttf') format('truetype');
  font-weight: 400;
  font-display: swap;
}
*/

/* === Reset Additions === */
html { scroll-behavior: smooth; }
body { -webkit-font-smoothing: antialiased; }
img { max-width: 100%; height: auto; }
video { object-fit: cover; }

/* === Loader === */
.loader {
  position: fixed; inset: 0; z-index: 9999;
  background: white;
  display: flex; align-items: center; justify-content: center;
  transition: opacity 0.6s ease;
}
body.is-loaded .loader { opacity: 0; pointer-events: none; }
.loader__dot {
  width: 14px; height: 14px; border-radius: 50%; margin: 0 5px;
  animation: loader-bounce 1.4s infinite ease-in-out;
}
.loader__dot:nth-child(1) { background: var(--color-primary); animation-delay: 0s; }
.loader__dot:nth-child(2) { background: var(--color-accent); animation-delay: 0.1s; }
.loader__dot:nth-child(3) { background: var(--color-text); animation-delay: 0.2s; }
@keyframes loader-bounce {
  0%, 80%, 100% { transform: scale(0) translateY(0); }
  40% { transform: scale(1) translateY(-18px); }
}

/* === Goods Grid === */
.goods-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
}
@media (min-width: 768px) {
  .goods-grid { grid-template-columns: repeat(4, 1fr); gap: 1.5rem; padding: 2rem; }
}

.goods-card {
  background: white; border-radius: 0.5rem; overflow: hidden;
  cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;
  border: none; padding: 0; text-align: left; width: 100%;  /* button reset */
  display: flex; flex-direction: column;
}
.goods-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.1); }
.goods-card__image { aspect-ratio: 1; overflow: hidden; }
.goods-card__image img { width: 100%; height: 100%; object-fit: contain; }
.goods-card__info { padding: 0.75rem; }
.goods-card__badge { display: inline-block; color: var(--color-accent); font-weight: bold; font-size: 0.75rem; }
.goods-card__name { font-size: 0.8rem; font-weight: 600; line-height: 1.3; }
.goods-card__price { font-size: 0.85rem; font-weight: bold; margin-top: 0.25rem; }
.goods-card__note { font-size: 0.65rem; color: var(--color-gray); margin-top: 0.25rem; }

/* === Tab Buttons === */
.tab-btn { background: transparent; color: black; }
.tab-btn.active { background: black; color: white; }
.tab-btn:hover { background: black; color: white; }

/* === Modal === */
.modal {
  display: none; position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.7); justify-content: center; align-items: center;
}
.modal.active { display: flex; }
.modal__content {
  position: relative; background: white; max-width: 500px; width: 90%;
  max-height: 90vh; overflow-y: auto; border-radius: 1rem;
}
.modal__content::-webkit-scrollbar { display: none; }
.modal__content { -ms-overflow-style: none; scrollbar-width: none; }
.modal__close {
  position: absolute; top: 0.75rem; right: 0.75rem; z-index: 10;
  width: 2.5rem; height: 2.5rem; border: none;
  background: var(--color-primary); color: white; border-radius: 50%;
  font-size: 1.4rem; cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.modal__single img, .modal__swiper img { width: 100%; max-height: 50vh; object-fit: contain; }
.modal__info { padding: 1.5rem; background: var(--color-black); color: white; }
.modal__info h3 { font-size: 1rem; font-weight: 700; }
.modal__price-text { font-size: 0.9rem; opacity: 0.85; }
.modal__note-text { font-size: 0.75rem; opacity: 0.7; }
.modal__info p { font-size: 0.85rem; line-height: 1.6; margin-top: 0.75rem; }
```

---

## Template 7: .gitignore

```
.DS_Store
.idea/
*.swp
*.swo
*~
node_modules/
.env
screen/
```

---

## Template 8: CLAUDE.md 範本

```markdown
# CLAUDE.md

## 專案概述

{{展覽名稱}}官方網站。純靜態網頁專案，無建置系統或套件管理。

## 技術架構

- **純靜態網頁**：HTML + CSS + 原生 JavaScript
- **CSS 框架**：Tailwind CSS（CDN）+ 少量自訂樣式
- **外部依賴**（CDN 載入）：
  - Swiper v11：商品燈箱輪播
  - Google Fonts：{{字型名稱}}
- **響應式斷點**：768px（桌面/行動版分界）

## 檔案結構

（由 mandi skill 產生的標準結構）

## CSS 命名規範

- 商品系統：`.goods-grid`、`.goods-card`、`.goods-card__image`
- Modal：`.modal`、`.modal__content`、`.modal__info`
- Tab：`.tab-btn`、`.goods-section`
- 導航：`.nav-link`、`.mobile-menu`
- 通用：`.loader`

## 商品資料格式

商品資料存於 `js/items/` 目錄：
- `jpItems.js` — 日本特展商品陣列
- `twItems.js` — 台灣限定商品陣列

每個商品物件結構：
\`\`\`javascript
{
  name: '商品名稱',
  price: 'NT.630',
  isNew: false,
  note: '限購備註',
  thumbnail: 'assets/goods/XX-001/thumb.jpg',
  images: ['assets/goods/XX-001/01.jpg'],
  description: '材質：...\n尺寸：...'
}
\`\`\`

## 開發指令

純靜態專案，無需建置步驟。建議使用 Live Server 進行開發。
```
