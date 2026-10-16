# 上游分支分流評估報告（2026-10-16）

## 1. 分支現況統計（共 138 條未合入分支）

| 類別 | 分支數 | 代表分支範例 | 性質說明 |
|---|---|---|---|
| `fix/*` | 47 | `fix/windows-window-capture-2183`, `fix/ghidra-*`, `fix/hopper-*` | 針對特定 issue 的 bug 修復 PR，多數等待審查中 |
| `codex/*` | 26 | `codex/bug-sweep-*`, `codex/windows-*`, `codex/ci-*` | 上游使用 AI/Codex 進行的批次巡檢與修復分支 |
| `review/*` / `review-fixes/*` | 10 | `review/ghidra-*`, `review/process-*` | PR 審查後的微調與修正 |
| `feat/*` | 8 | `feat/artifact-integrity-policy`, `feat/windows-window-capture` | 尚未定案的大型新功能 |
| `test/*` / `perf/*` / `audit/*` | 13 | `test/perf/measure-windows-mcp`, `audit/windows-proof` | 上游 CI 探針、效能測試與除錯腳本 |
| `release/*` / `release-please--*` | 8 | `release/5.0.0` ~ `6.3.0`, release-please bots | 舊版維護或自動化 bot 分支，完全無價值 |
| `cursor/*` / `chatgpt/*` / `agent/*` | 9 | `cursor/cloud-agent-*`, `agent/javascript-*` | 外部或特定代理的獨立實驗 |
| 其他（`morl/*`, `docs/*`, `chore/*`） | 17 | 作者個人草稿與文件調整 | 多數已被主線覆蓋或非核心變更 |

## 2. 評估結論：建議跟隨上游主線 `main`，不提前合併個別分支

### 理由：

1. **上游超高頻迭代（非停滯專案）**：
   - 上游有 4,400+ PRs，幾乎每天皆有數十個 commit 合入。
   - 目前在分支上的有效修復（如 bug-sweep），上游維護者通常在數天至一週內就會正式 review 併入 `main`。
2. **避免維護分歧（Divergence）與同步衝突**：
   - 提前手動 cherry-pick 未經上游定案的 PR，一旦上游 review 階段要求重構、改名或改寫，下次我們 `git fetch upstream main` 同步時會引發大量手動衝突。
3. **穩定性考量**：
   - `main` 上的 v6.5.0 是經過完整多平台 CI 驗證的正式標籤；未合入分支多含有未完成的測試、未確定的 API 契約。
4. **隨時有跡可循**：
   - 138 條分支的名稱與 commit SHA 已完整留存於 [`removed-branches-2026-10-16.tsv`](removed-branches-2026-10-16.tsv)。
   - 未來本機 Windows 實測若遇到具體障礙（例如特定 Windows Ghidra 橋接問題），可再精準檢索該清單提取特定 patch，不需盲目全數提前吸收。
