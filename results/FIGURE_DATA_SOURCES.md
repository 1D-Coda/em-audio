# Figure data sources

Every visual element in every figure, and the committed result file it is read from. No measured number is typed into a plotting script: where a value exists in `results/machine_readable/`, the script reads it, and a figure whose data is absent fails rather than being drawn from memory.

## `fig1_counterexample`

| element | source |
|---|---|
| waveform and interval strip | `constructed fixture rendered by tools/make_figures.py` |
| emitted claims | `A_synthetic_state_space.json (contract semantics)` |

## `fig2_architecture`

| element | source |
|---|---|
| diagram, no measured values | `none` |

## `fig3_promotion`

| element | source |
|---|---|
| panel A, promotion by depth | `B_adversarial_timelines.json -> per_depth` |
| panel B, policy ablation | `B2_policy_ablation.json -> arms` |
| panel C, closed-form control | `B_adversarial_timelines.json -> control_uniform_positions` |

## `fig4_corpus`

| element | source |
|---|---|
| promotion by transformation | `D_transform_matrix.json -> per_transformation` |

## `fig5_containment`

| element | source |
|---|---|
| measured reach | `K_support_containment.json -> per_operator[*].max_measured_reach_source_samples` |
| declared footprint | `K_support_containment.json -> per_operator[*].declared_footprint_samples` |
| samples outside | `K_support_containment.json -> per_operator[*].total_outside_declared_support` |

## `fig6_dilution`

| element | source |
|---|---|
| panel A, per transformation | `I_claim_dilution.json -> per_transformation` |
| panel B, composition depth | `I_claim_dilution.json -> composition_chain` |
| panel C, asset duration | `I_claim_dilution.json -> long_asset_chain` |

## `fig7_overhead`

| element | source |
|---|---|
| assertion size and time scaling | `G_overhead.json -> assertion_scaling` |
