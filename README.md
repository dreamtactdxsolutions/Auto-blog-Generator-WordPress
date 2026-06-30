# 🌴 宮古島レンタカー ブログ記事自動生成＆投稿システム

このシステムは、Googleの最新AI「Gemini API」を使って、宮古島に特化した魅力的なブログ記事を自動で生成し、WordPressへ下書き保存するPythonプログラムです。

**新機能: Search Console 連動 + CSV スケジューラー** 🎉
- 📅 **CSV基づく投稿スケジューラー** - 複数記事を自動投稿
- 🔍 **Google Search Console 連動** - 低掲載順位キーワード自動抽出
- 📊 **Streamlit ダッシュボード** - 管理画面で一元管理

---

## 🛠️ 事前準備ステップ

プログラムを動かすために、以下の順序で設定を行ってください。

### Step 1: 必要なライブラリのインストール
ターミナル（Mac）またはコマンドプロンプト（Windows）を開き、このフォルダに移動して以下のコマンドを実行します。
```bash
pip install -r requirements.txt
```

### Step 2: 複数のAPIキー・パスワードの取得

#### ① Gemini APIキー（無料）
1. [Google AI Studio (Gemini APIキー取得サイト)](https://aistudio.google.com/) にアクセスします。
2. Googleアカウントでサインインし、**「Get API key（APIキーを取得）」**ボタンをクリックします。
3. 画面の指示に従ってキーを生成し、表示された長いアルファベットと数字のキー（例：`AIzaSy...`）をコピーしておきます。

#### ② WordPress アプリケーションパスワード
1. ご自身のWordPressの管理画面（ダッシュボード）にログインします。
2. 左メニューから **「ユーザー」 ➔ 「プロフィール」**（または「個人設定」）を開きます。
3. 画面の下の方までスクロールし、**「アプリケーションパスワード」**という項目を探します。
4. **「新しいアプリケーションパスワード名」**の欄に、適当な名前（例: `blog-auto-app`）を入力し、**「新しいアプリケーションパスワードを追加」**ボタンをクリックします。
5. 画面に一度だけ表示される**4文字ごとに区切られたパスワード**（例：`xxxx xxxx xxxx xxxx xxxx`）を厳重にコピーします。
   *(※通常のログインパスワードとは異なります。安全のためにこちらをプログラム接続用に使用します)*

#### ③ Unsplash APIキー（オプション・無料：画像ネット自動取得用）
1. [Unsplash Developers](https://unsplash.com/developers) にアクセスし、ログイン（または無料登録）します。
2. 画面上部の **「Your Apps」** ➔ **「New Application」** をクリックします。
3. 利用規約に同意し、適当なアプリ名（例: `MiyakoBlogApp`）を入力して「Create Application」をクリックします。
4. アプリ詳細画面を少し下へスクロールし、**「Access Key」**（長い文字列）をコピーします。

#### ④ Google Search Console 認証キー（オプション：低掲載順位キーワード自動抽出用）
1. [Google Cloud Console](https://console.cloud.google.com/) にアクセスします。
2. 新しいプロジェクトを作成します。
3. **Web Masters API** を有効化します。
4. **サービスアカウント**を作成し、JSON形式の認証キーをダウンロードします。
5. [Google Search Console](https://search.google.com/search-console) で対象サイトを追加します。
6. サービスアカウントメールを**オーナー権限**でサイトに追加します。

---

### Step 3: 設定ファイル（`.env`）の編集
1. このフォルダ内にある `.env` ファイルを、メモ帳などのテキストエディタで開きます。
2. コピーした情報をそれぞれ書き換えて上書き保存します。

```env
# Gemini APIキー
GEMINI_API_KEY=ここにコピーしたGeminiのAPIキーを入力

# WordPress接続設定
WP_URL=https://miyakojima-rentacar.net/article
WP_USERNAME=yamazakikensetsu20010401
WP_PASSWORD=ここにコピーしたアプリケーションパスワード

# Unsplash APIキー（画像自動取得用：任意）
# 空白のままにしておくと、画像自動取得は行われません
UNSPLASH_ACCESS_KEY=ここにコピーしたUnsplashのAccess Keyを入力

# Google Maps APIキー（オプション：スポット写真自動取得用）
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
```

---

### Step 4: アイキャッチ画像の準備（ハイブリッド仕様）
1. 本プログラムを実行すると、自動的にフォルダ内に `images` というフォルダが作成されます（ない場合は自分で作成しても構いません）。
2. **優先（ローカル実写写真）：** 
   `images` フォルダの中に宮古島やレンタカーの実写写真を保存しておくと、システムは最優先でこの中から1枚をアイキャッチ画像に設定します。
3. **自動（インターネット補完）：** 
   `images` フォルダが空で、かつ `.env` に `UNSPLASH_ACCESS_KEY` が設定されている場合、システムが記事のテーマ（例: 絶品グルメ ➔ `mango dessert` など）に応じて、Unsplashから自動で画像をダウンロードして設定します。
   *(※画像がなく、キーも未設定の場合は、画像なしで記事が下書き保存されます)*

---

## 🚀 実行方法

### 📍 基本的な使い方

準備ができたら、ターミナルで以下のコマンドを実行します。

#### ① ランダムにキーワードを選んで記事を投稿する
```bash
python main.py
```
`keywords.json` のリストから自動で1つテーマが選ばれ、記事生成からWordPressへの下書き投稿までが一括で実行されます。

#### ② 特定のキーワードを指定して投稿する
`keywords.json` は上から順に `0, 1, 2, 3...` と番号が割り振られています。特定のテーマを強制的に書きたい場合は、コマンドの最後に番号をつけます。

```bash
# 例: 3番目のテーマ（ビーチと駐車場情報）で記事を書く場合
python main.py 3
```

---

## 🆕 新機能: CSVスケジューラー

複数の記事を日時指定で自動投稿できます。

### 使い方1: スケジューラー起動（毎日自動実行）

```bash
python scheduler.py --csv schedule.csv --mode schedule
```

指定時刻に自動で記事を生成・投稿します。**Ctrl+C で終了します**

#### 出力例：
```
================================================================================
📅 スケジュール一覧
================================================================================

[1] ファミリー向けレンタカー選び方ガイド
    キーワード: 宮古島 レンタカー 家族
    関連ワード: 子連れ, 安心ドライブ, チャイルドシート
    実行日時: 2026-07-15 09:00
    ステータス: pending

================================================================================
🕐 スケジューラーを起動中...
================================================================================
🟢 スケジューラーが起動しました。Ctrl+C で終了します。
```

### 使い方2: 全タスク即座実行（テスト用）

```bash
python scheduler.py --csv schedule.csv --mode run-all
```

`schedule.csv` に定義された全タスクを順番に実行します。

### 使い方3: 単一タスク実行

```bash
python scheduler.py --csv schedule.csv --mode run-one --task-index 0
```

指定したインデックス番号のタスクのみ実行します（0から始まります）

---

## 🔍 新機能: Google Search Console 連動

低掲載順位（20～100位）のキーワードを自動抽出し、改善記事のスケジュールを生成します。

### キーワード自動抽出 & 改善スケジュール生成

```bash
python search_console_integration.py \
  --credentials /path/to/service_account_key.json \
  --site-url https://miyakojima-rentacar.net/ \
  --min-position 20 \
  --max-position 100 \
  --days-back 30 \
  --output schedule_sc.csv
```

**オプション説明：**
- `--credentials`: Google Cloud サービスアカウント JSON キーのパス
- `--site-url`: 対象サイトの URL
- `--min-position`: 掲載順位の下限（デフォルト: 20位）
- `--max-position`: 掲載順位の上限（デフォルト: 100位）
- `--days-back`: 過去何日間を対象とするか（デフォルト: 30日）
- `--output`: 出力CSVファイルのパス

#### 出力例：
```
✅ Google Search Console に認証しました
✅ 23 件の低掲載順位キーワードを抽出しました

====================================================================================================
📊 Search Console キーワードレポート
====================================================================================================
キーワード                         順位 インプレッション クリック    CTR
----------------------------------------------------------------------------------------------------
宮古島 ドライブコース              45.2          234        12   5.13%
宮古島 グルメ おすすめ              78.5          156         8   5.13%
宮古島 レンタカー 安い              92.1           89         3   3.37%
...
====================================================================================================

✅ 改善スケジュールを生成しました: schedule_sc.csv
   23 件のタスクを出力しました
```

---

## 📊 新機能: 管理ダッシュボード（Streamlit）

ブラウザベースの管理画面で全機能を操作できます。

```bash
streamlit run dashboard.py
```

ブラウザで `http://localhost:8501` が自動で開きます。

### ダッシュボード機能：

**📅 スケジュール管理タブ**
- ✅ スケジュール一覧確認
- 🚀 全タスク即座実行
- ▶️ 単一タスク実行
- 📊 ステータス表示
- 💾 CSVダウンロード

**🔍 Search Console タブ**
- 🔎 低掲載順位キーワード抽出
- 📈 キーワードレポート表示
- 📅 改善スケジュール自動生成
- 💾 スケジュールダウンロード

**📊 統計情報タブ**
- 📋 総タスク数
- ⏳ 待機中タスク数
- ✅ 完了タスク数
- ❌ 失敗タスク数
- 📈 ステータス分布グラフ

**📚 使用方法タブ**
- 📖 全機能の詳細ドキュメント
- 🔐 認証設定ガイド
- ⚠️ トラブルシューティング

---

## 📋 schedule.csv ファイル形式

スケジューラーで使用するCSVファイルの形式です：

| カラム名 | 説明 | 例 |
|---------|------|-----|
| `keyword` | 記事のメインキーワード | `宮古島 レンタカー 家族` |
| `theme` | 記事のテーマ・タイトル | `ファミリー向けレンタカー選び方ガイド` |
| `sub_keywords` | 関連キーワード（パイプ\|で区切る） | `子連れ\|安心ドライブ\|チャイルドシート` |
| `publish_date` | 投稿日（YYYY-MM-DD形式） | `2026-07-15` |
| `publish_time` | 投稿時刻（HH:MM形式） | `09:00` |
| `execution_mode` | 実行モード（通常は`schedule`） | `schedule` |

**例：**
```csv
keyword,theme,sub_keywords,publish_date,publish_time,execution_mode
宮古島 レンタカー 家族,ファミリー向けレンタカー選び方ガイド,子連れ|安心ドライブ|チャイルドシート,2026-07-15,09:00,schedule
宮古島 ドライブ 穴場,地元民が愛する穴場ドライブスポット5選,穴場スポット|ドライブコース|絶景,2026-07-16,14:00,schedule
宮古島 グルメ 海鮮,最高に新鮮な海鮮グルメ完全ガイド,海鮮丼|マグロ|現地レストラン,2026-07-17,10:00,schedule
```

---

## 📝 投稿された記事の確認

投稿が完了すると、ターミナルに以下のようなURLが表示されます。
```
🔗 プレビュー/編集用URL: https://miyakojima-rentacar.net/wp-admin/post.php?post=xxxx&action=edit
```

WordPressの管理画面にログインした状態でこのURLを開くか、「投稿一覧」の「下書き」を確認してください。AIが生成した魅力的な記事が綺麗に流込まれています。

問題がなければ、お好きな画像を本文中に追加するなどの最終調整を行い、「公開」ボタンを押してブログを配信してください！

---

## 🎯 ワークフロー例

### シナリオ1: 毎日自動投稿

```bash
# ターミナル1: スケジューラー起動
python scheduler.py --csv schedule.csv --mode schedule

# ターミナルはそのまま実行し続ける
# 指定時刻に自動で記事が生成・投稿されます
```

### シナリオ2: Search Consoleデータから改善記事を自動生成

```bash
# Step 1: 低掲載順位キーワードを抽出 & スケジュール生成
python search_console_integration.py \
  --credentials ./google_service_account.json \
  --site-url https://miyakojima-rentacar.net/ \
  --output schedule_improvements.csv

# Step 2: 生成されたschedule_improvements.csvで即座実行
python scheduler.py --csv schedule_improvements.csv --mode run-all

# または、スケジューラーで定期実行
python scheduler.py --csv schedule_improvements.csv --mode schedule
```

### シナリオ3: 管理画面で一元管理

```bash
# ダッシュボードを開く
streamlit run dashboard.py

# ブラウザで以下が可能：
# - スケジュール確認
# - テスト実行
# - Search Console連動
# - 統計確認
# - CSVダウンロード
```

### シナリオ4: 継続的な改善ループ

```bash
# 毎週日曜日に実行するスクリプト（cron/タスクスケジューラ）
#!/bin/bash
cd /path/to/project

# 最新の低掲載順位キーワードを抽出
python search_console_integration.py \
  --credentials ./google_service_account.json \
  --site-url https://miyakojima-rentacar.net/ \
  --days-back 7 \
  --output schedule_weekly_improvements.csv

# 生成されたスケジュールを実行
python scheduler.py --csv schedule_weekly_improvements.csv --mode run-all
```

---

## ⚠️ トラブルシューティング

### 「schedule ライブラリが見つかりません」エラー
```bash
pip install schedule
```

### 「Google Auth ライブラリが見つかりません」エラー
```bash
pip install google-auth-oauthlib google-api-python-client
```

### 「Streamlit が見つかりません」エラー
```bash
pip install streamlit pandas
```

### Search Console 認証エラー
- サービスアカウントメールが Search Console で**オーナー権限**として追加されているか確認
- JSON キーのパスが正しいか確認
- Google Web Masters API が有効化されているか確認

### スケジューラーが実行されない
- 指定時刻が正しいか確認（24時間形式 HH:MM）
- schedule.csv のフォーマットが正しいか確認
- ターミナルがバックグラウンド実行しているか確認
- `.env` ファイルに全ての必須キーが設定されているか確認

### 記事生成に失敗する
- Gemini API キーが正しく設定されているか確認
- API 呼び出し回数の制限に達していないか確認
- キーワード/テーマが正しく設定されているか確認

### WordPress 連携エラー
- WordPress REST API が有効化されているか確認
- アプリケーションパスワードが正しいか確認
- WordPress URL が正しいか確認
- 管理者権限があるか確認

---

## 📚 主要ファイル一覧

| ファイル | 説明 |
|---------|------|
| `main.py` | メイン実行ファイル（単一記事生成・投稿） |
| `scheduler.py` | **新機能** CSVベースのスケジューラー |
| `search_console_integration.py` | **新機能** Search Console API統合 |
| `dashboard.py` | **新機能** Streamlit 管理ダッシュボード |
| `schedule.csv` | **新機能** スケジュール定義ファイル |
| `generator.py` | Gemini API を使った記事生成 |
| `wordpress.py` | WordPress REST API 統合 |
| `image_fetcher.py` | Unsplash から画像取得 |
| `config.py` | 環境変数設定 |
| `keywords.json` | 記事キーワード定義 |

---

## 📞 サポート

問題が発生した場合は、以下をご確認ください：

1. ✅ `.env` ファイルに全ての必須キーが設定されているか
2. ✅ `pip install -r requirements.txt` で全ライブラリがインストールされているか
3. ✅ WordPress のアプリケーションパスワードが正しく設定されているか
4. ✅ CSV ファイルのフォーマットが正しいか（エンコーディングは UTF-8）
5. ✅ ネットワーク接続が安定しているか

**ご質問やバグ報告は GitHub Issues でお知らせください！**

---

## 🤝 貢献

改善提案やバグ報告は大歓迎です。Pull Request もお待ちしています！

---

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

---

## 🔄 更新履歴

### v2.0.0 (2026-07-01)
- 🎉 CSV スケジューラー機能追加
- 🎉 Google Search Console 連動機能追加
- 🎉 Streamlit 管理ダッシュボード追加
- 📚 ドキュメント大幅拡充

### v1.0.0 (初版)
- ✅ 基本的な記事生成・投稿機能
- ✅ 画像自動取得機能
- ✅ WordPress 連携

---

**🎉 このシステムで、ブログ運営を完全自動化しましょう！**

何かご不明な点がありましたら、お気軽にお問い合わせください。
