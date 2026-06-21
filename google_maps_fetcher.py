import os
import re
import requests
import hashlib

def download_photo_for_spot(spot_name: str, api_key: str, save_dir: str) -> dict:
    """
    Google Places API を使用して、指定した観光スポット名の高画質写真を検索し、
    アスペクト比フィルタリングを行ってダウンロードします。また、権利帰属クレジットのHTMLを生成します。
    
    戻り値:
        dict: {"local_path": 保存先ファイルパス, "credit_html": クレジットHTML}
              取得に失敗した場合は None を返します。
    """
    if not api_key or "your_google_maps_api_key" in api_key:
        print("⚠️ Google Maps APIキーが設定されていないため、写真のダウンロードをスキップします。")
        return None
        
    print(f"🔍 Googleマップでスポット写真を取得中: {spot_name}")
    
    # 1. Places API (New) Text Search
    search_url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.id,places.displayName,places.photos"
    }
    # 宮古島を入れて検索精度を上げる
    query = f"宮古島 {spot_name}"
    payload = {
        "textQuery": query
    }
    
    try:
        response = requests.post(search_url, json=payload, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"❌ Places API 検索エラー (ステータス: {response.status_code}): {response.text}")
            return None
            
        data = response.json()
        places = data.get("places", [])
        if not places:
            print(f"⚠️ スポット '{spot_name}' がGoogleマップで見つかりませんでした。")
            return None
            
        place = places[0]
        photos = place.get("photos", [])
        if not photos:
            print(f"⚠️ スポット '{spot_name}' に写真が登録されていません。")
            return None
            
        # 2. ベストな写真の選定（高画質 ＆ 横長アスペクト比）
        best_photo = None
        best_score = -1
        
        for photo in photos:
            width = photo.get("widthPx", 0)
            height = photo.get("heightPx", 0)
            if width == 0 or height == 0:
                continue
                
            aspect_ratio = width / height
            score = 0
            
            # 解像度スコア
            if width >= 1200:
                score += 15
            elif width >= 1000:
                score += 10
            elif width >= 600:
                score += 5
                
            # アスペクト比スコア (1.2 ~ 1.8 はブログ向きの横長)
            if 1.2 <= aspect_ratio <= 1.8:
                score += 20
            elif 1.0 <= aspect_ratio <= 2.0:
                score += 10
            elif 0.8 <= aspect_ratio <= 2.4:
                score += 3
                
            if score > best_score:
                best_score = score
                best_photo = photo
                
        # マッチする写真がない場合は最初の写真にする
        if not best_photo:
            best_photo = photos[0]
            
        # 3. 写真のダウンロード
        photo_name = best_photo.get("name")
        download_url = f"https://places.googleapis.com/v1/{photo_name}/media"
        params = {
            "key": api_key,
            "maxWidthPx": 1200  # 横幅最大1200ピクセルで取得
        }
        
        photo_response = requests.get(download_url, params=params, timeout=20)
        if photo_response.status_code != 200:
            print(f"❌ 写真のダウンロードに失敗しました (ステータス: {photo_response.status_code})")
            return None
            
        # 保存先フォルダの作成
        os.makedirs(save_dir, exist_ok=True)
        
        # 安全なファイル名の作成 (スポット名をハッシュ化)
        hash_str = hashlib.md5(spot_name.encode('utf-8')).hexdigest()[:8]
        filename = f"google_maps_{hash_str}.jpg"
        filepath = os.path.join(save_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(photo_response.content)
            
        print(f"💾 写真の保存に成功しました: {filepath} (サイズ: {len(photo_response.content)} bytes)")
        
        # 4. クレジットHTMLの生成
        attributions = best_photo.get("authorAttributions", [])
        credit_parts = []
        for attr in attributions:
            name = attr.get("displayName")
            uri = attr.get("uri")
            if name:
                if uri:
                    # target="_blank" と nofollow を付与
                    credit_parts.append(f'<a href="{uri}" target="_blank" rel="noopener noreferrer nofollow">{name}様</a>')
                else:
                    credit_parts.append(f'{name}様')
                    
        if credit_parts:
            credits_str = "、".join(credit_parts)
            credit_html = f'<p style="font-size: 0.8em; color: #777; margin-top: 8px; text-align: center; margin-bottom: 25px;">画像出典：{credits_str}（Google Mapsより）</p>'
        else:
            credit_html = '<p style="font-size: 0.8em; color: #777; margin-top: 8px; text-align: center; margin-bottom: 25px;">画像出典：Google Maps</p>'
            
        return {
            "local_path": filepath,
            "credit_html": credit_html
        }
        
    except Exception as e:
        print(f"❌ Googleマップ写真取得中にエラーが発生しました ({spot_name}): {e}")
        import traceback
        traceback.print_exc()
        return None
