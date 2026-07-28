# eval-prf

Semantic precision / recall / F1 and $|\KB|$ per KB (exclude-2COV means; $^{\dagger}$ = non-converged: \texttt{max\_queries} budget or wall-clock timeout, per-KB reason in Table~\ref{tab:app-quacq-diag}). The 5th condition \textsc{QuAcq} (example-only) is reported in Table~\ref{tab:app-perset}; accuracy/specificity in Table~\ref{tab:app-accuracy}.

groups: A (×4), C (×4), ConMin (×4), QuAcq-a (×4)

| KB | P | R | F1 | $|KB|$ | P | R | F1 | $|KB|$ | P | R | F1 | $|KB|$ | P | R | F1 | $|KB|$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| $KB_{1}$ | 0.49 | 0.95 | 0.60 | 99.3 | 0.87 | 0.11 | 0.19 | 0.9 | 0.80 | 0.90 | **0.85** | 14.9 | 1.00 | 0.73 | 0.84 | 12.0 |
| $KB_{2}$ | 0.77 | 1.00 | **0.87** | 252.9 | 0.91 | 0.05 | 0.09 | 1.2 | 0.89 | 0.75 | 0.78 | 108.5 | 1.00† | 0.03† | 0.06† | 6.0† |
| $KB_{3}$ | 0.24 | 0.99 | 0.38 | 641.9 | 0.88 | 0.02 | 0.05 | 1.3 | 0.55 | 0.84 | **0.64** | 162.0 | 1.00† | 0.29† | 0.45† | 27.0† |
| $KB_{4}$ | 0.49 | 1.00 | 0.64 | 822.5 | 0.46 | 0.02 | 0.03 | 1.3 | 0.79 | 0.81 | **0.78** | 223.4 | 1.00† | 0.10† | 0.18† | 26.0† |
| $KB_{5}$ | 0.60 | 1.00 | 0.73 | 3,047.7 | 0.92 | 0.01 | 0.02 | 1.8 | 0.80 | 0.87 | **0.83** | 949.2 | 1.00† | 0.02† | 0.04† | 11.0† |
