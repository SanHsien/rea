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
  - 動到 `package.json`、`package-lock.json`、`.cursor/rules/no-upstream-pr.mdc`、本檔，以及為 `zod` 4.6 所做的兩處最小程式碼調整（`src/cli/omittableDefaults.ts`、`src/domain/offsetDateTime.ts` 的註解與其測試），沒有同步上游。鎖檔由 `npm update vite fast-uri --package-lock-only --ignore-scripts` 產生；`npm ci --ignore-scripts` 驗證。
  - `vite` 8.3.2 → 8.3.5（Dependabot #1、#2、#3：GHSA-587h-7wmj-h5pm high、GHSA-r825-w8mm-5pxw 與 GHSA-698v-4r3x-3vcv medium）。`vite` 是 `vitest` 的 peer，只在 dev 使用；`vitepress` 另有自己的 `vite` 6.4.4，不在受影響範圍。Dependabot PR #1 保持開啟。
  - `fast-uri` 3.1.8 → 3.1.9（`npm audit` moderate，無警示）。
  - lock diff：只有上述兩個版本變動，加上 `vite` 8.3.5 自帶的巢狀 `rolldown` 1.2.15、`postcss` 8.5.31、`@oxc-project/types` 與平台 binding（18 個新條目，全部來自 `registry.npmjs.org`，沒有新的 install script）。
  - **已修 `zod` 4.4.3 → 4.6.7（`npm audit` high，GHSA-mrhx-c7xc-m3w5，無 Dependabot 警示）**：直接相依，lock 內只有一份 `zod`，`@modelcontextprotocol/*` 與 `incur` 都解析到它。
    - 攻擊路徑：`$ZodArray` 對沒有長度上限的陣列會收集每個失敗元素的 issue，超大輸入會耗盡記憶體。MCP 工具輸入（`src/server/registerArtifactTools.ts`、`registerBrowserScenarioTool.ts`）、被分析網站的 cookies／local_storage（`src/domain/browserScenarioCapture.ts`）與外部 MCP 伺服器回傳資料（`src/server/EvidenceMcpServer.ts`）在執行期都會經過 zod。
    - 升級讓 5 個測試失敗，原因有兩個，對外契約都維持和升級前相同：
    1. 省略秒數的時間（`2026-10-09T04:00Z`）：zod 4.6 的 `datetime({ offset: true })` 依 RFC 3339 拒絕，zod 4.4 接受。`src/domain/offsetDateTime.ts` 的手寫正則**不改**，CLI／MCP 仍接受這種寫法（不縮窄輸入），只更新註解。`src/domain/offsetDateTime.test.ts` 的 zod 對照組以具名常數 `INTENTIONAL_ZOD_DIVERGENCES` 只排除「omitted seconds」這一例，並新增獨立測試直接釘住「省略秒數仍被接受、`04Z` 與 `04:0Z` 仍被拒絕」。
    2. `--schema` 的 `required`：zod 4.6 的 `z.toJSONSchema`（output 模式）把帶 `.default()` 的欄位列為必填，而 `incur`（0.6.1，最新 0.7.1 相同）的 `Schema.js` 呼叫時沒有帶 `io: "input"`。`src/cli/omittableDefaults.ts` 早已把有預設值的欄位包成 optional 來抵消這件事，但它判斷「有預設值」用的是 `_zod.optin === "optional"`；zod 4.6 對 `.default()` 回報 `"defaulted"`，所以判斷落空。現在兩個值都算（仍要求 `optout` 為 `undefined`，單純的 `.optional()` 不受影響），從 zod schema 判斷、沒有寫死欄位名單。`tests/boundary/cli/cliInputSchemaRequired.test.ts` 的期待值完全沒改。
    - 後處理的移除條件：`incur` 呼叫 `z.toJSONSchema` 時帶上 `io: "input"`，並且移除 `presentOmittableDefaults` 後上述測試仍全綠。這是對 `incur` 行為的 fork 端因應，不向上游回報（需維護者另行同意）。
  - **驗證限制**：本機是 Windows，完整 `vitest run` 在未改動的 `main` 也有 1831 個失敗（POSIX 訊號語意、缺少 `native/windows/build` 等），所以用同一台機器的前後差異比對。最終狀態（zod 4.6.7）失敗 1830 個；與 `main` 相比，唯一多出的是 `tests/acceptance/applications/runtime.test.ts` 的「reports a missing target through MCP and structured logs」（全套負載下逾時 15 秒），單獨重跑兩次都通過，屬負載造成的不穩定；`main` 另有 2 個只在基準線失敗的測試。`typecheck`、`lint`、`format:check`、`metadata:check`、`knip`（先 `npm run compile`）全綠；`offsetDateTime.test.ts` 與 `cliInputSchemaRequired.test.ts` 共 35 項通過。完整 gate 以 GitHub Actions 為準（目前此 repo 的 Actions 被停用）。
  - 補上 `.cursor/rules/no-upstream-pr.mdc`（這個 fork 先前沒有），規定 PR、push、release 只打 `SanHsien/rea`。
