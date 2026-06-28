import os
from dotenv import load_dotenv

# .env ファイルから環境変数を読み込みます
load_dotenv()

def get_setting(key, default=""):
    # Streamlit Cloud環境では、設定管理機能（Secrets）から優先的に取得します
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except:
        pass
    return os.getenv(key, default)

# 各種設定値の取得
GEMINI_API_KEY = get_setting("GEMINI_API_KEY")
ANTHROPIC_API_KEY = get_setting("ANTHROPIC_API_KEY")
WP_URL = get_setting("WP_URL")
WP_USERNAME = get_setting("WP_USERNAME")
WP_PASSWORD = get_setting("WP_PASSWORD")

# オプション設定（Unsplash APIキー：画像ネット自動取得用）
UNSPLASH_ACCESS_KEY = get_setting("UNSPLASH_ACCESS_KEY")

# オプション設定（Google Maps APIキー：観光地の写真自動取得用）
GOOGLE_MAPS_API_KEY = get_setting("GOOGLE_MAPS_API_KEY")

# 設定値が正しく入力されているかをチェックする関数
def validate_config(ai_model: str = "gemini"):
    missing = []
    
    # 選択されたモデルに応じたAPIキーのチェック
    if ai_model.lower() == "gemini":
        if not GEMINI_API_KEY or "your_gemini_api_key" in GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY (Gemini APIキー)")
    elif ai_model.lower() == "claude":
        if not ANTHROPIC_API_KEY or "your_anthropic_api_key" in ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY (Claude/Anthropic APIキー)")
            
    # WordPress関連の必須項目のチェック
    if not WP_URL or "your_wordpress_url" in WP_URL:
        missing.append("WP_URL (WordPressのURL)")
    if not WP_USERNAME or "your_username" in WP_USERNAME:
        missing.append("WP_USERNAME (WordPressのユーザー名)")
    if not WP_PASSWORD or "your_application_password" in WP_PASSWORD:
        missing.append("WP_PASSWORD (WordPressのアプリケーションパスワード)")
        
    if missing:
        print("\n❌ 設定エラー:")
        print("以下の設定が正しく入力されていません。")
        for item in missing:
            print(f"  - {item}")
        print("\nアプリ画面の『⚙️ システム設定』または `.env` を確認してください。\n")
        return False
        
    # オプション設定のステータス表示
    print(f"\n✅ 必須設定のチェック完了。 (AIモデル: {ai_model.upper()})")
    if UNSPLASH_ACCESS_KEY and "your_unsplash_access_key" not in UNSPLASH_ACCESS_KEY:
        print("📸 Unsplash APIキー設定済み: 画像のインターネット自動取得が『有効』です。")
    else:
        print("⚠️ Unsplash APIキー未設定: 画像のインターネット自動取得は『無効』です。")
        
    if GOOGLE_MAPS_API_KEY and "your_google_maps_api_key" not in GOOGLE_MAPS_API_KEY:
        print("🗺️  Google Maps APIキー設定済み: 観光地写真の自動取得が『有効』です。")
    else:
        print("⚠️  Google Maps APIキー未設定: 観光地写真の自動取得は『無効』です。")
    print()
    return True

