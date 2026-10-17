# 上游更新同步評估與決策紀錄（2026-10-17）

## 1. 執行背景與目標

- **上游儲存庫**：[`morluto/rea`](https://github.com/morluto/rea.git) (`main` 分支)
- **同步基線**：
  - 起始 SHA：`42fc6c53ae188978deb3bedfe88287b6b316ba22`（2026-10-16 基準）
  - 目標 SHA：`988494abdbb27fb91ca6bd80362c9f1a332f86c3`（2026-10-17 最新提交）
  - 累積提交數量：共 128 個 commit（包含使用者原先指出的 35 個提交與上游今日最新修復）
- **核心目標**：
  1. 建立自動排程機制（比照使用者其他 repo 如 `Antigravity-Manager` 與 `paulsha-cortex` 之規格）。
  2. 評估上游 128 個 commit 對本 Fork（特別是剛完成之 Windows 11 原生相容性硬化補丁與繁中單一基準策略）的影響。
  3. 完成同步整合、調和衝突、驗證品質門檻，並留下可追溯的決策紀錄供日後維護參考。

---

## 2. 上游更新範疇與分類評估

上游在此區間內主要進行了深度的所有權生命週期（Resource Ownership & Lifecycle）與取消語意重構，各模組關鍵提交如下：

### A. Provider 清理、所有權生命週期與取消重構
- **重大架構重構**：`150e996a8` (`refactor(providers)!: await owned readiness observations`)
  - 將所有 Provider 的就緒狀態探測調整為非同步 `await`，保證資源在獲取失敗或中途取消時能被其擁有者確實釋放。
- **Ghidra** (`cc2e18a26`, `c72786f28`, `5112fe07a`, `e31aa72c9`, `1e36e707b`, `8267edc0e`, `1b56237ca` 等)：
  - 支援非同步 Java 探測與取消語意；增強 macOS Homebrew openjdk 解析；啟動超時與回滾機制。
- **Kuna** (`988494abd`, `5717ad24a`, `6eb55be4e`, `54c71313a`, `6d5281407`, `8ab502439`)：
  - 改善可取消安裝啟動；字串掃描由原本 16 MiB 上限改為串流處理；明確失敗歸屬。
- **JEB** (`ece277b30`, `67384b23e`, `a6e8f5269`, `d74e72406`)：
  - 獨立快取解析元數據；操作逾時準確歸屬；獲取結果與清理所有權保全。
- **Cutter & Rizin** (`71929ed37`, `199396f61`, `5c0472c57`, `2b7b698db`, `1ff705473`, `9a82046b0`, `2c1dee16d`, `a6c6a76d3`)：
  - 規範化檢查點取消；保留中斷之命令幀；探測取消與佇列工作清理。
- **ADB** (`be0b2d138`, `7086768a2`, `3d028dbc7`, `c4475d4a6`, `0d2247428`, `61e688070`)：
  - 卸載請求限定於 user 0；區分無焦點與缺少宣告；保留命令擁有者取消結果。
- **Electron & Browser** (`360626434`, `709b5cbdc`, `bf3475867`, `ce0d6790e`, `df2fc251e`, `c360cfcd6`, `d72d856f5`, `5a77acfbc`)：
  - 保留原生 IPC 監聽行為；捕捉期間阻擋同步 Shell 效應；CDP 清理租約綁定。

### B. 語言語意與二進位分析
- **JavaScript AST** (`bfb7ed0bd`, `c3e42385e`, `0c7b6d834`, `556504edc`, `4d980d017`, `ab13a1c67`, `6c06f406f`, `17488bd63`, `6d2eeeaed`, `3eeada71f`, `2c7583599`, `d9d085a15`)：
  - 保留賦值與巢狀預設解構；從確切常值推導迴圈基數；限制 local getter-result 展開；端點追蹤納入 response carrier。
- **Native & Binary** (`8116dc065`, `060587b45`, `a70c42e03`, `f31b231a9`, `0f61261e0`, `467f5572a`, `3d4417684`, `9e7e13fb7`)：
  - PE 資源區間忽略零大小節區；解碼邊界恢復異常 Objective-C 名稱；PE 輸入位元組預算報告為檔案上限。

---

## 3. 衝突排查與調和決策

在合併 upstream/main 過程中，共有 2 處實質程式碼衝突與 4 處語系檔案 Modify/Delete 衝突：

| 衝突路徑 | 衝突性質 | 上游改動 | 本 Fork 現狀 | 最終裁決與調和方案 |
| :--- | :--- | :--- | :--- | :--- |
| `src/browser/PlaywrightBrowserScenarioProvider.test.ts` | 程式碼衝突 | 強化測試斷言，匹配完整 `partialObservation` 物件並驗證 `error.cause`。 | 先前為避開型別錯誤使用單純字串判定。 | **採納上游**。上游的新斷言更加嚴謹全面，且型別定義已完善。 |
| `src/ghidra/GhidraInstallation.ts` | 程式碼衝突 | 將 `probeJava` 重構為非同步並支援 `javaProbeFailure` 錯誤投影。 | 包含 `win32.isAbsolute(options.javaHome)` 之 Windows 路徑判定。 | **融合雙方優點**。在 `javaProbe` 條件判斷中保留 `path.isAbsolute(options.javaHome) \|\| win32.isAbsolute(options.javaHome)`，下方的結構完整採用上游的 `javaProbeFailure` 機制。 |
| `docs/readme/README_ko.md` | 語系衝突 | 上游修正韓文翻譯。 | 本 Fork 已統一繁中單一基準並刪除此檔。 | **維持刪除** (`git rm`)。符合 Fork 精簡策略。 |
| `website/locales/ko/messages.po` | 語系衝突 | 上游修正韓文 po。 | 本 Fork 已刪除此檔。 | **維持刪除** (`git rm`)。 |
| `website/locales/tr/messages.po` | 語系衝突 | 上游修正土耳其文 po。 | 本 Fork 已刪除此檔。 | **維持刪除** (`git rm`)。 |
| `website/locales/zh-CN/messages.po` | 語系衝突 | 上游修正簡中 po。 | 本 Fork 已刪除此檔。 | **維持刪除** (`git rm`)。 |

### 本 Fork 專屬 Windows 11 硬化機制檢驗
經比對驗證，本 Fork 原先實作之核心 Windows 11 相容性補丁完全未受上游變更干擾，依然完整生效：
1. `src/application/JsonFiles.ts`：原子寫入安全機制（NTFS 在同一實體檔案或無 hard link 權限時安全降級為 copy+delete）。
2. `src/application/SetupSkill.ts`：Windows 軟連結 `EPERM` 權限降級相容機制。
3. `src/application/SupportedClients.ts`：Windows 平台二進位副檔名（`.exe`、`.cmd`、`.bat`）自動補全探測。
4. `src/windows/WindowsOwnedProcess.ts`：Windows 進程樹安全終止回收與 taskkill fallback。

---

## 4. 自動檢查排程設計

依循使用者於其他 Repo 之統一架構，建立了上游更新自動排程與工具：
1. **設定檔**：`tools/upstream_baseline.json`
   - 記錄追蹤目標 (`https://github.com/morluto/rea.git`)、追蹤分支 (`main`)、當前基準 SHA (`988494abdbb27fb91ca6bd80362c9f1a332f86c3`)、PR/Issue 水位 (#4700) 與決策報告路徑。
2. **檢查腳本**：`tools/check_upstream_updates.py`
   - 純 Python 3 標準庫實現，相容 Windows 11 與 Linux。
   - 計算 Fork status（共同 baseline、Ahead / Behind commits 數）。
   - 支援 `--strict` 模式（若發現未審核上游提交則返回 non-zero exit code）。
   - 自動渲染 Markdown 審核摘要與改動清單。
3. **CI 排程工作流**：`.github/workflows/upstream-check.yml`
   - 觸發條件：每週一 03:00 UTC 定時排程 (`cron: "0 3 * * 1"`)、`workflow_dispatch` 手動觸發、以及工具設定更新時觸發。
   - 結果發布：自動將比對報告輸出至 `$GITHUB_STEP_SUMMARY`，有新提交時立即發出工作流告警，督促團隊進行評估與同步。

---

## 5. 即時 PR 與 Issue 水位審閱（至 #4705）

經 `tools/check_upstream_updates.py` 即時比對，上游最新議題如下：
- **PR #4703** (`test(kuna): preserve caller and producer graph failure context`)：針對 Kuna graph 在 caller 與 producer 失敗上下文保全的單元測試，為後續測試加固，對本 Fork 既有功能無破壞性影響。
- **Issue #4701** (`[Bug] Kuna graph retry tests expect producer operation after caller attribution`)：回報重試測試預期行為，目前上游正在 PR #4703 中收斂。
- **Issue #4702** (`[Bug] Kuna command cleanup retry leaves original ownership unresolved`)：追蹤指令清理重試時原始所有權的解析邊界，本 Fork 保持關注，待上游發布修復後由排程自動告警。

已將水位推進至 `#4705`，避免日後重複警報。

---

## 6. 結論與後續維護

- 本次同步成功將 `morluto/rea:main` 自 2026-10-16 以來累積之 **128 個 commits** 完整合併。
- 專案維持所有 Windows 11 原生相容性修正與繁中語系慣例。
- 日後上游更新將透過 GitHub Actions 自動排程定期檢測，若有新提交僅需執行 `python tools/check_upstream_updates.py` 產出差異並更新 `upstream_baseline.json`，無需再重複進行全域盤點。
