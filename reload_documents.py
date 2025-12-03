"""
ChromaDBのドキュメントを再読み込みするスクリプト
ファイル名を変更した後に実行してください
"""
from dotenv import load_dotenv
from chat.rag_manager import RAGManager

load_dotenv()

print("=" * 50)
print("📚 ChromaDB ドキュメント再読み込みスクリプト")
print("=" * 50)

rag_manager = RAGManager(
    documents_dir="data/documents",
    chroma_dir="data/chroma_db",
    collection_name="acom_documents",
    threshold=1.5
)

print("\n🔄 既存データをクリア中...")
success = rag_manager.chroma_manager.clear_collection()

if not success:
    print("❌ クリアに失敗しました")
    exit(1)

print("✅ クリア完了")

print("\n📥 新しいドキュメントを読み込み中...")
success = rag_manager.process_all_pdfs()

if success:
    print("\n" + "=" * 50)
    print("✅ 再読み込み完了！")
    print("=" * 50)
    
    status = rag_manager.get_status()
    collection_info = status['collection_info']
    
    print(f"\n📊 登録結果:")
    print(f"  ファイル数: {collection_info.get('file_count', 0)}個")
    print(f"  チャンク数: {collection_info.get('chunk_count', 0)}個")
    
    print(f"\n📄 登録されたファイル:")
    source_list = rag_manager.chroma_manager.get_source_list()
    for i, source in enumerate(source_list, 1):
        print(f"  {i}. {source}")
    
    print("\n✨ main.pyを起動してください")
else:
    print("❌ 読み込みに失敗しました")