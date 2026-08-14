# discovery-lite

Lightweight, gate-enforced on-ramp into `technical-discovery`: brainstorm
ideas, pause for approval, then hand off. One step, one gate -- the smallest
gate-enforced workflow in the catalog. Use this instead of
`concept-validation` when there's no prototyping phase wanted, just a
reviewed brainstorm before full discovery.

*Formerly `discovery-mini`, the catalog's ungated comparison baseline
("no approval gate — baseline for gate comparison"). Renamed and upgraded to
gate-enforced alongside the `technical-discovery` rollout. `discovery-mini-gated`
is unrelated and still exists separately, unchanged, as a client-trusted demo
of the old declarative-gate pattern -- not migrated to the new tools.*

## Step 0 — resolve paths and policy

```
/artifact-resolver brainstorm
```

Build `pathContext = {"brainstorm": {"path": ..., "content_type": ..., "mcp_type": ...}}`.
Read `.propel/gate-policy.json` and pass its raw content as `gatePolicyJson`
on `StartWorkflowRun` below -- `SubmitGateDecision` doesn't need it.

## Step 1 — start the run

```
StartWorkflowRun(workflow="discovery-lite", version="1.0", project=<projectName>,
                  inputs={"scope": <user's scope>}, rawInvocation=<literal command>,
                  pathContext=<from Step 0>, aiSignal=<...>, gatePolicyJson=<from Step 0>)
```

Report the `gatePlan`. S1's gate resolves to `always` via the manifest default
(no `condition` field) -- it is not separately policy-mandated the way
`technical-discovery`'s steps are, so an `--approve=none` request WILL lower
it unless you add a matching rule to `gate-policy.json`. Decide deliberately
whether that's acceptable for this workflow before relying on the default.

## Step 2 — execute S1 inline

1. `GetNextRunStep(project, runId)` → fetch directive
2. Execute brainstorm work inline (ask clarifications via AskUserQuestion as needed)
3. `CompleteRunStep(project, runId, stepId="S1", artifact=<brainstorm>)`

## Step 3 — S1 gate decision

If `status: "gate_pending"`, render artifact via `AskUserQuestion` (probe-user contract).
- Approve: `SubmitGateDecision(approve)` → handoff
- Reject: `SubmitGateDecision(reject, feedback=<reason>)` → loop to Step 2
- Abort: `SubmitGateDecision(abort)` → exit

## Handoff

On `status: "complete"`, hand off into `technical-discovery` per the
response's `handoffTo`.

## Invariants

- Never call `SubmitGateDecision` without an explicit user decision, or with
  empty `feedback` on `reject`.
- `propel-discovery-lite-s1` must never call `SubmitGateDecision` itself.
