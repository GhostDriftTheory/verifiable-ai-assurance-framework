/-
HAAC AI Assurance Framework — policy-independent assurance kernel.
Only the Lean standard library. This is a model, not a proof of Python/SQLite.
The semantic adequacy of a policy checker and its evidence remain premises.
-/
import Std

namespace HAAC

inductive Verdict where
  | satisfied | violated | unknown
  deriving DecidableEq, Repr

open Verdict

def meet : Verdict → Verdict → Verdict
  | violated, _ => violated
  | _, violated => violated
  | satisfied, satisfied => satisfied
  | _, _ => unknown

/-- Internal conjunction. Public summary rejects an empty requirement set. -/
def fold : List Verdict → Verdict
  | [] => satisfied
  | x :: xs => meet x (fold xs)

def summary : List Verdict → Verdict
  | [] => unknown
  | x :: xs => meet x (fold xs)

def authorize (xs : List Verdict) (approved active bound : Bool) : Bool :=
  decide (summary xs = satisfied) && approved && active && bound

/-- Stable identities and individual outcomes are retained, not only a score. -/
def report {I E : Type} (scope : List I) (check : I → E → Verdict) (e : E) :=
  scope.map (fun i => (i, check i e))

theorem meet_satisfied_iff (a b : Verdict) :
    meet a b = satisfied ↔ a = satisfied ∧ b = satisfied := by
  cases a <;> cases b <;> simp [meet]

theorem meet_comm (a b : Verdict) : meet a b = meet b a := by
  cases a <;> cases b <;> rfl

theorem meet_assoc (a b c : Verdict) :
    meet (meet a b) c = meet a (meet b c) := by
  cases a <;> cases b <;> cases c <;> rfl

theorem fold_satisfied_iff (xs : List Verdict) :
    fold xs = satisfied ↔ ∀ x ∈ xs, x = satisfied := by
  induction xs with
  | nil => simp [fold]
  | cons a xs ih => simp [fold, meet_satisfied_iff, ih]

theorem summary_satisfied_iff (xs : List Verdict) :
    summary xs = satisfied ↔ xs ≠ [] ∧ ∀ x ∈ xs, x = satisfied := by
  cases xs with
  | nil => simp [summary]
  | cons a xs => simp [summary, meet_satisfied_iff, fold_satisfied_iff]

theorem empty_not_satisfied : summary [] ≠ satisfied := by decide

theorem required_violation_blocks (xs : List Verdict) (h : violated ∈ xs) :
    summary xs ≠ satisfied := by
  intro hs
  have hf := (summary_satisfied_iff xs).mp hs
  have bad := hf.2 violated h
  cases bad

theorem required_unknown_blocks (xs : List Verdict) (h : unknown ∈ xs) :
    summary xs ≠ satisfied := by
  intro hs
  have hf := (summary_satisfied_iff xs).mp hs
  have bad := hf.2 unknown h
  cases bad

theorem authorize_iff (xs : List Verdict) (a r b : Bool) :
    authorize xs a r b = true ↔
    summary xs = satisfied ∧ a = true ∧ r = true ∧ b = true := by
  simp [authorize, Bool.and_eq_true, and_assoc]

theorem authorization_requires_every_rule (xs : List Verdict) (a r b : Bool)
    (h : authorize xs a r b = true) : ∀ x ∈ xs, x = satisfied := by
  have hs : summary xs = satisfied := ((authorize_iff xs a r b).mp h).1
  exact ((summary_satisfied_iff xs).mp hs).2

theorem no_approval_no_authorization (xs : List Verdict) (r b : Bool) :
    authorize xs false r b = false := by simp [authorize]

theorem revoked_no_authorization (xs : List Verdict) (a b : Bool) :
    authorize xs a false b = false := by simp [authorize]

theorem changed_binding_no_authorization (xs : List Verdict) (a r : Bool) :
    authorize xs a r false = false := by simp [authorize]

/-- Adding obligations cannot make a failed nonempty scope succeed. -/
theorem extension_cannot_erase_failure (xs ys : List Verdict)
    (hne : xs ≠ []) (hfail : summary xs ≠ satisfied) :
    summary (xs ++ ys) ≠ satisfied := by
  intro hs
  have hall := ((summary_satisfied_iff (xs ++ ys)).mp hs).2
  apply hfail
  apply (summary_satisfied_iff xs).mpr
  constructor
  · exact hne
  · intro x hx
    exact hall x (List.mem_append.mpr (Or.inl hx))

/-- Soundness is conditional on each domain checker's soundness. -/
theorem joint_soundness {I E : Type} (scope : List I)
    (check : I → E → Verdict) (property : I → E → Prop)
    (sound : ∀ i e, check i e = satisfied → property i e) (e : E)
    (h : summary (scope.map (fun i => check i e)) = satisfied) :
    ∀ i ∈ scope, property i e := by
  intro i hi
  apply sound i e
  exact ((summary_satisfied_iff _).mp h).2 _ (List.mem_map.mpr ⟨i, hi, rfl⟩)

/-- Adapters may change representation only if each relevant result is preserved. -/
theorem semantic_adapter_preserves_report {I E F : Type} (scope : List I)
    (c : I → E → Verdict) (d : I → F → Verdict) (adapt : E → F) (e : E)
    (preserves : ∀ i, c i e = d i (adapt e)) :
    report scope c e = report scope d (adapt e) := by
  induction scope with
  | nil => rfl
  | cons i rest ih =>
    change (i, c i e) :: report rest c e = (i, d i (adapt e)) :: report rest d (adapt e)
    rw [preserves i, ih]

/-- An aggregate failure does not identify whose policy failed. -/
theorem aggregation_loses_party_difference :
    summary [satisfied, violated] = summary [violated, satisfied] ∧
    ([(1, satisfied), (2, violated)] : List (Nat × Verdict)) ≠
      [(1, violated), (2, satisfied)] := by decide

/-- Same evidence can satisfy one legitimate rule and violate another. -/
def upperBound (limit : Nat) (value : Option Nat) : Verdict :=
  match value with
  | none => unknown
  | some x => if x ≤ limit then satisfied else violated

theorem different_rules_different_results :
    upperBound 8000 (some 7000) = satisfied ∧
    upperBound 6000 (some 7000) = violated := by decide

theorem compatible_rules_can_execute :
    authorize [upperBound 8000 (some 5000), upperBound 6000 (some 5000)]
      true true true = true := by decide

theorem disagreement_blocks_joint_execution :
    authorize [upperBound 8000 (some 7000), upperBound 6000 (some 7000)]
      true true true = false := by decide

theorem unknown_not_silently_accepted :
    authorize [upperBound 8000 none, upperBound 6000 none]
      true true true = false := by decide

-- A singleton decision is not authorization for a different joint scope.
theorem single_party_not_joint_permission :
    authorize [satisfied] true true true = true ∧
    authorize [satisfied, violated] true true true = false := by decide

#print axioms meet_satisfied_iff
#print axioms meet_comm
#print axioms meet_assoc
#print axioms fold_satisfied_iff
#print axioms summary_satisfied_iff
#print axioms empty_not_satisfied
#print axioms required_violation_blocks
#print axioms required_unknown_blocks
#print axioms authorize_iff
#print axioms authorization_requires_every_rule
#print axioms no_approval_no_authorization
#print axioms revoked_no_authorization
#print axioms changed_binding_no_authorization
#print axioms extension_cannot_erase_failure
#print axioms joint_soundness
#print axioms semantic_adapter_preserves_report
#print axioms aggregation_loses_party_difference
#print axioms different_rules_different_results
#print axioms compatible_rules_can_execute
#print axioms disagreement_blocks_joint_execution
#print axioms unknown_not_silently_accepted
#print axioms single_party_not_joint_permission
end HAAC
