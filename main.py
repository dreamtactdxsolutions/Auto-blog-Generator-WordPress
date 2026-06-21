import os
import sys
import json
import random
import config
from generator import generate_blog_article
from image_fetcher import download_image_from_unsplash
from image_processor import create_title_banner  # タイトル文字入れモジュールのインポート
from wordpress import (
    get_random_image_from_folder, 
    upload_image_to_wordpress, 
    upload_image_to_wordpress_detailed,
    post_article_to_wordpress,
    get_existing_posts_detailed
)
from google_maps_fetcher import download_photo_for_spot

# ==================================================
# 関連記事の選定ロジック & 定型テンプレート
# ==================================================

# デフォルトの関連記事（過去に実績のある記事。マッチする記事が不足している場合のフォールバック）
DEFAULT_RELATED_POSTS = [
    {
        "title": "あわせて読みたい記事1",
        "url": "https://miyakojima-rentacar.net/article/archives/126",
        "image_url": "https://miyakojima-rentacar.net/article/wp-content/uploads/2024/07/164a04c03f52a1b095085fadcd8ae12d-scaled.jpg"
    },
    {
        "title": "あわせて読みたい記事2",
        "url": "https://miyakojima-rentacar.net/article/archives/4893",
        "image_url": "https://miyakojima-rentacar.net/article/wp-content/uploads/2026/06/miyakozima-bi-ti-rankingu.png"
    },
    {
        "title": "あわせて読みたい記事3",
        "url": "https://miyakojima-rentacar.net/article/archives/4695",
        "image_url": "https://miyakojima-rentacar.net/article/wp-content/uploads/2026/03/miakojima-drve-spot.png"
    }
]

def select_related_posts(current_title: str, current_keyword: str, existing_posts: list, count: int = 3) -> list:
    """
    既存の記事一覧から、現在の記事に関連性の高い記事を自動でスコアリング選定して返します。
    """
    if not existing_posts:
        return DEFAULT_RELATED_POSTS
        
    import re
    tokens = re.split(r'[ 　,、!！?？]', current_keyword)
    tokens = [t for t in tokens if t and len(t) > 1]
    
    scored_posts = []
    for post in existing_posts:
        if post.get('title') == current_title:
            continue
            
        score = 0
        title = post.get('title', '')
        
        # キーワードとのマッチングスコア (タイトルに含まれる単語)
        for token in tokens:
            if token in title:
                score += 10
                
        # 関連するシノニム（連想ワード）
        related_keywords = {
            "ビーチ": ["海", "砂浜", "シュノーケル", "海岸", "シュノーケリング", "絶景", "観光", "スポット"],
            "グルメ": ["そば", "ランチ", "スイーツ", "カフェ", "食べ物", "レストラン", "宮古牛", "美味しい"],
            "ドライブ": ["レンタカー", "移動", "アクセス", "駐車場", "コース", "ルート", "運転"],
            "子連れ": ["子供", "家族", "ファミリー", "チャイルドシート", "安心"],
        }
        
        for key, synonyms in related_keywords.items():
            if key in current_keyword or key in current_title:
                for syn in synonyms:
                    if syn in title:
                        score += 3
                        
        scored_posts.append((score, post))
        
    # スコア順にソート
    scored_posts.sort(key=lambda x: x[0], reverse=True)
    
    # 選択
    selected = [item[1] for item in scored_posts[:count]]
    
    # 不足分の補填 (URLの重複を避けて追加)
    used_urls = {p.get('url') for p in selected}
    
    # まず既存記事の他のものから補填
    for score, post in scored_posts:
        if len(selected) >= count:
            break
        if post.get('url') not in used_urls:
            selected.append(post)
            used_urls.add(post.get('url'))
            
    # それでも足りない場合はデフォルトの3記事から補填
    for def_post in DEFAULT_RELATED_POSTS:
        if len(selected) >= count:
            break
        if def_post.get('url') not in used_urls:
            selected.append(def_post)
            used_urls.add(def_post.get('url'))
            
    return selected

def build_cta_html(related_posts: list) -> str:
    """
    関連記事を埋め込んだ定型CTA/バナーのHTMLブロックを生成します。
    """
    related_posts_html = ""
    for idx, post in enumerate(related_posts, 1):
        related_posts_html += f"""<!------ 記事{idx} ------>
<div style="margin-top: 15px;">
<a href="{post.get('url')}" target="_blank" class="layout-card" style="text-decoration: none; display: flex; align-items: center; border: none; border-radius: 8px; padding: 0; background-color: #f9f9f9; box-shadow: 2px 2px 12px rgba(0, 0, 0, 0.1); overflow: hidden;" rel="noopener">
<div style="flex-shrink: 0;">
<img class="layout-card-img" src="{post.get('image_url')}" style="height: auto; display: block;"></div>
<div style="padding: 16px; min-width:0;"><h3 class="js-h1-title" style="margin: 0; font-size: 1.2em; color: #333;">読み込み中…</h3></div>
</a>
</div>"""

    # JSやCSS内に中括弧 {} が多く含まれているため、f-string ではなく普通の文字列 replace で置換します。
    template = """
<!------------ ボタン -------------->
<div class="slash-wrap" style="margin: 40px auto 0px auto; text-align: center;"><span class="slash" style="display: inline-block; font-size: 1.2em;">宮古島での移動はレンタカーが便利！</span></div>
<style>
/*  ボタンの吹き出しＣＳＳ */
.slash-wrap { text-align: center; margin-top: 25px; }
.slash { display: inline-block; }
.slash::before { content: '＼'; margin-right: 5px; }
.slash::after { content: '／'; margin-left: 5px; }
@media screen and (max-width: 600px) { .slash-wrap { font-size: 15px; } }
</style>
<a href="https://app.miyakojima-rentacar.net/" style="display: inline-block; padding: 10px 20px; background-color: #F0D500; color: white; text-align: center; text-decoration: none; border-radius: 25px; font-size: 20px; width: 100%; box-sizing: border-box; margin: 10px 0 20px;">
<i class="bi bi-calendar-check me-2"></i><strong>宮古島レンタカーの料金・予約はこちら</strong>
</a>
<div class="container" style="padding-left: 20px; padding-right: 20px;">
<p class="p-0 m-0 mt-3" style="text-align: center;">
<a href="https://app.miyakojima-rentacar.net/" target="_blank" rel="noopener">
<img src="https://miyakojima-rentacar.net/article/wp-content/uploads/2025/10/yoyaku_banner.jpg"
alt="宮古島でレンタカーを借りるなら宮古島レンタカー"
style="width: 100%; max-width: 540px; height: auto;"
onmouseover="this.style.opacity='0.7';"
onmouseout="this.style.opacity='1';" />
</a>
</p>
</div>
<!------------ 沖縄情報局へ -------------->
<div style="margin: 40px 0; text-align: center;">
<a href="https://okinawa-rentalcar.net/article/" target="_blank" rel="noopener noreferrer">
<img class="okinawa-banner" src="https://miyakojima-rentacar.net/article/wp-content/uploads/2025/12/5be7eecaf807f14205b9a49353c6d0f2.jpg" alt="沖縄情報局｜沖縄本島の情報はこちらから"></a>
</div>
<style>
.okinawa-banner { max-width: 60%; height: auto; }
@media screen and (max-width: 768px) {
.okinawa-banner { max-width: 85%; height: auto; }
}
</style>
<!------------ 関連記事 -------------->
<div style="background:#f2f8fa; border-radius:12px; width: 100%; padding: 20px 10px; margin: 40px 0">
<div style="font-weight: bold; text-align: left; width: 100%; font-size: 1.3em; color: #2da8cc;"><span style="padding-left: 8px;">あわせて読みたい</span>
<div style="border-bottom:5px solid rgba(45,168,204,0.35); margin-top: 6px;"></div>
</div>
{related_posts_html}
</div>
<style>
/* PC: 横並び */
.layout-card { display: flex; flex-direction: row; align-items: center; }
.layout-card-img { max-width: 150px; }
/* SP: 縦並び＋画像100% */
@media screen and (max-width: 768px) {
.layout-card { flex-direction: column; }
.layout-card-img { width: 100%; height: auto; max-width: none; display: block; aspect-ratio: 16 / 9; object-fit: cover; }
}
</style>
<script>
document.addEventListener('DOMContentLoaded', function () {
document.querySelectorAll('.js-h1-title').forEach(function (titleEl) {
var link = titleEl.closest('a');
if (!link) {
titleEl.textContent = 'リンクなし';
return;
}
var url = link.href;
if (!url) {
titleEl.textContent = 'URLなし';
return;
}
titleEl.textContent = '読み込み中…';
fetch(url)
.then(function (response) {
if (!response.ok) {
throw new Error('HTTP ' + response.status);
}
return response.text();
})
.then(function (htmlText) {
var parser = new DOMParser();
var doc = parser.parseFromString(htmlText, 'text/html');
var h1 = doc.querySelector('h1');
if (!h1) {
throw new Error('H1 not found');
}
var text = h1.textContent.trim();
if (!text) {
throw new Error('H1 empty');
}
titleEl.textContent = text;
})
.catch(function (error) {
console.error('H1取得エラー:', url, error);
titleEl.textContent = 'タイトル取得エラー';
});
});
});
</script>
<!------------ INSTAGRAMバナー -------------->
<div class="ig-section">
<div class="ig-text"><span class="slash" style="display: inline-block;">Instagram開設しました！いいねとフォローお願いします♪</span></div>
<a href="https://www.instagram.com/miyakojima_real/" target="_blank" rel="noopener">
<img src="https://miyakojima-rentacar.net/article/wp-content/uploads/2025/12/okinawarentacar_instagram_banner.jpg" alt="沖縄レンタカー公式Instagramバナー"  style="max-width: 100%; height: auto; display: block; margin: 0 auto;"  /></a>
</div>
<style>
.ig-section { text-align: center; margin: 60px 0; }
.ig-text { text-align: center; font-size: 16px; margin-bottom: 5px; }
.slash { display: inline-block; }
.slash::before { content: '＼'; margin-right: 5px; }
.slash::after { content: '／'; margin-left: 5px; }
@media (max-width: 767px) {
.ig-section { text-align: center; margin: 40px 0; }
.ig-text { margin-bottom: 1px !important; font-size: 12px; }
}
</style>
<!-・//////////////////////////// CSS ///////////////////////////// -->
<style>
@media screen and (max-width: 768px) { .list-custom { font-size: 14px; } }
</style>
<style>
.list-custom { font-size: 16px; }
@media screen and (max-width: 768px) {
.list-custom { font-size: 14px; }
}
</style>
<style>
.rank-cell { vertical-align:middle; font-weight:bold; text-align:center; }
.item-cell, .reason-cell { word-wrap:break-word; }
@media screen and (max-width:768px){
.table.table-bordered.table-striped { font-size:12px!important; }
}
</style>
<style>
.chat-design{ width: 100%; margin: 2em auto; }
@media screen and (max-width: 767px) {
.chat-design{ width: 100%; margin: 2em auto; }
}
</style>
<!-・////////// テキストBOX /////////// -->
<style>
.list-1 { position: relative; display: block; width: 90%; margin: 10px auto; padding: 1.5em 2em 1.5em 1em; border: 2px solid #2589d0; border-radius: 12px; background: #fff; box-sizing: border-box; }
.list-1 > div { position: absolute; top: -0.85em; left: 1.2em; padding: 0 0.7em; background: #fff; color: #2589d0; font-weight: 600; font-size: 1em; border-radius: 10px; z-index: 10; line-height: 1.2; white-space: nowrap; }
.list-1 ol { list-style-type: decimal; list-style-position: outside;}
.list-1 li { word-break: break-word; }
.list-1 li::marker { color: #2589d0; font-size: 1.1em; }
@media (max-width: 600px) {
.list-1 { margin: 1.2em auto; width: 100%; padding: 1em 1em 1em 0em; }
.list-1 > div { left: 0.15em; font-size: 16px; white-space: normal; padding: 0; }
}
</style>
<!-・////////// ランキング /////////// -->
<style>
/* テキストBOXシンプルのCSS */
.list-8 { position: relative; display: block; max-width: 800px; width: 100%; margin-bottom: 1.8em; margin-top: 2em; padding: 1.5em 1em 1em 2.5em; border: 2px solid #d4af37; border-radius: 12px; background: #fff; box-sizing: border-box; }
/* タイトル（吹き出し風見出し） */
.list-8 > div { position: absolute; top: -0.85em; left: 1.2em; padding: 0 0.7em; background: #fff; color: #d4af37; font-weight: 600; font-size: 1.2em; border-radius: 10px; z-index: 10; line-height: 1.2; white-space: normal; max-width: calc(100% - 2em); }
/* リストスタイル */
.list-8 ol { list-style-type: disc; list-style-position: outside; margin: 0; padding-left: 1.3em; }
.list-8 li { padding: 0.3em 0.3em 0.3em 0; word-break: break-word; }
.list-8 li::marker { color: #2589d0; font-size: 1.2em; }
/* ---------- ランキング色（TOP3を金・銀・銅） ---------- */
.list-8.list-8-num li:nth-child(1)::marker { color: #b8860b; font-weight: 700; }
.list-8.list-8-num li:nth-child(2)::marker { color: #777; font-weight: 700; }
.list-8.list-8-num li:nth-child(n+4)::marker { color: #555; }
@media (max-width: 600px) {
.list-8 { width: 100%; padding-left: 1.8em; margin-top: 1.5em; margin-bottom: 1.2em; }
.list-8 > div { left: 0.6em; font-size: 0.95em; }
}
.list-8.list-8-num li { list-style: decimal outside !important; }
</style>
<!-・////////// 画像付き文章/////////// -->
<style>
.ranking-title{
border-bottom: 3px solid rgba(53,167,201,0.55);
width: 100%;
padding-bottom: 5px;
margin: 30px 0 15px;
}
.spot-wrap{
display:flex;
gap:20px;
align-items:center;
margin-bottom:20px;
}
.spot-img{
width:250px;
height:auto;
object-fit:cover;
flex-shrink:0;
margin:0 10px;
}
.spot-text{
flex:1;
line-height:1.9;
}
.ranking-table td:first-child{
width:32%;
background-color:#2589d0 !important;
color:#fff !important;
font-weight:bold;
text-align:center;
vertical-align:middle;
}
@media (max-width:768px){
.spot-wrap{
flex-direction:column;
align-items:flex-start;
width:100%;
gap:10px;
}
.spot-img{
width:100%;
max-width:200px !important;
height:auto;
margin:5px auto 0;
}
.spot-text{
width:100%;
}
.ranking-title{
width:100%;
min-width:0;
}
}
</style>
"""
    return template.replace("{related_posts_html}", related_posts_html)

def process_content_headings(content: str):
    """
    本文中の <h3>, <h4>, <h5> タグを抽出し、
    それぞれ <h2> (背景水色バー), <h3> (左縦線), <h4> (下線) にマッピングしつつ、
    適切なクラスやスタイル、IDを自動付与します。
    また、目次用の見出しタイトルのリストを返します。
    """
    import re
    headings = []
    
    # 1. AIが生成した <h3> を <h2> (背景水色バー) に変換し、セクションで囲む
    h3_counter = [0]
    
    def replace_h3_to_h2(match):
        inner_html = match.group(1)
        clean_text = re.sub(r'<[^>]+>', '', inner_html).strip()
        headings.append(clean_text)
        
        h3_counter[0] += 1
        idx = h3_counter[0]
        
        # 2番目以降の <h2> の前には前のセクションを閉じるタグを挿入
        if idx > 1:
            prefix = f'\n</section>\n<!--・/// start: {clean_text} ////// -->\n<section class="row mt-3">\n'
        else:
            prefix = f'\n<!--・/// start: {clean_text} ////// -->\n<section class="row mt-3">\n'
            
        return f'{prefix}<h2 id="toc-{idx}" class="fs-4 py-3 ps-2 text-white" style="background-color: #35a7c9;">{inner_html}</h2>'

    pattern_h3 = r'<h3[^>]*>(.*?)</h3>'
    modified_content = re.sub(pattern_h3, replace_h3_to_h2, content, flags=re.IGNORECASE)
    
    # 最後にセクションを閉じる
    if h3_counter[0] > 0:
        modified_content += "\n</section>\n"
        
    # 2. AIが生成した <h4> を <h3> (左縦線) に変換
    h4_counter = [0]
    def replace_h4_to_h3(match):
        inner_html = match.group(1)
        h4_counter[0] += 1
        idx = h4_counter[0]
        return f'<h3 id="h3-{idx}" class="fs-5 p-0 m-0 py-1 ps-3 mt-4" style="border-left: thick solid #35a7c9; line-height: 1.6; display: inline-block;">{inner_html}</h3>'
        
    pattern_h4 = r'<h4[^>]*>(.*?)</h4>'
    modified_content = re.sub(pattern_h4, replace_h4_to_h3, modified_content, flags=re.IGNORECASE)
    
    # 3. AIが生成した <h5> を <h4> (下線) に変換
    h5_counter = [0]
    def replace_h5_to_h4(match):
        inner_html = match.group(1)
        h5_counter[0] += 1
        idx = h5_counter[0]
        return f'<h4 id="h4-{idx}" class="ranking-title" style="margin-top: 40px;">{inner_html}</h4>'
        
    pattern_h5 = r'<h5[^>]*>(.*?)</h5>'
    modified_content = re.sub(pattern_h5, replace_h5_to_h4, modified_content, flags=re.IGNORECASE)
    
    return modified_content, headings


def build_intro_block(summary_items: list, headings: list) -> str:
    """
    「この記事で分かること」BOXと「アンカーリンク目次」のHTMLを生成します。
    """
    if not summary_items and not headings:
        return ""
        
    intro_html = ""
    
    # 1. 「この記事で分かること」BOXの生成
    if summary_items:
        li_items = "".join([f"  <li>{item}</li>\n" for item in summary_items])
        intro_html += f"""
<div style="border: 2px solid #35a7c9; padding: 25px 12px 10px; font-size: 1em; border-radius: 5px; position: relative; margin-bottom: 30px; margin-top: 10px;">
<div class="responsive-title" style="position: absolute; top: -12px; left: -1; background-color: #35a7c9; color: white; padding: 6px 10px; border-radius: 5px; font-size: 20px; white-space: nowrap;">■ この記事で分かること ■</div>
<ul class="responsive-text" style="margin-top: 30px; padding-left: 1.2em; line-height: 1.8;">
{li_items}</ul>
</div>
"""

    # 2. 「アンカーリンク目次」BOXの生成
    if headings:
        li_headings = ""
        for idx, heading in enumerate(headings, 1):
            li_headings += f'  <li><a href="#toc-{idx}" class="responsive-text" style="color: #35a7c9; text-decoration: none; font-weight: bold;">{heading}</a></li>\n'
            
        intro_html += f"""
<div style="border: 2px solid #35a7c9; padding: 25px 12px 10px; font-size: 1em; border-radius: 5px; position: relative; margin-bottom: 30px;">
<div class="responsive-title" style="position: absolute; top: -12px; left: -1; background-color: #35a7c9; color: white; padding: 6px 10px; border-radius: 5px; font-size: 20px; white-space: nowrap;">■ 目次 ■</div>
<ol class="responsive-text" style="margin-top: 30px; padding-left: 1.2em; line-height: 1.8; list-style-type: decimal; list-style-position: outside;">
{li_headings}</ol>
</div>
"""

    # レスポンシブ用の共通スタイル
    intro_html += """
<style>
@media screen and (max-width: 768px) {
.responsive-title { font-size: 17px !important; left: 50% !important; transform: translateX(-50%) !important; word-break: break-word !important; }
.responsive-text { font-size: 14px !important; word-break: break-word !important; }
}
</style>
"""
    return intro_html

def insert_intro_block(content: str, intro_block: str) -> str:
    import re
    # 置換後は <h2> が大見出しになっているので、最初の <h2> を探します
    match = re.search(r'<h2[^>]*>', content, re.IGNORECASE)
    if match:
        start_idx = match.start()
        return content[:start_idx] + intro_block + content[start_idx:]
    else:
        # もし <h2> がなければ <h3> を探します
        match_h3 = re.search(r'<h3[^>]*>', content, re.IGNORECASE)
        if match_h3:
            start_idx = match_h3.start()
            return content[:start_idx] + intro_block + content[start_idx:]
        return intro_block + content

def insert_spot_images_to_content(content: str, spots: list, api_key: str, save_dir: str, wp_url: str, username: str, app_password: str) -> str:
    """
    本文中の各スポットの見出しの直後に、Googleマップから自動取得した写真とクレジットを挿入します。
    """
    if not spots or not api_key or "your_google_maps_api_key" in api_key:
        return content
        
    import re
    modified_content = content
    
    for spot in spots:
        # 1. Googleマップから写真をダウンロード
        photo_info = download_photo_for_spot(spot, api_key, save_dir)
        if not photo_info:
            continue
            
        local_path = photo_info.get("local_path")
        credit_html = photo_info.get("credit_html")
        
        # 2. WordPressにアップロード
        print(f"📤 スポット写真 '{spot}' をWordPressにアップロード中...")
        upload_res = upload_image_to_wordpress_detailed(wp_url, username, app_password, local_path)
        if not upload_res:
            continue
            
        source_url = upload_res.get("source_url")
        
        # 3. 挿入するHTMLブロックを構築
        image_block = f"""
<div style="text-align: center; margin: 35px 0;">
  <img src="{source_url}" alt="{spot}" style="width: 100%; max-width: 600px; border-radius: 12px; height: auto; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
  {credit_html}
</div>
"""
        
        # 4. 本文の該当見出し（<h3>）の直後に挿入する
        # スポット名の一部でもマッチするように末尾の「ビーチ」等を取り除いて検索
        search_spot = spot
        if len(spot) > 4 and spot.endswith("ビーチ"):
            search_spot = spot[:-3]
        elif len(spot) > 3 and spot.endswith("店"):
            search_spot = spot[:-1]
            
        escaped_search = re.escape(search_spot)
        pattern = rf'<h3[^>]*>[^<]*?{escaped_search}[^<]*?</h3>'
        
        def insert_after_match(match):
            return match.group(0) + "\n" + image_block
            
        new_content, count = re.subn(pattern, insert_after_match, modified_content, count=1, flags=re.IGNORECASE)
        if count > 0:
            print(f"✅ スポット写真 '{spot}' を見出しの直後に自動挿入しました。")
            modified_content = new_content
        else:
            print(f"⚠️ スポット見出し '{search_spot}' が本文中に見つからなかったため、写真の自動挿入をスキップしました。")
            
    return modified_content

def main():
    print("==================================================")
    print("🌴 宮古島レンタカー ブログ記事自動生成＆投稿システム 🌴")
    print("==================================================")
    
    # 1. 設定ファイルのバリデーション（チェック）
    if not config.validate_config():
        sys.exit(1)
        
    # 2. キーワードリストの読み込み
    keywords_file = os.path.join(os.path.dirname(__file__), "keywords.json")
    if not os.path.exists(keywords_file):
        print(f"❌ エラー: キーワードファイル '{keywords_file}' が見つかりません。")
        sys.exit(1)
        
    try:
        with open(keywords_file, "r", encoding="utf-8") as f:
            keyword_list = json.load(f)
    except Exception as e:
        print(f"❌ エラー: キーワードファイルの読み込みに失敗しました: {e}")
        sys.exit(1)
        
    if not keyword_list:
        print("❌ エラー: キーワードリストが空です。")
        sys.exit(1)
        
    # 3. 記事テーマの選定
    if len(sys.argv) > 1:
        try:
            index = int(sys.argv[1])
            selected = keyword_list[index % len(keyword_list)]
            print(f"💡 コマンド引数より、リストの {index} 番目のテーマを執筆します。")
        except ValueError:
            selected = random.choice(keyword_list)
            print("💡 ランダムなテーマを執筆します。")
    else:
        selected = random.choice(keyword_list)
        print("💡 ランダムなテーマを執筆します。")
        
    keyword = selected.get("keyword")
    theme = selected.get("theme")
    sub_keywords = selected.get("sub_keywords", [])
    
    print(f"\n📌 今回執筆するテーマ:")
    print(f"  - テーマ名　: {theme}")
    print(f"  - 主要ワード: {keyword}")
    print(f"  - 関連ワード: {', '.join(sub_keywords)}")
    print("==================================================")
    
    # 4. WordPressから既存の投稿詳細情報を取得
    print("🔍 WordPressから過去の公開済み記事の一覧を取得しています...")
    existing_posts = get_existing_posts_detailed(
        wp_url=config.WP_URL,
        username=config.WP_USERNAME,
        app_password=config.WP_PASSWORD
    )
    
    # 重複回避用のタイトルリストを抽出
    existing_titles = [post['title'] for post in existing_posts]
    
    # 5. Gemini APIによる記事の生成 (既存タイトルを渡して重複回避)
    try:
        blog_post = generate_blog_article(
            api_key=config.GEMINI_API_KEY,
            keyword=keyword,
            theme=theme,
            sub_keywords=sub_keywords,
            existing_titles=existing_titles
        )
    except Exception as e:
        print("❌ 記事の生成に失敗したため、処理を中断します。")
        sys.exit(1)
        
    # 6. あわせて読みたい（関連記事）の自動選定と定型CTAのマージ
    print("🔗 今回の記事に関連する過去の記事を自動選定中...")
    related_posts = select_related_posts(
        current_title=blog_post.get("title", theme),
        current_keyword=keyword,
        existing_posts=existing_posts
    )
    
    # 定型CTAを生成
    cta_html = build_cta_html(related_posts)
    
    # 「この記事で分かること」BOXと目次を生成し、本文に挿入
    print("📝 「この記事で分かること」BOXと目次を生成し、本文に挿入中...")
    summary_items = blog_post.get("summary_items", [])
    processed_content, headings = process_content_headings(blog_post["content"])
    
    # 画像保存用のフォルダパスを設定
    image_folder = os.path.join(os.path.dirname(__file__), "images")
    
    # Googleマップの観光地写真の自動挿入
    spots = blog_post.get("spots", [])
    if spots and config.GOOGLE_MAPS_API_KEY and "your_google_maps_api_key" not in config.GOOGLE_MAPS_API_KEY:
        print(f"🗺️  Googleマップから {len(spots)} 個のスポット写真を自動取得し、挿入します...")
        processed_content = insert_spot_images_to_content(
            content=processed_content,
            spots=spots,
            api_key=config.GOOGLE_MAPS_API_KEY,
            save_dir=image_folder,
            wp_url=config.WP_URL,
            username=config.WP_USERNAME,
            app_password=config.WP_PASSWORD
        )
        
    intro_block = build_intro_block(summary_items, headings)
    blog_post["content"] = insert_intro_block(processed_content, intro_block)
    
    # 記事本文の末尾に定型CTAを結合します（※目次の誤検出を防ぐため、目次生成後に行います）
    blog_post["content"] += cta_html
        
    # 7. アイキャッチ画像の準備 (ハイブリッド選定ロジック)
    image_folder = os.path.join(os.path.dirname(__file__), "images")
    
    # 【ステップA】まずローカルの images フォルダをチェック（実写優先）
    image_path = get_random_image_from_folder(image_folder)
    
    # 【ステップB】ローカルに画像がなく、Unsplash APIキーが登録されていればネットから自動取得
    if not image_path:
        if config.UNSPLASH_ACCESS_KEY and "your_unsplash_access_key" not in config.UNSPLASH_ACCESS_KEY:
            image_keyword = blog_post.get("image_keyword", "okinawa beach")
            print(f"\n💡 ローカル画像が空のため、Unsplashから自動取得を試みます。")
            print(f"   (検索キーワード: {image_keyword})")
            
            image_path = download_image_from_unsplash(
                keyword=image_keyword,
                access_key=config.UNSPLASH_ACCESS_KEY,
                save_dir=image_folder
            )
        else:
            print("\n💡 ローカル画像がなく、Unsplash APIキーも未設定のため、画像なしで投稿します。")
            
    # 【ステップC】画像が準備できた場合は、文字入れバナーを生成してからWordPressへアップロード
    featured_media_id = None
    if image_path:
        print(f"\n🎨 画像にブログのタイトル文字を合成中...")
        banner_path = os.path.join(image_folder, "processed_banner.jpg")
        
        # AIが生成したバナー専用 of 改行入りタイトル・副題を取得
        # （存在しない場合のフォールバックとして従来の title と theme を設定）
        banner_title = blog_post.get("banner_title")
        banner_subtitle = blog_post.get("banner_subtitle")
        
        if not banner_title:
            banner_title = blog_post.get("title", theme)
            banner_subtitle = None
        
        # タイトル付きバナー画像を生成
        processed_image_path = create_title_banner(
            image_path=image_path,
            title=banner_title,
            output_path=banner_path,
            sub_title=banner_subtitle
        )
        
        print(f"📤 WordPressへアイキャッチ画像をアップロード中...")
        featured_media_id = upload_image_to_wordpress(
            wp_url=config.WP_URL,
            username=config.WP_USERNAME,
            app_password=config.WP_PASSWORD,
            image_path=processed_image_path
        )
        if not featured_media_id:
            print("⚠️ 画像のアップロードに失敗したため、画像なしで記事の投稿を継続します。")
            
    # 8. WordPressへの投稿 (安全のため下書き: status="draft")
    try:
        post_url = post_article_to_wordpress(
            wp_url=config.WP_URL,
            username=config.WP_USERNAME,
            app_password=config.WP_PASSWORD,
            title=blog_post.get("title", theme),
            content=blog_post.get("content", ""),
            excerpt=blog_post.get("meta_description", ""),
            featured_media_id=featured_media_id,
            status="draft"
        )
        print("==================================================")
        print("✨ すべての処理が正常に完了しました！")
        print(f"WordPressの管理画面にログインし、下書きを確認してください。")
        print("==================================================")
    except Exception as e:
        print(f"❌ WordPressへの投稿に失敗しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
