# HAAC AI Assurance Framework

## Different safety rules. A shared way to verify and authorize execution.
## 安全基準は異なっていても、検証と実行許可の仕組みは共通化できる。

**Public Working Draft v0.3.0 · 2026-11-03 · AI Assurance Inc.**  
[日本語](#日本語) · [English](#english) · [共通要求 / Framework](FRAMEWORK.md) · [試験 / Conformance](CONFORMANCE.md) · [Lean model](PolicyKernel.lean)

## 日本語

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

**新規Leanコードは本作成環境で未検査です。** 検査器を導入できなかったため、形式検証成功とは表示していません。次のコマンドとCIの`formal`ジョブは、指定版のLeanによる証明検査、Pythonとの具体入力照合、意図的な偽命題の拒否を要求し、未導入や失敗を成功にしません。

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
| 新規Leanのカーネル検査／GitHub上のCI | **未実施** | 証明ソースと必須検査設定を同梱 |
| 外部者による再実行／独立組織の実装間試験 | **未実施** | 作成者の自己試験と明確に区別 |

試験対象は合成条件と、同じローカルDB内で観測した作用です。上記の件数を合算して安全性、攻撃防御率、認証点数にしません。初回確認環境はLinux・Python 3.13.5です。実行環境と配布ファイルのハッシュは結果に保存します。

### コンパクトな8ファイル

| ファイル | 内容 |
|---|---|
| `README.md` | 核心、具体例、実行方法、成果と限界 |
| `FRAMEWORK.md` | 12要求、異なる基準の接続、数理的根拠、保証範囲 |
| `CONFORMANCE.md` | 24観点、旧41ケース、新30ケース、期待値、適合表示 |
| `assurance.py` | 試験対象、別プロセス実行、比較実験、形式検査の起動 |
| `verify.py` | 別実装の判定と保存証拠の再検証 |
| `PolicyKernel.lean` | 共通保証原理の22命題の証明候補 |
| `lean-toolchain` | Leanの固定バージョン |
| `.github/workflows/verify.yml` | Linux／Windowsの試験と、必須の形式検査 |

生成される結果ファイルはリポジトリに置かず、別ディレクトリに保存します。既存v0.2の6ファイルを更新し、Leanの2ファイルを追加する構成です。`.github`フォルダもアップロードしてください。

### 何への適合を示せるか

`CONSISTENT_REFERENCE`は、**宣言した合成プロファイルの記録が、同じ版の規則と照合値に整合する**という結果です。HAAP全体の相互運用性、組織の身元、実世界の観測事実、法令適合性を認定しません。

同梱ハッシュはローカルの照合基準です。証拠と同時に置き換えられれば真正性を保証できません。別経路で確保した値を`--sha256`で指定しても、観測内容の真実性や身元まで証明するものではありません。照合値なしは`CONSISTENT_UNANCHORED`、終了コード2です。

フレームワーク全体の適合、参照コードの試験成功、限定した形式モデルの検査は別の主張です。署名、組織の信頼基点、本番システムの全実行経路、独立した観測者、政策解釈の妥当性は追加確認が必要です。

### 公開主体・利用条件・変更手続

発行主体は**株式会社AIアシュアランス**。HAACでの検討に供する公開作業草案です。HAAC正式採択、政府承認、国際標準、第三者認証を表明しません。特定の製品、ADIC実装、条件記述言語、運用モデルは適合条件にしません。

本版は**ソース公開の検討草案で、OSSライセンスは設定していません**。既存版の権利方針を変更せず、仕様の利用、コードの再配布・商用組込み、特許の取扱いは権利者の確定事項としています。正式な共通利用の募集前に、これらを明確にする必要があります。公開を、既存特許の実施許諾や全技術の開示と解釈しないでください。

意見はIssueで、版、R/T/P番号、合成の再現例、期待結果と実結果を記載してください。秘密、認証情報、実顧客データは投稿しないでください。レビューでは、政策解釈の担当と、実装検証の担当を分けます。採否の理由、未解決事項、変更履歴を残し、旧版の証拠を新版の条件で上書きしません。日本語が本草案の規範本文です。

**v0.2→v0.3：** 訴求の中心を「異なる安全基準を接続する共通の保証原理」へ変更。既存12要求と実行試験を保ち、30の比較ケース、別検証、適用範囲の固定、形式モデル、負の対照、必須形式検査を追加しました。新規形式検査は未実施として公開範囲を限定しています。

## English

### Shared assurance, not identical policy

**Safety rules may differ. The procedure for verifying them and authorizing a specific operation can be shared.** This framework preserves each party's rules, interpretation, version, evidence and individual result instead of forcing a common safety threshold or a common verdict.

In a synthetic example, A accepts 2–8°C while B accepts 2–6°C. At 7°C, A is satisfied and B is not. Both results are reproducible. An operation requiring both parties is withheld; at 5°C with valid approval and authority, it proceeds. A separately approved A-only operation has its own scope. An A-only permission must not authorize an A+B operation.

The same procedure covers structurally different rules: a cyber operator's impact limit and another party's permitted environment and required approval count. Unknown requirements are not silently satisfied. Required parties cannot be removed after a grant. Conflicting policies are not averaged, voted away or replaced by the most permissive rule.

This supports agreement about **how a decision was justified**, not a mathematical guarantee of agreement about values. Authorized people determine applicability, interpretation and acceptable evidence. The framework does not prove that their choices are legitimate or complete.

### Executable package and formal status

The eight files contain twelve requirements, twenty-four test topics, the retained execution laboratory, thirty new policy cases, two separately written Python evaluators, a Lean model, and CI settings. Run `python assurance.py policies` for the central examples, then the test and verifier commands above. Python 3.11+ and the standard library suffice for the ordinary executable tests; these do not invoke Lean or use the network. Tool installation and CI setup require network access. Formal checking is explicitly requested by `formal` or `--require-lean`. No production credentials are used.

Author-run local checks passed 30 new policy cases and 82 retained execution cases; rejected 6+10 faulty controls and 18+21 record mutations; agreed on 968 abstract inputs and 150 typed rule inputs; and passed 605 finite structural checks. These categories are not a safety percentage. Actual effects are recorded in a receiver subprocess and SQLite; the separate verifier does not import the execution program.

**The new Lean proof candidate has not been kernel-checked in the authoring environment because the toolchain could not be installed.** It is not advertised as a successful formal verification. `python assurance.py formal` and the mandatory `formal` CI job require Lean 4.19.0, theorem checks, 1,089 generated concrete obligations and rejection of three false obligations. Missing Lean or a failure returns an error, never a proof-success result. Hosted CI and external reproduction have not been performed.

The mathematical model expresses policy-independent soundness **assuming each domain checker is sound**, nonempty all-required authorization, resistance to erasing a failure by adding requirements, preservation under a semantic adapter, and the loss of party-specific information under aggregation. It does not prove Python/SQLite, a real system, source truth, cryptography or natural-language interpretation.

### Scope, rights and stewardship

This is a public working draft issued by AI Assurance Inc. for HAAC discussion, not an adopted Council standard, a government endorsement or third-party certification. No proprietary implementation or named policy language is required. HAAP's public overview is the semantic reference, not an established wire-compatibility claim.

The draft remains source-available **without an OSS license**; reuse, redistribution, commercial integration and patent terms require the rights holder's determination. No new rights grant is made by this revision. Production secrets and proprietary engines are not included. Japanese is the normative draft text. Report discrepancies, retain versioned evidence, and distinguish policy-owner approval from technical review.

## Sources / 参照資料

Existing sources support their own scope. Their full codebases were not rerun in preparing this release.

| Source | Connection, not an additional guarantee |
|---|---|
| [HAAP public technical overview](https://hiroshima-ai-assurance.com/protocol) — checked 2026-11-03 | Distinct verification, adoption and authorization states. Normative wire interoperability remains separate work. |
| [Responsibility Information Kernel](https://github.com/GhostDriftTheory/responsibility-info-kernel) — README checked 2026-11-03 | Relevant distinctions can be lost in summaries; retaining appropriate information supports later inspection. Not proof of the new code. |
| [Responsibility OS Kernel](https://github.com/GhostDriftTheory/responsibility-os-kernel) / [ADIC AI Assurance](https://github.com/GhostDriftTheory/adic-ai-assurance-lean) | Existing preservation structures under stated assumptions; retained references from v0.2. |
| [VPI Cyber Assurance](https://github.com/GhostDriftTheory/verifiable-physical-internet-cyber-assurance) / [Cold Chain Cyber Assurance](https://github.com/GhostDriftTheory/verifiable-coldchain-cyber-assurance) | Existing bounded execution-control and model-verification experiments; not certification of this release. |
| [OECD reporting framework](https://oecd.ai/en/transparency/overview) / [AISI evaluation guide](https://aisi.go.jp/output/output_framework/guide_to_evaluation_perspective_on_ai_safety/) | External governance/evaluation frameworks to connect through reviewed mappings, not replace. No complete clause-by-clause conformity is claimed. |
| [Lean 4.19 language reference](https://lean-lang.org/doc/reference/4.19.0/Introduction/) | Toolchain documentation; no external approval of these proof candidates. |
