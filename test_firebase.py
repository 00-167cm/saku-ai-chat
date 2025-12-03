import firebase_admin
from firebase_admin import credentials, firestore

# Firebase初期化
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)

# Firestore接続
db = firestore.client()

# テスト：chatsコレクションを取得
docs = db.collection('chats').get()

print("=== Firestore接続テスト ===")
for doc in docs:
    print(f"ドキュメントID: {doc.id}")
    print(f"データ: {doc.to_dict()}")
    
print("\n✅ 接続成功！")