import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

def download_font_if_not_exists(font_dir: str = "fonts") -> str:
    """
    Google Fonts から Dela Gothic One フォントをダウンロードしてローカルに保存します。
    """
    os.makedirs(font_dir, exist_ok=True)
    font_path = os.path.join(font_dir, "DelaGothicOne-Regular.ttf")
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/delagothicone/DelaGothicOne-Regular.ttf"
        print(f"📥 Dela Gothic One フォントをダウンロードしています... ({url})")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(font_path, "wb") as f:
            f.write(response.content)
        print(f"✅ フォントのダウンロードが完了しました: {font_path}")
    return font_path

def split_title(title: str):
    """
    タイトルをメインタイトル（前半）とサブタイトル（後半）に分割します。
    「！」や「？」などの区切り文字で分割を試みます。
    """
    delimiters = ["！", "!", "？", "?", "｜", "|", "：", ":", "　", " - ", " -"]
    
    main_title = ""
    sub_title = ""
    
    # 記号での分割を試みる
    split_done = False
    for delim in delimiters:
        if delim in title:
            parts = title.split(delim, 1)
            # 区切り文字自身をメインタイトルに含める (「！」など)
            if delim in ["！", "!", "？", "?"]:
                main_title = parts[0] + delim
            else:
                main_title = parts[0]
            
            sub_title = parts[1]
            split_done = True
            break
            
    if not split_done or not main_title.strip() or not sub_title.strip():
        # 分割できなかった場合、あるいはどちらかが空の場合は文字数で半分に分割する
        length = len(title)
        if length > 12:
            half = length // 2
            main_title = title[:half]
            sub_title = title[half:]
        else:
            main_title = title
            sub_title = ""
            
    # サブタイトルの前後に既存サンプルのように「- 」を付与する（すでについていなければ）
    sub_title = sub_title.strip()
    if sub_title and not (sub_title.startswith("-") or sub_title.startswith("ー")):
        sub_title = f"- {sub_title} -"
        
    return main_title.strip(), sub_title.strip()

def wrap_text_by_length(text: str, max_chars: int) -> str:
    """
    テキストが極端に長い場合（max_charsを超える場合）のみ、適切に改行を入れます。
    単に1文字ずつぶつ切りにするのではなく、なるべく区切りの良いところか、文字数の真ん中あたりで改行します。
    """
    if not text:
        return ""
    if "\n" in text:
        return text
    
    # max_chars以下なら改行しない（スケーリングに任せる）
    if len(text) <= max_chars:
        return text
        
    # 区切り文字があればそこで改行を試みる
    for sep in ["　", " ", "、", ","]:
        if sep in text:
            parts = text.split(sep, 1)
            if parts[0] and parts[1]:
                return f"{parts[0]}\n{parts[1]}"
                
    # なければ真ん中付近で改行する
    mid = len(text) // 2
    return f"{text[:mid]}\n{text[mid:]}"

def get_scaled_font(text: str, font_path: str, initial_size: int, max_width: int, stroke_width: int):
    """
    指定した最大幅に収まるように、フォントサイズを自動で縮小して返します。
    """
    font_size = initial_size
    dummy_img = Image.new("RGBA", (1200, 630))
    dummy_draw = ImageDraw.Draw(dummy_img)
    
    while font_size > 20:
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception as e:
            print(f"Font error: {e}")
            return ImageFont.load_default(), font_size
            
        max_line_w = 0
        for line in text.split('\n'):
            bbox = dummy_draw.textbbox((0, 0), line, font=font, stroke_width=stroke_width)
            w = bbox[2] - bbox[0]
            if w > max_line_w:
                max_line_w = w
        
        if max_line_w <= max_width:
            return font, font_size
            
        font_size -= 2
        
    try:
        return ImageFont.truetype(font_path, 20), 20
    except:
        return ImageFont.load_default(), 20

def create_title_banner(image_path: str, title: str, output_path: str, sub_title: str = None) -> str:
    """
    元の画像（ローカル画像またはネット画像）を読み込み、
    その上にブログタイトルを重ね合わせたタイトル入りバナー画像（1200x630）を生成して保存します。
    既存ブログ（sample_existing.png）のデザインテイストを完全に再現します：
      - 上段：メインタイトル（黄色・極太・袋文字）
      - 下段：サブタイトル（白色・中太・袋文字・前後にハイフン）
      - フォント：Dela Gothic One
      - 不透明度15%の薄い黒フィルターを背景写真にオーバーレイ
    """
    # AIがテキストとして出力した "\n" (バックスラッシュ+n) を、実際の改行コードに置換します
    if title:
        title = title.replace("\\n", "\n")
    if sub_title:
        sub_title = sub_title.replace("\\n", "\n")

    try:
        # 1. 画像の読み込みとアスペクト比維持トリミングリサイズ (1200x630)
        img = Image.open(image_path)
        target_size = (1200, 630)
        img_resized = ImageOps.fit(img, target_size, Image.Resampling.LANCZOS)
        
        # 2. 文字の視認性を高めるための半透明黒レイヤーの合成
        # 明るいトーンを維持するため、不透明度を約15% (255 * 0.15 = 38) に設定
        overlay = Image.new("RGBA", target_size, (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)
        draw_overlay.rectangle([0, 0, 1200, 630], fill=(0, 0, 0, 38))
        
        img_rgba = img_resized.convert("RGBA")
        img_composite = Image.alpha_composite(img_rgba, overlay)
        
        # 3. フォントのダウンロード
        base_dir = os.path.dirname(os.path.abspath(__file__))
        font_dir = os.path.join(base_dir, "fonts")
        font_file = download_font_if_not_exists(font_dir)
        
        # 4. タイトルの分割と自動改行の調整
        # AIからあらかじめ改行済みのテキストが渡された場合はそれを使用し、
        # そうでなければ従来の split_title でタイトルを分割します。
        if sub_title is not None and sub_title.strip() != "":
            main_text = title
            sub_text = sub_title.strip()
            
            # サブタイトルの前後に「- 」を付与（すでに付いていなければ）
            if sub_text and not (sub_text.startswith("-") or sub_text.startswith("ー")):
                sub_text = f"- {sub_text} -"
            
            # AIが自然な改行を入れているため、プログラムによる機械的改行は適用しません
            main_text_wrapped = main_text
            sub_text_wrapped = sub_text
        else:
            main_text, sub_text = split_title(title)
            
            # 1行が長すぎる場合は改行を入れる（1段あたりの最大文字数を少し広めの 18 / 24 に設定）
            main_text_wrapped = wrap_text_by_length(main_text, 18)
            sub_text_wrapped = wrap_text_by_length(sub_text, 24)
        
        # 5. 描画の設定とフォントスケーリング
        draw = ImageDraw.Draw(img_composite)
        
        # 描画パラメータ
        outline_color = (80, 50, 10, 255) # 既存ブログに合わせた濃い茶色
        stroke_width = 8
        main_fill_color = (255, 230, 0, 255) # メインタイトルは黄色
        sub_fill_color = (255, 255, 255, 255) # サブタイトルは白色
        
        # 画像幅からマージンを引いた最大描画幅 (1100px)
        max_draw_width = 1100
        
        # 動的にフォントサイズを縮小して取得
        main_font, main_size = get_scaled_font(main_text_wrapped, font_file, 74, max_draw_width, stroke_width)
        
        # サブタイトル用フォント（メインより小さくスケーリング。初期サイズ44）
        if sub_text_wrapped:
            sub_font, sub_size = get_scaled_font(sub_text_wrapped, font_file, 44, max_draw_width, stroke_width)
        else:
            sub_font, sub_size = ImageFont.load_default(), 0
            
        # テキストの高さ計算
        # メインタイトル（上段）
        main_bbox = draw.multiline_textbbox((0, 0), main_text_wrapped, font=main_font, stroke_width=stroke_width)
        main_h = main_bbox[3] - main_bbox[1]
        
        # サブタイトル（下段）
        if sub_text_wrapped:
            sub_bbox = draw.multiline_textbbox((0, 0), sub_text_wrapped, font=sub_font, stroke_width=stroke_width)
            sub_h = sub_bbox[3] - sub_bbox[1]
        else:
            sub_h = 0
            
        # 行間
        gap = 30
        
        # 全体の高さを計算
        total_h = main_h + sub_h + (gap if sub_text_wrapped else 0)
        
        # 開始Y座標（中央揃え）
        start_y = (630 - total_h) / 2
        
        # 描画
        current_y = start_y
        
        # メインタイトルの描画 (黄色・上段)
        draw.multiline_text(
            (600, current_y),
            main_text_wrapped,
            font=main_font,
            fill=main_fill_color,
            stroke_fill=outline_color,
            stroke_width=stroke_width,
            anchor="ma",
            align="center"
        )
        current_y += main_h + gap
        
        # サブタイトルの描画 (白色・下段)
        if sub_text_wrapped:
            draw.multiline_text(
                (600, current_y),
                sub_text_wrapped,
                font=sub_font,
                fill=sub_fill_color,
                stroke_fill=outline_color,
                stroke_width=stroke_width,
                anchor="ma",
                align="center"
            )
            
        # 6. 保存処理
        final_img = img_composite.convert("RGB")
        final_img.save(output_path, "JPEG", quality=95)
        print(f"🎨 タイトル入りバナー画像の生成に成功しました！ (保存先: {output_path})")
        return output_path
        
    except Exception as e:
        print(f"❌ バナー生成中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        # 万が一失敗した場合は、元の画像をリサイズしただけのものを出力して処理の強制終了を防ぎます
        try:
            img = Image.open(image_path)
            img_resized = ImageOps.fit(img, (1200, 630), Image.Resampling.LANCZOS)
            final_img = img_resized.convert("RGB")
            final_img.save(output_path, "JPEG", quality=90)
            return output_path
        except:
            return image_path

# 単体テスト用
if __name__ == "__main__":
    test_title = "【宮古島3泊4日】初めてでも安心！絶景満喫＆レンタカー完全攻略モデルコース"
    test_img = "images/unsplash_oz4NaYU6F5M.jpg" # 既存のUnsplash画像を指定
    
    if not os.path.exists(test_img):
        # ない場合は、適当な新規画像を作ってテストする
        print("💡 テスト用の元画像がないため、ダミー画像を作成してテストします。")
        os.makedirs("images", exist_ok=True)
        img = Image.new("RGB", (1200, 630), (100, 180, 255))
        img.save(test_img)
        
    create_title_banner(test_img, test_title, "images/processed_banner.jpg")
