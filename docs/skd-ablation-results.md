# Matched-candidate-pool ablations

Positive paired difference favors SKD. Exact-k subset requires all selectors. Correlations deduplicate selected one-edit candidates; samples can contribute multiple candidates, so these are descriptive, dependent observations, not causal estimates.

Primary comparisons require every selector to realize k edits. Pool coverage and all-eligible results remain visible alongside the comparable subsets.

|Scheme|k|Reference|Pairs|SKD minus reference score reduction|95% bootstrap interval|
|---|---:|---|---:|---:|---|
|kgw|1|random_pool|239|-0.013022|[-0.044220, 0.018865]|
|kgw|1|entropy_only|239|-0.007646|[-0.035614, 0.019713]|
|kgw|2|random_pool|239|-0.016786|[-0.060303, 0.024907]|
|kgw|2|entropy_only|239|-0.003715|[-0.042985, 0.033516]|
|kgw|3|random_pool|239|-0.025116|[-0.080931, 0.026868]|
|kgw|3|entropy_only|239|-0.010074|[-0.057456, 0.035393]|
|kgw|5|random_pool|239|-0.010011|[-0.074211, 0.050413]|
|kgw|5|entropy_only|239|0.001165|[-0.055845, 0.056547]|
|synthid|1|random_pool|240|0.000142|[-0.000278, 0.000554]|
|synthid|1|entropy_only|240|0.000217|[-0.000141, 0.000576]|
|synthid|2|random_pool|240|0.000360|[-0.000233, 0.000942]|
|synthid|2|entropy_only|240|0.000546|[0.000049, 0.001053]|
|synthid|3|random_pool|240|0.000737|[-0.000057, 0.001488]|
|synthid|3|entropy_only|240|0.000763|[0.000185, 0.001337]|
|synthid|5|random_pool|240|0.000721|[-0.000127, 0.001567]|
|synthid|5|entropy_only|240|0.000612|[-0.000055, 0.001315]|

Positive differences favor SKD. A confidence interval crossing zero does not establish a ranking advantage. The percentile intervals use 5,000 paired sample resamples and public seed 20261024. Missing-score pairs are listed in the machine-readable artifact.

## Post-hoc one-edit feature/effect correlations

|Scheme|Feature|Unique observed candidate edits|Spearman|
|---|---|---:|---:|
|kgw|E|1063|-0.048595|
|kgw|L|1063|0.140799|
|kgw|T|1063|0.223062|
|kgw|R|1063|-0.209476|
|kgw|D|1063|0.120864|
|synthid|E|1080|0.017229|
|synthid|L|1080|0.121126|
|synthid|T|1080|0.136319|
|synthid|R|1080|-0.127336|
|synthid|D|1080|0.079963|

[All methods, budgets, quality and coverage tables](benchmarks/qwen-v030/summary.md). The public feature artifacts contain raw values and normalized ranks; the diagnostics file reports selected feature means by scheme, selector and budget.
