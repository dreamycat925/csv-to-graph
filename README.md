# CSV to Graph

心理検査ログの CSV を `input/` に入れ、`docker compose up -d` で `output/` に折れ線 PNG を生成する構成です。

既存アプリの CSV 仕様を参照し、以下の 5 系統に合わせて自動判定します。

- `cft_test_log.csv` / `cft_extension_log.csv`
- `pitch_glide_test_log.csv`
- `fm_detection_test_log.csv`
- `two_point_orientation_discrimination_log.csv`
- `two_point_discrimination_log.csv`

## 使い方

1. CSV を `input/` に置く
2. 次を実行する

```bash
docker compose up -d --build
```

生成結果は `output/` に保存されます。

設定を変えたい場合だけ `.env.example` を `.env` にコピーして使います。`.env` がなくても起動できます。

## ディレクトリ

- `input/`: 元の CSV
- `output/`: 生成された PNG

## デフォルト動作

- `input/` 配下の `*.csv` を順番に処理
- CSV名と列構成から検査種別を自動判定
- 各検査アプリの進捗グラフ仕様に寄せて描画
- 文字コードは `utf-8-sig`, `utf-8`, `cp932` を順に試行
- 出力先は `output/`

## 出力されるグラフ

- `click-fusion-test`
  - `stim_kind == 2` のみを対象
  - 横軸: `two_trial_index`
  - 縦軸: `gap_ms`
  - marker: `reversal`, `small_reversal`
- `pitch-glide-direction-threshold`
  - `trial_type == glide` のみを対象
  - 横軸: `n_updates_glide`
  - 縦軸: `D_ms_presented`
  - marker: big-step / small-step reversal
  - 可能なら threshold 参照線も描画
- `frequency-modulation-auditory-test`
  - `trial_type == rough` のみを対象
  - 横軸: `rough_trial_no`
  - 縦軸: `mi`
  - marker: big-step / small-step reversal
  - 可能なら threshold 参照線も描画
- `two-point-orientation-discrimination`
  - `phase == test` を対象
  - `phase_run` ごとに別PNG
  - 横軸: `phase_trial`
  - 縦軸: `size_mm`
  - marker: reversal 前半4回 / 後半
- `2pd`
  - `phase == test` かつ `stimulus_presented_code == 2` を対象
  - `phase_run` ごとに別PNG
  - 横軸: `two_trial_index`
  - 縦軸: `size_mm`
  - marker: reversal 前半4回 / 後半

## `.env` で変更できる項目

```env
INPUT_DIR=/app/input
OUTPUT_DIR=/app/output
FIGURE_WIDTH=14
FIGURE_HEIGHT=8
CHART_TITLE_PREFIX=
```

- `CHART_TITLE_PREFIX`: グラフタイトル先頭に付ける文字列

## 想定 CSV

- 1 行が 1 回の記録
- 例: `timestamp, patient_id, score`
- 横軸列は日時または連番を想定
- 縦軸列は数値である必要があります

未対応の CSV はエラーとして一覧表示します。必要なら対象アプリを追加できます。
