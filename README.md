# HAAC AI Assurance Framework

## Different safety rules. A shared way to verify and authorize execution.

**Public Working Draft v0.3.0 · Optional API connector v0.1.0 · 2026-11-03 · AI Assurance Inc.**  
[English](#english) · [日本語](#日本語) · [共通要求 / Framework](FRAMEWORK.md) · [試験 / Conformance](CONFORMANCE.md) · [Lean model](PolicyKernel.lean)

English-first presentation; Japanese remains the normative draft text. Core requirements, fixtures and existing code are unchanged by the API add-on.

## English

### Shared assurance, not identical policy

**Safety rules may differ. The procedure for verifying them and authorizing a specific operation can be shared.** This framework preserves each party's rules, interpretation, version, evidence and individual result instead of forcing a common safety threshold or a common verdict.

In a synthetic example, A accepts 2–8°C while B accepts 2–6°C. At 7°C, A is satisfied and B is not. Both results are reproducible. An operation requiring both parties is withheld; at 5°C with valid approval and authority, it proceeds. A separately approved A-only operation has its own scope. An A-only permission must not authorize an A+B operation.

The same procedure covers structurally different rules: a cyber operator's impact limit and another party's permitted environment and required approval count. Unknown requirements are not silently satisfied. Required parties cannot be removed after a grant. Conflicting policies are not averaged, voted away or replaced by the most permissive rule.

This supports agreement about **how a decision was justified**, not a mathematical guarantee of agreement about values. Authorized people determine applicability, interpretation and acceptable evidence. The framework does not prove that their choices are legitimate or complete.

### A concrete example

These are synthetic rules, not actual pharmaceutical standards or legislation.

| The same verification procedure | A's result | B's result | Operation requiring both |
|---|---|---|---|
| A permits 2–8°C, B permits 2–6°C; observation is 7°C | Satisfied | Violated | Block; retain both results |
| The same rules at 5°C, with approval and authority | Satisfied | Satisfied | Execute the specified mock action once |
| Temperature evidence is absent | Unknown | Unknown | Hold; identify missing evidence |
| Cyber impact limit passes, but B's environment/approval-count conditions fail | Satisfied | Violated | Block using the same framework |
| Required party B is removed after a permit is issued | Retain original result | Retain original result | Reject reuse of the old permit |

### Run the existing core

Python **3.11+**, standard library only. The ordinary core tests need no API key, external model, Docker or production data and make no external network calls. Toolchain installation and hosted CI preparation need network access.

```console
python assurance.py policies
python assurance.py test --output ../haac-run-v03
python verify.py ../haac-run-v03/policy-evidence.json --sha256-file ../haac-run-v03/policy-evidence.sha256 --mutations
python verify.py ../haac-run-v03/evidence.json --sha256-file ../haac-run-v03/evidence.sha256 --mutations

# Requires an installed Lean 4.19.0; missing tools are errors, never success
python assurance.py formal
```

Normal `test` does not invoke Lean. Use `formal` or `test --require-lean` explicitly. Choose a new output directory; old output is not overwritten. On Windows, substitute `py -3` when appropriate.

### Formal grounding and checked results

The common mathematical rule is conditional: **if each declared domain checker is sound**, joint authorization requires all mandatory conditions, valid approval, active authority and matching binding. It preserves individual verdicts instead of hiding disagreement in one aggregate label. It does not prove domain truth, correct policy interpretation or universal agreement.

The baseline core's [GitHub Actions run](https://github.com/GhostDriftTheory/verifiable-ai-assurance-framework/actions/runs/41570646962) at commit `e1ab350` succeeded on 2026-11-03: four Ubuntu/Windows × Python 3.11/3.13 jobs and a formal job. The latter checked 22 theorem declarations with Lean 4.19.0, 1,089 concrete correspondence obligations and rejection of three false claims. **This is baseline-core evidence, not hosted CI or formal proof of the optional API connector.**

| Check category | Recorded core result | Scope |
|---|---|---|
| Differing-policy cases | 30 cases | Thresholds, uses, approvals, missing evidence, versions and binding |
| Retained execution cases | 82 cases | 41 cases × mock notification/configuration |
| Faulty controls | 6 new + 10 retained detected | Includes any-one-party authorization, missing approval and always-stop |
| Record mutations | 18 new + 21 retained rejected | Scope, verdict, effect, audit and false assurance claims |
| Separately written Python evaluators | 968 + 150 inputs agree | Finite abstract and typed-boundary checks, not general proofs |
| Structural invariants | 605 checks | A bounded finite range |
| External reproduction / independently authored interoperability | Not performed | Same-author separate programs are not organizational independence |

Do not sum those categories into a safety percentage. Effects occur in a subprocess and local SQLite; the independent policy verifier does not import the executor. The Lean model does not prove the entire Python program, database, cryptography, external devices or natural-language interpretation.

### Eight core files plus one optional connector

| File | Purpose |
|---|---|
| `README.md` | Purpose, examples, operation, results and limits |
| `FRAMEWORK.md` | Twelve requirements, policy connection and assurance boundaries |
| `CONFORMANCE.md` | Twenty-four topics, 41 retained fixtures, 30 policy fixtures and acceptance criteria |
| `assurance.py` | Existing execution target, subprocess experiments and formal-check command |
| `verify.py` | Existing independently implemented policy/effect checks |
| `PolicyKernel.lean` | Twenty-two declarations checked in the baseline CI |
| `lean-toolchain` | Pinned Lean version |
| `.github/workflows/verify.yml` | Existing core-only CI and formal checks |
| `openai_api_experiment.py` | Optional API/offline experiment and saved-record verification |

Only the three Markdown files and the new Python file change in this update. Existing Python, Lean, toolchain and workflow files stay unchanged. The workflow does **not** automatically test the add-on or make paid calls; run its `self-test` separately.

### Optional OpenAI API experiment — one additional Python file

`openai_api_experiment.py` connects a **real model proposal** to the existing, unchanged local execution gate. It does not give the model permission to rewrite evidence, policies, mandatory participants, approval or authority. The model chooses `REQUEST_EXECUTION` or `HOLD` and returns the exact supplied operation. A changed target, payload, identity or version is rejected by the adapter rather than silently replaced with the expected operation.

**This is an optional bounded integration experiment, not a new safety standard.** It reuses ten existing policy fixtures: P01, P02, P03, P11, P12, P14, P15, P18, P19 and P30. The last three contain declared post-grant changes/time advancement performed by the test harness, not invented by the model. The model is shown the initial context, not the expected answer or future fault injection.

Python 3.11+ and its standard library are sufficient; **no SDK, additional dependency file or API schema file is needed**. Run from the repository directory:

```console
# No key, no network: parsing/binding tests, mock transport, real local effects and replay
python openai_api_experiment.py self-test

# Deliberately request every candidate using synthetic inputs — NOT OpenAI results
python openai_api_experiment.py offline --output ../haac-api-offline

# Recheck these saved records with the existing independent policy verifier
python openai_api_experiment.py verify ../haac-api-offline/api-evidence.json --sha256-file ../haac-api-offline/api-evidence.sha256 --mutations

# Two paid calls as an initial connection check; replace YOUR_MODEL_ID
python openai_api_experiment.py live --model YOUR_MODEL_ID --cases P01,P02 --max-requests 2 --output ../haac-api-live

# Recheck the saved API experiment without calling the model again
python openai_api_experiment.py verify ../haac-api-live/api-evidence.json --sha256-file ../haac-api-live/api-evidence.sha256
```

Choose a model available to your API account that supports Responses and strict Structured Outputs. Set `OPENAI_API_KEY` locally, or enter it at the hidden terminal prompt when `live` starts; the key is never saved in experiment files. `OPENAI_MODEL` can replace `--model`. On Windows, use `py -3` in place of `python` as needed. Do not paste a key into GitHub or this repository.

`live` is the only command that makes API calls. It uses the official Responses endpoint, `text.format` with a strict JSON schema, no tools and `store=false`; that setting is **not** a promise of zero retention of all provider logs.[API1–API3] Only built-in synthetic contexts are sent. The connector rejects redirects and does not use environment proxy/base-URL overrides. Paid calls are limited before starting: the default is ten cases × one repetition, with `--max-requests 10`; there are no retries, automatic model substitutions or synthetic fallbacks. A request limit and `--max-output-tokens` are not a fixed monetary budget. `--reasoning-effort` is optional and must be supported by the chosen model; increase `--max-output-tokens` explicitly if needed rather than treating an incomplete response as valid.

The **same accepted proposal** is compared on two isolated local SQLite targets: an intentionally permissive control that acts on the proposal without checking policy, and the existing HAAC gate. This control is not OpenAI's default behavior or a representative competing product. Model HOLDs/refusals and API errors are recorded without dispatching either target. If the model produces no prohibited request, the run reports zero such requests tested—not a fabricated interception rate. The adapter is a single-candidate execute/hold experiment, not an unrestricted agent planner or production API gateway.

`api-evidence.json` retains the request, model response ID and returned model name, assistant output, token usage when provided, dispatch decision, fixture digest, and observed local effects. Reasoning output items and credentials are not saved. `journal.jsonl` preserves responses and observations as the run proceeds; an interrupted journal is not a complete experiment. `api-report.json` and a SHA-256 sidecar summarize the run. **Outputs must go in a new directory outside the repository.** Review generated text before sharing it.

The `verify` command re-parses the saved response, checks scope and provenance labels, and delegates gate/observation recomputation to unchanged `verify.py` in a fresh process that does not import `assurance.py`. Common adapter parsing is shared code, not a separately authored adapter. The nine-file manifest includes the added script; the original core evidence formats retain their original eight-file manifests. Use this wrapper command for `api-evidence.json`; the legacy `verify.py` CLI expects the original core formats.

**Verified here:** ten offline scenarios, 21 response/scope checks, four non-dispatch integration cases, six mocked transport checks, two mocked-envelope checks and 14 evidence mutations. **Not performed here:** live OpenAI calls or hosted CI for this add-on. Mocked responses are not API experiments. Live transcripts remain self-recorded—not cryptographically authenticated by OpenAI—and a co-generated digest alone cannot prevent coordinated replacement. A successful replay verifies declared record consistency, not provider identity, real-world truth, all-model behavior or an extension of the Lean proof to the API.

### Read the claims correctly

`CONSISTENT_REFERENCE` means the declared synthetic profile's record agrees with its rules and supplied digest. It is not HAAP wire interoperability, issuer authentication, proof of real-world observations or regulatory certification. Without an anchor the original verifier reports `CONSISTENT_UNANCHORED` and exits 2. A co-generated digest is only a local baseline; a separately obtained digest improves integrity checking but is still not proof of identity or truth.

Whole-framework conformance, reference-test success and abstract formal verification are different claims. Signatures, trust anchors, actual organizational authority, complete production enforcement paths, independent observers and legitimate policy interpretation need additional review.

### Scope, rights and stewardship


This is a public working draft issued by AI Assurance Inc. for HAAC discussion, not an adopted Council standard, a government endorsement or third-party certification. No proprietary implementation or named policy language is required. HAAP's public overview is the semantic reference, not an established wire-compatibility claim.

The draft remains source-available **without an OSS license**; reuse, redistribution, commercial integration and patent terms require the rights holder's determination. No new rights grant is made by this revision. Production secrets and proprietary engines are not included. Japanese is the normative draft text. Report discrepancies, retain versioned evidence, and distinguish policy-owner approval from technical review.

**Documentation/API update:** English precedes Japanese, but Japanese remains normative. The existing R/T/P requirements, machine-readable fixtures and rights policy are preserved. Markdown changes also change source hashes: verify archived evidence with its generating commit; regenerate evidence when using this updated checkout. No proof result is silently transferred to the API connector.

## 日本語

**安全基準は異なっていても、検証と実行許可の仕組みは共通化できる。**

### このフレームワークの中心

国、企業、業界でAI安全性の基準が違っていても、**どの基準を適用し、何を根拠に判断し、誰が実行を許可し、実際に何が起きたか**を、共通の方法で確かめられるようにします。

目指すのは**安全基準の一本化ではなく、異なる基準を尊重したまま運用できる、検証の共通ルール**です。全員が同じ結論になる必要はありません。同じルールと同じ証拠に対する結果を再現でき、異なる結果の理由を当事者と第三者が確かめられることを重視します。

そのために、条件の検証、組織としての採用、操作の許可、実際の作用を分離します。**AIの提案と実行を分けることは、この共通ルールを現場で機能させる仕組みです。**

### 30秒で分かる例

以下は説明用の合成条件です。実在する医薬品の品質基準や各国の法令ではありません。

| 同じ手順で確認する場面 | Aのルールによる結果 | Bのルールによる結果 | A・Bの両方が必要な共同操作 |
|---|---|---|---|
| Aは2～8℃、Bは2～6℃。観測値は7℃ | 適合 | 不適合 | **実行しない。違いを記録する** |
| 同じルールで観測値は5℃。承認と権限も成立 | 適合 | 適合 | **指定操作を1回実行する** |
| 温度記録がない | 判定不能 | 判定不能 | **保留し、必要な証拠を示す** |
| 設定変更：Aの影響度条件は満たすが、Bの用途制限と承認数を満たさない | 適合 | 不適合 | **同じ仕組みで実行を止める** |
| 許可後にBの条件を削除する | 元の判定を保持 | 元の判定を保持 | **許可の流用を拒否する** |

Aだけを対象とする別の操作は、適正な範囲設定と承認の下で別途許可できます。世界中の基準を一律に重ねる設計でも、緩い基準を選んで共同操作を通す設計でもありません。

**基準の妥当性や、どの当事者を必須にするかは、権限を持つ主体が決めます。数学が価値判断を一致させたり、全員の納得を保証したりするという主張ではありません。**

### 動かして確認する

Python **3.11以上、標準ライブラリのみ**。APIキー、外部AI、Docker、本番データは不要です。通常のPython試験は外部通信を行いません。Python・Lean等の初回導入とGitHub Actionsの環境準備には通信が必要です。

```console
# まず核心を見る：同じ証拠、異なるルール、共同操作の可否
python assurance.py policies

# 全試験、誤実装対照、改変検査。新しい出力先を指定
python assurance.py test --output ../haac-run-v03

# 実行側の判定関数を使わない別検証器で再確認
python verify.py ../haac-run-v03/policy-evidence.json --sha256-file ../haac-run-v03/policy-evidence.sha256 --mutations
python verify.py ../haac-run-v03/evidence.json --sha256-file ../haac-run-v03/evidence.sha256 --mutations
```

通常の`test`ではLeanを自動起動せず、形式検査は`formal`または`--require-lean`で明示して実行します。

Windowsで`python`が使えない場合は`py -3`に置き換えます。出力先は上書きしません。旧版の保存証拠は、生成時の旧版で検証してください。

### 数理仕様と実装をどう結び付けるか

| 層 | 役割 | 本版での位置付け |
|---|---|---|
| 各国・各組織の基準 | 守るべき条件と、その解釈を決める | 外部から与える。自動翻訳の正しさは仮定しない |
| 共通の保証原理 | 必須条件を省かず、不明を充足にせず、判定の違いを保持する | `FRAMEWORK.md`と`PolicyKernel.lean` |
| 実行と観測 | 許可を確認して作用を起こし、結果を保存する | 別プロセスとSQLiteで実行 |
| 独立した再計算 | 当時のルールと証拠で結果を照合する | `verify.py`。実行側をimportしない |

新規Leanモデルは、任意の基準の評価結果を共通の判定規則に接続します。「共同で許可するなら、対象の必須条件はすべて満たされている」「条件を追加しても既存の不適合を消せない」「同じ集約結果でも、どの当事者が不適合かは異なり得る」などを記述しています。

**既存コアはGitHub Actionsで形式検査に成功しています。** 2026年11月3日の[実行記録](https://github.com/GhostDriftTheory/verifiable-ai-assurance-framework/actions/runs/41570646962)、コミット`e1ab350`で、22定理宣言、1,089具体命題、偽命題3件の拒否を確認しました。今回追加したAPI接続自体の形式証明ではありません。次のコマンドとCIの`formal`ジョブは、指定版のLeanによる証明検査、Pythonとの具体入力照合、意図的な偽命題の拒否を要求し、未導入や失敗を成功にしません。

```console
# Lean 4.19.0を導入した環境。未導入なら終了コード2
python assurance.py formal
# 全試験に加え、形式検証の実行も必須にする
python assurance.py test --output ../haac-run-formal --require-lean
```

形式モデルの健全性は、各業務の評価器と証拠に関する明示した前提に依存します。Leanの検査成功後も、Python全体、SQLite、暗号、実設備、自然言語の解釈の正しさまで証明したことにはなりません。

### 今回、実際に確認したこと

| 検査区分 | ローカルでの結果 | 意味 |
|---|---|---|
| 異なるルールの比較・共同操作 | **30ケース成功** | 閾値、用途、承認数、欠損、版、単位、条件の差替え等 |
| 既存の実行制御 | **82ケース成功** | 41ケース×通知受付／設定変更。再送、中断、応答消失、回復等 |
| 誤実装対照 | **新規6件＋既存10件を検出** | 「誰か1社が適合なら許可」、不明の許可、全停止等を拒否 |
| 証拠・形式の改変 | **新規18件＋既存21件を拒否** | 当事者の削除、判定変更、作用の改変、虚偽の認証表示等 |
| 独立した2つのPython計算 | **968組＋150組が一致** | 長さ0～4の三値列×承認等、型・単位・比較演算の境界値 |
| 有限範囲の構造条件 | **605検査成功** | 全必須条件、一覧順序、条件追加で不適合が消えないこと |
| 既存コアのLean／GitHub CI | **成功** | [コミット`e1ab350`の5ジョブ](https://github.com/GhostDriftTheory/verifiable-ai-assurance-framework/actions/runs/41570646962)。API追加部分のCIではない |
| 外部者による再実行／独立組織の実装間試験 | **未実施** | 作成者の自己試験と明確に区別 |

試験対象は合成条件と、同じローカルDB内で観測した作用です。上記の件数を合算して安全性、攻撃防御率、認証点数にしません。初回確認環境はLinux・Python 3.13.5です。実行環境と配布ファイルのハッシュは結果に保存します。

### 既存8ファイル＋追加1ファイル

| ファイル | 内容 |
|---|---|
| `README.md` | 核心、具体例、実行方法、成果と限界 |
| `FRAMEWORK.md` | 12要求、異なる基準の接続、数理的根拠、保証範囲 |
| `CONFORMANCE.md` | 24観点、旧41ケース、新30ケース、期待値、適合表示 |
| `assurance.py` | 試験対象、別プロセス実行、比較実験、形式検査の起動 |
| `verify.py` | 別実装の判定と保存証拠の再検証 |
| `PolicyKernel.lean` | 共通保証原理の22命題。上記CIで検査済み |
| `lean-toolchain` | Leanの固定バージョン |
| `.github/workflows/verify.yml` | Linux／Windowsの既存コア試験と、必須の形式検査 |
| `openai_api_experiment.py` | 任意のAPI接続、合成実験、既存検証器を利用した再確認 |

生成される結果ファイルはリポジトリに置かず、別ディレクトリに保存します。今回の差替えは3つのMarkdown、追加はAPI実験用Pythonだけです。既存のPython、Lean、`lean-toolchain`、CI設定は変更しません。既存CIはAPI追加部分を自動実行しないため、その確認は`self-test`で別途行います。

### 任意のOpenAI API実験：追加Pythonは1ファイル

`openai_api_experiment.py`は、**実際のモデルが返した操作提案**を、変更していない既存の実行ゲートへ接続します。モデルが変更できるのは実行要求か保留かという提案であり、証拠、基準、必須当事者、承認、権限はローカルの試験条件として固定します。モデルは指定操作と`REQUEST_EXECUTION`または`HOLD`を返します。宛先、内容、識別情報、版が違う場合は、期待値へ勝手に補正せずアダプターが拒否します。

これは既存P01、P02、P03、P11、P12、P14、P15、P18、P19、P30を使う**限定的な接続実験**です。最後の3ケースは、許可後の当事者削除、証拠変更、時刻変更を試験プログラムが投入します。モデルがその変更を起こしたという実績にはしません。モデルへ渡すのは初期条件であり、期待結果や後から投入する変更は渡しません。

**Python 3.11以上の標準ライブラリだけで動きます。** SDK、依存関係ファイル、スキーマ用ファイルを追加する必要はありません。

```console
# キーも通信も不要。入力検査、模擬通信、実際のローカル作用、再検証を確認
python openai_api_experiment.py self-test

# 合成入力で全候補を意図的に実行要求する。OpenAIの出力ではない
python openai_api_experiment.py offline --output ../haac-api-offline

# 保存証拠を既存の別検証器で再確認し、改変検査も実行
python openai_api_experiment.py verify ../haac-api-offline/api-evidence.json --sha256-file ../haac-api-offline/api-evidence.sha256 --mutations

# 最初は2回の実API接続。YOUR_MODEL_IDを利用可能なモデルIDに置換
python openai_api_experiment.py live --model YOUR_MODEL_ID --cases P01,P02 --max-requests 2 --output ../haac-api-live

# 保存済みのAPI実験を、APIへ再接続せずに検証
python openai_api_experiment.py verify ../haac-api-live/api-evidence.json --sha256-file ../haac-api-live/api-evidence.sha256
```

Responses APIと厳格なStructured Outputsに対応し、自分のAPIアカウントで利用できるモデルを指定します。キーは環境変数`OPENAI_API_KEY`に設定するか、`live`開始時の非表示入力で渡します。実験ファイルにキーは保存しません。`OPENAI_MODEL`を設定した場合は`--model`を省略できます。Windowsでは必要に応じて`python`を`py -3`へ置き換えてください。

**外部APIへ接続するのは`live`だけです。** 公式Responsesエンドポイントへ、厳格なJSON Schemaによる`text.format`、ツールなし、`store=false`で送信します。この設定は、提供者側のあらゆるログの保存がゼロであることを意味しません。[API1–API3] 送信対象は同梱の合成条件だけです。接続先変更、環境変数によるプロキシ設定、リダイレクトは使用しません。既定値は10ケースを1回ずつ、最大10リクエストです。再試行、モデルの自動変更、失敗時の合成結果への差替えはしません。リクエスト数と`--max-output-tokens`の上限は、金額上限ではありません。`--reasoning-effort`は対応するモデルでのみ指定し、応答が未完了なら出力上限等を明示的に見直してください。

同じ受理済み提案を、独立した2つのローカルSQLite対象へ渡します。一方は提案どおりに動かす意図的に条件検査を省いた対照、もう一方は既存のHAACゲートです。対照はOpenAIの標準動作や他社製品の代表ではありません。モデルの保留、拒否、APIエラーではどちらも操作せず、そのまま記録します。**禁止される提案がモデルから出なかった場合は、当該ケースを試せた件数を0とし、遮断成功率を作りません。** 自由な計画生成や、本番システムへの汎用接続を実証するものではありません。

`api-evidence.json`には、送信内容、応答ID、応答中のモデル名、アシスタント出力、取得できたトークン使用量、振分け結果、試験条件の照合値、実際に観測したローカル作用を保存します。推論用出力項目と認証情報は保存しません。`journal.jsonl`へ途中経過を残し、完了時に`api-report.json`とハッシュファイルを保存します。中断した途中記録は、全試験完了の証拠ではありません。**出力先にはリポジトリ外の新規ディレクトリを指定します。** 公開前に生成された文章も確認してください。

`verify`コマンドは、保存されたモデル出力から提案を読み直し、対象範囲と実行結果を照合します。ゲートの再計算には、別プロセスから既存`verify.py`を利用し、実行側の`assurance.py`を呼びません。ただし、アダプターの読取り処理は共通コードです。新形式の証拠には追加Pythonを含む9ファイルのハッシュを記録し、従来形式の8ファイル分のハッシュとは区別します。`api-evidence.json`にはこの追加Pythonの`verify`を使い、従来`verify.py`のCLIへ直接渡しません。

**今回確認したのは**、オフライン10ケース、応答と対象範囲の21検査、操作しない4ケース、通信を模擬した6検査、模擬応答の2種類の記録検査、証拠改変14種類です。**実OpenAI API呼出しと、この追加部分のGitHub CIは未実施です。** 模擬応答をAPI実験の結果とは扱いません。保存応答は自己記録であり、OpenAIによる電子署名付きの出所証明ではありません。記録と同梱ハッシュの同時差替えや、現実の観測内容の真実性まで保証せず、既存Lean証明の対象もAPI全体へ拡張しません。

### 何への適合を示せるか

`CONSISTENT_REFERENCE`は、**宣言した合成プロファイルの記録が、同じ版の規則と照合値に整合する**という結果です。HAAP全体の相互運用性、組織の身元、実世界の観測事実、法令適合性を認定しません。

同梱ハッシュはローカルの照合基準です。証拠と同時に置き換えられれば真正性を保証できません。別経路で確保した値を`--sha256`で指定しても、観測内容の真実性や身元まで証明するものではありません。照合値なしは`CONSISTENT_UNANCHORED`、終了コード2です。

フレームワーク全体の適合、参照コードの試験成功、限定した形式モデルの検査は別の主張です。署名、組織の信頼基点、本番システムの全実行経路、独立した観測者、政策解釈の妥当性は追加確認が必要です。

### 公開主体・利用条件・変更手続

発行主体は**株式会社AIアシュアランス**。HAACでの検討に供する公開作業草案です。HAAC正式採択、政府承認、国際標準、第三者認証を表明しません。特定の製品、ADIC実装、条件記述言語、運用モデルは適合条件にしません。

本版は**ソース公開の検討草案で、OSSライセンスは設定していません**。既存版の権利方針を変更せず、仕様の利用、コードの再配布・商用組込み、特許の取扱いは権利者の確定事項としています。正式な共通利用の募集前に、これらを明確にする必要があります。公開を、既存特許の実施許諾や全技術の開示と解釈しないでください。

意見はIssueで、版、R/T/P番号、合成の再現例、期待結果と実結果を記載してください。秘密、認証情報、実顧客データは投稿しないでください。レビューでは、政策解釈の担当と、実装検証の担当を分けます。採否の理由、未解決事項、変更履歴を残し、旧版の証拠を新版の条件で上書きしません。日本語が本草案の規範本文です。

**v0.2→v0.3：** 訴求の中心を「異なる安全基準を接続する共通の保証原理」へ変更。既存12要求と実行試験を保ち、30の比較ケース、別検証、適用範囲の固定、形式モデル、負の対照、必須形式検査を追加しました。当初未実施だった形式検査は、その後、上記のコアCIで成功を確認しました。

**今回の文書改訂：** 英語を先、日本語を後に配置し、任意のAPI実験を追加しました。既存のR/T/P要件、機械可読ケース、利用条件は維持しています。文書の変更もハッシュを変えるため、過去の証拠は生成時のコミット、新しく生成する証拠は新しいファイル一式で検証します。

## Sources / 参照資料

Existing sources support their own scope. Their full codebases were not rerun in preparing this release.

| Source | Connection, not an additional guarantee |
|---|---|
| [HAAP public technical overview](https://hiroshima-ai-assurance.com/protocol) — checked 2026-11-03 | Distinct verification, adoption and authorization states. Normative wire interoperability remains separate work. |
| [Responsibility Information Kernel](https://github.com/GhostDriftTheory/responsibility-info-kernel) — README checked 2026-11-03 | Relevant distinctions can be lost in summaries; retaining appropriate information supports later inspection. Not proof of the new code. |
| [Responsibility OS Kernel](https://github.com/GhostDriftTheory/responsibility-os-kernel) / [ADIC AI Assurance](https://github.com/GhostDriftTheory/adic-ai-assurance-lean) | Existing preservation structures under stated assumptions; retained references from v0.2. |
| [VPI Cyber Assurance](https://github.com/GhostDriftTheory/verifiable-physical-internet-cyber-assurance) / [Cold Chain Cyber Assurance](https://github.com/GhostDriftTheory/verifiable-coldchain-cyber-assurance) | Existing bounded execution-control and model-verification experiments; not certification of this release. |
| [OECD reporting framework](https://oecd.ai/en/transparency/overview) / [AISI evaluation guide](https://aisi.go.jp/output/output_framework/guide_to_evaluation_perspective_on_ai_safety/) | External governance/evaluation frameworks to connect through reviewed mappings, not replace. No complete clause-by-clause conformity is claimed. |
| [Lean 4.19 language reference](https://lean-lang.org/doc/reference/4.19.0/Introduction/) | Toolchain documentation; tool documentation, not third-party approval of this implementation. |

| [Baseline core CI](https://github.com/GhostDriftTheory/verifiable-ai-assurance-framework/actions/runs/41570646962) | 2026-11-03, commit `e1ab350`: existing Python/Lean checks; not the later API add-on. |
| [API1: Responses API reference](https://developers.openai.com/api/reference/resources/responses/methods/create) | Request/response fields used by the optional connector; checked 2026-11-03. |
| [API2: Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) | Strict JSON output and refusal/incomplete handling; shape constraints are not authority. |
| [API3: API data controls](https://developers.openai.com/api/docs/guides/your-data) | `store=false` is not a general zero-retention promise. |
