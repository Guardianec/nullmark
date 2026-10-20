# Experiment 003 — Baseline Attack Benchmark

All eligible attempts, including failures and abstentions. Quality-conditioned rates use the explicitly reported passing subset.

One local Qwen model, one master/key configuration, a fresh prompt corpus and frozen v0.1.1 evaluators. Target FPR 1%; SynthID d20 weighted observed held-out FPR was 3/99 (3.03%). No calibration was fitted on this corpus.

Embedding cosine is semantic similarity, not factual correctness. The .90/.95 bands are descriptive operating points, not universal thresholds.

## Baseline eligibility

- kgw: 128/128 eligible (100.0%); miss 0.0%; abstention 0.0%.
- synthid: 128/128 eligible (100.0%); miss 0.0%; abstention 0.0%.

## Attack outcomes

|Scheme|Attack|Budget|Eligible|Complete|Evasion|Abstain|Δ score|Semantic|Word edit|
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
|kgw|random_edit|0.01|128|100.0%|0.0%|0.0%|0.093|1.000|0.005|
|kgw|random_edit|0.02|128|100.0%|0.0%|0.0%|0.136|1.000|0.008|
|kgw|random_edit|0.05|128|100.0%|0.0%|0.0%|0.148|1.000|0.009|
|kgw|random_edit|0.1|128|100.0%|0.0%|0.0%|0.148|1.000|0.009|
|kgw|random_edit|0.2|128|100.0%|0.0%|0.0%|0.148|1.000|0.009|
|synthid|random_edit|0.01|128|100.0%|0.0%|0.0%|0.002|1.000|0.005|
|synthid|random_edit|0.02|128|100.0%|0.0%|0.0%|0.003|1.000|0.008|
|synthid|random_edit|0.05|128|100.0%|0.0%|0.0%|0.003|1.000|0.009|
|synthid|random_edit|0.1|128|100.0%|0.0%|0.0%|0.003|1.000|0.009|
|synthid|random_edit|0.2|128|100.0%|0.0%|0.0%|0.003|1.000|0.009|
|kgw|synonym_replace|0.01|128|100.0%|0.0%|1.6%|0.047|0.998|0.004|
|kgw|synonym_replace|0.02|128|100.0%|0.0%|1.6%|0.080|0.997|0.006|
|kgw|synonym_replace|0.05|128|100.0%|0.0%|2.3%|0.101|0.997|0.008|
|kgw|synonym_replace|0.1|128|100.0%|0.0%|2.3%|0.101|0.997|0.008|
|kgw|synonym_replace|0.2|128|100.0%|0.0%|2.3%|0.101|0.997|0.008|
|synthid|synonym_replace|0.01|128|100.0%|0.0%|0.0%|0.001|0.998|0.004|
|synthid|synonym_replace|0.02|128|100.0%|0.0%|1.6%|0.003|0.997|0.007|
|synthid|synonym_replace|0.05|128|100.0%|0.0%|1.6%|0.003|0.997|0.008|
|synthid|synonym_replace|0.1|128|100.0%|0.0%|1.6%|0.003|0.997|0.008|
|synthid|synonym_replace|0.2|128|100.0%|0.0%|1.6%|0.003|0.997|0.008|
|kgw|paraphrase|None|128|100.0%|1.6%|22.7%|0.919|0.992|0.077|
|synthid|paraphrase|None|128|100.0%|5.5%|25.0%|0.017|0.991|0.081|
|kgw|entropy_rewrite|0.01|128|100.0%|0.0%|1.6%|0.064|0.998|0.004|
|kgw|entropy_rewrite|0.02|128|100.0%|0.0%|1.6%|0.077|0.998|0.006|
|kgw|entropy_rewrite|0.05|128|100.0%|0.0%|2.3%|0.101|0.997|0.008|
|kgw|entropy_rewrite|0.1|128|100.0%|0.0%|2.3%|0.101|0.997|0.008|
|kgw|entropy_rewrite|0.2|128|100.0%|0.0%|2.3%|0.101|0.997|0.008|
|synthid|entropy_rewrite|0.01|128|100.0%|0.0%|0.8%|0.002|0.998|0.004|
|synthid|entropy_rewrite|0.02|128|100.0%|0.0%|1.6%|0.002|0.997|0.007|
|synthid|entropy_rewrite|0.05|128|100.0%|0.0%|1.6%|0.003|0.997|0.008|
|synthid|entropy_rewrite|0.1|128|100.0%|0.0%|1.6%|0.003|0.997|0.008|
|synthid|entropy_rewrite|0.2|128|100.0%|0.0%|1.6%|0.003|0.997|0.008|

## Quality-conditioned evasion

|Scheme|Attack|Budget|Semantic band|Evasions / passing samples|Coverage|
|---|---|---:|---:|---:|---:|
|kgw|random_edit|0.01|≥0.9|0/128|100.0%|
|kgw|random_edit|0.01|≥0.95|0/128|100.0%|
|kgw|random_edit|0.02|≥0.9|0/128|100.0%|
|kgw|random_edit|0.02|≥0.95|0/128|100.0%|
|kgw|random_edit|0.05|≥0.9|0/128|100.0%|
|kgw|random_edit|0.05|≥0.95|0/128|100.0%|
|kgw|random_edit|0.1|≥0.9|0/128|100.0%|
|kgw|random_edit|0.1|≥0.95|0/128|100.0%|
|kgw|random_edit|0.2|≥0.9|0/128|100.0%|
|kgw|random_edit|0.2|≥0.95|0/128|100.0%|
|synthid|random_edit|0.01|≥0.9|0/128|100.0%|
|synthid|random_edit|0.01|≥0.95|0/128|100.0%|
|synthid|random_edit|0.02|≥0.9|0/128|100.0%|
|synthid|random_edit|0.02|≥0.95|0/128|100.0%|
|synthid|random_edit|0.05|≥0.9|0/128|100.0%|
|synthid|random_edit|0.05|≥0.95|0/128|100.0%|
|synthid|random_edit|0.1|≥0.9|0/128|100.0%|
|synthid|random_edit|0.1|≥0.95|0/128|100.0%|
|synthid|random_edit|0.2|≥0.9|0/128|100.0%|
|synthid|random_edit|0.2|≥0.95|0/128|100.0%|
|kgw|synonym_replace|0.01|≥0.9|0/128|100.0%|
|kgw|synonym_replace|0.01|≥0.95|0/128|100.0%|
|kgw|synonym_replace|0.02|≥0.9|0/128|100.0%|
|kgw|synonym_replace|0.02|≥0.95|0/127|99.2%|
|kgw|synonym_replace|0.05|≥0.9|0/128|100.0%|
|kgw|synonym_replace|0.05|≥0.95|0/127|99.2%|
|kgw|synonym_replace|0.1|≥0.9|0/128|100.0%|
|kgw|synonym_replace|0.1|≥0.95|0/127|99.2%|
|kgw|synonym_replace|0.2|≥0.9|0/128|100.0%|
|kgw|synonym_replace|0.2|≥0.95|0/127|99.2%|
|synthid|synonym_replace|0.01|≥0.9|0/128|100.0%|
|synthid|synonym_replace|0.01|≥0.95|0/128|100.0%|
|synthid|synonym_replace|0.02|≥0.9|0/128|100.0%|
|synthid|synonym_replace|0.02|≥0.95|0/127|99.2%|
|synthid|synonym_replace|0.05|≥0.9|0/128|100.0%|
|synthid|synonym_replace|0.05|≥0.95|0/127|99.2%|
|synthid|synonym_replace|0.1|≥0.9|0/128|100.0%|
|synthid|synonym_replace|0.1|≥0.95|0/127|99.2%|
|synthid|synonym_replace|0.2|≥0.9|0/128|100.0%|
|synthid|synonym_replace|0.2|≥0.95|0/127|99.2%|
|kgw|paraphrase|None|≥0.9|2/128|100.0%|
|kgw|paraphrase|None|≥0.95|2/127|99.2%|
|synthid|paraphrase|None|≥0.9|7/128|100.0%|
|synthid|paraphrase|None|≥0.95|6/126|98.4%|
|kgw|entropy_rewrite|0.01|≥0.9|0/128|100.0%|
|kgw|entropy_rewrite|0.01|≥0.95|0/128|100.0%|
|kgw|entropy_rewrite|0.02|≥0.9|0/128|100.0%|
|kgw|entropy_rewrite|0.02|≥0.95|0/128|100.0%|
|kgw|entropy_rewrite|0.05|≥0.9|0/128|100.0%|
|kgw|entropy_rewrite|0.05|≥0.95|0/127|99.2%|
|kgw|entropy_rewrite|0.1|≥0.9|0/128|100.0%|
|kgw|entropy_rewrite|0.1|≥0.95|0/127|99.2%|
|kgw|entropy_rewrite|0.2|≥0.9|0/128|100.0%|
|kgw|entropy_rewrite|0.2|≥0.95|0/127|99.2%|
|synthid|entropy_rewrite|0.01|≥0.9|0/128|100.0%|
|synthid|entropy_rewrite|0.01|≥0.95|0/128|100.0%|
|synthid|entropy_rewrite|0.02|≥0.9|0/128|100.0%|
|synthid|entropy_rewrite|0.02|≥0.95|0/127|99.2%|
|synthid|entropy_rewrite|0.05|≥0.9|0/128|100.0%|
|synthid|entropy_rewrite|0.05|≥0.95|0/127|99.2%|
|synthid|entropy_rewrite|0.1|≥0.9|0/128|100.0%|
|synthid|entropy_rewrite|0.1|≥0.95|0/127|99.2%|
|synthid|entropy_rewrite|0.2|≥0.9|0/128|100.0%|
|synthid|entropy_rewrite|0.2|≥0.95|0/127|99.2%|

## Interpretation

- kgw: largest measured evasion is paraphrase at budget None (1.6%); highest mean semantic similarity is random_edit at budget 0.01. Compare actual edits, failures and quality bands before interpreting this ordering.
- kgw: largest paired mean score reduction is paraphrase at None: 0.919. This is a within-scheme comparison only.
- kgw: sparse requested budgets with at least one observed evasion: none. This is a fixed sweep, not an estimate of the minimum successful edit budget.
- kgw, requested 1%: entropy evasion 0.0%, random 0.0%; mean actual word edits 0.004 vs 0.005. Different candidate availability prevents attributing the whole difference to position selection alone.
- kgw, requested 2%: entropy evasion 0.0%, random 0.0%; mean actual word edits 0.006 vs 0.008. Different candidate availability prevents attributing the whole difference to position selection alone.
- kgw, requested 5%: entropy evasion 0.0%, random 0.0%; mean actual word edits 0.008 vs 0.009. Different candidate availability prevents attributing the whole difference to position selection alone.
- kgw, requested 10%: entropy evasion 0.0%, random 0.0%; mean actual word edits 0.008 vs 0.009. Different candidate availability prevents attributing the whole difference to position selection alone.
- kgw, requested 20%: entropy evasion 0.0%, random 0.0%; mean actual word edits 0.008 vs 0.009. Different candidate availability prevents attributing the whole difference to position selection alone.
- synthid: largest measured evasion is paraphrase at budget None (5.5%); highest mean semantic similarity is random_edit at budget 0.01. Compare actual edits, failures and quality bands before interpreting this ordering.
- synthid: largest paired mean score reduction is paraphrase at None: 0.017. This is a within-scheme comparison only.
- synthid: sparse requested budgets with at least one observed evasion: none. This is a fixed sweep, not an estimate of the minimum successful edit budget.
- synthid, requested 1%: entropy evasion 0.0%, random 0.0%; mean actual word edits 0.004 vs 0.005. Different candidate availability prevents attributing the whole difference to position selection alone.
- synthid, requested 2%: entropy evasion 0.0%, random 0.0%; mean actual word edits 0.007 vs 0.008. Different candidate availability prevents attributing the whole difference to position selection alone.
- synthid, requested 5%: entropy evasion 0.0%, random 0.0%; mean actual word edits 0.008 vs 0.009. Different candidate availability prevents attributing the whole difference to position selection alone.
- synthid, requested 10%: entropy evasion 0.0%, random 0.0%; mean actual word edits 0.008 vs 0.009. Different candidate availability prevents attributing the whole difference to position selection alone.
- synthid, requested 20%: entropy evasion 0.0%, random 0.0%; mean actual word edits 0.008 vs 0.009. Different candidate availability prevents attributing the whole difference to position selection alone.

Score units differ between KGW and SynthID; compare within each scheme. Sparse budgets are upper bounds: safe candidates can run out. Abstention is not evasion. Failures remain in all-eligible denominators. No minimum successful budget search was performed. Human inspection is required for factual drift, grammar and truncated source generations.
