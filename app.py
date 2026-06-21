import os
import sys
import json
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
    post_article_to_wordpress,
    get_existing_posts_detailed
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
        keys = ["GEMINI_API_KEY", "WP_URL", "WP_USERNAME", "WP_PASSWORD", "UNSPLASH_ACCESS_KEY", "GOOGLE_MAPS_API_KEY"]
        for k in keys:
            if k in st.secrets:
                values[k] = st.secrets[k]
    except:
        pass
        
    # 2. ローカルの .env ファイルがあれば上書きします
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    values[k.strip()] = v.strip()
    return values

def save_env_values(new_values):
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    lines = []
    updated_keys = set()
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k, v = stripped.split("=", 1)
                    k = k.strip()
                    if k in new_values:
                        lines.append(f"{k}={new_values[k]}\n")
                        updated_keys.add(k)
                    else:
                        lines.append(line)
                else:
                    lines.append(line)
    
    # 既存の .env に無かったキーを追加
    for k, v in new_values.items():
        if k not in updated_keys:
            lines.append(f"{k}={v}\n")
            
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

# タブ機能で画面を整理（スポット画像登録用タブを追加）
tab1, tab2, tab3 = st.tabs(["📝 記事生成", "📷 スポット画像登録", "⚙️ システム設定"])

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
    with col_env2:
        unsplash_key = st.text_input("Unsplash APIキー (アイキャッチ自動取得用：任意)", value=env_values.get("UNSPLASH_ACCESS_KEY", ""), help="Unsplashの開発者用Access Key")
        maps_key = st.text_input("Google Maps APIキー (観光地写真用：任意)", value=env_values.get("GOOGLE_MAPS_API_KEY", ""), type="password", help="Google Cloud Consoleから取得したPlaces APIが有効なAPIキー")
        
    if st.button("⚙️ 設定を保存する"):
        new_env = {
            "GEMINI_API_KEY": gemini_key,
            "WP_URL": wp_url,
            "WP_USERNAME": wp_username,
            "WP_PASSWORD": wp_password,
            "UNSPLASH_ACCESS_KEY": unsplash_key,
            "GOOGLE_MAPS_API_KEY": maps_key
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

with tab1:
    st.markdown("### ✍️ 記事の作成モード")
    create_mode = st.radio(
        "記事の作成方法を選択してください",
        ["🎯 テーマ指定モード (キーワードやタイトルを自分で指定)", "🔥 トレンドリサーチモード (最近の流行・話題を自動検索して執筆)"],
        horizontal=True
    )
    
    use_trend_research = False
    trend_genre = "すべて"
    theme = None
    keyword = None
    sub_keywords = []

    if "トレンドリサーチ" in create_mode:
        use_trend_research = True
        st.info("💡 AIが2026年現在の宮古島に関する新店舗のオープン情報、話題のイベント、観光トレンドなどをWeb上から自動リサーチし、最適なテーマを決めて執筆します。")
        trend_genre = st.selectbox("リサーチしたい情報のジャンルを選択してください", ["すべて", "グルメ・カフェ・新店舗", "観光スポット・イベント・フェスティバル", "アクティビティ・体験"])
    else:
        st.markdown("### ✍️ 記事の作成条件")
        # 1. キーワードリストの読み込み
        keywords_file = os.path.join(os.path.dirname(__file__), "keywords.json")
        keyword_list = []
        if os.path.exists(keywords_file):
            try:
                with open(keywords_file, "r", encoding="utf-8") as f:
                    keyword_list = json.load(f)
            except Exception as e:
                st.error(f"キーワードファイル（keywords.json）の読み込みに失敗しました: {e}")
                
        # プルダウンの選択肢を作成
        options = ["✨ 新しいテーマを手動で自由に書きたい"]
        for item in keyword_list:
            options.append(f"📌 【{item['keyword']}】{item['theme']}")
            
        selected_option = st.selectbox("作成したいブログ記事のテーマを選んでください", options)
        
        # 入力項目エリア
        col_input1, col_input2 = st.columns(2)
        
        if selected_option == "✨ 新しいテーマを手動で自由に書きたい":
            with col_input1:
                theme = st.text_input("記事のタイトル（テーマ名）", placeholder="例：宮古島をレンタカーで巡る！1日王道絶景ドライブモデルコース")
                keyword = st.text_input("主要検索キーワード", placeholder="例：宮古島 ドライブコース")
            with col_input2:
                sub_keywords_input = st.text_area("関連キーワード (カンマ `,` または改行で区切ってください)", placeholder="例：伊良部大橋, 東平安名崎, レンタカー, ドライブ")
                sub_keywords = [k.strip() for k in sub_keywords_input.replace("\n", ",").split(",") if k.strip()]
        else:
            # keywords.json から選ばれたデータを取得
            selected_index = options.index(selected_option) - 1
            selected_data = keyword_list[selected_index]
            
            with col_input1:
                theme = st.text_input("記事のタイトル（テーマ名）", value=selected_data["theme"])
                keyword = st.text_input("主要検索キーワード", value=selected_data["keyword"])
            with col_input2:
                default_sub = ", ".join(selected_data.get("sub_keywords", []))
                sub_keywords_input = st.text_area("関連キーワード (カンマ `,` または改行で区切ってください)", value=default_sub)
                sub_keywords = [k.strip() for k in sub_keywords_input.replace("\n", ",").split(",") if k.strip()]
            
    st.markdown("---")
    st.markdown("### ⚙️ オプション設定")
    
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        use_maps_photos = st.checkbox("Googleマップからスポットの絶景写真を自動取得し、記事中に挿入する", value=True, help="Places APIを使って観光地の写真を検索し、撮影者へのクレジットと共に記事内に自動配置します。")
        use_unsplash = st.checkbox("アイキャッチ画像をUnsplashから自動取得する（ローカル画像が不足している場合のみ）", value=True, help="imagesフォルダに実写画像が無い場合、自動で海の画像を検索・ダウンロードしてバナーに加工します。")
    with col_opt2:
        post_status = st.selectbox("WordPressへの公開ステータス", ["下書き (draft) - 推奨", "公開 (publish)"], index=0, help="まずは下書きで登録し、確認したのちに公開するのが安全です。")
        wp_status = "draft" if "下書き" in post_status else "publish"
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 実行ボタン
    if st.button("🚀 この内容で記事を自動生成してWordPressに保存する"):
        # 設定チェック
        env_values = load_env_values()
        cur_gemini = env_values.get("GEMINI_API_KEY", "")
        cur_wp_url = env_values.get("WP_URL", "")
        cur_wp_user = env_values.get("WP_USERNAME", "")
        cur_wp_pass = env_values.get("WP_PASSWORD", "")
        cur_maps_key = env_values.get("GOOGLE_MAPS_API_KEY", "")
        cur_unsplash_key = env_values.get("UNSPLASH_ACCESS_KEY", "")
        
        if not cur_gemini or not cur_wp_url or not cur_wp_user or not cur_wp_pass:
            st.error("❌ 接続エラー: システム設定タブに必要なAPIキーやWordPress接続情報が入力されていません。設定を入力してから再実行してください。")
        elif not use_trend_research and (not theme or not keyword):
            st.error("❌ 入力エラー: テーマ指定モードでは、記事のタイトルと主要キーワードは必須です。入力してください。")
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
                status_monitor.update(label="🤖 Gemini AIがブログ記事を執筆中...（数分かかる場合があります）", state="running")
                blog_post = generate_blog_article(
                    api_key=cur_gemini,
                    keyword=keyword,
                    theme=theme,
                    sub_keywords=sub_keywords,
                    existing_titles=existing_titles,
                    use_trend_research=use_trend_research,
                    trend_genre=trend_genre
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
                    featured_media_id = upload_image_to_wordpress(
                        wp_url=cur_wp_url,
                        username=cur_wp_user,
                        app_password=cur_wp_pass,
                        image_path=processed_image_path
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
                st.error(f"エラー内容: {e}")
                st.info("システム設定に入力された情報が正しいか再度確認してください。")
