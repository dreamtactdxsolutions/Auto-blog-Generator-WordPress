import os
import random
import requests
import re
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
    tags: list = None,
    status: str = "draft",
    date: str = None
) -> str:
    """
    WordPress REST APIを使用してブログ記事を投稿します。
    デフォルトでは安全のため「下書き (draft)」状態で保存されます。
    未来の日付（ISO 8601形式）と status="future" を指定することで、予約投稿が可能です。
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
        
    # タグIDリストが指定されている場合はセット
    if tags:
        data['tags'] = tags

    # 公開日時が指定されている場合はセット（例: "2026-07-10T12:00:00"）
    if date:
        data['date'] = date
        
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
            print(f"\n🎉 WordPressへの記事投稿に成功しました！ (ステータス: {status}, 日時: {date or '即時'})")
            print(f"🔗 プレビュー/編集用URL: {post_url}\n")
            return post_url
        else:
            print(f"❌ 記事の投稿に失敗しました (ステータスコード: {response.status_code})")
            print(response.text)
            raise Exception("WordPress REST APIの応答エラー")
            
    except Exception as e:
        print(f"❌ WordPressへの接続または投稿中にエラーが発生しました: {e}")
        raise e

def get_article_content_detailed(wp_url: str, username: str, app_password: str, post_id: int) -> dict:
    """
    指定された記事IDのコンテンツ（タイトル、本文、抜粋、タグIDリスト、アイキャッチメディアID）を取得します。
    """
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    
    try:
        import html
        response = requests.get(
            url,
            auth=HTTPBasicAuth(username, app_password),
            timeout=20
        )
        
        if response.status_code == 200:
            post = response.json()
            title = post.get('title', {}).get('rendered', '')
            title = html.unescape(title)
            content = post.get('content', {}).get('raw', post.get('content', {}).get('rendered', ''))
            excerpt = post.get('excerpt', {}).get('raw', post.get('excerpt', {}).get('rendered', ''))
            excerpt = re.sub(r'<[^>]+>', '', excerpt).strip() if excerpt else ""
            
            return {
                "id": post.get("id"),
                "title": title,
                "content": content,
                "excerpt": html.unescape(excerpt),
                "tags": post.get("tags", []),
                "featured_media": post.get("featured_media")
            }
        else:
            print(f"❌ 記事の取得に失敗しました (ID: {post_id}, ステータスコード: {response.status_code})")
            return None
    except Exception as e:
        print(f"❌ 記事取得中にエラーが発生しました (ID: {post_id}): {e}")
        return None

def update_article_in_wordpress(
    wp_url: str, 
    username: str, 
    app_password: str, 
    post_id: int,
    title: str = None, 
    content: str = None, 
    excerpt: str = None, 
    featured_media_id: int = None, 
    tags: list = None,
    status: str = None
) -> str:
    """
    指定された記事IDの既存投稿をWordPress REST API経由で更新（上書き）します。
    """
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    
    data = {}
    if title is not None: data['title'] = title
    if content is not None: data['content'] = content
    if excerpt is not None: data['excerpt'] = excerpt
    if status is not None: data['status'] = status
    if featured_media_id is not None: data['featured_media'] = featured_media_id
    if tags is not None: data['tags'] = tags
        
    try:
        response = requests.post(
            url,
            json=data,
            auth=HTTPBasicAuth(username, app_password),
            timeout=30
        )
        
        if response.status_code == 200:
            post_data = response.json()
            post_url = post_data.get('link')
            print(f"\n🎉 WordPressの記事更新（ID: {post_id}）に成功しました！")
            print(f"🔗 更新記事URL: {post_url}\n")
            return post_url
        else:
            print(f"❌ 記事の更新に失敗しました (ステータスコード: {response.status_code})")
            print(response.text)
            raise Exception("WordPress REST APIの応答エラー")
            
    except Exception as e:
        print(f"❌ WordPressへの接続または更新中にエラーが発生しました: {e}")
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
        'status': 'publish,draft',
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

def get_or_create_wp_tags(wp_url: str, username: str, app_password: str, tag_names: list) -> list:
    """
    タグ名（文字列）のリストを受け取り、WordPress上のタグIDのリストに変換します。
    存在しないタグは自動的に新規作成します。
    """
    if not tag_names:
        return []
        
    auth = HTTPBasicAuth(username, app_password)
    tag_ids = []
    
    for name in tag_names:
        name = name.strip()
        if not name:
            continue
            
        # 1. 既存のタグを検索
        search_url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/tags"
        params = {"search": name}
        
        try:
            response = requests.get(search_url, params=params, auth=auth, timeout=15)
            matched_id = None
            if response.status_code == 200:
                existing_tags = response.json()
                # 完全一致するタグがあるか確認
                for t in existing_tags:
                    if t.get("name") == name:
                        matched_id = t.get("id")
                        break
                
            if matched_id:
                tag_ids.append(matched_id)
                print(f"🏷️ 既存のタグを使用します: {name} (ID: {matched_id})")
                continue
            
            # 2. 存在しない場合は新規作成
            create_url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/tags"
            data = {"name": name}
            create_response = requests.post(create_url, json=data, auth=auth, timeout=15)
            
            if create_response.status_code == 201:
                new_tag = create_response.json()
                new_id = new_tag.get("id")
                tag_ids.append(new_id)
                print(f"🏷️ 新しいタグを作成しました: {name} (ID: {new_id})")
            else:
                print(f"⚠️ タグ '{name}' の作成に失敗しました (ステータス: {create_response.status_code})")
                # 作成に失敗したが、検索結果にある場合はフォールバックとして最初のタグを使用
                if response.status_code == 200 and existing_tags:
                    fallback_id = existing_tags[0].get("id")
                    tag_ids.append(fallback_id)
                    print(f"   フォールバックとして類似タグID {fallback_id} を使用します。")
                    
        except Exception as e:
            print(f"⚠️ タグ '{name}' の処理中にエラーが発生しました: {e}")
            
    return tag_ids

