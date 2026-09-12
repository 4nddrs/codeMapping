# Code Mapping Sessions

A browsable archive of traced code-mapping sessions for robotics and machine-learning projects. Each session is a self-contained HTML call tree or probe report, collected from a concrete training, evaluation, inference, or serving run.

The repository is intentionally static: there is no build step, package manager, or application server requirement. Open the menu locally and follow the links to inspect a session.

Live menu: [roaring-kringle-be46b2.netlify.app](https://roaring-kringle-be46b2.netlify.app/).

## Quick Start.

### Open directly in a browser

Open [`index.html`](index.html) in a browser. All session links use relative paths, so the archive works directly from disk.

### Serve locally

For a local URL, use the included helper:

```bash
bash serve.sh
```

The menu will be available at `http://localhost:8766/`. A different port or bind address can be supplied:

```bash
bash serve.sh 9000
bash serve.sh 8766 0.0.0.0
```

The server uses Python's built-in `http.server`; Python 3 is required for this option.

## Repository Layout

```text
index.html                      Archive menu and session index
projects/                       Self-contained traced session pages
serve.sh                        Optional local static-file server
README.md                       Project documentation
code_flow_v2/                   Versioned Code Mapping workflow and portable tracer
```

## Included Sessions

| Session | Traced run | Result | Report |
| --- | --- | --- | --- |
| Patch Policy | `bash docs/code_mapping/run_capture.sh` · Push-T VQ-BeT training and rollout | Exit 0; 21 updates; 302 simulator steps; coverage 0.0 | [Code flow](projects/patch_policy/index.html) |
| GAP | `gap run examples/libero_quickstart/graph --sim libero_object_all_variance/0` | Success, reward 1.00 | [Open](projects/gap/index.html) |
| CAP | `python test_sim.py --model_path checkpoints/pick.pt --condition 3d --num_episodes 12 --seed 0` | Exit 0, 9/12 picked | [Open](projects/cap/index.html) |
| RLDX-1 | Training and inference traces | Two runs completed | [Training](projects/rldx1/train.html), [Inference](projects/rldx1/inference.html) |
| Robo2VLM | 500 probes from the `test` split | 13 probe types | [Open](projects/robo2vlm/index.html) |
| Robo2VLM · Training | Two-GPU Llama 3.2 Vision LoRA training: 64 examples, 8 optimizer steps; recursive Python coverage | SUCCESS · 2 GPUs · 8 steps · loss 3.55917 | [Code mapping](projects/robo2vlm/train.html) |
| UMI | Debug training run | Exit 0 | [Open](projects/umi/index.html) |
| simtoolreal | DexToolBench IsaacGym episode | 580 steps, 37/37 goals | [Open](projects/simtoolreal/index.html) |
| perturb_flow | Training and evaluation traces | Training completed; evaluation report included | [Training](projects/perturb_flow/train.html), [Evaluation](projects/perturb_flow/eval.html) |
| VERA | PushT, MimicGen, DROID, and training traces | Serving and training reports | [PushT](projects/vera/pusht-serve.html), [MimicGen](projects/vera/mimicgen-serve.html), [DROID](projects/vera/droid-serve.html), [IDM](projects/vera/train-idm.html), [Planner](projects/vera/train-planner.html) |
| VLM4VLA | Coverage and training/I/O traces | Short trial completed | [Coverage](projects/vlm4vla/index.html), [Training/I/O](projects/vlm4vla/io.html) |
| RoboInter | Training, inference, scoring, annotation-service and dataloader traces | Five runs, all exit 0; the annotation and dataloader runs use synthesised input | [Training](projects/robointer/index.html), [Inference](projects/robointer/eval.html), [Scoring](projects/robointer/score.html), [Annotation](projects/robointer/annotate.html), [Dataloader](projects/robointer/dataloader.html) |

The full command lines, coverage counts, timings, and outcomes are documented in the menu at [`index.html`](index.html).

## Adding a Session

1. Add the generated HTML report to a new folder under `projects/`.
2. Add a session card to `index.html`, including its name, description, command, result, and relative link.
3. Update the totals and section counts in `index.html` when applicable.
4. Open the menu locally and verify that the new link works from disk and through `serve.sh`.

Keep generated reports self-contained whenever possible. If a report references the original source repository, document that source and the exact capture command in the menu or in this README.

## Notes

- The HTML reports are snapshots of specific runs, not live views of the source projects.
- The original project source code and large datasets are not included in this repository.
- Some reports contain links or metadata pointing to the external source repositories used during capture.
- The archive can be published as a static site, including through GitHub Pages, without additional configuration.

## Mapping workflow

The [Code Mapping workflow](code_flow_v2/README.md) is versioned with this menu.
Normal mapping requests include the evidence and documentation, a rendered call tree,
a verified localhost:8766 menu entry, and the authorized site publication. Existing
traces are reused for rendering. Explicit data-only or local-only requests take precedence.
See [publishing and workflow synchronization](code_flow_v2/PUBLISHING.md) for the
working-pack path and the local, pushed, and deployed checks.

<!-- PATCH_POLICY_RUNS_BEGIN -->
## Patch Policy execution paths

[Open the grouped flows](https://roaring-kringle-be46b2.netlify.app/#patch-policy). The original PushT VQ-BeT baseline remains at its existing URL. These are bounded real executions; failed or blocked configurations are labeled.

| Path | Kind | Recorded outcome | Navigator |
| --- | --- | --- | --- |
| PushT Diffusion | training | SUCCESS · exit 0 · 221.0s · 2 observed updates · 302 parent simulator steps · reward 0 · final coverage mean 0 | [Flow](projects/patch_policy/pusht_diffusion.html) |
| Blockpush VQ-BeT | training | SUCCESS · exit 0 · 104.1s · 2 observed updates · 300 parent simulator steps · reward 0 · entered mean 0 | [Flow](projects/patch_policy/blockpush_vq.html) |
| Blockpush Diffusion | training | SUCCESS · exit 0 · 817.2s · 2 observed updates · 300 parent simulator steps · reward 0 · entered mean 0 | [Flow](projects/patch_policy/blockpush_diffusion.html) |
| Cube VQ-BeT | training | SUCCESS · exit 0 · 85.5s · 2 observed updates · 300 parent simulator steps · reward -600 · entered mean 0 | [Flow](projects/patch_policy/cube_vq.html) |
| Cube Diffusion | training | SUCCESS · exit 0 · 319.3s · 2 observed updates · 300 parent simulator steps · reward -600 · entered mean 0 | [Flow](projects/patch_policy/cube_diffusion.html) |
| Libero Goal VQ-BeT | training | SUCCESS · exit 0 · 96.3s · 2 observed updates · 300 parent simulator steps · reward 0 · best evaluation reward 0 | [Flow](projects/patch_policy/libero_goal_vq.html) |
| Libero Goal Diffusion | training | SUCCESS · exit 0 · 336.7s · 2 observed updates · 300 parent simulator steps · reward 0 · best evaluation reward 0 | [Flow](projects/patch_policy/libero_goal_diffusion.html) |
| Online Encoding | training | SUCCESS · exit 0 · 84.8s · 2 observed updates · 302 parent simulator steps · reward 0 · final coverage mean 0 | [Flow](projects/patch_policy/pusht_online.html) |
| Checkpoint Evaluation | training | SUCCESS · exit 0 · 79.9s · 302 parent simulator steps · reward 0 · final coverage mean 0 | [Flow](projects/patch_policy/pusht_checkpoint_eval.html) |
| Snapshot Resume | training | SUCCESS · exit 0 · 86.5s · 2 observed updates · 302 parent simulator steps · reward 0 · final coverage mean 0 | [Flow](projects/patch_policy/pusht_resume.html) |
| Diffusion Resume | training | SUCCESS · exit 0 · 406.2s · 2 observed updates · 604 parent simulator steps · reward 0 · final coverage mean 0 | [Flow](projects/patch_policy/pusht_diffusion_resume.html) |
| Model Resources | resources | SUCCESS · exit 0 · 67.3s | [Flow](projects/patch_policy/resources_vq.html) |
| DINOv2 Encoders | encoder | SUCCESS · exit 0 · 47.6s | [Flow](projects/patch_policy/encoders_dino_contexts.html) |
| ResNet-18 Encoders | encoder | SUCCESS · exit 0 · 45.5s | [Flow](projects/patch_policy/encoders_resnet.html) |
| WebSSL Encoders | encoder | SUCCESS · exit 0 · 92.1s | [Flow](projects/patch_policy/encoders_webssl_contexts.html) |
| SigLIP2 Encoders | encoder | SUCCESS · exit 0 · 119.8s | [Flow](projects/patch_policy/encoders_siglip2.html) |
| V-JEPA 2 Encoders | encoder | SUCCESS · exit 0 · 108.2s | [Flow](projects/patch_policy/encoders_vjepa2.html) |
| DINOv3 Encoders | encoder | FAILED · exit 1 · 50.0s · OSError('You are trying to access a gated repo.\nMake sure to have access to it at https://huggingface.co/facebook/dinov3-vits16plus-pretrain-lvd1689m.\n403 Cli | [Flow](projects/patch_policy/encoders_dinov3.html) |
| DynaMo checkpoint configuration Encoders | encoder | FAILED · exit 1 · 43.1s | [Flow](projects/patch_policy/encoders_dynamo.html) |
| PushT Simulator | simulator | SUCCESS · exit 0 · 23.3s | [Flow](projects/patch_policy/pusht_simulator_v2.html) |
| Block Push Simulator | simulator | SUCCESS · exit 0 · 26.5s | [Flow](projects/patch_policy/blockpush_simulator_v2.html) |
| Cube Simulator | simulator | SUCCESS · exit 0 · 11.5s | [Flow](projects/patch_policy/cube_simulator_v2.html) |
| LIBERO Ten Task Simulators | simulator | SUCCESS · exit 0 · 81.7s | [Flow](projects/patch_policy/libero_simulator_v2.html) |
| Cube Episode Video Export | utility | SUCCESS · exit 0 · 8.1s | [Flow](projects/patch_policy/cube_video_export.html) |
| Cube Plan Oracle Collection | utility | SUCCESS · exit 0 · 20.0s | [Flow](projects/patch_policy/cube_generate_play.html) |
| Cube Markov Oracle Collection | utility | SUCCESS · exit 0 · 15.5s | [Flow](projects/patch_policy/cube_generate_noisy.html) |
<!-- PATCH_POLICY_RUNS_END -->
