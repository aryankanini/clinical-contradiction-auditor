# concept-validation

Composite agent: brainstorm candidate concepts, select one, build a throwaway
prototype, then hand off into `technical-discovery`. Unlike a bare `ReadWorkflow`
orchestrator, this one is gate-ENFORCED server-side: `GetNextRunStep` refuses
to return a directive while a gate is pending, so the steps below cannot be
skipped by proceeding anyway.

## Step 0 — resolve paths and policy

```
/artifact-resolver brainstorm
/artifact-resolver prototype
```

Build `pathContext` from the two results:

```json
{
  "brainstorm": {"path": "<propelFilePath>", "content_type": "<contentType>", "mcp_type": "<mcpType>"},
  "prototype":  {"path": "<propelFilePath>", "content_type": "<contentType>", "mcp_type": "<mcpType>"}
}
```

Read `.propel/gate-policy.json` and pass its raw content as `gatePolicyJson`
on `StartWorkflowRun` in Step 1 -- that is the ONLY call that needs it. Gate
resolution happens once, at run start; the server freezes the result into the
run and never needs the policy re-supplied afterward. Passing this large JSON
blob as an inline string argument is already the single riskiest parameter in
this whole flow -- only require it where it's actually used.

## Step 1 — start the run

Call MCP tool:
```
StartWorkflowRun(workflow="concept-validation", version="1.0", project=<projectName from project-config.json>,
                  inputs={"scope": <user's scope>}, rawInvocation=<the literal command as typed>,
                  pathContext=<from Step 0>, aiSignal=<true if scope carries [AI-CANDIDATE]/[HYBRID]>,
                  gatePolicyJson=<from Step 0>)
```

Update the ToDo list from the returned `directive`. Report the `gatePlan` to
the user before doing any work — if a row carries a `note`, their `--approve=`
request was clamped by a mandate; say so and give the `reason`. Never let them
discover a gate by hitting it.

## Step 2 — execute S1 inline

1. `GetNextRunStep(project, runId)` → fetch directive
2. Execute brainstorm work inline (generate candidates, ask clarifications as needed)
3. `CompleteRunStep(project, runId, stepId="S1", envelope={artifacts, candidates, openQuestions})`

## Step 3 — S1 gate (selection)

If `status: "gate_pending"`, render via `AskUserQuestion` (probe-user contract).
Map candidates to options (top 3 + Custom if >3 produced).
```
SubmitGateDecision(project, runId, stepId="S1", decision="select", selection=[<id>])
```
Reject loops back to S1.

## Step 4 — execute S2 inline

1. `GetNextRunStep(project, runId)` → fetch directive (includes S1 context: selected candidate)
2. Execute prototype build inline
3. `CompleteRunStep(project, runId, stepId="S2", envelope={artifacts, facts: {eval.verdict}})`

## Step 5 — S2 gate (approval)

If `status: "gate_pending"`, render artifact via `AskUserQuestion`.
- `PASS` verdict auto-approves, complete immediately
- Any other verdict raises gate; user can approve/reject/abort

## Step 5 — post-approval hook

If the response from Step 2 or Step 4 carries a `hook` object, run:
```
AUTO_MERGE=<hook.autoMerge> BASE=<hook.base> \
  bash .propel/hooks/post-approval/post-approval.sh <hook.args...> <hook.artifacts...>
```
(use `post-approval.ps1` on Windows). Its JSON stdout is the `mergeReceipt` —
only needed if a subsequent `SubmitGateDecision` call for the same step
requires it.

## Step 6 — handoff

On `status: "complete"`, the response carries `handoffTo: "technical-discovery"`.
Tell the user the selected concept is ready and offer to start `technical-discovery`
(its S1 = `/create-spec`, which will consult the approved `prototype` and
`brainstorm` artifacts per `spec`'s `references` in `project-config.json`).
`technical-discovery` is itself gate-enforced -- see `orchestrators/technical-discovery.md`
-- so starting it means calling `StartWorkflowRun(workflow="technical-discovery", ...)`,
not the bare `ReadWorkflow` some older orchestrators still use.

## Invariants

- Never call `SubmitGateDecision` without an explicit user decision.
- Never pass an `--approve=` value the user did not type.
- Never call `GetNextRunStep` as a way to skip past a pending gate — it will
  refuse and return an error naming the step that needs a decision.
- `propel-concept-validation-s1`/`propel-concept-validation-s2` subagents must never call
  `SubmitGateDecision` — they have no interactive turn with the user, so a
  gate raised inside a subagent is unsatisfiable. They stop at
  `CompleteRunStep` and return its result; gate handling stays with the
  parent session that invoked them.
