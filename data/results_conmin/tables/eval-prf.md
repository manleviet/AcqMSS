# eval-prf

Semantic precision / recall / F1 and $|\KB|$ per KB, all five conditions. Values are means over the samplings other than 2-COV, five per knowledge base and two on $KB_5$, and over the three folds. A dagger marks a run that did not converge, stopped by the \texttt{max\_queries} budget or by the wall clock, whose figures are therefore lower bounds.

groups: A (×2), C (×2), ConMin (×2), QuAcq-ex (×2), QuAcq (×2)

| KB ($|C_tau|$) | P/R/F1 | $|KB|$ | P/R/F1 | $|KB|$ | P/R/F1 | $|KB|$ | P/R/F1 | $|KB|$ | P/R/F1 | $|KB|$ |
|---|---|---|---|---|---|---|---|---|---|---|
| $KB_{1}$ (13) | .49/.95/.60 | 99.3 | .87/.11/.19 | 0.9 | .80/.90/**.85** | 14.9 | .13/.01/.01 | 0.1 | 1.00/.73/.84 | 12.0 |
| $KB_{2}$ (102) | .77/1.00/**.87** | 252.9 | .91/.05/.09 | 1.2 | .89/.75/.78 | 108.5 | .80/.01/.02 | 2.3 | 1.00†/.03†/.06† | 6.0† |
| $KB_{3}$ (70) | .24/.99/.38 | 641.9 | .88/.02/.05 | 1.3 | .55/.84/**.64** | 162.0 | .93/.01/.02 | 1.3 | 1.00†/.29†/.45† | 27.0† |
| $KB_{4}$ (219) | .49/1.00/.64 | 822.5 | .46/.02/.03 | 1.3 | .79/.81/**.78** | 223.4 | .87/.01/.02 | 2.6 | 1.00†/.10†/.18† | 26.0† |
| $KB_{5}$ (905) | .60/1.00/.73 | 3,048 | .92/.01/.02 | 1.8 | .80/.87/**.83** | 949.2 | 1.00/.01/.01 | 5.0 | 1.00†/.02†/.04† | 11.0† |
