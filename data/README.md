# Data

Raw `.pcapng` files are intentionally excluded from Git. They contain unrelated apartment Wi-Fi traffic and must remain local.

`labels/session_intervals.csv` records the available timing notes. Rows marked `assumed_until_end` use the last reported state through the end of the 12-minute capture; revise them if there were later door changes. Session 1 has only a point note and its raw capture is unavailable, so it is not used in derived model data.

`derived/day1-session2.csv` and `derived/day1-session3.csv` contain only the user's iPhone VHT BFM reports, with per-report SCIDX, phi/psi codes, decoded angles, report width code, and timestamp-derived door labels. Phone/AP MACs are excluded.

After a 5-second transition margin, session 2 contributes 648 reports (4 closed, 644 open); session 3 contributes 1,636 reports (76 open, 1,560 closed). The labels are highly imbalanced within each session and are based on one recorded transition per session. Do not use these captures alone for a final performance claim; collect balanced alternating blocks and additional days.

`derived/windows-30s.csv` is an exploratory window set (35 windows) and `derived/exploratory_loso.json` records the diagnostic split outcome. The model evaluation is intentionally marked exploratory: one test fold contains only one class and the other training fold lacks both classes. Do not cite its 0% diagnostic fold accuracy as project performance.
