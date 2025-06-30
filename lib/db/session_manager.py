"""
BirdNet セッション名管理ユーティリティ
場所 + 種名 + 日付の形式でセッション名を管理
"""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class LocationSpeciesDateManager:
    """場所 + 種名 + 日付形式のセッション名管理"""
    
    # 対応鳥種のマッピング
    SPECIES_MAP = {
        # 日本語名: [英語名, 学名, キーワード]
        'ヨタカ': ['Gray Nightjar', 'Caprimulgus jotaka', ['yotaka', 'nightjar', 'ヨタカ']],
        'オオタカ': ['Northern Goshawk', 'Accipiter gentilis', ['ootaka', 'goshawk', 'オオタカ']],
        'フクロウ': ['Ural Owl', 'Strix uralensis', ['fukurou', 'owl', 'フクロウ']],
        'ミゾゴイ': ['Japanese Night Heron', 'Gorsachius goisagi', ['mizogoi', 'heron', 'ミゾゴイ']],
        'サシバ': ['Gray-faced Buzzard', 'Butastur indicus', ['sashiba', 'buzzard', 'サシバ']]
    }
    
    @classmethod
    def detect_species_from_filename(cls, filename: str) -> List[str]:
        """ファイル名から鳥種を検出"""
        filename_lower = filename.lower()
        detected_species = []
        
        for species, (en_name, sci_name, keywords) in cls.SPECIES_MAP.items():
            for keyword in keywords:
                if keyword.lower() in filename_lower:
                    detected_species.append(species)
                    break
        
        return list(set(detected_species))  # 重複除去
    
    @classmethod
    def create_session_name(cls, location: str, species: List[str], date: str = None) -> str:
        """場所 + 種名 + 日付形式のセッション名を作成"""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        # 種名を結合（複数種の場合）
        species_str = '_'.join(species) if species else 'unknown'
        
        # セッション名生成
        session_name = f"{location}_{species_str}_{date}"
        
        return session_name
    
    @classmethod
    def parse_session_name(cls, session_name: str) -> Dict[str, str]:
        """セッション名から場所、種名、日付を解析"""
        # パターン: 場所_種名_日付
        pattern = r'^(.+?)_(.+?)_(.+)$'
        match = re.match(pattern, session_name)
        
        if match:
            location = match.group(1)
            species = match.group(2).split('_')
            date = match.group(3)
            
            return {
                'location': location,
                'species': species,
                'date': date,
                'valid': True
            }
        else:
            return {
                'location': '',
                'species': [],
                'date': '',
                'valid': False
            }
    
    @classmethod
    def suggest_session_name(cls, source_path: str, location: str = None) -> Dict[str, any]:
        """ファイルパスから推奨セッション名を提案"""
        path = Path(source_path)
        
        # ファイル名から種名を検出
        detected_species = cls.detect_species_from_filename(path.name)
        
        # 場所の推定（指定がない場合）
        if location is None:
            # ディレクトリ名やファイル名から場所を推測
            location = cls._guess_location_from_path(path)
        
        # 日付は現在日時（英語形式）
        date = datetime.now().strftime('%Y%m%d')
        
        # セッション名生成
        if detected_species:
            suggested_name = cls.create_session_name(location, detected_species, date)
        else:
            suggested_name = f"{location}_audio_analysis_{date}"
        
        return {
            'suggested_name': suggested_name,
            'location': location,
            'species': detected_species,
            'date': date,
            'alternatives': cls._generate_alternatives(location, detected_species, date)
        }
    
    @classmethod
    def _guess_location_from_path(cls, path: Path) -> str:
        """パスから場所を推測"""
        # よくある場所のキーワード
        location_keywords = {
            '森林': '森林',
            'forest': '森林',
            '公園': '公園',
            'park': '公園',
            '山': '山地',
            'mountain': '山地',
            '川': '河川',
            'river': '河川',
            '湖': '湖',
            'lake': '湖',
            '海': '海岸',
            'sea': '海岸',
            '田': '田園',
            'field': '田園'
        }
        
        full_path = str(path).lower()
        
        for keyword, location in location_keywords.items():
            if keyword in full_path:
                return location
        
        # 推測できない場合はディレクトリ名を使用
        if path.parent.name and path.parent.name != '.':
            return path.parent.name
        
        return '調査地点'
    
    @classmethod
    def _generate_alternatives(cls, location: str, species: List[str], date: str) -> List[str]:
        """代替案を生成"""
        alternatives = []
        
        # 短縮版
        short_date = datetime.now().strftime('%m%d')
        species_str = '_'.join(species) if species else '鳥類'
        alternatives.append(f"{location}_{species_str}_{short_date}")
        
        # 詳細版
        detail_date = datetime.now().strftime('%Y年%m月%d日_%H時')
        alternatives.append(f"{location}_{species_str}_{detail_date}")
        
        # 英語版
        if species:
            en_species = []
            for sp in species:
                if sp in cls.SPECIES_MAP:
                    en_species.append(cls.SPECIES_MAP[sp][0].replace(' ', ''))
            if en_species:
                alternatives.append(f"{location}_{'_'.join(en_species)}_{datetime.now().strftime('%Y%m%d')}")
        
        return alternatives

def interactive_session_naming(source_path: str) -> str:
    """対話式でセッション名を決定"""
    manager = LocationSpeciesDateManager()
    
    print("\n🏷️  セッション名設定")
    print("=" * 50)
    
    # 自動推定の結果を表示
    suggestion = manager.suggest_session_name(source_path)
    
    print(f"📁 ソースファイル: {Path(source_path).name}")
    print(f"🔍 検出された種: {', '.join(suggestion['species']) if suggestion['species'] else '未検出'}")
    print(f"📍 推定された場所: {suggestion['location']}")
    print(f"📅 日付: {suggestion['date']}")
    print()
    print(f"💡 推奨セッション名: {suggestion['suggested_name']}")
    print()
    
    # 選択肢を表示
    print("選択してください:")
    print("1. 推奨名をそのまま使用")
    print("2. 場所を手動入力")
    print("3. 種名を手動選択")
    print("4. 完全にカスタム入力")
    print("5. 代替案から選択")
    
    choice = input("\n選択 (1-5): ").strip()
    
    if choice == "1":
        return suggestion['suggested_name']
    
    elif choice == "2":
        location = input("場所を入力してください: ").strip()
        if not location:
            location = suggestion['location']
        return manager.create_session_name(location, suggestion['species'])
    
    elif choice == "3":
        print("\n利用可能な種名:")
        for i, species in enumerate(manager.SPECIES_MAP.keys(), 1):
            print(f"  {i}. {species}")
        print(f"  {len(manager.SPECIES_MAP) + 1}. その他")
        
        species_choice = input("種名を選択してください (番号または名前): ").strip()
        
        if species_choice.isdigit():
            idx = int(species_choice) - 1
            species_list = list(manager.SPECIES_MAP.keys())
            if 0 <= idx < len(species_list):
                selected_species = [species_list[idx]]
            elif idx == len(species_list):
                custom_species = input("種名を入力してください: ").strip()
                selected_species = [custom_species] if custom_species else suggestion['species']
            else:
                selected_species = suggestion['species']
        else:
            selected_species = [species_choice] if species_choice else suggestion['species']
        
        return manager.create_session_name(suggestion['location'], selected_species)
    
    elif choice == "4":
        location = input("場所を入力してください: ").strip()
        species_input = input("種名を入力してください (複数の場合はカンマ区切り): ").strip()
        date_input = input("日付を入力してください (空白で今日): ").strip()
        
        species = [s.strip() for s in species_input.split(',')] if species_input else ['調査対象']
        date = date_input if date_input else datetime.now().strftime('%Y年%m月%d日')
        
        return manager.create_session_name(location, species, date)
    
    elif choice == "5":
        print("\n代替案:")
        alternatives = suggestion['alternatives']
        for i, alt in enumerate(alternatives, 1):
            print(f"  {i}. {alt}")
        
        alt_choice = input("選択してください (1-3): ").strip()
        if alt_choice.isdigit() and 1 <= int(alt_choice) <= len(alternatives):
            return alternatives[int(alt_choice) - 1]
        else:
            return suggestion['suggested_name']
    
    else:
        return suggestion['suggested_name']

# 使用例とテスト
def demo_naming():
    """命名システムのデモ"""
    manager = LocationSpeciesDateManager()
    
    test_files = [
        "y2mate.com - 1ヨタカ 鳴き声.BirdNET.results.csv",
        "森林公園_オオタカ_録音.csv",
        "data/audio/フクロウ夜間調査.wav"
    ]
    
    print("=== 場所+種名+日付 セッション名管理デモ ===")
    
    for file_path in test_files:
        print(f"\n📁 ファイル: {file_path}")
        
        # 自動推定
        suggestion = manager.suggest_session_name(file_path)
        print(f"   推奨名: {suggestion['suggested_name']}")
        print(f"   場所: {suggestion['location']}")
        print(f"   種名: {', '.join(suggestion['species'])}")
        print(f"   代替案: {', '.join(suggestion['alternatives'][:2])}")
        
        # 手動作成例
        manual_name = manager.create_session_name("奥多摩", ["ヨタカ"], "2024年6月29日")
        print(f"   手動例: {manual_name}")
        
        # 解析テスト
        parsed = manager.parse_session_name(manual_name)
        print(f"   解析結果: {parsed}")

if __name__ == "__main__":
    demo_naming()
