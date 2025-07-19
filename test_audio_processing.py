#!/usr/bin/env python3
"""
フェーズ2音声セグメント処理テストスクリプト
開発・テスト用の実行スクリプト
"""

import sys
import os
import logging
from pathlib import Path

# UTF-8エンコーディングでコンソール出力を設定
if sys.platform == "win32":
    # Windowsでのコンソール出力をUTF-8に設定
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lib.audio_processing import ProcessingManager

# カスタムログフォーマッター（絵文字を安全に処理）
class SafeFormatter(logging.Formatter):
    def format(self, record):
        try:
            return super().format(record)
        except UnicodeEncodeError:
            # 絵文字を代替文字に置換
            record.msg = str(record.msg).replace('🎵', '[MUSIC]').replace('✅', '[OK]').replace('❌', '[ERROR]')
            return super().format(record)

# ロガー設定
def setup_logging():
    """安全なロガー設定"""
    # ストリームハンドラー（コンソール出力）
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(SafeFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # ファイルハンドラー（UTF-8エンコーディング）
    file_handler = logging.FileHandler('audio_processing.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # ルートロガー設定
    logging.basicConfig(
        level=logging.INFO,
        handlers=[stream_handler, file_handler]
    )

setup_logging()
logger = logging.getLogger(__name__)

def test_single_detection():
    """単一検出結果のテスト処理"""
    logger.info("=== 単一検出結果テスト ===")
    
    # ProcessingManager初期化
    manager = ProcessingManager(enable_spectrogram=True)
    
    # データベース内の最初の未処理レコードを取得してテスト
    pending = manager._get_pending_detections()
    
    if not pending:
        logger.info("未処理レコードがありません")
        return
    
    # 最初のレコードでテスト
    test_detection = pending[0]
    logger.info(f"テスト対象: ID {test_detection['id']}, 種名: {test_detection.get('common_name', 'Unknown')}")
    
    # 処理実行
    success, message = manager.process_single_detection(test_detection['id'])
    
    if success:
        logger.info(f"[OK] テスト成功: {message}")
    else:
        logger.error(f"[ERROR] テスト失敗: {message}")
    
    # 統計表示
    stats = manager.get_processing_statistics()
    logger.info(f"処理統計: {stats}")

def test_batch_processing(limit: int = 5):
    """バッチ処理テスト"""
    logger.info(f"=== バッチ処理テスト (最大{limit}件) ===")
    
    # ProcessingManager初期化
    manager = ProcessingManager(enable_spectrogram=True)
    
    # 未処理レコード確認
    pending = manager._get_pending_detections()
    
    if not pending:
        logger.info("未処理レコードがありません")
        return
    
    # 制限数まで処理
    test_count = min(limit, len(pending))
    logger.info(f"テスト処理対象: {test_count}件")
    
    # 各レコードを処理
    manager.reset_processing_stats()
    for i, detection in enumerate(pending[:test_count]):
        logger.info(f"処理中 ({i+1}/{test_count}): ID {detection['id']}")
        success, message = manager._process_single_detection(detection)
        
        if success:
            logger.info(f"  [OK] 成功: {message}")
        else:
            logger.warning(f"  [ERROR] 失敗: {message}")
    
    # 最終統計
    stats = manager.get_processing_statistics()
    logger.info("=== バッチ処理結果 ===")
    logger.info(f"処理件数: {stats['processed_count']}")
    logger.info(f"成功件数: {stats['success_count']}")
    logger.info(f"音声生成成功: {stats['audio_success']}")
    logger.info(f"スペクトログラム生成成功: {stats['spectrogram_success']}")
    logger.info(f"エラー件数: {stats['error_count']}")
    
    if stats['errors']:
        logger.info("エラー詳細:")
        for error in stats['errors'][:5]:  # 最初の5件のみ表示
            logger.info(f"  - {error}")

def show_processing_status():
    """処理状況の表示"""
    logger.info("=== 現在の処理状況 ===")
    
    manager = ProcessingManager()
    stats = manager.get_processing_statistics()
    
    logger.info(f"総検出数: {stats.get('total_detections', 0)}")
    logger.info(f"音声処理済み: {stats.get('processed_audio', 0)} ({stats.get('audio_progress_percent', 0):.1f}%)")
    logger.info(f"スペクトログラム処理済み: {stats.get('processed_spectrogram', 0)} ({stats.get('spectrogram_progress_percent', 0):.1f}%)")
    logger.info(f"未処理: {stats.get('pending_audio', 0)}")
    logger.info(f"ストレージ使用量: {stats.get('total_mb', 0):.1f} MB")

def validate_generated_files():
    """生成されたファイルの検証"""
    logger.info("=== 生成ファイル検証 ===")
    
    manager = ProcessingManager()
    issues = manager.validate_generated_files()
    
    total_issues = sum(len(issue_list) for issue_list in issues.values())
    
    if total_issues == 0:
        logger.info("[OK] 生成されたファイルに問題はありません")
    else:
        logger.warning(f"[WARNING] {total_issues}件の問題が見つかりました")
        
        for issue_type, issue_list in issues.items():
            if issue_list:
                logger.warning(f"{issue_type}: {len(issue_list)}件")
                for issue in issue_list[:3]:  # 最初の3件のみ表示
                    logger.warning(f"  - {issue}")

def main():
    """メイン関数"""
    print("[MUSIC] BirdNET音声セグメント処理テストスクリプト")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python test_audio_processing.py status     - 処理状況表示")
        print("  python test_audio_processing.py single     - 単一レコードテスト")
        print("  python test_audio_processing.py batch [N]  - バッチ処理テスト（N件、デフォルト5件）")
        print("  python test_audio_processing.py validate   - 生成ファイル検証")
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == "status":
            show_processing_status()
        
        elif command == "single":
            test_single_detection()
        
        elif command == "batch":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            test_batch_processing(limit)
        
        elif command == "validate":
            validate_generated_files()
        
        else:
            logger.error(f"不明なコマンド: {command}")
            
    except Exception as e:
        logger.error(f"実行エラー: {e}")
        raise

if __name__ == "__main__":
    main()
