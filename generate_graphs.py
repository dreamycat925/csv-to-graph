from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

matplotlib.rcParams["font.family"] = "Noto Sans CJK JP"
matplotlib.rcParams["axes.unicode_minus"] = False


ENCODINGS = ("utf-8-sig", "utf-8", "cp932")
BIG_REV_COLOR = "#2563eb"
SMALL_REV_COLOR = "#dc2626"
LINE_COLOR = "#475569"


@dataclass
class PlotResult:
    output_paths: list[Path]


def load_csv(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ENCODINGS:
        try:
            return pd.read_csv(path, encoding=encoding)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"CSV read failed: {path.name}: {last_error}")


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def boolish(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).astype(str).str.lower().isin({"1", "true", "t", "yes"})


def style_axes(ax: plt.Axes, *, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)


def save_figure(fig: plt.Figure, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def title_for(csv_path: Path, suffix: str = "") -> str:
    prefix = os.getenv("CHART_TITLE_PREFIX", "").strip()
    base = csv_path.stem if not suffix else f"{csv_path.stem} {suffix}"
    return f"{prefix} {base}".strip()


def add_reference_line(ax: plt.Axes, y_value: float | None, label: str, color: str = "black") -> None:
    if y_value is None or pd.isna(y_value):
        return
    ax.axhline(y=float(y_value), color=color, linestyle="--", linewidth=1.5, label=label)


def detect_format(csv_path: Path, df: pd.DataFrame) -> str:
    name = csv_path.name.lower()
    columns = set(df.columns)

    if name == "cft_extension_log.csv":
        return "click_fusion_extension"
    if name == "cft_test_log.csv" or {"stim_kind", "gap_ms"}.issubset(columns):
        return "click_fusion"
    if name == "pitch_glide_test_log.csv" or {"trial_type", "D_ms_presented", "n_updates_glide"}.issubset(columns):
        return "pitch_glide"
    if name == "fm_detection_test_log.csv" or {"trial_type", "mi", "rough_trial_no"}.issubset(columns):
        return "fm_detection"
    if name == "two_point_orientation_discrimination_log.csv" or {"orientation_presented", "phase_run", "phase_trial", "size_mm"}.issubset(columns):
        return "two_point_orientation"
    if name == "two_point_discrimination_log.csv" or {"stimulus_presented_code", "two_trial_index", "phase_run", "size_mm"}.issubset(columns):
        return "two_point_discrimination"

    raise ValueError(f"Unsupported CSV format: {csv_path.name}")


def render_click_fusion(csv_path: Path, df: pd.DataFrame, output_dir: Path) -> PlotResult:
    plot_df = df.copy()
    plot_df["stim_kind"] = numeric(plot_df["stim_kind"])
    plot_df = plot_df[plot_df["stim_kind"] == 2].copy()
    if plot_df.empty:
        raise ValueError("No stim_kind == 2 rows found")

    if "two_trial_index" in plot_df.columns and numeric(plot_df["two_trial_index"]).notna().any():
        plot_df["x"] = numeric(plot_df["two_trial_index"])
    else:
        plot_df["x"] = range(1, len(plot_df) + 1)
    plot_df["gap_ms"] = numeric(plot_df["gap_ms"])
    plot_df = plot_df.dropna(subset=["x", "gap_ms"]).sort_values("x")
    if plot_df.empty:
        raise ValueError("No plottable gap data found")

    reversal = boolish(plot_df["reversal"]) if "reversal" in plot_df.columns else pd.Series(False, index=plot_df.index)
    if "small_reversal" in plot_df.columns:
        small_reversal = boolish(plot_df["small_reversal"])
    else:
        step_mode = plot_df["step_mode"].fillna("").astype(str) if "step_mode" in plot_df.columns else ""
        small_reversal = reversal & (step_mode == "small")

    fig, ax = plt.subplots(figsize=(float(os.getenv("FIGURE_WIDTH", "14")), float(os.getenv("FIGURE_HEIGHT", "8"))))
    ax.plot(plot_df["x"], plot_df["gap_ms"], color=BIG_REV_COLOR, marker="o", linewidth=2)

    big_df = plot_df[reversal & ~small_reversal]
    small_df = plot_df[small_reversal]
    if not big_df.empty:
        ax.scatter(big_df["x"], big_df["gap_ms"], color=BIG_REV_COLOR, s=80, marker="o", label="reverse", zorder=3)
    if not small_df.empty:
        ax.scatter(small_df["x"], small_df["gap_ms"], color=SMALL_REV_COLOR, s=90, marker="s", label="small reverse", zorder=3)

    style_axes(ax, title=title_for(csv_path), xlabel="2音 trial 数", ylabel="提示gap (ms)")
    if not big_df.empty or not small_df.empty:
        ax.legend()
    output_path = save_figure(fig, output_dir / f"{csv_path.stem}.png")
    return PlotResult([output_path])


def render_click_fusion_extension(csv_path: Path, df: pd.DataFrame, output_dir: Path) -> PlotResult:
    plot_df = df.copy()
    plot_df["x"] = range(1, len(plot_df) + 1)
    plot_df["gap_ms"] = numeric(plot_df["gap_ms"])
    plot_df["correct"] = boolish(plot_df["correct"]) if "correct" in plot_df.columns else False
    plot_df = plot_df.dropna(subset=["gap_ms"])
    if plot_df.empty:
        raise ValueError("No plottable extension gap data found")

    fig, ax = plt.subplots(figsize=(float(os.getenv("FIGURE_WIDTH", "14")), float(os.getenv("FIGURE_HEIGHT", "8"))))
    ax.plot(plot_df["x"], plot_df["gap_ms"], color=LINE_COLOR, marker="o", linewidth=2, label="gap_ms")

    correct_df = plot_df[plot_df["correct"]]
    incorrect_df = plot_df[~plot_df["correct"]]
    if not correct_df.empty:
        ax.scatter(correct_df["x"], correct_df["gap_ms"], color=BIG_REV_COLOR, s=80, marker="o", label="correct", zorder=3)
    if not incorrect_df.empty:
        ax.scatter(incorrect_df["x"], incorrect_df["gap_ms"], color=SMALL_REV_COLOR, s=80, marker="x", label="incorrect", zorder=3)

    style_axes(ax, title=title_for(csv_path), xlabel="extension trial 数", ylabel="gap (ms)")
    ax.legend()
    output_path = save_figure(fig, output_dir / f"{csv_path.stem}.png")
    return PlotResult([output_path])


def render_pitch_glide(csv_path: Path, df: pd.DataFrame, output_dir: Path) -> PlotResult:
    plot_df = df.copy()
    plot_df = plot_df[plot_df["trial_type"].astype(str) == "glide"].copy()
    if plot_df.empty:
        raise ValueError("No glide rows found")

    if "n_updates_glide" in plot_df.columns and numeric(plot_df["n_updates_glide"]).notna().all():
        plot_df["x"] = numeric(plot_df["n_updates_glide"])
    elif "glide_no_planned" in plot_df.columns and numeric(plot_df["glide_no_planned"]).notna().all():
        plot_df["x"] = numeric(plot_df["glide_no_planned"])
    else:
        plot_df["x"] = range(1, len(plot_df) + 1)
    plot_df["y"] = numeric(plot_df["D_ms_presented"])
    plot_df["reversal"] = boolish(plot_df["reversal"]) if "reversal" in plot_df.columns else False
    plot_df["reversal_level_ms"] = numeric(plot_df["reversal_level_ms"]) if "reversal_level_ms" in plot_df.columns else pd.NA
    plot_df["reversal_phase"] = plot_df["reversal_phase"].fillna(plot_df["phase"]).astype(str) if "reversal_phase" in plot_df.columns else "big"
    plot_df = plot_df.dropna(subset=["x", "y"]).sort_values("x")
    if plot_df.empty:
        raise ValueError("No plottable glide data found")

    fig, ax = plt.subplots(figsize=(float(os.getenv("FIGURE_WIDTH", "14")), float(os.getenv("FIGURE_HEIGHT", "8"))))
    ax.plot(plot_df["x"], plot_df["y"], color=LINE_COLOR, marker="o", linewidth=2, label="D_ms_presented")

    reversal_df = plot_df[plot_df["reversal"] & plot_df["reversal_level_ms"].notna()].copy()
    big_df = reversal_df[reversal_df["reversal_phase"] != "small"]
    small_df = reversal_df[reversal_df["reversal_phase"] == "small"]
    if not big_df.empty:
        ax.scatter(big_df["x"], big_df["reversal_level_ms"], color=BIG_REV_COLOR, s=90, marker="D", label="big-step reversal", zorder=3)
    if not small_df.empty:
        ax.scatter(small_df["x"], small_df["reversal_level_ms"], color=SMALL_REV_COLOR, s=100, marker="D", label="small-step reversal", zorder=3)

    ref_value = None
    if len(small_df) >= 6:
        ref_value = float(small_df["reversal_level_ms"].tail(6).median())
        add_reference_line(ax, ref_value, "official threshold")
    elif "threshold_live_median" in plot_df.columns:
        live_values = numeric(plot_df["threshold_live_median"]).dropna()
        if not live_values.empty:
            ref_value = float(live_values.iloc[-1])
            add_reference_line(ax, ref_value, "reference threshold")

    style_axes(ax, title=title_for(csv_path), xlabel="変化あり（GLIDE）提示数", ylabel="提示 D (ms)")
    ax.legend()
    output_path = save_figure(fig, output_dir / f"{csv_path.stem}.png")
    return PlotResult([output_path])


def render_fm_detection(csv_path: Path, df: pd.DataFrame, output_dir: Path) -> PlotResult:
    plot_df = df.copy()
    plot_df = plot_df[plot_df["trial_type"].astype(str) == "rough"].copy()
    if plot_df.empty:
        raise ValueError("No rough rows found")

    if "rough_trial_no" in plot_df.columns and numeric(plot_df["rough_trial_no"]).notna().any():
        plot_df["x"] = numeric(plot_df["rough_trial_no"])
    else:
        plot_df["x"] = range(1, len(plot_df) + 1)
    plot_df["y"] = numeric(plot_df["mi"])
    plot_df["reversal"] = boolish(plot_df["reversal"]) if "reversal" in plot_df.columns else False
    plot_df["reversal_level"] = numeric(plot_df["reversal_level"]) if "reversal_level" in plot_df.columns else plot_df["y"]
    plot_df["reversal_order"] = numeric(plot_df["reversal_order"]) if "reversal_order" in plot_df.columns else pd.NA
    plot_df["reversal_phase"] = plot_df["reversal_phase"].fillna("").astype(str) if "reversal_phase" in plot_df.columns else ""
    plot_df = plot_df.dropna(subset=["x", "y"]).sort_values("x")
    if plot_df.empty:
        raise ValueError("No plottable rough data found")

    if (plot_df["reversal_phase"] == "").any():
        order = 0
        phases: list[str] = []
        for is_reversal in plot_df["reversal"].tolist():
            if is_reversal:
                order += 1
                phases.append("small" if order > 4 else "big")
            else:
                phases.append("")
        plot_df["reversal_phase"] = phases

    fig, ax = plt.subplots(figsize=(float(os.getenv("FIGURE_WIDTH", "14")), float(os.getenv("FIGURE_HEIGHT", "8"))))
    ax.plot(plot_df["x"], plot_df["y"], color=LINE_COLOR, marker="o", linewidth=2, label="提示MI")

    reversal_df = plot_df[plot_df["reversal"] & plot_df["reversal_level"].notna()].copy()
    big_df = reversal_df[reversal_df["reversal_phase"] != "small"]
    small_df = reversal_df[reversal_df["reversal_phase"] == "small"]
    if not big_df.empty:
        ax.scatter(big_df["x"], big_df["reversal_level"], color=BIG_REV_COLOR, s=90, marker="D", label="big-step reversal", zorder=3)
    if not small_df.empty:
        ax.scatter(small_df["x"], small_df["reversal_level"], color=SMALL_REV_COLOR, s=100, marker="D", label="small-step reversal", zorder=3)

    ref_value = None
    if len(small_df) >= 6:
        ref_value = float(small_df["reversal_level"].tail(6).median())
        add_reference_line(ax, ref_value, "official threshold")
    elif "threshold_live_mi" in plot_df.columns:
        live_values = numeric(plot_df["threshold_live_mi"]).dropna()
        if not live_values.empty:
            ref_value = float(live_values.iloc[-1])
            add_reference_line(ax, ref_value, "reference threshold")

    style_axes(ax, title=title_for(csv_path), xlabel="rough試行数", ylabel="提示MI")
    ax.legend()
    output_path = save_figure(fig, output_dir / f"{csv_path.stem}.png")
    return PlotResult([output_path])


def render_two_point_orientation(csv_path: Path, df: pd.DataFrame, output_dir: Path) -> PlotResult:
    test_df = df[df["phase"].astype(str) == "test"].copy()
    if test_df.empty:
        raise ValueError("No test rows found")

    outputs: list[Path] = []
    for phase_run in sorted(numeric(test_df["phase_run"]).dropna().astype(int).unique().tolist()):
        run_df = test_df[numeric(test_df["phase_run"]) == phase_run].copy()
        run_df["x"] = numeric(run_df["phase_trial"])
        run_df["y"] = numeric(run_df["size_mm"])
        run_df["reversal"] = boolish(run_df["reversal"]) if "reversal" in run_df.columns else False
        run_df["reversal_level_mm"] = numeric(run_df["reversal_level_mm"]) if "reversal_level_mm" in run_df.columns else pd.NA
        run_df["n_reversals"] = numeric(run_df["n_reversals"]) if "n_reversals" in run_df.columns else pd.NA
        run_df = run_df.dropna(subset=["x", "y"]).sort_values("x")
        if run_df.empty:
            continue

        reversal_df = run_df[run_df["reversal"] & run_df["reversal_level_mm"].notna()].copy()
        big_df = reversal_df[reversal_df["n_reversals"] <= 4]
        small_df = reversal_df[reversal_df["n_reversals"] > 4]

        fig, ax = plt.subplots(figsize=(float(os.getenv("FIGURE_WIDTH", "14")), float(os.getenv("FIGURE_HEIGHT", "8"))))
        ax.plot(run_df["x"], run_df["y"], color=LINE_COLOR, linewidth=2.5, label="size_mm")
        if not big_df.empty:
            ax.scatter(big_df["x"], big_df["reversal_level_mm"], color=BIG_REV_COLOR, s=90, marker="s", label="first 4 reversal", zorder=3)
        if not small_df.empty:
            ax.scatter(small_df["x"], small_df["reversal_level_mm"], color=SMALL_REV_COLOR, s=90, marker="s", label="after first 4", zorder=3)

        style_axes(ax, title=title_for(csv_path, f"phase_run_{phase_run}"), xlabel="施行回数", ylabel="dome サイズ (mm)")
        ax.legend()
        outputs.append(save_figure(fig, output_dir / f"{csv_path.stem}_phase_run_{phase_run}.png"))

    if not outputs:
        raise ValueError("No plottable test runs found")
    return PlotResult(outputs)


def render_two_point_discrimination(csv_path: Path, df: pd.DataFrame, output_dir: Path) -> PlotResult:
    test_df = df[df["phase"].astype(str) == "test"].copy()
    if test_df.empty:
        raise ValueError("No test rows found")

    outputs: list[Path] = []
    test_df["stimulus_presented_code"] = numeric(test_df["stimulus_presented_code"])
    test_df = test_df[test_df["stimulus_presented_code"] == 2].copy()
    if test_df.empty:
        raise ValueError("No stimulus_presented_code == 2 rows found")

    for phase_run in sorted(numeric(test_df["phase_run"]).dropna().astype(int).unique().tolist()):
        run_df = test_df[numeric(test_df["phase_run"]) == phase_run].copy()
        run_df["x"] = numeric(run_df["two_trial_index"])
        run_df["y"] = numeric(run_df["size_mm"])
        run_df["reversal"] = boolish(run_df["reversal"]) if "reversal" in run_df.columns else False
        run_df["reversal_level_mm"] = numeric(run_df["reversal_level_mm"]) if "reversal_level_mm" in run_df.columns else pd.NA
        run_df["n_reversals"] = numeric(run_df["n_reversals"]) if "n_reversals" in run_df.columns else pd.NA
        run_df = run_df.dropna(subset=["x", "y"]).sort_values("x")
        if run_df.empty:
            continue

        reversal_df = run_df[run_df["reversal"] & run_df["reversal_level_mm"].notna()].copy()
        big_df = reversal_df[reversal_df["n_reversals"] <= 4]
        small_df = reversal_df[reversal_df["n_reversals"] > 4]

        fig, ax = plt.subplots(figsize=(float(os.getenv("FIGURE_WIDTH", "14")), float(os.getenv("FIGURE_HEIGHT", "8"))))
        ax.plot(run_df["x"], run_df["y"], color=LINE_COLOR, linewidth=2.5, label="size_mm")
        if not big_df.empty:
            ax.scatter(big_df["x"], big_df["reversal_level_mm"], color=BIG_REV_COLOR, s=90, marker="s", label="first 4 reversal", zorder=3)
        if not small_df.empty:
            ax.scatter(small_df["x"], small_df["reversal_level_mm"], color=SMALL_REV_COLOR, s=90, marker="s", label="after first 4", zorder=3)

        style_axes(ax, title=title_for(csv_path, f"phase_run_{phase_run}"), xlabel="2点 trial 数", ylabel="提示 mm")
        ax.legend()
        outputs.append(save_figure(fig, output_dir / f"{csv_path.stem}_phase_run_{phase_run}.png"))

    if not outputs:
        raise ValueError("No plottable test runs found")
    return PlotResult(outputs)


def render_csv(csv_path: Path, output_dir: Path) -> PlotResult:
    df = load_csv(csv_path)
    if df.empty:
        raise ValueError("CSV is empty")

    fmt = detect_format(csv_path, df)
    if fmt == "click_fusion":
        return render_click_fusion(csv_path, df, output_dir)
    if fmt == "click_fusion_extension":
        return render_click_fusion_extension(csv_path, df, output_dir)
    if fmt == "pitch_glide":
        return render_pitch_glide(csv_path, df, output_dir)
    if fmt == "fm_detection":
        return render_fm_detection(csv_path, df, output_dir)
    if fmt == "two_point_orientation":
        return render_two_point_orientation(csv_path, df, output_dir)
    if fmt == "two_point_discrimination":
        return render_two_point_discrimination(csv_path, df, output_dir)
    raise ValueError(f"Unsupported renderer: {fmt}")


def main() -> int:
    input_dir = Path(os.getenv("INPUT_DIR", "/app/input"))
    output_dir = Path(os.getenv("OUTPUT_DIR", "/app/output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(input_dir.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {input_dir}")
        return 0

    failures: list[str] = []
    for csv_file in csv_files:
        try:
            result = render_csv(csv_file, output_dir)
            for output_path in result.output_paths:
                print(f"Generated: {output_path}")
        except Exception as exc:
            failures.append(f"{csv_file.name}: {exc}")

    if failures:
        print("Failed files:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
