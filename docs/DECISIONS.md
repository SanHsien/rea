# 決策紀錄

- **上游基準**：`morluto/rea` `main`（MIT）。
- **只留 `main` 分支，不提前合併上游 WIP 分支**：
  - 138 條分支（舊 release、修復分支、實驗分支與 bot 分支）名稱與 SHA 留存於 [`docs/records/removed-branches-2026-10-16.tsv`](records/removed-branches-2026-10-16.tsv)。
  - 分流評估詳見 [`docs/records/upstream-branch-evaluation-2026-10-16.md`](records/upstream-branch-evaluation-2026-10-16.md)：因上游屬超高頻迭代專案，提前合併 WIP 分支易造成未來同步嚴重衝突；採「跟隨上游主線 `main`」，未來實測遇到特定問題時再按紀錄提取對應修復。
- **只留最新 tag（`rea-agents-6.5.0`）**：舊有 35 個 tag 名稱與 SHA 留存於 [`docs/records/removed-tags-2026-10-16.tsv`](records/removed-tags-2026-10-16.tsv)。
- **文件與語系慣例**：
  - 根目錄 `README.md` 預設繁體中文，新增 `README.en.md` 英文鏡像。
  - 不保留簡體中文，移除非繁體中文、非英文的所有 README 檔案（`docs/readme/`）與語系目錄（`website/locales/`），僅保留繁體中文與英文。
  - 移除所有宣傳上游的內容（Discord 徽章/社群、Trendshift 排名、Star 歷史圖表、skills.sh 連結與官方防 fork 宣告）。
  - GitHub About 欄位採用雙語（中文在前，`｜` 分隔），清空 `homepageUrl` 並補齊相關 topics。
