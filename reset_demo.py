"""
🔄 デモ用チャットリセットスクリプト

毎日1回実行して、Firestoreをテンプレート会話のみにリセットする

【使い方】
手動実行: python reset_demo.py
自動実行: cron で毎日深夜に実行

【処理内容】
1. Firestoreの全チャットを削除
2. テンプレート会話2つを新規作成
   - RAGモードの例
   - 通常モードの例（マークダウン表付き）
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

# プロジェクトのパスを追加（cronから実行する場合に必要）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chat.db_manager import DBManager


# ============================================
# テンプレート会話の定義
# ============================================

TEMPLATE_CHATS = [
    {
        "title": "審査の流れについて",
        "messages": [
            {
                "role": "user",
                "content": "審査の流れを教えて",
                "is_rag": False,
                "chunks": []
            },
            {
                "role": "assistant",
                "content": """NSC業務フローに基づき、審査の流れは以下の通りです。

1. **初期受付**: 申込データに必ず「NSCコード」を記録します。これにより案件のトラッキングが可能になります。

2. **書類受領・確認**: 書類のチェックを行い、不備がある場合は「NSC-NG理由コード表」に基づき、具体的な不備内容をシステムに記録します。

3. **信用情報照会**: CIC・JICC・全銀協の3機関すべてを必ず照会し、「NSC審査シート」に記録します。

4. **審査判定**: 「NSC審査基準マトリックス」に従い、グレーゾーン案件は必ずスーパーバイザー（SV）にエスカレーションします。

5. **契約内容確定**: 「NSC承認レベル表」に基づき、金額に応じた承認者の電子承認を取得します。

6. **最終決裁依頼**: 「NSC決裁申請フォーマット」を使用し、チェックリスト全項目を確認済みにします。

詳しい手続きや注意点については、各ステップにおけるローカルルールに従って進めてください。""",
                "is_rag": True,
                "chunks": [
                    {
                        "chunk_id": "acom_workflow_rag.pdf_4_3",
                        "similarity_score": 1.0134,
                        "source": "acom_workflow_rag.pdf"
                    },
                    {
                        "chunk_id": "acom_workflow_rag.pdf_2_1",
                        "similarity_score": 1.1445,
                        "source": "acom_workflow_rag.pdf"
                    },
                    {
                        "chunk_id": "acom_workflow_rag.pdf_5_4",
                        "similarity_score": 1.1711,
                        "source": "acom_workflow_rag.pdf"
                    }
                ]
            }
        ]
    },
    {
        "title": "犬の種類一覧",
        "messages": [
            {
                "role": "user",
                "content": "犬の種類を一覧で見せて！",
                "is_rag": False,
                "chunks": []
            },
            {
                "role": "assistant",
                "content": """人気の犬種を一覧でご紹介します！🐕

## 小型犬

| 犬種 | 特徴 | 体重目安 |
|------|------|----------|
| トイプードル | 賢くて抜け毛が少ない | 3-4kg |
| チワワ | 世界最小の犬種 | 1-3kg |
| ポメラニアン | ふわふわの毛並み | 2-3kg |
| ミニチュアダックス | 胴長短足が可愛い | 4-5kg |

## 中型犬

| 犬種 | 特徴 | 体重目安 |
|------|------|----------|
| 柴犬 | 日本を代表する犬種 | 8-10kg |
| コーギー | 短い足と大きな耳 | 10-12kg |
| ビーグル | 優れた嗅覚を持つ | 9-11kg |

## 大型犬

| 犬種 | 特徴 | 体重目安 |
|------|------|----------|
| ゴールデンレトリバー | 優しく従順 | 25-35kg |
| ラブラドールレトリバー | 盲導犬としても活躍 | 25-35kg |
| シベリアンハスキー | 青い目が美しい | 20-30kg |

気になる犬種はありますか？🐶""",
                "is_rag": False,
                "chunks": []
            }
        ]
    }
]


def reset_to_demo():
    """
    Firestoreをリセットしてデモ用テンプレートのみにする
    """
    print("=" * 50)
    print("🔄 デモ用チャットリセット開始")
    print(f"   実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # DBManager初期化
    db_manager = DBManager()
    
    # ============================================
    # Step 1: 全チャットを削除
    # ============================================
    print("\n📋 Step 1: 既存チャットを削除中...")
    
    all_chats = db_manager.get_all_chats()
    delete_count = 0
    
    for chat in all_chats:
        success = db_manager.delete_chat(chat["id"])
        if success:
            delete_count += 1
            print(f"   ✅ 削除: {chat['title']}")
        else:
            print(f"   ❌ 削除失敗: {chat['title']}")
    
    print(f"\n   合計 {delete_count} 件のチャットを削除しました")
    
    # ============================================
    # Step 2: テンプレート会話を作成
    # ============================================
    print("\n📝 Step 2: テンプレート会話を作成中...")
    
    for template in TEMPLATE_CHATS:
        # チャットを作成
        chat_id = db_manager.create_chat(title=template["title"])
        
        if chat_id:
            # メッセージを保存
            db_manager.save_chat_history(chat_id, template["messages"])
            print(f"   ✅ 作成: {template['title']}")
        else:
            print(f"   ❌ 作成失敗: {template['title']}")
    
    # ============================================
    # 完了
    # ============================================
    print("\n" + "=" * 50)
    print("✅ デモ用チャットリセット完了！")
    print("=" * 50)
    
    # 最終確認
    final_chats = db_manager.get_all_chats()
    print(f"\n📊 現在のチャット数: {len(final_chats)} 件")
    for chat in final_chats:
        print(f"   - {chat['title']}")
    
    print("\n✨ Streamlitを起動してください: streamlit run main.py")


if __name__ == "__main__":
    reset_to_demo()