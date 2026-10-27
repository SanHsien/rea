# 上游同步評估與決策紀錄（2026-10-27，`rea-agents-6.8.0`）

## 1. 範圍

- 上游：[`morluto/rea`](https://github.com/morluto/rea) `main`。
- 前次水位：`988494abdbb27fb91ca6bd80362c9f1a332f86c3`（`rea-agents-6.5.0` 之後，2026-10-17）。
- 本次目標：上游最新正式版本 `rea-agents-6.8.0`（tag commit `160d821ac9a0310afcb8d1fc427862dd6508add5`，2026-10-25 發布）。
  - 不追 `main` 尖端：同步當下 `main` 已在 tag 之後再前進 534 個 commit，且一天多次變動；正式版本是上游自己驗過的穩定點。
- 量體：`988494a..rea-agents-6.8.0` 共 1914 個 commit；水位以上、發布前開出的 PR 1017 筆（其中 474 筆已合併）、issue 1321 筆。

## 2. 作法：以 release 為單位的淨樹同步（PLAYBOOK §5 的有記錄例外）

本 fork 歷史已壓縮，與上游沒有共同祖先，PLAYBOOK §5 原則上改「逐項移植」。這次量體逐項移植不可行，因此：

1. 建立只在本機使用、從未推送的合成 commit：以 `988494a` 為父、樹等於 fork `main`，讓 Git 能以 `988494a` 當合併基底做三方合併。
2. 將 `rea-agents-6.8.0` 合併進合成 commit，逐一解衝突。
3. 把合併結果的「樹」以**單一 commit** 接在 fork `main` 之上，不把上游 1914 個 commit 的歷史帶進 fork。

之後一律以上游正式版本為粒度追蹤（`tools/upstream_baseline.json` 的 `track: release`）。

## 3. 衝突處理

| 類別                                                               | 處理                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `README.md`（繁中）、`README.en.md`、`docs/readme/README_zh-TW.md` | 保留 fork 的語系列、Fork 說明與「不宣傳上游」原則（去掉 Star 歷史、Discord、Trendshift）；上游新增段落（精簡輸入 Schema、`rea --update`、更新命令輸出上限、Node.js 新下限、Linux `ps` 前提、啟動期限變數、可分析目標表新增列、案例圖改 SVG）全部帶入並翻成繁體中文，包含上游 zh-TW 版仍是英文的表格列。 |
| 語系                                                               | 照舊只留英文與繁中：刪除上游新增與既有的其他語系 README 與 `website/locales/*`，`languages.json` 維持兩種語言，`website.py sync` 與 `translations extract` 重產。                                                                                                                                       |
| `src/application/LinuxHopper.ts`、`MacHopper.ts`                   | 上游已改為一律 `posix.join`（與 fork 修正目的相同），採上游。                                                                                                                                                                                                                                           |
| `src/application/MacHopperPaths.ts`                                | 上游一律 `posix.join`；疊回 fork 的 `joinFor`（Windows home 路徑用 `win32.join`），否則 Windows 上 `hopperLauncherSelection` 測試回歸。                                                                                                                                                                 |
| `src/ghidra/GhidraInstallation.ts`                                 | 合併兩邊：上游新增「沒有選定安裝就不探測 Java」，fork 保留「Windows 磁碟機代號的 `JAVA_HOME` 在任何主機都算絕對路徑」。                                                                                                                                                                                 |
| 測試檔                                                             | 上游已自行修掉的 Windows 測試差異採上游；`src/electron/ElectronFuseProvider.test.ts` 補回 fork 對建 symlink 測試的 `skipIf(win32)`（Windows 建 symlink 需權限，合併時被上游版本蓋掉）。                                                                                                                 |
| `package.json`／`package-lock.json`                                | 採上游鎖檔，再補回 fork 的 `zod` 4.6.7 與 `fast-uri` 3.1.9（2026-10-24 安全修補）；`vite` 上游已是 8.3.5。                                                                                                                                                                                              |
| 產生檔                                                             | `docs/error-contract.schema.json`、`licenses/npm-dependencies.txt` 以產生器重產；`licenses/npm-runtime-notices.txt` 以上游版本為底，換入 fork 已驗證的 `fast-uri@3.1.9`、`zod@4.6.7` 段落並更新指紋，`licenses:check` 通過。                                                                            |

## 4. Workflow 與供應鏈審查

- `.github/` 新增或修改約 119 個檔。會在 fork 上發佈、推送或使用 secrets 的路徑：
  - `release.yml`：`release-proposal` 先前已有守衛；這次在發佈鏈的兩個根 job `merged-release`、`release-please` 加上 `github.repository == 'morluto/rea'`（`qualification`、`rehearsal`、`publish`、`verify-npm`、`publish-mcp` 都依賴這兩個 job，跟著不會執行）。
  - `release-recovery.yml`：`verify`（`publish-mcp` 依賴它，會用 OIDC 發佈 MCP Registry）加守衛。
  - `website-pages.yml`：`prepare`（`deploy` 依賴它，用 Cloudflare secrets 部署 rea.tools）加守衛。
  - 其餘：`pr-readiness.yml` 是 `pull_request_target`，只檢出預設分支、權限只有 `statuses: write`，不執行 PR 程式；`cache-retention.yml` 的 `actions: write` 只清本 repo 快取；`real-*` 與 `ci.yml` 用的 `TURBO_TOKEN` 在 fork 沒有設定，為空值。這些維持上游原樣。
- 新依賴：`@bufbuild/protobuf`、`@msgpack/msgpack`（runtime），`oxlint-tsgolint`、`release-please`、`tsrs`（dev）；鎖檔新增 196 個條目，全部來自 `registry.npmjs.org`，沒有新的 install script。
- `scripts/prepare.mjs` 新增：開發安裝時以 `git apply` 套用 repo 內的 `patches/release-please+17.3.0.patch`（先檢查版本必須是 17.3.0；修改 `release-please` 的 GraphQL 暫時錯誤重試、單一 Node 專案略過檔案清單查詢、發佈歷史不完整時拒絕產生提案，沒有新的網路目標或程式執行）；husky 仍可用 `HUSKY=0` 關閉。`.husky/` 沒有變動。
- `scripts/ci/prepare-npm-publication.mjs`：只驗證已合格的封裝與 npm 現況、寫 `GITHUB_OUTPUT`，本身不發佈；所在的 `publish` job 已被上面的守衛擋住。
- 判準八（藏在 diff 裡的內容）：掃描 1914 個 commit 的新增行——大段空白後接程式、零寬或雙向控制字元、長 base64、設定檔裡的 `eval`／`child_process`。命中的都是 Markdown 表格對齊、工具契約說明字串、測試資料（APK 簽章、pyc）與兩個刻意測 BOM 的測試，沒有可疑內容。

## 5. PR／issue 軸

- 已合併的 PR（474 筆）經 commit 軸帶入。
- 水位：PR 推進到 `#7097`、issue 推進到 `#7095`（`rea-agents-6.8.0` 發布前開出的最大號碼）。發布之後開出的項目留給下一個正式版本一起看（檢查工具的 release 截止日）。
- 未合併 PR 與 issue 只對 Windows／CJK 相關的逐筆看；其餘約 1770 筆批次記為「不採用」，觸發條件：上游合併並發布後隨正式版本進來，或維護者在本機實際遇到該問題。
- 需要注意的開放項目：
  - issue #7075（Windows：Ghidra LaunchSupport 寫不進 `java_home.save`）：上游維護者在 Windows 11、6.7.0 與 6.8.0 都重現不出來，尚無修正。**不採用**；觸發條件：上游合併修正，或本機 `rea doctor` 全綠但 Ghidra 啟動出現同樣錯誤。
  - issue #7121（Windows Ghidra 拒絕 DOS MZ）：發布後才開，上游 draft #7144 處理中，留到下一個正式版本。
  - issue #5811／PR #6347（Windows 上 `rea mcp add` 出現 `spawn npx ENOENT`）：上游仍開放。**不採用**；替代作法是 `rea setup --client`；觸發條件：上游合併。
  - PR #5317（`cmd.exe /s /c` 批次啟動器引號）、PR #6410（兩個 Windows 失敗測試）、PR #6326（Windows live 工具）、PR #5391（Windows 調查 app）：上游未合併，不提前移植（沿用 2026-10-16「不合併上游 WIP」決定）。
- **提前帶入一個發布後的上游修正**：`4557791a2`（PR #7152，關閉 #7151，已合併到上游 `main`）。6.8.0 的 `src/domain/localPath.ts` 在 Windows 主機公告的絕對路徑 pattern 含未跳脫的 `/`，用 `v` 旗標編譯 pattern 的 MCP 客戶端會拒收整份工具清單；fork 以 Windows 為主要平台，所以先套用這個兩檔的修正（Windows 上 `tests/boundary/mcp/advertisedPatternsVMode.test.ts` 由失敗轉通過）。下一個正式版本會包含它。

### Windows／CJK 相關未合併 PR（35 筆）

| #     | 狀態   | 標題                                                                                             |
| ----- | ------ | ------------------------------------------------------------------------------------------------ |
| #4738 | CLOSED | fix(apktool): disclose locale tables that carry other qualifiers                                 |
| #4758 | CLOSED | docs(i18n): add Telugu README translation                                                        |
| #4780 | OPEN   | test(install): pin the C locale for the truncated installer check                                |
| #4864 | OPEN   | docs(windows-ghidra): record a large PE that exceeds the default startup budget                  |
| #4918 | CLOSED | fix(apktool): select three-digit regions through the b+ locale table                             |
| #4971 | OPEN   | docs(i18n): add Azerbaijani README and sync Turkish edition                                      |
| #4988 | OPEN   | ci(windows): run the caller path separator regression in the Windows lane                        |
| #5023 | OPEN   | feat(kuna): admit Windows PE images through the verified provider lane                           |
| #5039 | OPEN   | docs(windows): clarify native artifact restore and cleanup in source …                           |
| #5127 | CLOSED | fix(artifacts): preserve original Unicode spelling when NFC normalization changes a logical path |
| #5204 | CLOSED | fix(android): select Windows JADX java.exe from PATH, not the working directory                  |
| #5208 | CLOSED | fix(cli): clamp failure token windows past the available range                                   |
| #5213 | OPEN   | test(mcp): normalize server identity fixture paths on Windows                                    |
| #5231 | CLOSED | fix(cli): clamp exhausted failure token windows                                                  |
| #5276 | OPEN   | docs: add Urdu README translation                                                                |
| #5305 | CLOSED | docs: add WSL2 fallback hint for ELF targets on Windows Ghidra P0 (#5243)                        |
| #5317 | OPEN   | fix: correct cmd.exe /s /c argument quoting for Windows batch launchers                          |
| #5321 | CLOSED | fix(artifacts): note legacy code page readings of unflagged ZIP names                            |
| #5391 | OPEN   | feat(desktop): add Windows investigation app                                                     |
| #5669 | OPEN   | test: cover Unicode code point ordering                                                          |
| #6124 | OPEN   | fix(ghidra): point Windows ELF rejection to WSL2 fallback                                        |
| #6129 | CLOSED | fix(javascript): preserve unavailable source coverage for invalid UTF-8                          |
| #6266 | CLOSED | fix(ci): avoid utility loading in the Windows ACL observer                                       |
| #6322 | CLOSED | docs: state that the general source suite is not expected to pass on Windows                     |
| #6326 | OPEN   | feat(windows): admit live SQLite, process, and window tools                                      |
| #6346 | CLOSED | fix(hooks): add a sh shebang so husky hooks run from Git Bash on Windows                         |
| #6347 | OPEN   | fix(cli): delegate rea mcp add to setup --client on Windows (#5811)                              |
| #6348 | CLOSED | fix(windows): type missing process-control refusals as capability_unavailable (#6050)            |
| #6410 | OPEN   | fix(tests): make two Windows-failing tests pass and give the Ghidra transport one owner          |
| #6429 | CLOSED | fix(mcp): publish portable Windows absolute path patterns                                        |
| #6685 | OPEN   | test(search): cover Unicode literal syntax and astral case folding                               |
| #6742 | CLOSED | fix(signals): retain Unicode literal matches across sigma word positions (#6714)                 |
| #6782 | OPEN   | docs(contributing): document restoring the Windows native addon from the verified npm tarball    |
| #6905 | CLOSED | fix(environment)!: keep unsupported HAR body encodings opaque                                    |
| #6906 | CLOSED | fix(analysis): treat unsupported HAR body encodings as unavailable text (#6889)                  |

### Windows／CJK 相關issue（61 筆）

| #     | 狀態   | 標題                                                                                                                                                   |
| ----- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| #4707 | CLOSED | [Bug] Windows: rea analyze rejects backslash absolute paths with "Ambiguous Windows path component is unsupported" (Win32 50)                          |
| #4777 | CLOSED | [Feature] Share one APK resource decode across selected locale-table reads                                                                             |
| #4815 | OPEN   | Windows lab findings: 14 tool-level gaps with proposed fixes (AI-authored, verification documented)                                                    |
| #4817 | CLOSED | [Bug] Apktool locale limit rejects script-region-variant table names                                                                                   |
| #4818 | CLOSED | [Bug] Apktool advisory context omits the Windows follow-up and 3.x regression                                                                          |
| #4874 | CLOSED | [Bug] Shared APK locale projection forgets observed counts for a skipped alias                                                                         |
| #4876 | CLOSED | [Bug] APK CLI locale-list schema omits the domain array bounds                                                                                         |
| #4880 | CLOSED | [Bug] Later APK locale read failure discards completed decode facts                                                                                    |
| #4883 | CLOSED | [Bug] Windows: `rea --update` fails with `spawn npm ENOENT` because the bundled incur updater cannot launch `npm.cmd`                                  |
| #4982 | CLOSED | [Feature] Offer table-only Apktool string projection for locale queries                                                                                |
| #4989 | CLOSED | [Bug] Windows update command surface test intermittently exceeds its deadline                                                                          |
| #5055 | CLOSED | [Bug] LLDB structured readback reports replacement-decoded malformed UTF-8 as facts                                                                    |
| #5091 | CLOSED | [Bug] Rizin recent output retains three times its UTF-8 byte budget for CJK frames                                                                     |
| #5096 | CLOSED | [Bug] Windows JADX selects a current-directory java.exe before the selected PATH JDK                                                                   |
| #5104 | CLOSED | [Bug] Empty APPDATA makes Windows client registration write into the working directory                                                                 |
| #5108 | CLOSED | [Bug] inspect-artifact loses original decomposed Unicode member names                                                                                  |
| #5110 | CLOSED | [Bug] Exhausted CLI failure token windows display a reversed range                                                                                     |
| #5185 | OPEN   | Feature Request: Support Analysis of MQL5 `.ex5` Expert Advisors Loaded by `terminal64.exe`                                                            |
| #5225 | OPEN   | [Windows x64] rea inspect --provider ghidra fails snapshot admission with Win32 5 (EACCES) in an AppContainer process; succeeds from an ordinary shell |
| #5237 | OPEN   | [Windows native] Private DACL contains unexpected trustees (Win32 5) blocks Android inspection before JADX                                             |
| #5242 | CLOSED | [Bug] Rizin recent-output retains up to 3x its UTF-8 byte budget for CJK frames                                                                        |
| #5243 | OPEN   | Windows Ghidra P0: no path for ELF/arm64 targets (e.g. Android libapp.so)                                                                              |
| #5259 | CLOSED | REA 6.7.0 fails to start on Windows: ERR_MODULE_NOT_FOUND for MCP client index.mjs                                                                     |
| #5320 | CLOSED | [Bug] inspect-artifact reports CP949 ZIP member names only as CP437 text, with no limitation                                                           |
| #5503 | CLOSED | [Bug] trace_feature drops Hopper string encoding and termination qualifications                                                                        |
| #5530 | CLOSED | [Bug] CLI token windows duplicate digest characters and corrupt emoji                                                                                  |
| #5553 | CLOSED | [Bug] analyze_swift_types misclassifies nested Unicode types and hides class results                                                                   |
| #5657 | OPEN   | [Design] Classic console ROM targets on Windows (raw image with an installed Ghidra language, or a named Ghidra loader)                                |
| #5702 | CLOSED | [Bug] inspect-plist rewrites Unicode separators as LF when XML fallback is used                                                                        |
| #5723 | CLOSED | [Bug] Windows native module rea-windows-x64.node blocked by Smart App Control                                                                          |
| #5811 | OPEN   | [Bug] `rea mcp add` fails on Windows with `spawn npx ENOENT`                                                                                           |
| #5951 | CLOSED | [Bug] Invalid-UTF-8 HTML omits its unavailable reference-parsing scope                                                                                 |
| #5995 | CLOSED | [Bug] Invalid-UTF-8 JavaScript is omitted from semantic unavailable-source coverage                                                                    |
| #6050 | CLOSED | [Bug] Missing Windows worker controls surface as execution_failure instead of capability_unavailable                                                   |
| #6197 | OPEN   | Ghidra provider ignores adjacent PDB companions for Windows PE targets (no symbol names without manual workaround)                                     |
| #6275 | CLOSED | [Bug] Windows native verifier's private-runtime ACL observer times out in powershell.exe                                                               |
| #6308 | CLOSED | [Docs] Windows source checkouts: say the general source suite is not expected to pass on Windows                                                       |
| #6439 | CLOSED | [Bug] inspect-apk-signature loses v1 signer identity when issuer string encoding changes                                                               |
| #6463 | CLOSED | [Docs] Unblob submodule checkout fails on Windows with `invalid path`                                                                                  |
| #6476 | CLOSED | [Bug] inspect-python-pyc splits a valid Unicode scalar in a constant preview                                                                           |
| #6503 | CLOSED | [Bug] BEAM inspection rejects an extended compact atom-length encoding                                                                                 |
| #6584 | CLOSED | [Bug] ADB package inspection stops counting permissions at a valid Unicode name                                                                        |
| #6593 | CLOSED | [Bug] Pyc code-name equality merges distinct Unicode names and drops a code object                                                                     |
| #6601 | CLOSED | [Bug] Firmware extraction returns nonexistent paths for decomposed Unicode filenames                                                                   |
| #6647 | CLOSED | [Bug] ELF export inventory renders UTF-8 names as Latin-1 without encoding metadata                                                                    |
| #6676 | CLOSED | [Bug] PYZ inventory leaves valid interned Unicode module names opaque                                                                                  |
| #6693 | CLOSED | [Bug] Sigrok Evidence silently replaces invalid UTF-8 and loses encoding warnings                                                                      |
| #6736 | CLOSED | [Bug] PyInstaller inventory collapses distinct POSIX backslash and slash paths                                                                         |
| #6743 | CLOSED | [Bug] Firmware staging inventory silently omits non-UTF-8 filenames                                                                                    |
| #6745 | CLOSED | [Bug] ELF export inventory corrupts UTF-8 symbol version names                                                                                         |
| #6765 | CLOSED | [Bug] Historical-source symlink targets alias replacement-character filenames after lossy UTF-8 decoding                                               |
| #6775 | CLOSED | [Bug] Pcap summaries silently replace malformed UTF-8 and report complete Evidence                                                                     |
| #6795 | CLOSED | [Bug] SQLite selected-table metadata aliases distinct names after UTF-8 replacement decoding                                                           |
| #6801 | CLOSED | [Bug] Objective-C++ property type encodings are split at template argument commas                                                                      |
| #6825 | CLOSED | [Bug] Apple bundle scans report complete coverage after skipping non-UTF-8 filenames                                                                   |
| #6836 | CLOSED | [Bug] Automatic protobuf decoding ignores illegal MIME encoding and version parameters                                                                 |
| #6889 | CLOSED | [Bug] Unsupported HAR body encodings are treated as decoded response text                                                                              |
| #6926 | CLOSED | [Bug] Explicit P/Invoke charsets add Windows suffix candidates for ELF imports                                                                         |
| #6956 | CLOSED | [Bug] trace_dylib_resolution can resolve candidates outside the analyzed root on Windows                                                               |
| #7050 | CLOSED | [Bug] npm ci fails on Windows: release-please patch step passes a backslash path to git apply --directory                                              |
| #7075 | OPEN   | Windows: Ghidra provider fails to start - LaunchSupport cannot write java_home.save (access denied)                                                    |

## 6. 驗證

Windows 11、Node 24.22.1（`.nvmrc`），本機：

- `npm ci --ignore-scripts`、build、typecheck、lint、`lint:typed`、format check、knip、`knip:production`、architecture guards、`metadata:check`、`mcp-catalog:check:built`、`docs:check:built`（含 `licenses:check`、error schema）全部通過。`website.py check` 在本機缺 `cairosvg`（原生 Cairo）而無法產生分享圖，由 CI 的 website-check 涵蓋。
- vitest：同步前 `main` 一次完整執行為基準（17658 個測試、532 個失敗）；同步後分 11 批、每批新程序執行（約 31700 個測試），逐測試比對差集，不看總數：
  - 同步造成的回歸已修正並重跑通過：`ElectronFuseProvider.test.ts` symlink 測試的 Windows 略過、`MacHopperPaths.ts` 的 Windows home 路徑、`releaseWorkflow`／`releaseRecovery` 測試對 fork 守衛的期待、`advertisedPatternsVMode`（#7152）。
  - 負載下逾時、單獨重跑通過：MCP 邊界 9 個、acceptance 3 個、`browserScenarioCleanup` 1 個。
  - 仍失敗、非 fork 造成（不修，避免日後合併衝突）：`flutterBuildProvider` 7 個與 `clientRegistrationStatus` 1 個是上游新斷言寫死 POSIX 路徑；`cliSetup` 2 個是上游新加的 MSIX 偵測訊息（測試在 MSIX 套件的應用程式底下執行時觸發）；`packageRunnerRegistration` 1 個是上游 `doctor` 在 Windows 經 npx 查核超過 20 秒期限（同步前 3.6 秒）。
  - 上游新增、在 Windows 失敗的測試 332 個（最多為 `ghidraClient`、`packedBridgeVerification`）；上游 #6308 已說明一般原始碼測試不保證在 Windows 通過。
- `python tools/check_upstream_updates.py --strict --ticket-cap 3000`：exit 0（發布後開出的 215 個 PR、193 個 issue 依 `ticket_cutoff` 延到下一個正式版本）。
