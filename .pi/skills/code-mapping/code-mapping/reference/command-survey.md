# Mapping the important commands in a repository

Use this when the user asks for all important execution paths, several commands,
or broader coverage than an existing single flow. An explicit single-command
request keeps its stated scope.

1. Inventory README commands, executable entrypoints, config families, and
   actual dispatch branches. Separate distinct behavior from aliases, launcher
   sizes, inactive templates, commented-out tests, and unused library classes.
2. Build a command matrix: purpose, existing evidence, required data/model
   assets, environment/hardware, planned bounds, and expected outputs. Cover
   materially different task/policy families, preprocessing, loading/resume,
   inference/evaluation, and executable utilities where the repository has them.
   Encoder or backend families may use a single explicit diagnostic command
   covering their variants; record each variant's outcome and sampled values.
3. Reuse matching completed captures. Run the remaining paths with real inputs
   and bounded execution appropriate to code mapping. Preserve default model
   behavior where feasible; document any diagnostic wrapper, iteration limit,
   selected task, or dataset subset. A short execution is not full training or
   benchmark reproduction. Avoid an unnecessary Cartesian product of configs.
4. Keep a separate brief, output directory, capture, curated stages, and result
   per command. Distinguish application failures, capture-tool failures, missing
   assets/access, and paths not attempted. Retain failed evidence when fixing a
   blocker, and do not label an import-only attempt as a completed execution.
5. If important code runs only in subprocesses, use supported worker tracing or
   a separately labeled direct-process diagnostic to expose those internals.
   Never claim parent-process coverage includes a simulator worker or other rank.
6. Verify actual work: optimization and saved state when training, resumed
   counters when restoring, real output values for each probed variant, and
   readable generated assets. Bind navigator stages to exact file/function or
   node identities; common names such as `main` can occur in several files.
7. Publish the selected command pages under one project folder and group their
   cards in the existing sessions menu. Keep prior URLs usable. Update counts
   from the selected traces and retain an inventory of successes and blockers.
   Run the local/public browser checks in [PUBLISHING.md](../../PUBLISHING.md).

Finish with a link to the project's grouped flows, the paths actually covered,
and concrete remaining blockers. Do not say “all commands passed” when only
representative paths ran or some configurations failed.
