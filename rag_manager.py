"""
🤖 RAG管理
    RAG（検索拡張生成）の全体制御を行う
    
【役割】
- DocumentProcessorとChromaManagerの統合
- PDFの自動処理パイプライン
- RAGモードと通常モードの判定
- RAG用プロンプトの生成
"""
import os
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

from chat.document_processor import DocumentProcessor
from chat.chroma_manager import ChromaManager

# Googleドライブのファイルリンクマッピング
GOOGLE_DRIVE_LINKS = {
    "acom_customer_record_rules.pdf": "https://drive.google.com/file/d/1x7v3R6Fqphg96j-VaK6bX26zF3LoW9qi/view?usp=drive_link",
    "acom_documents_mapping.pdf": "https://drive.google.com/file/d/1x48SomSfB3L0m7v85jotNB1cNQ2e36aE/view?usp=drive_link",
    "acom_workflow_rag.pdf": "https://drive.google.com/file/d/1nJv48_0QCg6BF-wyXYR0mvjSF5wiITYY/view?usp=drive_link"
}

class RAGManager:
    """
    RAG管理クラス
    PDF処理からベクトル検索、回答生成まで一貫して管理
    
    【このクラスが持つデータ】
    - self.document_processor: PDF処理担当
    - self.chroma_manager: ベクトルDB担当
    - self.documents_dir: PDFを置くディレクトリ
    - self.threshold: RAG使用判定の閾値
    """
    
    def __init__(
        self,
        documents_dir: str = "data/documents",
        chroma_dir: str = "data/chroma_db",
        collection_name: str = "acom_documents",
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        threshold: float = 0.5
    ):
        """
        RAGManager初期化
        
        【処理内容】
        1. DocumentProcessorを初期化
        2. ChromaManagerを初期化
        3. ディレクトリを設定
        
        Args:
            documents_dir: PDFを格納するディレクトリ
            chroma_dir: ChromaDBの永続化先
            collection_name: コレクション名
            chunk_size: チャンクサイズ
            chunk_overlap: チャンク重複サイズ
            threshold: RAG使用判定の閾値（距離がこれ以下ならRAG使用）
        
        【呼び出し例】
        rag = RAGManager(
            documents_dir="data/documents",
            chroma_dir="data/chroma_db"
        )
        """
        self.documents_dir = documents_dir
        self.threshold = threshold
        
        # ディレクトリ作成
        Path(documents_dir).mkdir(parents=True, exist_ok=True)
        
        # DocumentProcessorを初期化
        self.document_processor = DocumentProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # ChromaManagerを初期化
        self.chroma_manager = ChromaManager(
            persist_directory=chroma_dir,
            collection_name=collection_name
        )
        
        print(f"✅ RAGManager初期化完了")
        print(f"   ドキュメント格納先: {documents_dir}")
    
    def process_and_store_pdf(self, pdf_path: str) -> bool:
        """
        PDFを処理してChromaDBに格納（単一ファイル）
        
        【処理の流れ】
        1. PDFからテキスト抽出
        2. チャンク分割
        3. ベクトル化してChromaに格納
        
        Args:
            pdf_path: PDFファイルのパス
        
        Returns:
            成功した場合True
        
        【呼び出し例】
        rag.process_and_store_pdf("data/documents/rules.pdf")
        """
        print(f"\n📄 PDF処理開始: {pdf_path}")
        
        # チャンクに分割
        chunks = self.document_processor.process_pdf(pdf_path)
        
        if not chunks:
            return False
        
        # ChromaDBに格納
        result = self.chroma_manager.add_documents(chunks)
        
        return result
    
    def process_all_pdfs(self) -> bool:
        """
        ドキュメントディレクトリ内の全PDFを処理
        
        【処理の流れ】
        1. ディレクトリ内のPDFを検索
        2. 各PDFを処理してChromaに格納
        
        Returns:
            成功した場合True
        
        【呼び出し例】
        rag.process_all_pdfs()
        """
        print(f"\n📁 ディレクトリ処理開始: {self.documents_dir}")
        
        # 全PDFをチャンク化
        all_chunks = self.document_processor.process_directory(self.documents_dir)
        
        if not all_chunks:
            return False
        
        # ChromaDBに格納
        result = self.chroma_manager.add_documents(all_chunks)
        
        return result
    
    def query(
        self,
        user_question: str,
        n_results: int = 3
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        ユーザーの質問に対してRAG検索を実行
        
        【処理の流れ】
        1. 質問をベクトル化して類似検索
        2. 閾値で「RAG使用」か「通常回答」か判定
        3. 結果とフラグを返す
        
        Args:
            user_question: ユーザーの質問
            n_results: 取得する関連ドキュメント数
        
        Returns:
            (関連ドキュメントリスト, RAGを使うべきか)
        
        【呼び出し例】
        results, use_rag = rag.query("書類不備の対応は？")
        """
        return self.chroma_manager.search_with_threshold(
            query=user_question,
            threshold=self.threshold,
            n_results=n_results
        )
    
    def build_rag_context(
        self,
        search_results: List[Dict[str, Any]]
    ) -> str:
        """
        検索結果からRAG用のコンテキスト（参照情報）を構築
        
        【処理内容】
        検索結果を整形して、AIに渡すコンテキストを作成
        
        Args:
            search_results: query()で取得した検索結果
        
        Returns:
            コンテキスト文字列
        
        【出力例】
        '''
        【参照資料1】(rules.pdf / ページ3)
        書類不備がある場合は「NSC-NG理由コード表」に基づき...
        
        【参照資料2】(rules.pdf / ページ5)
        お客様への再提出依頼はテンプレート文を使用...
        '''
        """
        if not search_results:
            return ""
        
        context_parts = []
        
        for i, result in enumerate(search_results, start=1):
            source = result["metadata"].get("source", "不明")
            page = result["metadata"].get("page", "?")
            text = result["text"]
            
            context_parts.append(
                f"【参照資料{i}】({source} / ページ{page})\n{text}"
            )
        
        return "\n\n".join(context_parts)
    
    def build_rag_prompt(
        self,
        user_question: str,
        context: str
    ) -> str:
        """
        RAGモード用のプロンプトを構築
        
        【処理内容】
        参照資料とユーザーの質問を組み合わせて
        AIに渡すプロンプトを作成
        
        Args:
            user_question: ユーザーの質問
            context: build_rag_context()で作成したコンテキスト
        
        Returns:
            RAG用プロンプト
        """
        return f"""以下の参照資料に基づいて、ユーザーの質問に回答してください。    

【重要なルール】
1. NSC業務フローに基づき、またはネットサービスセンターのローカルルールによると、という接頭語を付けて回答してください
2. 参照資料に書かれている情報のみを使用してください
3. 参照資料にない情報は「資料に記載がありません」と伝えてください
4. 具体的なコード名やルール名がある場合は、それを明記してください

===== 参照資料 =====
{context}
====================

ユーザーの質問: {user_question}

上記の参照資料に基づいて回答してください:"""
    
    def get_rag_response_data(
        self,
        user_question: str
    ) -> Dict[str, Any]:
        """
        RAG処理を実行して、回答に必要なデータを取得
        
        【処理の流れ】
        1. 類似度検索を実行
        2. RAGを使うか判定
        3. 使う場合はコンテキストとプロンプトを構築
        
        Args:
            user_question: ユーザーの質問
        
        Returns:
            {
                "use_rag": True/False,
                "context": "参照資料...",  # RAG使用時のみ
                "prompt": "RAGプロンプト...",  # RAG使用時のみ
                "search_results": [...]  # RAG使用時のみ
            }
        
        【呼び出し例】(chat_managerやgui.pyから)
        rag_data = rag.get_rag_response_data("審査の流れは？")
        if rag_data["use_rag"]:
            # RAGプロンプトを使ってAIに質問
        else:
            # 通常の質問をAIに送信
        """
        # 検索実行
        results, use_rag = self.query(user_question)
        
        if not use_rag:
            return {
                "use_rag": False,
                "context": "",
                "prompt": "",
                "search_results": []
            }
        
        # コンテキスト構築
        context = self.build_rag_context(results)
        
        # プロンプト構築
        prompt = self.build_rag_prompt(user_question, context)
        
        return {
            "use_rag": True,
            "context": context,
            "prompt": prompt,
            "search_results": results
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        RAGシステムの状態を取得
        
        Returns:
            {
                "documents_dir": "data/documents",
                "collection_info": {...},
                "threshold": 0.5
            }
        """
        return {
            "documents_dir": self.documents_dir,
            "collection_info": self.chroma_manager.get_collection_info(),
            "threshold": self.threshold
        }
    
    def get_google_drive_link(self, filename: str) -> str:  # ← ここに追加！
        """
        ファイル名からGoogleドライブのリンクを取得
        
        Args:
            filename: ファイル名
        
        Returns:
            GoogleドライブのURL(なければ空文字列)
        """
        return GOOGLE_DRIVE_LINKS.get(filename, "")
    
    def reload_documents(self) -> bool:
        """ドキュメントを再読み込み"""
        print("\n🔄 ドキュメント再読み込み開始...")
        self.chroma_manager.clear_collection()
        return self.process_all_pdfs()
