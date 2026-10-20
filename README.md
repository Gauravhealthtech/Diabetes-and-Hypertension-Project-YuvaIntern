# Closing the Care Cascade for Diabetes and Hypertension in India

Data analysis project (Yuva Intern programme) on where the diabetes and hypertension care cascade (prevalence, awareness, treatment, control) breaks down across India, and which groups and areas are most affected.

**Current status:** Week 2 complete (data collection, cleaning and preprocessing). Next: Week 3 (visualization).

## What is in this repository

| File | Description |
| --- | --- |
| `clean_nfhs5.py` | Cleaning and preprocessing script for the NFHS-5 state and union territory fact sheet file |
| `nfhs5_states_clean_long.csv` | Cleaned long-format file: 4,847 rows (one per area and indicator), 18 columns |
| `nfhs5_cvd_dm_analysis.csv` | Analysis file for blood pressure and blood sugar: 444 rows (12 indicators x 37 areas) |
| `nfhs5_states.csv` | Raw input file, unchanged (to be added) |
| `cleaning_log.json` | Counts and checks produced by the script (generated on run) |
| `missing_state.png`, `bp_urban_rural.png` | Figures produced by the script |
| Week 1 and Week 2 reports | Strategic plan and cleaning workflow documentation |

## Data source

National Family Health Survey (NFHS-5), 2019-21: state and union territory fact sheet indicators (India, 36 states and UTs, 131 indicators; urban, rural and total values, plus NFHS-4 totals).
Citation: IIPS and ICF. *National Family Health Survey (NFHS-5), 2019-21.* Mumbai: IIPS.

This repository contains published aggregate data only. No individual-level (microdata) files are included, in line with the DHS Program terms of use.

## How to run

```bash
pip install pandas numpy matplotlib
# put nfhs5_states.csv in the same folder as the script
python clean_nfhs5.py
```

The script logs a SHA-256 checksum of the raw file, runs the cleaning steps, and writes the two cleaned CSVs, `cleaning_log.json` and the figures.

## Cleaning workflow (summary)

1. Freeze and profile the raw file
2. Standardise labels, units and area names
3. Check for duplicates
4. Check for impossible or placeholder values
5. Logic and outlier checks
6. Classify missing data (flagged, not imputed)
7. Derive variables (urban-rural gap, change since NFHS-4, group, flags)
8. Select blood pressure and blood sugar indicators for analysis
9. Validate against the national row and export

## Key findings from the cleaning

- No duplicate rows and no impossible values (no percentages outside 0 to 100, no negatives).
- Footnote digits and units were fused into 47 indicator labels; these were split into separate columns.
- Four area names were standardised (for example "NCT Delhi" to "Delhi", "&" to "and").
- One indicator (vitamin A dose) is worded differently across states; flagged, not pooled.
- Blood pressure and blood sugar labels appear twice with no sex given; women and men were assigned by order in the fact sheet and documented.
- Missing values are structural (small areas, suppressed cells), so they were flagged and **not imputed**.
- 46 statistical outliers were flagged, not deleted.

## Limitations

- State-level aggregates cannot show awareness, treatment and control; those need individual-level NFHS-5 microdata (access via the DHS Program).
- The file does not record why a value is missing.
- NFHS-5 biomarker data cover a limited age range, so findings do not describe all adults.

## Project roadmap

| Week | Stage | Status |
| --- | --- | --- |
| 1 | Strategy and planning | Done |
| 2 | Data collection, cleaning and preprocessing | Done |
| 3 | Data visualization and reporting | Next |
| 4 | Predictive analytics and modelling | Planned |
| 5 | Data quality assurance and compliance | Planned |
| 6 | Final presentation and reflection | Planned |

## Author

Gaurav
