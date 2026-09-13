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
| Patch Policy | Fresh bounded PushT VQ-BeT training and rollout; 27 command flows in the repository group | Baseline exit 0; 2 updates; 302 simulator steps; task coverage 0.0 | [Code flow](projects/patch_policy/index.html) |
| Cosmos Policy | 11 bounded command flows (Quick Start, LIBERO/RoboCasa evaluation, ALOHA serving and planning, training, data preparation) in the repository group | 10/11 exit 0 | [Grouped flows](index.html#cosmos-policy) |
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

[Open the grouped flows](https://roaring-kringle-be46b2.netlify.app/#patch-policy). Fresh captures replace the prior evidence at all existing page URLs, including the PushT VQ-BeT baseline. These are bounded real executions; failed or blocked configurations are labeled.

| Path | Kind | Recorded outcome | Navigator |
| --- | --- | --- | --- |
| PushT VQ-BeT baseline | training | SUCCESS · exit 0 · 132.7s · 2 observed updates · 302 parent simulator steps · reward 0 · final coverage mean 0 | [Flow](projects/patch_policy/index.html) |
| PushT Diffusion | training | SUCCESS · exit 0 · 348.3s · 2 observed updates · 302 parent simulator steps · reward 0 · final coverage mean 0 | [Flow](projects/patch_policy/pusht_diffusion.html) |
| Blockpush VQ-BeT | training | SUCCESS · exit 0 · 199.7s · 2 observed updates · 300 parent simulator steps · reward 0 · entered mean 0 | [Flow](projects/patch_policy/blockpush_vq.html) |
| Blockpush Diffusion | training | SUCCESS · exit 0 · 1597.4s · 2 observed updates · 300 parent simulator steps · reward 0 · entered mean 0 | [Flow](projects/patch_policy/blockpush_diffusion.html) |
| Cube VQ-BeT | training | SUCCESS · exit 0 · 186.8s · 2 observed updates · 300 parent simulator steps · reward -600 · entered mean 0 | [Flow](projects/patch_policy/cube_vq.html) |
| Cube Diffusion | training | SUCCESS · exit 0 · 627.3s · 2 observed updates · 300 parent simulator steps · reward -600 · entered mean 0 | [Flow](projects/patch_policy/cube_diffusion.html) |
| Libero Goal VQ-BeT | training | SUCCESS · exit 0 · 158.0s · 2 observed updates · 300 parent simulator steps · reward 0 · best evaluation reward 0 | [Flow](projects/patch_policy/libero_goal_vq.html) |
| Libero Goal Diffusion | training | SUCCESS · exit 0 · 551.9s · 2 observed updates · 300 parent simulator steps · reward 0 · best evaluation reward 0 | [Flow](projects/patch_policy/libero_goal_diffusion.html) |
| Online Encoding | training | SUCCESS · exit 0 · 144.4s · 2 observed updates · 302 parent simulator steps · reward 0 · final coverage mean 0 | [Flow](projects/patch_policy/pusht_online.html) |
| Checkpoint Evaluation | training | SUCCESS · exit 0 · 136.3s · 302 parent simulator steps · reward 0 · final coverage mean 0 | [Flow](projects/patch_policy/pusht_checkpoint_eval.html) |
| Snapshot Resume | training | SUCCESS · exit 0 · 145.7s · 2 observed updates · 302 parent simulator steps · reward 0 · final coverage mean 0 | [Flow](projects/patch_policy/pusht_resume.html) |
| Diffusion Resume | training | SUCCESS · exit 0 · 640.3s · 2 observed updates · 604 parent simulator steps · reward 0 · final coverage mean 0 | [Flow](projects/patch_policy/pusht_diffusion_resume.html) |
| Model Resources | resources | SUCCESS · exit 0 · 103.4s | [Flow](projects/patch_policy/resources_vq.html) |
| DINOv2 Encoders | encoder | SUCCESS · exit 0 · 88.2s | [Flow](projects/patch_policy/encoders_dino_contexts.html) |
| ResNet-18 Encoders | encoder | SUCCESS · exit 0 · 94.1s | [Flow](projects/patch_policy/encoders_resnet.html) |
| WebSSL Encoders | encoder | SUCCESS · exit 0 · 398.0s | [Flow](projects/patch_policy/encoders_webssl_contexts.html) |
| SigLIP2 Encoders | encoder | SUCCESS · exit 0 · 238.5s | [Flow](projects/patch_policy/encoders_siglip2.html) |
| V-JEPA 2 Encoders | encoder | SUCCESS · exit 0 · 171.7s | [Flow](projects/patch_policy/encoders_vjepa2.html) |
| DINOv3 Encoders | encoder | FAILED · exit 1 · 105.4s · OSError('You are trying to access a gated repo.\nMake sure to have access to it at https://huggingface.co/facebook/dinov3-vits16plus-pretrain-lvd1689m.\n403 Cli | [Flow](projects/patch_policy/encoders_dinov3.html) |
| DynaMo checkpoint configuration Encoders | encoder | FAILED · exit 1 · 75.6s | [Flow](projects/patch_policy/encoders_dynamo.html) |
| PushT Simulator | simulator | SUCCESS · exit 0 · 51.3s | [Flow](projects/patch_policy/pusht_simulator_v2.html) |
| Block Push Simulator | simulator | SUCCESS · exit 0 · 55.5s | [Flow](projects/patch_policy/blockpush_simulator_v2.html) |
| Cube Simulator | simulator | SUCCESS · exit 0 · 27.1s | [Flow](projects/patch_policy/cube_simulator_v2.html) |
| LIBERO Ten Task Simulators | simulator | SUCCESS · exit 0 · 157.9s | [Flow](projects/patch_policy/libero_simulator_v2.html) |
| Cube Episode Video Export | utility | SUCCESS · exit 0 · 15.5s | [Flow](projects/patch_policy/cube_video_export.html) |
| Cube Plan Oracle Collection | utility | SUCCESS · exit 0 · 37.2s | [Flow](projects/patch_policy/cube_generate_play.html) |
| Cube Markov Oracle Collection | utility | SUCCESS · exit 0 · 40.2s | [Flow](projects/patch_policy/cube_generate_noisy.html) |
<!-- PATCH_POLICY_RUNS_END -->
<!-- COSMOS_POLICY_RUNS_BEGIN -->
## Cosmos Policy execution paths

[Open the grouped flows](https://roaring-kringle-be46b2.netlify.app/#cosmos-policy). Bounded real executions of NVlabs/cosmos-policy commands; deviations are declared per flow in the repository's docs/code_mapping.

| Path | Kind | Recorded outcome | Navigator |
| --- | --- | --- | --- |
| Quick Start inference | inference | exit 0 · 535.2s · 16×7 actions · value 0.063 · mapping docs pending | [Flow](projects/cosmos_policy/quickstart.html) |
| LIBERO evaluation | simulation evaluation | exit 0 · 488.9s · 1/1 success · mapping docs pending | [Flow](projects/cosmos_policy/libero_eval.html) |
| RoboCasa evaluation | simulation evaluation | exit 0 · 476.3s · 1/1 success · 296 steps · mapping docs pending | [Flow](projects/cosmos_policy/robocasa_eval.html) |
| ALOHA policy server | serving | exit 0 · 295.9s · 50×14 actions · value 0.054 · mapping docs pending | [Flow](projects/cosmos_policy/aloha_deploy.html) |
| ALOHA model-based planning | serving + planning | exit 0 · 507.1s · seed 195 selected · value 0.065 · mapping docs pending | [Flow](projects/cosmos_policy/aloha_planning.html) |
| LIBERO training | training | exit 0 · 733.1s · losses 14.81 · 15.47 · 3.35 · checkpoint iter 3 · mapping docs pending | [Flow](projects/cosmos_policy/train_libero.html) |
| ALOHA training | training | exit 0 · 600.5s · losses 16.06 · 14.85 · 15.60 · checkpoint iter 3 | [Flow](projects/cosmos_policy/train_aloha.html) |
| RoboCasa training | training | exit 0 · 829.1s · losses 2.09 · 2.07 · 15.73 · checkpoint iter 3 · mapping docs pending | [Flow](projects/cosmos_policy/train_robocasa.html) |
| ALOHA T5 text embeddings | data preparation | exit 0 · 208.1s · 1 command · matches release · mapping docs pending | [Flow](projects/cosmos_policy/t5_aloha.html) |
| ALOHA data preprocessing | data preparation | exit 0 · 150.8s · 1 train + 1 val episode | [Flow](projects/cosmos_policy/aloha_preprocess.html) |
| Installation check | utility | exit 1 · 66.6s · 4 packages absent (cosmos-predict2, robocasa, fastapi, uvicorn) | [Flow](projects/cosmos_policy/verify_install.html) |

Not traced on this machine:

- `run_aloha_eval.py` — Needs ALOHA hardware; aloha_utils imports experiments.robot.aloha.real_env, which is absent from the repository; interactive prompts.
- `debug_deploy.py` — HTTP smoke client posting random images to a live server; superseded by aloha_deploy (real observation, in-process).
- `regenerate_libero_dataset.py` — Imports cosmos_policy.experiments.robot.libero.compress_libero_dataset, which does not exist in the repository; also needs original raw LIBERO demos.
- `regenerate_robocasa_dataset.py` — Needs raw RoboCasa v0.1 demonstrations, not available on this machine.
- `cosmos_policy/install.sh` — Bash installer (pip/uv/git subprocesses); its Python step is covered by verify_install.
- `save_libero_t5_text_embeddings.py / save_robocasa_t5_text_embeddings.py` — Same T5 path as t5_aloha with a different dataset class constructor; represented by t5_aloha.
- `aloha_dataset.py / libero_dataset.py / robocasa_dataset.py __main__` — Hard-coded non-existent data paths; the dataset classes run inside the three training traces.
- `train.py experiment=...__resumeFrom50K_648_rollouts_Vsprime_value_func` — Its 648-rollout planning dataset is not released; its .pt load_path would also be skipped by the dcp checkpointer.
- `deploy.py --ar_qvalue_prediction True` — Model-free Q(s,a) search branch; no Q-value checkpoint is released, so a run would produce meaningless values. The V(s') planning branch is traced (aloha_planning).
- `run_libero_eval.py / run_robocasa_eval.py --data_collection True` — Rollout-recording mode that writes the all_episodes training format; not separately traced (the evaluation flows run with the documented --data_collection False).
- `train.py --dryrun` — Config composition only; the training traces cover the same config path. On this host its import also asserts a GPU (flash_attn), so it cannot run CPU-only.
- `cosmos_policy/_src/** __main__ scripts, justfile, bin/uv_lock*.sh` — Inherited Imaginaire/Predict2 framework utilities and packaging scripts, not documented Cosmos Policy commands.
<!-- COSMOS_POLICY_RUNS_END -->

<!-- DREAMZERO_RUNS_BEGIN -->
## DreamZero execution paths

[Open the grouped flows](https://roaring-kringle-be46b2.netlify.app/#dreamzero). Bounded real executions of the dreamzero0/dreamzero repository at `ab790c1` on 2 x RTX A6000; deviations and blocked commands are documented in each flow's mapping.

| Flow | Scope | Recorded outcome | Navigator |
| --- | --- | --- | --- |
| Wan2.2-5B policy server session | drivers/serve_wan22_session.py · serve_dreamzero_wan22 main + WebsocketClientPolicy, one process | exit 0 · 454.8s · 8 infers + 1 reset · 2 mp4 | [Flow](projects/dreamzero/s1_serve_wan22.html) |
| Wan2.2-5B LoRA training | scripts/train/droid_training_wan22.sh · 2 steps, 1 GPU, DROID episodes 0-9 | exit 0 · 677.0s · traced · loss 1.0248 then 2.0593 · 614-tensor 89.9 MB save | [Flow](projects/dreamzero/t1_wan22_lora.html) |
| Initial actions extraction | get_initial_actions.py · 10 DROID episodes | exit 0 · 32.7s · 10 trajectories · 1 npz (5608 B) | [Flow](projects/dreamzero/u5_initial_actions.html) |
| LeRobot v2 to GEAR metadata (xArm6) | convert_lerobot_to_gear.py · meta/ generation, 101 episodes | exit 0 · 25.9s · 6 meta files written · 0 validation warnings | [Flow](projects/dreamzero/u1_gear_convert.html) |
| DROID dataset download (subset) | scripts/data/download_droid_hf.py · 8-file allow_patterns subset | exit 0 · 212.0s · 8 files · 1 attempt, no 429 | [Flow](projects/dreamzero/u3_download_subset.html) |
| Websocket policy protocol smoke | drivers/protocol_smoke.py · eval_utils policy_server + policy_client, one process | exit 0 · 1.0s · 18 traced functions · action (1, 8) zeros | [Flow](projects/dreamzero/u4_protocol_smoke.html) |
<!-- DREAMZERO_RUNS_END -->
