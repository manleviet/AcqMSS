# Evaluation Results

Generated from: data/results

KB Mapping: KB1=REAL-FM-7, KB2=fqa, KB3=arcade, KB4=REAL-FM-4


# Paper Tables (Incremental)

## Table 7: ACQMSS #consistency checks and runtime (msec) - Incremental Mode

| Strategy | |E+| | |E-| | KB1 | KB2 | KB3 | KB4 |
|:---|---:|---:|:---:|:---:|:---:|:---:|
| RS(1n) | - | - | - | - | - | - |
| RS(2n) | - | - | - | - | - | - |
| RS(3n) | - | - | - | - | - | - |
| RS(m) | - | - | - | - | - | - |
| 2-COV | - | - | - | - | - | - |
| FF | - | - | - | - | - | - |

## Table 9: Accuracy with Random Sampling (RS) - Incremental Mode

| Strategy | KB1 | KB2 | KB3 | KB4 |
|:---|:---:|:---:|:---:|:---:|
| RS(1n) | - | - | - | - |
| RS(2n) | - | - | - | - |
| RS(3n) | - | - | - | - |
| RS(m) | - | - | - | - |

## Table 10: Accuracy with 2-wise coverage (2-COV) - Incremental Mode

| KB | Accuracy |
|:---|:---:|
| KB1 | - |
| KB2 | - |
| KB3 | - |
| KB4 | - |

## Table 11: Accuracy with Feature Frequency (FF) - Incremental Mode

| KB | Accuracy |
|:---|:---:|
| KB1 | - |
| KB2 | - |
| KB3 | - |
| KB4 | - |

# Additional Tables (Incremental)

## Table: Accuracy (Compact) - Incremental Mode

| KB | RS(1n) | RS(2n) | RS(3n) | RS(m) | 2-COV | FF |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| KB1 | - | - | - | - | - | - |

## Table: Accuracy by Sampling Strategy (Incremental)

| KB | RS(1n) | RS(2n) | RS(3n) | RS(m) | 2-COV | FF |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| KB1 | - | - | - | - | - | - |

## Table: Runtime (ms) - Incremental Mode

| KB | RS(1n) | RS(2n) | RS(3n) | RS(m) | 2-COV | FF |
|:---|---:|---:|---:|---:|---:|---:|
| KB1 | - | - | - | - | - | - |

## Table: Consistency Checks - Incremental Mode

| KB | RS(1n) | RS(2n) | RS(3n) | RS(m) | 2-COV | FF |
|:---|---:|---:|---:|---:|---:|---:|
| KB1 | - | - | - | - | - | - |

## Table: Performance Metrics (Incremental)

| KB | Strategy | Runtime (ms) | #Checks | Memory (MB) | n_bias | n_mss | n_kb |
|:---|:---|---:|---:|---:|---:|---:|---:|

## Table: KB Summary (Incremental)

| KB | Strategy | n_bias | n_kb (mean) | n_intersected | Reduction |
|:---|:---|---:|---:|---:|---:|

# Paper Tables (Non-incremental)

## Table 7: ACQMSS #consistency checks and runtime (msec) - Non-incremental Mode

| Strategy | |E+| | |E-| | KB1 | KB2 | KB3 | KB4 |
|:---|---:|---:|:---:|:---:|:---:|:---:|
| RS(1n) | 8 | 0 | 598 / 193.5 | - | - | - |
| RS(2n) | 17 | 1 | 599 / 236.1 | - | - | - |
| RS(3n) | 25 | 2 | 599 / 280.0 | - | - | - |
| RS(m) | 5 | 0 | 589 / 190.5 | - | - | - |
| 2-COV | 0 | 6 | 301 / 70.5 | - | - | - |
| FF | 4 | 2 | 588 / 159.7 | - | - | - |

## Table 9: Accuracy with Random Sampling (RS) - Non-incremental Mode

| Strategy | KB1 | KB2 | KB3 | KB4 |
|:---|:---:|:---:|:---:|:---:|
| RS(1n) | 0.2778 ± 0.0481 | - | - | - |
| RS(2n) | 0.5583 ± 0.2184 | - | - | - |
| RS(3n) | 0.8603 ± 0.1430 | - | - | - |
| RS(m) | 0.1944 ± 0.1735 | - | - | - |

## Table 10: Accuracy with 2-wise coverage (2-COV) - Non-incremental Mode

| KB | Accuracy |
|:---|:---:|
| KB1 | 1.0000 ± 0.0000 |
| KB2 | - |
| KB3 | - |
| KB4 | - |

## Table 11: Accuracy with Feature Frequency (FF) - Non-incremental Mode

| KB | Accuracy |
|:---|:---:|
| KB1 | 0.4444 ± 0.1925 |
| KB2 | - |
| KB3 | - |
| KB4 | - |

# Additional Tables (Non-incremental)

## Table: Accuracy (Compact) - Non-incremental Mode

| KB | RS(1n) | RS(2n) | RS(3n) | RS(m) | 2-COV | FF |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| KB1 | 0.28±0.05 | 0.56±0.22 | 0.86±0.14 | 0.19±0.17 | 1.00±0.00 | 0.44±0.19 |

## Table: Accuracy by Sampling Strategy (Non-incremental)

| KB | RS(1n) | RS(2n) | RS(3n) | RS(m) | 2-COV | FF |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| KB1 | 0.2778 ± 0.0481 | 0.5583 ± 0.2184 | 0.8603 ± 0.1430 | 0.1944 ± 0.1735 | 1.0000 ± 0.0000 | 0.4444 ± 0.1925 |

## Table: Runtime (ms) - Non-incremental Mode

| KB | RS(1n) | RS(2n) | RS(3n) | RS(m) | 2-COV | FF |
|:---|---:|---:|---:|---:|---:|---:|
| KB1 | 194 | 236 | 280 | 191 | 70 | 160 |

## Table: Consistency Checks - Non-incremental Mode

| KB | RS(1n) | RS(2n) | RS(3n) | RS(m) | 2-COV | FF |
|:---|---:|---:|---:|---:|---:|---:|
| KB1 | 598 | 599 | 599 | 589 | 301 | 588 |

## Table: Performance Metrics (Non-incremental)

| KB | Strategy | Runtime (ms) | #Checks | Memory (MB) | n_bias | n_mss | n_kb |
|:---|:---|---:|---:|---:|---:|---:|---:|
| KB1 | RS(1n) | 193.53 ± 14.65 | 598 ± 7 | 0.33 | 295 | 91.7 | 18.7 |
| KB1 | RS(2n) | 236.10 ± 21.04 | 599 ± 3 | 0.38 | 295 | 69.0 | 18.3 |
| KB1 | RS(3n) | 279.97 ± 43.36 | 599 ± 6 | 0.43 | 295 | 61.7 | 15.0 |
| KB1 | RS(m) | 190.53 ± 16.56 | 589 ± 11 | 0.30 | 295 | 131.7 | 19.7 |
| KB1 | 2-COV | 70.50 ± 0.54 | 301 ± 0 | 0.26 | 295 | 294.0 | 15.7 |
| KB1 | FF | 159.74 ± 5.41 | 588 ± 6 | 0.28 | 295 | 142.3 | 19.3 |

## Table: KB Summary (Non-incremental)

| KB | Strategy | n_bias | n_kb (mean) | n_intersected | Reduction |
|:---|:---|---:|---:|---:|---:|
| KB1 | RS(1n) | 295 | 18.7 | 2 | 93.7% |
| KB1 | RS(2n) | 295 | 18.3 | 4 | 93.8% |
| KB1 | RS(3n) | 295 | 15.0 | 2 | 94.9% |
| KB1 | RS(m) | 295 | 19.7 | 1 | 93.3% |
| KB1 | 2-COV | 295 | 15.7 | 0 | 94.7% |
| KB1 | FF | 295 | 19.3 | 0 | 93.4% |

## Table: Incremental vs Non-Incremental Comparison

| KB | Strategy | Mode | Accuracy | Runtime (ms) | #Checks |
|:---|:---|:---|---:|---:|---:|
| KB1 | RS(1n) | Non-Inc | 0.2778 | 193.53 | 598 |
| KB1 | RS(2n) | Non-Inc | 0.5583 | 236.10 | 599 |
| KB1 | RS(3n) | Non-Inc | 0.8603 | 279.97 | 599 |
| KB1 | RS(m) | Non-Inc | 0.1944 | 190.53 | 589 |
| KB1 | 2-COV | Non-Inc | 1.0000 | 70.50 | 301 |
| KB1 | FF | Non-Inc | 0.4444 | 159.74 | 588 |