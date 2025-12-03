# saku-ai-chat
# 🤖 社内業務ルール対応 AIチャットボット

RAG（Retrieval-Augmented Generation）技術を活用し、社内の業務ルールに基づいて正確に回答できるAIチャットボットです。

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40-red)
![LangChain](https://img.shields.io/badge/LangChain-0.3-green)
![Firebase](https://img.shields.io/badge/Firebase-Firestore-orange)

---

## 📋 概要

### 解決した課題

一般的なAI（ChatGPTなど）は、社内の最新業務ルールを知りません。そのため、業務に関する質問に正確に答えることができませんでした。

### 解決策

**RAG（検索拡張生成）** 技術を使い、社内資料を参照しながら回答できる仕組みを構築しました。

---

## ✨ 主な機能

| 機能 | 説明 |
|------|------|
| 📚 **RAGモード** | 社内資料を検索し、関連情報に基づいて回答 |
| 💬 **通常モード** | 一般的な質問にはAIの知識で回答 |
| 🔄 **自動判定** | 質問内容から最適なモードを自動選択 |
| 📎 **参照元表示** | どの資料を参照したか明示 |
| 💾 **会話履歴保存** | Firestoreで会話を永続化 |
| 🔁 **デイリーリセット** | 毎日自動でデモ状態にリセット |

---

## 🛠️ 技術スタック

### バックエンド
- **Python 3.12** - メイン言語
- **LangChain** - LLMオーケストレーション
- **OpenAI API** - GPT-4oによる回答生成 & Embeddings
- **ChromaDB** - ベクトルデータベース
- **Firebase Firestore** - 会話履歴の永続化

### フロントエンド
- **Streamlit** - WebアプリケーションUI

### ドキュメント処理
- **PyMuPDF** - PDF解析
- **BeautifulSoup** - HTML解析

---

## 🏗️ システム構成

```
┌─────────────────────────────────────────────────────────────┐
│                      Streamlit UI                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      ChatManager                            │
│            (会話管理・セッション状態管理)                      │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌───────────────────┐ ┌─────────────┐ ┌─────────────────────┐
│    RAGManager     │ │ LangChain   │ │     DBManager       │
│  (検索・判定)      │ │  Manager    │ │   (Firestore)       │
└───────────────────┘ └─────────────┘ └─────────────────────┘
         │                   │
         ▼                   ▼
┌───────────────────┐ ┌─────────────┐
│    ChromaDB       │ │  OpenAI API │
│ (ベクトル検索)     │ │  (GPT-4o)   │
└───────────────────┘ └─────────────┘
```

---

## 📁 ディレクトリ構成

```
Chat_bot/
├── main.py                 # エントリーポイント
├── reset_demo.py           # デモリセット用スクリプト
├── reload_documents.py     # ドキュメント再読み込み
├── requirements.txt        # 依存パッケージ
├── firebase-key.json       # Firebase認証キー（※Git管理外）
├── .env                    # 環境変数（※Git管理外）
│
├── chat/                   # メインモジュール
│   ├── gui.py              # Streamlit UI
│   ├── chat_manager.py     # 会話管理
│   ├── db_manager.py       # Firestore操作
│   ├── rag_manager.py      # RAG制御
│   ├── chroma_manager.py   # ベクトルDB操作
│   ├── document_processor.py # PDF/HTML処理
│   └── langchain_manager.py  # LangChain制御
│
└── data/
    ├── documents/          # 業務資料（PDF/HTML）
    └── chroma_db/          # ベクトルDB永続化
```

---

## 🔍 RAGの仕組み

### 1. ドキュメント処理（事前準備）

```
業務資料（PDF/HTML）
        │
        ▼ DocumentProcessor
┌─────────────────────┐
│ テキスト抽出        │
│ 500文字ごとに分割   │
│ (100文字オーバーラップ) │
└─────────────────────┘
        │
        ▼ ChromaManager
┌─────────────────────┐
│ OpenAI Embeddings   │
│ でベクトル化        │
│ ChromaDBに保存      │
└─────────────────────┘
```

### 2. 質問応答（リアルタイム）

```
ユーザーの質問
「書類不備の対応は？」
        │
        ▼ RAGManager
┌─────────────────────┐
│ 質問をベクトル化    │
│ ChromaDBで類似検索  │
│ 閾値で判定          │
└─────────────────────┘
        │
        ├── 関連あり → RAGモード
        │   └── 参照資料 + 質問 → GPT-4o → 回答
        │
        └── 関連なし → 通常モード
            └── 質問のみ → GPT-4o → 回答
```

---

## 💡 工夫したポイント

### 1. 自動モード判定
類似度スコアの閾値を設けることで、RAGモードと通常モードを自動で切り替え。ユーザーは意識せずに最適な回答を得られます。

### 2. 参照元の明示
RAGモードで回答する際、どの資料のどのページを参照したかを表示。回答の信頼性を担保します。

### 3. 会話の永続化
Firebase Firestoreを使用し、会話履歴をクラウドに保存。ブラウザを閉じても履歴が残ります。

### 4. デモ用自動リセット
cronジョブで毎日自動リセット。常にクリーンなデモ環境を維持できます。

---

## 🚀 セットアップ

### 1. リポジトリをクローン

```bash
git clone https://github.com/YOUR_USERNAME/Chat_bot.git
cd Chat_bot
```

### 2. 仮想環境を作成

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
```

### 3. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数を設定

```bash
# .envファイルを作成
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

### 5. Firebase設定

Firebase Consoleからサービスアカウントキーをダウンロードし、`firebase-key.json`として配置

### 6. アプリを起動

```bash
streamlit run main.py
```

---

## 📸 スクリーンショット

（ここにアプリのスクリーンショットを追加）

---

## 🎯 今後の改善予定

- [ ] SINR（Sentence-BERT）による検索精度向上
- [ ] Streamlit Community Cloudへのデプロイ
- [ ] 複数ユーザー対応

---

## 👩‍💻 開発者

**さくら**

金融事務からのキャリアチェンジを目指し、AI/LLM技術を学習中。
このプロジェクトは、実務で使えるRAGシステムの構築を通じて、最新のAI技術を習得することを目的としています。

---

## 📄 ライセンス

MIT License
