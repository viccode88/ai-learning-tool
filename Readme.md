## 目錄

1. [專案簡介](#專案簡介)
2. [快速開始](#快速開始)
3. [更新日誌](#快速開始)
---

## 專案簡介

本專案是一個整合式 AI 學習平台，目前提供兩大核心功能：

- **英文學習助手**：智能查詢、對話練習、語音合成
- **數學解題系統**：高中數學詳細解題、概念解釋、圖片識別

### 技術棧

**後端**
- FastAPI
- OpenAI API
- Python3.x

**前端**
- React 19
- Vite 6
- TailwindCSS 3
- Framer Motion
- Lucide React

---

## 快速開始

### 環境需求

- Python 3.8+
- Node.js 16+
- OpenAI API Key

### 1. 安裝依賴

#### 後端依賴

```bash
# 進入專案根目錄
cd self_ai_project

# 安裝 Python 依賴
pip install -r requirements.txt
```

主要依賴：
```
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
pydantic>=2.8.0
httpx>=0.27.0
openai>=1.40.0
python-multipart>=0.0.9
python-dotenv>=1.0.0
```

#### 前端依賴

```bash
# 進入前端目錄
cd App/front

# 安裝 Node.js 依賴
npm install
```

### 2. 開始使用

#### 使用互動式腳本（推薦）

```bash
chmod +x interactive.sh
./interactive.sh
```

首次運行時，系統會自動引導您完成 API 金鑰設定。

#### 手動設定

在 `backend/` 目錄下創建 `.env` 文件：

```bash
cd backend
echo "OPENAI_API_KEY=sk-your-actual-api-key-here" > .env
```

### 3. 啟動服務

#### 使用互動式管理器（推薦）

```bash
./interactive.sh
# 輸入 'start' 啟動所有服務
```

#### 手動啟動

**後端**
```bash
cd backend
python main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8000
```

**前端**
```bash
cd App/front
npm run dev
```

### 4. 訪問應用

- **前端界面**：http://localhost:5173
- **後端 API**：http://localhost:8000
- **API 文檔**：http://localhost:8000/docs

---

## 更新日誌

### v0.3.1(當前)
- 新增深色模式
- 優化 UI/UX
- 修復已知 bug
- 改進對話記錄系統

### v0.3.0
- 初始版本發布
- 英文學習基礎功能
- 數學解題基礎功能

---

