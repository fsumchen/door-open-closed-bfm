# Code

- `extract_bfm.py`: selects VHT compressed beamforming reports for one phone/AP pair from a local capture, parses per-tone SCIDX/phi/psi values, assigns interval labels, records label certainty/report-width code, and excludes a transition margin.
- `make_windows.py`: forms 30-second windows and compact tone-angle summary features; drops sparse or mixed-label windows.
- `evaluate_loso.py`: exploratory standardized nearest-centroid baseline with leave-one-session-out splits. It writes confusion matrices and explicitly records skipped/one-class folds. Current results are not a final performance estimate.
- `plot_bfm_heatmaps.py`: creates exploratory phi-by-SCIDX over time SVG heatmaps from the user's derived data.
- `analyze_capture_hw4.py` and `analyze_part3_hw4_reference.py`: supplied HW4 examples. The Part 3 script expects HE 2x2, 40 MHz, 122-tone feedback; the final-project captures here contain VHT reports and should not be passed through it unchanged.

Dependencies: Python standard library and `tshark` for capture extraction. The derived CSVs omit phone/AP MAC addresses.
