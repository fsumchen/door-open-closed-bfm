# Code

- `extract_bfm.py` reads a local capture with `tshark`, selects VHT compressed beamforming reports for one phone/AP pair, parses per-tone SCIDX/phi/psi values, assigns interval labels, and omits a configurable transition margin.
- `analyze_capture_hw4.py` and `analyze_part3_hw4_reference.py` are supplied HW4 examples. The Part 3 script expects HE 2x2, 40 MHz, 122-tone feedback; the final-project capture here contains VHT reports and must not be passed through it unchanged.

The extractor is invoked with local phone and AP addresses. Those addresses are filters only and are not copied into the derived CSV.
