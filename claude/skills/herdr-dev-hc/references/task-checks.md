# Task-Specific Checks

Loaded from Phase 1 step 4 (**Task-specific checks**). Select only the
sections the requirement or the touched code actually triggers; never paste
the whole file into a dispatch.

- **Brief** lines go into the Requirement Brief. They record source-backed
  commitments; they do not authorize new features. A missing product decision
  is a Phase 1 step 6 question, not something main invents.
- **Worker** lines go into the dev brief and follow the existing slice-by-slice
  RED/GREEN contract.
- **Reviewer** lines go into the review brief and use the existing evidence,
  severity and scope rules — including the six-part security-finding gate.
  None of them is a separate release gate.

No universal numeric budgets (latency, memory, sample size, coverage %) come
from this file. A number is a requirement only when the source requirement
states it.

---

## Async UI

Trigger: new or changed UI that loads, submits or lists data.

- **Brief:** name component inputs, owned state, and the observable
  loading / empty / error / normal behavior; mark inapplicable states.
- **Worker:** exercise the applicable state transitions at the declared test
  seam, plus keyboard/semantic control behavior and long content / overflow.
  Check viewport boundaries only when a browser/E2E seam exists; otherwise
  note it as a limitation in the report.
- **Reviewer:** new animations and transitions honor
  `prefers-reduced-motion` and don't block the interaction path.
- **Reviewer:** where the project already has design tokens / a theme scale /
  a UI kit, new code uses them instead of literal colors, spacing or a
  re-built primitive. No tokens in the project → not a finding.

## API compatibility and load

Trigger: changed request/response contract, or load testing in scope.

- **Worker:** compare touched request/response schemas, status codes and
  error bodies with the existing contract; call out consumer-breaking
  changes explicitly.
- **Worker:** load testing only when the approved scope asks for it — named
  safe environment and workload; record p50/p95/p99, achieved load, error
  types, the bottleneck, and recovery after overload.

## Performance evidence

Trigger: the requirement makes a performance claim or sets a budget.

- **Worker:** record the command/tool, workload/data size, environment, and
  matched before/after measurements against the stated budget. No comparable
  baseline → say improvement was not established.

## Caching and outbound clients

Trigger: a new cache layer, or a new outbound HTTP/DB client or pool.

- **Reviewer:** the new client/pool sets explicit connect/request timeouts
  and a connection limit (or inherits a project default that does).
- **Reviewer:** many hot keys created with one identical TTL → flag the
  stampede risk only with the concrete keys and expiry path.

## Failing-test triage

Trigger: an existing test fails during the task.

- **Worker:** before changing the test, classify the cause — environment /
  setup, approved behavior change, test brittleness, or production defect.
  Keep the intended assertion; explain any changed expectation against the
  requirement. A test file outside `owns` is not yours to edit: use
  `may_touch_with_reason` or report BLOCKED.
- **Worker:** intermittent / order-dependent failures → compare isolated vs.
  suite runs; inspect shared state, clocks, async completion. Never go GREEN
  by adding sleeps or weakening assertions.

## Cleanup candidates

Trigger: Phase 3 quality review; used only through the Phase 4.5 tuning round.

All findings here are 🟡 tuning suggestions, never FIX.

- **Reviewer:** in the changed code, flag dead branches/imports,
  signature-restating comments and behaviorless wrappers — only where removal
  demonstrably preserves behavior. Keep boundary validation, real error
  handling, audit logs and public contracts.
- **Reviewer:** flag tests that only assert framework behavior or mock setup,
  and duplicates guarding the same behavior; name the coverage that remains.

## Additional security surfaces

Trigger: changed cookie-authenticated mutations, auth endpoints, or XML parsing
of attacker-controlled input.

- **Reviewer:** cookie-auth mutations → trace the effective CSRF/origin
  defense; auth endpoints → trace throttling.
- **Reviewer:** attacker-controlled XML → check external-entity / network /
  file resolution settings and any reachable disclosure or SSRF path.
- An old dependency is not a finding; a CVE claim needs version-specific
  evidence.

## Personal data

Trigger: account deletion / data purge, new PII fields, or new third-party
tracking / analytics scripts.

- **Brief:** record what deletion means for this feature (hard delete,
  anonymize, retention period) — a product decision, so ask if unstated.
- **Worker:** test that deletion/purge actually removes or anonymizes the
  stored PII, not just a UI flag.
- **Reviewer:** new third-party scripts/SDKs don't send events before the
  project's existing consent mechanism allows it.

## Paid AI integrations

Trigger: a product feature calls a paid model provider. (Not herdr's own
advisory Jev calls.)

- **Brief:** record the request size / token ceiling and per-user usage budget;
  unresolved limits are requirement questions.
- **Worker:** enforce those limits; log model, token usage and latency without
  prompts, secrets or identifying user data by default.
- **Worker:** test timeout / rate-limit behavior and the user-visible error.
  Any fallback keeps the approved contract and data policy.
- **Worker:** changed prompt/model behavior → keep the prompt in a tracked
  file and add a small representative eval set with expected outcomes;
  record the results in the report.
- **Reviewer:** changed prompt/model behavior → check the tracked prompt and
  the eval results. Evals supplement RED/GREEN tests, they don't replace them.

## Deployment configuration

Trigger: changed image builds or production manifests.

- **Reviewer:** trace secret inputs through build steps and copied files;
  credentials must not persist in image layers or build output.
- **Reviewer:** production manifests pin an immutable version/digest, not
  `latest` or another floating tag, per the project's release policy.

## Mobile interactions

Trigger: mobile performance, battery or gesture changes, or optimistic
network mutations.

- **Brief:** name the target device/OS and the measurement or interaction
  check; simulator-only evidence is labeled as a limitation.
- **Worker:** optimistic mutations → test rollback on failure; confirm
  accessibility labels and text-size/layout behavior survive the change.

## Feature flags and experiments

Trigger: the requirement introduces a flag or an experiment.

- **Brief:** hypothesis, primary metric, guardrail metrics, audience /
  allocation, evaluation window, decision rule.
- **Worker:** test flag-on, flag-off and the stop/rollback path; record who
  removes the flag and when.
- **Reviewer:** keep implementation evidence apart from experiment results.
  PASS means the code is reviewed, not that the experiment has run or won.
