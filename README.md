# CSV to Graph

This app reads psychological test log CSV files from `input/` and generates line-chart PNG files in `output/`.

It is designed to run with Docker Compose and automatically detects the CSV format based on the filename and column structure.

## Supported CSV Formats

The current implementation supports these log types:

- `cft_test_log.csv`
- `cft_extension_log.csv`
- `pitch_glide_test_log.csv`
- `fm_detection_test_log.csv`
- `two_point_orientation_discrimination_log.csv`
- `two_point_discrimination_log.csv`

## How It Works

- All `*.csv` files in `input/` are processed in order.
- The app tries these encodings when reading each file:
  - `utf-8-sig`
  - `utf-8`
  - `cp932`
- The CSV type is auto-detected from the filename or required columns.
- A chart is generated to match the progress-graph style expected for each test app.
- Output PNG files are saved to `output/`.
- If some files cannot be processed, the app prints a failure list and exits with a non-zero status.

## Usage

1. Put one or more CSV files into `input/`.
2. Run:

```bash
docker compose up -d --build
```

Generated PNG files will be written to `output/`.

If you want to override the default settings, create a `.env` file. The app also runs without `.env`.

## Directory Layout

- `input/`: source CSV files
- `output/`: generated PNG files
- `generate_graphs.py`: batch renderer
- `compose.yaml`: Docker Compose configuration
- `Dockerfile`: runtime image definition

## Output Behavior by Format

### Click Fusion Test

- Target rows: `stim_kind == 2`
- X-axis: `two_trial_index` when available, otherwise sequential index
- Y-axis: `gap_ms`
- Markers:
  - `reversal`
  - `small_reversal` or inferred small-step reversal from `step_mode`

### Click Fusion Extension

- X-axis: sequential index
- Y-axis: `gap_ms`
- Markers:
  - `correct`
  - `incorrect`

### Pitch Glide Test

- Target rows: `trial_type == "glide"`
- X-axis: `n_updates_glide`, or `glide_no_planned`, or sequential index
- Y-axis: `D_ms_presented`
- Markers:
  - big-step reversal
  - small-step reversal
- Reference line:
  - median threshold from the latest six small-step reversals when available
  - otherwise the last `threshold_live_median` value if present

### Frequency Modulation Detection Test

- Target rows: `trial_type == "rough"`
- X-axis: `rough_trial_no` when available, otherwise sequential index
- Y-axis: `mi`
- Markers:
  - big-step reversal
  - small-step reversal
- Reference line:
  - median threshold from the latest six small-step reversals when available
  - otherwise the last `threshold_live_mi` value if present

### Two-Point Orientation Discrimination

- Target rows: `phase == "test"`
- Output: one PNG per `phase_run`
- X-axis: `phase_trial`
- Y-axis: `size_mm`
- Markers:
  - first 4 reversals
  - reversals after the first 4

### Two-Point Discrimination

- Target rows:
  - `phase == "test"`
  - `stimulus_presented_code == 2`
- Output: one PNG per `phase_run`
- X-axis: `two_trial_index`
- Y-axis: `size_mm`
- Markers:
  - first 4 reversals
  - reversals after the first 4

## Environment Variables

You can change these values with a `.env` file:

```env
INPUT_DIR=/app/input
OUTPUT_DIR=/app/output
FIGURE_WIDTH=14
FIGURE_HEIGHT=8
CHART_TITLE_PREFIX=
```

- `INPUT_DIR`: directory containing source CSV files
- `OUTPUT_DIR`: directory for generated PNG files
- `FIGURE_WIDTH`: chart width
- `FIGURE_HEIGHT`: chart height
- `CHART_TITLE_PREFIX`: optional prefix added to chart titles

## Runtime Notes

- The Docker image installs `fonts-noto-cjk` so charts can render Japanese labels correctly.
- The renderer uses `matplotlib` with the non-interactive `Agg` backend.
- Dependencies are minimal: `pandas` and `matplotlib`.

## Unsupported CSV Files

If a CSV file does not match any supported format, it is reported as unsupported and included in the failure summary.
