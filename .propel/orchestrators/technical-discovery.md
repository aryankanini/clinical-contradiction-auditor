# technical-discovery

Gate-enforced technical discovery: requirements, architecture, optional system
modeling, and UI specification (Figma + wireframes, when the spec is UI-relevant).
Replaces the old bare `discovery-agent` -- every phase now requires human
approval, server-enforced, not just client convention.

## Step 0 — resolve paths and policy

```
/artifact-resolver spec
/artifact-resolver design
/artifact-resolver model
/artifact-resolver figma_spec
/artifact-resolver wireframe
```

Build `pathContext` from all five results (same `{path, content_type, mcp_type}`
shape as `concept-validation.md`). Read `.propel/gate-policy.json` and pass its
raw content as `gatePolicyJson` on `StartWorkflowRun` in Step 1 only --
`CompleteRunStep` and `SubmitGateDecision` don't need it. Gate resolution
happens once, at run start, and gets frozen into the run.

**Note the key is `design`, not `architecture`** -- the produced artifact for
S2 (design-architecture) resolves to the `design` key in `project-config.json`.
An earlier version of this workflow's manifest declared `architecture` and
would have hard-failed `BindRunPaths`; confirm the version you're running
against declares `produces: ["design"]` for S2.

## Step 1 — start the run

```
StartWorkflowRun(workflow="technical-discovery", version="1.0", project=<projectName>,
                  inputs={"scope": <user's scope or reference to the approved
                  concept-validation artifacts>}, rawInvocation=<literal command>,
                  pathContext=<from Step 0>, aiSignal=<...>, gatePolicyJson=<from Step 0>)
```

Report the `gatePlan` before doing any work. **S1 (create-spec) and S2
(design-architecture) are policy-MANDATED** via `gate-policy.json`'s
`prompt`-scoped rules -- an `--approve=` request cannot lower those two, and
the `gatePlan` will show `source: "policy-mandate"` on their rows regardless
of what was requested. S3–S5 resolve to `always` via the manifest default
only, which `--approve=` *can* lower. Tell the user this distinction up
front, not just "everything is mandated" -- a `--approve=none` request will
be partially honoured here, and discovering that mid-run is worse than
hearing it in the gate plan summary.

## Steps 2–11 — execute S1-S5 inline

For each step (S1-S5):

1. `GetNextRunStep(project, runId)` → fetch directive (includes previous step context)
2. Execute step work inline (ask clarifications via AskUserQuestion as needed)
3. `CompleteRunStep(project, runId, stepId="SN", artifact=<result>)`

If `status: "gate_pending"`, render via `AskUserQuestion` (probe-user contract):
- Approve: `SubmitGateDecision(approve)` → proceed to next step
- Reject: `SubmitGateDecision(reject, feedback=<reason>)` → loop to step (feedback required)
- Abort: `SubmitGateDecision(abort)` → exit

## S3 is conditionally skipped, S4/S5 are not (yet)

- **S3 (design-model)** honors `--design-model=false` server-side -- pass it
  through `rawInvocation` and the engine will skip S3 and its gate entirely.
- **S4 (create-figma-spec) and S5 (generate-wireframe)** declare a
  `content_scan` skip condition ("spec.md contains UI keywords") in the
  manifest, but **the engine does not evaluate `content_scan` conditions** --
  they always run and always gate, UI-relevant scope or not. This is a known,
  documented server-side limitation, not a bug in this orchestrator. If the
  scope is clearly non-UI, tell the user before S4's gate fires so the
  approval prompt for a Figma spec doesn't look like a mistake -- they can
  still `reject` (with feedback) to skip past it, since `on_reject` for both
  steps loops back rather than hard-failing.

## Post-approval hooks

Same as `concept-validation.md` Step 5: if a response carries a `hook` object,
run `.propel/hooks/post-approval/post-approval.sh` (or `.ps1`) and pass its
JSON stdout as `mergeReceipt` on the next call for that step. The server will
now refuse to advance past a step whose hook receipt is missing -- confirmed
enforced as of this version, this is not merely advisory.

## Handoff

On `status: "complete"`, hand off into `backlog-agent` per the response's
`handoffTo`.

## Invariants

- Never call `SubmitGateDecision` without an explicit user decision, and
  never with empty `feedback` on a `reject`.
- Never pass an `--approve=` value the user did not type -- and note that for
  this workflow specifically, it only partially matters: S1/S2 are
  policy-mandated and cannot be lowered regardless, but S3–S5 rely on the
  manifest default and CAN be lowered by an `--approve=` request.
- `propel-technical-discovery-s1..s5` subagents must never call
  `SubmitGateDecision` -- they stop at `CompleteRunStep` and return its
  result. Gate handling stays with the parent session.
