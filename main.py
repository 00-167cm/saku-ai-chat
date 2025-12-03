"""
エントリーポイント(全体起動スイッチ)
アプリケーションの起動と初期化を行う

【役割】
- 環境変数の読み込み
- ページ設定
- 各マネージャーのインスタンス化
- アプリケーションの実行
"""
from dotenv import load_dotenv
import streamlit as st
from chat.gui import GUI
from chat.chat_manager import ChatManager
from chat.langchain_manager import LangChainManager
from chat.db_manager import DBManager
from chat.rag_manager import RAGManager

# 環境変数の読み込み
load_dotenv()

# ページ設定
st.set_page_config(page_title="さくらのAIチャットボット", layout="wide")

# 各マネージャーの初期化
db_manager = DBManager()
langchain_manager = LangChainManager()
chat_manager = ChatManager(db_manager, langchain_manager)

# RAGManagerの初期化
rag_manager = RAGManager(
    documents_dir="data/documents",
    chroma_dir="data/chroma_db",
    collection_name="acom_documents",
    threshold=1.5
)

# GUIの初期化（RAGManagerを渡す）
gui = GUI(chat_manager, langchain_manager, rag_manager)

# アプリケーション実行
if __name__ == "__main__":
    gui.run()
