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

- **2026-10-24 修補 Dependabot 警示（`package-lock.json`）**：
  - 只動 `package-lock.json` 與 `.cursor/rules/no-upstream-pr.mdc`，沒有改任何產品程式碼，也沒有同步上游。鎖檔由 `npm update vite fast-uri --package-lock-only --ignore-scripts` 產生；`npm ci --ignore-scripts` 驗證。
  - `vite` 8.3.2 → 8.3.5（Dependabot #1、#2、#3：GHSA-587h-7wmj-h5pm high、GHSA-r825-w8mm-5pxw 與 GHSA-698v-4r3x-3vcv medium）。`vite` 是 `vitest` 的 peer，只在 dev 使用；`vitepress` 另有自己的 `vite` 6.4.4，不在受影響範圍。Dependabot PR #1 保持開啟。
  - `fast-uri` 3.1.8 → 3.1.9（`npm audit` moderate，無警示）。
  - lock diff：只有上述兩個版本變動，加上 `vite` 8.3.5 自帶的巢狀 `rolldown` 1.2.15、`postcss` 8.5.31、`@oxc-project/types` 與平台 binding（18 個新條目，全部來自 `registry.npmjs.org`，沒有新的 install script）。
  - **暫緩 `zod`（`npm audit` high，GHSA-mrhx-c7xc-m3w5，無 Dependabot 警示）**：直接相依，釘在 4.4.3，修補版只有 4.6.6／4.6.7。實測升到 4.6.7 與 4.6.6 都會讓 5 個測試失敗，且降回 4.4.3 後全部通過：`src/domain/offsetDateTime.test.ts`（省略秒數的 offset datetime 判定與先前的 Zod 驗證器不同）與 `tests/boundary/cli/cliInputSchemaRequired.test.ts` 的 4 個案例（由 Zod 產生的 CLI 輸入 JSON Schema 經 `ajv.compile` 後拒絕合法輸入或與 parser 的界線不一致）。修正需要改產品程式碼（`src/domain/offsetDateTime.ts` 與 CLI 輸入 schema 產生處），超出依賴更新的範圍。**重新評估條件**：有人為 zod 4.6 行為調整這兩處程式碼與測試時，同一個 PR 把 `zod` 升到 ≥ 4.6.6。
  - **驗證限制**：本機是 Windows，完整 `vitest run` 在未改動的 `main` 也有 1831 個失敗（POSIX 訊號語意、缺少 `native/windows/build` 等），所以用同一台機器的前後差異比對：升級後的失敗集合與 `main` 只差上述 5 個 zod 測試（`main` 另有 3 個只在基準線失敗的測試，屬於同一批環境性的不穩定）。`typecheck`、`lint`、`format:check`、`metadata:check`、`knip`（先 `npm run compile`）全綠。完整 gate 以 GitHub Actions 為準。
  - 補上 `.cursor/rules/no-upstream-pr.mdc`（這個 fork 先前沒有），規定 PR、push、release 只打 `SanHsien/rea`。
