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
- **2026-10-24：`cli-boundary` 測試 worker 堆積上限由 384 MB 調為 768 MB**：
  - 現象：`CI` 手動 run 40087950360（main `0379e16`，full tier、開 V8 coverage）的 `Test shard (6/6)` 在 `tests/boundary/cli/adbWindowFocus.test.ts` 發生 `JavaScript heap out of memory`（worker SIGABRT），`Portable tests` 合併報告時重播該錯誤、`CI required` 隨之失敗；同一 SHA 的 push run（fast tier、無 coverage）是綠的。
  - 根本原因：`cli-boundary` 使用 `isolate: false` 的長駐 forks worker，`execArgv` 固定 `--max-old-space-size=384`。10-17 新增的 adb 測試同時走 CLI 與 in-process MCP harness，把工具契約目錄與 MCP server 模組圖載入共用 worker；本地量測 full GC 後的存活堆積在 V8 coverage 下達 ~380 MB（無 coverage ~292 MB），等於上限，非單一測試洩漏。
  - 決策：保留「讓 worker 提早 GC」的上限設計，改為 768 MB（約 2 倍存活堆積），不跳過或搬移測試、不改 shard 分配。
