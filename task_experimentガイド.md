# task experiment 完全ガイド

## 概要

`task experiment` は、鳥の鳴き声識別システムにおける**完全自動化された機械学習パイプライン**である。このコマンド一つで、音声データの前処理からカスタムモデルの作成、評価まで全てを自動実行する。

## 実行方法

```bash
task experiment
```

## 処理フロー

### 1. 実験設定の読み込み
`./lib/experiments.json` から実験パラメータを読み込む。

**現在の設定例**:
```json
{
  "data": [
    {
      "id": 1,
      "normalization": "False",
      "denoise": "False", 
      "fmax": 15000,
      "fmin": 0
    }
  ]
}
```

### 2. 各実験設定に対する4ステップ処理

実験設定ごとに以下の4ステップを順次自動実行する：

#### ステップ1: 音声抽出 (`extract_audio`)
**処理内容**:
- 長時間録音ファイル（`data/audio/raw/`）から短時間セグメントを抽出
- `train.xlsx`のラベル情報に基づいて時間範囲を切り出し
- 前処理オプション（正規化・ノイズ除去）を適用
- 周波数フィルタリング（fmin-fmax）

**入力**:
```
data/audio/raw/
├── Northern_Goshawk/オオタカ録音1.mp3    # 長時間録音
└── ...
data/train.xlsx                           # ラベル情報
```

**出力**:
```
data/audio/extracted/
├── Northern_Goshawk/録音1_1m30s.mp3     # 短時間セグメント
└── ...
data/audio/extracted_spectrogram/
├── 録音1_1m30s.png                      # スペクトログラム
└── ...
```

#### ステップ2: モデル訓練 (`train_integrated_model`)
**処理内容**:
- 抽出した音声セグメントを使用してBirdNETベースのカスタムモデルを訓練
- TensorFlow Liteモデルとして出力

**実行コマンド例**:
```bash
python lib/birdnet/train.py \
  --i data/audio/train \
  --o model/1/models \
  --crop_mode segments \
  --crop_overlap 2 \
  --epochs 3 \
  --fmin 0 \
  --fmax 15000
```

**出力**:
```
model/1/
└── models.tflite                        # 訓練済みカスタムモデル
```

#### ステップ3: テスト解析 (`analyze_with_integrated_model`)
**処理内容**:
- 作成したカスタムモデルでテスト音声を解析
- 各音声ファイルの鳥種予測と信頼度を出力

**実行コマンド例**:
```bash
python lib/birdnet/analyze.py \
  --i data/audio/test \
  --o model/1 \
  --overlap 2 \
  --rtype csv \
  --classifier model/1/models.tflite \
  --fmax 15000 \
  --fmin 0 \
  --sensitivity 1.5 \
  --min_conf 0.1
```

**入力**:
```
data/audio/test/
├── オオタカテスト1.mp3                   # テスト音声
├── サシバテスト1.mp3
└── ...
```

**出力**:
```
model/1/
├── オオタカテスト1.BirdNET.results.csv   # 予測結果
├── サシバテスト1.BirdNET.results.csv
└── ...
```

#### ステップ4: 評価 (`evaluate_results`)
**処理内容**:
- 予測結果と正解ラベル（`train.xlsx`）を時系列で比較
- F1スコア、精度、再現率を計算

**時系列評価の詳細**:

1. **データ変換**:
```python
# 60分音声を1秒ごとに区切って評価
total_time = pd.DataFrame(data={"start_time": np.arange(0, 3600)})

# 正解ラベル: 1m30s〜1m35s = オオタカ → 90〜95秒で true_label=1
# 予測結果: BirdNETの信頼度 → 各秒での Confidence値
```

2. **比較例**:
```csv
start_time,true_label,Confidence,判定結果
90,1,0.82,正解（閾値0.1超過で検出、実際にオオタカ）
91,1,0.85,正解
95,0,0.15,偽陽性（検出したが実際は鳴き声なし）
150,1,0.05,偽陰性（見逃し）
```

3. **評価指標計算**:
```python
# 閾値0.1で二値化後、混同行列を作成
Precision = TP / (TP + FP)  # 「オオタカ」予測の正確性
Recall = TP / (TP + FN)     # 実際のオオタカ検出率  
F1_Score = 2 * (Precision * Recall) / (Precision + Recall)
```

**実行コマンド例**:
```bash
python lib/f1score.py --name=1
```

**出力**:
```
model/1/
└── results.csv                          # 評価結果（F1、精度、再現率）
```

**results.csv の内容例**:
```csv
file_name,species,F1_score,Precision,Recall
オオタカテスト1,オオタカ,0.844,0.785,0.914
サシバテスト1,サシバ,0.892,0.901,0.883
ミゾゴイテスト1,ミゾゴイ,0.756,0.778,0.734
```

## 複数実験の自動実行と結果保持

`experiments.json`に複数の設定を記載すると、全ての組み合わせで自動実験が実行される。

**例: 4つの前処理パターンで実験**:
```json
{
  "data": [
    {"id": 1, "normalization": "False", "denoise": "False", "fmax": 15000, "fmin": 0},
    {"id": 2, "normalization": "True",  "denoise": "False", "fmax": 15000, "fmin": 0},
    {"id": 3, "normalization": "True",  "denoise": "True",  "fmax": 15000, "fmin": 0},
    {"id": 4, "normalization": "False", "denoise": "True",  "fmax": 15000, "fmin": 0}
  ]
}
```

**重要**: **すべてのモデルが保持され、自動選択はされない**

**結果**: 
```
model/
├── 1/
│   ├── models.tflite                    # 前処理なしモデル
│   └── results.csv                      # F1=0.75, Precision=0.80, Recall=0.70
├── 2/
│   ├── models.tflite                    # 正規化のみモデル
│   └── results.csv                      # F1=0.82, Precision=0.85, Recall=0.79
├── 3/
│   ├── models.tflite                    # 正規化+ノイズ除去モデル
│   └── results.csv                      # F1=0.88, Precision=0.90, Recall=0.86
└── 4/
    ├── models.tflite                    # ノイズ除去のみモデル
    └── results.csv                      # F1=0.71, Precision=0.68, Recall=0.74
```

**最良モデルの選択**: 研究者が各 `results.csv` を比較して手動で判断
- 例: F1スコアが最も高い `model/3/` を選択

## 事前準備（必須）

### 1. データ構造
```
data/
├── audio/
│   ├── raw/                             # 元音声ファイル
│   │   ├── Northern_Goshawk/
│   │   ├── Gray-faced_Buzzard/
│   │   ├── Japanese_Night_Heron/
│   │   ├── Ural_Owl/
│   │   └── Gray_Nightjar/
│   └── test/                            # テスト音声
└── train.xlsx                          # ラベルデータ
```

### 2. train.xlsx の必須列
- `path`: 音声ファイル名（完全一致必須）
- `start_time`: 開始時間（例：1m30s）
- `end_time`: 終了時間（例：1m35s）
- `species1`: 鳥種の日本語名

### 3. 実行時間の目安
- 音声抽出: 数分〜数十分（データ量による）
- モデル訓練: 数時間（epochs=3、データ量による）
- テスト解析: 数分
- 評価: 数秒

**合計**: 数時間〜半日程度

## 最終出力（結果出力）

実験完了後、以下の構造でファイルが生成される：

```
model/
└── 1/                                   # 実験ID
    ├── models.tflite                    # 訓練済みカスタムモデル（実用可能なAIモデル）
    ├── オオタカテスト1.BirdNET.results.csv # 各テストファイルの時系列予測結果
    ├── サシバテスト1.BirdNET.results.csv
    ├── ...
    └── results.csv                      # 総合評価結果（F1、精度、再現率）
```

### 1. 訓練済みモデル (`models.tflite`)
**用途**: 実際の鳥の鳴き声識別に使用するAIモデル本体
- スマートフォンアプリや組み込みシステムで動作可能
- このファイルがあれば新しい音声ファイルの鳥種を予測可能

### 2. 時系列予測結果 (`{テストファイル名}.BirdNET.results.csv`)
**内容例**:
```csv
Start (s),End (s),Scientific name,Common name,Confidence
0.0,3.0,Accipiter gentilis,Northern Goshawk,0.85
3.0,6.0,Accipiter gentilis,Northern Goshawk,0.92
6.0,9.0,,background,0.12
9.0,12.0,Accipiter gentilis,Northern Goshawk,0.78
```
**意味**: 3秒ごとに区切った各時間帯での予測結果と確信度

### 3. 総合評価結果 (`results.csv`)
**内容例**:
```csv
file_name,species,F1_score,Precision,Recall
オオタカテスト1,オオタカ,0.844,0.785,0.914
オオタカテスト2,オオタカ,0.821,0.798,0.845
サシバテスト1,サシバ,0.892,0.901,0.883
ミゾゴイテスト1,ミゾゴイ,0.756,0.778,0.734
```

**各指標の意味**:
- **F1スコア**: 総合的な性能指標（0-1、高いほど良い）
- **Precision（精度）**: 「オオタカ」と予測した中で実際にオオタカだった割合
- **Recall（再現率）**: 実際のオオタカの鳴き声のうち正しく検出できた割合

### 4. 時系列評価の意義
**従来の評価**: 「この音声ファイルはオオタカか？」（ファイル単位）
**時系列評価**: 「60分の録音の中で、オオタカが鳴いた数秒間を正確に検出できるか？」（秒単位）

これにより、実際のフィールドワークでの使用を想定した現実的な性能評価が可能になる。

### 5. 実用的な使い方
```bash
# 1. 複数モデルの性能比較
cat model/*/results.csv | grep "F1_score"

# 2. 最良モデル（例：model/3/）で新しい音声を解析
python lib/birdnet/analyze.py \
  --i 新しい音声.mp3 \
  --classifier model/3/models.tflite
```

## まとめ

`task experiment` は、**データ準備さえ完了していれば**、コマンド一つで以下を全自動実行する：

1. **音声前処理**: 長時間録音 → 短時間訓練データ
2. **AI訓練**: カスタム鳥種識別モデル作成
3. **性能評価**: テストデータでの精度測定
4. **結果出力**: 使用可能なモデルと評価レポート

これにより、研究者は様々なパラメータ組み合わせを効率的に実験し、最適なモデルを見つけることができる。