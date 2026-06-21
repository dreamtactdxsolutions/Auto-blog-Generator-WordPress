import os
import random
import requests
from requests.auth import HTTPBasicAuth

def get_random_image_from_folder(folder_path: str) -> str:
    """
    指定されたフォルダからランダムに画像ファイル（jpg, jpeg, png）を1つ選択してパスを返します。
    画像が見つからない場合は None を返します。
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"📂 画像フォルダ '{folder_path}' が見つからなかったため、新規作成しました。")
        print("💡 ここに宮古島の写真（.jpgや.png）を入れておくと、自動でアイキャッチ画像に設定されます。")
        return None
        
    valid_extensions = ['.jpg', '.jpeg', '.png']
    images = [
        os.path.join(folder_path, f) for f in os.listdir(folder_path)
        if os.path.splitext(f.lower())[1] in valid_extensions
        and "processed_banner" not in f.lower()
        and "sample_existing" not in f.lower()
    ]
    
    if not images:
        print(f"⚠️ 画像フォルダ '{folder_path}' に画像ファイルが見つかりません。")
        return None
        
    selected_image = random.choice(images)
    print(f"🖼️ アイキャッチ画像として選択されました: {os.path.basename(selected_image)}")
    return selected_image

def upload_image_to_wordpress(wp_url: str, username: str, app_password: str, image_path: str) -> int:
    """
    ローカルの画像ファイルをWordPressのメディアライブラリにアップロードし、そのIDを返します。
    失敗した場合は None を返します。
    """
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/media"
    filename = os.path.basename(image_path)
    
    # 拡張子から Content-Type を判定
    _, ext = os.path.splitext(filename.lower())
    if ext in ['.jpg', '.jpeg']:
        content_type = 'image/jpeg'
    elif ext == '.png':
        content_type = 'image/png'
    else:
        content_type = 'application/octet-stream'

    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"',
        'Content-Type': content_type
    }
    
    try:
        with open(image_path, 'rb') as img:
            response = requests.post(
                url,
                headers=headers,
                data=img,
                auth=HTTPBasicAuth(username, app_password),
                timeout=30
            )
            
        if response.status_code == 201:
            media_data = response.json()
            media_id = media_data.get('id')
            print(f"📷 画像アップロード成功！ メディアID: {media_id} ({filename})")
            return media_id
        else:
            print(f"❌ 画像アップロードに失敗しました (ステータスコード: {response.status_code})")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ 画像アップロード中に通信エラーが発生しました: {e}")
        return None

def upload_image_to_wordpress_detailed(wp_url: str, username: str, app_password: str, image_path: str) -> dict:
    """
    ローカルの画像ファイルをWordPressのメディアライブラリにアップロードし、
    メディアIDとsource_urlを含む辞書を返します。
    失敗した場合は None を返します。
    """
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/media"
    filename = os.path.basename(image_path)
    
    _, ext = os.path.splitext(filename.lower())
    if ext in ['.jpg', '.jpeg']:
        content_type = 'image/jpeg'
    elif ext == '.png':
        content_type = 'image/png'
    else:
        content_type = 'application/octet-stream'

    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"',
        'Content-Type': content_type
    }
    
    try:
        with open(image_path, 'rb') as img:
            response = requests.post(
                url,
                headers=headers,
                data=img,
                auth=HTTPBasicAuth(username, app_password),
                timeout=30
            )
            
        if response.status_code == 201:
            media_data = response.json()
            media_id = media_data.get('id')
            source_url = media_data.get('source_url')
            print(f"📷 画像アップロード成功！ メディアID: {media_id}, URL: {source_url} ({filename})")
            return {"id": media_id, "source_url": source_url}
        else:
            print(f"❌ 画像アップロードに失敗しました (ステータスコード: {response.status_code})")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ 画像アップロード中に通信エラーが発生しました: {e}")
        return None

def post_article_to_wordpress(
    wp_url: str, 
    username: str, 
    app_password: str, 
    title: str, 
    content: str, 
    excerpt: str, 
    featured_media_id: int = None, 
    status: str = "draft"
) -> str:
    """
    WordPress REST APIを使用してブログ記事を投稿します。
    デフォルトでは安全のため「下書き (draft)」状態で保存されます。
    """
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts"
    
    data = {
        'title': title,
        'content': content,
        'excerpt': excerpt,
        'status': status
    }
    
    # アイキャッチ画像IDが指定されている場合はセット
    if featured_media_id:
        data['featured_media'] = featured_media_id
        
    try:
        response = requests.post(
            url,
            json=data,
            auth=HTTPBasicAuth(username, app_password),
            timeout=30
        )
        
        if response.status_code == 201:
            post_data = response.json()
            post_url = post_data.get('link')
            print(f"\n🎉 WordPressへの記事投稿に成功しました！ (ステータス: {status})")
            print(f"🔗 プレビュー/編集用URL: {post_url}\n")
            return post_url
        else:
            print(f"❌ 記事の投稿に失敗しました (ステータスコード: {response.status_code})")
            print(response.text)
            raise Exception("WordPress REST APIの応答エラー")
            
    except Exception as e:
        print(f"❌ WordPressへの接続または投稿中にエラーが発生しました: {e}")
        raise e

def get_existing_posts(wp_url: str, username: str, app_password: str) -> list:
    """
    WordPressから現在公開されている（publish）投稿のタイトル一覧を取得します。
    """
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts"
    # タイトルだけを軽量に取得するために _fields パラメータを使用します
    params = {
        'status': 'publish',
        'per_page': 100,
        '_fields': 'title'
    }
    
    try:
        import html
        response = requests.get(
            url,
            params=params,
            auth=HTTPBasicAuth(username, app_password),
            timeout=20
        )
        
        if response.status_code == 200:
            posts = response.json()
            titles = [post.get('title', {}).get('rendered', '') for post in posts]
            # HTMLエンティティ（&amp; や &#8211; など）をデコードして通常の文字に戻します
            titles = [html.unescape(title) for title in titles if title]
            print(f"📊 WordPressから既存記事のタイトルを {len(titles)} 件取得しました。")
            return titles
        else:
            print(f"⚠️ 既存記事の取得に失敗しました (ステータスコード: {response.status_code})")
            return []
    except Exception as e:
        print(f"⚠️ 既存記事 of 取得中にエラーが発生しました: {e}")
        return []

def get_existing_posts_detailed(wp_url: str, username: str, app_password: str) -> list:
    """
    WordPressから公開されている投稿の詳細情報（ID, タイトル, URL, アイキャッチ画像URL）の一覧を最大100件取得します。
    """
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts"
    params = {
        'status': 'publish',
        'per_page': 100,
        '_embed': 'true',  # メディア情報を埋め込む
    }
    
    try:
        import html
        response = requests.get(
            url,
            params=params,
            auth=HTTPBasicAuth(username, app_password),
            timeout=25
        )
        
        if response.status_code == 200:
            posts = response.json()
            detailed_posts = []
            
            for post in posts:
                post_id = post.get('id')
                title = post.get('title', {}).get('rendered', '')
                title = html.unescape(title)
                link = post.get('link', '')
                
                # アイキャッチ画像URLの取得
                image_url = ""
                embedded = post.get('_embedded', {})
                featured_media_list = embedded.get('wp:featuredmedia', [])
                if featured_media_list and isinstance(featured_media_list, list) and len(featured_media_list) > 0:
                    media = featured_media_list[0]
                    media_details = media.get('media_details', {})
                    sizes = media_details.get('sizes', {})
                    if 'medium' in sizes:
                        image_url = sizes['medium'].get('source_url', '')
                    elif 'full' in sizes:
                        image_url = sizes['full'].get('source_url', '')
                    else:
                        image_url = media.get('source_url', '')
                
                # 画像がない場合のデフォルト画像
                if not image_url:
                    image_url = "https://miyakojima-rentacar.net/article/wp-content/uploads/2025/10/yoyaku_banner.jpg"
                    
                detailed_posts.append({
                    'id': post_id,
                    'title': title,
                    'url': link,
                    'image_url': image_url
                })
                
            print(f"📊 WordPressから詳細付きの既存記事を {len(detailed_posts)} 件取得しました。")
            return detailed_posts
        else:
            print(f"⚠️ 詳細付き既存記事の取得に失敗しました (ステータスコード: {response.status_code})")
            return []
    except Exception as e:
        print(f"⚠️ 詳細付き既存記事の取得中にエラーが発生しました: {e}")
        return []

