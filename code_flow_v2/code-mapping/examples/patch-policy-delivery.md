# Patch Policy: rebuild and deliver the saved command suite

The current publication contains 27 fresh command captures, including the PushT
VQ-BeT baseline. Use the suite manifest to update these existing URLs together.
The general publishing procedure is [PUBLISHING.md](../../PUBLISHING.md).

## Rebuild and audit saved evidence

```bash
cd /mnt/sata1/code/robo/patch_policy
python docs/code_mapping/suite/render_suite.py \
  --plan docs/code_mapping/suite/publication_plan_rerun.json
python docs/code_mapping/suite/verify_call_evidence.py \
  --plan docs/code_mapping/suite/publication_plan_rerun.json \
  --output docs/code_mapping/suite/call-evidence-rerun.json
```

The plan selects immutable raw evidence under
`docs/code_mapping/suite/runs/<id>/trace/`. The project renderer adapts primitives,
array summaries, receivers, yielded values and execution contexts. A stock
`codetrace.py --rebuild` bypasses this adapter. The PushT diffusion run's
`innovation.json` retains the existing reviewed green frames; its ranges are
validated against the freshly rendered source cards. Keep these annotations
separate from observed execution coverage.

Preserve `callgraph.json`, `coverage.json` and `run.json`. A rebuild cannot recover
call events absent from an older capture. When fresh execution is requested,
create distinct run IDs and output directories using the project launcher and
job manifest; record real prerequisite failures. Do not overwrite prior runs.
The scripts, datasets, checkpoints and raw traces live with the target project;
cloning the menu retrieves the reusable pack and published pages, not those
machine-specific resources.

## Replace the existing grouped pages

After checking the menu checkout and updating it from `origin/main`, run from
the Patch Policy repository:

```bash
python docs/code_mapping/suite/publish_suite.py \
  --plan docs/code_mapping/suite/publication_plan_rerun.json \
  --menu /mnt/sata1/andres/menuCodeMapping \
  --catalog docs/code_mapping/suite/publication_catalog_rerun.json
python docs/code_mapping/suite/make_call_fix_report.py \
  --plan docs/code_mapping/suite/publication_plan_rerun.json \
  --output /mnt/sata1/andres/menuCodeMapping/projects/patch_policy/CALL_CAPTURE_FIX.md
```

`publication_id` maps fresh capture IDs to stable page URLs. The publisher
replaces the baseline and other 26 pages, reconciles menu totals, and preserves
the single closed-by-default repository group. The current baseline has two
optimizer updates and a complete 302-step rollout; the older 21-update SUCCESS
trace remains historical evidence. Always derive counts from the selected run.

## Verify localhost, push, then verify Netlify

Reuse the existing server on port 8766. The browser scripts require Google
Chrome and Python's `websocket-client` module. From the project root:

```bash
python docs/code_mapping/suite/verify_site.py \
  --base-url http://localhost:8766 \
  --catalog docs/code_mapping/suite/publication_catalog_rerun.json \
  --output docs/code_mapping/suite/delivery-local-rerun.json
python docs/code_mapping/suite/verify_call_navigation.py \
  --base-url http://localhost:8766 \
  --catalog docs/code_mapping/suite/publication_catalog_rerun.json \
  --output docs/code_mapping/suite/delivery-calls-local-rerun.json
python docs/code_mapping/suite/verify_sample_fields.py \
  --base-url http://localhost:8766 \
  --catalog docs/code_mapping/suite/publication_catalog_rerun.json \
  --output docs/code_mapping/suite/delivery-sample-fields-local-rerun.json
```

These checks cover the actual menu, stage navigation, context values, observed
call arrows, mutually exclusive returns, native/module endpoints, crowded-line
menus, real pointer hit testing and keyboard activation. Preserve existing
reviewed innovation frames when replacing the diffusion page.

After local checks pass, complete the authorized menu commit/push, including
intended reusable `code_flow_v2/` changes. Repeat these commands with
`--base-url https://roaring-kringle-be46b2.netlify.app/` and distinct public report
paths after deployment. A push alone does not prove deployment.

Record the commit, verified payloads, local/public URLs and remaining limits in
`docs/code_mapping/suite/RERUN_PUBLISHED.md`. The published issue report is
[CALL_CAPTURE_FIX.md](../../../projects/patch_policy/CALL_CAPTURE_FIX.md).
