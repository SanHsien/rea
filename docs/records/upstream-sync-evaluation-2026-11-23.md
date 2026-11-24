# 上游同步評估與決策紀錄（2026-11-23，`rea-agents-6.10.1`）

## 1. 範圍

- 上游：[`morluto/rea`](https://github.com/morluto/rea)。
- 前次水位：`rea-agents-6.8.0`（`160d821ac9a0310afcb8d1fc427862dd6508add5`，2026-10-27 審查）。
- 本次目標：上游最新正式版本 `rea-agents-6.10.1`（tag commit `8bb01b514ac766c0c3ecc8f362bd38186eaec9c2`，2026-11-20 發布；中間的 `6.9.0` 於 2026-11-12、`6.10.0` 於 2026-11-20 發布，一併帶入）。
  - 不追 `main` 尖端：同步當下上游 `main` 已在 tag 之後再前進；沿用 2026-10-16 起「以正式版本為粒度」的決定。
- 量體：`160d821..rea-agents-6.10.1` 共 3441 個 commit（非 merge 3439 個）；樹差異 8616 個檔、約 +128.8 萬／−45.4 萬行（`git diff --shortstat`，因檔數過多略過 rename 偵測）。
- PR／issue 軸：4324 筆 PR（#7098–#12737）、1230 筆 issue（#7096–#12920）。發布之後才開出的 1093 筆 PR、263 筆 issue 依 `ticket_cutoff: release` 留給下一個正式版本。

## 2. 作法：以 release 為單位的淨樹同步（沿用 2026-10-27 的有記錄例外，但合併基底改為真實的上游 tag）

fork 歷史已壓縮、與上游沒有共同祖先，所以仍以單一 commit 帶入結果，上游歷史不進 fork。這次比上次精確：

1. 本機建立從未推送的合成 commit，**父為 `rea-agents-6.8.0` tag、樹等於 fork `main`**（上次的父是更早的 `988494a`）。三方合併的基底因此就是上次同步的上游點，衝突只出現在 fork 自己動過的地方。
2. 把 `rea-agents-6.10.1` 合併進去並逐一解衝突。
3. 只把合併結果的樹以單一 commit 接在 fork `main` 上。

## 3. 衝突與 fork 修正的處理

| 類別                                                                                                                                     | 處理                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ---------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 語系檔（`docs/readme/README_*.md` 除 zh-TW、`website/locales/*/messages.po` 除 zh-TW）                                                   | 照舊只留英文與繁中，刪除上游新增與既有的其他語系（含新增的 `bg`）；`languages.json` 維持兩種語言；`messages.pot` 與 zh-TW 目錄以 `website.py translations extract` 重產，新增的 68 筆訊息（含新的 RL 環境指南頁）補繁體中文，`translations check --strict` 為 0 缺漏。`website/public/**` 以 `website.py sync` 重產。                                                                                                          |
| `README.en.md`、`README.md`（繁中）、`docs/readme/README_zh-TW.md`                                                                       | 英文鏡像以三方合併帶入上游改動；繁中兩份帶入並翻譯：新增的 RL 環境兩段、Kuna、Windows 捷徑／DWARF／ELF 相依性／二進位強化／NuGet／Deno 六個目標列、輸出 Schema 說明、套件執行器快取提醒；連結改為上游搬移後的 `docs/getting-started/`、`docs/guides/`、`docs/reference/` 等新路徑。不帶入 Discord 徽章與 Star 歷史（沿用「不宣傳上游」）。                                                                                     |
| `src/application/JsonFiles.ts` → `src/resources/TextFileWrite.ts`                                                                        | 上游把寫檔邏輯搬到新檔。fork 的 hard link 失敗（`EPERM`／`EXDEV`／`ENOSYS`）改 rename 的備援原樣補回新位置。                                                                                                                                                                                                                                                                                                                   |
| `src/process/ProcessOwnership.ts`                                                                                                        | 保留 fork 的 darwin `settledLivePids`（token 讀取失敗在清理寬限期內重列），並改用上游新的 `HOST_PLATFORM`；`docs/testing.md` 對應敘述搬到 `docs/development/testing.md`。                                                                                                                                                                                                                                                      |
| `src/ghidra/GhidraInstallation.ts`                                                                                                       | 合併兩邊：上游新增「沒有 application properties 就不探測 Java」，fork 保留「Windows 磁碟機代號的 `JAVA_HOME` 在任何主機都算絕對路徑」。                                                                                                                                                                                                                                                                                        |
| `src/cli/omittableDefaults.ts`、`src/domain/offsetDateTime.ts`、`src/domain/localPath.ts`（含測試）、`src/hopperPaths/MacHopperPaths.ts` | 採上游：上游已用不依賴 zod 版本的作法解決同一問題（`z.object({value}).safeParse({})`、自有的 ISO-8601 文法、host 無關的 Windows 絕對路徑 pattern、`appendCallerPath`）。2026-10-27 提前採用的 #7152 隨之成為上游本體。                                                                                                                                                                                                         |
| `scripts/ci/plan.mjs`、`scripts/ci/test-report.mjs`、`.github/workflows/ci.yml`、`ciChangeScope`／`ciTestReports` 測試                   | **撤回 2026-10-28「測試選擇改以檔案傳遞」的偏離**：上游改為選擇上限 400 個檔、超過就跑完整套件，選擇 JSON 不再隨變更路徑數量長大，不會再超過單一環境變數 128 KiB。`ci.yml` 只剩 fork 的週排程與 `CI_FORCE_FULL`；`ciChangeScope` 補回 fork 的「push 沒有 baseline 仍是 Linux fast tier」案例與 `README_zh-TW.md` 取代 `README_ja.md` 的路徑。                                                                                  |
| `.github/workflows/codeql.yml`、`.github/dependabot.yml`                                                                                 | 兩邊各自新增了同名檔。**保留 fork 的版本**（fork 的 CodeQL 告警判讀、dismiss 與觸發條件都建立在它上面；Dependabot 的 npm 版本更新維持關閉）。上游新增的 `.github/codeql/production.yml` 隨合併帶入但本 fork 的 workflow 不使用。                                                                                                                                                                                               |
| `package.json`／`package-lock.json`                                                                                                      | 採上游鎖檔，再重產：`zod` 維持 4.6.7（上游 4.6.6）、fork 的 `minimatch` 11.0.1 與 `@isaacs/nonrecursive-glob-match` 1.0.3 overrides 保留（上游鎖檔仍有 `minimatch` 10.2.5，落在 GHSA-g3hv-75wg-m249 範圍）；`@electron/asar` 的 `glob` 跟上游升到 14.0.4。`qs` 6.16.1 與 `vitepress.vite` 6.4.5 現在與上游相同，fork 端偏離消失。鎖檔新增 14 個套件，全部來自 `registry.npmjs.org`、沒有 install script；`npm audit` 為 0。    |
| `licenses/*`                                                                                                                             | `npm-dependencies.txt` 以產生器重產；`npm-runtime-notices.txt` 以上游為底，換入 fork 已驗證的 `zod@4.6.7`、`minimatch@11.0.1`、`@isaacs/nonrecursive-glob-match@1.0.3` 段落並更新指紋，`licenses:check` 通過。                                                                                                                                                                                                                 |
| 測試檔                                                                                                                                   | `FilesystemSnapshot.test.ts`（junction 建立 `EPERM` 略過）與 `binarySession.test.ts`（symlink／hard link 測試在 win32 略過）把 fork 的 Windows 略過疊回上游新版本；`setupEnvironment`、`cliJsonStdinCli`、`packageRunnerRegistration`、`claudeDesktopClientConfiguration` 上游已重寫或刪除對應案例，採上游；`readmeConsistency`、`test-website.py` 配合只留英文／繁中的語系政策調整（新增案例的 `zh-CN`／`ar` 改成 `zh-TW`）。 |

## 4. Workflow 與供應鏈審查

- `.github/` 在 6.8.0..6.10.1 間新增或修改的檔案：新增 `CODEOWNERS`、`actions/host-apt-packages`、`actions/ubuntu-archive`、`actions/windows-cross-compiler`、`codeql/production.yml`、`dependabot.yml`、`workflows/codeql.yml`，其餘為既有 workflow 修改。
  - fork 的 `github.repository == 'morluto/rea'` 守衛（`release.yml` 的 `merged-release`、`release-please`，`release-recovery.yml` 的 `verify`，`website-pages.yml` 的 `prepare`）在合併後仍在，由 `releaseWorkflow`／`releaseRecovery` 測試鎖住。
  - `.husky/pre-commit` 新增「merge commit 時略過 lint-staged」，只影響 merge；沒有新的網路目標。
- 判準八（藏在 diff 裡的內容）：掃描 6.8.0..6.10.1 的新增行（排除 locales、licenses、lock、`docs/readme`）：遠端腳本直管執行（`curl|bash`、`iwr|iex`）、破沙盒旗標（`--dangerously-*`、`bypassPermissions`、`--skip-permissions`）、提示注入句式、零寬／雙向控制字元、`base64 -d | sh`、`eval(fetch)`。
  - 唯一命中的 `curl … | bash` 是 `docs/getting-started/installation.md` 對上游自家 `install.sh` 的文件範例，6.8.0 的 `docs/installation.md` 已有同一行；`install.sh` 本身沒有變動。沒有破沙盒旗標、沒有遠端腳本直管執行的新增。
  - 零寬字元與「Ignore prior instructions…」命中的都是測試資料（BOM 測試、`promptMcp.test.ts` 的注入樣本）。
  - **沒有拒收項目。**
- Windows 原生模組：6.10.x 的 `scripts/run-exclusive*.mjs` 與 verifier fixture 在 Windows 上要載入 `native/windows/build/` 的原生模組。這個前提 6.8.0 就有：同步前的 fork `main`（`f61ce6301`）乾淨檢出跑 `npm run build:cached` 一樣因缺 `native/windows/build/manifest.json` 失敗，基準檢出改放 `npm pack rea-agents@6.8.0` 的檔案（SHA-256 `6a015bfe…`，與 manifest 一致）。本機依 `native/windows/README.md` 的手動復原步驟，從 `npm pack rea-agents@6.10.1`（registry 驗證完整性）取出 `manifest.json` 與 `rea-windows-x64.node`，核對 SHA-256 `801a9994a5ed…` 與 manifest 一致後放進被 Git 忽略的 `native/windows/build/`；fork 沒有改 `native/`，所以符合「檢出與已發布版本的原生契約相同」的前提。沒有執行任何 install script。

## 5. 採用／延後／拒收

- **採用**：6.9.0、6.10.0、6.10.1 的全部程式、文件與測試（淨樹），含 Ghidra 12.2、Kuna 提供者、RL 環境建置（`environment-build`）、Windows 捷徑／DWARF／NuGet／Deno 等新檢查、輸出 Schema 預設省略、setup 直接記錄執行環境、`TextFileWrite` 拆分、DOS MZ 於 Windows P0（#7144，隨同處理 issue #7121）。
- **取代 fork 修正（上游已有等效作法）**：zod 4.6 的 `omittableDefaults`／`offsetDateTime` 因應、`MacHopperPaths` 的 Windows home 連結、測試選擇檔案傳遞、`qs`／`vite` override。
- **延後**：
  - 其餘語系 README／網站語系（政策不變）。
  - Windows Ghidra `java_home.save`（issue #7075）：上游 #8889（`08a923f72`）在 6.10.1 內，改為回報受限主機的暫存寫入被拒；是否真的在 Windows 實機上排除，仍需維護者用 Ghidra 分析一個檔案確認（ROADMAP 保留該列）。
  - Node 26：`scripts/lib/verifier-source-loader.mjs` 現在先探測 transform 模式並在 Node 26 明確拒絕（#7839 系列；2026-11-24 以 Node 26.12.1 實跑得到「requires the Node.js version pinned in .nvmrc」）。ROADMAP 的 Node 26 列因觸發條件成立而刪除；本機驗證用 `.nvmrc` 的 Node 24.22.1。
- **拒收**：無。

## 6. PR／issue 軸

- 已合併的 PR 中，發布前合併者（2833 筆）經 commit 軸帶入；發布後才合併的 38 筆（number ≤ #12737）與未合併的 PR 留給下一個正式版本或「不採用」。
- 水位：`reviewed_pr_through` 12737、`reviewed_issue_through` 12920（檢查工具建議的上限，高於這兩個號碼會永久隱藏發布後才開的項目）。
- 範圍內 PR 4324 筆：發布前已合併 2833、已關閉未合併 1154、仍開放 299、發布後才合併 38。issue 1230 筆：已關閉 1010、仍開放 220。
- 只對 Windows／CJK 相關者逐筆看（標題比對 windows／win32／unicode／utf／powershell／drive-letter／symlink 等關鍵字，約 110 筆），**全部不採用**，原因與觸發條件：
  - 已關閉未合併的修正（NTFS／USN、Shell Link 路徑、桌面 ZIP UTF-8 名稱、PowerShell 文件、`registry hive`／Prefetch 提案等）：上游選擇另一條修正或已被取代；觸發條件是上游改合併後隨正式版本進來。
  - 仍開放：PR #10752（Ghidra 在 Windows 以 PATH 解析裸 `java`）、#10542（symlink 權限的測試略過）、#10617、#12642、#12683、#12690 與 issue #12641／#12681／#12687／#12689／#12697（Windows 上 POSIX 假設的測試失敗）、#8499（Windows JADX 橋 JVM 卡住）、#8312（Windows Chrome CDP 逾時）、#8700／#9182（Windows 原生自測 DACL）、#8410／#8298（Windows 上 ZIP 解壓與 JavaScript 分析慢）。沿用「不提前合併上游 WIP」；觸發條件是上游合併，或維護者在本機實際遇到同一問題。
  - 其餘約 1100 筆批次記為不採用，觸發條件同上。

## 7. 驗證

2026-11-24，Windows 11、Node 24.22.1（`.nvmrc`），本機三個檢出：同步前 fork `main`（`f61ce6301`，放 6.8.0 tarball 的原生模組）、同步結果、純上游 `rea-agents-6.10.1`（`8bb01b514`，放 6.10.1 的原生模組）。三者都 `npm ci --ignore-scripts`。

- 靜態：`build:cached`、`typecheck`、`lint`、`lint:typed`、`format:check`、`knip`、`knip:production`、`metadata:check`、`verify:architecture-guards`、`docs:check`（含 `readmeConsistency`）、`jscpd`、`scan:todos`、`licenses:check` 全部 exit 0；`npm audit` 0 筆。`format:check` 起初只差本 fork 的三份文件（`FORK.md`、`ROADMAP.md`、本紀錄），以 `oxfmt` 修正；同步前的 `main` 本來就因 `ROADMAP.md` 格式而讓 CI 的 Static checks 失敗（run 45179892772），這次一併修掉。
- Python（`scripts/run-python-tests.py`）：67 個測試 13 個錯誤，全是 POSIX 專用模組（`resource`、`os.mkfifo`）在 Windows 不存在；由 Linux CI 涵蓋。
- vitest：12 個 project 各自一批、每批新程序、每批 timeout 3600 秒。同步前 33551 個測試、847 個失敗。同步後 `boundary`、`acceptance` 兩批第一次逾時（未完成，不算失敗），只重跑這兩批（timeout 7200 秒，5780 秒與 4076 秒完成）；合計 55151 個測試、1614 個失敗。逐測試比對差集，不看總數：
  - 同步後失敗、同步前沒有或通過的測試分布在 186 個檔；把這些檔在純上游 6.10.1 檢出重跑（4151 個測試、1242 個失敗），只有 4 個是合併造成（上游通過、合併後失敗），已修正並單獨重跑通過，見 `docs/DECISIONS.md` 2026-11-23「同步後在 Windows 找到並修掉的 4 個回歸」。另有 `ProcessSamplingDescriptor` 1 個在負載下失敗、單獨重跑 3 次通過。
  - 其餘在純上游 6.10.1 同樣失敗：上游新增或改寫、寫死 POSIX 路徑語意、symlink 權限（`EPERM`）、Linux 專用工具（objdump、tshark、cgroup、apt）與負載下逾時；上游已說明一般原始碼測試不保證在 Windows 通過。
  - 同步前失敗、同步後通過：58 個。
- `python tools/check_upstream_updates.py --strict --ticket-cap 6000`：exit 0，PR 水位 #12737、issue 水位 #12920 之上沒有發布前的新項目（發布後的 1122 個 PR、272 個 issue 依 `ticket_cutoff` 延到下一個正式版本）。
- `python tools/check_dependency_freshness.py`：exit 0，0 筆待評估；`tools/test_check_dependency_freshness.py` 通過。
- 本機副作用：在 Windows 上跑 6.10.x 的 vitest 時，有測試以 `python3` 啟動子程序，觸發 Python install manager 在檢出根目錄裝出約 167 MB 的 `Python/`（同步結果與純上游檢出都出現，6.8.0 沒有）。它不在 `.gitignore`，跑完要刪掉，不要提交；前一次未完成的同步嘗試曾把它誤提交進本機暫存 commit。
- 未涵蓋：macOS（darwin 的 `settledLivePids` 只在 CI darwin lane 驗證）、Windows 實機 Ghidra 分析（ROADMAP 保留）、`website.py check` 的分享圖產生（本機缺 `cairosvg`）。
