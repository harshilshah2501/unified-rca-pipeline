# Report 09 — Design v3 Stage 4.2 layout screen (≤5M)

**This is a screening report of crossover candidates — not a production architecture recommendation.**

Identical pre-generated query traces are replayed across layouts for each `(family, scale, profile)`.
Hybrid runs with **zero mutation churn**. Primary edge order is clustered; natural order is a 500k control.

**Coverage this pass:** full factorial at **500k** (six families × three profiles × five layouts, plus natural-order control) and **1M** (same without natural). At **5M**, only a thin ceiling ladder — `uniform` and `hubby` × `balanced` × five layouts — plus the earlier `uniform` × `forward_dominant` cells from the aborted full matrix. Remaining 5M family×profile cells were **skipped** (not OOM) to keep wall-clock bounded; see `status.log`.

Source: `out/design-v3/stage4/screen` — 225 scenario rows.

## Per-cell metrics

| Cell | Layout | Build ms (med) | Fwd p50 | Fwd p95 | Rev p50 | Rev p95 | Peak RSS | Steady idx B | OK |
| ---- | ------ | -------------: | ------: | ------: | ------: | ------: | -------: | -----------: | -- |
| 1M-community-clustered-balanced-csr | csr | 835.8 | 0.011 | 0.100 | 10.038 | 50.064 | 364265472 | 57408185 | True |
| 1M-community-clustered-balanced-csr-csc | csr_csc | 1310.4 | 0.006 | 0.036 | 0.004 | 0.027 | 365367296 | 96476528 | True |
| 1M-community-clustered-balanced-hash | hash | 379.2 | 0.016 | 0.145 | 73.487 | 372.563 | 367857664 | 116397047 | True |
| 1M-community-clustered-balanced-hash-bi | hash_bi | 845.8 | 0.006 | 0.051 | 0.004 | 0.036 | 492388352 | 216290352 | True |
| 1M-community-clustered-balanced-hybrid | hybrid | 1232.0 | 0.008 | 0.041 | 0.005 | 0.029 | 367034368 | 96476528 | True |
| 1M-community-clustered-forward-dominant-csr | csr | 817.7 | 0.004 | 0.050 | 10.643 | 42.792 | 364048384 | 57408185 | True |
| 1M-community-clustered-forward-dominant-csr-csc | csr_csc | 1164.8 | 0.003 | 0.014 | 0.007 | 0.027 | 369987584 | 96476528 | True |
| 1M-community-clustered-forward-dominant-hash | hash | 442.8 | 0.006 | 0.088 | 71.210 | 275.812 | 366317568 | 116397047 | True |
| 1M-community-clustered-forward-dominant-hash-bi | hash_bi | 862.0 | 0.004 | 0.019 | 0.006 | 0.045 | 488185856 | 216290352 | True |
| 1M-community-clustered-forward-dominant-hybrid | hybrid | 1159.3 | 0.005 | 0.027 | 0.006 | 0.042 | 367038464 | 96476528 | True |
| 1M-community-clustered-reverse-heavy-csr | csr | 900.8 | 0.023 | 0.164 | 14.121 | 111.396 | 355012608 | 57408185 | True |
| 1M-community-clustered-reverse-heavy-csr-csc | csr_csc | 1260.5 | 0.008 | 0.079 | 0.004 | 0.040 | 367489024 | 96476528 | True |
| 1M-community-clustered-reverse-heavy-hash | hash | 407.5 | 0.049 | 0.320 | 103.835 | 855.391 | 362770432 | 116397047 | True |
| 1M-community-clustered-reverse-heavy-hash-bi | hash_bi | 937.8 | 0.012 | 0.135 | 0.005 | 0.071 | 500572160 | 216290352 | True |
| 1M-community-clustered-reverse-heavy-hybrid | hybrid | 1227.6 | 0.014 | 0.103 | 0.007 | 0.056 | 375382016 | 96476528 | True |
| 1M-hierarchical-clustered-balanced-csr | csr | 553.0 | 0.006 | 0.247 | 5.673 | 136.454 | 369090560 | 58995510 | True |
| 1M-hierarchical-clustered-balanced-csr-csc | csr_csc | 1094.8 | 0.002 | 0.092 | 0.005 | 0.094 | 372760576 | 99998385 | True |
| 1M-hierarchical-clustered-balanced-hash | hash | 358.5 | 0.011 | 0.510 | 50.104 | 2465.734 | 376864768 | 129290117 | True |
| 1M-hierarchical-clustered-balanced-hash-bi | hash_bi | 755.2 | 0.003 | 0.137 | 0.008 | 0.159 | 516235264 | 233679413 | True |
| 1M-hierarchical-clustered-balanced-hybrid | hybrid | 937.7 | 0.003 | 0.183 | 0.009 | 0.190 | 368361472 | 99998385 | True |
| 1M-hierarchical-clustered-forward-dominant-csr | csr | 601.1 | 0.008 | 0.240 | 12.579 | 90.800 | 373694464 | 58995510 | True |
| 1M-hierarchical-clustered-forward-dominant-csr-csc | csr_csc | 1004.7 | 0.008 | 0.133 | 0.015 | 0.197 | 371318784 | 99998385 | True |
| 1M-hierarchical-clustered-forward-dominant-hash | hash | 322.6 | 0.010 | 0.380 | 204.472 | 1386.835 | 385683456 | 129290117 | True |
| 1M-hierarchical-clustered-forward-dominant-hash-bi | hash_bi | 701.4 | 0.009 | 0.137 | 0.020 | 0.245 | 499081216 | 233679413 | True |
| 1M-hierarchical-clustered-forward-dominant-hybrid | hybrid | 963.0 | 0.011 | 0.156 | 0.019 | 0.187 | 373145600 | 99998385 | True |
| 1M-hierarchical-clustered-reverse-heavy-csr | csr | 681.5 | 0.038 | 0.651 | 7.115 | 101.645 | 368349184 | 58995510 | True |
| 1M-hierarchical-clustered-reverse-heavy-csr-csc | csr_csc | 1020.3 | 0.013 | 0.348 | 0.005 | 0.083 | 361705472 | 99998385 | True |
| 1M-hierarchical-clustered-reverse-heavy-hash | hash | 343.4 | 0.049 | 1.481 | 124.595 | 1753.060 | 381648896 | 129290117 | True |
| 1M-hierarchical-clustered-reverse-heavy-hash-bi | hash_bi | 894.6 | 0.021 | 0.643 | 0.007 | 0.169 | 503816192 | 233679413 | True |
| 1M-hierarchical-clustered-reverse-heavy-hybrid | hybrid | 1022.3 | 0.027 | 0.751 | 0.010 | 0.178 | 376549376 | 99998385 | True |
| 1M-hubby-clustered-balanced-csr | csr | 852.3 | 0.007 | 0.040 | 16.756 | 123.957 | 339943424 | 57395901 | True |
| 1M-hubby-clustered-balanced-csr-csc | csr_csc | 1357.3 | 0.002 | 0.012 | 0.006 | 0.063 | 371269632 | 96455904 | True |
| 1M-hubby-clustered-balanced-hash | hash | 407.2 | 0.010 | 0.055 | 105.002 | 705.532 | 372965376 | 127042437 | True |
| 1M-hubby-clustered-balanced-hash-bi | hash_bi | 923.9 | 0.003 | 0.020 | 0.008 | 0.057 | 500908032 | 225076756 | True |
| 1M-hubby-clustered-balanced-hybrid | hybrid | 1217.1 | 0.004 | 0.025 | 0.015 | 0.119 | 362274816 | 96455904 | True |
| 1M-hubby-clustered-forward-dominant-csr | csr | 893.4 | 0.004 | 0.034 | 18.388 | 114.035 | 371134464 | 57395901 | True |
| 1M-hubby-clustered-forward-dominant-csr-csc | csr_csc | 1271.1 | 0.002 | 0.010 | 0.007 | 0.087 | 361500672 | 96455904 | True |
| 1M-hubby-clustered-forward-dominant-hash | hash | 405.2 | 0.004 | 0.056 | 99.998 | 584.785 | 383823872 | 127042437 | True |
| 1M-hubby-clustered-forward-dominant-hash-bi | hash_bi | 1012.7 | 0.003 | 0.016 | 0.014 | 0.145 | 497528832 | 225076756 | True |
| 1M-hubby-clustered-forward-dominant-hybrid | hybrid | 1262.3 | 0.003 | 0.014 | 0.012 | 0.128 | 361840640 | 96455904 | True |
| 1M-hubby-clustered-reverse-heavy-csr | csr | 898.0 | 0.020 | 2.249 | 10.901 | 68.065 | 366190592 | 57395901 | True |
| 1M-hubby-clustered-reverse-heavy-csr-csc | csr_csc | 1025.8 | 0.008 | 1.608 | 0.003 | 0.052 | 359399424 | 96455904 | True |
| 1M-hubby-clustered-reverse-heavy-hash | hash | 481.6 | 0.039 | 4.865 | 71.912 | 430.276 | 362967040 | 127042437 | True |
| 1M-hubby-clustered-reverse-heavy-hash-bi | hash_bi | 886.6 | 0.014 | 3.954 | 0.006 | 0.101 | 505200640 | 225076756 | True |
| 1M-hubby-clustered-reverse-heavy-hybrid | hybrid | 973.6 | 0.011 | 2.339 | 0.006 | 0.087 | 366178304 | 96455904 | True |
| 1M-layered-clustered-balanced-csr | csr | 661.5 | 0.008 | 0.057 | 2.514 | 172.256 | 321253376 | 54624010 | True |
| 1M-layered-clustered-balanced-csr-csc | csr_csc | 1079.3 | 0.003 | 0.040 | 0.002 | 0.041 | 343523328 | 91576746 | True |
| 1M-layered-clustered-balanced-hash | hash | 333.1 | 0.020 | 0.123 | 17.645 | 1294.827 | 330399744 | 107613450 | True |
| 1M-layered-clustered-balanced-hash-bi | hash_bi | 787.2 | 0.003 | 0.043 | 0.001 | 0.052 | 464728064 | 203935314 | True |
| 1M-layered-clustered-balanced-hybrid | hybrid | 1088.0 | 0.004 | 0.036 | 0.002 | 0.068 | 352907264 | 91576746 | True |
| 1M-layered-clustered-forward-dominant-csr | csr | 706.8 | 0.007 | 0.041 | 12.892 | 30.697 | 326901760 | 54624010 | True |
| 1M-layered-clustered-forward-dominant-csr-csc | csr_csc | 1006.6 | 0.002 | 0.021 | 0.007 | 0.016 | 347987968 | 91576746 | True |
| 1M-layered-clustered-forward-dominant-hash | hash | 326.9 | 0.009 | 0.076 | 73.190 | 179.119 | 320303104 | 107613450 | True |
| 1M-layered-clustered-forward-dominant-hash-bi | hash_bi | 797.5 | 0.003 | 0.022 | 0.007 | 0.017 | 475316224 | 203935314 | True |
| 1M-layered-clustered-forward-dominant-hybrid | hybrid | 1033.0 | 0.004 | 0.033 | 0.005 | 0.018 | 343232512 | 91576746 | True |
| 1M-layered-clustered-reverse-heavy-csr | csr | 634.0 | 0.021 | 0.100 | 9.526 | 156.902 | 321515520 | 54624010 | True |
| 1M-layered-clustered-reverse-heavy-csr-csc | csr_csc | 916.7 | 0.006 | 0.032 | 0.002 | 0.035 | 348061696 | 91576746 | True |
| 1M-layered-clustered-reverse-heavy-hash | hash | 336.8 | 0.041 | 0.194 | 64.099 | 1110.438 | 321757184 | 107613450 | True |
| 1M-layered-clustered-reverse-heavy-hash-bi | hash_bi | 773.4 | 0.010 | 0.050 | 0.003 | 0.071 | 466530304 | 203935314 | True |
| 1M-layered-clustered-reverse-heavy-hybrid | hybrid | 890.6 | 0.011 | 0.057 | 0.004 | 0.057 | 348114944 | 91576746 | True |
| 1M-power-law-clustered-balanced-csr | csr | 612.0 | 0.093 | 6.643 | 3.999 | 36.388 | 309379072 | 57335521 | True |
| 1M-power-law-clustered-balanced-csr-csc | csr_csc | 984.8 | 0.056 | 6.511 | 0.008 | 0.092 | 362541056 | 96389465 | True |
| 1M-power-law-clustered-balanced-hash | hash | 192.3 | 0.142 | 15.473 | 42.415 | 325.178 | 352403456 | 111398231 | True |
| 1M-power-law-clustered-balanced-hash-bi | hash_bi | 533.5 | 0.096 | 12.012 | 0.012 | 0.170 | 480600064 | 209383453 | True |
| 1M-power-law-clustered-balanced-hybrid | hybrid | 961.2 | 0.161 | 10.581 | 0.015 | 0.150 | 365785088 | 96389465 | True |
| 1M-power-law-clustered-forward-dominant-csr | csr | 734.3 | 0.012 | 3.093 | 4.859 | 22.822 | 310210560 | 57335521 | True |
| 1M-power-law-clustered-forward-dominant-csr-csc | csr_csc | 1050.9 | 0.007 | 2.419 | 0.011 | 0.059 | 360476672 | 96389465 | True |
| 1M-power-law-clustered-forward-dominant-hash | hash | 194.3 | 0.019 | 6.271 | 29.374 | 161.686 | 360734720 | 111398231 | True |
| 1M-power-law-clustered-forward-dominant-hash-bi | hash_bi | 543.5 | 0.019 | 7.078 | 0.027 | 0.111 | 522100736 | 209383453 | True |
| 1M-power-law-clustered-forward-dominant-hybrid | hybrid | 1038.1 | 0.013 | 4.605 | 0.018 | 0.101 | 365694976 | 96389465 | True |
| 1M-power-law-clustered-reverse-heavy-csr | csr | 720.8 | 1.103 | 15.684 | 6.106 | 41.592 | 300195840 | 57335521 | True |
| 1M-power-law-clustered-reverse-heavy-csr-csc | csr_csc | 993.4 | 0.979 | 14.780 | 0.009 | 0.105 | 361730048 | 96389465 | True |
| 1M-power-law-clustered-reverse-heavy-hash | hash | 212.3 | 2.185 | 28.793 | 40.406 | 245.544 | 364990464 | 111398231 | True |
| 1M-power-law-clustered-reverse-heavy-hash-bi | hash_bi | 651.9 | 1.267 | 25.994 | 0.012 | 0.118 | 495591424 | 209383453 | True |
| 1M-power-law-clustered-reverse-heavy-hybrid | hybrid | 1054.7 | 1.342 | 23.898 | 0.019 | 0.154 | 354512896 | 96389465 | True |
| 1M-uniform-clustered-balanced-csr | csr | 780.3 | 0.012 | 0.137 | 11.736 | 100.217 | 359194624 | 57400989 | True |
| 1M-uniform-clustered-balanced-csr-csc | csr_csc | 1097.3 | 0.003 | 0.038 | 0.004 | 0.035 | 362467328 | 96461388 | True |
| 1M-uniform-clustered-balanced-hash | hash | 462.5 | 0.018 | 0.264 | 73.533 | 749.785 | 371855360 | 116379550 | True |
| 1M-uniform-clustered-balanced-hash-bi | hash_bi | 945.1 | 0.007 | 0.112 | 0.009 | 0.107 | 502800384 | 214426970 | True |
| 1M-uniform-clustered-balanced-hybrid | hybrid | 1102.7 | 0.007 | 0.084 | 0.009 | 0.091 | 370515968 | 96461388 | True |
| 1M-uniform-clustered-forward-dominant-csr | csr | 742.8 | 0.006 | 0.088 | 11.949 | 91.994 | 357859328 | 57400989 | True |
| 1M-uniform-clustered-forward-dominant-csr-csc | csr_csc | 1242.5 | 0.005 | 0.035 | 0.011 | 0.106 | 365678592 | 96461388 | True |
| 1M-uniform-clustered-forward-dominant-hash | hash | 433.8 | 0.011 | 0.192 | 97.264 | 734.046 | 345526272 | 116379550 | True |
| 1M-uniform-clustered-forward-dominant-hash-bi | hash_bi | 964.8 | 0.007 | 0.044 | 0.017 | 0.162 | 490176512 | 214426970 | True |
| 1M-uniform-clustered-forward-dominant-hybrid | hybrid | 1120.4 | 0.009 | 0.062 | 0.017 | 0.164 | 355901440 | 96461388 | True |
| 1M-uniform-clustered-reverse-heavy-csr | csr | 746.8 | 0.028 | 0.213 | 14.117 | 82.742 | 359653376 | 57400989 | True |
| 1M-uniform-clustered-reverse-heavy-csr-csc | csr_csc | 1093.1 | 0.008 | 0.099 | 0.004 | 0.050 | 365486080 | 96461388 | True |
| 1M-uniform-clustered-reverse-heavy-hash | hash | 481.6 | 0.063 | 0.522 | 110.483 | 667.586 | 354410496 | 116379550 | True |
| 1M-uniform-clustered-reverse-heavy-hash-bi | hash_bi | 941.0 | 0.013 | 0.137 | 0.006 | 0.062 | 490569728 | 214426970 | True |
| 1M-uniform-clustered-reverse-heavy-hybrid | hybrid | 1078.3 | 0.014 | 0.125 | 0.007 | 0.083 | 362061824 | 96461388 | True |
| 500k-community-clustered-balanced-csr | csr | 345.3 | 0.011 | 0.073 | 5.000 | 34.670 | 187736064 | 28703595 | True |
| 500k-community-clustered-balanced-csr-csc | csr_csc | 515.2 | 0.003 | 0.020 | 0.002 | 0.022 | 192548864 | 48236954 | True |
| 500k-community-clustered-balanced-hash | hash | 177.2 | 0.020 | 0.139 | 39.867 | 249.425 | 198635520 | 58242687 | True |
| 500k-community-clustered-balanced-hash-bi | hash_bi | 378.4 | 0.005 | 0.028 | 0.004 | 0.035 | 260825088 | 107386762 | True |
| 500k-community-clustered-balanced-hybrid | hybrid | 501.3 | 0.007 | 0.043 | 0.005 | 0.038 | 191266816 | 48236954 | True |
| 500k-community-clustered-forward-dominant-csr | csr | 357.9 | 0.007 | 0.077 | 7.966 | 35.047 | 186798080 | 28703595 | True |
| 500k-community-clustered-forward-dominant-csr-csc | csr_csc | 493.9 | 0.005 | 0.028 | 0.007 | 0.041 | 194899968 | 48236954 | True |
| 500k-community-clustered-forward-dominant-hash | hash | 231.4 | 0.011 | 0.153 | 53.142 | 210.774 | 218435584 | 58242687 | True |
| 500k-community-clustered-forward-dominant-hash-bi | hash_bi | 391.5 | 0.008 | 0.042 | 0.014 | 0.070 | 279752704 | 107386762 | True |
| 500k-community-clustered-forward-dominant-hybrid | hybrid | 506.2 | 0.009 | 0.052 | 0.013 | 0.065 | 189276160 | 48236954 | True |
| 500k-community-clustered-reverse-heavy-csr | csr | 352.9 | 0.016 | 0.121 | 4.619 | 34.063 | 191438848 | 28703595 | True |
| 500k-community-clustered-reverse-heavy-csr-csc | csr_csc | 505.0 | 0.006 | 0.043 | 0.002 | 0.023 | 192327680 | 48236954 | True |
| 500k-community-clustered-reverse-heavy-hash | hash | 189.2 | 0.041 | 0.249 | 32.773 | 249.064 | 209309696 | 58242687 | True |
| 500k-community-clustered-reverse-heavy-hash-bi | hash_bi | 388.7 | 0.007 | 0.077 | 0.005 | 0.041 | 265900032 | 107386762 | True |
| 500k-community-clustered-reverse-heavy-hybrid | hybrid | 519.5 | 0.010 | 0.082 | 0.005 | 0.045 | 192892928 | 48236954 | True |
| 500k-community-natural-balanced-csr | csr | 426.9 | 0.012 | 0.098 | 4.559 | 34.473 | 165158912 | 28703595 | False |
| 500k-community-natural-balanced-csr-csc | csr_csc | 650.4 | 0.004 | 0.028 | 0.003 | 0.022 | 194392064 | 48236954 | False |
| 500k-community-natural-balanced-hash | hash | 277.4 | 0.005 | 0.011 | 4.386 | 8.481 | 147808256 | 35181776 | True |
| 500k-community-natural-balanced-hash-bi | hash_bi | 328.9 | 0.001 | 0.002 | 0.000 | 0.001 | 168263680 | 53123086 | True |
| 500k-community-natural-balanced-hybrid | hybrid | 590.8 | 0.007 | 0.082 | 0.005 | 0.039 | 193839104 | 48236954 | False |
| 500k-hierarchical-clustered-balanced-csr | csr | 314.4 | 0.006 | 0.273 | 3.567 | 66.241 | 189530112 | 29496580 | True |
| 500k-hierarchical-clustered-balanced-csr-csc | csr_csc | 466.3 | 0.002 | 0.102 | 0.006 | 0.104 | 194781184 | 49996780 | True |
| 500k-hierarchical-clustered-balanced-hash | hash | 178.6 | 0.010 | 0.584 | 21.237 | 1003.473 | 220352512 | 64610988 | True |
| 500k-hierarchical-clustered-balanced-hash-bi | hash_bi | 432.8 | 0.003 | 0.179 | 0.009 | 0.229 | 284712960 | 116810301 | True |
| 500k-hierarchical-clustered-balanced-hybrid | hybrid | 489.8 | 0.003 | 0.205 | 0.011 | 0.229 | 196804608 | 49996780 | True |
| 500k-hierarchical-clustered-forward-dominant-csr | csr | 271.4 | 0.007 | 0.153 | 2.723 | 7.576 | 188964864 | 29496580 | True |
| 500k-hierarchical-clustered-forward-dominant-csr-csc | csr_csc | 432.2 | 0.007 | 0.083 | 0.005 | 0.039 | 193208320 | 49996780 | True |
| 500k-hierarchical-clustered-forward-dominant-hash | hash | 153.4 | 0.009 | 0.333 | 25.084 | 111.698 | 208363520 | 64610988 | True |
| 500k-hierarchical-clustered-forward-dominant-hash-bi | hash_bi | 346.2 | 0.009 | 0.131 | 0.015 | 0.043 | 271564800 | 116810301 | True |
| 500k-hierarchical-clustered-forward-dominant-hybrid | hybrid | 444.1 | 0.012 | 0.165 | 0.007 | 0.036 | 195555328 | 49996780 | True |
| 500k-hierarchical-clustered-reverse-heavy-csr | csr | 296.0 | 0.029 | 0.491 | 5.160 | 59.917 | 196894720 | 29496580 | True |
| 500k-hierarchical-clustered-reverse-heavy-csr-csc | csr_csc | 474.1 | 0.016 | 0.255 | 0.008 | 0.137 | 195526656 | 49996780 | True |
| 500k-hierarchical-clustered-reverse-heavy-hash | hash | 187.6 | 0.061 | 0.921 | 87.281 | 1055.356 | 200556544 | 64610988 | True |
| 500k-hierarchical-clustered-reverse-heavy-hash-bi | hash_bi | 417.7 | 0.019 | 0.547 | 0.013 | 0.287 | 293851136 | 116810301 | True |
| 500k-hierarchical-clustered-reverse-heavy-hybrid | hybrid | 475.5 | 0.023 | 0.471 | 0.014 | 0.229 | 200159232 | 49996780 | True |
| 500k-hierarchical-natural-balanced-csr | csr | 399.3 | 0.008 | 0.312 | 2.791 | 38.350 | 167825408 | 29496580 | True |
| 500k-hierarchical-natural-balanced-csr-csc | csr_csc | 567.1 | 0.002 | 0.121 | 0.002 | 0.063 | 197394432 | 49996780 | True |
| 500k-hierarchical-natural-balanced-hash | hash | 249.6 | 0.005 | 0.011 | 3.861 | 10.926 | 144580608 | 34869902 | True |
| 500k-hierarchical-natural-balanced-hash-bi | hash_bi | 322.7 | 0.000 | 0.002 | 0.000 | 0.000 | 162357248 | 49634177 | True |
| 500k-hierarchical-natural-balanced-hybrid | hybrid | 610.2 | 0.003 | 0.188 | 0.003 | 0.095 | 198606848 | 49996780 | True |
| 500k-hubby-clustered-balanced-csr | csr | 272.0 | 0.005 | 0.028 | 3.978 | 37.490 | 187092992 | 28698760 | True |
| 500k-hubby-clustered-balanced-csr-csc | csr_csc | 449.5 | 0.002 | 0.012 | 0.002 | 0.043 | 191328256 | 48229171 | True |
| 500k-hubby-clustered-balanced-hash | hash | 141.7 | 0.010 | 0.080 | 25.768 | 244.323 | 203669504 | 61610095 | True |
| 500k-hubby-clustered-balanced-hash-bi | hash_bi | 309.3 | 0.002 | 0.012 | 0.002 | 0.038 | 272084992 | 110644876 | True |
| 500k-hubby-clustered-balanced-hybrid | hybrid | 455.5 | 0.002 | 0.014 | 0.003 | 0.051 | 193134592 | 48229171 | True |
| 500k-hubby-clustered-forward-dominant-csr | csr | 289.4 | 0.002 | 0.013 | 6.621 | 38.391 | 190492672 | 28698760 | True |
| 500k-hubby-clustered-forward-dominant-csr-csc | csr_csc | 399.5 | 0.001 | 0.005 | 0.007 | 0.055 | 191852544 | 48229171 | True |
| 500k-hubby-clustered-forward-dominant-hash | hash | 140.5 | 0.003 | 0.027 | 37.888 | 232.956 | 208629760 | 61610095 | True |
| 500k-hubby-clustered-forward-dominant-hash-bi | hash_bi | 296.7 | 0.001 | 0.007 | 0.020 | 0.128 | 280137728 | 110644876 | True |
| 500k-hubby-clustered-forward-dominant-hybrid | hybrid | 405.0 | 0.002 | 0.008 | 0.018 | 0.118 | 194846720 | 48229171 | True |
| 500k-hubby-clustered-reverse-heavy-csr | csr | 304.1 | 0.012 | 1.653 | 5.045 | 29.956 | 189771776 | 28698760 | True |
| 500k-hubby-clustered-reverse-heavy-csr-csc | csr_csc | 448.7 | 0.006 | 0.884 | 0.003 | 0.042 | 193875968 | 48229171 | True |
| 500k-hubby-clustered-reverse-heavy-hash | hash | 143.5 | 0.026 | 3.454 | 30.144 | 176.719 | 205725696 | 61610095 | True |
| 500k-hubby-clustered-reverse-heavy-hash-bi | hash_bi | 358.2 | 0.013 | 1.702 | 0.006 | 0.081 | 274198528 | 110644876 | True |
| 500k-hubby-clustered-reverse-heavy-hybrid | hybrid | 403.9 | 0.010 | 1.610 | 0.006 | 0.083 | 189509632 | 48229171 | True |
| 500k-hubby-natural-balanced-csr | csr | 381.8 | 0.004 | 0.029 | 2.302 | 76.227 | 166477824 | 28698760 | False |
| 500k-hubby-natural-balanced-csr-csc | csr_csc | 585.4 | 0.001 | 0.008 | 0.003 | 0.051 | 193839104 | 48229171 | False |
| 500k-hubby-natural-balanced-hash | hash | 195.1 | 0.003 | 0.008 | 2.631 | 24.403 | 157855744 | 33100931 | True |
| 500k-hubby-natural-balanced-hash-bi | hash_bi | 288.4 | 0.000 | 0.001 | 0.001 | 0.003 | 161431552 | 46943152 | True |
| 500k-hubby-natural-balanced-hybrid | hybrid | 508.7 | 0.002 | 0.011 | 0.006 | 0.103 | 197754880 | 48229171 | False |
| 500k-layered-clustered-balanced-csr | csr | 323.3 | 0.011 | 0.062 | 1.194 | 10.997 | 170172416 | 27312547 | True |
| 500k-layered-clustered-balanced-csr-csc | csr_csc | 437.8 | 0.002 | 0.018 | 0.000 | 0.003 | 185389056 | 45789010 | True |
| 500k-layered-clustered-balanced-hash | hash | 143.2 | 0.021 | 0.126 | 7.807 | 70.188 | 190197760 | 53862929 | True |
| 500k-layered-clustered-balanced-hash-bi | hash_bi | 330.4 | 0.003 | 0.033 | 0.001 | 0.006 | 256651264 | 101999682 | True |
| 500k-layered-clustered-balanced-hybrid | hybrid | 450.6 | 0.004 | 0.034 | 0.001 | 0.006 | 185753600 | 45789010 | True |
| 500k-layered-clustered-forward-dominant-csr | csr | 290.4 | 0.005 | 0.030 | 6.325 | 22.042 | 170344448 | 27312547 | True |
| 500k-layered-clustered-forward-dominant-csr-csc | csr_csc | 450.8 | 0.004 | 0.013 | 0.005 | 0.027 | 182206464 | 45789010 | True |
| 500k-layered-clustered-forward-dominant-hash | hash | 142.2 | 0.008 | 0.056 | 44.624 | 149.789 | 190984192 | 53862929 | True |
| 500k-layered-clustered-forward-dominant-hash-bi | hash_bi | 439.6 | 0.006 | 0.019 | 0.007 | 0.048 | 267317248 | 101999682 | True |
| 500k-layered-clustered-forward-dominant-hybrid | hybrid | 436.7 | 0.008 | 0.026 | 0.006 | 0.064 | 186040320 | 45789010 | True |
| 500k-layered-clustered-reverse-heavy-csr | csr | 313.0 | 0.014 | 0.113 | 2.243 | 61.749 | 167714816 | 27312547 | True |
| 500k-layered-clustered-reverse-heavy-csr-csc | csr_csc | 442.8 | 0.006 | 0.033 | 0.001 | 0.027 | 181936128 | 45789010 | True |
| 500k-layered-clustered-reverse-heavy-hash | hash | 156.0 | 0.031 | 0.197 | 14.389 | 409.790 | 182681600 | 53862929 | True |
| 500k-layered-clustered-reverse-heavy-hash-bi | hash_bi | 361.2 | 0.009 | 0.058 | 0.002 | 0.045 | 255156224 | 101999682 | True |
| 500k-layered-clustered-reverse-heavy-hybrid | hybrid | 426.0 | 0.011 | 0.064 | 0.003 | 0.041 | 188145664 | 45789010 | True |
| 500k-layered-natural-balanced-csr | csr | 429.3 | 0.011 | 0.041 | 2.396 | 23.485 | 159518720 | 27312547 | True |
| 500k-layered-natural-balanced-csr-csc | csr_csc | 689.2 | 0.004 | 0.013 | 0.001 | 0.009 | 187748352 | 45789010 | True |
| 500k-layered-natural-balanced-hash | hash | 211.1 | 0.003 | 0.009 | 1.703 | 4.257 | 109797376 | 22470424 | True |
| 500k-layered-natural-balanced-hash-bi | hash_bi | 256.5 | 0.000 | 0.001 | 0.000 | 0.000 | 125947904 | 33018420 | True |
| 500k-layered-natural-balanced-hybrid | hybrid | 617.6 | 0.007 | 0.028 | 0.001 | 0.014 | 189878272 | 45789010 | True |
| 500k-power-law-clustered-balanced-csr | csr | 306.7 | 0.012 | 1.714 | 1.321 | 14.360 | 168210432 | 28667434 | True |
| 500k-power-law-clustered-balanced-csr-csc | csr_csc | 437.0 | 0.016 | 1.127 | 0.005 | 0.061 | 188932096 | 48194091 | True |
| 500k-power-law-clustered-balanced-hash | hash | 92.7 | 0.031 | 3.410 | 10.931 | 123.066 | 189571072 | 55473766 | True |
| 500k-power-law-clustered-balanced-hash-bi | hash_bi | 327.0 | 0.025 | 2.639 | 0.009 | 0.115 | 253145088 | 104511823 | True |
| 500k-power-law-clustered-balanced-hybrid | hybrid | 412.0 | 0.028 | 2.514 | 0.010 | 0.111 | 192253952 | 48194091 | True |
| 500k-power-law-clustered-forward-dominant-csr | csr | 282.0 | 0.014 | 2.345 | 2.090 | 9.684 | 166227968 | 28667434 | True |
| 500k-power-law-clustered-forward-dominant-csr-csc | csr_csc | 496.2 | 0.006 | 2.118 | 0.008 | 0.034 | 188977152 | 48194091 | True |
| 500k-power-law-clustered-forward-dominant-hash | hash | 96.0 | 0.017 | 4.357 | 16.304 | 59.024 | 184520704 | 55473766 | True |
| 500k-power-law-clustered-forward-dominant-hash-bi | hash_bi | 237.8 | 0.014 | 3.398 | 0.014 | 0.055 | 259776512 | 104511823 | True |
| 500k-power-law-clustered-forward-dominant-hybrid | hybrid | 443.4 | 0.019 | 4.182 | 0.013 | 0.060 | 193716224 | 48194091 | True |
| 500k-power-law-clustered-reverse-heavy-csr | csr | 267.2 | 0.290 | 13.447 | 2.218 | 11.584 | 166981632 | 28667434 | True |
| 500k-power-law-clustered-reverse-heavy-csr-csc | csr_csc | 395.0 | 0.296 | 13.681 | 0.006 | 0.055 | 190545920 | 48194091 | True |
| 500k-power-law-clustered-reverse-heavy-hash | hash | 91.8 | 0.769 | 25.823 | 18.283 | 88.046 | 193585152 | 55473766 | True |
| 500k-power-law-clustered-reverse-heavy-hash-bi | hash_bi | 240.6 | 0.439 | 23.409 | 0.009 | 0.098 | 257708032 | 104511823 | True |
| 500k-power-law-clustered-reverse-heavy-hybrid | hybrid | 446.3 | 0.525 | 27.307 | 0.011 | 0.096 | 195026944 | 48194091 | True |
| 500k-power-law-natural-balanced-csr | csr | 354.5 | 0.013 | 3.391 | 1.698 | 11.189 | 158445568 | 28667434 | False |
| 500k-power-law-natural-balanced-csr-csc | csr_csc | 473.0 | 0.006 | 2.601 | 0.004 | 0.034 | 191041536 | 48194091 | False |
| 500k-power-law-natural-balanced-hash | hash | 83.5 | 0.000 | 0.000 | 0.010 | 0.014 | 92098560 | 1328973 | True |
| 500k-power-law-natural-balanced-hash-bi | hash_bi | 79.0 | 0.000 | 0.000 | 0.000 | 0.000 | 90808320 | 2094422 | True |
| 500k-power-law-natural-balanced-hybrid | hybrid | 456.3 | 0.013 | 4.055 | 0.007 | 0.062 | 189210624 | 48194091 | False |
| 500k-uniform-clustered-balanced-csr | csr | 319.8 | 0.011 | 0.113 | 4.467 | 44.375 | 189980672 | 28700912 | True |
| 500k-uniform-clustered-balanced-csr-csc | csr_csc | 383.2 | 0.005 | 0.048 | 0.003 | 0.052 | 189878272 | 48231500 | True |
| 500k-uniform-clustered-balanced-hash | hash | 197.6 | 0.025 | 0.290 | 42.666 | 425.795 | 204992512 | 58184284 | True |
| 500k-uniform-clustered-balanced-hash-bi | hash_bi | 368.2 | 0.006 | 0.091 | 0.004 | 0.066 | 288456704 | 107231142 | True |
| 500k-uniform-clustered-balanced-hybrid | hybrid | 385.3 | 0.008 | 0.061 | 0.006 | 0.063 | 193142784 | 48231500 | True |
| 500k-uniform-clustered-forward-dominant-csr | csr | 359.5 | 0.007 | 0.081 | 4.669 | 30.786 | 185929728 | 28700912 | True |
| 500k-uniform-clustered-forward-dominant-csr-csc | csr_csc | 462.9 | 0.010 | 0.079 | 0.015 | 0.083 | 195006464 | 48231500 | True |
| 500k-uniform-clustered-forward-dominant-hash | hash | 198.3 | 0.009 | 0.162 | 35.716 | 230.551 | 199868416 | 58184284 | True |
| 500k-uniform-clustered-forward-dominant-hash-bi | hash_bi | 458.2 | 0.009 | 0.055 | 0.017 | 0.110 | 256724992 | 107231142 | True |
| 500k-uniform-clustered-forward-dominant-hybrid | hybrid | 483.3 | 0.008 | 0.060 | 0.011 | 0.103 | 194347008 | 48231500 | True |
| 500k-uniform-clustered-reverse-heavy-csr | csr | 269.1 | 0.024 | 0.240 | 5.430 | 43.277 | 189120512 | 28700912 | True |
| 500k-uniform-clustered-reverse-heavy-csr-csc | csr_csc | 415.6 | 0.006 | 0.081 | 0.004 | 0.035 | 193077248 | 48231500 | True |
| 500k-uniform-clustered-reverse-heavy-hash | hash | 167.9 | 0.045 | 0.496 | 37.449 | 308.694 | 219246592 | 58184284 | True |
| 500k-uniform-clustered-reverse-heavy-hash-bi | hash_bi | 345.9 | 0.010 | 0.142 | 0.005 | 0.053 | 279937024 | 107231142 | True |
| 500k-uniform-clustered-reverse-heavy-hybrid | hybrid | 378.9 | 0.015 | 0.179 | 0.007 | 0.060 | 194691072 | 48231500 | True |
| 500k-uniform-natural-balanced-csr | csr | 376.8 | 0.010 | 0.143 | 7.950 | 45.576 | 168878080 | 28700912 | False |
| 500k-uniform-natural-balanced-csr-csc | csr_csc | 605.0 | 0.003 | 0.044 | 0.005 | 0.053 | 199061504 | 48231500 | False |
| 500k-uniform-natural-balanced-hash | hash | 230.5 | 0.004 | 0.009 | 3.859 | 13.409 | 149147648 | 35180022 | True |
| 500k-uniform-natural-balanced-hash-bi | hash_bi | 284.0 | 0.001 | 0.004 | 0.000 | 0.003 | 173895680 | 52613087 | True |
| 500k-uniform-natural-balanced-hybrid | hybrid | 606.6 | 0.007 | 0.078 | 0.010 | 0.059 | 197607424 | 48231500 | False |
| 5M-hubby-clustered-balanced-csr | csr | 7205.0 | 0.008 | 0.049 | 73.168 | 490.832 | 1529589760 | 314534490 | True |
| 5M-hubby-clustered-balanced-csr-csc | csr_csc | 10577.8 | 0.001 | 0.008 | 0.004 | 0.030 | 1763897344 | 509861254 | True |
| 5M-hubby-clustered-balanced-hash | hash | 2909.3 | 0.012 | 0.105 | 530.702 | 3960.593 | 1662545920 | 636216421 | True |
| 5M-hubby-clustered-balanced-hash-bi | hash_bi | 6876.4 | 0.002 | 0.015 | 0.006 | 0.051 | 2422919168 | 1126642782 | True |
| 5M-hubby-clustered-balanced-hybrid | hybrid | 10059.2 | 0.002 | 0.012 | 0.006 | 0.046 | 1764872192 | 509861254 | True |
| 5M-uniform-clustered-balanced-csr | csr | 5923.4 | 0.011 | 0.152 | 50.527 | 288.514 | 1651212288 | 314560571 | True |
| 5M-uniform-clustered-balanced-csr-csc | csr_csc | 7854.4 | 0.003 | 0.048 | 0.003 | 0.032 | 1741258752 | 509889449 | True |
| 5M-uniform-clustered-balanced-hash | hash | 3060.4 | 0.021 | 0.401 | 490.870 | 2746.935 | 1701679104 | 609608408 | True |
| 5M-uniform-clustered-balanced-hash-bi | hash_bi | 6728.5 | 0.006 | 0.086 | 0.005 | 0.056 | 2442719232 | 1099989643 | True |
| 5M-uniform-clustered-balanced-hybrid | hybrid | 8626.1 | 0.005 | 0.079 | 0.004 | 0.053 | 1755176960 | 509889449 | True |
| 5M-uniform-clustered-forward-dominant-csr | csr | 5828.6 | 0.008 | 0.141 | 76.922 | 483.516 | 1670053888 | 314560571 | True |
| 5M-uniform-clustered-forward-dominant-csr-csc | csr_csc | 7718.0 | 0.004 | 0.040 | 0.015 | 0.093 | 1741037568 | 509889449 | True |
| 5M-uniform-clustered-forward-dominant-hash | hash | 2618.4 | 0.012 | 0.277 | 678.587 | 4916.367 | 1702305792 | 609608408 | True |
| 5M-uniform-clustered-forward-dominant-hash-bi | hash_bi | 6808.3 | 0.009 | 0.096 | 0.043 | 0.142 | 2429091840 | 1099989643 | True |
| 5M-uniform-clustered-forward-dominant-hybrid | hybrid | 7773.9 | 0.009 | 0.071 | 0.026 | 0.144 | 1753149440 | 509889449 | True |

## Rankings by regime (lowest reverse p95, then build)

### balanced × community × 1M

1. `csr_csc` — rev_p95=0.027 fwd_p95=0.036 build=1310.392 rss=365367296 idx=96476528
2. `hybrid` — rev_p95=0.029 fwd_p95=0.041 build=1232.021 rss=367034368 idx=96476528
3. `hash_bi` — rev_p95=0.036 fwd_p95=0.051 build=845.806 rss=492388352 idx=216290352
4. `csr` — rev_p95=50.064 fwd_p95=0.100 build=835.795 rss=364265472 idx=57408185
5. `hash` — rev_p95=372.563 fwd_p95=0.145 build=379.193 rss=367857664 idx=116397047

### balanced × community × 500k

1. `hash_bi` — rev_p95=0.001 fwd_p95=0.002 build=328.931 rss=168263680 idx=53123086
2. `csr_csc` — rev_p95=0.022 fwd_p95=0.020 build=515.248 rss=192548864 idx=48236954
3. `csr_csc` — rev_p95=0.022 fwd_p95=0.028 build=650.411 rss=194392064 idx=48236954
4. `hash_bi` — rev_p95=0.035 fwd_p95=0.028 build=378.391 rss=260825088 idx=107386762
5. `hybrid` — rev_p95=0.038 fwd_p95=0.043 build=501.269 rss=191266816 idx=48236954
6. `hybrid` — rev_p95=0.039 fwd_p95=0.082 build=590.780 rss=193839104 idx=48236954
7. `hash` — rev_p95=8.481 fwd_p95=0.011 build=277.444 rss=147808256 idx=35181776
8. `csr` — rev_p95=34.473 fwd_p95=0.098 build=426.914 rss=165158912 idx=28703595
9. `csr` — rev_p95=34.670 fwd_p95=0.073 build=345.280 rss=187736064 idx=28703595
10. `hash` — rev_p95=249.425 fwd_p95=0.139 build=177.172 rss=198635520 idx=58242687

### balanced × hierarchical × 1M

1. `csr_csc` — rev_p95=0.094 fwd_p95=0.092 build=1094.818 rss=372760576 idx=99998385
2. `hash_bi` — rev_p95=0.159 fwd_p95=0.137 build=755.231 rss=516235264 idx=233679413
3. `hybrid` — rev_p95=0.190 fwd_p95=0.183 build=937.717 rss=368361472 idx=99998385
4. `csr` — rev_p95=136.454 fwd_p95=0.247 build=552.979 rss=369090560 idx=58995510
5. `hash` — rev_p95=2465.734 fwd_p95=0.510 build=358.479 rss=376864768 idx=129290117

### balanced × hierarchical × 500k

1. `hash_bi` — rev_p95=0.000 fwd_p95=0.002 build=322.656 rss=162357248 idx=49634177
2. `csr_csc` — rev_p95=0.063 fwd_p95=0.121 build=567.143 rss=197394432 idx=49996780
3. `hybrid` — rev_p95=0.095 fwd_p95=0.188 build=610.192 rss=198606848 idx=49996780
4. `csr_csc` — rev_p95=0.104 fwd_p95=0.102 build=466.336 rss=194781184 idx=49996780
5. `hybrid` — rev_p95=0.229 fwd_p95=0.205 build=489.819 rss=196804608 idx=49996780
6. `hash_bi` — rev_p95=0.229 fwd_p95=0.179 build=432.755 rss=284712960 idx=116810301
7. `hash` — rev_p95=10.926 fwd_p95=0.011 build=249.650 rss=144580608 idx=34869902
8. `csr` — rev_p95=38.350 fwd_p95=0.312 build=399.283 rss=167825408 idx=29496580
9. `csr` — rev_p95=66.241 fwd_p95=0.273 build=314.437 rss=189530112 idx=29496580
10. `hash` — rev_p95=1003.473 fwd_p95=0.584 build=178.633 rss=220352512 idx=64610988

### balanced × hubby × 1M

1. `hash_bi` — rev_p95=0.057 fwd_p95=0.020 build=923.930 rss=500908032 idx=225076756
2. `csr_csc` — rev_p95=0.063 fwd_p95=0.012 build=1357.342 rss=371269632 idx=96455904
3. `hybrid` — rev_p95=0.119 fwd_p95=0.025 build=1217.053 rss=362274816 idx=96455904
4. `csr` — rev_p95=123.957 fwd_p95=0.040 build=852.336 rss=339943424 idx=57395901
5. `hash` — rev_p95=705.532 fwd_p95=0.055 build=407.166 rss=372965376 idx=127042437

### balanced × hubby × 500k

1. `hash_bi` — rev_p95=0.003 fwd_p95=0.001 build=288.393 rss=161431552 idx=46943152
2. `hash_bi` — rev_p95=0.038 fwd_p95=0.012 build=309.345 rss=272084992 idx=110644876
3. `csr_csc` — rev_p95=0.043 fwd_p95=0.012 build=449.510 rss=191328256 idx=48229171
4. `csr_csc` — rev_p95=0.051 fwd_p95=0.008 build=585.408 rss=193839104 idx=48229171
5. `hybrid` — rev_p95=0.051 fwd_p95=0.014 build=455.460 rss=193134592 idx=48229171
6. `hybrid` — rev_p95=0.103 fwd_p95=0.011 build=508.658 rss=197754880 idx=48229171
7. `hash` — rev_p95=24.403 fwd_p95=0.008 build=195.079 rss=157855744 idx=33100931
8. `csr` — rev_p95=37.490 fwd_p95=0.028 build=271.985 rss=187092992 idx=28698760
9. `csr` — rev_p95=76.227 fwd_p95=0.029 build=381.798 rss=166477824 idx=28698760
10. `hash` — rev_p95=244.323 fwd_p95=0.080 build=141.698 rss=203669504 idx=61610095

### balanced × hubby × 5M

1. `csr_csc` — rev_p95=0.030 fwd_p95=0.008 build=10577.839 rss=1763897344 idx=509861254
2. `hybrid` — rev_p95=0.046 fwd_p95=0.012 build=10059.200 rss=1764872192 idx=509861254
3. `hash_bi` — rev_p95=0.051 fwd_p95=0.015 build=6876.416 rss=2422919168 idx=1126642782
4. `csr` — rev_p95=490.832 fwd_p95=0.049 build=7205.008 rss=1529589760 idx=314534490
5. `hash` — rev_p95=3960.593 fwd_p95=0.105 build=2909.328 rss=1662545920 idx=636216421

### balanced × layered × 1M

1. `csr_csc` — rev_p95=0.041 fwd_p95=0.040 build=1079.341 rss=343523328 idx=91576746
2. `hash_bi` — rev_p95=0.052 fwd_p95=0.043 build=787.238 rss=464728064 idx=203935314
3. `hybrid` — rev_p95=0.068 fwd_p95=0.036 build=1087.988 rss=352907264 idx=91576746
4. `csr` — rev_p95=172.256 fwd_p95=0.057 build=661.469 rss=321253376 idx=54624010
5. `hash` — rev_p95=1294.827 fwd_p95=0.123 build=333.122 rss=330399744 idx=107613450

### balanced × layered × 500k

1. `hash_bi` — rev_p95=0.000 fwd_p95=0.001 build=256.546 rss=125947904 idx=33018420
2. `csr_csc` — rev_p95=0.003 fwd_p95=0.018 build=437.803 rss=185389056 idx=45789010
3. `hash_bi` — rev_p95=0.006 fwd_p95=0.033 build=330.444 rss=256651264 idx=101999682
4. `hybrid` — rev_p95=0.006 fwd_p95=0.034 build=450.584 rss=185753600 idx=45789010
5. `csr_csc` — rev_p95=0.009 fwd_p95=0.013 build=689.207 rss=187748352 idx=45789010
6. `hybrid` — rev_p95=0.014 fwd_p95=0.028 build=617.640 rss=189878272 idx=45789010
7. `hash` — rev_p95=4.257 fwd_p95=0.009 build=211.063 rss=109797376 idx=22470424
8. `csr` — rev_p95=10.997 fwd_p95=0.062 build=323.325 rss=170172416 idx=27312547
9. `csr` — rev_p95=23.485 fwd_p95=0.041 build=429.255 rss=159518720 idx=27312547
10. `hash` — rev_p95=70.188 fwd_p95=0.126 build=143.220 rss=190197760 idx=53862929

### balanced × power_law × 1M

1. `csr_csc` — rev_p95=0.092 fwd_p95=6.511 build=984.846 rss=362541056 idx=96389465
2. `hybrid` — rev_p95=0.150 fwd_p95=10.581 build=961.170 rss=365785088 idx=96389465
3. `hash_bi` — rev_p95=0.170 fwd_p95=12.012 build=533.535 rss=480600064 idx=209383453
4. `csr` — rev_p95=36.388 fwd_p95=6.643 build=612.050 rss=309379072 idx=57335521
5. `hash` — rev_p95=325.178 fwd_p95=15.473 build=192.315 rss=352403456 idx=111398231

### balanced × power_law × 500k

1. `hash_bi` — rev_p95=0.000 fwd_p95=0.000 build=78.990 rss=90808320 idx=2094422
2. `hash` — rev_p95=0.014 fwd_p95=0.000 build=83.533 rss=92098560 idx=1328973
3. `csr_csc` — rev_p95=0.034 fwd_p95=2.601 build=472.951 rss=191041536 idx=48194091
4. `csr_csc` — rev_p95=0.061 fwd_p95=1.127 build=436.959 rss=188932096 idx=48194091
5. `hybrid` — rev_p95=0.062 fwd_p95=4.055 build=456.288 rss=189210624 idx=48194091
6. `hybrid` — rev_p95=0.111 fwd_p95=2.514 build=411.964 rss=192253952 idx=48194091
7. `hash_bi` — rev_p95=0.115 fwd_p95=2.639 build=327.022 rss=253145088 idx=104511823
8. `csr` — rev_p95=11.189 fwd_p95=3.391 build=354.541 rss=158445568 idx=28667434
9. `csr` — rev_p95=14.360 fwd_p95=1.714 build=306.686 rss=168210432 idx=28667434
10. `hash` — rev_p95=123.066 fwd_p95=3.410 build=92.728 rss=189571072 idx=55473766

### balanced × uniform × 1M

1. `csr_csc` — rev_p95=0.035 fwd_p95=0.038 build=1097.342 rss=362467328 idx=96461388
2. `hybrid` — rev_p95=0.091 fwd_p95=0.084 build=1102.733 rss=370515968 idx=96461388
3. `hash_bi` — rev_p95=0.107 fwd_p95=0.112 build=945.114 rss=502800384 idx=214426970
4. `csr` — rev_p95=100.217 fwd_p95=0.137 build=780.263 rss=359194624 idx=57400989
5. `hash` — rev_p95=749.785 fwd_p95=0.264 build=462.469 rss=371855360 idx=116379550

### balanced × uniform × 500k

1. `hash_bi` — rev_p95=0.003 fwd_p95=0.004 build=283.990 rss=173895680 idx=52613087
2. `csr_csc` — rev_p95=0.052 fwd_p95=0.048 build=383.155 rss=189878272 idx=48231500
3. `csr_csc` — rev_p95=0.053 fwd_p95=0.044 build=604.982 rss=199061504 idx=48231500
4. `hybrid` — rev_p95=0.059 fwd_p95=0.078 build=606.577 rss=197607424 idx=48231500
5. `hybrid` — rev_p95=0.063 fwd_p95=0.061 build=385.257 rss=193142784 idx=48231500
6. `hash_bi` — rev_p95=0.066 fwd_p95=0.091 build=368.225 rss=288456704 idx=107231142
7. `hash` — rev_p95=13.409 fwd_p95=0.009 build=230.546 rss=149147648 idx=35180022
8. `csr` — rev_p95=44.375 fwd_p95=0.113 build=319.797 rss=189980672 idx=28700912
9. `csr` — rev_p95=45.576 fwd_p95=0.143 build=376.831 rss=168878080 idx=28700912
10. `hash` — rev_p95=425.795 fwd_p95=0.290 build=197.592 rss=204992512 idx=58184284

### balanced × uniform × 5M

1. `csr_csc` — rev_p95=0.032 fwd_p95=0.048 build=7854.364 rss=1741258752 idx=509889449
2. `hybrid` — rev_p95=0.053 fwd_p95=0.079 build=8626.053 rss=1755176960 idx=509889449
3. `hash_bi` — rev_p95=0.056 fwd_p95=0.086 build=6728.486 rss=2442719232 idx=1099989643
4. `csr` — rev_p95=288.514 fwd_p95=0.152 build=5923.358 rss=1651212288 idx=314560571
5. `hash` — rev_p95=2746.935 fwd_p95=0.401 build=3060.385 rss=1701679104 idx=609608408

### forward_dominant × community × 1M

1. `csr_csc` — rev_p95=0.027 fwd_p95=0.014 build=1164.795 rss=369987584 idx=96476528
2. `hybrid` — rev_p95=0.042 fwd_p95=0.027 build=1159.313 rss=367038464 idx=96476528
3. `hash_bi` — rev_p95=0.045 fwd_p95=0.019 build=862.004 rss=488185856 idx=216290352
4. `csr` — rev_p95=42.792 fwd_p95=0.050 build=817.732 rss=364048384 idx=57408185
5. `hash` — rev_p95=275.812 fwd_p95=0.088 build=442.846 rss=366317568 idx=116397047

### forward_dominant × community × 500k

1. `csr_csc` — rev_p95=0.041 fwd_p95=0.028 build=493.933 rss=194899968 idx=48236954
2. `hybrid` — rev_p95=0.065 fwd_p95=0.052 build=506.206 rss=189276160 idx=48236954
3. `hash_bi` — rev_p95=0.070 fwd_p95=0.042 build=391.463 rss=279752704 idx=107386762
4. `csr` — rev_p95=35.047 fwd_p95=0.077 build=357.913 rss=186798080 idx=28703595
5. `hash` — rev_p95=210.774 fwd_p95=0.153 build=231.441 rss=218435584 idx=58242687

### forward_dominant × hierarchical × 1M

1. `hybrid` — rev_p95=0.187 fwd_p95=0.156 build=963.038 rss=373145600 idx=99998385
2. `csr_csc` — rev_p95=0.197 fwd_p95=0.133 build=1004.695 rss=371318784 idx=99998385
3. `hash_bi` — rev_p95=0.245 fwd_p95=0.137 build=701.404 rss=499081216 idx=233679413
4. `csr` — rev_p95=90.800 fwd_p95=0.240 build=601.122 rss=373694464 idx=58995510
5. `hash` — rev_p95=1386.835 fwd_p95=0.380 build=322.557 rss=385683456 idx=129290117

### forward_dominant × hierarchical × 500k

1. `hybrid` — rev_p95=0.036 fwd_p95=0.165 build=444.065 rss=195555328 idx=49996780
2. `csr_csc` — rev_p95=0.039 fwd_p95=0.083 build=432.205 rss=193208320 idx=49996780
3. `hash_bi` — rev_p95=0.043 fwd_p95=0.131 build=346.182 rss=271564800 idx=116810301
4. `csr` — rev_p95=7.576 fwd_p95=0.153 build=271.358 rss=188964864 idx=29496580
5. `hash` — rev_p95=111.698 fwd_p95=0.333 build=153.424 rss=208363520 idx=64610988

### forward_dominant × hubby × 1M

1. `csr_csc` — rev_p95=0.087 fwd_p95=0.010 build=1271.129 rss=361500672 idx=96455904
2. `hybrid` — rev_p95=0.128 fwd_p95=0.014 build=1262.324 rss=361840640 idx=96455904
3. `hash_bi` — rev_p95=0.145 fwd_p95=0.016 build=1012.708 rss=497528832 idx=225076756
4. `csr` — rev_p95=114.035 fwd_p95=0.034 build=893.444 rss=371134464 idx=57395901
5. `hash` — rev_p95=584.785 fwd_p95=0.056 build=405.248 rss=383823872 idx=127042437

### forward_dominant × hubby × 500k

1. `csr_csc` — rev_p95=0.055 fwd_p95=0.005 build=399.459 rss=191852544 idx=48229171
2. `hybrid` — rev_p95=0.118 fwd_p95=0.008 build=405.010 rss=194846720 idx=48229171
3. `hash_bi` — rev_p95=0.128 fwd_p95=0.007 build=296.660 rss=280137728 idx=110644876
4. `csr` — rev_p95=38.391 fwd_p95=0.013 build=289.390 rss=190492672 idx=28698760
5. `hash` — rev_p95=232.956 fwd_p95=0.027 build=140.513 rss=208629760 idx=61610095

### forward_dominant × layered × 1M

1. `csr_csc` — rev_p95=0.016 fwd_p95=0.021 build=1006.554 rss=347987968 idx=91576746
2. `hash_bi` — rev_p95=0.017 fwd_p95=0.022 build=797.517 rss=475316224 idx=203935314
3. `hybrid` — rev_p95=0.018 fwd_p95=0.033 build=1033.032 rss=343232512 idx=91576746
4. `csr` — rev_p95=30.697 fwd_p95=0.041 build=706.793 rss=326901760 idx=54624010
5. `hash` — rev_p95=179.119 fwd_p95=0.076 build=326.918 rss=320303104 idx=107613450

### forward_dominant × layered × 500k

1. `csr_csc` — rev_p95=0.027 fwd_p95=0.013 build=450.819 rss=182206464 idx=45789010
2. `hash_bi` — rev_p95=0.048 fwd_p95=0.019 build=439.598 rss=267317248 idx=101999682
3. `hybrid` — rev_p95=0.064 fwd_p95=0.026 build=436.679 rss=186040320 idx=45789010
4. `csr` — rev_p95=22.042 fwd_p95=0.030 build=290.383 rss=170344448 idx=27312547
5. `hash` — rev_p95=149.789 fwd_p95=0.056 build=142.179 rss=190984192 idx=53862929

### forward_dominant × power_law × 1M

1. `csr_csc` — rev_p95=0.059 fwd_p95=2.419 build=1050.927 rss=360476672 idx=96389465
2. `hybrid` — rev_p95=0.101 fwd_p95=4.605 build=1038.059 rss=365694976 idx=96389465
3. `hash_bi` — rev_p95=0.111 fwd_p95=7.078 build=543.518 rss=522100736 idx=209383453
4. `csr` — rev_p95=22.822 fwd_p95=3.093 build=734.306 rss=310210560 idx=57335521
5. `hash` — rev_p95=161.686 fwd_p95=6.271 build=194.331 rss=360734720 idx=111398231

### forward_dominant × power_law × 500k

1. `csr_csc` — rev_p95=0.034 fwd_p95=2.118 build=496.156 rss=188977152 idx=48194091
2. `hash_bi` — rev_p95=0.055 fwd_p95=3.398 build=237.808 rss=259776512 idx=104511823
3. `hybrid` — rev_p95=0.060 fwd_p95=4.182 build=443.431 rss=193716224 idx=48194091
4. `csr` — rev_p95=9.684 fwd_p95=2.345 build=282.044 rss=166227968 idx=28667434
5. `hash` — rev_p95=59.024 fwd_p95=4.357 build=95.997 rss=184520704 idx=55473766

### forward_dominant × uniform × 1M

1. `csr_csc` — rev_p95=0.106 fwd_p95=0.035 build=1242.505 rss=365678592 idx=96461388
2. `hash_bi` — rev_p95=0.162 fwd_p95=0.044 build=964.809 rss=490176512 idx=214426970
3. `hybrid` — rev_p95=0.164 fwd_p95=0.062 build=1120.410 rss=355901440 idx=96461388
4. `csr` — rev_p95=91.994 fwd_p95=0.088 build=742.801 rss=357859328 idx=57400989
5. `hash` — rev_p95=734.046 fwd_p95=0.192 build=433.841 rss=345526272 idx=116379550

### forward_dominant × uniform × 500k

1. `csr_csc` — rev_p95=0.083 fwd_p95=0.079 build=462.913 rss=195006464 idx=48231500
2. `hybrid` — rev_p95=0.103 fwd_p95=0.060 build=483.333 rss=194347008 idx=48231500
3. `hash_bi` — rev_p95=0.110 fwd_p95=0.055 build=458.153 rss=256724992 idx=107231142
4. `csr` — rev_p95=30.786 fwd_p95=0.081 build=359.453 rss=185929728 idx=28700912
5. `hash` — rev_p95=230.551 fwd_p95=0.162 build=198.333 rss=199868416 idx=58184284

### forward_dominant × uniform × 5M

1. `csr_csc` — rev_p95=0.093 fwd_p95=0.040 build=7718.019 rss=1741037568 idx=509889449
2. `hash_bi` — rev_p95=0.142 fwd_p95=0.096 build=6808.294 rss=2429091840 idx=1099989643
3. `hybrid` — rev_p95=0.144 fwd_p95=0.071 build=7773.860 rss=1753149440 idx=509889449
4. `csr` — rev_p95=483.516 fwd_p95=0.141 build=5828.611 rss=1670053888 idx=314560571
5. `hash` — rev_p95=4916.367 fwd_p95=0.277 build=2618.352 rss=1702305792 idx=609608408

### reverse_heavy × community × 1M

1. `csr_csc` — rev_p95=0.040 fwd_p95=0.079 build=1260.531 rss=367489024 idx=96476528
2. `hybrid` — rev_p95=0.056 fwd_p95=0.103 build=1227.607 rss=375382016 idx=96476528
3. `hash_bi` — rev_p95=0.071 fwd_p95=0.135 build=937.830 rss=500572160 idx=216290352
4. `csr` — rev_p95=111.396 fwd_p95=0.164 build=900.789 rss=355012608 idx=57408185
5. `hash` — rev_p95=855.391 fwd_p95=0.320 build=407.474 rss=362770432 idx=116397047

### reverse_heavy × community × 500k

1. `csr_csc` — rev_p95=0.023 fwd_p95=0.043 build=504.975 rss=192327680 idx=48236954
2. `hash_bi` — rev_p95=0.041 fwd_p95=0.077 build=388.668 rss=265900032 idx=107386762
3. `hybrid` — rev_p95=0.045 fwd_p95=0.082 build=519.503 rss=192892928 idx=48236954
4. `csr` — rev_p95=34.063 fwd_p95=0.121 build=352.862 rss=191438848 idx=28703595
5. `hash` — rev_p95=249.064 fwd_p95=0.249 build=189.207 rss=209309696 idx=58242687

### reverse_heavy × hierarchical × 1M

1. `csr_csc` — rev_p95=0.083 fwd_p95=0.348 build=1020.289 rss=361705472 idx=99998385
2. `hash_bi` — rev_p95=0.169 fwd_p95=0.643 build=894.580 rss=503816192 idx=233679413
3. `hybrid` — rev_p95=0.178 fwd_p95=0.751 build=1022.307 rss=376549376 idx=99998385
4. `csr` — rev_p95=101.645 fwd_p95=0.651 build=681.544 rss=368349184 idx=58995510
5. `hash` — rev_p95=1753.060 fwd_p95=1.481 build=343.396 rss=381648896 idx=129290117

### reverse_heavy × hierarchical × 500k

1. `csr_csc` — rev_p95=0.137 fwd_p95=0.255 build=474.055 rss=195526656 idx=49996780
2. `hybrid` — rev_p95=0.229 fwd_p95=0.471 build=475.508 rss=200159232 idx=49996780
3. `hash_bi` — rev_p95=0.287 fwd_p95=0.547 build=417.750 rss=293851136 idx=116810301
4. `csr` — rev_p95=59.917 fwd_p95=0.491 build=296.048 rss=196894720 idx=29496580
5. `hash` — rev_p95=1055.356 fwd_p95=0.921 build=187.583 rss=200556544 idx=64610988

### reverse_heavy × hubby × 1M

1. `csr_csc` — rev_p95=0.052 fwd_p95=1.608 build=1025.838 rss=359399424 idx=96455904
2. `hybrid` — rev_p95=0.087 fwd_p95=2.339 build=973.575 rss=366178304 idx=96455904
3. `hash_bi` — rev_p95=0.101 fwd_p95=3.954 build=886.582 rss=505200640 idx=225076756
4. `csr` — rev_p95=68.065 fwd_p95=2.249 build=897.966 rss=366190592 idx=57395901
5. `hash` — rev_p95=430.276 fwd_p95=4.865 build=481.577 rss=362967040 idx=127042437

### reverse_heavy × hubby × 500k

1. `csr_csc` — rev_p95=0.042 fwd_p95=0.884 build=448.708 rss=193875968 idx=48229171
2. `hash_bi` — rev_p95=0.081 fwd_p95=1.702 build=358.239 rss=274198528 idx=110644876
3. `hybrid` — rev_p95=0.083 fwd_p95=1.610 build=403.882 rss=189509632 idx=48229171
4. `csr` — rev_p95=29.956 fwd_p95=1.653 build=304.058 rss=189771776 idx=28698760
5. `hash` — rev_p95=176.719 fwd_p95=3.454 build=143.466 rss=205725696 idx=61610095

### reverse_heavy × layered × 1M

1. `csr_csc` — rev_p95=0.035 fwd_p95=0.032 build=916.737 rss=348061696 idx=91576746
2. `hybrid` — rev_p95=0.057 fwd_p95=0.057 build=890.572 rss=348114944 idx=91576746
3. `hash_bi` — rev_p95=0.071 fwd_p95=0.050 build=773.409 rss=466530304 idx=203935314
4. `csr` — rev_p95=156.902 fwd_p95=0.100 build=633.963 rss=321515520 idx=54624010
5. `hash` — rev_p95=1110.438 fwd_p95=0.194 build=336.783 rss=321757184 idx=107613450

### reverse_heavy × layered × 500k

1. `csr_csc` — rev_p95=0.027 fwd_p95=0.033 build=442.785 rss=181936128 idx=45789010
2. `hybrid` — rev_p95=0.041 fwd_p95=0.064 build=426.044 rss=188145664 idx=45789010
3. `hash_bi` — rev_p95=0.045 fwd_p95=0.058 build=361.198 rss=255156224 idx=101999682
4. `csr` — rev_p95=61.749 fwd_p95=0.113 build=312.951 rss=167714816 idx=27312547
5. `hash` — rev_p95=409.790 fwd_p95=0.197 build=155.965 rss=182681600 idx=53862929

### reverse_heavy × power_law × 1M

1. `csr_csc` — rev_p95=0.105 fwd_p95=14.780 build=993.402 rss=361730048 idx=96389465
2. `hash_bi` — rev_p95=0.118 fwd_p95=25.994 build=651.901 rss=495591424 idx=209383453
3. `hybrid` — rev_p95=0.154 fwd_p95=23.898 build=1054.693 rss=354512896 idx=96389465
4. `csr` — rev_p95=41.592 fwd_p95=15.684 build=720.789 rss=300195840 idx=57335521
5. `hash` — rev_p95=245.544 fwd_p95=28.793 build=212.279 rss=364990464 idx=111398231

### reverse_heavy × power_law × 500k

1. `csr_csc` — rev_p95=0.055 fwd_p95=13.681 build=394.951 rss=190545920 idx=48194091
2. `hybrid` — rev_p95=0.096 fwd_p95=27.307 build=446.324 rss=195026944 idx=48194091
3. `hash_bi` — rev_p95=0.098 fwd_p95=23.409 build=240.628 rss=257708032 idx=104511823
4. `csr` — rev_p95=11.584 fwd_p95=13.447 build=267.220 rss=166981632 idx=28667434
5. `hash` — rev_p95=88.046 fwd_p95=25.823 build=91.797 rss=193585152 idx=55473766

### reverse_heavy × uniform × 1M

1. `csr_csc` — rev_p95=0.050 fwd_p95=0.099 build=1093.079 rss=365486080 idx=96461388
2. `hash_bi` — rev_p95=0.062 fwd_p95=0.137 build=941.021 rss=490569728 idx=214426970
3. `hybrid` — rev_p95=0.083 fwd_p95=0.125 build=1078.259 rss=362061824 idx=96461388
4. `csr` — rev_p95=82.742 fwd_p95=0.213 build=746.783 rss=359653376 idx=57400989
5. `hash` — rev_p95=667.586 fwd_p95=0.522 build=481.612 rss=354410496 idx=116379550

### reverse_heavy × uniform × 500k

1. `csr_csc` — rev_p95=0.035 fwd_p95=0.081 build=415.579 rss=193077248 idx=48231500
2. `hash_bi` — rev_p95=0.053 fwd_p95=0.142 build=345.880 rss=279937024 idx=107231142
3. `hybrid` — rev_p95=0.060 fwd_p95=0.179 build=378.871 rss=194691072 idx=48231500
4. `csr` — rev_p95=43.277 fwd_p95=0.240 build=269.069 rss=189120512 idx=28700912
5. `hash` — rev_p95=308.694 fwd_p95=0.496 build=167.921 rss=219246592 idx=58184284

## Crossover candidates

- `('balanced', 'community', '1M')`: `csr_csc` reverse p95 (0.027) beats `hash_bi` (0.036)
- `('balanced', 'community', '1M')`: `csr_csc` steady index (96476528) undercuts `hash_bi` (216290352)
- `('forward_dominant', 'community', '1M')`: `csr_csc` reverse p95 (0.027) beats `hash_bi` (0.045)
- `('forward_dominant', 'community', '1M')`: `csr_csc` steady index (96476528) undercuts `hash_bi` (216290352)
- `('reverse_heavy', 'community', '1M')`: `csr_csc` reverse p95 (0.040) beats `hash_bi` (0.071)
- `('reverse_heavy', 'community', '1M')`: `csr_csc` steady index (96476528) undercuts `hash_bi` (216290352)
- `('balanced', 'hierarchical', '1M')`: `csr_csc` reverse p95 (0.094) beats `hash_bi` (0.159)
- `('balanced', 'hierarchical', '1M')`: `csr_csc` steady index (99998385) undercuts `hash_bi` (233679413)
- `('forward_dominant', 'hierarchical', '1M')`: `csr_csc` reverse p95 (0.197) beats `hash_bi` (0.245)
- `('forward_dominant', 'hierarchical', '1M')`: `csr_csc` steady index (99998385) undercuts `hash_bi` (233679413)
- `('reverse_heavy', 'hierarchical', '1M')`: `csr_csc` reverse p95 (0.083) beats `hash_bi` (0.169)
- `('reverse_heavy', 'hierarchical', '1M')`: `csr_csc` steady index (99998385) undercuts `hash_bi` (233679413)
- `('balanced', 'hubby', '1M')`: `csr_csc` steady index (96455904) undercuts `hash_bi` (225076756)
- `('forward_dominant', 'hubby', '1M')`: `csr_csc` reverse p95 (0.087) beats `hash_bi` (0.145)
- `('forward_dominant', 'hubby', '1M')`: `csr_csc` steady index (96455904) undercuts `hash_bi` (225076756)
- `('reverse_heavy', 'hubby', '1M')`: `csr_csc` reverse p95 (0.052) beats `hash_bi` (0.101)
- `('reverse_heavy', 'hubby', '1M')`: `csr_csc` steady index (96455904) undercuts `hash_bi` (225076756)
- `('balanced', 'layered', '1M')`: `csr_csc` reverse p95 (0.041) beats `hash_bi` (0.052)
- `('balanced', 'layered', '1M')`: `csr_csc` steady index (91576746) undercuts `hash_bi` (203935314)
- `('forward_dominant', 'layered', '1M')`: `csr_csc` steady index (91576746) undercuts `hash_bi` (203935314)
- `('reverse_heavy', 'layered', '1M')`: `csr_csc` reverse p95 (0.035) beats `hash_bi` (0.071)
- `('reverse_heavy', 'layered', '1M')`: `csr_csc` steady index (91576746) undercuts `hash_bi` (203935314)
- `('balanced', 'power_law', '1M')`: `csr_csc` reverse p95 (0.092) beats `hash_bi` (0.170)
- `('balanced', 'power_law', '1M')`: `csr_csc` steady index (96389465) undercuts `hash_bi` (209383453)
- `('forward_dominant', 'power_law', '1M')`: `csr_csc` reverse p95 (0.059) beats `hash_bi` (0.111)
- `('forward_dominant', 'power_law', '1M')`: `csr_csc` steady index (96389465) undercuts `hash_bi` (209383453)
- `('forward_dominant', 'power_law', '1M')`: `hash` wins forward-only build (194.3 vs hash_bi 543.5) with similar fwd tail
- `('reverse_heavy', 'power_law', '1M')`: `csr_csc` reverse p95 (0.105) beats `hash_bi` (0.118)
- `('reverse_heavy', 'power_law', '1M')`: `csr_csc` steady index (96389465) undercuts `hash_bi` (209383453)
- `('balanced', 'uniform', '1M')`: `csr_csc` reverse p95 (0.035) beats `hash_bi` (0.107)
- `('balanced', 'uniform', '1M')`: `csr_csc` steady index (96461388) undercuts `hash_bi` (214426970)
- `('forward_dominant', 'uniform', '1M')`: `csr_csc` reverse p95 (0.106) beats `hash_bi` (0.162)
- `('forward_dominant', 'uniform', '1M')`: `csr_csc` steady index (96461388) undercuts `hash_bi` (214426970)
- `('reverse_heavy', 'uniform', '1M')`: `csr_csc` reverse p95 (0.050) beats `hash_bi` (0.062)
- `('reverse_heavy', 'uniform', '1M')`: `csr_csc` steady index (96461388) undercuts `hash_bi` (214426970)
- `('forward_dominant', 'community', '500k')`: `csr_csc` reverse p95 (0.041) beats `hash_bi` (0.070)
- `('forward_dominant', 'community', '500k')`: `csr_csc` steady index (48236954) undercuts `hash_bi` (107386762)
- `('reverse_heavy', 'community', '500k')`: `csr_csc` reverse p95 (0.023) beats `hash_bi` (0.041)
- `('reverse_heavy', 'community', '500k')`: `csr_csc` steady index (48236954) undercuts `hash_bi` (107386762)
- `('forward_dominant', 'hierarchical', '500k')`: `csr_csc` steady index (49996780) undercuts `hash_bi` (116810301)
- `('reverse_heavy', 'hierarchical', '500k')`: `csr_csc` reverse p95 (0.137) beats `hash_bi` (0.287)
- `('reverse_heavy', 'hierarchical', '500k')`: `csr_csc` steady index (49996780) undercuts `hash_bi` (116810301)
- `('forward_dominant', 'hubby', '500k')`: `csr_csc` reverse p95 (0.055) beats `hash_bi` (0.128)
- `('forward_dominant', 'hubby', '500k')`: `csr_csc` steady index (48229171) undercuts `hash_bi` (110644876)
- `('reverse_heavy', 'hubby', '500k')`: `csr_csc` reverse p95 (0.042) beats `hash_bi` (0.081)
- `('reverse_heavy', 'hubby', '500k')`: `csr_csc` steady index (48229171) undercuts `hash_bi` (110644876)
- `('forward_dominant', 'layered', '500k')`: `csr_csc` reverse p95 (0.027) beats `hash_bi` (0.048)
- `('forward_dominant', 'layered', '500k')`: `csr_csc` steady index (45789010) undercuts `hash_bi` (101999682)
- `('reverse_heavy', 'layered', '500k')`: `csr_csc` reverse p95 (0.027) beats `hash_bi` (0.045)
- `('reverse_heavy', 'layered', '500k')`: `csr_csc` steady index (45789010) undercuts `hash_bi` (101999682)
- `('forward_dominant', 'power_law', '500k')`: `csr_csc` reverse p95 (0.034) beats `hash_bi` (0.055)
- `('forward_dominant', 'power_law', '500k')`: `csr_csc` steady index (48194091) undercuts `hash_bi` (104511823)
- `('reverse_heavy', 'power_law', '500k')`: `csr_csc` reverse p95 (0.055) beats `hash_bi` (0.098)
- `('reverse_heavy', 'power_law', '500k')`: `csr_csc` steady index (48194091) undercuts `hash_bi` (104511823)
- `('forward_dominant', 'uniform', '500k')`: `csr_csc` reverse p95 (0.083) beats `hash_bi` (0.110)
- `('forward_dominant', 'uniform', '500k')`: `csr_csc` steady index (48231500) undercuts `hash_bi` (107231142)
- `('reverse_heavy', 'uniform', '500k')`: `csr_csc` reverse p95 (0.035) beats `hash_bi` (0.053)
- `('reverse_heavy', 'uniform', '500k')`: `csr_csc` steady index (48231500) undercuts `hash_bi` (107231142)
- `('balanced', 'hubby', '5M')`: `csr_csc` reverse p95 (0.030) beats `hash_bi` (0.051)
- `('balanced', 'hubby', '5M')`: `csr_csc` steady index (509861254) undercuts `hash_bi` (1126642782)
- `('balanced', 'uniform', '5M')`: `csr_csc` reverse p95 (0.032) beats `hash_bi` (0.056)
- `('balanced', 'uniform', '5M')`: `csr_csc` steady index (509889449) undercuts `hash_bi` (1099989643)
- `('forward_dominant', 'uniform', '5M')`: `csr_csc` reverse p95 (0.093) beats `hash_bi` (0.142)
- `('forward_dominant', 'uniform', '5M')`: `csr_csc` steady index (509889449) undercuts `hash_bi` (1099989643)

## Illustrative index-economics break-even (not a decision lock)

For each regime with both `hash` and `hash_bi` (or `csr_csc`), estimate `cost(Qr) ≈ (1−Qr)·mean_fwd + Qr·mean_rev` using **mean** class latencies from the trace. Labeled **illustrative** only.

### balanced × community × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.016 | 0.006 | hash_bi |
| 10% | 7.363 | 0.006 | hash_bi |
| 20% | 14.710 | 0.006 | hash_bi |
| 30% | 22.057 | 0.006 | hash_bi |
| 40% | 29.404 | 0.006 | hash_bi |
| 50% | 36.751 | 0.005 | hash_bi |
| 60% | 44.098 | 0.005 | hash_bi |
| 70% | 51.446 | 0.005 | hash_bi |
| 80% | 58.793 | 0.005 | hash_bi |
| 90% | 66.140 | 0.004 | hash_bi |
| 100% | 73.487 | 0.004 | hash_bi |

### balanced × community × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.005 | 0.001 | hash_bi |
| 10% | 0.443 | 0.001 | hash_bi |
| 20% | 0.881 | 0.001 | hash_bi |
| 30% | 1.319 | 0.001 | hash_bi |
| 40% | 1.757 | 0.001 | hash_bi |
| 50% | 2.195 | 0.001 | hash_bi |
| 60% | 2.633 | 0.001 | hash_bi |
| 70% | 3.071 | 0.001 | hash_bi |
| 80% | 3.509 | 0.000 | hash_bi |
| 90% | 3.948 | 0.000 | hash_bi |
| 100% | 4.386 | 0.000 | hash_bi |

### balanced × hierarchical × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.011 | 0.003 | hash_bi |
| 10% | 5.020 | 0.003 | hash_bi |
| 20% | 10.029 | 0.004 | hash_bi |
| 30% | 15.039 | 0.004 | hash_bi |
| 40% | 20.048 | 0.005 | hash_bi |
| 50% | 25.057 | 0.005 | hash_bi |
| 60% | 30.067 | 0.006 | hash_bi |
| 70% | 35.076 | 0.006 | hash_bi |
| 80% | 40.085 | 0.007 | hash_bi |
| 90% | 45.094 | 0.007 | hash_bi |
| 100% | 50.104 | 0.008 | hash_bi |

### balanced × hierarchical × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.005 | 0.000 | hash_bi |
| 10% | 0.391 | 0.000 | hash_bi |
| 20% | 0.776 | 0.000 | hash_bi |
| 30% | 1.162 | 0.000 | hash_bi |
| 40% | 1.548 | 0.000 | hash_bi |
| 50% | 1.933 | 0.000 | hash_bi |
| 60% | 2.319 | 0.000 | hash_bi |
| 70% | 2.704 | 0.000 | hash_bi |
| 80% | 3.090 | 0.000 | hash_bi |
| 90% | 3.476 | 0.000 | hash_bi |
| 100% | 3.861 | 0.000 | hash_bi |

### balanced × hubby × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.010 | 0.003 | hash_bi |
| 10% | 10.509 | 0.003 | hash_bi |
| 20% | 21.008 | 0.004 | hash_bi |
| 30% | 31.508 | 0.004 | hash_bi |
| 40% | 42.007 | 0.005 | hash_bi |
| 50% | 52.506 | 0.005 | hash_bi |
| 60% | 63.005 | 0.006 | hash_bi |
| 70% | 73.504 | 0.006 | hash_bi |
| 80% | 84.003 | 0.007 | hash_bi |
| 90% | 94.503 | 0.007 | hash_bi |
| 100% | 105.002 | 0.008 | hash_bi |

### balanced × hubby × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.003 | 0.000 | hash_bi |
| 10% | 0.266 | 0.000 | hash_bi |
| 20% | 0.529 | 0.000 | hash_bi |
| 30% | 0.791 | 0.001 | hash_bi |
| 40% | 1.054 | 0.001 | hash_bi |
| 50% | 1.317 | 0.001 | hash_bi |
| 60% | 1.580 | 0.001 | hash_bi |
| 70% | 1.842 | 0.001 | hash_bi |
| 80% | 2.105 | 0.001 | hash_bi |
| 90% | 2.368 | 0.001 | hash_bi |
| 100% | 2.631 | 0.001 | hash_bi |

### balanced × hubby × 5M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.012 | 0.002 | hash_bi |
| 10% | 53.081 | 0.003 | hash_bi |
| 20% | 106.150 | 0.003 | hash_bi |
| 30% | 159.219 | 0.003 | hash_bi |
| 40% | 212.288 | 0.004 | hash_bi |
| 50% | 265.357 | 0.004 | hash_bi |
| 60% | 318.426 | 0.004 | hash_bi |
| 70% | 371.495 | 0.005 | hash_bi |
| 80% | 424.564 | 0.005 | hash_bi |
| 90% | 477.633 | 0.005 | hash_bi |
| 100% | 530.702 | 0.006 | hash_bi |

### balanced × layered × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.020 | 0.003 | hash_bi |
| 10% | 1.783 | 0.003 | hash_bi |
| 20% | 3.545 | 0.002 | hash_bi |
| 30% | 5.308 | 0.002 | hash_bi |
| 40% | 7.070 | 0.002 | hash_bi |
| 50% | 8.833 | 0.002 | hash_bi |
| 60% | 10.595 | 0.002 | hash_bi |
| 70% | 12.358 | 0.002 | hash_bi |
| 80% | 14.120 | 0.002 | hash_bi |
| 90% | 15.883 | 0.002 | hash_bi |
| 100% | 17.645 | 0.001 | hash_bi |

### balanced × layered × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.003 | 0.000 | hash_bi |
| 10% | 0.173 | 0.000 | hash_bi |
| 20% | 0.343 | 0.000 | hash_bi |
| 30% | 0.513 | 0.000 | hash_bi |
| 40% | 0.683 | 0.000 | hash_bi |
| 50% | 0.853 | 0.000 | hash_bi |
| 60% | 1.023 | 0.000 | hash_bi |
| 70% | 1.193 | 0.000 | hash_bi |
| 80% | 1.363 | 0.000 | hash_bi |
| 90% | 1.533 | 0.000 | hash_bi |
| 100% | 1.703 | 0.000 | hash_bi |

### balanced × power_law × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.142 | 0.096 | hash_bi |
| 10% | 4.369 | 0.087 | hash_bi |
| 20% | 8.596 | 0.079 | hash_bi |
| 30% | 12.824 | 0.071 | hash_bi |
| 40% | 17.051 | 0.062 | hash_bi |
| 50% | 21.278 | 0.054 | hash_bi |
| 60% | 25.506 | 0.046 | hash_bi |
| 70% | 29.733 | 0.037 | hash_bi |
| 80% | 33.960 | 0.029 | hash_bi |
| 90% | 38.187 | 0.021 | hash_bi |
| 100% | 42.415 | 0.012 | hash_bi |

### balanced × power_law × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.000 | 0.000 | hash_bi |
| 10% | 0.001 | 0.000 | hash_bi |
| 20% | 0.002 | 0.000 | hash_bi |
| 30% | 0.003 | 0.000 | hash_bi |
| 40% | 0.004 | 0.000 | hash_bi |
| 50% | 0.005 | 0.000 | hash_bi |
| 60% | 0.006 | 0.000 | hash_bi |
| 70% | 0.007 | 0.000 | hash_bi |
| 80% | 0.008 | 0.000 | hash_bi |
| 90% | 0.009 | 0.000 | hash_bi |
| 100% | 0.010 | 0.000 | hash_bi |

### balanced × uniform × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.018 | 0.007 | hash_bi |
| 10% | 7.369 | 0.007 | hash_bi |
| 20% | 14.721 | 0.007 | hash_bi |
| 30% | 22.072 | 0.008 | hash_bi |
| 40% | 29.424 | 0.008 | hash_bi |
| 50% | 36.775 | 0.008 | hash_bi |
| 60% | 44.127 | 0.008 | hash_bi |
| 70% | 51.478 | 0.009 | hash_bi |
| 80% | 58.830 | 0.009 | hash_bi |
| 90% | 66.181 | 0.009 | hash_bi |
| 100% | 73.533 | 0.009 | hash_bi |

### balanced × uniform × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.004 | 0.001 | hash_bi |
| 10% | 0.390 | 0.001 | hash_bi |
| 20% | 0.775 | 0.001 | hash_bi |
| 30% | 1.161 | 0.001 | hash_bi |
| 40% | 1.546 | 0.001 | hash_bi |
| 50% | 1.932 | 0.001 | hash_bi |
| 60% | 2.317 | 0.000 | hash_bi |
| 70% | 2.703 | 0.000 | hash_bi |
| 80% | 3.088 | 0.000 | hash_bi |
| 90% | 3.474 | 0.000 | hash_bi |
| 100% | 3.859 | 0.000 | hash_bi |

### balanced × uniform × 5M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.021 | 0.006 | hash_bi |
| 10% | 49.106 | 0.006 | hash_bi |
| 20% | 98.191 | 0.006 | hash_bi |
| 30% | 147.275 | 0.006 | hash_bi |
| 40% | 196.360 | 0.005 | hash_bi |
| 50% | 245.445 | 0.005 | hash_bi |
| 60% | 294.530 | 0.005 | hash_bi |
| 70% | 343.615 | 0.005 | hash_bi |
| 80% | 392.700 | 0.005 | hash_bi |
| 90% | 441.785 | 0.005 | hash_bi |
| 100% | 490.870 | 0.005 | hash_bi |

### forward_dominant × community × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.006 | 0.004 | hash_bi |
| 10% | 7.126 | 0.004 | hash_bi |
| 20% | 14.246 | 0.004 | hash_bi |
| 30% | 21.367 | 0.004 | hash_bi |
| 40% | 28.487 | 0.005 | hash_bi |
| 50% | 35.608 | 0.005 | hash_bi |
| 60% | 42.728 | 0.005 | hash_bi |
| 70% | 49.848 | 0.005 | hash_bi |
| 80% | 56.969 | 0.005 | hash_bi |
| 90% | 64.089 | 0.006 | hash_bi |
| 100% | 71.210 | 0.006 | hash_bi |

### forward_dominant × community × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.011 | 0.008 | hash_bi |
| 10% | 5.324 | 0.009 | hash_bi |
| 20% | 10.637 | 0.009 | hash_bi |
| 30% | 15.950 | 0.010 | hash_bi |
| 40% | 21.263 | 0.010 | hash_bi |
| 50% | 26.576 | 0.011 | hash_bi |
| 60% | 31.890 | 0.011 | hash_bi |
| 70% | 37.203 | 0.012 | hash_bi |
| 80% | 42.516 | 0.013 | hash_bi |
| 90% | 47.829 | 0.013 | hash_bi |
| 100% | 53.142 | 0.014 | hash_bi |

### forward_dominant × hierarchical × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.010 | 0.009 | hash_bi |
| 10% | 20.457 | 0.010 | hash_bi |
| 20% | 40.903 | 0.011 | hash_bi |
| 30% | 61.349 | 0.012 | hash_bi |
| 40% | 81.795 | 0.013 | hash_bi |
| 50% | 102.241 | 0.015 | hash_bi |
| 60% | 122.688 | 0.016 | hash_bi |
| 70% | 143.134 | 0.017 | hash_bi |
| 80% | 163.580 | 0.018 | hash_bi |
| 90% | 184.026 | 0.019 | hash_bi |
| 100% | 204.472 | 0.020 | hash_bi |

### forward_dominant × hierarchical × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.009 | 0.009 | hash |
| 10% | 2.516 | 0.009 | hash_bi |
| 20% | 5.024 | 0.010 | hash_bi |
| 30% | 7.531 | 0.011 | hash_bi |
| 40% | 10.039 | 0.011 | hash_bi |
| 50% | 12.546 | 0.012 | hash_bi |
| 60% | 15.054 | 0.012 | hash_bi |
| 70% | 17.561 | 0.013 | hash_bi |
| 80% | 20.069 | 0.013 | hash_bi |
| 90% | 22.576 | 0.014 | hash_bi |
| 100% | 25.084 | 0.015 | hash_bi |

### forward_dominant × hubby × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.004 | 0.003 | hash_bi |
| 10% | 10.004 | 0.004 | hash_bi |
| 20% | 20.003 | 0.005 | hash_bi |
| 30% | 30.003 | 0.006 | hash_bi |
| 40% | 40.002 | 0.008 | hash_bi |
| 50% | 50.001 | 0.009 | hash_bi |
| 60% | 60.001 | 0.010 | hash_bi |
| 70% | 70.000 | 0.011 | hash_bi |
| 80% | 79.999 | 0.012 | hash_bi |
| 90% | 89.999 | 0.013 | hash_bi |
| 100% | 99.998 | 0.014 | hash_bi |

### forward_dominant × hubby × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.003 | 0.001 | hash_bi |
| 10% | 3.791 | 0.003 | hash_bi |
| 20% | 7.580 | 0.005 | hash_bi |
| 30% | 11.368 | 0.007 | hash_bi |
| 40% | 15.157 | 0.009 | hash_bi |
| 50% | 18.945 | 0.011 | hash_bi |
| 60% | 22.734 | 0.013 | hash_bi |
| 70% | 26.522 | 0.015 | hash_bi |
| 80% | 30.311 | 0.017 | hash_bi |
| 90% | 34.099 | 0.018 | hash_bi |
| 100% | 37.888 | 0.020 | hash_bi |

### forward_dominant × layered × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.009 | 0.003 | hash_bi |
| 10% | 7.327 | 0.003 | hash_bi |
| 20% | 14.645 | 0.004 | hash_bi |
| 30% | 21.963 | 0.004 | hash_bi |
| 40% | 29.281 | 0.005 | hash_bi |
| 50% | 36.599 | 0.005 | hash_bi |
| 60% | 43.917 | 0.006 | hash_bi |
| 70% | 51.236 | 0.006 | hash_bi |
| 80% | 58.554 | 0.007 | hash_bi |
| 90% | 65.872 | 0.007 | hash_bi |
| 100% | 73.190 | 0.007 | hash_bi |

### forward_dominant × layered × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.008 | 0.006 | hash_bi |
| 10% | 4.469 | 0.006 | hash_bi |
| 20% | 8.931 | 0.006 | hash_bi |
| 30% | 13.392 | 0.006 | hash_bi |
| 40% | 17.854 | 0.006 | hash_bi |
| 50% | 22.316 | 0.007 | hash_bi |
| 60% | 26.777 | 0.007 | hash_bi |
| 70% | 31.239 | 0.007 | hash_bi |
| 80% | 35.701 | 0.007 | hash_bi |
| 90% | 40.162 | 0.007 | hash_bi |
| 100% | 44.624 | 0.007 | hash_bi |

### forward_dominant × power_law × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.019 | 0.019 | hash_bi |
| 10% | 2.955 | 0.020 | hash_bi |
| 20% | 5.890 | 0.020 | hash_bi |
| 30% | 8.826 | 0.021 | hash_bi |
| 40% | 11.761 | 0.022 | hash_bi |
| 50% | 14.697 | 0.023 | hash_bi |
| 60% | 17.632 | 0.024 | hash_bi |
| 70% | 20.568 | 0.024 | hash_bi |
| 80% | 23.503 | 0.025 | hash_bi |
| 90% | 26.439 | 0.026 | hash_bi |
| 100% | 29.374 | 0.027 | hash_bi |

### forward_dominant × power_law × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.017 | 0.014 | hash_bi |
| 10% | 1.645 | 0.014 | hash_bi |
| 20% | 3.274 | 0.014 | hash_bi |
| 30% | 4.903 | 0.014 | hash_bi |
| 40% | 6.531 | 0.014 | hash_bi |
| 50% | 8.160 | 0.014 | hash_bi |
| 60% | 9.789 | 0.014 | hash_bi |
| 70% | 11.418 | 0.014 | hash_bi |
| 80% | 13.046 | 0.014 | hash_bi |
| 90% | 14.675 | 0.014 | hash_bi |
| 100% | 16.304 | 0.014 | hash_bi |

### forward_dominant × uniform × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.011 | 0.007 | hash_bi |
| 10% | 9.736 | 0.008 | hash_bi |
| 20% | 19.461 | 0.009 | hash_bi |
| 30% | 29.187 | 0.010 | hash_bi |
| 40% | 38.912 | 0.011 | hash_bi |
| 50% | 48.637 | 0.012 | hash_bi |
| 60% | 58.363 | 0.013 | hash_bi |
| 70% | 68.088 | 0.014 | hash_bi |
| 80% | 77.813 | 0.015 | hash_bi |
| 90% | 87.539 | 0.016 | hash_bi |
| 100% | 97.264 | 0.017 | hash_bi |

### forward_dominant × uniform × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.009 | 0.009 | hash_bi |
| 10% | 3.580 | 0.009 | hash_bi |
| 20% | 7.151 | 0.010 | hash_bi |
| 30% | 10.721 | 0.011 | hash_bi |
| 40% | 14.292 | 0.012 | hash_bi |
| 50% | 17.863 | 0.013 | hash_bi |
| 60% | 21.434 | 0.014 | hash_bi |
| 70% | 25.004 | 0.014 | hash_bi |
| 80% | 28.575 | 0.015 | hash_bi |
| 90% | 32.146 | 0.016 | hash_bi |
| 100% | 35.716 | 0.017 | hash_bi |

### forward_dominant × uniform × 5M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.012 | 0.009 | hash_bi |
| 10% | 67.869 | 0.012 | hash_bi |
| 20% | 135.727 | 0.015 | hash_bi |
| 30% | 203.584 | 0.019 | hash_bi |
| 40% | 271.442 | 0.022 | hash_bi |
| 50% | 339.299 | 0.026 | hash_bi |
| 60% | 407.157 | 0.029 | hash_bi |
| 70% | 475.014 | 0.032 | hash_bi |
| 80% | 542.872 | 0.036 | hash_bi |
| 90% | 610.729 | 0.039 | hash_bi |
| 100% | 678.587 | 0.043 | hash_bi |

### reverse_heavy × community × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.049 | 0.012 | hash_bi |
| 10% | 10.428 | 0.011 | hash_bi |
| 20% | 20.806 | 0.010 | hash_bi |
| 30% | 31.185 | 0.010 | hash_bi |
| 40% | 41.563 | 0.009 | hash_bi |
| 50% | 51.942 | 0.008 | hash_bi |
| 60% | 62.321 | 0.008 | hash_bi |
| 70% | 72.699 | 0.007 | hash_bi |
| 80% | 83.078 | 0.006 | hash_bi |
| 90% | 93.457 | 0.006 | hash_bi |
| 100% | 103.835 | 0.005 | hash_bi |

### reverse_heavy × community × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.041 | 0.007 | hash_bi |
| 10% | 3.314 | 0.007 | hash_bi |
| 20% | 6.587 | 0.007 | hash_bi |
| 30% | 9.860 | 0.006 | hash_bi |
| 40% | 13.134 | 0.006 | hash_bi |
| 50% | 16.407 | 0.006 | hash_bi |
| 60% | 19.680 | 0.006 | hash_bi |
| 70% | 22.953 | 0.005 | hash_bi |
| 80% | 26.226 | 0.005 | hash_bi |
| 90% | 29.499 | 0.005 | hash_bi |
| 100% | 32.773 | 0.005 | hash_bi |

### reverse_heavy × hierarchical × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.049 | 0.021 | hash_bi |
| 10% | 12.504 | 0.020 | hash_bi |
| 20% | 24.958 | 0.018 | hash_bi |
| 30% | 37.413 | 0.017 | hash_bi |
| 40% | 49.868 | 0.015 | hash_bi |
| 50% | 62.322 | 0.014 | hash_bi |
| 60% | 74.777 | 0.013 | hash_bi |
| 70% | 87.231 | 0.011 | hash_bi |
| 80% | 99.686 | 0.010 | hash_bi |
| 90% | 112.141 | 0.008 | hash_bi |
| 100% | 124.595 | 0.007 | hash_bi |

### reverse_heavy × hierarchical × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.061 | 0.019 | hash_bi |
| 10% | 8.783 | 0.018 | hash_bi |
| 20% | 17.505 | 0.018 | hash_bi |
| 30% | 26.227 | 0.017 | hash_bi |
| 40% | 34.949 | 0.017 | hash_bi |
| 50% | 43.671 | 0.016 | hash_bi |
| 60% | 52.393 | 0.016 | hash_bi |
| 70% | 61.115 | 0.015 | hash_bi |
| 80% | 69.837 | 0.014 | hash_bi |
| 90% | 78.559 | 0.014 | hash_bi |
| 100% | 87.281 | 0.013 | hash_bi |

### reverse_heavy × hubby × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.039 | 0.014 | hash_bi |
| 10% | 7.226 | 0.013 | hash_bi |
| 20% | 14.413 | 0.012 | hash_bi |
| 30% | 21.601 | 0.011 | hash_bi |
| 40% | 28.788 | 0.011 | hash_bi |
| 50% | 35.975 | 0.010 | hash_bi |
| 60% | 43.162 | 0.009 | hash_bi |
| 70% | 50.350 | 0.008 | hash_bi |
| 80% | 57.537 | 0.007 | hash_bi |
| 90% | 64.724 | 0.007 | hash_bi |
| 100% | 71.912 | 0.006 | hash_bi |

### reverse_heavy × hubby × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.026 | 0.013 | hash_bi |
| 10% | 3.038 | 0.012 | hash_bi |
| 20% | 6.050 | 0.012 | hash_bi |
| 30% | 9.062 | 0.011 | hash_bi |
| 40% | 12.073 | 0.010 | hash_bi |
| 50% | 15.085 | 0.009 | hash_bi |
| 60% | 18.097 | 0.009 | hash_bi |
| 70% | 21.109 | 0.008 | hash_bi |
| 80% | 24.121 | 0.007 | hash_bi |
| 90% | 27.133 | 0.006 | hash_bi |
| 100% | 30.144 | 0.006 | hash_bi |

### reverse_heavy × layered × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.041 | 0.010 | hash_bi |
| 10% | 6.446 | 0.010 | hash_bi |
| 20% | 12.852 | 0.009 | hash_bi |
| 30% | 19.258 | 0.008 | hash_bi |
| 40% | 25.664 | 0.007 | hash_bi |
| 50% | 32.070 | 0.007 | hash_bi |
| 60% | 38.475 | 0.006 | hash_bi |
| 70% | 44.881 | 0.005 | hash_bi |
| 80% | 51.287 | 0.005 | hash_bi |
| 90% | 57.693 | 0.004 | hash_bi |
| 100% | 64.099 | 0.003 | hash_bi |

### reverse_heavy × layered × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.031 | 0.009 | hash_bi |
| 10% | 1.467 | 0.009 | hash_bi |
| 20% | 2.903 | 0.008 | hash_bi |
| 30% | 4.339 | 0.007 | hash_bi |
| 40% | 5.775 | 0.007 | hash_bi |
| 50% | 7.210 | 0.006 | hash_bi |
| 60% | 8.646 | 0.005 | hash_bi |
| 70% | 10.082 | 0.004 | hash_bi |
| 80% | 11.518 | 0.004 | hash_bi |
| 90% | 12.954 | 0.003 | hash_bi |
| 100% | 14.389 | 0.002 | hash_bi |

### reverse_heavy × power_law × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 2.185 | 1.267 | hash_bi |
| 10% | 6.007 | 1.141 | hash_bi |
| 20% | 9.829 | 1.016 | hash_bi |
| 30% | 13.651 | 0.890 | hash_bi |
| 40% | 17.473 | 0.765 | hash_bi |
| 50% | 21.295 | 0.639 | hash_bi |
| 60% | 25.117 | 0.514 | hash_bi |
| 70% | 28.939 | 0.389 | hash_bi |
| 80% | 32.761 | 0.263 | hash_bi |
| 90% | 36.583 | 0.138 | hash_bi |
| 100% | 40.406 | 0.012 | hash_bi |

### reverse_heavy × power_law × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.769 | 0.439 | hash_bi |
| 10% | 2.520 | 0.396 | hash_bi |
| 20% | 4.272 | 0.353 | hash_bi |
| 30% | 6.023 | 0.310 | hash_bi |
| 40% | 7.774 | 0.267 | hash_bi |
| 50% | 9.526 | 0.224 | hash_bi |
| 60% | 11.277 | 0.181 | hash_bi |
| 70% | 13.029 | 0.138 | hash_bi |
| 80% | 14.780 | 0.095 | hash_bi |
| 90% | 16.531 | 0.052 | hash_bi |
| 100% | 18.283 | 0.009 | hash_bi |

### reverse_heavy × uniform × 1M

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.063 | 0.013 | hash_bi |
| 10% | 11.105 | 0.012 | hash_bi |
| 20% | 22.147 | 0.011 | hash_bi |
| 30% | 33.189 | 0.011 | hash_bi |
| 40% | 44.231 | 0.010 | hash_bi |
| 50% | 55.273 | 0.009 | hash_bi |
| 60% | 66.315 | 0.009 | hash_bi |
| 70% | 77.357 | 0.008 | hash_bi |
| 80% | 88.399 | 0.007 | hash_bi |
| 90% | 99.441 | 0.007 | hash_bi |
| 100% | 110.483 | 0.006 | hash_bi |

### reverse_heavy × uniform × 500k

| Qr | hash cost | hash_bi cost | cheaper |
| --: | --------: | -----------: | ------- |
| 0% | 0.045 | 0.010 | hash_bi |
| 10% | 3.786 | 0.009 | hash_bi |
| 20% | 7.526 | 0.009 | hash_bi |
| 30% | 11.266 | 0.008 | hash_bi |
| 40% | 15.007 | 0.008 | hash_bi |
| 50% | 18.747 | 0.007 | hash_bi |
| 60% | 22.487 | 0.007 | hash_bi |
| 70% | 26.228 | 0.006 | hash_bi |
| 80% | 29.968 | 0.006 | hash_bi |
| 90% | 33.708 | 0.005 | hash_bi |
| 100% | 37.449 | 0.005 | hash_bi |

## Skips / failures

- `SKIP remaining 5M full-matrix cells — thin ladder only (uniform+hubby × balanced × 5 layouts)`

## Explicit non-recommendation

Do **not** treat this screen as Motadata production topology guidance. Deferred: concurrency stress, mutation/lifecycle economics, 10M+, Stage 4.3–4.6 confirmation.
