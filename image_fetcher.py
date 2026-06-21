import os
import requests

def download_image_from_unsplash(keyword: str, access_key: str, save_dir: str = "images") -> str:
    """
    Unsplash APIを使用して、指定されたキーワードに合う美しい横長（landscape）画像を自動で1枚ダウンロードし、
    指定の保存フォルダに保存します。保存した画像のローカルファイルパスを返します。
    """
    # キーが未設定の場合は処理をスキップ
    if not access_key or "your_unsplash_access_key" in access_key:
        print("⚠️ Unsplash APIキーが設定されていないため、インターネットからの画像取得をスキップします。")
        return None
        
    url = "https://api.unsplash.com/photos/random"
    params = {
        'query': keyword,
        'client_id': access_key,
        'orientation': 'landscape'  # ブログのアイキャッチに適した「横長」に限定
    }
    
    # 保存先ディレクトリの作成
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        
    print(f"🔍 インターネット（Unsplash）から画像を検索中... (キーワード: {keyword})")
    
    try:
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            image_url = data.get("urls", {}).get("regular")
            photo_id = data.get("id")
            
            if not image_url:
                print("⚠️ Unsplashの応答データに画像URLが見つかりませんでした。")
                return None
                
            # 重複を避けるため、Unsplashの写真IDをファイル名に含めます
            file_path = os.path.join(save_dir, f"unsplash_{photo_id}.jpg")
            
            # 画像データのダウンロードと保存
            print(f"📥 見つかった画像をダウンロード中...")
            img_data = requests.get(image_url, timeout=20)
            
            if img_data.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(img_data.content)
                print(f"✅ 画像の取得・保存に成功しました！ (保存先: {file_path})")
                return file_path
            else:
                print(f"⚠️ 画像データの取得に失敗しました (ステータス: {img_data.status_code})")
                return None
                
        elif response.status_code == 403:
            print("⚠️ Unsplash APIエラー (403 Forbidden): APIの利用回数制限（1時間に50回）に達したか、キーが無効です。")
            return None
        else:
            print(f"⚠️ Unsplash APIエラー (ステータス: {response.status_code})")
            return None
            
    except Exception as e:
        print(f"⚠️ 画像取得中にエラーが発生しました: {e}")
        return None

# 単体テスト用の処理
if __name__ == "__main__":
    # プロジェクトの設定ファイルを読み込みます
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import config
    
    if config.validate_config():
        if config.UNSPLASH_ACCESS_KEY:
            test_keyword = "okinawa beach"
            path = download_image_from_unsplash(test_keyword, config.UNSPLASH_ACCESS_KEY, "images_test")
            if path:
                print(f"🎉 テスト成功！ 画像がここに保存されました: {path}")
            else:
                print("❌ テスト失敗: 画像が取得できませんでした。")
        else:
            print("❌ テストには .env に UNSPLASH_ACCESS_KEY の設定が必要です。")
