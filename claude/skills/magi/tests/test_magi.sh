#!/usr/bin/env bash
# MAGI Consensus Engine - Test Suite
# Tests skill structure, decision table logic, and state file format

set -uo pipefail

PASS=0
FAIL=0
SKILL_DIR="${HOME}/.claude/skills/magi"

pass() { echo "  ✅ $1"; PASS=$((PASS + 1)); }
fail() { echo "  ❌ $1"; FAIL=$((FAIL + 1)); }
header() { echo ""; echo "=== $1 ==="; }

# ─── Test 1: Skill File Structure ───
header "Skill File Structure"

[[ -f "$SKILL_DIR/SKILL.md" ]] && pass "SKILL.md exists" || fail "SKILL.md missing"
[[ -f "$SKILL_DIR/references/flow.md" ]] && pass "flow.md exists" || fail "flow.md missing"
[[ -f "$SKILL_DIR/references/vote-prompt.md" ]] && pass "vote-prompt.md exists" || fail "vote-prompt.md missing"

# Check frontmatter
grep -q '^name: magi' "$SKILL_DIR/SKILL.md" && pass "SKILL.md has correct name" || fail "SKILL.md missing name frontmatter"
grep -q 'MELCHIOR' "$SKILL_DIR/SKILL.md" && pass "SKILL.md references MELCHIOR" || fail "SKILL.md missing MELCHIOR"
grep -q 'BALTHASAR' "$SKILL_DIR/SKILL.md" && pass "SKILL.md references BALTHASAR" || fail "SKILL.md missing BALTHASAR"
grep -q 'CASPER' "$SKILL_DIR/SKILL.md" && pass "SKILL.md references CASPER" || fail "SKILL.md missing CASPER"

# ─── Test 2: Flow.md Content ───
header "Flow.md Content Validation"

FLOW="$SKILL_DIR/references/flow.md"
grep -q 'DECISION TABLE' "$FLOW" && pass "Decision table present" || fail "Decision table missing"
grep -q 'PATTERN_BLUE' "$FLOW" && pass "PATTERN_BLUE state defined" || fail "PATTERN_BLUE missing"
grep -q 'SYNCHRONIZED' "$FLOW" && pass "SYNCHRONIZED state defined" || fail "SYNCHRONIZED missing"
grep -q 'DISSENT_DETECTED' "$FLOW" && pass "DISSENT_DETECTED state defined" || fail "DISSENT_DETECTED missing"
grep -q 'INCONCLUSIVE' "$FLOW" && pass "INCONCLUSIVE state defined" || fail "INCONCLUSIVE missing"
grep -q 'DEGRADED' "$FLOW" && pass "DEGRADED mode defined" || fail "DEGRADED missing"
grep -q 'ABSTAIN' "$FLOW" && pass "ABSTAIN handling defined" || fail "ABSTAIN missing"
grep -q 'magi_state.json' "$FLOW" && pass "State file referenced" || fail "State file not referenced"
grep -q 'apocrypha.jsonl' "$FLOW" && pass "Dissent log referenced" || fail "Dissent log not referenced"
grep -q 'pending_tasks' "$FLOW" && pass "pending_tasks in state schema" || fail "pending_tasks missing from schema"
grep -q 'CCB_REQ_ID' "$FLOW" && pass "Hook correlation via CCB_REQ_ID" || fail "CCB_REQ_ID correlation missing"
grep -q 'END TURN' "$FLOW" && pass "Async Guardrail documented" || fail "Async Guardrail not documented"
grep -q 'risk_mass.*0.7' "$FLOW" && pass "Risk mass threshold 0.7 defined" || fail "Threshold missing"

# ─── Test 3: Vote Prompt Template ───
header "Vote Prompt Template Validation"

VOTE="$SKILL_DIR/references/vote-prompt.md"
grep -q 'BALTHASAR-2' "$VOTE" && pass "BALTHASAR-2 preamble present" || fail "BALTHASAR-2 preamble missing"
grep -q 'CASPER-3' "$VOTE" && pass "CASPER-3 preamble present" || fail "CASPER-3 preamble missing"
grep -q 'MELCHIOR-1' "$VOTE" && pass "MELCHIOR-1 reference present" || fail "MELCHIOR-1 reference missing"
grep -q '"vote"' "$VOTE" && pass "Vote field in JSON schema" || fail "Vote field missing"
grep -q '"risk_mass"' "$VOTE" && pass "risk_mass field in JSON schema" || fail "risk_mass field missing"
grep -q '"reasoning"' "$VOTE" && pass "reasoning field in JSON schema" || fail "reasoning field missing"
grep -q 'MAGI_VOTE_REQ' "$VOTE" && pass "Request header documented" || fail "Request header missing"
grep -q 'MAGI_VOTE_RESULT' "$VOTE" && pass "Response header documented" || fail "Response header missing"
grep -q 'ABSTAIN' "$VOTE" && pass "ABSTAIN fallback documented" || fail "ABSTAIN fallback missing"

# ─── Test 4: Decision Table Scenarios (Logic Validation) ───
header "Decision Table Scenario Validation"

# Scenario A: All APPROVE
grep -q 'All systems vote == APPROVE' "$FLOW" && pass "Scenario A: All APPROVE -> SYNCHRONIZED" || fail "Scenario A missing"

# Scenario B: One VETO
grep -q 'Any system vote == VETO' "$FLOW" && pass "Scenario B: Any VETO -> PATTERN_BLUE" || fail "Scenario B missing"

# Scenario C: DEADLOCK (mixed, no veto)
grep -q 'Mixed votes but no VETO' "$FLOW" && pass "Scenario C: Mixed -> DISSENT_DETECTED" || fail "Scenario C missing"

# Scenario D: ABSTAIN + remaining unanimous
grep -q 'ABSTAIN, remaining unanimous' "$FLOW" && pass "Scenario D: ABSTAIN+unanimous -> DEGRADED" || fail "Scenario D missing"

# Scenario E: ABSTAIN + remaining split
grep -q 'ABSTAIN, remaining split' "$FLOW" && pass "Scenario E: ABSTAIN+split -> INCONCLUSIVE" || fail "Scenario E missing"

# Scenario F: Multiple ABSTAIN
grep -q '2+ systems ABSTAIN' "$FLOW" && pass "Scenario F: 2+ ABSTAIN -> INCONCLUSIVE" || fail "Scenario F missing"

# ─── Test 5: State Machine Completeness ───
header "State Machine Completeness"

for state in IDLE EVALUATION MELCHIOR_VOTED WAITING_VOTES COLLECTING AGGREGATION DEGRADED LOG_AND_RETURN ESCALATE_TO_EMPEROR; do
  grep -q "$state" "$FLOW" && pass "State: $state defined" || fail "State: $state missing"
done

# ─── Summary ───
header "SUMMARY"
TOTAL=$((PASS + FAIL))
echo "  Total: $TOTAL tests"
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo ""

if [[ $FAIL -eq 0 ]]; then
  echo "🟢 ALL TESTS PASSED"
  exit 0
else
  echo "🔴 $FAIL TESTS FAILED"
  exit 1
fi
