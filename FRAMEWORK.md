# HAAC AI Assurance Framework — Shared Assurance across Different Rules

**Public Working Draft v0.3.0 · 2026-11-03**  
[Overview / 概要](README.md) · [Tests / 試験](CONFORMANCE.md) · [English](#english)

## 日本語

### 1. 目的：基準を一致させず、検証の共通ルールを作る

**国、企業、業界の安全基準が異なっていても、どの条件を採用し、何を根拠に判定し、どの操作を許可したかを、共通の手順で検証できるようにします。**

標準化する対象は「何を安全とするか」という価値判断そのものではありません。各主体が選んだ基準を明示し、その適用範囲、証拠、判定、許可、実際の作用を結び付ける保証の構造です。互いの基準が異なることを、実装上の誤りと混同しません。

同じルールと証拠なら検証結果を再現できること、異なるルールで結果が違えばその理由を残せること、共同操作では必要な当事者の条件を勝手に省けないことが中核です。これを**共通に検証可能な運用の土台**として提案します。全員の価値判断や納得を数学が保証するという主張ではありません。

| 共通にすること | 各主体が決定すること |
|---|---|
| ルールの出所、版、解釈、適用範囲の表示 | どの法令、契約、方針が当該操作に適用されるか |
| 条件充足、違反、判定不能の区別 | 閾値、必要な承認、許容リスク |
| ルールごとの結果を残す方法 | 証拠の信頼性や十分性を認める条件 |
| 操作別の許可と、許可を作用に結び付ける方法 | 実行を委任する範囲、安全な停止・継続の方法 |
| 適合性試験と独立再検証の手順 | 法的判断、価値判断、現実の事実の確認 |

特定の製品、ADIC実装、条件記述言語、運用モデルの採用を必須にしません。以下の小型ルール形式は**同梱実験用の参照形式**であり、各社にそれへの移行を要求するものではありません。

### 2. 既存の基準を接続するための契約

実装者は、対象操作ごとに次の対応を提示します。

```text
元の基準（出典、版、該当箇所）
  → 当該業務での解釈と、その承認者
  → 必要な当事者と、適用する条件・評価器
  → 証拠の出所、鮮度、型、単位、取得範囲
  → 各条件の結果と未確認事項
  → 採用・個別操作の許可
  → 観測した作用と、その後の再検証
```

この連鎖を記述することは、元の基準全体への適合認証ではありません。自然言語の条件を自動で完全に翻訳できるとも仮定しません。解釈できない必須条件は、人による審査を含めて未解決として残します。

**適用範囲は評価結果を見てから変更してはなりません。** 必要な当事者と採用した条件の版は、権限を持つ主体が先に定めます。一社の承認を、複数社の共同操作へ流用しません。範囲変更を行う場合は、その理由と権限を確認し、新たな評価と許可を発行します。

| 接続時の義務 | 禁止する扱い | 参照試験 |
|---|---|---|
| 必要な当事者と、各条件の承認済みの版を固定 | 条件が厳しい当事者を黙って外す | P07–P10, P18, P23, P29 |
| 各主体の判定と理由を保持 | 共通スコアだけで差を消す | P01, P13, P14 |
| 単位と型の意味を確認する | 単位が違う数値をそのまま比較 | P04, P05, P25, P26 |
| 未確認の必須条件を残す | 未対応の評価を「適合」にする | P03, P06, P16, P27, P28 |
| 操作、条件、証拠と許可を対応付ける | 許可後の対象変更や条件の緩和 | P17–P21, P30 |
| 不適合に加え、正常系も確認 | 全停止するだけで合格とする | P02, P10, P15, P22, P25 |

### 3. 判定の区別と共同操作の意味

```text
異なる基準 → 同じ検証構造 → ルール別の結果を保持
                              ↓
               対象の必須条件をすべて確認
                              ↓
                組織としての採用・必要承認
                              ↓
                操作別許可 → 再確認 → 作用
                              ↓
                   結果照合 → 独立再検証
```

| 区分 | 状態 | 同一視してはならないこと |
|---|---|---|
| 条件検証 | `SATISFIED / UNSATISFIED / INDETERMINATE` | 不明は充足ではない |
| 採用可能性 | `ADOPTABLE / CONDITIONALLY_ADOPTABLE / NOT_ADOPTABLE / PENDING_EVIDENCE` | 採用可能と実際の承認は異なる |
| 操作許可 | `AUTHORIZED / REQUIRES_REVIEW / NOT_AUTHORIZED` | 許可は実行完了ではない |
| 作用の結果 | `COMPLETED / PARTIAL / QUARANTINED / UNKNOWN` 等 | 応答消失は未実行の証明ではない |

最初の3区分はHAAP公開概要に意味上対応します。[S1] 結果区分、本草案の集約規則、JSONの形式は本版の提案であり、HAAPの正式な通信規格とはしません。

**集約規則**：空の必須条件一覧は判定不能とします。確認済みの違反が一つでもあれば全体は不適合、違反がなくても未確認があれば判定不能、全条件が確認できたときだけ充足です。違反と不明が併存しても、不明の詳細を消しません。

**共同操作の許可**：宣言した範囲の必須条件すべての充足、必要な承認、有効な権限、対象と許可の一致が必要です。世界中の全基準を一律に重ねるという意味ではありません。単独操作は別の承認済み範囲で評価できますが、その許可を共同操作へ流用できません。

矛盾した基準から、勝手に平均値、投票、多数決、最も緩い基準を作って許可してはなりません。矛盾は人の判断を要する課題として示します。正規の手続で基準を変更する場合も、旧判断と変更理由を保存します。

停止は指定操作の保留であり、全設備の無条件の急停止ではありません。緊急退避や安全な継続には、その操作自身の権限と条件を定めます。毎回の手動承認は必須でなく、レビュー済みの権限委任も認めます。

### 4. 共通要求 R01–R12

以下はv0.2から引き継ぐ本草案の要求です。「しなければなりません」は、本草案への適合主張に必要な条件を示し、政府や国際標準による採択を意味しません。

#### R01 — 保証する操作と境界

対象操作、対象資源、作用が起きる地点、組織・システムの範囲、前提、対象外、停止時の安全な挙動を明記しなければなりません。模擬通知の成功を実貨物の移動保証へ拡張してはなりません。

#### R02 — 責任・権限・承認

条件を決める主体、証拠を提供する主体、採用を承認する主体、実行主体、照合・異議対応の担当を区別し、委任範囲と有効期間を記録しなければなりません。役割名や署名だけで実在する権限を認定してはなりません。

#### R03 — 条件・評価方法の版と時間

適用条件、評価方法、閾値、単位、版、評価時点、許容される証拠の古さを操作に対応付けなければなりません。条件や対象が変わった場合、旧結果を無条件で流用してはなりません。

#### R04 — 証拠の十分性と限界

必要証拠、出所、確認方法、未確認事項を列挙しなければなりません。欠落・矛盾・形式不正・未対応の必須条件を充足扱いにしてはなりません。改変検知、発行者認証、観測内容の真実性を別の主張として扱わなければなりません。

#### R05 — 検証・採用・許可の分離

条件の検証結果、組織としての採用判断、個別操作の実行許可を区別しなければなりません。条件充足や担当者の確認済み表示だけから、実行許可を導出してはなりません。必要な承認は対象操作・内容・承認者に対応付けます。

#### R06 — 操作ごとの許可と失効

許可を操作ID、内容、宛先、実行主体、条件版、期限、許容作用に対応付けなければなりません。失効・取消し・更新時の効力と伝播遅延、既発行許可の扱いを明記し、宣言した意味に従って実行直前に再確認します。

#### R07 — 実際の作用に対する制御

宣言した対象操作の全実行経路に、許可を必須とする制御を設けなければなりません。画面表示やログの判定だけでは足りません。迂回経路、同時処理、検証から作用までの状態変化を試験し、制御できない経路を保証対象に含めてはなりません。

#### R08 — 結果不明・再送・回復

応答消失、再起動、処理中断で結果が不明な場合、完了・未実行を推測してはなりません。操作の同一性と保存済み結果を照合し、二重作用を防ぐ範囲を明示します。再試行、保留解除、取消し、切替えの条件を定めなければなりません。

#### R09 — 実行結果の照合

許可した作用と、観測・保存した結果を対応付けて照合しなければなりません。不一致、部分実行、結果不明を正常完了として報告してはなりません。事後隔離や補償処理を、実行前の遮断や元の作用の不存在と混同してはなりません。

#### R10 — 追跡可能な記録と最小開示

要求、証拠参照、評価、承認、許可、実行結果、変更履歴を同一操作へ対応付け、再検証に必要な範囲で保存しなければなりません。保存期間・開示先・閲覧権限を定め、秘密鍵や不要な個人情報を検証資料へ含めてはなりません。

#### R11 — 独立した再検証

実行側の結論をそのまま受け入れず、利用可能な証拠と指定版の規則から再判定する方法を示さなければなりません。証拠不足や未知の信頼基点を判定不能として扱います。別プログラム、別担当者、別組織の独立性を区別して報告します。

#### R12 — 変更・例外・適合主張

ルール変更、モデル更新、例外承認、試験変更の影響を追跡しなければなりません。例外は失敗した検証を成功へ書き換えず、許容された別の手続として記録します。適合主張には版、対象、前提、試験結果、未実施項目、残余リスクを添えます。

### 5. 共通保証原理の数理的な意味

必要な条件の集合を `I`、証拠を `e`、条件 `i` の評価を `cᵢ(e)` とします。評価の出力は充足、違反、判定不能の三値です。条件の中身は分野ごとに異なって構いません。

```text
共通許可判定（抽象モデル）
⇔ Iが空でなく、すべてのi∈Iで cᵢ(e)=充足
   かつ必要承認が有効
   かつ権限が有効
   かつ許可と対象が一致
```

この式は、現実の安全性の定義ではありません。本版で選ぶ「必須条件を省略しない許可規則」です。実際の作用を制御するには、R07の実行ゲートがこの判断を必須にする必要があります。

**条件付きの健全性**：各評価器について「充足と判定したなら、その評価器が対象とする性質が成り立つ」という前提が成立する場合、共通規則で許可した操作は、宣言した全必須条件の性質を満たします。共通規則だけでは、各評価器の正しさ、証拠の真実性、条件一覧の完全性は導けません。

**違いを残す必要性**：Aが充足でBが違反の場合と、その逆では、全体の集約値はいずれも不適合です。集約値だけから誰のどの条件が成立しなかったかは復元できません。そのため、当事者、条件の版、個別結果、証拠参照を含む責任情報を残します。責任OSはこの意味での責任の運用層（governance operating layer）であり、コンピュータのOSではありません。

| 数理的性質 | `PolicyKernel.lean`の主な命題 | 実行側との接点 |
|---|---|---|
| 空一覧や未確認から許可しない | `summary_satisfied_iff`, `required_unknown_blocks` | P03, P07–P09, P16, P28 |
| 許可に全必須条件が必要 | `authorization_requires_every_rule`, `joint_soundness` | P01–P03, P14–P16 |
| 承認、権限、結び付きが必要 | `authorize_iff`, `no_approval_no_authorization`, `changed_binding_no_authorization` | P11, P12, P17–P21 |
| 条件を追加しても既存の不適合を消せない | `extension_cannot_erase_failure` | 605件の有限範囲の構造検査 |
| 意味保存を満たす変換は結果を保持 | `semantic_adapter_preserves_report` | P25。変換の意味保存自体は別の前提 |
| 集約だけでは当事者の差が消える | `aggregation_loses_party_difference` | P01, P13, P14 |
| 別の条件から異なる結論を認める | `different_rules_different_results` | P01。P02は両者が成立する正常例 |
| 単独の許可を共同操作へ流用しない | `single_party_not_joint_permission` | P10, P18 |

**新規22命題のLeanソースは、この配布の作成環境でカーネル検査できていません。** 証明候補を検証済みとは表示しません。`python assurance.py formal`はLean 4.19.0を必須にし、ソースの検査、Pythonの出力と1,089の具体入力命題の照合、3つの偽命題の拒否を実行します。未導入や失敗は終了コード2です。

Python同士の968組の抽象入力照合、150組の型付き条件照合、605件の有限構造検査は実行済みです。これらは一般定理の証明ではありません。また、Lean検査後も、任意のPython入力、JSON解析、SQLite、暗号、物理設備までの実装同値性を示したことにはなりません。

責任OS／ADIC／責任情報カーネルの既存成果は、責任情報や監査上必要な区別の保存という技術的背景です。[S2–S4] この新規コードが以前の証明を自動的に継承したとは主張しません。

### 6. 参照プロファイルと保証境界

#### RP-0.3：異なるルールの共通検証

温度条件を扱う合成例と、システム設定変更を扱う合成例を、同じ三値集約と許可規則で扱います。温度の例は実医薬品の基準ではなく、設定変更の例も本番ネットワーク操作ではありません。

| 項目 | 本版の意味 |
|---|---|
| 適用範囲 | `required_parties`を事前に定め、重複・空一覧・欠落を許可へ進めない |
| 条件の固定 | `policy_pins`で承認済みポリシーのハッシュを照合。ローカルに信頼した入力であり、署名や認証ではない |
| 条件記録 | `party, id, version, source, interpretation, rules`を保持 |
| 条件評価 | `between, lte, gte, eq, one_of`。未知の演算子は判定不能 |
| 型・単位 | 数値は整数で比較し、boolと混同しない。温度はmC（1/1000℃）。曖昧な単位推定はしない |
| 変換 | 明示的な`centi-C-v1`のみ、1/100℃整数をmCへ正確に変換。未対応の変換は判定不能 |
| 時間 | 試験用整数時計。証拠経過0～20、許可の有効区間は`[start,start+10)` |
| 許可の結び付き | 操作、当事者一覧、条件、証拠、承認状態等を固定。現在時刻だけはハッシュから除き、期限で確認 |
| 一覧の順序 | 条件の在庫一覧の並び替えだけを正規化。履歴の時間順序や条件変更の意味は消さない |
| 実行 | 別プロセスが同一SQLiteトランザクションで再確認し、模擬状態変更と作用・監査記録を保存 |
| 再検証 | 公開試験入力と別に実装した評価器から期待値を計算し、受信側の保存状態と照合 |

`assessment.authorization`は現在の条件に基づく許可候補です。保存された操作別許可（`grant`）とは区別し、実行時には両方を確認します。条件を変更して新しい候補が成立しても、以前の許可の流用はできません。

本プロファイルの当事者一覧、ポリシーの解釈、承認・失効フラグ、証拠は試験者が与えます。現実の組織権限や証拠の真実性を検証する機能ではありません。ハッシュの一致を、その条件が妥当であることの証明に使いません。

30ケースは各々、新規のDBで一つの操作を評価します。複数操作の再送、並行処理、中断・回復は、次の引継ぎプロファイルで別に検査します。両群の結果を、実企業間の独立実装試験として扱いません。

#### RP-0.2：引き継ぐ実行制御の試験

通知受付と模擬設定変更に41ケースずつを適用します。対象はSQLite内の作用です。許可、失効、条件版、事前改訂番号を確認し、同一の`(issuer,id)`への二重作用をDB制約とトランザクションで抑制します。

保存前のプロセス中断では、同一DB内の原子的な作用のロールバックを前提に再試行します。保存後の応答消失では、保存結果を照合し、応答がないことを未実行と決めつけません。取消しは作用前のみ、宛先切替えと正規の例外解除は非対応として拒否します。事後の隔離や部分作用を事前遮断とは数えません。

OS、Python、SQLite、試験者、ローカルDB、時計を信頼します。管理者の直接DB改変、本番APIの全経路、分散鍵管理、署名、実世界の真値、性能SLAは対象外です。外部APIや設備の作用は同じDBトランザクションでは扱えず、この原子性保証をそのまま転用できません。

### 7. 記録、再実行、適合主張

保存する情報は、対象操作、元の提案、適用範囲、各ルールの出所と版、解釈の承認、証拠参照、個別判定、未確認事項、許可、実行結果、変更履歴、検証器と配布物の版です。保存期間、開示権限、異議への対応も設計審査に含めます。

機密情報を非開示にする場合も、第三者が再計算できない部分は明示します。判定結果だけの共有を、判断根拠を含む独立検証とは呼びません。署名、ハッシュ、発行者の身元、観測の真実性は別の主張です。

| 結果形式 | 内容 | 意味 |
|---|---|---|
| `haac-policy-evidence/0.3` | 30比較ケース、当事者別結果、操作の作用、8ファイルのハッシュ | 本版の合成比較実験 |
| `haac-reference-evidence/0.2` | 引継ぎ82ケース、状態、履歴、実行環境、8ファイルのハッシュ | 内容形式は維持し、framework版は0.3.0とする |
| `test-report.json` | 検査区分別の結果、形式検査の実施状況 | 自己試験の集計。認証書ではない |

対象側の状態を同じ管理者が収集しています。別プログラムによる再検証は提供しますが、別組織の監査、別実装間の交換、本番での安全性は未実証です。

任意の製品を評価するには、その製品の実際の作用を観測できるアダプターと、権限・証拠・制御経路のレビューが必要です。参照モデルに合う記録を作るだけでは、外部製品の適合を示せません。

### 8. 外部の評価枠組みとの接続

OECD、AISI、国内ガイドライン等の要求は「出典・版・節 → 業務での解釈と承認者 → R番号 → T/P番号 → 証拠 → 機械判定できない部分」で対応付けます。既存の安全性評価、監督、制御、監査の機能が存在しないとは主張しません。本版はこれらを置き換えず、操作ごとの根拠と作用の照合へつなぐ提案です。

本版の合成ルールを、特定の法令や国際原則を完全に実装したものとして表示してはなりません。正式な利用では、該当業務の専門家による解釈審査、当事者の合意、外部再実行、知財と利用条件の整理が必要です。

## English

### 1. Shared verification while preserving different rules

Safety thresholds and substantive policy judgments may differ. This draft shares the way an operation's applicable rules, versions, evidence, individual verdicts, authorization and actual effect are inspected. It seeks a common, reproducible assurance procedure, not a common risk appetite or a guarantee that everyone agrees.

Identical rules and evidence should produce reproducible results. Different rules may legitimately produce different results. Preserve those differences rather than hiding them in an aggregate score. A joint operation must not omit a required participant merely because its rule is stricter; an independently approved single-party operation has a different scope.

No proprietary implementation, policy language or named operational model is mandatory. The small input language in this laboratory is a reference adapter, not a required replacement for existing policy systems.

### 2. Connection contract and authorization

Record the source requirement/version/section, the authorized operational interpretation, required parties and approved policy versions, evidence provenance/type/unit/freshness, individual verdicts and unresolved obligations, organizational adoption, scoped permission, observed effects and verification procedure.

Applicability and interpretation remain human governance responsibilities. A supplied list does not prove that all relevant laws or contractual obligations were identified. Unknown mandatory requirements remain unresolved. Changes of scope require an authorized new assessment, not silent deletion after seeing an inconvenient result.

The aggregate is INDETERMINATE for an empty set, UNSATISFIED if any verified violation exists, INDETERMINATE if unresolved obligations remain without a violation, and SATISFIED only if all required checks satisfy. Keep unresolved details even when a violation determines the aggregate. Joint authorization additionally requires valid approval, active authority and matching binding. Conflicting requirements are not averaged or voted away. This applies to the declared operation, not every rule worldwide.

HAAP separates verification, adoptability and authorization.[S1] This draft's additional aggregation, outcome fields and serialization are not an adopted HAAP wire protocol. Approval need not be a human click for each operation: an appropriate delegation can apply. Holding an action is not indiscriminate shutdown of all equipment.

### 3. Core requirements R01–R12

#### R01 — Operation and assurance boundary

Specify the operation, resources, effect boundary, participating systems, assumptions, exclusions, and safe behavior when the operation is held. A simulated notification must not be represented as assurance of physical cargo movement.

#### R02 — Accountability, authority and approval

Distinguish the rule owner, evidence provider, adoption approver, executor, and reconciliation/dispute owner. Record delegation scope and validity. A role label or signature alone must not establish real organizational authority.

#### R03 — Versioned rules and time

Bind applicable rules, evaluation method, thresholds, units, versions, evaluation time, and permitted evidence age to the operation. Changed rules or targets must not inherit an old result without revalidation.

#### R04 — Evidence sufficiency and limits

Enumerate required evidence, provenance, verification methods, and unresolved conditions. Missing, conflicting, malformed, or unsupported mandatory evidence must not count as satisfied. Integrity, issuer authentication, and observation truth are distinct claims.

#### R05 — Separate verification, adoption and authorization

Keep condition evaluation, organizational adoption, and operation-specific authorization distinct. Satisfied conditions or a generic reviewed flag must not alone authorize execution. Required approvals must bind the approver to the operation and its content.

#### R06 — Scoped grants and revocation

Bind authorization to operation identity, content, recipient, executor, rule version, validity and allowed effects. Declare revocation/cancellation/update semantics, propagation delay, and treatment of issued grants; recheck at the execution boundary under those semantics.

#### R07 — Enforcement at the effect boundary

Every in-scope path to the declared effect must require valid authorization. A dashboard or decision log is insufficient. Test bypasses, concurrent activity, and state changes between check and effect; exclude uncontrolled paths from the claim.

#### R08 — Uncertainty, retries and recovery

Do not infer completion or non-execution from a lost response, restart or interruption. Reconcile operation identity with durable outcomes and state the scope of duplicate-effect protection. Define conditions for retry, release from hold, cancellation and switching.

#### R09 — Outcome reconciliation

Link and compare the authorized effect with observed and retained outcomes. A mismatch, partial execution or unknown outcome must not be reported as successful completion. Post-effect quarantine or compensation is not prevention or proof that the original effect never occurred.

#### R10 — Linked records and minimum disclosure

Link requirements, evidence references, evaluations, approvals, grants, receipts and updates to the operation, retaining what re-verification needs. Define retention and access. Verification material must not expose private keys or unnecessary personal data.

#### R11 — Independent re-verification

Provide a way to recompute the relevant checks from available evidence and identified rule versions rather than trusting the executor's conclusion. Missing evidence or unknown trust anchors must be reported as unverifiable. Distinguish separate programs, separate personnel and separate organizations.

#### R12 — Change, exceptions and claims

Track the impact of rule/model updates, exceptions and test changes. Preserve failed verification results when an authorized exception process is used. Any conformance claim must include version, scope, assumptions, results, unperformed tests and residual risks.

### 4. Mathematical meaning and verification status

Let `I` be a declared nonempty set of required conditions, `e` the evidence and `cᵢ(e)` a three-valued checker. Authorization requires all `cᵢ(e)` to be satisfied plus approval, active authority and matching binding. The checker bodies can differ by sector. If each checker is sound for its stated property, authorization entails all those properties in the declared scope. Checker soundness, evidence truth and applicability completeness are premises, not consequences.

`PolicyKernel.lean` contains 22 candidate theorem declarations for nonempty all-required authorization, blocking unknowns and violations, binding and authority, monotonic rejection under added requirements, conditional joint soundness, preservation under a semantics-preserving adapter and the information lost by aggregation. The named theorem/test mapping appears in the table above. The adapter theorem assumes preservation for the relevant evidence; it does not prove arbitrary JSON parsers or unit conversions correct.

**The new Lean source has not been kernel-checked in the authoring environment.** The formal command requires Lean 4.19.0, checks the candidate file, checks 1,089 generated concrete equalities against Python outputs and rejects three intentionally false claims. Failure or an unavailable toolchain is an error, never a successful proof. The executed 968 abstract comparisons, 150 typed comparisons and 605 finite structural checks are not general proofs.

Earlier Responsibility OS/ADIC/information kernels motivate preserving accountability-relevant distinctions.[S2–S4] Responsibility OS denotes a governance operating layer, not a computer OS. Their proofs do not automatically certify this new implementation.

### 5. Bounded reference profiles

RP-0.3 compares synthetic cold-chain thresholds and synthetic cyber-operation restrictions using the same kernel. Required parties and approved policy digests are trusted harness inputs. Preserve policy identity, source, interpretation, version and rule-specific results. Supported operators are `between/lte/gte/eq/one_of`; unsupported operators and incompatible types/units yield unknown. Temperature uses integer milli-degrees C. Only the explicitly declared `centi-C-v1` exact conversion is supported; other adapters fail closed to unknown.

Permission binds the operation, participants, rules, evidence and approval/authority context. Current logical time is excluded from the digest and checked against a half-open ten-tick permit interval. Evidence may be zero to twenty ticks old. Inventory order alone is normalized; event order and rule changes are not erased. A receiver subprocess rechecks inside the same SQLite transaction as the simulated effect and audit record.

`assessment.authorization` is the current assessment of eligibility for authorization, not itself the retained scoped grant. Execution must also validate the saved grant. Reassessing changed conditions as eligible does not make an older grant reusable.

Each of the 30 policy cases uses a fresh database and one operation. The retained RP-0.2 profile covers 41 execution cases across notification/configuration, including repeated and concurrent requests, process termination, lost replies, recovery and outcome mismatch. Effects, receipts and audit records share a transaction. Retry after rollback relies on that local boundary, not a general inference from missing evidence. Switches and authorized exception overrides are unsupported and rejected.

Trusted components include the operating system, runtime, SQLite, local administrator, harness inputs, database and clock. Organizational authentication, signatures, real-world facts, compromised administrators, actual system-wide bypass resistance, external API effects, distributed revocation, cryptographic security, performance and regulatory conformity remain outside the profile.

### 6. Evidence and claims

New policy evidence uses `haac-policy-evidence/0.3`; retained execution evidence keeps `haac-reference-evidence/0.2` with framework version 0.3.0. Both reference all eight release files. Keep source bytes, source requirement versions, scope, verdicts, observations, histories and outstanding reviews. A digest alone is neither an identity credential nor proof of fact.

A separate program recalculates results without importing the executor. The programs share the published specification and author, not organizational independence. Whole-framework conformity needs applicable R01–R12 design reviews and actual-system evidence in addition to reference tests. External products need actual-effect adapters and trust/authority review; fabricated matching records are not certification.

Map external requirements through source/version/section → reviewed interpretation → R identifier → T/P test → evidence → non-mechanized remainder. Such mappings are not complete compliance with OECD, AISI, legislation or a sector standard. No public authority's endorsement or global consensus is claimed.

## References / 参照

- [S1 HAAP public technical overview](https://hiroshima-ai-assurance.com/protocol), checked 2026-11-03.
- [S2 Responsibility Information Kernel](https://github.com/GhostDriftTheory/responsibility-info-kernel), README checked 2026-11-03.
- [S3 Responsibility OS Kernel](https://github.com/GhostDriftTheory/responsibility-os-kernel), retained reference from v0.2.
- [S4 ADIC AI Assurance](https://github.com/GhostDriftTheory/adic-ai-assurance-lean), retained reference from v0.2.

New requirements and reference profiles are proposals of this release. Prior repositories were not rerun as part of this revision. Sources for other prior experiments and external frameworks appear in README.md.
