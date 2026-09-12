# Patch Policy: rebuild and deliver the saved code flow

Use this example when updating the existing Patch Policy session on this
machine. For another project, use its own brief, trace, and curated symbols.
The general publishing procedure is [PUBLISHING.md](../../PUBLISHING.md).

## Rebuild from saved evidence

```bash
cd /mnt/sata1/code/robo/patch_policy
python docs/code_mapping/tools/render_success.py
python docs/code_mapping/tools/verify_viewer.py
```

This uses `docs/code_mapping/line_coverage/success/` and the same
`docs/code_mapping/important.txt` as the mapping. The renderer adapts this
capture's primitives, array summaries, and sample contexts and uses its copied
viewer template. A stock `codetrace.py --rebuild` bypasses that adapter. Preserve
`callgraph.json`, `coverage.json`, and `run.json`; do not run
`run_capture.sh` merely to refresh the page. The scripts and raw evidence live
with the target repository; these instructions do not bundle or recreate them.

## Update the existing menu entry

After checking the menu checkout and updating it from `origin/main`, run from
the Patch Policy repository:

```bash
python /mnt/sata1/andres/code/code_flow/code_flow_v2/code-mapping/codetrace/menu_card.py \
  --out docs/code_mapping/line_coverage/success \
  --slug patch_policy --name 'Patch Policy' \
  --title 'Patch Policy · PushT Call Tree' \
  --tag 'Push-T · training and rollout' \
  --what 'One epoch on two demonstrations, 21 policy updates, and a 302-step simulator rollout; rollout coverage was 0.0.' \
  --fam cap --copy --force
```

These numbers describe the saved SUCCESS trial; derive replacements from new
evidence if the trial changes. The command replaces
`projects/patch_policy/index.html` in the shared menu. Replace its existing
card and README row rather than adding a duplicate. Label 260 as function
cards, representing 122 distinct functions. For an unchanged capture the menu
totals remain unchanged; the helper's proposed add-one totals do not apply to
this replacement.

## Verify localhost, push, then verify Netlify

Reuse the existing menu server on port 8766, or start it as documented in
PUBLISHING.md. The browser checks below require Google Chrome and the Python
`websocket-client` module. They open the actual menu, click the Patch Policy
card, compare the payload, check the 32-stage list, and exercise search, value
inspection, and all 16 selected execution-context samples. Also select a stage
to confirm it navigates to the expected card.

```bash
cd /mnt/sata1/code/robo/patch_policy
python docs/code_mapping/tools/verify_delivery.py http://localhost:8766 \
  --output docs/code_mapping/runs/local_delivery_verification.json
```

After the local checks pass, complete the authorized commit/push in
`/mnt/sata1/andres/menuCodeMapping` using PUBLISHING.md. Include the updated
versioned `code_flow_v2/` when changing the pack. Then verify the public site:

```bash
python docs/code_mapping/tools/verify_delivery.py https://roaring-kringle-be46b2.netlify.app/ \
  --output docs/code_mapping/runs/public_delivery_verification.json
```

Keep the publication record in `docs/code_mapping/runs/PUBLISHED.md` current
with the actual commit, check results, and these verified page URLs:

- http://localhost:8766/projects/patch_policy/index.html
- https://roaring-kringle-be46b2.netlify.app/projects/patch_policy/

Link the record from `MAPPING.md` and `runs/SUCCESS.md`, and update the brief,
gaps, and completion checklist. An exit-zero capture establishes execution;
this short saved run's task coverage was 0.0.
