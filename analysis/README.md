# Analysis

This directory contains generated reports from IOI collection and computational stress testing.

## Current report
- `ioi_120bpm_run_01_report.json`

## Method
1. Collect human tap timing data as inter-onset intervals (IOIs)
2. Estimate an empirical jitter distribution from residuals relative to a rolling local median
3. Stress-test the tap-to-note mapping in two ways:
    - threshold-local perturbation analysis
    - full-sequence Monte Carlo replay

## Main interpretation

The same amount of timing noise produces much larger behavioral changes when the system operates near discrete decision thresholds than when it operates inside a stable region.
