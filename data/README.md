# Data

Raw `.pcapng` files are intentionally excluded from Git. They contain unrelated apartment Wi-Fi traffic and must remain local.

`labels/session_intervals.csv` records the available timing notes. Rows marked `assumed_until_end` use the last reported state through the end of the 12-minute capture; revise them if there were later door changes. Session 1 has only a point label note. Its 916 phone BFM reports are included as unlabeled derived data and excluded from model windows.

`derived/day1-session1-unlabeled.csv` contains 916 phone BFM reports without interval labels. `derived/day1-session2.csv` and `derived/day1-session3.csv` contain only the user's iPhone VHT BFM reports, with per-report SCIDX, phi/psi codes, decoded angles, report width code, and timestamp-derived door labels. Phone/AP MACs are excluded.

After a 5-second transition margin, session 2 contributes 648 reports (4 closed, 644 open); session 3 contributes 1,636 reports (76 open, 1,560 closed). Four additional five-minute captures collected on 23 November contribute: env1 open 1,504, env1 closed 3,183, env2 open 2,303, and env2 closed 2,090 phone BFM reports. Env1's paired states used different AP radios, while env2 used the same radio. Raw captures are local under `/tmp/door-*.pcapng` and are excluded from Git. The new labels identify one state per capture, based on the user's notes.

`derived/windows-30s-current.csv` contains 75 exploratory windows. `derived/exploratory_loso_current.json` records capture-level leave-one-session-out results (mean fold accuracy 22.0%; most test folds contain one class). `derived/exploratory_env2_holdout.json` holds out both env2 captures together: 20 test windows, balanced 10/10, with 19 correct (95.0%; confusion matrix closed 10/10 and open 9/10). This is a same-day exploratory result, not a generalization claim. Env1 changes AP radio between door states. A matched different-day collection and evaluation remain necessary.
