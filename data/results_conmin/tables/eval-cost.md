# eval-cost

Learning cost. \textsc{ConMin}(raw,$k{=}1$) sizes/checks/time; \textsc{QuAcq} time+queries. budget/$|B|$ = \texttt{max\_queries}$/|B|$, the query budget fixed before the run (busybox $0.75<1$, below $|B|$) — independent of the stop reason; on a wall-clock timeout t(s) is the timeout wall and queries the count reached, but the budget was still \texttt{max\_queries}. Exclude-2COV means.

| KB | $|A|$ | $|C|$ | $supp$ | $|U|$ | checks | t(s) | QuAcq t(s) | q | QuAcq-a t(s) | q | budget/$|B|$ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| $KB_{1}$ | 99.3 | 0.9 | 77.0 | 0.0 | 510 | 1.2 | 0.1 | 18.7 | 1.9 | 272.0 | 16.9 |
| $KB_{2}$ | 252.9 | 1.2 | 176.9 | 0.0 | 604 | 28.1 | 6.5 | 69.0 | 245.1† | 5,000.0† | 10.9 |
| $KB_{3}$ | 641.9 | 1.3 | 342.0 | 0.0 | 2,919 | 168.9 | 8.9 | 58.9 | 5,213.4† | 5,000.0† | 2.8 |
| $KB_{4}$ | 822.5 | 1.3 | 511.3 | 0.0 | 3,359 | 4,729.8 | 103.6 | 117.3 | 15,490.7† | 5,000.0† | 2.4 |
| $KB_{5}$ | 3,047.7 | 1.8 | 1,360.2 | 0.0 | 10,676 | 59,905.0 | 3,568.4 | 296.3 | 36,754.4† | 1,901.0† | 0.75 |
