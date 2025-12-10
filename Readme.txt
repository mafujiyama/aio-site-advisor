【AIOマルチエージェントでサイト構造を分析】

1. 全体アーキテクチャ（概念図）
前提：
　バックエンド：Python + LangGraph（マルチエージェントの実行）
　API層：FastAPI
　ユースケース：キーワードを渡すと、
　上位10サイトを取得 → 構造分析 → 競合比較 → 提案書・記事案・構造化データを返す

・KeywordPlanner ノード
　「どのキーワードをやるかだけ考える SEO ストラテジスト」
・SERP ノード
　「検索結果を取得するだけのリサーチャー（API＋ロジック）」
・Parser ノード
　「HTMLを構造化するテクニカルアナリスト」
・Analyzer ノード
　「構造を比較してスコアリングするアナリスト」
・Strategist ノード
　「提案書にまとめるビジネスコンサル」
・Content / Schema ノード
　「記事を書くライター」「構造化データを書くマークアップ担当」


 [Client(Web UI / CLI)]
        |
        v
   [FastAPI API層]
        |
        v
 ┌─────────────────────┐
 │    Orchestrator     │ ← LangGraphで実装
 │  (Workflow/Graph)   │
 └─────────────────────┘
        |
        v
 [Agent K: キーワード設計エージェント] 
        |
        v
  優先キーワード群 (keyword_plan)
        |
        |  (for each keyword)
        v
   |      |        |        |         |          |
   v      v        v        v         v          v
[Agent] [Agent]  [Agent]  [Agent]   [Agent]    [Agent]
 SERP   Parser   Analyzer Strategist Content   Schema
取得    構造化   競合比較   提案化     記事生成   構造化データ

2. ディレクトリ構成（MVP用）
リポジトリ名の例：aio-site-advisor

aio-site-advisor/
├── app/
│   ├── main.py               # FastAPI エントリポイント
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py         # /analyze などのエンドポイント定義
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py          # LangGraphの状態定義（キーワード、結果など）
│   │   └── workflow.py       # Orchestrator：ノードとフロー定義
│   └── config.py             # 共通設定（APIキー、SERPクライアント設定など）
│
├── agents/
│   ├── __init__.py
│   ├── serp_agent.py         # Agent1: 上位10件取得 + メタ情報
│   ├── parser_agent.py       # Agent2: HTML → 構造データ化
│   ├── analyzer_agent.py     # Agent3: 競合比較・スコアリング
│   ├── strategist_agent.py   # Agent4: 提案書ドラフト生成
│   ├── content_agent.py      # Agent5: 記事構成/本文ドラフト
│   └── schema_agent.py       # Agent6: 構造化データ(JSON-LD)生成
│
├── services/
│   ├── __init__.py
│   ├── serp_client.py        # Google/SerpAPI/Bing等への検索クライアント
│   ├── crawler.py            # HTML取得（requests/Playwright等）
│   ├── html_parser.py        # BeautifulSoup等での構造抽出
│   ├── seo_metrics.py        # キーワード出現率、タイトル文字数などの指標計算
│   └── report_builder.py     # 提案書用のMarkdown/JSON構造を組み立て
│
├── models/
│   ├── __init__.py
│   ├── serp_models.py        # 検索結果・サイト構造データ用のPydanticモデル
│   ├── analysis_models.py    # スコア・ギャップ分析結果のモデル
│   └── report_models.py      # 提案書・記事ブリーフ・構造化データのモデル
│
├── data/
│   ├── tmp/                  # 一時ファイル・キャッシュ
│   └── reports/              # 出力したレポート(Markdown/JSONなど)
│
├── config/
│   ├── settings.example.yaml # 環境設定サンプル（SERP APIキーなど）
│   └── keywords_sample.txt   # サンプルキーワード一覧（テスト用）
│
├── tests/
│   ├── __init__.py
│   ├── test_serp_agent.py
│   ├── test_parser_agent.py
│   ├── test_analyzer_agent.py
│   ├── test_content_agent.py
│   └── test_schema_agent.py
│
├── scripts/
│   ├── run_local.sh          # ローカル起動用（uvicorn + 簡易テスト）
│   └── example_request.http  # VSCode用のサンプルリクエスト
│
├── docker/
│   ├── Dockerfile            # アプリ用Dockerfile（必要なら）
│   └── docker-compose.yml    # Redisなどとまとめて起動する場合
│
├── .env.example              # OPENAI_API_KEYなどの環境変数サンプル
├── pyproject.toml or requirements.txt
└── README.md


3. 各レイヤーの役割イメージ
app/
・app/main.py
　　FastAPIアプリを立ち上げ
　　POST /analyze でキーワードと対象サイトURLを受け取り、LangGraphのワークフローを実行
　　app/graph/workflow.py
　　ここに「マルチエージェントのフロー」を集約
　　例：
　　　ノード node_serp → node_parse → node_analyze → node_strategist → node_content → node_schema
　　　app/graph/state.py
　　　LangGraphのStateクラス（キーワード、SERP結果、構造データ、分析結果、提案書、記事案、構造化データ…）を定義
agents/
　　それぞれ「LLMのプロンプト + 必要なツール呼び出し」に集中させるイメージです。
　　　例：agents/analyzer_agent.py の役割
　　　入力：
　　　　フィールド例：sites_structures（上位10サイト分の構造データ）、target_site_structure（自社）
　　　処理：
　　　　services.seo_metrics を使って数値指標（タイトル文字数、キーワード比率など）を計算
　　　　LLMで「どこが弱く、どこを真似すべきか」を自然言語で整理する
　　　出力：
　　　　AnalysisResult（スコア表＋ギャップコメント＋改善ポイント）
services/
　　・serp_client.py
　　　　SerpAPI / カスタム検索APIの呼び出しロジックだけをベタっと書く場所
　　　crawler.py
　　　　HTML取得（User-Agent、タイムアウトなどもここ）
　　・html_parser.py
　　　　BeautifulSoupなどで
　　　　　　<title> / <meta> / h1~h3
　　　　　　パンくず
　　　　　　本文本文の抽出
　　・seo_metrics.py
　　　　「キーワード出現率」「見出しカバレッジ」「文字数」などの計算ロジック
　　・report_builder.py
　　　　AnalysisResult から提案書の章立て・Markdown整形などを一手に引き受ける
　　・models/
　　　　API入出力、LangGraph state、各エージェント間のデータ受け渡しを型で固定しておくと、
　　　　プロンプトがブレにくい
　　　　テストしやすいので、ここはしっかり切っておくのがオススメです。



■実行手順
Windows
1.プロジェクトフォルダに移動
cd C:\Users\masaki.fujiyama\Desktop\aio-site-advisor-main


2. 仮想環境を作成※初回のみ
py -m venv venv


3. 稼働環境を有効化
py -m venv venv
　成功すると
　(venv) C:\Users\masaki.fujiyama\Desktop\aio-site-advisor-main>

4. パッケージインストール※初回のみ
pip install -r requirements.txt

5. アプリ起動
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
8000ポートだと不正アクセスとみなされる為、8001で起動。

6. Swaggerを開く
http://127.0.0.1:8001/docs


🔳実行手順
mac
1. プロジェクトフォルダに移動
cd ~/Desktop/ai_app/aio-site-advisor

2. 仮想環境の作成※初回のみ
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

2. 仮想環境を有効化
source .venv/bin/activate

3. FastAPIアプリを起動
uvicorn app.main:app --reload --port 8000

4. Swaggerを開く
http://localhost:8000/docs


macのセッティング
pip install pydantic-settings



api/analyze-lgの内容
plannerエージェントがキーワードのプランニングを行う。
「検索行動パターン + 製造業サイトのSEO」で自然なキーワード群を生成する
       1. Know（知りたい）/ Informational Intent
       2. Compare（比較したい）/ Commercial Investigation
       3. Buy（買いたい）/ Transactional Intent
       4. Navigational（特定の場所に行きたい）/ Navigational Intent

検索キーワードのpriorityは以下のような観点から重み付けをしている
       ① 検索ボリュームの高さが予想されるか
       ② コンバージョンへ近いか
       ③ BtoB製造業における重要性
       ④ コンテンツ施策の優先度

検索キーワードのreason(理由)はなぜそのキーワードが必要なのかを記載している


| No | 項目       | 意味                            | どう生成されているか           　|
| -- | -------- | ----------------------------- | ----------------------- 　　　　　|
| ①  | keyword群 | seed_keyword から派生する重要キーワード10件 | LLM or ルールベース     |
| ②  | intent   | ユーザーの検索目的分類            | Google検索意図 × 製造業向け分類    |
| ③  | category | intentに応じてカテゴリ分類        | KNOW→基礎/設計、COMPARE→比較など 　|
| ④  | priority | SEO施策の優先度（1〜5）           | LLMスコア or ルールベース値       |
| ⑤  | reason   | なぜそのキーワードが必要か         | LLMまたは固定テンプレ            　|






