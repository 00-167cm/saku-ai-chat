"""
🟢 GUI管理
    画面に表示することからsession_stateの管理(情報の追加更新)
    session_state:画面表示に関する情報を持ち回っている

【重要】ChatManagerを「正」のデータソースとして扱う
- 初期化: ChatManager → session_state
- 更新: GUI → ChatManager → session_state

【役割】
- Streamlitを使った画面表示
- ユーザー入力の受付
- ChatManagerへのデータ要求
- AI応答の表示
- タイトルの自動生成
- RAGモード/通常モードの自動判定

【更新履歴】
- RAGManagerを追加
- RAGモードでの応答生成を追加
- 🆕 Firebase Firestore対応
"""
import streamlit as st
from typing import Dict, List, Any
import os
from dotenv import load_dotenv

# 環境変数を読み込む
load_dotenv()

class GUI:
    """
    GUI管理クラス
    
    【このクラスが持つデータ】
    - self.chat_manager: ChatManagerのインスタンス
    - self.langchain_manager: LangChainManagerのインスタンス
    - self.rag_manager: RAGManagerのインスタンス
    
    【データの流れ】
    ChatManager(正のデータ) → session_state → 画面表示
    ユーザー入力 → GUI → ChatManager → session_state → Firestore
    """
    def __init__(self, chat_manager, langchain_manager, rag_manager=None):
        """
        クラスの初期化
        
        【処理の流れ】
        1. chat_manager, langchain_manager, rag_managerを受け取って保存
        2. session_stateを初期化
        
        Args:
            chat_manager: ChatManagerのインスタンス
            langchain_manager: LangChainManagerのインスタンス
            rag_manager: RAGManagerのインスタンス（オプション）
        
        【呼び出し例】(main.pyで実行)
        chat_manager = ChatManager(db_manager, langchain_manager)
        gui = GUI(chat_manager, langchain_manager, rag_manager)
        """
        # 引数をインスタンス変数に保存
        self.chat_manager = chat_manager
        self.langchain_manager = langchain_manager
        self.rag_manager = rag_manager

        # session_stateを初期化
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """
        session_stateの初期化
        ChatManagerから取得した値を設定

        session_state.current_chat に現在のチャット情報が設定された

        【処理の流れ】
        1. current_chatを初期化(現在選択中のチャット情報)
        2. chat_listを初期化(ChatManagerから取得)
        3. all_chat_historiesを初期化
        4. current_chat.idを初期化(デフォルトで選択するチャット)
        5. current_chat.titleを初期化
        
        【session_stateの構造】
        st.session_state = {
            "current_chat": {
                "id": "abc123",
                "title": "チャットタイトル"
            },
            "chat_list": [{"id": "...", "title": "..."}, ...],
            "all_chat_histories": {"chat_id": [...], ...}
        }
        """
        # current_chatの初期化
        if "current_chat" not in st.session_state:
            st.session_state.current_chat = {}
        
        # chat_listの初期化 (ChatManagerから取得)
        if "chat_list" not in st.session_state:
            st.session_state.chat_list = self.chat_manager.get_chat_list()
        
        # all_chat_historiesの初期化
        if "all_chat_histories" not in st.session_state:
            st.session_state.all_chat_histories = {}
        
        # current_chat.idの初期化
        if "id" not in st.session_state.current_chat:
            st.session_state.current_chat["id"] = self.chat_manager.get_current_chat_id(
                st.session_state.chat_list
            )
        
        # current_chat.titleの初期化(デフォルトで選択するチャット)
        if "title" not in st.session_state.current_chat:
            current_id = st.session_state.current_chat["id"]
            st.session_state.current_chat["title"] = self.chat_manager.get_chat_title_by_id(current_id)
    
    def _update_current_chat(self, new_id: str):
        """
        選択中のチャットIDを更新
        ChatManagerから最新データを取得

        【処理内容】
        1. session_stateのcurrent_chat.idを更新
        2. ChatManagerから新しいIDのタイトルを取得
        3. session_stateのcurrent_chat.titleを更新
        
        Args:
            new_id: 新しいチャットID
        
        【呼び出し例】(サイドバーのボタンが押された時)
        self._update_current_chat("def456")
        """
        st.session_state.current_chat["id"] = new_id
        st.session_state.current_chat["title"] = self.chat_manager.get_chat_title_by_id(new_id)
        
        # チャット切り替え時は最新の履歴をChatManagerから取得
        # (session_stateに保存されているものと同じだが、明示的に取得)
    
    def _add_user_message(self, user_input: str):
        """
        ユーザーメッセージを追加
        ChatManager経由で追加してsession_stateとFirestoreに同期

        【処理内容】
        ChatManagerのadd_message()を呼び出す
        (内部でsession_stateとFirestoreも更新される)

        Args:
            user_input: ユーザーの入力テキスト

        【呼び出し例】(ユーザーがメッセージを送信した時)
        self._add_user_message("こんにちは")
        """
        # ChatManagerに追加 (内部でsession_stateとFirestoreも更新される)
        self.chat_manager.add_message(
            st.session_state.current_chat["id"],
            "user",
            user_input
        )
    
    def _add_ai_message(
        self, 
        ai_response: str, 
        is_rag: bool = False,
        chunks: List[Dict[str, Any]] = None
    ):
        """
        AIメッセージを追加
        ChatManager経由で追加してsession_stateとFirestoreに同期

        【処理内容】
        ChatManagerのadd_message()を呼び出す
        (内部でsession_stateとFirestoreも更新される)

        Args:
            ai_response: AIの応答テキスト
            is_rag: RAGモードかどうか 🆕
            chunks: RAG使用時の参照チャンク情報 🆕
                    [{"chunk_id": "xxx", "similarity_score": 0.89, "source": "file.pdf"}, ...]

        【呼び出し例】(AIの応答を受け取った後)
        # 通常メッセージ
        self._add_ai_message("やあ!元気?")
        
        # RAGモードのメッセージ
        self._add_ai_message(
            "NSC業務フローによると...",
            is_rag=True,
            chunks=[{"chunk_id": "xxx", "similarity_score": 0.89, "source": "業務フロー.pdf"}]
        )
        """
        # ChatManagerに追加 (内部でsession_stateとFirestoreも更新される)
        self.chat_manager.add_message(
            st.session_state.current_chat["id"],
            "assistant",
            ai_response,
            is_rag=is_rag,
            chunks=chunks
        )
    
    def _auto_generate_title_if_needed(self) -> bool:
        """
        必要に応じてタイトルを自動生成
        
        【処理の流れ】
        1. ChatManagerに「タイトル生成すべきか」を確認
        2. 必要なら生成して更新
        3. session_stateのcurrent_chat.titleも更新
        
        【呼び出しタイミング】
        AI応答完了後
        
        Returns:
            bool: タイトルが生成された場合True、されなかった場合False
        """
        current_id = st.session_state.current_chat["id"]
        
        # タイトル生成が必要かチェック
        if self.chat_manager.should_generate_title(current_id):
            try:
                # タイトルを生成
                new_title = self.chat_manager.generate_chat_title(current_id)
                
                # ChatManagerのタイトルを更新（Firestoreにも保存される）
                self.chat_manager.update_chat_title(current_id, new_title)
                
                # session_stateのcurrent_chat.titleも更新
                st.session_state.current_chat["title"] = new_title
                
                # タイトルが生成されたことを返す
                return True
                
            except Exception as e:
                # エラーが発生してもアプリを止めない
                print(f"タイトル生成エラー: {e}")
                return False
        
        # タイトル生成が不要だった場合
        return False
    
    def _render_title(self):
        """
        タイトルを表示

        【Streamlitの表示関数】
        - st.title(): 大きなタイトル
        - st.header(): 見出し
        - st.subheader(): 小見出し
        - st.markdown(): マークダウン形式のテキスト
        """
        st.title("🐥さくらのAIチャットボット")
    
    def _render_sidebar(self):
        """
        サイドバーを表示

        ・サイドバーに3つのボタンが表示された
        "AIチャットボットの設計"
        "LangChain"
        "StreamlitでUI構築"
        
        【処理内容】
        1. サイドバーにタイトルを表示
        2. 新規チャット作成ボタンを追加
        3. ChatManagerから最新のチャット一覧を取得
        4. 各チャットをボタンとして表示
        5. ボタンが押されたらIDを更新して画面を再描画
        
        【Streamlitのサイドバー】
        st.sidebar.xxx() で左側のサイドバーに表示される
        
        【st.rerun()とは】
        Streamlitのコードを最初から再実行する
        これにより画面が更新される"""
        st.sidebar.title("💬 チャット履歴")
        
        # 新規チャット作成ボタン
        # use_container_width=True で横幅いっぱいに表示
        if st.sidebar.button("➕ 新規チャット", key="new_chat_button", use_container_width=True):
            # 新規チャットを作成
            self._create_new_chat()
            # 画面を再描画
            st.rerun()
        
        # 区切り線を追加(見やすくするため)
        st.sidebar.divider()
        
        # ChatManagerから最新のチャット一覧を取得
        chat_list = self.chat_manager.get_chat_list()
        
        # チャット一覧のボタンを表示
        for chat in chat_list:
            if st.sidebar.button(f"{chat['title']}", key=f"link_{chat['id']}"):
                # ボタンが押されたらIDを更新
                self._update_current_chat(chat["id"])
                st.rerun()  # 画面を再描画
        
        if self.rag_manager:
            st.sidebar.divider()
            st.sidebar.subheader("📚 RAG設定")
            
            status = self.rag_manager.get_status()
            collection_info = status['collection_info']
            
            st.sidebar.info(f"""
**ファイル数**: {collection_info.get('file_count', 0)}個
            """)
            
            if "previous_threshold" not in st.session_state:
                st.session_state.previous_threshold = status['threshold']
            
            current_threshold = status['threshold']
            new_threshold = st.sidebar.slider(
                "閾値",
                min_value=0.0,
                max_value=3.0,
                value=current_threshold,
                step=0.1,
                help="値が小さいほど厳密にマッチします。通常は1.0〜2.0が推奨です。"
            )
            
            if new_threshold != st.session_state.previous_threshold:
                self.rag_manager.threshold = new_threshold
                st.session_state.previous_threshold = new_threshold
                st.toast(f"✅ 閾値を {new_threshold} に更新しました", icon="✅")
            
            with st.sidebar.expander("📄 格納されているファイル"):
                source_list = self.rag_manager.chroma_manager.get_source_list()
                if source_list:
                    # 📁 Googleドライブフォルダへのリンクを環境変数から取得
                    drive_folder_url = os.getenv("GOOGLE_DRIVE_FOLDER_URL", "")
                    if drive_folder_url:
                        st.markdown(
                            f"📁 [**資料格納先に移動**]({drive_folder_url})",
                            unsafe_allow_html=True
                        )
                        st.divider()

                    # ファイル一覧を表示（クリック不可）
                    for i, source in enumerate(source_list, 1):
                        st.markdown(f"{i}. {source}")
                else:
                    st.text("ファイルが登録されていません")

    
    def _create_new_chat(self):
        """
        新規チャットを作成
        
        【処理内容】
        1. チャット番号を計算(既存チャット数 + 1)
        2. 仮タイトルを生成(例:"新規チャット 4")
        3. ChatManagerで新規チャット作成（Firestoreにも保存）
        4. 作成したチャットを現在のチャットに設定
        
        【補足】
        - 作成したチャットは空の状態(会話履歴なし)
        - ChatManagerがsession_stateとFirestoreに同期してくれる
        """
        # 現在のチャット数を取得
        chat_list = self.chat_manager.get_chat_list()
        chat_count = len(chat_list)
        
        # 仮タイトルを生成
        # 例: チャットが3つある → "新規チャット 4"
        new_title = f"新規チャット {chat_count + 1}"
        
        # ChatManagerで新規チャット作成（Firestoreにも保存される）
        # create_new_chat_with_title() は {"id": "xxx", "title": "xxx"} を返す
        new_chat = self.chat_manager.create_new_chat_with_title(new_title)
        
        # 作成したチャットを現在のチャットに設定
        self._update_current_chat(new_chat["id"])
    
    def _render_chat_title(self):
        """
        選択中のチャットのタイトルを表示

        ・画面に2つのメッセージが表示された
        ユーザー: "AIの設計ってどう考えるの?"
        AI: "まず目的を決めるとこからだね💡"
        
        【処理内容】
        1. 現在のチャットIDからタイトルを取得
        2. st.subheader()で表示"""
        selected_title = self.chat_manager.get_chat_title_by_id(
            st.session_state.current_chat["id"]
        )
        # 「新規チャット」で始まる場合は表示しない
        if not selected_title.startswith("新規チャット"):
            st.subheader(f"📂 {selected_title}")
    
    def _render_chat_history(self):
        """
        会話履歴を表示
        ChatManagerから取得した履歴を表示

        【処理内容】
        1. ChatManagerから現在のチャットの会話履歴を取得
        2. 各メッセージをループして表示
        3. 🆕 is_ragフラグとchunksを使ってRAG情報を表示
        4. 参照資料のファイル名をGoogleドライブリンクに変換

        【st.chat_message()とは】
        チャット形式でメッセージを表示するStreamlitの機能
        - role="user": 右側に表示(ユーザー)
        - role="assistant": 左側に表示(AI)
        """
        # ChatManagerから最新の会話履歴を取得
        # get_chat_histories()に現在のチャットIDを渡す
        chat_histories = self.chat_manager.get_chat_histories(
            st.session_state.current_chat["id"]
        )

        # 履歴をループして表示
        for chat in chat_histories:
            with st.chat_message(chat["role"]):
                st.markdown(chat["content"])

                # assistantメッセージの場合は常にモード表示
                if chat["role"] == "assistant":
                    if chat.get("is_rag") and chat.get("chunks"):
                        # RAGモード
                        st.info("📚 **RAGモード**: 資料を参照して回答を生成しました")
                        with st.expander("📖 参照した資料の詳細を見る", expanded=False):
                            for i, chunk in enumerate(chat["chunks"], 1):
                                # ファイル名を取得
                                source = chunk.get('source', '不明')

                                # Googleドライブリンクを取得
                                if self.rag_manager:
                                    drive_link = self.rag_manager.get_google_drive_link(source)
                                else:
                                    drive_link = ""

                                # リンクがあればクリック可能に、なければ通常表示
                                if drive_link:
                                    st.markdown(f"**[{i}]** [{source}]({drive_link}) 📄")
                                else:
                                    st.markdown(f"**[{i}]** {source}")

                                # 類似度スコアを表示
                                score = chunk.get('similarity_score', 0)
                                st.markdown(f"**類似度スコア**: {score:.4f} (スコアが低いほど関連性が高い)")

                                # 最後以外は区切り線を入れる
                                if i < len(chat["chunks"]):
                                    st.divider()
                    else:
                        # 通常モード
                        st.info("💬 **通常モード**: RAG資料に関連情報がないため、一般知識で回答しました")
    
    def _render_chat_input(self):
        """
        チャット入力欄を表示して処理
        
        メッセージ送信完了!
        画面の状態:
        ✅ ダミー会話(2件)
        ✅ ユーザー: "こんにちは"
        ✅ AI: "こんにちは!元気?
        
        【st.chat_input()とは】
        チャット入力欄を表示する
        - 戻り値: ユーザーが入力したテキスト(入力がなければNone)
        
        【:= 演算子(セイウチ演算子)とは】
        代入と条件チェックを同時に行う
        if user_input := st.chat_input(...):
        = user_input = st.chat_input(...)
            if user_input:
        
        """
        # 入力欄
        user_input = st.chat_input("送信するメッセージを入力")

        if not user_input:
            return

        # ユーザーメッセージを表示
        with st.chat_message("user"):
            st.markdown(user_input)

        # ChatManagerに保存(session_stateとFirestoreも更新)
        self._add_user_message(user_input)

        # RAGモードか通常モードか判定してAI応答を取得
        self._process_ai_response_with_rag(user_input)
        
        # AI応答完了後にタイトルを自動生成
        title_generated = self._auto_generate_title_if_needed()
        
        # タイトルが生成された場合は画面を再描画
        if title_generated:
            st.rerun()

    def _process_ai_response_with_rag(self, user_input: str):
        """
        RAGを考慮してAI応答を取得・表示・保存

        【処理の流れ】
        1. RAGManagerで類似度検索
        2. 関連ドキュメントがあればRAGモードで回答
        3. なければ通常モードで回答
        4. RAGを使った場合は参照元を表示
        5. 🆕 Firestoreに保存する形式でchunksを作成

        Args:
            user_input: ユーザーの入力テキスト
        """
        current_id = st.session_state.current_chat["id"]

        with st.chat_message("assistant"):
            message_placeholder = st.empty()

            # RAGManagerがあれば検索を実行
            use_rag = False
            rag_context = ""
            search_results = []

            if self.rag_manager:
                message_placeholder.markdown("🔍 関連資料を検索中...")
                rag_data = self.rag_manager.get_rag_response_data(user_input)
                use_rag = rag_data["use_rag"]
                rag_context = rag_data.get("context", "")
                search_results = rag_data.get("search_results", [])

            # 回答生成
            full_response = ""

            if use_rag and rag_context:
                # RAGモードで回答
                message_placeholder.markdown("📚 資料を参照して回答を生成中...")

                # RAGプロンプトを作成
                rag_prompt = rag_data["prompt"]

                # 会話履歴を取得（RAGプロンプトを最後に追加）
                chat_histories = self.chat_manager.get_chat_histories(current_id)
                formatted_messages = self.chat_manager.format_chat_histories(chat_histories[:-1])  # 最後のユーザー入力は除く

                # RAGプロンプトをHumanMessageとして追加
                formatted_messages.append(
                    self.langchain_manager.create_human_message(rag_prompt)
                )

                # RAGモードでストリーミング応答を取得
                for chunk in self.langchain_manager.get_streaming_response_rag(formatted_messages):
                    full_response += chunk
                    message_placeholder.markdown(full_response)
            else:
                # 通常モードで回答
                message_placeholder.markdown("🤔 AIが考え中だよ...ちょっと待ってね!")

                # 会話履歴を取得してフォーマット
                chat_histories = self.chat_manager.get_chat_histories(current_id)
                formatted_messages = self.chat_manager.format_chat_histories(chat_histories)

                # 通常モードでストリーミング応答を取得
                for chunk in self.langchain_manager.get_streaming_response(formatted_messages):
                    full_response += chunk
                    message_placeholder.markdown(full_response)

            # RAGを使ったかどうかを表示
            if use_rag and search_results:
                st.info("📚 **RAGモード**: 資料を参照して回答を生成しました")
                with st.expander("📖 参照した資料の詳細を見る", expanded=False):
                    for i, doc in enumerate(search_results, 1):
                        # ファイル名とページ番号を取得
                        source = doc['metadata'].get('source', '不明')
                        page = doc['metadata'].get('page', '?')
                        
                        # Googleドライブリンクを取得
                        drive_link = self.rag_manager.get_google_drive_link(source)
                        
                        # リンクがあればクリック可能に、なければ通常表示
                        if drive_link:
                            st.markdown(f"**[{i}]** [{source}]({drive_link}) (ページ {page}) 📄")
                        else:
                            st.markdown(f"**[{i}]** {source} (ページ {page})")
                        
                        # 参照したテキストの抜粋を表示
                        st.markdown(f"> {doc['text'][:200]}...")
                        
                        # 類似度スコアを表示
                        st.markdown(f"**類似度スコア**: {doc['distance']:.4f} (スコアが低いほど関連性が高い)")
                        
                        # 最後以外は区切り線を入れる
                        if i < len(search_results):
                            st.divider()
            else:
                st.info("💬 **通常モード**: RAG資料に関連情報がないため、一般知識で回答しました")

        # 🆕 Firestore保存用のchunks形式に変換
        chunks_to_save = None
        if use_rag and search_results:
            chunks_to_save = []
            for doc in search_results:
                chunks_to_save.append({
                    "chunk_id": f"{doc['metadata'].get('source', '')}_{doc['metadata'].get('page', '')}_{doc['metadata'].get('chunk_index', '')}",
                    "similarity_score": doc['distance'],
                    "source": doc['metadata'].get('source', '不明')
                })

        # ChatManagerに保存（Firestoreにも保存される）
        self._add_ai_message(
            full_response, 
            is_rag=use_rag,
            chunks=chunks_to_save
        )

    def _process_ai_response(self):
        """
        AI応答を取得・表示・保存（通常モード - 後方互換用）
        
        【処理の流れ】
        1. 現在のチャットIDを取得
        2. ChatManagerから会話履歴を取得
        3. LangChain形式にフォーマット
        4. LangChainManagerでストリーム応答を取得
        5. 1文字ずつ画面に表示
        6. 完成した応答をChatManagerに保存
        """
        # 現在のチャットIDを取得
        current_id = st.session_state.current_chat["id"]
        # with st.chat_message("assistant"): AI として表示 
        with st.chat_message("assistant"):
            # st.empty()で空のプレースホルダーを作成
            message_placeholder = st.empty()
            message_placeholder.markdown("🤔 AIが考え中だよ...ちょっと待ってね!")

            # 完全な応答を格納する変数
            full_response = ""
            
            # ChatManagerから現在の会話履歴を取得
            chat_histories = self.chat_manager.get_chat_histories(current_id)
            
            # LangChain用にフォーマット
            formatted_messages = self.chat_manager.format_chat_histories(chat_histories)
            
            # ストリーム応答を取得
            for chunk in self.langchain_manager.get_streaming_response(formatted_messages):
                full_response += chunk
                message_placeholder.markdown(full_response)
        
        # ChatManagerに保存（Firestoreにも保存される）
        self._add_ai_message(full_response)
    
    def run(self):
        """
        アプリケーションのメイン実行
        
        【処理の流れ】
        1. タイトル表示
        2. サイドバー表示
        3. チャットタイトル表示
        4. 会話履歴表示
        5. チャット入力欄表示
        
        【呼び出し例】(main.pyで実行)
        gui = GUI(chat_manager, langchain_manager)
        gui.run()
        
        【Streamlitの実行順序】
        Streamlitは上から順番に実行される
        run()内の処理も上から順に実行される
        """
        # タイトル表示
        self._render_title()
        
        # サイドバー表示
        self._render_sidebar()
        
        # チャットタイトル表示
        self._render_chat_title()
        
        # 会話履歴表示
        self._render_chat_history()
        
        # チャット入力欄表示
        self._render_chat_input()