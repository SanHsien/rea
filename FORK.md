# Fork 說明

本 repo 是 [morluto/rea](https://github.com/morluto/rea) 的 Windows 優先維護 fork。原作者與版權持有人是 morluto，原始專案的功能與設計歸上游所有。

## 來源與授權

| 項目       | 內容                                                                                                                  |
| ---------- | --------------------------------------------------------------------------------------------------------------------- |
| 上游       | `morluto/rea`，預設分支 `main`                                                                                        |
| 授權       | MIT（`gh api repos/morluto/rea/license` 回報 SPDX `MIT`；本 repo 的 `LICENSE` 版權行為 `Copyright (c) 2026 morluto`） |
| 目前同步點 | `rea-agents-6.8.0`，commit `160d821ac9a0310afcb8d1fc427862dd6508add5`（`tools/upstream_baseline.json`）               |
| 授權文字   | 沿用上游 `LICENSE`，未更動                                                                                            |

## 為什麼有這個 fork

來源是 [`ROADMAP.md`](ROADMAP.md) 的「現況」與 [`docs/DECISIONS.md`](docs/DECISIONS.md)：

- **Windows 優先維護**：在 Windows 11 原生環境修補檔案系統權限、路徑解析與行程樹終止等問題，報告見
  [`docs/records/codebase-review-and-windows-hardening-2026-10-17.md`](docs/records/codebase-review-and-windows-hardening-2026-10-17.md)。
- **以 release 為單位同步上游**：2026-10-27 起追 `rea-agents-*` 正式版本，不追 `main` 尖端；理由與衝突處理見
  [`docs/DECISIONS.md`](docs/DECISIONS.md) 與
  [`docs/records/upstream-sync-evaluation-2026-10-27.md`](docs/records/upstream-sync-evaluation-2026-10-27.md)。
- **發佈守衛**：發佈鏈只在 `morluto/rea` 執行，本 fork 不發佈 npm、MCP Registry 或網站。

## 與上游的差異

下列每一列都已對照上游 `main` 的檔案清單或內容檢查過（2026-11-08）。

| 項目                                                                                                                            | 與上游的差異                                                                                                                                                                                                                                                                                             |
| ------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tools/upstream_baseline.json`、`tools/check_upstream_updates.py`、`.github/workflows/upstream-check.yml`                       | 上游沒有這三個檔案。本 fork 用它們追蹤上游，見下節                                                                                                                                                                                                                                                       |
| `.github/workflows/release.yml`、`release-recovery.yml`、`website-pages.yml`                                                    | 上游有這些檔案。本 fork 在發佈用 job 加上 `github.repository == 'morluto/rea'` 條件，fork 不會發佈。`release.yml` 有三處守衛、`release-recovery.yml` 與 `website-pages.yml` 各一處                                                                                                                       |
| `.github/workflows/dependency-freshness.yml`、`tools/check_dependency_freshness.py`、`tools/test_check_dependency_freshness.py` | 上游沒有。檢查精確釘版是否落後 registry                                                                                                                                                                                                                                                                  |
| `.github/dependency-deferrals.json`                                                                                             | 上游沒有。逐筆記錄延後升級某依賴的理由與 `deferredLatest`，registry 超過該版就失效並重新評估                                                                                                                                                                                                             |
| `package.json` 的 `overrides`                                                                                                   | 上游 `main` 只有 `typed-rest-client.qs`（6.16.1）與 `vitepress.vite`（6.4.4）。本 fork 多了 `@electron/asar`、`frida`、`@stryker-mutator/core`、`@google-automations/git-file-utils` 範圍限定的 `glob`／`minimatch` override，並把 `vitepress.vite` 升到 6.4.5。理由與重新評估條件見 `docs/DECISIONS.md` |
| `docs/DECISIONS.md`                                                                                                             | 上游沒有。記錄同步、告警判讀與偏離上游的決定                                                                                                                                                                                                                                                             |
| `docs/records/`                                                                                                                 | 上游 `main` 沒有這個目錄。放同步評估、Windows 強化報告等本 fork 的記錄                                                                                                                                                                                                                                   |
| `ROADMAP.md`                                                                                                                    | 上游沒有這個檔名（上游路線圖是 `docs/roadmap.md`，本 fork 不改）。這份只管本 fork 的維護工作                                                                                                                                                                                                             |
| `.cursor/rules/no-upstream-pr.mdc`                                                                                              | 上游沒有。規定 PR、push、release 一律指向 `SanHsien/rea`                                                                                                                                                                                                                                                 |
| `README.md`、`README.en.md`                                                                                                     | 加了 Fork 說明；預設語系為繁體中文，語系只留英文與繁中（`docs/DECISIONS.md` 2026-10-27 條）                                                                                                                                                                                                              |
| `AGENTS.md`                                                                                                                     | 兩邊都有。本 fork 的版本是較舊的上游內容，不含 fork 專屬段落；與上游 `main` 的差異來自上游之後新增的內容，會隨下次 release 同步更新                                                                                                                                                                      |

## 如何追蹤上游

- `tools/upstream_baseline.json` 設定 `track: release`、`release_tag_prefix: rea-agents-`、`ticket_cutoff: release`，目前已審查到 `rea-agents-6.8.0`、PR #7097、issue #7095，日期 2026-10-27。
- `.github/workflows/upstream-check.yml` 每週一 03:00 UTC 跑 `tools/check_upstream_updates.py`，也可手動觸發；報告水位之後的新 release、PR 與 issue。「查不到」不會被當成「沒有新東西」。
- `tools/check_upstream_updates.py` 是從 `SanHsien/repo-fleet-ops` 逐字複製的版本，不在 fork 內修改。
- 同步以 release 為單位，淨樹合併，上游歷史不進本 fork；作法與例外理由見 `docs/DECISIONS.md` 的 2026-10-27 條。

## 對外規則

PR、push、release 一律指向 `SanHsien/rea`，不指向上游；見 `.cursor/rules/no-upstream-pr.mdc`。
