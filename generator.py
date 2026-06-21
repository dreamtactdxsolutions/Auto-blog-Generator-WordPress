import os
import re
from google import genai
from google.genai import types
def generate_blog_article(
    api_key: str, 
    keyword: str = None, 
    theme: str = None, 
    sub_keywords: list = None, 
    existing_titles: list = None,
    use_trend_research: bool = False,
    trend_genre: str = "すべて"
) -> dict:
    client = genai.Client(api_key=api_key)
    
    existing_titles_section = ""
    if existing_titles:
        existing_titles_list_str = "\n".join([f"- {title}" for title in existing_titles])
        existing_titles_section = f"""
【重複回避ルール (重要)】
以下のタイトルは既にブログ内に存在します。今回の記事がこれらと内容やテーマ、切り口において重複（かぶり）しないように、新しい視点や独自のアプローチで執筆してください：
{existing_titles_list_str}
"""
    
    if use_trend_research:
        genre_str = f"特に指定されたジャンル「{trend_genre}」に関連する最新トレンドに注目してください。" if trend_genre else ""
        prompt_topic = f"""
【今回の指令 (最新トレンドリサーチ)】
Google検索ツールを使って、2026年現在の宮古島に関する最新の観光情報や流行の話題をくまなくリサーチしてください。
{genre_str}
例えば、以下のようなトピックを調べてリサーチのヒントにしてください：
1. 最近（特に2025〜2026年）オープンした新しいカフェ、レストラン、新名所（例：トゥリバー地区の「Yard miyakojima」など）、商業施設、新しいホテル（例：「キャノピーbyヒルトン沖縄宮古島リゾート」など）
2. 近々開催される予定の人気イベントや季節のフェスティバル（例：10月開催予定の「MIYAKO ISLAND ROCK FESTIVAL 2026」や夏祭りなど）
3. 2026年の旅行客に今最もホットな話題や、トレンドの楽しみ方・過ごし方

上記の検索結果から、読者（特にレンタカーを利用する観光客）が「今最も知りたい！行ってみたい！」と感じるようなテーマを1つ厳選し、そのトレンド情報を中心に深く掘り下げた魅力的なブログ記事を執筆してください。
記事のタイトル、主要キーワード、関連キーワードは、あなたのリサーチ結果に基づいて自動でふさわしいものを決定し、出力フォーマットに従って出力してください。
"""
    else:
        sub_keywords_str = "、".join(sub_keywords) if sub_keywords else ""
        prompt_topic = f"""
【今回の記事のテーマ】
テーマ: {theme}
主要キーワード: {keyword}
関連キーワード: {sub_keywords_str}
"""

    prompt = f"""
あなたは宮古島のレンタカー会社「宮古島レンタカー」のブログ編集部（現地スタッフ）です。
宮古島への旅行を計画している読者、または興味を持っている読者に向けた、魅力的で非常に信頼性の高いブログ記事を書いてください。


{prompt_topic}
{existing_titles_section}

【ファクトチェックと情報源 (最重要)】
1. あなたには「Google検索ツール」が提供されています。宮古島の最新の観光スポット情報、駐車場の有無、移動所要時間、注意点など、あやふやな点や具体的なデータは必ず検索して確認し、正確な事実のみを記載してください。
2. 嘘の情報や、古い情報を書かないように、ファクトチェックを十分にチェックしてください。
3. **【参考URLリンクのまとめ化ルール】**
   読者が記事の途中で外部サイトへ離脱するのを防ぎ、最後まで記事を読んでもらえるようにするため、**本文中には外部サイト（公式サイト、Wikipedia、観光協会など）への直接リンクは絶対に挿入しないでください。**
   代わりに、各スポットを紹介する本文中では、「※最新情報や営業時間は記事末尾の参考リンクをご確認ください」や「※詳細は記事末尾の参考サイトにまとめられています」のように、最後にリンクをまとめている旨を記載してください。
   そして、記事の最後（「まとめ」の直後）に、紹介した各観光地の参考リンク（公式サイト、Wikipedia、沖縄観光情報WEBサイト おきなわ物語など）を、以下のHTML構造を使ってまとめて出力してください。紹介したスポットに合わせて、参考１、参考２……のようにリストを作成してください。
   ```html
   <div class="c-box-2" style="position: relative; padding: 20px; border: 1px solid #000; border-radius: 14px;">
   <ul style="margin: 0; padding-left: 1.2em; color: #666; list-style-type: disc;">
    	<li>参考１：スポット名 「<a href="公式サイトURL" target="_blank" rel="noopener noreferrer nofollow">公式サイト名など</a>」「<a href="WikipediaのURL" target="_blank" rel="noopener noreferrer nofollow">Wikipedia</a>」</li>
    	<li>参考２：スポット名 「<a href="公式サイトURL" target="_blank" rel="noopener noreferrer nofollow">公式サイト名など</a>」「<a href="おきなわ物語などのURL" target="_blank" rel="noopener noreferrer nofollow">おきなわ物語</a>」</li>
   </ul>
   </div>
   <style>
   .c-box-2{{ width:fit-content; max-width:100%; margin:30px 0; }}
   .c-box-2 ul{{ font-size:0.9em; }}
   .c-box-2 ul li::marker{{font-size:0.7em;}}
   @media screen and (max-width:768px){{
   .c-box-2{{ display:block; width:90%; margin:20px auto; padding:5px 12px 15px 10px!important;}}
   .c-box-2 ul{{ font-size:0.8em; }}
   }}
   </style>
   ```
4. **【Googleマップリンクは本文中に残す】**
   読者が現地でナビゲーションしやすいように、紹介する主要な観光地やお店について、Google Mapの検索リンクは本文中にそのまま挿入してください。
   リンク形式: `<a href="https://www.google.com/maps/search/?api=1&query=施設名" target="_blank" rel="noopener">Googleマップで見る</a>`
   例: 「※詳細な営業時間は末尾の参考リンクの公式サイトをご確認ください。（地図：<a href="https://www.google.com/maps/search/?api=1&query=砂山ビーチ" target="_blank" rel="noopener">Googleマップで見る</a>）」
5. 営業情報や料金など、時期によって変更されやすい情報については、「※最新情報は各施設の公式サイトなどをご確認ください」といった旅行者への注意喚起を必ず適切に含めてください。

【記事の執筆ルール（書式とトーン）】
1. **ペルソナとトーン**:
   - あなたは「宮古島レンタカーのブログ編集部（現地スタッフ）」としての立ち位置で執筆してください。「宮古島レンタカー」は会社・サービス名ですので、個人名のように自己紹介をさせないでください（例：「私『宮古島レンタカー』です」などの自己紹介は絶対に禁止です）。
   - 冒頭での過度な自己紹介は不要です。読者への歓迎や挨拶（例：「はいさい！宮古島旅行を計画中の皆さん〜」など）から自然に本題へ入ってください。
   - 親しみやすく、温かみがありつつも、観光ガイドとして信頼に値する丁寧で理路整然とした言葉遣い（例：「〜ですよね！」「〜をご紹介します。」など）にしてください。
   - 単なる紹介にとどまらず、「現地スタッフからのドライブの際のアドバイス（駐車場が混みやすい時間、日差しの強さ等）」を交えて実用性を高めてください。

2. **構成と構成タグ（HTML形式）**:
   - 本文はWordPressにそのまま貼り付けられるHTML形式で出力してください。
   - `<h3>`（大見出し）、`<h4>`（中見出し）、`<p>`（本文段落）、`<ul>`/`<li>`（リスト形式の箇条書き）を使って、綺麗に整理されたブログ記事の書式にしてください。
   - ※ `<html>` や `<body>`、`<!DOCTYPE>` などのページ全体を囲うタグは**絶対に含めない**でください。
   - ※ 記事の最後には、以下の監修クレジットをそのまま必ず含めてください：
     `<p style="text-align: right; color: #666; font-size: 0.9em; margin-top: 30px;">宮古島観光ガイド編集部（監修）</p>`

3. **レンタカーへの自然な誘導（CTA）**:
   - 記事の最後（まとめの前、またはまとめの中）で、「宮古島には電車がなくバスの便も限られているため、限られた旅行時間を有意義に使い、絶景スポットをスムーズに巡るするにはレンタカーが絶対に欠かせない」という点に触れてください。
   - その上で、「宮古島レンタカー」（リンク先URL: https://app.miyakojima-rentacar.net/ ）への自然なテキストリンクでの案内文を含めてください。
   - **注意（最重要）**: バナー画像、ボタン風デザインの大きなHTMLブロック、スタイルシートはAI側では**絶対に出力しないでください**（プログラム側で末尾に完全な定型バナー・ボタン群を自動結合するため、内容が二重になるのを防ぐためです）。テキストによる自然な紹介リンクのみにしてください。
     例: 「宮古島を快適にドライブするなら、事前のご予約が安心です。<a href="https://app.miyakojima-rentacar.net/">宮古島レンタカーの予約はこちら</a>からどうぞ。」

【出力フォーマット】
プログラムで正しく抽出するために、必ず以下のタグで囲んで出力してください。前置きや解説テキストは一切不要です。

[TITLE_START]
記事のタイトル（WordPress用：改行なしのプレーンなタイトル）
[TITLE_END]

[KEYWORD_START]
今回の記事で最も中心となる主要なSEOキーワード（例：宮古島 新店舗、宮古島 ロックフェス など、2語からなるキーワード。テーマ指定モードの場合は指定された主要キーワードをそのまま出力してください）
[KEYWORD_END]

[SUB_KEYWORDS_START]
関連するキーワード（例：Yard miyakojima, 開業, トゥリバー など。テーマ指定モードの場合は指定された関連キーワードをそのままカンマ区切りで出力してください）
[SUB_KEYWORDS_END]

[BANNER_TITLE_START]
バナー画像に合成するメインタイトル（記事タイトルの前半部分）。
バナーにしたときに読みやすくなるよう、言葉の意味や文節の区切りなど、最も自然な位置にあらかじめ改行コード（実際の改行）を1箇所挿入してください。1行あたり10〜15文字程度、全体で2行以内に収まるようにしてください。
（例：【宮古島3泊4日】初めてでも安心！ ➔ 「【宮古島3泊4日】\\n初めてでも安心！」 のように改行を含める）
[BANNER_TITLE_END]

[BANNER_SUBTITLE_START]
バナー画像に合成するサブタイトル（記事タイトルの前半部分）。
同様に、言葉の意味や文節の区切りなど、最も自然な位置にあらかじめ改行コード（実際の改行）を1箇所挿入してください。1行あたり12〜17文字程度、全体で2行以内に収まるようにしてください。前後に「- 」を付与する必要はありません（描画プログラム側で自動付与します）。
（例：絶景満喫＆レンタカー完全攻略モデルコース ➔ 「絶景満喫＆レンタカー\\n完全攻略モデルコース」 のように改行を含める）
[BANNER_SUBTITLE_END]

[SUMMARY_START]
この記事を読むと分かることを、記事の内容に合わせて簡潔な箇条書き（要点4点）で出力してください。
（例：
- 宮古島でおすすめの絶景ビーチ5選
- 旅行目的別に選ぶ最適なビーチの選び方
- 透明度抜群の海が持つ特徴と海況の注意点
- レンタカーで巡る空港別のドライブコース
）
※ 「- 」などのプレーンな箇条書き形式（マークダウン）で出力してください。HTMLの <li> タグはAI側では出力しないでください。
[SUMMARY_END]

[META_START]
検索用メタディスクリプション
[META_END]

[IMAGE_KEYWORD_START]
この記事の内容に最もマッチする「Unsplashでの英語画像検索用キーワード」（例: okinawa beach, mango dessert, miyako bridge, tropical driving など。単語2つ程度の英語）を1つ出力してください。
[IMAGE_KEYWORD_END]

[SPOTS_START]
この記事の中で紹介した主要な観光スポット、ビーチ、お店などの「正式名称（Googleマップで検索できる正確な日本語の名称）」を、紹介した順番に1行に1つずつ出力してください。前後に「- 」や番号などは付けないでください。
（例：
与那覇前浜ビーチ
砂山ビーチ
新城海岸
）
[SPOTS_END]

[CONTENT_START]
HTML形式の記事本文
[CONTENT_END]
"""

    print(f"🤖 Gemini APIを使用して記事を生成中... (モード: {'トレンドリサーチ' if use_trend_research else 'テーマ指定'}) (Google検索グラウンディング有効)")
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.6,
                tools=[{"google_search": {}}],
            ),
        )
        
        text = response.text
        if not text:
            raise Exception("Gemini API から応答テキストが返されませんでした。")
        
        title_match = re.search(r'\[TITLE_START\](.*?)\[TITLE_END\]', text, re.DOTALL)
        keyword_match = re.search(r'\[KEYWORD_START\](.*?)\[KEYWORD_END\]', text, re.DOTALL)
        sub_kws_match = re.search(r'\[SUB_KEYWORDS_START\](.*?)\[SUB_KEYWORDS_END\]', text, re.DOTALL)
        banner_title_match = re.search(r'\[BANNER_TITLE_START\](.*?)\[BANNER_TITLE_END\]', text, re.DOTALL)
        banner_subtitle_match = re.search(r'\[BANNER_SUBTITLE_START\](.*?)\[BANNER_SUBTITLE_END\]', text, re.DOTALL)
        summary_match = re.search(r'\[SUMMARY_START\](.*?)\[SUMMARY_END\]', text, re.DOTALL)
        meta_match = re.search(r'\[META_START\](.*?)\[META_END\]', text, re.DOTALL)
        image_kw_match = re.search(r'\[IMAGE_KEYWORD_START\](.*?)\[IMAGE_KEYWORD_END\]', text, re.DOTALL)
        spots_match = re.search(r'\[SPOTS_START\](.*?)\[SPOTS_END\]', text, re.DOTALL)
        content_match = re.search(r'\[CONTENT_START\](.*?)\[CONTENT_END\]', text, re.DOTALL)
        
        title = theme if theme else "宮古島最新ガイド"
        ret_keyword = keyword if keyword else "宮古島 観光"
        ret_sub_keywords = sub_keywords if sub_keywords else []
        banner_title = ""
        banner_subtitle = ""
        summary_items = []
        spots = []
        meta = "宮古島レンタカーのおすすめブログ記事です。"
        image_keyword = "okinawa beach"
        content = text
        
        if title_match: title = title_match.group(1).strip()
        if keyword_match: ret_keyword = keyword_match.group(1).strip()
        if sub_kws_match:
            raw_sub = sub_kws_match.group(1).strip()
            ret_sub_keywords = [k.strip() for k in raw_sub.replace("、", ",").split(",") if k.strip()]
        if banner_title_match: banner_title = banner_title_match.group(1).strip()
        if banner_subtitle_match: banner_subtitle = banner_subtitle_match.group(1).strip()
        if meta_match: meta = meta_match.group(1).strip()
        if image_kw_match: image_keyword = image_kw_match.group(1).strip()
        if content_match: content = content_match.group(1).strip()
        
        if spots_match:
            for line in spots_match.group(1).strip().split('\n'):
                line = line.strip()
                line = re.sub(r'^[-*・\d+\.\s]+', '', line).strip()
                if line:
                    spots.append(line)
        
        if summary_match:
            for line in summary_match.group(1).strip().split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('*') or line.startswith('・'):
                    item = re.sub(r'^[-*・]\s*', '', line).strip()
                    if item:
                        summary_items.append(item)
                        
        while len(summary_items) < 4:
            summary_items.append("宮古島のレンタカーで巡るおすすめ情報")
        
        title = re.sub(r'^#+\s*', '', title)
        image_keyword = " ".join(image_keyword.split())
            
        return {
            "title": title,
            "keyword": ret_keyword,
            "sub_keywords": ret_sub_keywords,
            "banner_title": banner_title,
            "banner_subtitle": banner_subtitle,
            "summary_items": summary_items,
            "spots": spots,
            "meta_description": meta,
            "image_keyword": image_keyword,
            "content": content
        }
        
    except Exception as e:
        print(f"❌ 記事生成中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        raise e
