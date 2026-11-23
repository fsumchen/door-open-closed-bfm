# Paper outline — draft plan

1. Abstract: provisional, update after the different-day held-out evaluation.
2. Introduction: Wi-Fi sensing motivation; distinguish CSI from compressed BFM feedback; state the door open/closed task.
3. Background and related work: cite 2FiA, BFMSense, and BFMScan.
4. Data collection: AX211 monitor, separate `mon0`, Ruckus AP, iPhone beamformee, channel 44, 80 MHz monitor tune, door geometry, workload, and timestamp labeling.
5. Method: decode per-tone VHT feedback angles; form fixed-duration windows; report the classifier only after balanced labeled sessions exist.
6. Evaluation: include clearly marked same-day exploratory diagnostics; final result must split by whole day and include confusion matrix, class counts, and failure cases.
7. Limitations: current captures are same-day, labels are sparse/inferred after a single transition, and session/class imbalance is severe.
8. Discussion and conclusion.

Do not present the same-day 95% result as final. Update the abstract and evaluation after a balanced different-day session is captured and held out. Keep all figures tied to the author's own derived data.
