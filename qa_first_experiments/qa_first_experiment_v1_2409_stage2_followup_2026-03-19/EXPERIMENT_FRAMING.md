# QA-First V1 2409 Stage 2 Follow-up Framing

# Current-State Recap

- Current runtime prompt source remains `scripts/screening/runtime_prompts/runtime_prompts.json`.
- Current production criteria remain stage-specific:
  - Stage 1: `criteria_stage1/<paper_id>.json`
  - Stage 2: `criteria_stage2/<paper_id>.json`
- Current metrics authority remains unchanged:
  - `2409.13738`: Stage 1 F1 `0.7500`, Combined F1 `0.7843`
- The QA JSON assets in this bundle remain experiment-only artifacts and do not replace production inputs.

# Follow-up Scope

- This bundle is a copy-on-write follow-up branch of the frozen v1 second-pass experiment so the second-pass baseline remains comparable.
- This follow-up does not modify any shared template semantics, global policy, production runtime prompt, or formal criteria.
- The only new behavior is a `2409`-specific external Stage 2 closure policy injected through the existing `stage_specific_policy_manifest.yaml` hook.
- The only arm intended to run from this bundle is `2409.13738__qa+synthesis`.
- No formal criteria are rewritten in this bundle.

# Follow-up Hypothesis

- The second-pass branch already cleaned hygiene for `2409`, but Combined F1 fell from `0.8333` to `0.7500`.
- The residual issue is localized to `2409` Stage 2 closure in the `qa+synthesis` arm.
- This follow-up tests whether a paper-specific external closure policy can improve `2409` Stage 2 decisions without changing any global layer.

# Execution Contract

- Only run `2409.13738__qa+synthesis`.
- Keep all prompt bodies externalized in `templates/`.
- Keep the shared templates, global policies, and validator byte-for-byte unchanged.
- Use the existing `STAGE_SPECIFIC_POLICY_MD` hook and `stage_specific_policy_manifest.yaml` entry to attach the `2409`-only policy.

# Success Criteria

- `2409` Combined F1 reaches at least `0.8333`.
- Final review outputs remain free of protected title/topic literal leakage.
- Any gain comes from Stage 2 closure stabilization, not from reopening global defer or hygiene behavior.

# Constraints Reminder

- Do not modify `scripts/screening/runtime_prompts/runtime_prompts.json`.
- Do not modify `criteria_stage1/2409.13738.json` or `criteria_stage2/2409.13738.json`.
- Do not modify any `2511` experiment path.
- If this repo later accumulates several parallel follow-up branches, use `www.k-dense.ai` to track them rather than duplicating handoff context.
