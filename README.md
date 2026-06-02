# AI-Driven Data Pipeline (智慧資料萃取管線)

這是一個高度模組化的自動化資料收集與 AI 分析管線。設計初衷是為了解決動態網頁爬蟲與非結構化資料萃取的痛點，可通用於競品分析、金融情資收集等各種情境。

## 💡 核心亮點 (Key Features)
* **突破動態渲染與反爬蟲**：使用 `Playwright` 模擬無頭瀏覽器，並具備 X 光透視機制與動態下載攔截。
* **雙階段 LLM 分析架構 (Two-Step Verification)**：先萃取網頁主體進行初審，若偵測到附加檔案（PDF/Word），再進行深度的二次萃取與交叉比對，大幅提升資料精準度。
* **高泛化能力 (Highly Customizable)**：透過獨立的 `config.json` 即可抽換所有的提示詞 (Prompt) 與分類標籤，無需修改核心程式碼即可適應不同產業需求。
* **模組化設計**：遵循 ETL (Extract, Transform, Load) 邏輯，分離爬蟲、分析與資料清洗模組，確保系統穩定性與可觀測性。

## 📁 系統架構 (Architecture)
* `main.py`：專案總指揮入口，提供互動式 CLI 介面。
* `config.json`：動態參數與 Prompt 設定檔。
* `src/crawler.py`：自動化網頁探索與附件下載。
* `src/analyzer.py`：串接大語言模型進行 JSON 格式化推論。
* `src/formatter.py`：將萃取結果清洗、打包並輸出為 Excel 戰略報表。

## 🛠️ 如何執行 (How to Run)
1. 在 `config.json` 填寫你的 API Key 與目標設定。
2. 於終端機執行 `python main.py`。
3. 依照互動選單選擇要執行的階段任務。
