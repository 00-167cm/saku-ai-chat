"""
🟣 DB管理（Firebase Firestore版）
    Firestoreとの接続処理(登録・更新・取得)
    chat_managerから登録更新用のデータを受け取る
    取得した値をchat_managerに渡す

【Firestoreのデータ構造】
chats (コレクション)
 └── {chat_id} (ドキュメント)
      ├── title: string
      ├── created_at: timestamp
      ├── updated_at: timestamp
      └── messages: array
           └── [
                 {
                   role: "user" or "assistant",
                   content: "メッセージ内容",
                   is_rag: boolean,
                   created_at: timestamp,
                   chunks: [{chunk_id, similarity_score, source}, ...]  # is_rag=trueの時のみ
                 },
                 ...
               ]
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import ArrayUnion


class DBManager:
    """
    Firebase Firestore管理クラス
    チャットデータの永続化を担当
    """
    
    def __init__(self, credential_path: str = "firebase-key.json"):
        """
        Firestore接続の初期化

        Args:
            credential_path: サービスアカウントキーのパス
        """
        self.credential_path = credential_path
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """
        Firebaseの初期化
        既に初期化済みの場合はスキップ
        """
        try:
            # 既に初期化されているかチェック
            firebase_admin.get_app()
            print("✅ Firebase既に初期化済み")
        except ValueError:
            # 初期化されていない場合は初期化
            cred = credentials.Certificate(self.credential_path)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase初期化完了")
        
        # Firestoreクライアント取得
        self.db = firestore.client()
        self.chats_ref = self.db.collection('chats')
    
    # ============================================
    # チャット操作
    # ============================================
    
    def get_all_chats(self) -> List[Dict[str, str]]:
        """
        すべてのチャット一覧を取得
        
        Returns:
            チャット一覧 [{"id": "xxx", "title": "xxx"}, ...]
            updated_atの降順（新しい順）
        """
        try:
            docs = self.chats_ref.order_by(
                'updated_at', 
                direction=firestore.Query.DESCENDING
            ).get()
            
            chats = []
            for doc in docs:
                data = doc.to_dict()
                chats.append({
                    "id": doc.id,
                    "title": data.get("title", "無題のチャット")
                })
            
            return chats
            
        except Exception as e:
            print(f"❌ チャット一覧取得エラー: {e}")
            return []
    
    def get_chat_by_id(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        指定されたIDのチャット情報を取得
        
        Args:
            chat_id: チャットID
        
        Returns:
            チャット情報 {"id": "xxx", "title": "xxx", "created_at": "xxx"}
            存在しない場合はNone
        """
        try:
            doc = self.chats_ref.document(chat_id).get()
            
            if doc.exists:
                data = doc.to_dict()
                return {
                    "id": doc.id,
                    "title": data.get("title", "無題のチャット"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at")
                }
            return None
            
        except Exception as e:
            print(f"❌ チャット取得エラー: {e}")
            return None
    
    def create_chat(self, chat_id: str = None, title: str = "新しいチャット") -> Optional[str]:
        """
        新しいチャットを作成
        
        Args:
            chat_id: チャットID（Noneの場合は自動生成）
            title: チャットタイトル
        
        Returns:
            作成されたチャットID、失敗した場合はNone
        """
        try:
            now = datetime.now()
            
            chat_data = {
                "title": title,
                "created_at": now,
                "updated_at": now,
                "messages": []
            }
            
            if chat_id:
                # 指定されたIDで作成
                self.chats_ref.document(chat_id).set(chat_data)
                return chat_id
            else:
                # 自動ID生成
                doc_ref = self.chats_ref.add(chat_data)
                return doc_ref[1].id
                
        except Exception as e:
            print(f"❌ チャット作成エラー: {e}")
            return None
    
    def update_chat_title(self, chat_id: str, new_title: str) -> bool:
        """
        チャットのタイトルを更新
        
        Args:
            chat_id: チャットID
            new_title: 新しいタイトル
        
        Returns:
            成功した場合True
        """
        try:
            self.chats_ref.document(chat_id).update({
                "title": new_title,
                "updated_at": datetime.now()
            })
            return True
            
        except Exception as e:
            print(f"❌ タイトル更新エラー: {e}")
            return False
    
    def delete_chat(self, chat_id: str) -> bool:
        """
        チャットを削除
        
        Args:
            chat_id: チャットID
        
        Returns:
            成功した場合True
        """
        try:
            self.chats_ref.document(chat_id).delete()
            return True
            
        except Exception as e:
            print(f"❌ チャット削除エラー: {e}")
            return False
    
    # ============================================
    # メッセージ操作
    # ============================================
    
    def get_chat_history(self, chat_id: str) -> List[Dict[str, Any]]:
        """
        指定されたチャットの会話履歴を取得
        
        Args:
            chat_id: チャットID
        
        Returns:
            会話履歴 [{"role": "user", "content": "xxx", "is_rag": False}, ...]
        """
        try:
            doc = self.chats_ref.document(chat_id).get()
            
            if doc.exists:
                data = doc.to_dict()
                return data.get("messages", [])
            return []
            
        except Exception as e:
            print(f"❌ 履歴取得エラー: {e}")
            return []
    
    def save_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        is_rag: bool = None,
        chunks: List[Dict[str, Any]] = None
    ) -> bool:
        """
        メッセージを保存

        Args:
            chat_id: チャットID
            role: メッセージの役割("user" or "assistant")
            content: メッセージ内容
            is_rag: RAGモードかどうか（assistantメッセージのみ、Noneの場合は保存しない）
            chunks: RAG使用時の参照チャンク情報
                    [{"chunk_id": "xxx", "similarity_score": 0.89, "source": "file.pdf"}, ...]

        Returns:
            成功した場合True
        """
        try:
            message = {
                "role": role,
                "content": content,
                "created_at": datetime.now()
            }

            # assistantメッセージの場合のみis_ragを追加
            if is_rag is not None:
                message["is_rag"] = is_rag

                # RAGモードの場合はチャンク情報を追加
                if is_rag and chunks:
                    message["chunks"] = chunks

            # 配列に追加 & updated_atを更新
            self.chats_ref.document(chat_id).update({
                "messages": ArrayUnion([message]),
                "updated_at": datetime.now()
            })

            return True

        except Exception as e:
            print(f"❌ メッセージ保存エラー: {e}")
            return False
    
    def save_chat_history(
        self,
        chat_id: str,
        messages: List[Dict[str, Any]]
    ) -> bool:
        """
        チャット履歴を一括保存（上書き）
        
        Args:
            chat_id: チャットID
            messages: メッセージリスト
        
        Returns:
            成功した場合True
        """
        try:
            self.chats_ref.document(chat_id).update({
                "messages": messages,
                "updated_at": datetime.now()
            })
            return True
            
        except Exception as e:
            print(f"❌ 履歴保存エラー: {e}")
            return False
    
    def clear_chat_history(self, chat_id: str) -> bool:
        """
        指定されたチャットの会話履歴をクリア
        
        Args:
            chat_id: チャットID
        
        Returns:
            成功した場合True
        """
        try:
            self.chats_ref.document(chat_id).update({
                "messages": [],
                "updated_at": datetime.now()
            })
            return True
            
        except Exception as e:
            print(f"❌ 履歴クリアエラー: {e}")
            return False
    
    # ============================================
    # 検索・統計
    # ============================================
    
    def search_chats(self, keyword: str) -> List[Dict[str, str]]:
        """
        チャットをキーワード検索（タイトルのみ）
        
        Args:
            keyword: 検索キーワード
        
        Returns:
            マッチしたチャット一覧
        
        【注意】
        Firestoreは部分一致検索が苦手なので、
        全件取得してPython側でフィルタリング
        """
        try:
            all_chats = self.get_all_chats()
            
            matched = [
                chat for chat in all_chats
                if keyword.lower() in chat["title"].lower()
            ]
            
            return matched
            
        except Exception as e:
            print(f"❌ 検索エラー: {e}")
            return []
    
    def get_chat_count(self) -> int:
        """
        チャットの総数を取得
        
        Returns:
            チャット数
        """
        try:
            docs = self.chats_ref.get()
            return len(docs)
            
        except Exception as e:
            print(f"❌ カウントエラー: {e}")
            return 0
    
    # ============================================
    # エクスポート・インポート
    # ============================================
    
    def export_chat_to_json(self, chat_id: str) -> Optional[str]:
        """
        チャットをJSON形式でエクスポート
        
        Args:
            chat_id: チャットID
        
        Returns:
            JSON文字列、失敗した場合はNone
        """
        try:
            doc = self.chats_ref.document(chat_id).get()
            
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            
            # datetimeをISO形式に変換
            export_data = {
                "chat_info": {
                    "id": doc.id,
                    "title": data.get("title"),
                    "created_at": data.get("created_at").isoformat() if data.get("created_at") else None,
                    "updated_at": data.get("updated_at").isoformat() if data.get("updated_at") else None
                },
                "messages": []
            }
            
            for msg in data.get("messages", []):
                msg_copy = msg.copy()
                if "created_at" in msg_copy and hasattr(msg_copy["created_at"], "isoformat"):
                    msg_copy["created_at"] = msg_copy["created_at"].isoformat()
                export_data["messages"].append(msg_copy)
            
            return json.dumps(export_data, ensure_ascii=False, indent=2)
            
        except Exception as e:
            print(f"❌ エクスポートエラー: {e}")
            return None
    
    def import_chat_from_json(self, json_str: str) -> Optional[str]:
        """
        JSON形式からチャットをインポート
        
        Args:
            json_str: JSON文字列
        
        Returns:
            インポートされたチャットID、失敗した場合はNone
        """
        try:
            data = json.loads(json_str)
            chat_info = data.get("chat_info", {})
            messages = data.get("messages", [])
            
            title = chat_info.get("title", "インポートされたチャット")
            
            # 新しいチャットを作成
            chat_id = self.create_chat(title=title)
            
            if chat_id:
                # メッセージを保存
                self.save_chat_history(chat_id, messages)
                return chat_id
            
            return None
            
        except json.JSONDecodeError as e:
            print(f"❌ JSONパースエラー: {e}")
            return None
        except Exception as e:
            print(f"❌ インポートエラー: {e}")
            return None