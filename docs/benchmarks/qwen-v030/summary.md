# Experiment 004 — Sparse Keyless Disruption

Fixed 1/2/3/5 local edits; one candidate pool per sample. All weights were committed before detector evaluation. Positive score reduction means weaker detector evidence.

Target FPR 1%; the frozen SynthID d20 weighted evaluator had observed held-out FPR 3/99 (3.03%). No recalibration. Embedding cosine does not establish factual correctness.

## Baseline eligibility

- kgw: 239/240 eligible; miss 0; abstention 1.
- synthid: 240/240 eligible; miss 0; abstention 0.

## Candidate coverage among eligible baselines

|Scheme|Edits|Pool capable / eligible|All selectors exact k|Missing pool|
|---|---:|---:|---:|---:|
|kgw|1|239/239|239|0|
|kgw|2|239/239|239|0|
|kgw|3|239/239|239|0|
|kgw|5|239/239|239|0|
|synthid|1|240/240|240|0|
|synthid|2|240/240|240|0|
|synthid|3|240/240|240|0|
|synthid|5|240/240|240|0|

## All eligible attempts (exhaustion retained)

|Scheme|Method|k|N|Evasion|Abstention|Failures|Δ score|Semantic|Word fraction|Token fraction|Anchors|
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|kgw|random_pool|1|239|0.00%|14.64%|0|0.1160|0.9983|0.0109|0.0088|1.0000|
|kgw|random_pool|2|239|0.00%|17.99%|0|0.2294|0.9968|0.0211|0.0168|1.0000|
|kgw|random_pool|3|239|0.00%|23.85%|0|0.3516|0.9955|0.0313|0.0248|1.0000|
|kgw|random_pool|5|239|0.00%|28.03%|0|0.5704|0.9927|0.0528|0.0418|1.0000|
|synthid|random_pool|1|240|0.00%|5.42%|0|0.0023|0.9985|0.0103|0.0080|1.0000|
|synthid|random_pool|2|240|0.00%|12.08%|0|0.0044|0.9971|0.0208|0.0164|1.0000|
|synthid|random_pool|3|240|0.00%|17.08%|0|0.0064|0.9956|0.0317|0.0249|1.0000|
|synthid|random_pool|5|240|0.00%|18.33%|0|0.0108|0.9921|0.0533|0.0420|1.0000|
|kgw|entropy_only|1|239|0.00%|17.57%|0|0.1107|0.9983|0.0084|0.0065|1.0000|
|kgw|entropy_only|2|239|0.00%|27.20%|0|0.2164|0.9965|0.0178|0.0139|1.0000|
|kgw|entropy_only|3|239|0.00%|35.15%|0|0.3366|0.9952|0.0268|0.0210|1.0000|
|kgw|entropy_only|5|239|0.00%|44.35%|0|0.5592|0.9923|0.0465|0.0361|1.0000|
|synthid|entropy_only|1|240|0.00%|8.75%|0|0.0022|0.9973|0.0087|0.0070|1.0000|
|synthid|entropy_only|2|240|0.42%|20.00%|0|0.0042|0.9957|0.0175|0.0139|1.0000|
|synthid|entropy_only|3|240|0.42%|25.42%|0|0.0064|0.9938|0.0268|0.0211|1.0000|
|synthid|entropy_only|5|240|0.42%|31.67%|0|0.0109|0.9909|0.0470|0.0366|1.0000|
|kgw|context_only|1|239|0.00%|9.62%|0|0.1692|0.9979|0.0159|0.0125|1.0000|
|kgw|context_only|2|239|0.00%|11.30%|0|0.3471|0.9955|0.0312|0.0245|1.0000|
|kgw|context_only|3|239|0.00%|16.74%|0|0.4795|0.9937|0.0448|0.0353|1.0000|
|kgw|context_only|5|239|0.00%|22.59%|0|0.6978|0.9915|0.0664|0.0524|1.0000|
|synthid|context_only|1|240|0.00%|9.58%|0|0.0029|0.9976|0.0159|0.0123|1.0000|
|synthid|context_only|2|240|0.00%|12.08%|0|0.0054|0.9957|0.0309|0.0237|1.0000|
|synthid|context_only|3|240|0.00%|14.17%|0|0.0081|0.9938|0.0447|0.0346|1.0000|
|synthid|context_only|5|240|0.42%|17.50%|0|0.0124|0.9903|0.0672|0.0527|1.0000|
|kgw|tokenizer_only|1|239|0.00%|23.01%|0|0.2042|0.9970|0.0213|0.0191|1.0000|
|kgw|tokenizer_only|2|239|0.00%|22.18%|0|0.3446|0.9948|0.0395|0.0350|1.0000|
|kgw|tokenizer_only|3|239|0.00%|23.01%|0|0.4983|0.9925|0.0565|0.0491|1.0000|
|kgw|tokenizer_only|5|239|0.42%|24.27%|0|0.7755|0.9886|0.0869|0.0740|1.0000|
|synthid|tokenizer_only|1|240|0.00%|17.92%|0|0.0027|0.9962|0.0217|0.0193|1.0000|
|synthid|tokenizer_only|2|240|0.00%|17.50%|0|0.0056|0.9937|0.0402|0.0353|1.0000|
|synthid|tokenizer_only|3|240|0.42%|17.50%|0|0.0080|0.9915|0.0572|0.0497|1.0000|
|synthid|tokenizer_only|5|240|1.25%|23.33%|0|0.0129|0.9877|0.0873|0.0745|1.0000|
|kgw|skd|1|239|0.00%|16.74%|0|0.1030|0.9992|0.0094|0.0081|1.0000|
|kgw|skd|2|239|0.00%|19.67%|0|0.2126|0.9985|0.0183|0.0151|1.0000|
|kgw|skd|3|239|0.00%|23.01%|0|0.3265|0.9977|0.0271|0.0222|1.0000|
|kgw|skd|5|239|0.00%|30.96%|0|0.5604|0.9959|0.0452|0.0371|1.0000|
|synthid|skd|1|240|0.00%|12.08%|0|0.0024|0.9990|0.0101|0.0086|1.0000|
|synthid|skd|2|240|0.00%|16.25%|0|0.0047|0.9980|0.0196|0.0164|1.0000|
|synthid|skd|3|240|0.42%|20.00%|0|0.0072|0.9973|0.0293|0.0242|1.0000|
|synthid|skd|5|240|0.42%|25.00%|0|0.0115|0.9955|0.0467|0.0381|1.0000|

## Exact-k comparable subsets

|Scheme|Method|k|N|Evasion|Abstention|Failures|Δ score|Semantic|Word fraction|Token fraction|Anchors|
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|kgw|random_pool|1|239|0.00%|14.64%|0|0.1160|0.9983|0.0109|0.0088|1.0000|
|kgw|entropy_only|1|239|0.00%|17.57%|0|0.1107|0.9983|0.0084|0.0065|1.0000|
|kgw|context_only|1|239|0.00%|9.62%|0|0.1692|0.9979|0.0159|0.0125|1.0000|
|kgw|tokenizer_only|1|239|0.00%|23.01%|0|0.2042|0.9970|0.0213|0.0191|1.0000|
|kgw|skd|1|239|0.00%|16.74%|0|0.1030|0.9992|0.0094|0.0081|1.0000|
|kgw|random_pool|2|239|0.00%|17.99%|0|0.2294|0.9968|0.0211|0.0168|1.0000|
|kgw|entropy_only|2|239|0.00%|27.20%|0|0.2164|0.9965|0.0178|0.0139|1.0000|
|kgw|context_only|2|239|0.00%|11.30%|0|0.3471|0.9955|0.0312|0.0245|1.0000|
|kgw|tokenizer_only|2|239|0.00%|22.18%|0|0.3446|0.9948|0.0395|0.0350|1.0000|
|kgw|skd|2|239|0.00%|19.67%|0|0.2126|0.9985|0.0183|0.0151|1.0000|
|kgw|random_pool|3|239|0.00%|23.85%|0|0.3516|0.9955|0.0313|0.0248|1.0000|
|kgw|entropy_only|3|239|0.00%|35.15%|0|0.3366|0.9952|0.0268|0.0210|1.0000|
|kgw|context_only|3|239|0.00%|16.74%|0|0.4795|0.9937|0.0448|0.0353|1.0000|
|kgw|tokenizer_only|3|239|0.00%|23.01%|0|0.4983|0.9925|0.0565|0.0491|1.0000|
|kgw|skd|3|239|0.00%|23.01%|0|0.3265|0.9977|0.0271|0.0222|1.0000|
|kgw|random_pool|5|239|0.00%|28.03%|0|0.5704|0.9927|0.0528|0.0418|1.0000|
|kgw|entropy_only|5|239|0.00%|44.35%|0|0.5592|0.9923|0.0465|0.0361|1.0000|
|kgw|context_only|5|239|0.00%|22.59%|0|0.6978|0.9915|0.0664|0.0524|1.0000|
|kgw|tokenizer_only|5|239|0.42%|24.27%|0|0.7755|0.9886|0.0869|0.0740|1.0000|
|kgw|skd|5|239|0.00%|30.96%|0|0.5604|0.9959|0.0452|0.0371|1.0000|
|synthid|random_pool|1|240|0.00%|5.42%|0|0.0023|0.9985|0.0103|0.0080|1.0000|
|synthid|entropy_only|1|240|0.00%|8.75%|0|0.0022|0.9973|0.0087|0.0070|1.0000|
|synthid|context_only|1|240|0.00%|9.58%|0|0.0029|0.9976|0.0159|0.0123|1.0000|
|synthid|tokenizer_only|1|240|0.00%|17.92%|0|0.0027|0.9962|0.0217|0.0193|1.0000|
|synthid|skd|1|240|0.00%|12.08%|0|0.0024|0.9990|0.0101|0.0086|1.0000|
|synthid|random_pool|2|240|0.00%|12.08%|0|0.0044|0.9971|0.0208|0.0164|1.0000|
|synthid|entropy_only|2|240|0.42%|20.00%|0|0.0042|0.9957|0.0175|0.0139|1.0000|
|synthid|context_only|2|240|0.00%|12.08%|0|0.0054|0.9957|0.0309|0.0237|1.0000|
|synthid|tokenizer_only|2|240|0.00%|17.50%|0|0.0056|0.9937|0.0402|0.0353|1.0000|
|synthid|skd|2|240|0.00%|16.25%|0|0.0047|0.9980|0.0196|0.0164|1.0000|
|synthid|random_pool|3|240|0.00%|17.08%|0|0.0064|0.9956|0.0317|0.0249|1.0000|
|synthid|entropy_only|3|240|0.42%|25.42%|0|0.0064|0.9938|0.0268|0.0211|1.0000|
|synthid|context_only|3|240|0.00%|14.17%|0|0.0081|0.9938|0.0447|0.0346|1.0000|
|synthid|tokenizer_only|3|240|0.42%|17.50%|0|0.0080|0.9915|0.0572|0.0497|1.0000|
|synthid|skd|3|240|0.42%|20.00%|0|0.0072|0.9973|0.0293|0.0242|1.0000|
|synthid|random_pool|5|240|0.00%|18.33%|0|0.0108|0.9921|0.0533|0.0420|1.0000|
|synthid|entropy_only|5|240|0.42%|31.67%|0|0.0109|0.9909|0.0470|0.0366|1.0000|
|synthid|context_only|5|240|0.42%|17.50%|0|0.0124|0.9903|0.0672|0.0527|1.0000|
|synthid|tokenizer_only|5|240|1.25%|23.33%|0|0.0129|0.9877|0.0873|0.0745|1.0000|
|synthid|skd|5|240|0.42%|25.00%|0|0.0115|0.9955|0.0467|0.0381|1.0000|

## Paired score-reduction differences, percentile bootstrap 95% CI

|Scheme|k|Reference|Pairs|SKD minus reference|95% interval|
|---|---:|---|---:|---:|---|
|kgw|1|random_pool|239|-0.0130|[-0.0442, 0.0189]|
|kgw|1|entropy_only|239|-0.0076|[-0.0356, 0.0197]|
|kgw|2|random_pool|239|-0.0168|[-0.0603, 0.0249]|
|kgw|2|entropy_only|239|-0.0037|[-0.0430, 0.0335]|
|kgw|3|random_pool|239|-0.0251|[-0.0809, 0.0269]|
|kgw|3|entropy_only|239|-0.0101|[-0.0575, 0.0354]|
|kgw|5|random_pool|239|-0.0100|[-0.0742, 0.0504]|
|kgw|5|entropy_only|239|0.0012|[-0.0558, 0.0565]|
|synthid|1|random_pool|240|0.0001|[-0.0003, 0.0006]|
|synthid|1|entropy_only|240|0.0002|[-0.0001, 0.0006]|
|synthid|2|random_pool|240|0.0004|[-0.0002, 0.0009]|
|synthid|2|entropy_only|240|0.0005|[0.0000, 0.0011]|
|synthid|3|random_pool|240|0.0007|[-0.0001, 0.0015]|
|synthid|3|entropy_only|240|0.0008|[0.0002, 0.0013]|
|synthid|5|random_pool|240|0.0007|[-0.0001, 0.0016]|
|synthid|5|entropy_only|240|0.0006|[-0.0001, 0.0013]|

## Limits

All eligible attempts, including failures and abstentions. Quality-conditioned rates use the explicitly reported passing subset.

Positive paired difference favors SKD. Exact-k subset requires all selectors. Correlations deduplicate selected one-edit candidates; samples can contribute multiple candidates, so these are descriptive, dependent observations, not causal estimates.

Candidate coverage is measured on eligible baselines; ineligible samples are reported separately. Failed pools count as unavailable. Candidate-local semantic checks can miss factual drift. Shared feature signals may be correlated. Multi-edit combinations are validated structurally, with whole-text quality measured after finalization. Historical v0.2 denominators are separate. This experiment makes no cross-key or cross-scheme transfer claims. See quality.jsonl and metrics.json for .90/.95 quality-conditioned rates.
