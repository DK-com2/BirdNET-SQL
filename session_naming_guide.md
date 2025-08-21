# セッション名ガイド

解析結果をデータベースに保存する際のセッション名の付け方について説明します。

## セッション名とは

セッション名は解析結果をグループ化するための識別子です。同じセッション名で保存された解析結果は、まとめて管理・検索できます。

## 自動生成されるセッション名

### 対話モード
セッション名を空白で入力した場合、以下の形式で自動生成されます：
```
YYYYMMDD_HHMMSS
```

例：`20250821_143022`

### 自動モード
`--session`オプションを指定しない場合、以下の形式で自動生成されます：
```
auto_{model_name}_{YYYYMMDD_HHMMSS}
```

例：
- `auto_default_20250821_143022`
- `auto_custom_model_1_20250821_090015`

## セッション名の推奨例

### 日時ベース
- `morning_20250821` - 朝の解析
- `evening_birds` - 夕方の鳥類
- `weekly_survey_0821` - 週次調査

### 場所ベース
- `garden_recording` - 庭での録音
- `forest_walk` - 森での散歩
- `park_observation` - 公園での観察

### 目的ベース
- `species_identification` - 種の特定
- `migration_study` - 渡り鳥調査
- `daily_monitoring` - 日常監視

## 注意事項

- セッション名に使用できない文字：`\ / : * ? " < > |`
- 日本語文字も使用可能ですが、英数字を推奨
- 同じセッション名を複数回使用すると、結果がマージされます

## コマンドライン例

```bash
# セッション名を指定
python main.py --auto --action analyze --model default --session "morning_birds"

# 自動生成される場合
python main.py --auto --action analyze --model default
# → auto_default_20250821_143022
```