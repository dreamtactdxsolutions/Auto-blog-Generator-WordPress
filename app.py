import os
import sys
import streamlit as st
from PIL import Image

# プロジェクト内の設定・生成モジュールをインポート
import config
from generator import generate_blog_article
from image_fetcher import download_image_from_unsplash
from image_processor import create_title_banner
from wordpress import (
    get_random_image_from_folder, 
    upload_image_to_wordpress, 
    upload_image_to_wordpress_detailed,
    post_article_to_wordpress,
    get_existing_posts_detailed,
    get_or_create_wp_tags
)
from google_maps_fetcher import download_photo_for_spot
from main import (
    select_related_posts,
    build_cta_html,
    process_content_headings,
    build_intro_block,
    insert_intro_block,
    insert_spot_images_to_content
)

# ページ基本設定
st.set_page_config(
    page_title="宮古島レンタカー ブログ自動生成APP",
    page_icon="🌴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 宮古島をイメージしたモダンなカスタムスタイル
st.markdown("""
<style>
    /* メインの背景 */
    .stApp {
        background-color: #f7fafc;
    }
    /* ヘッダーコンテナ */
    .header-banner {
        background: linear-gradient(135deg, #35a7c9 0%, #007791 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    .header-banner h1 {
        font-size: 2.2rem;
        margin: 0;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .header-banner p {
        font-size: 1rem;
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    /* カード風のセクション装飾 */
    .css-1r6g82t {
        background-color: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    /* ボタンのカスタム */
    div.stButton > button:first-child {
        background-color: #35a7c9;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 2rem;
        font-weight: bold;
        font-size: 1rem;
        transition: all 0.3s ease;
        width: 100%;
    }
    div.stButton > button:first-child:hover {
        background-color: #007791;
        border: none;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

# ヘッダー表示
st.markdown("""
<div class="header-banner">
    <h1>🌴 宮古島レンタカー ブログ記事自動生成ツール 🌴</h1>
    <p>AIによる高品質な記事執筆と、Googleマップの写真自動挿入、WordPressへの下書き保存を1クリックで行います</p>
</div>
""", unsafe_allow_html=True)

# .envの読み込み・保存用ヘルパー関数
def load_env_values():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    values = {}
    
    # 1. クラウド環境用に st.secrets から初期値を読み込みます
    try:
        import streamlit as st
        keys = [
            "GEMINI_API_KEY", "WP_URL", "WP_USERNAME", "WP_PASSWORD", 
            "UNSPLASH_ACCESS_KEY", "GOOGLE_MAPS_API_KEY", "ANTHROPIC_API_KEY",
            "GOOGLE_SERVICE_ACCOUNT_JSON", "SEARCH_CONSOLE_PROPERTY_URL"
        ]
        for k in keys:
            if k in st.secrets:
                values[k] = st.secrets[k]
    except Exception:
        pass
        
    # 2. ローカルの .env ファイルがあれば上書きします
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k_clean = k.strip()
                    # すでに st.secrets からロード済みのキーは、.env の値で上書きしない（本番のSecretsを最優先）
                    if k_clean in values and values[k_clean]:
                        continue
                    
                    # JSON文字列のデコード対応 (エスケープされた改行などを戻す)
                    val = v.strip()
                    if val.startswith('"') and val.endswith('"'):
                        val = val[1:-1].replace('\\"', '"')
                        # ダブルクォーテーションで分割し、外側（偶数セグメント）の \\n のみ改行コードにする
                        parts = val.split('"')
                        for i in range(len(parts)):
                            if i % 2 == 0:
                                parts[i] = parts[i].replace('\\n', '\n')
                        val = '"'.join(parts)
                    values[k_clean] = val
    return values

def save_env_values(new_values):
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    lines = []
    updated_keys = set()
    
    # 保存用の値をクォーティング処理
    formatted_values = {}
    for k, v in new_values.items():
        val = v.strip()
        # 改行やJSONを含むものはダブルクォーテーションで囲み、改行をエスケープ
        if "\n" in val or "{" in val:
            escaped_val = val.replace('"', '\\"').replace('\n', '\\n')
            formatted_values[k] = f'"{escaped_val}"'
        else:
            formatted_values[k] = val

    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k, v = stripped.split("=", 1)
                    k = k.strip()
                    if k in formatted_values:
                        lines.append(f"{k}={formatted_values[k]}\n")
                        updated_keys.add(k)
                    else:
                        lines.append(line)
                else:
                    lines.append(line)
    
    # 既存の .env に無かったキーを追加
    for k, v in formatted_values.items():
        if k not in updated_keys:
            lines.append(f"{k}={v}\n")
            
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

# タブ機能で画面を整理
tab1, tab_improve, tab2, tab3, tab4 = st.tabs(["📝 記事生成", "📈 記事改善（Search Console）", "📷 スポット画像登録", "⚙️ システム設定", "📖 取扱説明書"])

                        
with tab1:
    st.markdown("### ✍️ 記事の作成モード")
    create_mode = st.radio(
        "記事の作成方法を選択してください",
        ["🎯 テーマ指定モード (キーワードやタイトルを自分で指定)", "🔥 トレンドリサーチモード (最近の流行・話題を自動検索して執筆)", "📅 CSV一括予約投稿モード (CSVファイルから複数記事を作成・予約投稿)"],
        horizontal=True
    )
    
    use_trend_research = False
    use_csv_mode = False
    trend_genre = "すべて"
    theme = None
    keyword = None
    sub_keywords = []
    uploaded_csv = None

    if "トレンドリサーチ" in create_mode:
        use_trend_research = True
        st.info("💡 AIが2026年現在の宮古島に関する新店舗のオープン情報、話題のイベント、観光トレンドなどをWeb上から自動リサーチし、最適なテーマを決めて執筆します。")
        trend_genre = st.selectbox("リサーチしたい情報のジャンルを選択してください", ["すべて", "グルメ・カフェ・新店舗", "観光スポット・イベント・フェスティバル", "アクティビティ・体験"])
    elif "CSV一括予約" in create_mode:
        use_csv_mode = True
        st.info("💡 キーワードと日付（投稿予定日時）を記述したCSVをアップロードすることで、未来の日時での「予約投稿（WordPressの Scheduled / Future 状態）」として一括で記事を生成・投稿します。")
        
        # テンプレートダウンロード
        template_path = os.path.join(os.path.dirname(__file__), "csv_template.csv")
        if os.path.exists(template_path):
            with open(template_path, "rb") as f:
                st.download_button(
                    label="📥 CSVテンプレートをダウンロード",
                    data=f,
                    file_name="blog_csv_template.csv",
                    mime="text/csv"
                )
        uploaded_csv = st.file_uploader("予約リストCSVファイルをアップロードしてください", type=["csv"])
    else:
        st.markdown("### ✍️ 記事の作成条件")
        col_input1, col_input2 = st.columns(2)
        
        with col_input1:
            theme = st.text_input("記事のタイトル（テーマ名）", placeholder="例：宮古島をレンタカーで巡る！1日王道絶景ドライブモデルコース")
            keyword = st.text_input("主要検索キーワード", placeholder="例：宮古島 ドライブコース")
        with col_input2:
            sub_keywords_input = st.text_area("関連キーワード (カンマ `,` または改行で区切ってください)", placeholder="例：伊良部大橋, 東平安名崎, レンタカー, ドライブ")
            sub_keywords = [k.strip() for k in sub_keywords_input.replace("\n", ",").split(",") if k.strip()]
            
    st.markdown("---")
    st.markdown("### ⚙️ オプション設定")
    
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        use_maps_photos = st.checkbox("Googleマップからスポットの絶景写真を自動取得し、記事中に挿入する", value=True, help="Places APIを使って観光地の写真を検索し、撮影者へのクレジットと共に記事内に自動配置します。")
        use_unsplash = st.checkbox("アイキャッチ画像をUnsplashから自動取得する（ローカル画像が不足している場合のみ）", value=True, help="imagesフォルダに実写画像が無い場合、自動で海の画像を検索・ダウンロードしてバナーに加工します。")
    with col_opt2:
        selected_model = st.selectbox("使用するAIモデル", ["Gemini 3.5 Flash", "Claude Sonnet 4.6"], index=0, help="ブログの執筆を行うAIモデルを選択します。Claudeを使用する場合はシステム設定でClaude用のAPIキーを設定してください。")
        ai_model = "claude" if "Claude" in selected_model else "gemini"
        
        if use_csv_mode:
            st.caption("※CSV内の post_date に日時が記述されている場合、ステータスは自動的に「予約投稿 (future)」となります。空の場合は下書きで登録されます。")
            wp_status = "draft"
        else:
            post_status = st.selectbox("WordPressへの公開ステータス", ["下書き (draft) - 推奨", "公開 (publish)"], index=0, help="まずは下書きで登録し、確認したのちに公開するのが安全です。")
            wp_status = "draft" if "下書き" in post_status else "publish"
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 実行ボタンの表示切替
    btn_label = "🚀 一括生成・予約投稿を開始する" if use_csv_mode else "🚀 この内容で記事を自動生成してWordPressに保存する"
    
    if st.button(btn_label):
        # 設定チェック
        env_values = load_env_values()
        cur_gemini = env_values.get("GEMINI_API_KEY", "")
        cur_anthropic = env_values.get("ANTHROPIC_API_KEY", "")
        cur_wp_url = env_values.get("WP_URL", "")
        cur_wp_user = env_values.get("WP_USERNAME", "")
        cur_wp_pass = env_values.get("WP_PASSWORD", "")
        cur_maps_key = env_values.get("GOOGLE_MAPS_API_KEY", "")
        cur_unsplash_key = env_values.get("UNSPLASH_ACCESS_KEY", "")
        
        # 選択されたモデルに応じたキーのチェック
        active_api_key = cur_gemini if ai_model == "gemini" else cur_anthropic
        
        # トレンドリサーチかつClaudeの場合にGemini APIキーも必要であることをチェック
        has_required_keys = True
        if ai_model == "claude" and use_trend_research:
            if not cur_gemini or not cur_anthropic:
                has_required_keys = False
        else:
            if not active_api_key:
                has_required_keys = False
 
        if not has_required_keys or not cur_wp_url or not cur_wp_user or not cur_wp_pass:
            if ai_model == "claude" and use_trend_research:
                st.error("❌ 接続エラー: トレンドリサーチモードでClaudeを使用するには、Gemini APIキーとClaude APIキーの両方をシステム設定に入力してください。")
            else:
                st.error(f"❌ 接続エラー: 選択されたAIモデル（{selected_model}）のAPIキーまたはWordPress接続情報が入力されていません。設定を入力してから再実行してください。")
        elif use_csv_mode and not uploaded_csv:
            st.error("❌ 入力エラー: 予約リストのCSVファイルをアップロードしてください。")
        elif not use_csv_mode and not use_trend_research and (not theme or not keyword):
            st.error("❌ 入力エラー: テーマ指定モードでは、記事のタイトルと主要キーワードは必須です。入力してください。")
        else:
            # CSV一括処理モードの場合
            if use_csv_mode:
                import csv
                import io
                from main import generate_and_post_single_article
                
                try:
                    csv_data = uploaded_csv.getvalue().decode("utf-8-sig")
                    reader = csv.DictReader(io.StringIO(csv_data))
                    rows = list(reader)
                except Exception as e:
                    st.error(f"❌ CSVファイルの読み込みに失敗しました: {e}")
                    rows = []
                    
                if not rows:
                    st.error("❌ CSVデータが空、またはフォーマットが正しくありません。")
                else:
                    status_monitor = st.status("🎬 CSVから一括予約生成を実行中...", expanded=True)
                    success_count = 0
                    
                    for idx, row in enumerate(rows):
                        kw = row.get("keyword")
                        th = row.get("theme") or f"{kw}に関するおすすめ情報"
                        sub_kws_str = row.get("sub_keywords", "")
                        sub_kws = [k.strip() for k in sub_kws_str.replace("、", ",").split(",") if k.strip()]
                        p_date = row.get("post_date")
                        
                        if not kw:
                            status_monitor.write(f"⚠️ 行 {idx+1}: 主要キーワードが空のためスキップしました。")
                            continue
                            
                        status_monitor.update(label=f"🔄 処理中 ({idx+1}/{len(rows)}): {th}...", state="running")
                        try:
                            res_url = generate_and_post_single_article(
                                keyword=kw,
                                theme=th,
                                sub_keywords=sub_kws,
                                ai_model=ai_model,
                                wp_status="future" if p_date else "draft",
                                post_date=p_date
                            )
                            status_monitor.write(f"✅ 生成成功: [編集画面を開く]({res_url}) (公開予定: {p_date or '即時（下書き）'})")
                            success_count += 1
                        except Exception as e:
                            status_monitor.write(f"❌ 生成失敗 ({th}): {e}")
                            
                    status_monitor.update(label=f"🎉 一括処理が完了しました！ ({success_count} / {len(rows)} 件成功)", state="complete")
                    st.balloons()
            
            # 通常の記事生成モード（テーマ指定 or トレンドリサーチ）の場合
            else:
                # 処理ステータスモニター
                status_monitor = st.status("🎬 ブログ自動生成の実行準備をしています...", expanded=True)
                
                try:
                    # 1. 過去記事の取得
                    status_monitor.update(label="🔍 重複を防ぐため、WordPressから公開済み記事の一覧を取得中...", state="running")
                    existing_posts = get_existing_posts_detailed(
                        wp_url=cur_wp_url,
                        username=cur_wp_user,
                        app_password=cur_wp_pass
                    )
                    existing_titles = [post['title'] for post in existing_posts]
                    
                    # 2. 記事の生成
                    status_monitor.update(label=f"🤖 {selected_model}がブログ記事を執筆中...（数分かかる場合があります）", state="running")
                    blog_post = generate_blog_article(
                        api_key=active_api_key,
                        keyword=keyword,
                        theme=theme,
                        sub_keywords=sub_keywords,
                        existing_titles=existing_titles,
                        use_trend_research=use_trend_research,
                        trend_genre=trend_genre,
                        ai_model=ai_model
                    )
                    
                    generated_theme = blog_post.get("title", theme)
                    generated_keyword = blog_post.get("keyword", keyword)
                    generated_sub_keywords = blog_post.get("sub_keywords", sub_keywords)
                    
                    # 3. 関連記事選定
                    status_monitor.update(label="🔗 関連記事を自動選定しています...", state="running")
                    related_posts = select_related_posts(
                        current_title=generated_theme,
                        current_keyword=generated_keyword,
                        existing_posts=existing_posts
                    )
                    cta_html = build_cta_html(related_posts)
                    
                    # 4. 見出しのフォーマットと目次生成
                    status_monitor.update(label="📝 「この記事で分かること」BOXと目次を構成しています...", state="running")
                    summary_items = blog_post.get("summary_items", [])
                    processed_content, headings = process_content_headings(blog_post["content"])
                    
                    image_folder = os.path.join(os.path.dirname(__file__), "images")
                    if not os.path.exists(image_folder):
                        os.makedirs(image_folder)
                        
                    # 5. Googleマップ写真の自動取得
                    spots = blog_post.get("spots", [])
                    if spots and use_maps_photos and cur_maps_key:
                        status_monitor.update(label=f"🗺️  Googleマップから {len(spots)} 個のスポットの写真を探索・挿入中...", state="running")
                        processed_content = insert_spot_images_to_content(
                            content=processed_content,
                            spots=spots,
                            api_key=cur_maps_key,
                            save_dir=image_folder,
                            wp_url=cur_wp_url,
                            username=cur_wp_user,
                            app_password=cur_wp_pass
                        )
                        
                    intro_block = build_intro_block(summary_items, headings)
                    blog_post["content"] = insert_intro_block(processed_content, intro_block)
                    blog_post["content"] += cta_html
                    
                    # 6. アイキャッチ画像の準備
                    status_monitor.update(label="🖼️  アイキャッチバナー画像を生成しています...", state="running")
                    image_path = get_random_image_from_folder(image_folder)
                    
                    if not image_path and use_unsplash and cur_unsplash_key:
                        image_keyword = blog_post.get("image_keyword", "okinawa beach")
                        status_monitor.update(label=f"📸 ローカルに画像がないため、Unsplashから '{image_keyword}' の写真をダウンロード中...", state="running")
                        image_path = download_image_from_unsplash(
                            keyword=image_keyword,
                            access_key=cur_unsplash_key,
                            save_dir=image_folder
                        )
                        
                    featured_media_id = None
                    featured_media_url = None
                    banner_image = None
                    
                    if image_path:
                        status_monitor.update(label="🎨 画像にタイトルとサブタイトルを合成中...", state="running")
                        banner_path = os.path.join(image_folder, "processed_banner.jpg")
                        
                        banner_title = blog_post.get("banner_title", generated_theme)
                        banner_subtitle = blog_post.get("banner_subtitle")
                        
                        processed_image_path = create_title_banner(
                            image_path=image_path,
                            title=banner_title,
                            output_path=banner_path,
                            sub_title=banner_subtitle
                        )
                        
                        banner_image = Image.open(processed_image_path)
                        
                        status_monitor.update(label="📤 加工したアイキャッチ画像をWordPressにアップロード中...", state="running")
                        upload_res = upload_image_to_wordpress_detailed(
                            wp_url=cur_wp_url,
                            username=cur_wp_user,
                            app_password=cur_wp_pass,
                            image_path=processed_image_path
                        )
                        if upload_res:
                            featured_media_id = upload_res.get("id")
                            featured_media_url = upload_res.get("source_url")
                            
                    # 本文の最先頭にアイキャッチ画像バナーを挿入
                    if featured_media_url:
                        banner_html = f"""
<div style="text-align: center; margin-bottom: 30px;">
  <img src="{featured_media_url}" alt="{generated_theme}" style="width: 100%; max-width: 100%; border-radius: 12px; height: auto; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
</div>
"""
                        blog_post["content"] = banner_html + blog_post["content"]
                        
                    # 6.5 WordPressのタグ（ハッシュタグ）を取得・作成
                    status_monitor.update(label="🏷️ 記事内のスポット名やキーワードからタグを登録中...", state="running")
                    tag_names = list(set(spots + [generated_keyword])) # 重複排除
                    tag_ids = get_or_create_wp_tags(
                        wp_url=cur_wp_url,
                        username=cur_wp_user,
                        app_password=cur_wp_pass,
                        tag_names=tag_names
                    )
                    
                    # 7. WordPress投稿
                    status_monitor.update(label=f"📤 ブログ記事データをWordPressへ{'下書き' if wp_status == 'draft' else '公開'}投稿中...", state="running")
                    post_url = post_article_to_wordpress(
                        wp_url=cur_wp_url,
                        username=cur_wp_user,
                        app_password=cur_wp_pass,
                        title=generated_theme,
                        content=blog_post.get("content", ""),
                        excerpt=blog_post.get("meta_description", ""),
                        featured_media_id=featured_media_id,
                        tags=tag_ids,
                        status=wp_status
                    )
                    
                    # 完了！
                    status_monitor.update(label="🎉 すべての生成＆投稿プロセスが完了しました！", state="complete")
                    st.balloons()
                    
                    st.success("✨ ブログ記事の投稿に成功しました！")
                    
                    # 結果・プレビューセクションの表示
                    st.markdown(f"### 👉 [WordPressの投稿（編集画面）を開く]({post_url})")
                    
                    col_res1, col_res2 = st.columns([2, 3])
                    with col_res1:
                        if banner_image:
                            st.image(banner_image, caption="自動合成されたアイキャッチ画像バナー", use_container_width=True)
                    with col_res2:
                        st.markdown(f"**📝 生成タイトル:** {generated_theme}")
                        st.markdown(f"**🔍 メタディスクリプション（抜粋）:**\n{blog_post.get('meta_description', '')}")
                        st.markdown(f"**🏷️ 主要キーワード:** `{generated_keyword}`")
                        st.markdown(f"**🏷️ 関連キーワード:** `{', '.join(generated_sub_keywords) if isinstance(generated_sub_keywords, list) else generated_sub_keywords}`")
                        
                    st.markdown("---")
                    with st.expander("📄 生成された記事本文のHTMLプレビューを表示"):
                        # 簡易表示用のコンテナ
                        st.code(blog_post.get("content", ""), language="html")
                        
                except Exception as e:
                    status_monitor.update(label="❌ エラーにより生成処理が中断されました", state="error")
                    error_msg = str(e)
                    if "Gemini APIの利用制限" in error_msg:
                        st.error(error_msg)
                    else:
                        st.error(f"エラー内容: {e}")
                        st.info("システム設定に入力された情報が正しいか再度確認してください。")

with tab_improve:
    st.markdown("### 📈 Search Console 連携＆自動記事改善")
    st.caption("Google Search Consoleの掲載実績データに基づき、検索順位が低迷している（例: 10〜30位付近の）公開済み記事を自動でリライトします。狙うキーワードの検索意図を満たす情報を追加し、掲載順位を上げます。")
    
    # 接続確認 - st.secretsから直接読み取り、途中の加工処理による文字崩れを完全に防止
    sc_json_raw = None
    try:
        import streamlit as st_secrets_reader
        if "GOOGLE_SERVICE_ACCOUNT_JSON" in st_secrets_reader.secrets:
            sc_json_raw = st_secrets_reader.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
    except Exception:
        pass
    if not sc_json_raw:
        sc_json_raw = config.GOOGLE_SERVICE_ACCOUNT_JSON
    
    sc_prop = config.SEARCH_CONSOLE_PROPERTY_URL
    
    if not sc_json_raw or not sc_prop:
        st.info("⚠️ 連携するには、システム設定（⚙️タブ）で「Googleサービスアカウントキー (JSON)」および「Search Console プロパティURL」を設定してください。")
    else:
        st.write("#### 1. 過去30日間の掲載パフォーマンス分析")
        col_an1, col_an2 = st.columns([1, 3])
        with col_an1:
            days_range = st.slider("分析対象期間（日前）", min_value=7, max_value=90, value=30)
            min_imp = st.number_input("最小表示回数（期間中）", min_value=1, value=10)
        with col_an2:
            st.write("")
            st.write("")
            analyze_trigger = st.button("📊 Search Console データを取得して改善候補を分析")

        if "sc_analysis_results" not in st.session_state:
            st.session_state["sc_analysis_results"] = None

        if analyze_trigger:
            with st.spinner("🔍 Search Console APIに接続してデータを分析中..."):
                from search_console import get_search_console_service, fetch_performance_data, analyze_low_performing_pages
                service, err_msg = get_search_console_service(sc_json_raw)
                if not service:
                    st.error(f"❌ Google Search Console APIとの認証に失敗しました。サービスアカウントのJSONキーを確認してください。 (エラー詳細: {err_msg})")
                else:
                    raw_data = fetch_performance_data(service, sc_prop, days=days_range)
                    if not raw_data:
                        st.warning("⚠️ 掲載データが見つかりませんでした。プロパティURLが正しいか確認してください（例: trailing slashを揃える、ドメインプロパティの場合は `sc-domain:example.com`）。")
                    else:
                        suggestions = analyze_low_performing_pages(raw_data, min_impressions=min_imp)
                        st.session_state["sc_analysis_results"] = suggestions
                        
        suggestions = st.session_state["sc_analysis_results"]
        if suggestions:
            st.success(f"✅ 分析完了: 改善候補となる記事が {len(suggestions)} 件見つかりました。")
            
            # 推奨記事の選択リスト
            options = []
            for url, info in suggestions.items():
                options.append(f"📍 {url} (表示: {info['impressions']}回 / 順位: {info['avg_position']}位) ➔ 狙うクエリ: {', '.join(info['queries'])}")
                
            selected_option = st.selectbox("リライトを実行する記事を選択してください", options)
            
            if selected_option:
                # 選択されたURLとクエリの取得
                selected_idx = options.index(selected_option)
                target_url = list(suggestions.keys())[selected_idx]
                target_info = suggestions[target_url]
                
                st.markdown("##### 📌 改善対象の記事情報")
                col_sel1, col_sel2 = st.columns(2)
                with col_sel1:
                    st.write(f"**URL**: {target_url}")
                    st.write(f"**過去{days_range}日間の表示回数**: {target_info['impressions']} 回")
                    st.write(f"**平均表示順位**: {target_info['avg_position']} 位")
                with col_sel2:
                    st.write(f"**流入クエリ（狙うキーワード）**: {', '.join(target_info['queries'])}")
                
                st.write("---")
                st.write("#### 2. 自動改善（リライト）の実行設定")
                
                col_rew1, col_rew2 = st.columns(2)
                with col_rew1:
                    rewrite_model = st.selectbox("使用するAIモデル (リライト用)", ["Gemini 3.5 Flash", "Claude Sonnet 4.6"], index=0, key="rew_model")
                    rew_ai_model = "claude" if "Claude" in rewrite_model else "gemini"
                    
                    policy = st.radio("リライトした記事の保存方法", ["新しい下書き記事として別保存（推奨）", "既存の記事に直接上書き更新する"], index=0)
                    overwrite_wp = True if "直接上書き" in policy else False
                with col_rew2:
                    st.info("💡 元記事の構成やHTML見出しの流れを維持しながら、追加キーワードで検索する読者の疑問に答えるように情報を肉付けします。")
                
                # リライト実行
                if st.button("🚀 自動リライト（改善）を実行する"):
                    # WordPress 投稿IDの抽出
                    from search_console import extract_wp_post_id_from_url
                    from wordpress import get_article_content_detailed, update_article_in_wordpress
                    from generator import rewrite_blog_article
                    
                    post_id = extract_wp_post_id_from_url(target_url)
                    
                    if not post_id:
                        st.error("❌ エラー: URLからWordPressの投稿ID（数値）を自動抽出できませんでした。手動で記事IDを確認してください。")
                    else:
                        st.toast("🔄 WordPressから現在の記事データを取得中...")
                        env_values = load_env_values()
                        cur_wp_url = env_values.get("WP_URL", "")
                        cur_wp_user = env_values.get("WP_USERNAME", "")
                        cur_wp_pass = env_values.get("WP_PASSWORD", "")
                        
                        # WordPress接続テストとデバッグ情報の取得
                        import requests
                        from requests.auth import HTTPBasicAuth
                        debug_wp_info = "未解析"
                        try:
                            test_url = f"{cur_wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
                            res = requests.get(
                                test_url,
                                auth=HTTPBasicAuth(cur_wp_user, cur_wp_pass),
                                timeout=10
                            )
                            masked_pass = cur_wp_pass[:3] + "..." + cur_wp_pass[-3:] if len(cur_wp_pass) > 6 else "***"
                            debug_wp_info = f"接続先: {test_url} / ユーザー: {cur_wp_user} / パスワード: {masked_pass} (文字数: {len(cur_wp_pass)}) / ステータスコード: {res.status_code} / レスポンス: {res.text[:150]}"
                        except Exception as we:
                            debug_wp_info = f"リクエスト失敗: {we}"

                        original_post = get_article_content_detailed(cur_wp_url, cur_wp_user, cur_wp_pass, post_id)
                        
                        if not original_post:
                            st.error(f"❌ エラー: WordPressから記事（ID: {post_id}）を取得できませんでした。ログイン情報やURLを確認してください。\n\n(接続デバッグ情報: {debug_wp_info})")
                        else:
                            st.toast("🤖 AIによるリライト記事を生成中...")
                            # 実行用のAPIキー取得
                            active_api_key = env_values.get("GEMINI_API_KEY", "") if rew_ai_model == "gemini" else env_values.get("ANTHROPIC_API_KEY", "")
                            
                            try:
                                rewrite_res = rewrite_blog_article(
                                    api_key=active_api_key,
                                    original_title=original_post["title"],
                                    original_content=original_post["content"],
                                    low_performing_queries=target_info["queries"],
                                    ai_model=rew_ai_model
                                )
                                
                                new_title = rewrite_res["title"]
                                new_content = rewrite_res["content"]
                                new_excerpt = rewrite_res["meta_description"]
                                
                                if overwrite_wp:
                                    st.toast("📤 WordPressの既存記事を上書き更新中...")
                                    res_url = update_article_in_wordpress(
                                        wp_url=cur_wp_url,
                                        username=cur_wp_user,
                                        app_password=cur_wp_pass,
                                        post_id=post_id,
                                        title=new_title,
                                        content=new_content,
                                        excerpt=new_excerpt
                                    )
                                    st.success(f"🎉 記事の上書き更新に成功しました！\n👉 [更新された記事を確認する]({res_url})")
                                else:
                                    st.toast("📤 新しい下書き記事として保存中...")
                                    res_url = post_article_to_wordpress(
                                        wp_url=cur_wp_url,
                                        username=cur_wp_user,
                                        app_password=cur_wp_pass,
                                        title=f"【改善版】{new_title}",
                                        content=new_content,
                                        excerpt=new_excerpt,
                                        featured_media_id=original_post.get("featured_media"),
                                        tags=original_post.get("tags"),
                                        status="draft"
                                    )
                                    st.success(f"🎉 改善したリライト記事を『下書き』として保存しました！\n👉 [下書きの編集・プレビュー画面を開く]({res_url})")
                            except Exception as e:
                                st.error(f"❌ リライト処理中にエラーが発生しました: {e}")
                                    
with tab2:
    st.markdown("### 📷 観光地・自社店舗写真の登録・管理")
    st.caption("AIが記事内で特定の観光地やお店（例:『宮古島レンタカー』など）を執筆した際、Googleマップの一般写真ではなく、こちらで登録した指定写真を優先して自動挿入します。スマホからも名前を指定してアップロードできます。")
    
    custom_spots_dir = os.path.join(os.path.dirname(__file__), "images", "custom_spots")
    if not os.path.exists(custom_spots_dir):
        os.makedirs(custom_spots_dir)
        
    # 新規登録フォーム
    st.write("#### 🆕 新しい公式写真を登録する")
    col_up1, col_up2 = st.columns([1, 2])
    with col_up1:
        target_spot_name = st.text_input("適用したいスポット・お店の正確な名前", placeholder="例：宮古島レンタカー")
    with col_up2:
        uploaded_file = st.file_uploader("写真を選択（スマホの写真ライブラリから選択可能）", type=["png", "jpg", "jpeg"])
        
    if st.button("💾 写真をこの名前で保存する"):
        if not target_spot_name.strip():
            st.error("❌ エラー: スポット名を入力してください。")
        elif not uploaded_file:
            st.error("❌ エラー: 写真ファイルを選択してください。")
        else:
            # 拡張子の取得
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            if ext not in [".png", ".jpg", ".jpeg"]:
                ext = ".jpg" # デフォルト
            
            # 保存処理
            save_path = os.path.join(custom_spots_dir, f"{target_spot_name.strip()}{ext}")
            
            # 競合ファイルの削除 (他の拡張子があった場合)
            for other_ext in [".png", ".jpg", ".jpeg"]:
                other_path = os.path.join(custom_spots_dir, f"{target_spot_name.strip()}{other_ext}")
                if os.path.exists(other_path):
                    os.remove(other_path)
                    
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            st.success(f"✅ スポット '{target_spot_name.strip()}' の写真を優先画像として登録しました！")
            st.rerun()
            
    # 登録済み一覧の表示
    st.write("---")
    st.write("#### 🗂️ 現在登録されている優先写真一覧")
    
    if os.path.exists(custom_spots_dir):
        files = [f for f in os.listdir(custom_spots_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    else:
        files = []
        
    if not files:
        st.info("現在登録されている優先写真はありません。")
    else:
        # グリッド状（3列）で画像と削除ボタンを表示
        cols = st.columns(3)
        from PIL import Image
        for i, filename in enumerate(sorted(files)):
            col = cols[i % 3]
            spot_name = os.path.splitext(filename)[0]
            img_path = os.path.join(custom_spots_dir, filename)
            
            with col:
                st.write(f"**📍 {spot_name}**")
                try:
                    img = Image.open(img_path)
                    st.image(img, use_container_width=True)
                except Exception as e:
                    st.error("画像の読み込みに失敗しました")
                    
                if st.button(f"🗑️ 削除", key=f"del_{spot_name}"):
                    os.remove(img_path)
                    st.success(f"'{spot_name}' の写真を削除しました。")
                    st.rerun()

with tab3:
    st.markdown("### ⚙️ システム連携・APIキーの設定")
    st.caption("WordPressへの自動投稿やGoogleマップの写真取得に必要な各種キーを編集できます。保存すると `.env` ファイルが自動更新されます。")
    
    env_values = load_env_values()
    
    col_env1, col_env2 = st.columns(2)
    with col_env1:
        gemini_key = st.text_input("Gemini APIキー", value=env_values.get("GEMINI_API_KEY", ""), type="password", help="Gemini API (Google AI Studio) から取得したAPIキー")
        wp_url = st.text_input("WordPress URL", value=env_values.get("WP_URL", ""), help="WordPressのトップURL（例: https://example.com/article）")
        wp_username = st.text_input("WordPress ユーザー名", value=env_values.get("WP_USERNAME", ""))
        wp_password = st.text_input("WordPress アプリケーションパスワード", value=env_values.get("WP_PASSWORD", ""), type="password", help="WordPressの管理画面 ＞ ユーザー ＞ プロフィール から生成できるパスワード")
        search_console_property = st.text_input("Search Console プロパティURL", value=env_values.get("SEARCH_CONSOLE_PROPERTY_URL", ""), help="連携するサイトのURL（例: https://miyakojima-rentacar.net/ または sc-domain:miyakojima-rentacar.net）")
    with col_env2:
        anthropic_key = st.text_input("Claude (Anthropic) APIキー", value=env_values.get("ANTHROPIC_API_KEY", ""), type="password", help="Anthropic Consoleから取得したAPIキー")
        unsplash_key = st.text_input("Unsplash APIキー (アイキャッチ自動取得用：任意)", value=env_values.get("UNSPLASH_ACCESS_KEY", ""), help="Unsplashの開発者用Access Key")
        maps_key = st.text_input("Google Maps APIキー (観光地写真用：任意)", value=env_values.get("GOOGLE_MAPS_API_KEY", ""), type="password", help="Google Cloud Consoleから取得したPlaces APIが有効なAPIキー")
        raw_sa_json = env_values.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        # もし辞書オブジェクト（Secretsからテーブル形式でロードされた場合など）であれば、JSON文字列にシリアライズします
        if isinstance(raw_sa_json, dict) or (not isinstance(raw_sa_json, str) and hasattr(raw_sa_json, "get")):
            import json
            try:
                # Streamlitの循環参照による無限再帰を防ぐため、必要なキーだけを安全にコピーしてシリアライズします
                info = {}
                for key_name in [
                    "type", "project_id", "private_key_id", "private_key", "client_email",
                    "client_id", "auth_uri", "token_uri", "auth_provider_x509_cert_url",
                    "client_x509_cert_url", "universe_domain"
                ]:
                    if hasattr(raw_sa_json, "get"):
                        info[key_name] = raw_sa_json.get(key_name)
                    elif key_name in raw_sa_json:
                        info[key_name] = raw_sa_json[key_name]
                raw_sa_json = json.dumps(info, indent=2, ensure_ascii=False)
            except Exception:
                pass
        service_account_json = st.text_area("Google サービスアカウントキー (JSON)", value=str(raw_sa_json), height=150, help="Search Console APIへのアクセス権限を持つサービスアカウントのJSONキーファイルの中身をそのまま貼り付けてください。")
        
    if st.button("⚙️ 設定を保存する"):
        new_env = {
            "GEMINI_API_KEY": gemini_key,
            "WP_URL": wp_url,
            "WP_USERNAME": wp_username,
            "WP_PASSWORD": wp_password,
            "UNSPLASH_ACCESS_KEY": unsplash_key,
            "GOOGLE_MAPS_API_KEY": maps_key,
            "ANTHROPIC_API_KEY": anthropic_key,
            "GOOGLE_SERVICE_ACCOUNT_JSON": service_account_json,
            "SEARCH_CONSOLE_PROPERTY_URL": search_console_property
        }
        save_env_values(new_env)
        st.success("✅ 設定情報を保存しました！システムに即時反映されます。")
        
        # モジュール上の設定値を直接書き換え
        config.GEMINI_API_KEY = gemini_key
        config.WP_URL = wp_url
        config.WP_USERNAME = wp_username
        config.WP_PASSWORD = wp_password
        config.UNSPLASH_ACCESS_KEY = unsplash_key
        config.GOOGLE_MAPS_API_KEY = maps_key
        config.ANTHROPIC_API_KEY = anthropic_key
        config.GOOGLE_SERVICE_ACCOUNT_JSON = service_account_json
        config.SEARCH_CONSOLE_PROPERTY_URL = search_console_property

with tab4:
    st.markdown("### 📖 取扱説明書・設定ガイド")
    st.caption("アプリの使い方や、WordPress・各種API的連携手順、本番デプロイ時の注意点を解説しています。")
    
    manual_path = os.path.join(os.path.dirname(__file__), "manual.html")
    if os.path.exists(manual_path):
        with open(manual_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        # 画像パスをGitHubのリモートURLに置換して、Streamlitのiframe内でも画像が表示されるようにします
        repo_url = "https://raw.githubusercontent.com/dreamtactdxsolutions/Auto-blog-Generator-WordPress/main/"
        html_content = html_content.replace("images/manual_header.png", repo_url + "images/manual_header.png")
        html_content = html_content.replace("images/api_guide.png", repo_url + "images/api_guide.png")
        html_content = html_content.replace("images/step_guide.png", repo_url + "images/step_guide.png")
        
        # iframeでHTMLマニュアルを表示
        import streamlit.components.v1 as components
        components.html(html_content, height=900, scrolling=True)
    else:
        st.error("取扱説明書ファイル（manual.html）が見つかりませんでした。")
