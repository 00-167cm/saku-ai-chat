"""
📄 ドキュメント処理
    PDFからテキストを抽出し、チャンクに分割する
    
【役割】
- PDFファイルの読み込み
- テキスト抽出
- チャンク分割（RAG用に適切なサイズに）
- メタデータの付与（ファイル名、ページ番号など）
"""
import os
from typing import List, Dict, Any
from pathlib import Path

# PDF処理用ライブラリ
import fitz  # PyMuPDF

# HTML処理用ライブラリ
from bs4 import BeautifulSoup

# LangChainのテキスト分割
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentProcessor:
    """
    ドキュメント処理クラス
    PDFをテキスト化してチャンクに分割する
    
    【このクラスが持つデータ】
    - self.chunk_size: 1チャンクの最大文字数
    - self.chunk_overlap: チャンク間の重複文字数
    - self.text_splitter: テキスト分割器（LangChain）
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100
    ):
        """
        ドキュメント処理の初期化
        
        【処理内容】
        1. チャンクサイズを設定
        2. テキスト分割器を初期化
        
        Args:
            chunk_size: 1チャンクの最大文字数（デフォルト500文字）
            chunk_overlap: チャンク間の重複文字数（デフォルト100文字）
        
        【なぜ重複させるの？】
        文の途中で切れると意味が失われるため、
        前後のチャンクと少し重複させることで
        文脈を保持する
        
        【呼び出し例】
        processor = DocumentProcessor(chunk_size=500, chunk_overlap=100)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # テキスト分割器を初期化
        # RecursiveCharacterTextSplitter: 段落→文→単語の順で分割を試みる
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            # 日本語対応のセパレーター
            separators=["\n\n", "\n", "。", "、", " ", ""]
        )
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        PDFからテキストを抽出（ページごと）
        
        【処理の流れ】
        1. PyMuPDFでPDFを開く
        2. 各ページのテキストを抽出
        3. ページ番号とファイル名をメタデータとして付与
        
        Args:
            pdf_path: PDFファイルのパス
        
        Returns:
            ページごとのテキストとメタデータのリスト
            [
                {
                    "text": "ページ1のテキスト...",
                    "metadata": {
                        "source": "document.pdf",
                        "page": 1
                    }
                },
                ...
            ]
        
        【呼び出し例】
        pages = processor.extract_text_from_pdf("data/documents/rules.pdf")
        """
        # 結果を格納するリスト
        pages = []
        
        # ファイル名を取得（パスから）
        file_name = Path(pdf_path).name
        
        try:
            # PDFを開く
            doc = fitz.open(pdf_path)
            
            # 各ページを処理
            for page_num, page in enumerate(doc, start=1):
                # ページからテキストを抽出
                text = page.get_text()
                
                # 空でなければ追加
                if text.strip():
                    pages.append({
                        "text": text,
                        "metadata": {
                            "source": file_name,
                            "page": page_num
                        }
                    })
            
            # PDFを閉じる
            doc.close()
            
            print(f"✅ PDF読み込み完了: {file_name} ({len(pages)}ページ)")
            return pages
            
        except Exception as e:
            print(f"❌ PDF読み込みエラー: {pdf_path}")
            print(f"   エラー内容: {e}")
            return []

    def extract_text_from_html(self, html_path: str) -> List[Dict[str, Any]]:
        """
        HTMLからテキストを抽出

        【処理の流れ】
        1. HTMLファイルを読み込む
        2. BeautifulSoupでHTMLを解析
        3. テキストのみを抽出（タグを除去）
        4. ファイル名をメタデータとして付与

        Args:
            html_path: HTMLファイルのパス

        Returns:
            テキストとメタデータのリスト
            [
                {
                    "text": "HTMLのテキスト内容...",
                    "metadata": {
                        "source": "document.html",
                        "page": 1
                    }
                }
            ]

        【呼び出し例】
        pages = processor.extract_text_from_html("data/documents/rules.html")
        """
        # ファイル名を取得（パスから）
        file_name = Path(html_path).name

        try:
            # HTMLファイルを読み込む
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # BeautifulSoupでHTMLを解析
            soup = BeautifulSoup(html_content, 'html.parser')

            # scriptタグとstyleタグを除去
            for script in soup(['script', 'style']):
                script.decompose()

            # テキストのみを抽出
            text = soup.get_text()

            # 余分な空白を削除
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            # 空でなければ返す
            if text.strip():
                print(f"✅ HTML読み込み完了: {file_name}")
                return [{
                    "text": text,
                    "metadata": {
                        "source": file_name,
                        "page": 1
                    }
                }]
            else:
                print(f"⚠️ テキストが抽出できませんでした: {file_name}")
                return []

        except Exception as e:
            print(f"❌ HTML読み込みエラー: {html_path}")
            print(f"   エラー内容: {e}")
            return []

    def split_into_chunks(
        self,
        pages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        ページテキストをチャンクに分割
        
        【処理の流れ】
        1. 各ページのテキストを取得
        2. text_splitterでチャンクに分割
        3. 各チャンクにメタデータを付与
        
        Args:
            pages: extract_text_from_pdf()の戻り値
        
        Returns:
            チャンクごとのテキストとメタデータのリスト
            [
                {
                    "text": "チャンク1のテキスト...",
                    "metadata": {
                        "source": "document.pdf",
                        "page": 1,
                        "chunk_index": 0
                    }
                },
                ...
            ]
        
        【呼び出し例】
        chunks = processor.split_into_chunks(pages)
        """
        chunks = []
        chunk_index = 0
        
        for page in pages:
            # ページテキストをチャンクに分割
            page_chunks = self.text_splitter.split_text(page["text"])
            
            # 各チャンクにメタデータを付与
            for chunk_text in page_chunks:
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        **page["metadata"],  # 元のメタデータをコピー
                        "chunk_index": chunk_index
                    }
                })
                chunk_index += 1
        
        print(f"✅ チャンク分割完了: {len(chunks)}チャンク")
        return chunks
    
    def process_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        PDFを処理してチャンクに分割（一連の処理をまとめて実行）
        
        【処理の流れ】
        1. PDFからテキスト抽出
        2. チャンクに分割
        3. 結果を返す
        
        Args:
            pdf_path: PDFファイルのパス
        
        Returns:
            チャンクのリスト（split_into_chunks()と同じ形式）
        
        【呼び出し例】
        chunks = processor.process_pdf("data/documents/rules.pdf")
        """
        # テキスト抽出
        pages = self.extract_text_from_pdf(pdf_path)
        
        if not pages:
            return []
        
        # チャンク分割
        chunks = self.split_into_chunks(pages)

        return chunks

    def process_html(self, html_path: str) -> List[Dict[str, Any]]:
        """
        HTMLを処理してチャンクに分割（一連の処理をまとめて実行）

        【処理の流れ】
        1. HTMLからテキスト抽出
        2. チャンクに分割
        3. 結果を返す

        Args:
            html_path: HTMLファイルのパス

        Returns:
            チャンクのリスト（split_into_chunks()と同じ形式）

        【呼び出し例】
        chunks = processor.process_html("data/documents/rules.html")
        """
        # テキスト抽出
        pages = self.extract_text_from_html(html_path)

        if not pages:
            return []

        # チャンク分割
        chunks = self.split_into_chunks(pages)

        return chunks

    def process_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """
        ディレクトリ内の全PDFとHTMLを処理

        【処理の流れ】
        1. ディレクトリ内の.pdfと.htmlファイルを検索
        2. 各ファイルを処理
        3. 全チャンクをまとめて返す

        Args:
            directory_path: ファイルが格納されたディレクトリのパス

        Returns:
            全ファイルのチャンクをまとめたリスト

        【呼び出し例】
        all_chunks = processor.process_directory("data/documents")
        """
        all_chunks = []

        # ディレクトリ内のファイルを取得
        directory = Path(directory_path)

        if not directory.exists():
            print(f"❌ ディレクトリが存在しません: {directory_path}")
            return []

        # .pdfと.htmlファイルを検索
        pdf_files = list(directory.glob("*.pdf"))
        html_files = list(directory.glob("*.html"))

        total_files = len(pdf_files) + len(html_files)

        if total_files == 0:
            print(f"⚠️ PDFまたはHTMLファイルが見つかりません: {directory_path}")
            return []

        print(f"📁 {len(pdf_files)}個のPDFファイル、{len(html_files)}個のHTMLファイルを検出")

        # 各PDFを処理
        for pdf_file in pdf_files:
            chunks = self.process_pdf(str(pdf_file))
            all_chunks.extend(chunks)

        # 各HTMLを処理
        for html_file in html_files:
            chunks = self.process_html(str(html_file))
            all_chunks.extend(chunks)

        print(f"✅ 全ファイル処理完了: 合計{len(all_chunks)}チャンク")
        return all_chunks
