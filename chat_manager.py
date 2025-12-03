"""
🟡 ChatManager (処理の振り分けを行うコントローラー)GUI ⇄ DB ⇄ LangChain をつなぐ
    【役割】
    - 各チャットの会話履歴を管理
    - DBとGUIの橋渡し
    - データの加工(DB形式 ↔ session_state形式)
    - チャットの作成・削除・更新
    - タイトルの自動生成
    【重要】Streamlitは再実行されるたびにインスタンスが作り直されるため、
    session_stateから値を復元して「正」のデータを保持する

【更新履歴】
- RAGManagerを追加（オプショナル）
- Firebase Firestore対応 🆕
"""
import streamlit as st
import shortuuid
from typing import List, Dict, Any, Optional


class ChatManager:
    """
    チャット管理のコントローラークラス
    
    【このクラスが持つデータ】
    - self.db_manager: DBManagerのインスタンス(Firestore操作用)
    - self.langchain_manager: LangChainManagerのインスタンス(AI連携用)
    - self.rag_manager: RAGManagerのインスタンス(RAG操作用)
    - self.chat_list: チャット一覧 [{"id": "xxx", "title": "xxx"}, ...]
    - self.all_chat_histories: 全チャットの会話履歴
        {"chat_id": [{"role": "user", "content": "..."}, ...]}
    
    【Streamlitの特性】
    Streamlitは画面が更新されるたび、Pythonコードが最初から実行される
    つまり、普通の変数は毎回リセットされる
    → session_stateに保存することで、データを保持できる
    → ChatManagerは起動時にsession_stateから復元する
    
    【Firebase対応】🆕
    - 初回起動時: Firestoreからデータを取得
    - メッセージ追加時: Firestoreに保存
    - session_stateはキャッシュとして使用（Firestoreが「正」のデータ）
    """
    def __init__(self, db_manager, langchain_manager, rag_manager=None):
        """
        クラスの初期化
        
        【処理の流れ】
        1. db_manager, langchain_manager, rag_managerを受け取って保存
        2. session_stateから既存データを復元
        (なければFirestoreから取得)
        
        Args:
            db_manager: DBManagerのインスタンス（Firestore版）
            langchain_manager: LangChainManagerのインスタンス
            rag_manager: RAGManagerのインスタンス（オプション）
        
        【呼び出し例】(main.pyで実行)
        db_manager = DBManager()
        langchain_manager = LangChainManager()
        rag_manager = RAGManager()
        chat_manager = ChatManager(db_manager, langchain_manager, rag_manager)
        """
        # 引数をインスタンス変数に保存
        self.db_manager = db_manager
        self.langchain_manager = langchain_manager
        self.rag_manager = rag_manager
        
        # session_stateから復元(Streamlit再実行対策)
        # この関数で self.chat_list と self.all_chat_histories が設定される
        self._restore_from_session_state()
    
    def _restore_from_session_state(self):
        """
        session_stateから値を復元、なければFirestoreから取得
        
        【処理の流れ】
        1. session_stateに"chat_list"があるかチェック
        2. あれば: 既存データを復元（キャッシュとして使用）
        3. なければ: Firestoreからデータを取得
        
        【Firebase対応】🆕
        - 初回起動: Firestoreから全データを取得
        - 2回目以降: session_stateから復元（高速化のため）
        """
        # session_stateに"chat_list"がある = 既にデータが存在
        if "chat_list" in st.session_state:
            # 既存データがあれば復元（キャッシュ）
            self.chat_list = st.session_state.chat_list
            self.all_chat_histories = st.session_state.get("all_chat_histories", {})
        else:
            # 🆕 Firestoreからデータを取得
            self.chat_list = self._load_chat_list_from_db()
            self.all_chat_histories = self._load_all_histories_from_db()
            
            # session_stateに保存(キャッシュ)
            st.session_state.chat_list = self.chat_list
            st.session_state.all_chat_histories = self.all_chat_histories
    
    def _load_chat_list_from_db(self) -> List[Dict[str, str]]:
        """
        🆕 Firestoreからチャット一覧を取得
        
        Returns:
            チャット一覧 [{"id": "xxx", "title": "xxx"}, ...]
        """
        return self.db_manager.get_all_chats()
    
    def _load_all_histories_from_db(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        🆕 Firestoreから全チャットの会話履歴を取得
        
        Returns:
            全チャットの会話履歴
            {"chat_id": [{"role": "user", "content": "..."}, ...], ...}
        """
        histories = {}
        for chat in self.chat_list:
            chat_id = chat["id"]
            histories[chat_id] = self.db_manager.get_chat_history(chat_id)
        return histories
    
    def get_chat_list(self) -> List[Dict[str, str]]:
        """
        チャット一覧を取得

        【戻り値】
        [{"id": "xxx", "title": "xxx"}, ...]
        
        【呼び出し例】(gui.pyから)
        chat_list = chat_manager.get_chat_list()
        """
        return self.chat_list
    
    def get_current_chat_id(self, chat_list: List[Dict[str, str]]) -> str:
        """
        デフォルトで選択するチャットIDを返す
        chat_listの最初の要素のIDを返す
        
        【処理内容】
        - chat_listが空でなければ、最初のチャットのIDを返す
        - 空なら新しいIDを生成
        
        Args:
            chat_list: チャット一覧
        
        Returns:
            チャットID(文字列)
        
        【呼び出し例】(gui.pyから)
        default_id = chat_manager.get_current_chat_id(chat_list)
        """
        if chat_list:
            return chat_list[0]["id"]
        else:
            # チャットリストが空の場合は新規作成
            return shortuuid.uuid()
    
    def get_chat_title_by_id(self, chat_id: str) -> str:
        """
        チャットIDからタイトルを取得
        
        【処理内容】
        - chat_listをループして、指定されたIDのタイトルを探す
        - 見つからなければ"不明なチャット"を返す
        
        Args:
            chat_id: チャットID
        
        Returns:
            チャットタイトル(文字列)
        
        【呼び出し例】(gui.pyから)
        title = chat_manager.get_chat_title_by_id("abc123")
        """
        for chat in self.chat_list:
            # chatは {"id": "xxx", "title": "xxx"} という辞書
            if chat["id"] == chat_id:
                # IDが一致したらタイトルを返す
                return chat["title"]
            
        # ループを抜けた = 見つからなかった
        return "不明なチャット"
    
    def get_chat_histories(self, chat_id: str) -> List[Dict[str, Any]]:
        """
        指定したチャットIDの会話履歴を取得
        
        【処理内容】
        - all_chat_historiesからchat_idに対応する履歴を取得
        - なければ空リストを返す
        
        Args:
            chat_id: チャットID
        
        Returns:
            会話履歴のリスト
            [{"role": "user", "content": "...", "is_rag": False}, ...]
        
        【呼び出し例】(gui.pyから)
        histories = chat_manager.get_chat_histories("abc123")
        """
        return self.all_chat_histories.get(chat_id, [])
    
    def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        is_rag: bool = False,
        chunks: List[Dict[str, Any]] = None
    ):
        """
        チャットにメッセージを追加
        ChatManager、session_state、Firestoreの全てを更新

        【処理内容】
        1. メッセージ辞書を作成
        2. ChatManager側のデータ(self.all_chat_histories)を更新
        3. session_stateにも同期
        4. 🆕 Firestoreにも保存

        Args:
            chat_id: チャットID
            role: "user" または "assistant"
            content: メッセージ内容
            is_rag: RAGモードかどうか（assistantメッセージのみ有効）🆕
            chunks: RAG使用時の参照チャンク情報 🆕
                    [{"chunk_id": "xxx", "similarity_score": 0.89, "source": "file.pdf"}, ...]

        【呼び出し例】(gui.pyから)
        # ユーザーメッセージ
        chat_manager.add_message("abc123", "user", "こんにちは")

        # RAGモードのメッセージ
        chat_manager.add_message(
            "abc123",
            "assistant",
            "NSC業務フローによると...",
            is_rag=True,
            chunks=[{"chunk_id": "xxx", "similarity_score": 0.89, "source": "業務フロー.pdf"}]
        )
        """
        # メッセージ辞書を作成
        message = {
            "role": role,
            "content": content
        }

        # assistantメッセージの場合のみis_ragとchunksを追加
        if role == "assistant":
            message["is_rag"] = is_rag
            # RAGモードの場合はチャンク情報を追加
            if is_rag and chunks:
                message["chunks"] = chunks

        # ChatManager側のデータを更新
        # chat_idがall_chat_historiesに存在しない場合、空リストを作成
        if chat_id not in self.all_chat_histories:
            self.all_chat_histories[chat_id] = []

        # リストにメッセージを追加
        self.all_chat_histories[chat_id].append(message)

        # session_stateにも同期(これがないとStreamlit再実行時にデータが消える)
        st.session_state.all_chat_histories = self.all_chat_histories

        # 🆕 Firestoreにも保存
        self.db_manager.save_message(
            chat_id=chat_id,
            role=role,
            content=content,
            is_rag=is_rag if role == "assistant" else None,
            chunks=chunks
        )
    
    def create_new_chat_with_title(self, title: str) -> Dict[str, str]:
        """
        新しいチャットを作成してIDとタイトルを返す

        【処理内容】
        1. 🆕 Firestoreに新しいチャットを作成
        2. chat_listに追加
        3. all_chat_historiesに空リストを作成
        4. session_stateに同期
        
        Args:
            title: チャットのタイトル
        
        Returns:
            作成されたチャット情報 {"id": "xxx", "title": "xxx"}
        
        【呼び出し例】
        new_chat = chat_manager.create_new_chat_with_title("新しいチャット")
        """
        # 🆕 Firestoreに作成（自動IDを取得）
        new_id = self.db_manager.create_chat(title=title)
        
        if new_id is None:
            # 作成失敗時はローカルIDを生成
            new_id = shortuuid.uuid()
        
        new_chat = {"id": new_id, "title": title}
        
        # ChatManager側のデータを更新
        # リストの先頭に追加（新しいチャットが一番上に来るように）
        self.chat_list.insert(0, new_chat)
        self.all_chat_histories[new_id] = []
        
        # session_stateにも同期
        st.session_state.chat_list = self.chat_list
        st.session_state.all_chat_histories = self.all_chat_histories
        
        return new_chat
    
    def format_chat_histories(self, chat_histories: List[Dict[str, str]]) -> List[Any]:
        """
        会話履歴をLangChainに渡す用に整形
        
        【処理内容】
        1. 通常の辞書形式の履歴をループ
        2. roleに応じてHumanMessageまたはAIMessageに変換
        3. 変換したオブジェクトをリストに追加
        
        【変換前(通常形式)】
        [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "やあ!"}
        ]
        
        【変換後(LangChain形式)】
        [
            HumanMessage(content="こんにちは"),
            AIMessage(content="やあ!")
        ]
        
        Args:
            chat_histories: 通常形式の会話履歴
        
        Returns:
            LangChain形式のメッセージリスト
        
        【呼び出し例】(gui.pyから)
        normal_histories = [{"role": "user", "content": "こんにちは"}]
        lc_messages = chat_manager.format_chat_histories(normal_histories)
        """
        lc_chat_list = []
        for chat in chat_histories:
            if chat["role"] == "user":
                # langchain_managerを使ってHumanMessageを作成
                content = self.langchain_manager.create_human_message(chat["content"])
                lc_chat_list.append(content)
            elif chat["role"] == "assistant":
                # langchain_managerを使ってAIMessageを作成
                content = self.langchain_manager.create_ai_message(chat["content"])
                lc_chat_list.append(content)
        # 変換されたリストを返す
        return lc_chat_list
    
    def update_chat_title(self, chat_id: str, new_title: str):
        """
        チャットのタイトルを更新
        
        【処理内容】
        1. chat_listをループして該当するチャットを探す
        2. 見つかったらタイトルを更新
        3. session_stateに同期
        4. 🆕 Firestoreにも保存
        
        Args:
            chat_id: チャットID
            new_title: 新しいタイトル
        
        【呼び出し例】
        chat_manager.update_chat_title("abc123", "新しいタイトル")
        """
        for chat in self.chat_list:
            if chat["id"] == chat_id:
                chat["title"] = new_title
                break
        
        # session_stateにも同期
        st.session_state.chat_list = self.chat_list
        
        # 🆕 Firestoreにも保存
        self.db_manager.update_chat_title(chat_id, new_title)
    
    def should_generate_title(self, chat_id: str) -> bool:
        """
        タイトルを自動生成すべきかどうかを判定
        
        【判定条件】
        1. タイトルが「新規チャット」で始まる
        2. メッセージが2件以上ある(ユーザー1回 + AI1回 = 会話が成立)
        
        Args:
            chat_id: チャットID
        
        Returns:
            True: タイトル生成すべき / False: 不要
        """
        # 現在のタイトルを取得
        current_title = self.get_chat_title_by_id(chat_id)
        
        # 「新規チャット」で始まるかチェック
        if not current_title.startswith("新規チャット"):
            return False
        
        # メッセージ数をチェック
        histories = self.get_chat_histories(chat_id)
        # AI応答完了後 = 2件以上(ユーザー + AI)
        if len(histories) >= 2:
            return True
        
        return False
    
    def generate_chat_title(self, chat_id: str) -> str:
        """
        会話内容からタイトルを自動生成
        
        【処理の流れ】
        1. 会話履歴を取得
        2. LangChainManagerにタイトル生成を依頼
        3. 生成されたタイトルを返す
        
        Args:
            chat_id: チャットID
        
        Returns:
            生成されたタイトル(12文字以内)
        """
        # 会話履歴を取得
        histories = self.get_chat_histories(chat_id)
        
        # 最初の2件のメッセージを取得(タイトル生成に使用)
        recent_messages = histories[:2]
        
        # LangChain形式に変換
        formatted_messages = self.format_chat_histories(recent_messages)
        
        # LangChainManagerにタイトル生成を依頼
        title = self.langchain_manager.generate_title(formatted_messages)
        
        return title
    
    def delete_chat(self, chat_id: str):
        """
        チャットを削除

        【処理内容】
        1. chat_listから該当するチャットを除外
        2. all_chat_historiesから該当する履歴を削除
        3. session_stateに同期
        4. 🆕 Firestoreからも削除
        
        Args:
            chat_id: チャットID
        
        【リスト内包表記の説明】
        [chat for chat in self.chat_list if chat["id"] != chat_id]
        = chat_listの各chatについて、IDがchat_idでないものだけを残す
        
        【呼び出し例】
        chat_manager.delete_chat("abc123")
        """
        # リスト内包表記で、指定ID以外のチャットを残す
        # ChatManager側のデータを削除
        self.chat_list = [chat for chat in self.chat_list if chat["id"] != chat_id]
        # 辞書から該当するキーを削除
        if chat_id in self.all_chat_histories:
            del self.all_chat_histories[chat_id]
        
        # session_stateにも同期
        st.session_state.chat_list = self.chat_list
        st.session_state.all_chat_histories = self.all_chat_histories
        
        # 🆕 Firestoreからも削除
        self.db_manager.delete_chat(chat_id)
    
    # RAG関連メソッド
    def get_rag_manager(self):
        """
        RAGManagerを取得
        
        Returns:
            RAGManagerのインスタンス（なければNone）
        """
        return self.rag_manager
    
    def is_rag_enabled(self) -> bool:
        """
        RAGが有効かどうかを確認
        
        Returns:
            RAGが有効ならTrue
        """
        if self.rag_manager is None:
            return False
        
        status = self.rag_manager.get_status()
        return status["collection_info"]["chunk_count"] > 0
    
    def refresh_from_db(self):
        """
        🆕 Firestoreから最新データを再取得
        キャッシュをクリアしてDBから読み直す
        
        【使用場面】
        - データの同期が必要な時
        - 別のセッションで更新があった時
        """
        # Firestoreから再取得
        self.chat_list = self._load_chat_list_from_db()
        self.all_chat_histories = self._load_all_histories_from_db()
        
        # session_stateを更新
        st.session_state.chat_list = self.chat_list
        st.session_state.all_chat_histories = self.all_chat_histories
        
        print("✅ Firestoreから最新データを取得しました")