# 台灣信用卡推薦平台 - 設計系統

> **Version:** 1.0.0
> **Last Updated:** 2026-02-06
> **Stack:** Next.js 14 + Tailwind CSS

---

## 1. 設計理念

### 核心價值
- **信任感 (Trust):** 金融服務需要傳達安全與可靠
- **清晰度 (Clarity):** 資訊密集但易於理解
- **效率 (Efficiency):** 快速找到最適合的信用卡

### 目標用戶
- 台灣地區尋找信用卡的消費者
- 年齡層 25-55 歲
- 重視回饋、年費、權益比較

---

## 2. 色彩系統

### 主色調 (Banking/Traditional Finance)

```css
:root {
  /* Primary - 專業深綠 (信任、穩健) */
  --color-primary: #0F766E;
  --color-primary-hover: #0D9488;
  --color-primary-light: #14B8A6;

  /* Secondary - 明亮青色 */
  --color-secondary: #14B8A6;
  --color-secondary-hover: #2DD4BF;

  /* CTA - 藍色 (行動呼籲) */
  --color-cta: #0369A1;
  --color-cta-hover: #0284C7;

  /* Accent - 金色 (高端、獎勵) */
  --color-accent: #F59E0B;
  --color-accent-hover: #FBBF24;

  /* Background */
  --color-bg-primary: #F0FDFA;
  --color-bg-secondary: #FFFFFF;
  --color-bg-tertiary: #F8FAFC;

  /* Text */
  --color-text-primary: #134E4A;
  --color-text-secondary: #475569;
  --color-text-muted: #64748B;

  /* Border */
  --color-border: #99F6E4;
  --color-border-light: #E2E8F0;

  /* Status */
  --color-success: #10B981;
  --color-warning: #F59E0B;
  --color-error: #EF4444;
  --color-info: #3B82F6;
}
```

### Tailwind 配置

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#0F766E',
          hover: '#0D9488',
          light: '#14B8A6',
        },
        secondary: {
          DEFAULT: '#14B8A6',
          hover: '#2DD4BF',
        },
        cta: {
          DEFAULT: '#0369A1',
          hover: '#0284C7',
        },
        accent: {
          DEFAULT: '#F59E0B',
          hover: '#FBBF24',
        },
      },
    },
  },
}
```

### 色彩使用規則

| 用途 | 色彩 | Tailwind Class |
|------|------|----------------|
| 主要按鈕 | Primary | `bg-primary hover:bg-primary-hover` |
| 次要按鈕 | Secondary | `bg-secondary hover:bg-secondary-hover` |
| CTA 按鈕 | CTA Blue | `bg-cta hover:bg-cta-hover` |
| 回饋標籤 | Accent Gold | `bg-accent text-white` |
| 卡片背景 | White | `bg-white` |
| 頁面背景 | Light Teal | `bg-[#F0FDFA]` |
| 主要文字 | Dark Teal | `text-[#134E4A]` |
| 次要文字 | Slate | `text-slate-600` |

---

## 3. 字型系統

### 字型家族

```css
/* Google Fonts Import */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=Noto+Sans+TC:wght@300;400;500;700&display=swap');

:root {
  --font-heading: 'IBM Plex Sans', 'Noto Sans TC', system-ui, sans-serif;
  --font-body: 'IBM Plex Sans', 'Noto Sans TC', system-ui, sans-serif;
  --font-mono: 'IBM Plex Mono', ui-monospace, monospace;
}
```

### 字型規格

| 層級 | 大小 | 行高 | 字重 | Tailwind Class |
|------|------|------|------|----------------|
| H1 | 36px / 2.25rem | 1.2 | 700 | `text-4xl font-bold leading-tight` |
| H2 | 30px / 1.875rem | 1.25 | 600 | `text-3xl font-semibold` |
| H3 | 24px / 1.5rem | 1.3 | 600 | `text-2xl font-semibold` |
| H4 | 20px / 1.25rem | 1.4 | 500 | `text-xl font-medium` |
| Body | 16px / 1rem | 1.6 | 400 | `text-base` |
| Small | 14px / 0.875rem | 1.5 | 400 | `text-sm` |
| Caption | 12px / 0.75rem | 1.4 | 400 | `text-xs` |

### 中文排版注意事項

- 行高至少 1.6 倍 (中文需要更多呼吸空間)
- 段落間距使用 `mb-4` 或 `space-y-4`
- 避免全大寫 (中文沒有大小寫區別)

---

## 4. 間距系統

### 基準單位

```
4px  = 0.25rem = space-1
8px  = 0.5rem  = space-2
12px = 0.75rem = space-3
16px = 1rem    = space-4
20px = 1.25rem = space-5
24px = 1.5rem  = space-6
32px = 2rem    = space-8
40px = 2.5rem  = space-10
48px = 3rem    = space-12
64px = 4rem    = space-16
```

### 常用組合

| 元素 | 內距 | 外距 |
|------|------|------|
| 卡片 | `p-6` | `mb-6` |
| 按鈕 (大) | `px-6 py-3` | - |
| 按鈕 (中) | `px-4 py-2` | - |
| 輸入框 | `px-4 py-3` | `mb-4` |
| 區塊標題 | - | `mb-8` |
| 頁面容器 | `px-4 md:px-6 lg:px-8` | `py-8 md:py-12` |

---

## 5. 元件規範

### 5.1 按鈕

```html
<!-- Primary Button -->
<button class="
  px-6 py-3
  bg-primary hover:bg-primary-hover
  text-white font-medium
  rounded-lg
  transition-colors duration-200
  cursor-pointer
  focus:outline-none focus:ring-2 focus:ring-primary/50
  disabled:opacity-50 disabled:cursor-not-allowed
">
  立即申請
</button>

<!-- Secondary Button -->
<button class="
  px-6 py-3
  bg-white hover:bg-gray-50
  text-primary font-medium
  border border-primary
  rounded-lg
  transition-colors duration-200
  cursor-pointer
">
  了解更多
</button>

<!-- CTA Button -->
<button class="
  px-8 py-4
  bg-cta hover:bg-cta-hover
  text-white font-semibold
  rounded-xl
  shadow-lg hover:shadow-xl
  transition-all duration-200
  cursor-pointer
">
  開始推薦
</button>
```

### 5.2 卡片

```html
<!-- Credit Card Display -->
<div class="
  bg-white
  rounded-2xl
  shadow-sm hover:shadow-md
  border border-gray-100
  p-6
  transition-shadow duration-200
  cursor-pointer
">
  <!-- Card Header -->
  <div class="flex items-center gap-4 mb-4">
    <img src="..." alt="銀行 Logo" class="w-12 h-12 object-contain" />
    <div>
      <h3 class="text-lg font-semibold text-[#134E4A]">卡片名稱</h3>
      <p class="text-sm text-slate-500">銀行名稱</p>
    </div>
  </div>

  <!-- Reward Badge -->
  <span class="
    inline-flex items-center
    px-3 py-1
    bg-accent/10 text-accent
    text-sm font-medium
    rounded-full
  ">
    最高 5% 回饋
  </span>

  <!-- Card Content -->
  <div class="mt-4 space-y-2">
    <p class="text-slate-600">年費：免年費</p>
    <p class="text-slate-600">基本回饋：1%</p>
  </div>
</div>
```

### 5.3 表單輸入

```html
<!-- Text Input -->
<div class="space-y-2">
  <label for="amount" class="block text-sm font-medium text-[#134E4A]">
    每月消費金額
  </label>
  <input
    type="number"
    id="amount"
    class="
      w-full px-4 py-3
      border border-gray-200
      rounded-lg
      text-[#134E4A]
      placeholder:text-slate-400
      focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary
      transition-colors duration-200
    "
    placeholder="輸入金額"
  />
</div>

<!-- Slider -->
<div class="space-y-2">
  <label class="flex justify-between text-sm font-medium text-[#134E4A]">
    <span>餐飲消費比例</span>
    <span class="text-primary">30%</span>
  </label>
  <input
    type="range"
    min="0"
    max="100"
    class="
      w-full h-2
      bg-gray-200
      rounded-lg
      appearance-none
      cursor-pointer
      accent-primary
    "
  />
</div>
```

### 5.4 導航列

```html
<nav class="
  fixed top-4 left-4 right-4 z-50
  bg-white/80 backdrop-blur-lg
  border border-gray-100
  rounded-2xl
  shadow-sm
">
  <div class="max-w-7xl mx-auto px-6 py-4">
    <div class="flex items-center justify-between">
      <!-- Logo -->
      <a href="/" class="text-xl font-bold text-primary">
        信用卡推薦
      </a>

      <!-- Nav Links -->
      <div class="hidden md:flex items-center gap-8">
        <a href="/" class="text-slate-600 hover:text-primary transition-colors">
          首頁
        </a>
        <a href="/cards" class="text-slate-600 hover:text-primary transition-colors">
          信用卡
        </a>
        <a href="/recommend" class="text-slate-600 hover:text-primary transition-colors">
          推薦
        </a>
      </div>
    </div>
  </div>
</nav>
```

---

## 6. 響應式斷點

```javascript
// Tailwind breakpoints
screens: {
  'sm': '640px',   // 手機橫向
  'md': '768px',   // 平板
  'lg': '1024px',  // 小筆電
  'xl': '1280px',  // 桌機
  '2xl': '1536px', // 大螢幕
}
```

### 常用響應式模式

```html
<!-- 容器最大寬度 -->
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

<!-- 網格布局 -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

<!-- 隱藏/顯示 -->
<div class="hidden md:block">  <!-- 平板以上顯示 -->
<div class="md:hidden">        <!-- 手機顯示 -->
```

---

## 7. 動效規範

### 時間函數

| 用途 | 持續時間 | Tailwind |
|------|----------|----------|
| 顏色變化 | 150ms | `duration-150` |
| 微互動 | 200ms | `duration-200` |
| 展開/收合 | 300ms | `duration-300` |
| 頁面轉場 | 500ms | `duration-500` |

### 緩動函數

```css
/* 預設使用 ease-out */
transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
```

### 減少動態偏好

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 8. 無障礙規範

### 色彩對比

| 元素 | 最低對比度 |
|------|-----------|
| 正文文字 | 4.5:1 |
| 大標題 (18px+) | 3:1 |
| 非文字元素 | 3:1 |

### 焦點狀態

```html
<!-- 所有互動元素必須有可見焦點 -->
<button class="
  focus:outline-none
  focus:ring-2
  focus:ring-primary/50
  focus:ring-offset-2
">
```

### 表單標籤

```html
<!-- 所有輸入必須有關聯標籤 -->
<label for="email" class="sr-only">電子郵件</label>
<input id="email" type="email" />
```

### ARIA 標籤

```html
<!-- 圖示按鈕需要 aria-label -->
<button aria-label="關閉選單">
  <svg>...</svg>
</button>

<!-- 載入狀態 -->
<div role="status" aria-live="polite">
  載入中...
</div>
```

---

## 9. 圖示系統

### 建議圖示庫

- **Heroicons** - https://heroicons.com/ (React 友善)
- **Lucide** - https://lucide.dev/ (輕量)

### 使用規則

- 統一使用 24x24 或 20x20 尺寸
- 線條粗細一致 (stroke-width: 1.5 或 2)
- 使用 `currentColor` 繼承文字顏色

```html
<!-- 正確 -->
<svg class="w-6 h-6 text-slate-500" fill="none" stroke="currentColor">

<!-- 錯誤：不要使用 emoji -->
<span>🔥</span>
```

---

## 10. 載入狀態

### Skeleton Loader

```html
<div class="animate-pulse space-y-4">
  <div class="h-4 bg-gray-200 rounded w-3/4"></div>
  <div class="h-4 bg-gray-200 rounded w-1/2"></div>
</div>
```

### Spinner

```html
<div class="flex items-center justify-center">
  <div class="
    w-8 h-8
    border-4 border-primary/30
    border-t-primary
    rounded-full
    animate-spin
  "></div>
</div>
```

### 按鈕載入狀態

```html
<button disabled class="opacity-50 cursor-not-allowed">
  <svg class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
  </svg>
  處理中...
</button>
```

---

## 11. 頁面結構

### 標準頁面模板

```html
<main class="min-h-screen bg-[#F0FDFA]">
  <!-- Navbar (fixed, 需要 padding-top) -->
  <nav class="fixed top-4 left-4 right-4 z-50">...</nav>

  <!-- Content (配合 navbar 高度) -->
  <div class="pt-24 pb-12">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <!-- Page content -->
    </div>
  </div>

  <!-- Footer -->
  <footer class="bg-white border-t">...</footer>
</main>
```

---

## 12. 檢查清單

### 交付前必查

- [ ] 所有可點擊元素有 `cursor-pointer`
- [ ] Hover 狀態有平滑過渡 (150-300ms)
- [ ] 無 emoji 作為圖示
- [ ] 表單輸入有關聯 label
- [ ] 圖片有 alt 文字
- [ ] 載入狀態有視覺回饋
- [ ] 響應式測試 (375px, 768px, 1024px, 1440px)
- [ ] 焦點狀態可見
- [ ] 色彩對比度符合 WCAG AA (4.5:1)
