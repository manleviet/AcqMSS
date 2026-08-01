# app-sampling

Sensitivity of \textsc{ConMin} to the example sampling, at raw negatives and $k=1$, rows ordered by training positives. $|E^+|$ and $|E^-|$ are training examples per fold and $|A|/|B|$ is the fraction of the bias the pool retains, both averaged over $KB_{1}$ to $KB_{4}$. $KB_{5}$ is excluded because the RS-$2n$, RS-$3n$ and RS-$m$ samplings are infeasible on it. Bold marks the best F1 per column.

groups: training set (×2),   (×5), F1 per KB (×4)

| sampling | $|E^+|$ | $|E^-|$ | $|A|/|B|$ | $|KB|$ | P | R | F1 | $KB_{1}$ | $KB_{2}$ | $KB_{3}$ | $KB_{4}$ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2-COV | 0.3 | 9.2 | 90\% | 48.5 | .80 | .41 | .43 | .43 | .08 | .59 | .61 |
| RS-$m$ | 8.8 | 0.7 | 64\% | 59.0 | .82 | .54 | .61 | .80 | .41 | .69 | .56 |
| FF | 29.7 | 3.7 | 50\% | 105.6 | .77 | .75 | .75 | .77 | .76 | **.71** | .77 |
| RS-$n$ | 82.7 | 8.8 | 36\% | 144.1 | .71 | .89 | .78 | .85 | .87 | .60 | .80 |
| RS-$2n$ | 165.0 | 18.0 | 30\% | 166.7 | .72 | .96 | .81 | .88 | .92 | .58 | .86 |
| RS-$3n$ | 247.3 | 27.2 | 27\% | 160.7 | .77 | .98 | **.85** | **.94** | **.95** | .61 | **.89** |
