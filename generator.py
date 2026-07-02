import os
import re
from google import genai
from google.genai import types
from anthropic import Anthropic
import config

def generate_blog_article(
    api_key: str, 
    keyword: str = None, 
    theme: str = None, 
    sub_keywords: list = None, 
    existing_titles: list = None,
    use_trend_research: bool = False,
    trend_genre: str = "すべて",
    ai_model: str = "gemini"
) -> dict:
    client = None
    if ai_model.lower() == "gemini":
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
        if ai_model.lower() == "claude":
            # Claudeの場合、検索機能がないため、まずGeminiを使ってGoogle検索でリサーチを行います（ハイブリッド構成）
            gemini_key = config.GEMINI_API_KEY
            if not gemini_key or "your_gemini_api_key" in gemini_key:
                raise Exception("トレンドリサーチモードでClaudeを使用するには、システム設定でGemini APIキーも入力してください。")
            
            print("🔍 Gemini APIとGoogle検索を使用して最新情報をリサーチ中...")
            research_client = genai.Client(api_key=gemini_key)
            genre_str = f"特に指定されたジャンル「{trend_genre}」に関連する最新トレンド" if trend_genre else "最新の観光情報やイベント"
            research_prompt = f"""
Google検索ツールを使って、2026年現在の宮古島に関する{genre_str}について詳しくリサーチしてください。
最近（2025〜2026年）オープンしたお店、開催予定のイベント、観光客に話題の過ごし方などを箇条書きで具体的にまとめてください。
"""
            research_response = research_client.models.generate_content(
                model='gemini-3.5-flash',
                contents=research_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    tools=[{"google_search": {}}],
                ),
            )
            research_result = research_response.text
            
            prompt_topic = f"""
【今回の指令 (最新トレンドリサーチ)】
以下は、Google検索ツールによってリサーチされた2026年現在の宮古島の最新情報です：
---
{research_result}
---

上記の最新情報の中から、読者（特にレンタカーを利用する観光客）が「今最も知りたい！行ってみたい！」と感じるようなテーマを1つ厳選し、その情報を中心に深く掘り下げた魅力的なブログ記事を執筆してください。
記事のタイトル、主要キーワード、関連キーワードは、あなたのリサーチ結果に基づいて自動でふさわしいものを決定し、出力フォーマットに従って出力してください。
"""
        else:
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
3. **【参考URLとGoogleマップリンクのまとめ化ルール（最重要）】**
   - 読者が記事の途中で外部サイトへ離脱するのを防ぎ、かつ読みやすさを向上させるため、**本文中には外部サイト（公式サイト、Wikipedia、観光協会など）やGoogleマップのリンクは絶対に挿入しないでください。**
   - また、「※最新情報や営業時間は末尾の参考リンクをご確認ください」といった注記も、各スポットごとに何回も書くと記事が非常に見づらくなります。そのため、**本文中の各スポット紹介にはこれらのリンクや注記を一切書かないでください。**
   - すべてのリンク（公式サイト、Wikipedia、Googleマップ位置情報リンクなど）は、記事の最後（「まとめ」の直後）に、以下のHTML構造を使って「参考リンクBOX」として1箇所にまとめて出力してください。
   - 参考リンクBOXの直前に、「※各スポットの最新情報・営業時間やGoogleマップ位置情報は、以下の参考リンクをご確認ください。」という注記を**1度だけ**記載してください。
   ```html
   <div class="c-box-2" style="position: relative; padding: 20px; border: 1px solid #000; border-radius: 14px;">
   <ul style="margin: 0; padding-left: 1.2em; color: #666; list-style-type: disc;">
    	<li>参考１：スポット名 「<a href="公式サイトURL" target="_blank" rel="noopener noreferrer nofollow">公式サイト</a>」「<a href="https://www.google.com/maps/search/?api=1&query=スポット名" target="_blank" rel="noopener noreferrer nofollow">Googleマップで見る</a>」</li>
    	<li>参考２：スポット名 「<a href="公式サイトURL" target="_blank" rel="noopener noreferrer nofollow">公式サイト</a>」「<a href="https://www.google.com/maps/search/?api=1&query=スポット名" target="_blank" rel="noopener noreferrer nofollow">Googleマップで見る</a>」（Wikipedia等の情報源があれば「<a href="WikipediaのURL" target="_blank" rel="noopener noreferrer nofollow">Wikipedia</a>」も並べる）</li>
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
4. 営業情報や料金など、時期によって変更されやすい情報については、上記の参考リンクBOX付近で「※最新情報は各施設の公式サイトなどをご確認ください」といった旅行者への注意喚起を1箇所にまとめて含めてください。

【記事品質ルール（最重要）】

旅行者が「この情報があって良かった」と感じられる実用的な記事を作成してください。
単なる観光スポット紹介や特徴の説明だけで終わることは禁止します。

スポット・施設・イベントを紹介する際は、可能な限り以下の情報を含めてください。

■必須
・どのような人におすすめか
・おすすめしない人
・滞在時間の目安
・おすすめの時間帯
・訪問前の注意点
・レンタカー利用者向けアドバイス

■情報が確認できる場合のみ
・混雑しやすい時間帯
・予算の目安
・駐車場情報
・写真映えする時間帯
・ベストシーズン
・近くに立ち寄れるスポット

上記は単なる箇条書きではなく、本文の流れの中で自然に解説してください。

読者が

「行くべきか」
「いつ行くべきか」
「どのくらい滞在するべきか」
「何に注意すればよいか」

まで判断できる内容にしてください。

各h4の本文は300〜500文字以上とし、

・理由
・背景
・具体例
・他スポットとの違い
・現地スタッフだから分かる実用情報

を必ず含めてください。

「○○がおすすめです」「景色がきれいです」だけの紹介記事は禁止します。


【現地スタッフ視点】

各スポットにつき最低1回は、
「現地スタッフから見ると」
「実際にお客様をご案内していると」
「レンタカー利用者は」
など、現地スタッフならではの視点・注意点・実務的なアドバイスを含めてください。


【検索上位記事との差別化】

Google検索結果を要約しただけの記事は禁止します。

各見出しでは

・なぜそうなのか
・他との違い
・旅行者が失敗しやすいポイント
・現地だから分かる情報

まで掘り下げて解説してください。

読者が「へぇ、知らなかった」と思える情報を、各h4ごとに最低3つ含めてください。


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

    print(f"🤖 {ai_model.upper()}を使用して記事を生成中... (モード: {'トレンドリサーチ' if use_trend_research else 'テーマ指定'})")
    
    try:
        text = ""
        if ai_model.lower() == "gemini":
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.6,
                    tools=[{"google_search": {}}],
                ),
            )
            text = response.text
        elif ai_model.lower() == "claude":
            print("✍️ Claude Sonnet 4.6 を使用して執筆中...")
            claude_client = Anthropic(api_key=api_key)
            response = claude_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4000,
                temperature=0.6,
                system="あなたは宮古島のレンタカー会社「宮古島レンタカー」のブログ編集部（現地スタッフ）です。提供されたフォーマットと厳格なルールに従って、日本語でブログ記事を出力してください。",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            text = response.content[0].text
            
        if not text:
            raise Exception(f"{ai_model.upper()} API から応答テキストが返されませんでした。")
        
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
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            friendly_msg = build_friendly_429_message(error_msg)
            print(f"❌ {friendly_msg}")
            raise RuntimeError(friendly_msg) from e
            
        print(f"❌ 記事生成中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        raise e

def build_friendly_429_message(original_error_msg: str) -> str:
    import re
    from datetime import datetime, timedelta

    # 秒数を抽出するパターン
    # 例： "Please retry in 39.817274777s."
    retry_match = re.search(r'Please retry in\s+([0-9\.]+)\s*s', original_error_msg, re.IGNORECASE)
    # 例： "'retryDelay': '39s'"
    delay_match = re.search(r"['\"]retryDelay['\"]\s*:\s*['\"]([0-9\.]+)\s*s['\"]", original_error_msg, re.IGNORECASE)
    
    seconds = None
    if retry_match:
        try:
            seconds = float(retry_match.group(1))
        except ValueError:
            pass
    elif delay_match:
        try:
            seconds = float(delay_match.group(1))
        except ValueError:
            pass

    header = "🚨 Gemini APIの利用制限（429 RESOURCE_EXHAUSTED）に達しました。\n"
    reason = "無料枠の制限（1日あたり20リクエスト、または1分あたりの上限）を超えたため、一時的にAPIが利用できなくなっています。\n\n"
    
    if seconds is not None:
        now = datetime.now()
        resume_time = now + timedelta(seconds=seconds)
        
        # 待機時間の表記フォーマット
        if seconds < 60:
            wait_str = f"約 {int(seconds)} 秒間"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            sec = int(seconds % 60)
            wait_str = f"約 {minutes} 分 {sec} 秒間"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            sec = int(seconds % 60)
            wait_str = f"約 {hours} 時間 {minutes} 分 {sec} 秒間"

        # 再開予想時刻のフォーマット（日付が変わるかをチェック）
        if resume_time.date() > now.date():
            time_format = resume_time.strftime("明日 %m月%d日 %H時%M分%S秒")
        else:
            time_format = resume_time.strftime("%H時%M分%S秒")

        time_info = f"🕒 【再開予定時刻】\n{time_format} までお待ちください。（待機時間：{wait_str}）\n\n"
    else:
        time_info = "🕒 【再開予定時刻】\nしばらく時間（数分〜数時間）を置いてから再度お試しください。\n\n"

    suggestions = (
        "💡 【解決策】\n"
        "1. 上記の再開予定時刻まで待ってから、もう一度実行する。\n"
        "2. Google AI Studio ( https://aistudio.google.com/ ) で新しい別の無料APIキーを取得し、システム設定から入れ替える。\n"
        "3. Google AI Studioで支払い方法（クレジットカード等）を登録し、有料プラン（従量課金）へ移行して制限を解除する。"
    )
    
    return header + reason + time_info + suggestions


def rewrite_blog_article(
    api_key: str,
    original_title: str,
    original_content: str,
    low_performing_queries: list,
    ai_model: str = "gemini"
) -> dict:
    """
    指定された記事のタイトル、本文と、Search Consoleから抽出した流入キーワード（クエリ）のリストを受け取り、
    それらのクエリに対する読者の検索意図を満たす情報を本文中に自然に加筆・補強したリライト記事を生成します。
    """
    client = None
    if ai_model.lower() == "gemini":
        client = genai.Client(api_key=api_key)
        
    queries_str = "、".join(low_performing_queries) if low_performing_queries else "なし"
    
    prompt = f"""
あなたは宮古島のレンタカー会社「宮古島レンタカー」のブログ編集部（現地スタッフ）です。
既存のブログ記事をリライト（自動改善）して、検索エンジンでの掲載順位を上げ、かつ読者にとってより実用的で魅力的な内容にアップデートしてください。

【元記事情報】
元タイトル: {original_title}
元本文（HTML形式）:
---
{original_content}
---

【改善のために狙う検索キーワード（クエリ）】
以下のキーワードで検索する読者の疑問やインテント（知りたいこと）に答える情報を、記事の中に自然に加筆してください：
{queries_str}

【執筆・リライトルール】
1. **実用情報の追加**: 
   狙うキーワードに対する具体的な回答（理由、背景、現地スタッフならではの実用アドバイス等）を既存の構成や本文の自然な流れの中に肉付けしてください。
   単にキーワードを羅列するのではなく、本文に溶け込ませてください。
2. **既存の構成・HTMLタグの維持**:
   既存の <h2>, <h3>, <h4> などの見出し構成や全体的な流れは極力維持しつつ、不足している情報を加筆・書き換えてください。
   WordPress用のHTMLタグ（<h3>/<h4>/<h5>/p/ul/li）の形式で出力してください。
   ※ ページ全体を囲む <html> や <body> などのタグは含めないでください。
3. **文字数と品質**:
   加筆する見出し（特に中見出し）の本文は300〜500文字以上とし、内容を薄めずに掘り下げてください。
4. **【参考URLとGoogleマップリンクのまとめ化ルール（最重要）】** およびCTA、監修クレジットなどの定型部分が元記事に含まれている場合、リライト後の本文中にも崩さずに残すか、不要な場合は削除しないようにしてください。今回の出力は、純粋に「本文全体のHTML」のみを出力してください。

【出力フォーマット】
プログラムで正しく抽出するために、必ず以下のタグで囲んで出力してください。前置きや解説テキストは一切不要です。

[TITLE_START]
改善後の新しい記事のタイトル（必要に応じて、よりクエリに合致し魅力的なタイトルへ修正してください。修正不要なら元タイトルをそのまま使用してください。改行なしプレーン）
[TITLE_END]

[META_START]
検索用メタディスクリプション（改善した内容に合うように新しく作成してください）
[META_END]

[CONTENT_START]
リライト後のHTML形式の記事本文全体
[CONTENT_END]
"""

    print(f"🤖 {ai_model.upper()}を使用して記事をリライト（自動改善）中... (対象記事: {original_title})")
    
    try:
        text = ""
        if ai_model.lower() == "gemini":
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
            )
            text = response.text
        elif ai_model.lower() == "claude":
            claude_client = Anthropic(api_key=api_key)
            response = claude_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4000,
                temperature=0.6,
                system="あなたは宮古島のレンタカー会社「宮古島レンタカー」のブログ編集部（現地スタッフ）です。提供されたフォーマットとルールに従って、日本語でリライト後のブログ記事を出力してください。",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            text = response.content[0].text
            
        if not text:
            raise Exception(f"{ai_model.upper()} API から応答テキストが返されませんでした。")
        
        title_match = re.search(r'\[TITLE_START\](.*?)\[TITLE_END\]', text, re.DOTALL)
        meta_match = re.search(r'\[META_START\](.*?)\[META_END\]', text, re.DOTALL)
        content_match = re.search(r'\[CONTENT_START\](.*?)\[CONTENT_END\]', text, re.DOTALL)
        
        title = original_title
        meta = "宮古島レンタカーのおすすめブログ記事です。"
        content = text
        
        if title_match: title = title_match.group(1).strip()
        if meta_match: meta = meta_match.group(1).strip()
        if content_match: content = content_match.group(1).strip()
        
        title = re.sub(r'^#+\s*', '', title)
            
        return {
            "title": title,
            "meta_description": meta,
            "content": content
        }
        
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            friendly_msg = build_friendly_429_message(error_msg)
            print(f"❌ {friendly_msg}")
            raise RuntimeError(friendly_msg) from e
            
        print(f"❌ 記事リライト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        raise e


