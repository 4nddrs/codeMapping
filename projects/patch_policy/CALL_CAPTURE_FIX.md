# Patch Policy call-arrow fixes and fresh reruns

All 27 published flows were freshly attempted: 25 targets succeeded and 2 encountered unavailable prerequisites. All 27 captures passed the call-evidence and rendering audits, including the failed attempts.

## Issues fixed

- The old recorder skipped dependency functions, concrete PyTorch module calls and native operations. Fresh captures retain direct observed endpoints, including `self.input_emb(sample) → Linear.forward`.
- Whole-run highlights could combine mutually exclusive returns. Fresh project cards use line events from their own caller group; retained value samples keep their recorded invocation/frame line scope.
- Helpers exceeding the instance limit could inherit function-level edges from other callers. Fresh instance edges preserve the actual caller even when a helper card is merged.
- Several arrows on a long source line could be clipped. Overflowing rows now keep a primary arrow and a **+N calls** menu containing every observed destination.
- Untraced dependency source is excluded from coverage totals, so adding reference cards does not lower the displayed project coverage ratio.
- Exceptional exits, successful `None`, generator suspension, and unavailable native values have separate evidence and inspector labels.
- Python profiler events can confuse `yield None` with generator closure or exceptional termination. Ambiguous saved samples now say `unknown`; older aggregate suspension counts retain a broader label and a visible provenance note. Future captures use the corrected classification. Raw evidence remains unchanged.

## Reported diffusion examples

In the fresh PushT diffusion run, `DiffusionPolicy.forward` line 773 leads to `_predict` in the 61-call rollout context. Line 775 leads to `_update` in the two validation and two training calls. The context cards no longer borrow the other path’s highlight or arrow.

`TransformerForDiffusion.forward` line 447 opens the actual `Linear.forward` endpoint: two validation calls, two training calls, and 6,100 rollout calls. The time embedding, condition projection, dropout, encoder, decoder, final layer norm and output head were audited as well. Crowded line 815 exposes all six recorded destinations, including the two distinct native tensor conversions.

## Validation

The complete page audit reconciled 5,049 project arrows and 22,677 dependency arrows, with 34,322 displayed context-line events and 35,142 retained dependency samples. No recorder errors, dropped boundary records, context-sampling overflows or unfinished dependency samples were accepted.

The reusable regression suite passes 23 tests covering module/native calls, nested calls, short circuits, comprehensions, exception outcomes, context lines, merged helpers, threads, renderer accounting and older trace compatibility. Browser acceptance checks use real pointer hit testing and native keyboard activation in addition to payload comparisons. The separate delivery reports establish which localhost/public deployment was checked.

| Flow | Fresh target result | Project arrows | Dependency arrows |
| --- | --- | ---: | ---: |
| [PushT VQ-BeT baseline](index.html) | Succeeded | 305 | 1,623 |
| [PushT Diffusion](pusht_diffusion.html) | Succeeded | 187 | 1,021 |
| [Blockpush VQ-BeT](blockpush_vq.html) | Succeeded | 295 | 1,616 |
| [Blockpush Diffusion](blockpush_diffusion.html) | Succeeded | 176 | 1,021 |
| [Cube VQ-BeT](cube_vq.html) | Succeeded | 297 | 1,630 |
| [Cube Diffusion](cube_diffusion.html) | Succeeded | 178 | 1,023 |
| [Libero Goal VQ-BeT](libero_goal_vq.html) | Succeeded | 285 | 1,637 |
| [Libero Goal Diffusion](libero_goal_diffusion.html) | Succeeded | 167 | 1,040 |
| [Online Encoding](pusht_online.html) | Succeeded | 289 | 1,551 |
| [Checkpoint Evaluation](pusht_checkpoint_eval.html) | Succeeded | 135 | 681 |
| [Snapshot Resume](pusht_resume.html) | Succeeded | 220 | 1,210 |
| [Diffusion Resume](pusht_diffusion_resume.html) | Succeeded | 233 | 1,157 |
| [Model Resources](resources_vq.html) | Succeeded | 102 | 583 |
| [DINOv2 Encoders](encoders_dino_contexts.html) | Succeeded | 12 | 187 |
| [ResNet-18 Encoders](encoders_resnet.html) | Succeeded | 12 | 178 |
| [WebSSL Encoders](encoders_webssl_contexts.html) | Succeeded | 12 | 198 |
| [SigLIP2 Encoders](encoders_siglip2.html) | Succeeded | 12 | 200 |
| [V-JEPA 2 Encoders](encoders_vjepa2.html) | Succeeded | 12 | 190 |
| [DINOv3 Encoders](encoders_dinov3.html) | Prerequisite unavailable | 11 | 134 |
| [DynaMo checkpoint configuration Encoders](encoders_dynamo.html) | Prerequisite unavailable | 10 | 118 |
| [PushT Simulator](pusht_simulator_v2.html) | Succeeded | 96 | 571 |
| [Block Push Simulator](blockpush_simulator_v2.html) | Succeeded | 115 | 472 |
| [Cube Simulator](cube_simulator_v2.html) | Succeeded | 511 | 1,213 |
| [LIBERO Ten Task Simulators](libero_simulator_v2.html) | Succeeded | 362 | 1,018 |
| [Cube Episode Video Export](cube_video_export.html) | Succeeded | 4 | 49 |
| [Cube Plan Oracle Collection](cube_generate_play.html) | Succeeded | 506 | 1,177 |
| [Cube Markov Oracle Collection](cube_generate_noisy.html) | Succeeded | 505 | 1,179 |

## Remaining limits

DINOv3 still requires access to its gated Hugging Face checkpoint; the fresh request returned HTTP 403. DynaMo configurations still require checkpoint paths that were not provided. These attempts are shown with their actual failure evidence.

Dependency bodies are source references, without recursive internal call or line coverage. Native argument/return values unavailable from the profiler remain labeled unavailable. Some built-in constructors and callbacks implemented entirely in native code, including `map`/`partial` and `dict`, emit no profiler call event; a real probe confirmed this. A covered line alone does not establish that every expression on it ran.

Older immutable traces remain in the source workspace. The fresh PushT VQ baseline uses two optimizer updates; the historical baseline used 21. Evaluation, resources and resume jobs use the new baseline artifacts with recorded hashes. All existing page URLs remain in the same collapsible repository group.

[Machine verification summary](CALL_CAPTURE_FIX.json) · [Portable workflow](../../code_flow_v2/README.md)
