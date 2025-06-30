# BirdNet セッション名管理ガイド
## 場所+種名+日付形式でのデータ管理

BirdNetの解析結果を「**場所_種名_日付**」の形式で体系的に管理できます。

## 🏷️ セッション名の形式

### 基本形式
```
場所_種名_日付
```

### 実際の例
```
奥多摩_ヨタカ_2024年6月29日
森林公園_オオタカ_2024年6月30日
多摩川_ミゾゴイ_2024年7月1日
```

## 🚀 使用方法

### 1. **自動生成**（推奨）
ファイル名から自動的に種名を検出し、セッション名を生成：

```bash
# ファイル名から自動推定
python lib\import_results.py model\1

# 出力例: model_ヨタカ_2024年6月29日
```

### 2. **対話形式**（詳細設定）
ステップバイステップでセッション名を設定：

```bash
python lib\import_results.py model\1 --interactive
```

対話例：
```
🏷️  セッション名設定
==================================================
📁 ソースファイル: y2mate.com - 1ヨタカ 鳴き声.BirdNET.results.csv
🔍 検出された種: ヨタカ
📍 推定された場所: model
📅 日付: 2024年6月29日

💡 推奨セッション名: model_ヨタカ_2024年6月29日

選択してください:
1. 推奨名をそのまま使用
2. 場所を手動入力
3. 種名を手動選択
4. 完全にカスタム入力
5. 代替案から選択
```

### 3. **パラメータ指定**
場所と種名を直接指定：

```bash
# 場所と種名を指定
python lib\import_results.py model\1 --location "奥多摩" --species "ヨタカ"

# 複数種の場合
python lib\import_results.py model\1 --location "森林公園" --species "ヨタカ,フクロウ"

# 日付も指定
python lib\import_results.py model\1 --location "多摩川" --species "ミゾゴイ" --date "2024年7月1日"
```

### 4. **完全手動**
セッション名を直接指定：

```bash
python lib\import_results.py model\1 --session "奥多摩_ヨタカ_2024年6月29日"
```

## 🐦 対応鳥種

システムが自動認識できる鳥種：

| 日本語名 | 英語名 | 学名 |
|---------|--------|------|
| ヨタカ | Gray Nightjar | Caprimulgus jotaka |
| オオタカ | Northern Goshawk | Accipiter gentilis |
| フクロウ | Ural Owl | Strix uralensis |
| ミゾゴイ | Japanese Night Heron | Gorsachius goisagi |
| サシバ | Gray-faced Buzzard | Butastur indicus |

## 📍 場所の推定

ファイルパスから場所を自動推定：

| キーワード | 推定される場所 |
|-----------|---------------|
| 森林、forest | 森林 |
| 公園、park | 公園 |
| 山、mountain | 山地 |
| 川、river | 河川 |
| 湖、lake | 湖 |
| 海、sea | 海岸 |
| 田、field | 田園 |

## 💡 実用的な使用例

### 研究・調査での活用

```bash
# 定期調査
python lib\import_results.py data\morning_survey --location "調査地点A" --species "ヨタカ"
python lib\import_results.py data\evening_survey --location "調査地点B" --species "フクロウ"

# 季節調査
python lib\import_results.py spring_data --location "奥多摩" --species "サシバ" --date "2024年春"
python lib\import_results.py summer_data --location "奥多摩" --species "ヨタカ" --date "2024年夏"

# 複数地点比較
python lib\import_results.py site1_data --location "森林公園" --species "オオタカ"
python lib\import_results.py site2_data --location "山地" --species "オオタカ"
python lib\import_results.py site3_data --location "河川敷" --species "オオタカ"
```

## 📊 セッション管理とクエリ

### セッション一覧の確認
```bash
# 解析付きセッション一覧
python lib\import_results.py --list
```

出力例：
```
📋 Database Sessions:
--------------------------------------------------------------------------------
ID: 6
Name: model_ヨタカ_2024年6月29日
  📍 場所: model
  🐦 種名: ヨタカ
  📅 日付: 2024年6月29日
Model: BirdNET (default)
Files: 1, Detections: 296
Created: 2024-06-29 15:30:00
```

### データベースビューアーでの活用
```bash
# 特定セッションの詳細確認
python lib\view_database.py --detections --stats --session-name "奥多摩_ヨタカ_2024年6月29日"

# 場所別の統計
python lib\view_database.py --stats --session-name "森林公園_*"

# 種別の統計
python lib\view_database.py --stats --session-name "*_ヨタカ_*"
```

## 🔧 高度な使用方法

### バッチ処理
複数のディレクトリを一括処理：

```bash
# 各ディレクトリに対して個別のセッション作成
for /d %i in (data\*) do python lib\import_results.py "%i" --interactive

# PowerShellの場合
Get-ChildItem data -Directory | ForEach-Object { python lib\import_results.py $_.FullName --interactive }
```

### 命名規則のカスタマイズ

```bash
# 時間情報付き
python lib\import_results.py model\1 --session "奥多摩_ヨタカ_2024年6月29日_朝5時"

# 調査者情報付き
python lib\import_results.py model\1 --session "奥多摩_ヨタカ_2024年6月29日_田中"

# 気象条件付き
python lib\import_results.py model\1 --session "奥多摩_ヨタカ_2024年6月29日_晴れ"
```

### セッション名の解析
Pythonコードでセッション名を解析：

```python
from lib.session_manager import LocationSpeciesDateManager

manager = LocationSpeciesDateManager()
result = manager.parse_session_name("奥多摩_ヨタカ_2024年6月29日")

print(f"場所: {result['location']}")
print(f"種名: {', '.join(result['species'])}")
print(f"日付: {result['date']}")
```

## 📈 データ分析での活用

### 1. 場所別分析
```bash
# 場所ごとの統計を取得
python lib\view_database.py --export "forest_analysis.csv" --session-name "森林*"
python lib\view_database.py --export "river_analysis.csv" --session-name "*川*"
```

### 2. 種別分析
```bash
# 種ごとの検出パターン分析
python lib\view_database.py --export "yotaka_all.csv" --session-name "*ヨタカ*"
python lib\view_database.py --export "owl_all.csv" --session-name "*フクロウ*"
```

### 3. 時系列分析
```bash
# 時期別の変化を追跡
python lib\view_database.py --export "spring_2024.csv" --session-name "*2024年3月*"
python lib\view_database.py --export "summer_2024.csv" --session-name "*2024年6月*"
```

## ⚠️ 注意事項とベストプラクティス

### セッション名の制約
- 長さ: 3-100文字
- 使用不可文字: `< > : " / \ | ? *`
- 予約語: CON, PRN, AUX, NUL, COM1-9, LPT1-9

### 推奨される命名規則

✅ **良い例**:
```
奥多摩_ヨタカ_2024年6月29日
森林公園_オオタカ_サシバ_2024年春
多摩川下流_ミゾゴイ_2024年7月1日_夜間
```

❌ **避けるべき例**:
```
test123  # 場所・種名・日付が不明
非常に長いセッション名で100文字を超えてしまう場合  # 長すぎる
場所/種名/日付  # 使用不可文字
```

### データ整理のコツ

1. **一貫性**: 同じプロジェクトでは統一した命名規則を使用
2. **階層性**: 場所は大→小の順（例: 東京都_奥多摩_御岳山）
3. **検索性**: 後で検索しやすいキーワードを含める
4. **バックアップ**: 重要なセッションは定期的にCSVエクスポート

## 🛠️ トラブルシューティング

### よくある問題

**Q: セッション名が文字化けする**
A: コマンドプロンプトの文字コードを設定：
```cmd
chcp 65001
```

**Q: 自動推定が正しくない**
A: 対話形式を使用するか、手動で指定：
```bash
python lib\import_results.py model\1 --interactive
```

**Q: 同じセッション名が複数作成される**
A: セッション一覧で確認し、重複を避ける：
```bash
python lib\import_results.py --list
```

**Q: 種名が検出されない**
A: ファイル名に日本語の鳥名を含めるか、手動指定：
```bash
python lib\import_results.py file.csv --species "カスタム種名"
```

## 📚 参考リンク

- [データベースビューアーガイド](database_viewer_guide.md)
- [BirdNet解析ガイド](推論用プログラム使い方.md)
- [カスタムモデル作成](訓練用プログラム使い方.md)

---

**🎯 まとめ**: 場所+種名+日付形式を使用することで、解析結果を体系的に管理し、後の研究や分析で効率的にデータを活用できます。
