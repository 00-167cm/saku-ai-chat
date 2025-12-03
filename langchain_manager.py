"""
🔵 langchain_managerの役割
    AIとの連携(ユーザーの入力渡すことから、AIの返答返すまで)
    chat_managerから受け取ったユーザーの入力をAIに渡す
    AIの回答を取得
    AIの回答をchat_managerに返す
    会話内容からタイトルを生成
    
【更新履歴】
- RAGモード用のプロンプトとレスポンス生成を追加
"""
# LangChainのOpenAI接続クラス
from langchain_openai import ChatOpenAI
# プロンプト管理
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# 出力を文字列に変換
from langchain_core.output_parsers import StrOutputParser
# メッセージ型
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
# 型ヒント用
from typing import List, Generator


class LangChainManager:
    """
    LangChainを使ったAI連携を管理するクラス
    初期化した時に引数を与えていないから、model,temperatureはデフォルト引数が適用される

    """
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.7):
        """
        LangChainの初期化
        
        OpenAIとの接続準備完了
        プロンプトテンプレート作成完了
        AIに送信できる状態になった

        【処理の流れ】
        1. 引数で受け取ったmodel, temperatureをインスタンス変数に保存
        2. LLM(ChatOpenAI)を初期化
        3. プロンプトテンプレートを作成
        4. 出力パーサーを初期化
        5. これらを組み合わせてチェーンを作成
        
        Args:
            model: 使用するOpenAIモデル
            temperature: 生成の多様性(0.0-1.0)
        """
        # 【処理の流れ】
        # 1.引数をインスタンス変数に格納
        self.model = model
        self.temperature = temperature

        # 関数名の頭につく「_」はそのクラス内からしか呼び出されないことを表すマナー(ルールではない)
        # 2._initialize_llm() を呼び出してLLMを初期化
        self.llm = self._initialize_llm()
        # → ChatOpenAI(model="gpt-4o-mini", temperature=0.7) が実行される
        # → OpenAIに接続できる状態になる

        # 3. プロンプトテンプレートを作成
        self.prompt = self._create_prompt()
        # → ChatPromptTemplate.from_messages([...]) が実行される
        # → システムプロンプトとMessagesPlaceholderが設定される

        # 4. 出力パーサーを初期化(AIの応答を文字列に変換するためのもの)
        self.output_parser = StrOutputParser()
        # 5. これらを組み合わせてチェーンを作成(prompt → llm → output_parser の順で処理が流れる)
        # |(パイプ)演算子でつなぐことで、データが順番に流れていく
        self.chain = self.prompt | self.llm | self.output_parser
        
        # タイトル生成用のチェーンも作成
        self.title_prompt = self._create_title_prompt()
        self.title_chain = self.title_prompt | self.llm | self.output_parser
        
        # 🆕 RAG用のプロンプトとチェーンを作成
        self.rag_prompt = self._create_rag_prompt()
        self.rag_chain = self.rag_prompt | self.llm | self.output_parser
    
    def _initialize_llm(self) -> ChatOpenAI:
        """
        LLM(Large Language Model)の初期化

        【処理内容】
        - ChatOpenAIクラスをインスタンス化
        - self.modelとself.temperatureを使ってAIとの接続を設定
        
        【戻り値】
        ChatOpenAIのインスタンス(AIとの接続オブジェクト)
        
        【補足】
        -> ChatOpenAI は「この関数の戻り値の型」を示す型ヒント
        実際の動作には影響しないが、コードを読む人に分かりやすくするため
        """
        return ChatOpenAI(
            model=self.model,
            temperature=self.temperature
        )
    
    def _create_prompt(self) -> ChatPromptTemplate:
        # インスタンス化したChatPromptTemplateを返す「だけ」
        # クラスの中に関数がある      
        """
        プロンプトテンプレートの作成
        【処理内容】
        - ChatPromptTemplate.from_messages()を呼び出してテンプレートを作成
        - システムプロンプト(AIの性格設定)と会話履歴の場所を定義
        
        【戻り値】
        ChatPromptTemplateのインスタンス

        【補足】
        クラスの中にある関数(メソッド)を呼び出す方法:
        
        方法①: インスタンス化してから呼び出す
            instance = ClassName()
            instance.method_name()
        
        方法②: クラスから直接呼び出す(クラスメソッドの場合)
            ClassName.method_name()
        
        今回は方法②を使っている
            ChatPromptTemplate.from_messages() はクラスメソッド
        
        """
        return ChatPromptTemplate.from_messages([
            (
                "system",
                "あなたはフレンドリーで親切なAIアシスタントです。ユーザーの質問に対して、明るくわかりやすく丁寧に答えてください。"
            ),
            MessagesPlaceholder(variable_name="messages")
        ])
    
    def _create_title_prompt(self) -> ChatPromptTemplate:
        """
        タイトル生成用のプロンプトテンプレートを作成
        
        【処理内容】
        - 会話内容を要約してタイトルを生成するためのプロンプト
        - 12文字以内という制約を設定
        
        【戻り値】
        ChatPromptTemplateのインスタンス
        """
        return ChatPromptTemplate.from_messages([
            (
                "system",
                """以下の会話内容を要約して、12文字以内の短いタイトルを生成してください。
                
ルール:
- 12文字以内で簡潔に
- 会話の主要なテーマを捉える
- 「〜について」などの余計な言葉は省く
- タイトルのみを出力(説明文は不要)

例:
会話: Pythonの基本文法について教えて → タイトル: Python文法
会話: おすすめのカフェを教えて → タイトル: おすすめカフェ
会話: ストレス解消法について → タイトル: ストレス解消"""
            ),
            MessagesPlaceholder(variable_name="messages")
        ])
    
    def _create_rag_prompt(self) -> ChatPromptTemplate:
        """
        🆕 RAG用のプロンプトテンプレートを作成
        
        【処理内容】
        - 参照資料を基に回答するためのプロンプト
        - NSCローカルルールに従った回答形式を指定
        
        【戻り値】
        ChatPromptTemplateのインスタンス
        """
        return ChatPromptTemplate.from_messages([
            (
                "system",
                """あなたはアコム ネットサービスセンターの業務サポートAIです。

【重要なルール】
1. 回答の冒頭に「NSC業務フローに基づき」または「ネットサービスセンターのローカルルールによると」という接頭語を付けてください
2. 参照資料に書かれている情報のみを使用してください
3. 参照資料にない情報は「資料に記載がありません」と正直に伝えてください
4. 具体的なコード名やルール名（NSCコード、NG理由コード表など）がある場合は、それを明記してください
5. 分かりやすく、丁寧に回答してください

参照資料がある場合は、それに基づいて回答します。"""
            ),
            MessagesPlaceholder(variable_name="messages")
        ])
    
    def create_human_message(self, content: str) -> HumanMessage:
        """
        ユーザーの入力からHumanMessageオブジェクトを作成
        
        【処理内容】
        - 文字列をLangChainのHumanMessage型に変換
        - LangChainはこの型を使ってユーザーメッセージを管理
        
        Args:
            content: ユーザーの入力テキスト(例: "こんにちは")
        
        Returns:
            HumanMessage: LangChain用のメッセージオブジェクト
        
        【呼び出し例】
        message = langchain_manager.create_human_message("こんにちは")
        # messageは HumanMessage(content="こんにちは") という形になる
        """
        return HumanMessage(content=content)
    
    def create_ai_message(self, content: str) -> AIMessage:
        """
        AIの応答からAIMessageオブジェクトを作成
        
        【処理内容】
        - 文字列をLangChainのAIMessage型に変換
        - LangChainはこの型を使ってAIの応答を管理
        
        Args:
            content: AIの応答テキスト(例: "こんにちは!調子はどう?")
        
        Returns:
            AIMessage: LangChain用のメッセージオブジェクト
        
        【呼び出し例】
        message = langchain_manager.create_ai_message("こんにちは!")
        # messageは AIMessage(content="こんにちは!") という形になる
        """
        # AIMessageクラスをインスタンス化
        # contentを引数として渡すと、AIの応答として扱われる
        return AIMessage(content=content)
    
    def get_streaming_response(
        self,
        messages: List
    ) -> Generator[str, None, None]:
        """
        メッセージ履歴を基にAIからストリーミング応答を取得
        
        【処理内容】
        1. self.chain.stream()でAIにメッセージを送る
        2. AIから1文字ずつ(チャンクごとに)応答が返ってくる
        3. yieldで1つずつ返す(ジェネレーター関数)
        
        Args:
            messages: LangChain形式のメッセージ履歴リスト
                [HumanMessage(...), AIMessage(...), ...]
        
        Yields:
            str: AIからの応答チャンク(1文字〜数文字ずつ)
        
        【Generatorとは】
        Generator[str, None, None] は型ヒントで:
        - 1つ目のstr: yieldで返す値の型
        - 2つ目のNone: send()で受け取る値の型(今回は使わない)
        - 3つ目のNone: return で返す値の型(今回は使わない)
        
        【yieldとreturnの違い】
        - return: 値を返して関数終了
        - yield: 値を返すが関数は一時停止(次の呼び出しで続きから再開)
        
        【呼び出し例】
        for chunk in langchain_manager.get_streaming_response(messages):
            print(chunk)  # "こ" "ん" "にち" "は" のように1つずつ表示
        """
        # self.chain.stream()でAIにメッセージを送信
        # {"messages": messages} で、プロンプトの{messages}部分に履歴を埋め込む
        for chunk in self.chain.stream({"messages": messages}):
            yield chunk
    
    def get_streaming_response_rag(
        self,
        messages: List
    ) -> Generator[str, None, None]:
        """
        🆕 RAGモード用のストリーミング応答を取得
        
        【処理内容】
        RAG用のプロンプト(rag_chain)を使ってストリーミング応答を取得
        
        Args:
            messages: LangChain形式のメッセージ履歴リスト
                      （RAGプロンプトを含む）
        
        Yields:
            str: AIからの応答チャンク
        
        【呼び出し例】
        for chunk in langchain_manager.get_streaming_response_rag(messages):
            print(chunk)
        """
        for chunk in self.rag_chain.stream({"messages": messages}):
            yield chunk
    
    def get_complete_response(
        self,
        messages: List
    ) -> str:
        """
        メッセージ履歴を基にAIから完全な応答を取得
        (ストリーミングではなく一度に取得)
        
        【処理内容】
        - self.chain.invoke()でAIにメッセージを送る
        - ストリーミングせず、完成した応答を一気に返す
        
        Args:
            messages: LangChain形式のメッセージ履歴リスト
        
        Returns:
            str: AIからの完全な応答(例: "こんにちは!調子はどう?")
        
        【get_streaming_response()との違い】
        - get_streaming_response: 1文字ずつ返す(リアルタイム表示向け)
        - get_complete_response: 全文を一気に返す(バッチ処理向け)
        
        【呼び出し例】
        response = langchain_manager.get_complete_response(messages)
        print(response)  # "こんにちは!調子はどう?" と一気に表示
        """
        return self.chain.invoke({"messages": messages})
    
    def generate_title(self, messages: List) -> str:
        """
        会話内容からタイトルを生成
        
        【処理内容】
        1. タイトル生成用のチェーンにメッセージを送る
        2. AIが会話を要約してタイトルを返す
        3. 15文字を超えた場合は切り詰める
        
        Args:
            messages: LangChain形式のメッセージ履歴リスト(最初の数件)
        
        Returns:
            生成されたタイトル(15文字以内)
        
        【呼び出し例】
        title = langchain_manager.generate_title(formatted_messages)
        # title = "Python基本文法"
        """
        # タイトル生成チェーンを実行
        title = self.title_chain.invoke({"messages": messages})
        
        # 余計な空白や改行を削除
        title = title.strip()
        
        # 15文字を超えた場合は切り詰める
        if len(title) > 15:
            title = title[:15]
        
        return title
    
    def update_system_prompt(self, new_system_prompt: str):
        """
        システムプロンプト(AIの性格設定)を更新
        
        【処理内容】
        1. 新しいシステムプロンプトでプロンプトテンプレートを再作成
        2. チェーンを再構築
        
        Args:
            new_system_prompt: 新しいシステムプロンプト
                            (例: "あなたは親切なアシスタントです")
        
        【使用例】
        langchain_manager.update_system_prompt("あなたは厳しい先生です")
        # この後のAI応答は「厳しい先生」として振る舞う
        """
        # 新しいプロンプトテンプレートを作成
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", new_system_prompt),
            MessagesPlaceholder(variable_name="messages")
        ])
        # チェーンを再構築
        self.chain = self.prompt | self.llm | self.output_parser
    
    def update_model_settings(
        self,
        model: str = None,
        temperature: float = None
    ):
        """
        モデル設定を更新
        
        【処理内容】
        1. modelやtemperatureが指定されていれば更新
        2. LLMを再初期化
        3. チェーンを再構築
        
        Args:
            model: 新しいモデル名(Noneなら変更なし)
            temperature: 新しいtemperature値(Noneなら変更なし)
        
        【使用例】
        # モデルだけ変更
        langchain_manager.update_model_settings(model="gpt-4")
        
        # temperatureだけ変更
        langchain_manager.update_model_settings(temperature=0.9)
        
        # 両方変更
        langchain_manager.update_model_settings(model="gpt-4", temperature=0.5)
        """
        # modelが指定されていれば(is not None)更新
        if model is not None:
            self.model = model
        # temperatureが指定されていれば更新
        if temperature is not None:
            self.temperature = temperature
        
        # 新しい設定でLLMを再初期化
        self.llm = self._initialize_llm()
        # チェーンを再構築
        self.chain = self.prompt | self.llm | self.output_parser
        self.title_chain = self.title_prompt | self.llm | self.output_parser
        self.rag_chain = self.rag_prompt | self.llm | self.output_parser
