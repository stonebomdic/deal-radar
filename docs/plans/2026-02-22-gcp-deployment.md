# GCP e2-micro 部署實作計畫

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 將 deal-radar 部署至 GCP e2-micro 免費方案，後端 Docker 持續運行排程，前端靜態化由 Nginx 服務。

**Architecture:** e2-micro VM 上只跑後端單容器（FastAPI + APScheduler），Next.js 以 `output: 'export'` 靜態匯出後由 Nginx 提供服務，Nginx 同時反向代理 `/api/*` 至後端 port 8000。Momo flash deals 排程降為每 3 小時以節省記憶體。

**Tech Stack:** GCP Compute Engine e2-micro、Docker、Nginx、Next.js static export、SQLite on persistent disk、2GB swap file。

---

## Task 1：分離 Momo flash deals 排程（降為每 3 小時）

**Files:**
- Modify: `src/scheduler/jobs.py`（新增 `run_momo_flash_deals_refresh`）
- Modify: `src/scheduler/runner.py`（拆成兩個 job）

**Step 1: 在 `jobs.py` 新增 Momo 專屬函式**

在 `run_flash_deals_refresh()` 之後加入：

```python
def run_pchome_flash_deals_refresh():
    """每 1 小時：更新 PChome 限時瘋搶"""
    from src.trackers.utils import refresh_flash_deals

    logger.info("Starting PChome flash deals refresh")
    with get_sync_session() as session:
        try:
            count = refresh_flash_deals(session, "pchome")
            logger.info(f"PChome flash deals refreshed: +{count} new")
        except Exception as e:
            logger.error(f"Error refreshing PChome flash deals: {e}")


def run_momo_flash_deals_refresh():
    """每 3 小時：更新 Momo 限時瘋搶（Playwright 較重，降低頻率）"""
    from src.trackers.utils import refresh_flash_deals

    logger.info("Starting Momo flash deals refresh")
    with get_sync_session() as session:
        try:
            count = refresh_flash_deals(session, "momo")
            logger.info(f"Momo flash deals refreshed: +{count} new")
        except Exception as e:
            logger.error(f"Error refreshing Momo flash deals: {e}")
```

**Step 2: 修改 `runner.py` 匯入並拆分排程**

將原本的 `run_flash_deals_refresh` import 改為：

```python
from src.scheduler.jobs import (
    check_expiring_promotions,
    check_new_promotions,
    cleanup_expired_promotions,
    run_daily_promotion_crawl,
    run_momo_flash_deals_refresh,
    run_pchome_flash_deals_refresh,
    run_price_tracking,
    run_weekly_card_crawl,
)
```

將原本的 `flash_deals_refresh` 單一 job 替換為：

```python
# PChome 每 1 小時（httpx 輕量）
scheduler.add_job(
    run_pchome_flash_deals_refresh,
    "interval",
    hours=1,
    id="pchome_flash_deals_refresh",
    name="PChome Flash Deals Refresh",
)

# Momo 每 3 小時（Playwright 較重）
scheduler.add_job(
    run_momo_flash_deals_refresh,
    "interval",
    hours=3,
    id="momo_flash_deals_refresh",
    name="Momo Flash Deals Refresh",
)
```

**Step 3: 執行測試確認排程設定正確**

```bash
python3 -m pytest tests/ -q
```

Expected: all tests pass（排程本身無 unit test，依賴整體不破壞）

**Step 4: Commit**

```bash
git add src/scheduler/jobs.py src/scheduler/runner.py
git commit -m "feat(scheduler): split flash deals refresh - momo every 3h, pchome every 1h"
```

---

## Task 2：建立 GCP 部署用 docker-compose override

**Files:**
- Create: `docker-compose.gcp.yml`

**Step 1: 建立檔案**

```yaml
# GCP e2-micro 部署 override
# 使用方式：docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.gcp.yml up -d
services:
  app:
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    restart: always
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  # 前端由 Nginx 靜態服務，不需要 Node.js 容器
  frontend:
    profiles:
      - disabled
```

**Step 2: 確認 docker-compose 語法正確**

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.gcp.yml config --quiet
```

Expected: 無錯誤輸出

**Step 3: Commit**

```bash
git add docker-compose.gcp.yml
git commit -m "feat(deploy): add docker-compose.gcp.yml for GCP e2-micro (frontend disabled)"
```

---

## Task 3：Next.js 靜態匯出設定

**Files:**
- Modify: `frontend/next.config.js`
- Create: `frontend/src/app/cards/[id]/CardDetailClient.tsx`
- Modify: `frontend/src/app/cards/[id]/page.tsx`

**Step 1: 修改 `next.config.js`**

將 `output: "standalone"` 改為 `output: "export"`，並移除不支援 static export 的 `rewrites()`（Nginx 負責代理）：

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  images: {
    unoptimized: true,
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
    ],
  },
};

module.exports = nextConfig;
```

> 注意：`output: 'export'` 不支援 `rewrites()`，改由 Nginx 代理 `/api/*`。`images.unoptimized: true` 是 static export 必要設定。

**Step 2: 將 `/cards/[id]/page.tsx` 的 client 邏輯移到獨立元件**

建立 `frontend/src/app/cards/[id]/CardDetailClient.tsx`，內容為原 `page.tsx` 的完整程式碼（保留 `"use client"` 與所有 import）。

**Step 3: 改寫 `frontend/src/app/cards/[id]/page.tsx` 為 Server Component**

```tsx
import CardDetailClient from "./CardDetailClient";

export const dynamicParams = false;

export async function generateStaticParams() {
  try {
    const apiUrl = process.env.API_URL || "http://localhost:8000";
    const res = await fetch(`${apiUrl}/api/cards?page=1&size=500`);
    if (!res.ok) return [];
    const data = await res.json();
    return (data.items || []).map((card: { id: number }) => ({
      id: String(card.id),
    }));
  } catch {
    return [];
  }
}

export default function CardDetailPage() {
  return <CardDetailClient />;
}
```

**Step 4: 本機測試 static export 可否建置（需先啟動後端）**

```bash
# 確保後端在 localhost:8000 運行
API_URL=http://localhost:8000 npm run build --prefix frontend
```

Expected: `frontend/out/` 目錄產生，包含 `cards/1/index.html` 等靜態頁面

**Step 5: Commit**

```bash
git add frontend/next.config.js frontend/src/app/cards/[id]/
git commit -m "feat(frontend): switch to static export for GCP deployment"
```

---

## Task 4：建立 Nginx 設定檔

**Files:**
- Create: `nginx/deal-radar.conf`

**Step 1: 建立設定檔**

```nginx
server {
    listen 80;
    server_name _;

    root /var/www/deal-radar;
    index index.html;

    # 靜態前端：先嘗試精確路徑，再試 .html，再試目錄，最後 404
    location / {
        try_files $uri $uri.html $uri/ =404;
    }

    # API 反向代理至後端
    location /api/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }

    # 健康檢查端點
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }

    # 關閉 access log 節省 I/O（e2-micro 磁碟較小）
    access_log off;
    error_log /var/log/nginx/deal-radar.error.log warn;
}
```

**Step 2: Commit**

```bash
git add nginx/deal-radar.conf
git commit -m "feat(deploy): add nginx config for static frontend + API reverse proxy"
```

---

## Task 5：建立 VM 初始化腳本

**Files:**
- Create: `scripts/gcp-vm-setup.sh`

**Step 1: 建立腳本**

```bash
#!/usr/bin/env bash
# GCP e2-micro VM 初始化腳本
# 執行一次：bash scripts/gcp-vm-setup.sh
set -euo pipefail

echo "=== [1/5] 更新套件 ==="
sudo apt-get update && sudo apt-get upgrade -y

echo "=== [2/5] 安裝 Docker ==="
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"

echo "=== [3/5] 安裝 Nginx ==="
sudo apt-get install -y nginx
sudo systemctl enable nginx

echo "=== [4/5] 建立 2GB swap ==="
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
    sudo sysctl -p
    echo "Swap 已建立並設為永久"
else
    echo "Swap 已存在，略過"
fi

echo "=== [5/5] 建立應用目錄 ==="
sudo mkdir -p /var/www/deal-radar
sudo chown "$USER:$USER" /var/www/deal-radar
mkdir -p ~/deal-radar

echo ""
echo "=== 完成！請重新登入以套用 docker 群組設定 ==="
echo "下一步："
echo "  1. 重新登入 VM"
echo "  2. 執行 bash scripts/gcp-deploy.sh 部署應用"
```

**Step 2: 建立部署/更新腳本**

Create `scripts/gcp-deploy.sh`:

```bash
#!/usr/bin/env bash
# 部署或更新 deal-radar（在 VM 上執行）
# 使用方式：bash scripts/gcp-deploy.sh
set -euo pipefail

APP_DIR="$HOME/deal-radar"
STATIC_DIR="/var/www/deal-radar"

echo "=== [1/4] 拉取最新程式碼 ==="
cd "$APP_DIR"
git pull origin main

echo "=== [2/4] 設定 Nginx ==="
sudo cp nginx/deal-radar.conf /etc/nginx/sites-available/deal-radar
sudo ln -sf /etc/nginx/sites-available/deal-radar /etc/nginx/sites-enabled/deal-radar
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

echo "=== [3/4] 啟動後端容器 ==="
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.gcp.yml up -d --build

echo "=== [4/4] 等待後端健康 ==="
echo "等待 API 就緒..."
for i in $(seq 1 12); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "API 就緒！"
        break
    fi
    echo "  等待中... ($i/12)"
    sleep 5
done

echo ""
echo "=== 部署完成 ==="
echo "前端靜態檔請另外上傳至 $STATIC_DIR"
echo "  本機執行：scp -r frontend/out/* user@VM_IP:$STATIC_DIR/"
```

**Step 3: 賦予執行權限並 commit**

```bash
chmod +x scripts/gcp-vm-setup.sh scripts/gcp-deploy.sh
git add scripts/gcp-vm-setup.sh scripts/gcp-deploy.sh
git commit -m "feat(deploy): add GCP VM setup and deploy scripts"
```

---

## Task 6：更新 README 部署章節

**Files:**
- Modify: `README.md`（新增 GCP 部署段落）

**Step 1: 在 README.md 的 Docker Commands 段落之後加入**

```markdown
## GCP 免費方案部署

使用 GCP e2-micro（永久免費），Nginx 服務靜態前端，Docker 跑後端。

### 前置條件
- GCP 帳號，建立 e2-micro VM（us-central1，30GB 標準磁碟，開放 port 80）
- 本機已安裝 `gcloud` CLI 並完成驗證

### 步驟

**1. VM 初始化（首次）**
```bash
# SSH 進 VM
gcloud compute ssh INSTANCE_NAME --zone=ZONE

# 下載並執行初始化腳本
git clone https://github.com/YOUR_REPO/deal-radar.git ~/deal-radar
cd ~/deal-radar
cp .env.example .env  # 填入 Telegram/Discord 等設定
bash scripts/gcp-vm-setup.sh
# 重新登入後繼續
```

**2. 建置前端靜態檔（本機執行）**
```bash
# 確保後端在本機 8000 port 運行（用於 generateStaticParams）
API_URL=http://localhost:8000 npm run build --prefix frontend
# 上傳靜態檔至 VM
scp -r frontend/out/* USER@VM_EXTERNAL_IP:/var/www/deal-radar/
```

**3. 部署後端**
```bash
# 在 VM 上
bash ~/deal-radar/scripts/gcp-deploy.sh
```

**4. 更新部署**
```bash
# 本機：重建前端並上傳
API_URL=http://localhost:8000 npm run build --prefix frontend
scp -r frontend/out/* USER@VM_EXTERNAL_IP:/var/www/deal-radar/

# VM 上：更新後端
cd ~/deal-radar && bash scripts/gcp-deploy.sh
```
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add GCP free tier deployment guide to README"
```

---

## 部署驗證清單

完成所有 Task 後，在 VM 上確認：

```bash
# 後端健康
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# API 可查詢（透過 Nginx）
curl http://VM_EXTERNAL_IP/api/flash-deals | head -c 200

# 前端首頁
curl -s -o /dev/null -w "%{http_code}" http://VM_EXTERNAL_IP/
# Expected: 200

# Swap 確認
free -h
# Expected: Swap 顯示 2.0G
```
