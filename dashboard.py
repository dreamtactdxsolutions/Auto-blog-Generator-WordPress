"""
📊 ブログ自動生成システム 管理ダッシュボード
Streamlit ベースの管理画面
"""

import os
import sys
import csv
import json
from datetime import datetime
from pathlib import Path

try:
    import streamlit as st
    import pandas as pd
except ImportError:
    print("❌ Streamlit がインストールされていません。")
    print("   pip install streamlit pandas を実行してください。")
    sys.exit(1)

import config
from scheduler import BlogScheduler
from search_console_integration import SearchConsoleOptimizer


# ページ設定
st.set_page_config(
    page_title="🌴 ブログ自動生成ダッシュボード",
    layout="wide",
    initial_sidebar_state="expanded"
)

# スタイル設定
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f7ff;
        border-left: 4px solid #35a7c9;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .status-pending {
        background-color: #fff3cd;
        color: #856404;
        padding: 5px 10px;
        border-radius: 3px;
        font-size: 12px;
    }
    .status-running {
        background-color: #cce5ff;
        color: #004085;
        padding: 5px 10px;
        border-radius: 3px;
        font-size: 12px;
    }
    .status-completed {
        background-color: #d4edda;
        color: #155724;
        padding: 5px 10px;
        border-radius: 3px;
        font-size: 12px;
    }
    .status-failed {
        background-color: #f8d7da;
        color: #721c24;
        padding: 5px 10px;
        border-radius: 3px;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# タイトル
# =============================================================================

st.title("🌴 宮古島レンタカー ブログ自動生成システム")
st.markdown("**Search Console 連動 + CSV スケジューラー**")

# =============================================================================
# サイドバー設定
# =============================================================================

with st.sidebar:
    st.header("⚙️ 設定")
    
    # スケジュールファイルパス
    csv_file = st.text_input(
        "📁 スケジュール CSV ファイル",
        value="schedule.csv",
        help="投稿スケジュール定義ファイル"
    )
    
    # Search Console 認証
    sc_enabled = st.checkbox("🔍 Search Console 連動を有効化")
    sc_credentials = None
    if sc_enabled:
        sc_credentials = st.text_input(
            "Google Cloud JSON キーパス",
            type="password",
            help="サービスアカウント認証キーのパス"
        )
    
    st.divider()
    
    # WordPress 接続情報（表示のみ）
    st.subheader("📝 WordPress 接続情報")
    st.text(f"URL: {config.WP_URL}")
    st.text(f"ユーザー: {config.WP_USERNAME}")


# =============================================================================
# タブ1: スケジュール管理
# =============================================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📅 スケジュール管理",
    "🔍 Search Console",
    "📊 統計情報",
    "📚 使用方法"
])

with tab1:
    st.header("📅 投稿スケジュール")
    
    # スケジューラー初期化
    if 'scheduler' not in st.session_state:
        if os.path.exists(csv_file):
            st.session_state.scheduler = BlogScheduler(csv_file=csv_file)
        else:
            st.warning(f"⚠️ スケジュールファイルが見つかりません: {csv_file}")
            st.session_state.scheduler = None
    
    scheduler = st.session_state.scheduler
    
    if scheduler and scheduler.tasks:
        # スケジュール一覧表示
        st.subheader(f"📋 {len(scheduler.tasks)} 件のスケジュール")
        
        # DataFrame作成
        schedule_data = []
        for idx, task in enumerate(scheduler.tasks, 1):
            schedule_data.append({
                '№': idx,
                'テーマ': task['theme'],
                'キーワード': task['keyword'],
                '実行日時': f"{task['publish_date']} {task['publish_time']}",
                'ステータス': task['status'].upper()
            })
        
        df = pd.DataFrame(schedule_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # 実行ボタン
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🚀 全タスク即座実行", use_container_width=True):
                st.info("✅ 全タスクの実行を開始します...")
                scheduler.run_all_tasks_now()
                st.success("✨ 全タスク完了！")
                st.rerun()
        
        with col2:
            # 単一タスク選択実行
            task_idx = st.selectbox(
                "タスク選択",
                options=range(len(scheduler.tasks)),
                format_func=lambda i: scheduler.tasks[i]['theme']
            )
            if st.button("▶️ 選択タスク実行", use_container_width=True):
                st.info(f"✅ タスク {task_idx+1} の実行を開始します...")
                scheduler.run_single_task(task_idx)
                st.success("✨ タスク完了！")
                st.rerun()
        
        with col3:
            if st.button("🔄 スケジューラー再読込", use_container_width=True):
                st.session_state.scheduler = BlogScheduler(csv_file=csv_file)
                st.success("✅ 再読込完了")
                st.rerun()
        
        st.divider()
        
        # CSV ダウンロード
        csv_content = df.to_csv(index=False, encoding='utf-8')
        st.download_button(
            label="💾 スケジュールをダウンロード",
            data=csv_content,
            file_name=f"schedule_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    else:
        st.warning("❌ スケジュールが読み込まれていません")


# =============================================================================
# タブ2: Search Console 連動
# =============================================================================

with tab2:
    st.header("🔍 Google Search Console 統合")
    
    if sc_enabled and sc_credentials:
        try:
            optimizer = SearchConsoleOptimizer(sc_credentials)
            
            st.success("✅ Search Console に接続しました")
            
            # サイト URL 入力
            site_url = st.text_input(
                "対象サイト URL",
                value=config.WP_URL,
                help="例: https://miyakojima-rentacar.net/"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                min_position = st.slider(
                    "掲載順位: 最小",
                    min_value=11,
                    max_value=50,
                    value=20
                )
            with col2:
                max_position = st.slider(
                    "掲載順位: 最大",
                    min_value=51,
                    max_value=200,
                    value=100
                )
            
            if st.button("📊 低掲載順位キーワード抽出", use_container_width=True):
                with st.spinner("キーワード抽出中..."):
                    keywords = optimizer.get_low_ranking_keywords(
                        site_url=site_url,
                        min_position=int(min_position),
                        max_position=int(max_position)
                    )
                
                if keywords:
                    st.session_state.sc_keywords = keywords
                    st.success(f"✅ {len(keywords)} 件のキーワードを抽出しました")
                else:
                    st.warning("該当するキーワードが見つかりません")
            
            # キーワード表示
            if 'sc_keywords' in st.session_state:
                keywords = st.session_state.sc_keywords
                
                st.subheader(f"📋 抽出キーワード ({len(keywords)}件)")
                
                # DataFrame作成
                kw_data = []
                for kw in keywords:
                    kw_data.append({
                        'キーワード': kw['keyword'],
                        '順位': f"{kw['position']:.1f}",
                        'インプレッション': kw['impressions'],
                        'クリック': kw['clicks'],
                        'CTR': f"{kw['ctr']:.2f}%"
                    })
                
                df_kw = pd.DataFrame(kw_data)
                st.dataframe(df_kw, use_container_width=True, hide_index=True)
                
                st.divider()
                
                # スケジュール生成ボタン
                if st.button("📅 改善スケジュールを生成", use_container_width=True):
                    output_file = f"schedule_sc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    result = optimizer.generate_improvement_schedule(
                        keywords,
                        output_csv=output_file
                    )
                    
                    if result:
                        st.success(f"✅ スケジュールを生成しました: {output_file}")
                        
                        # ダウンロード
                        with open(output_file, 'r', encoding='utf-8') as f:
                            csv_content = f.read()
                        
                        st.download_button(
                            label="💾 生成スケジュールをダウンロード",
                            data=csv_content,
                            file_name=output_file,
                            mime="text/csv"
                        )
        
        except Exception as e:
            st.error(f"❌ エラーが発生しました: {e}")
    
    else:
        st.info("ℹ️ Search Console 連動を有効化し、認証キーを設定してください")


# =============================================================================
# タブ3: 統計情報
# =============================================================================

with tab3:
    st.header("📊 統計情報")
    
    if scheduler and scheduler.tasks:
        # タスク統計
        total_tasks = len(scheduler.tasks)
        pending_tasks = sum(1 for t in scheduler.tasks if t['status'] == 'pending')
        completed_tasks = sum(1 for t in scheduler.tasks if t['status'] == 'completed')
        failed_tasks = sum(1 for t in scheduler.tasks if t['status'] == 'failed')
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📋 総タスク数", total_tasks)
        
        with col2:
            st.metric("⏳ 待機中", pending_tasks)
        
        with col3:
            st.metric("✅ 完了", completed_tasks)
        
        with col4:
            st.metric("❌ 失敗", failed_tasks)
        
        st.divider()
        
        # ステータス分布（円グラフ）
        status_counts = {
            'pending': pending_tasks,
            'completed': completed_tasks,
            'failed': failed_tasks
        }
        
        st.subheader("📈 ステータス分布")
        st.bar_chart(pd.Series(status_counts))
    
    else:
        st.warning("統計データがありません")


# =============================================================================
# タブ4: 使用方法
# =============================================================================

with tab4:
    st.header("📚 使用方法")
    
    st.subheader("🚀 クイックスタート")
    
    st.markdown("""
    ### 1️⃣ スケジュール CSV を準備
    
    `schedule.csv` ファイルに以下の形式で投稿スケジュールを定義します：
    
    ```csv
    keyword,theme,sub_keywords,publish_date,publish_time,execution_mode
    宮古島 レンタカー 家族,ファミリー向けレンタカー選び方ガイド,子連れ|安心ドライブ|チャイルドシート,2026-07-15,09:00,schedule
    宮古島 ドライブ 穴場,地元民が愛する穴場ドライブスポット5選,穴場スポット|ドライブコース|絶景,2026-07-16,14:00,schedule
    ```
    
    ### 2️⃣ スケジューラー実行（3つのモード）
    
    **スケジューラー起動（毎日自動実行）:**
    ```bash
    python scheduler.py --csv schedule.csv --mode schedule
    ```
    
    **全タスク即座実行（テスト用）:**
    ```bash
    python scheduler.py --csv schedule.csv --mode run-all
    ```
    
    **単一タスク実行（1件のみ）:**
    ```bash
    python scheduler.py --csv schedule.csv --mode run-one --task-index 0
    ```
    
    ### 3️⃣ Search Console 連動（低掲載順位キーワード自動抽出）
    
    **キーワード抽出 & スケジュール生成:**
    ```bash
    python search_console_integration.py \\
      --credentials /path/to/credentials.json \\
      --site-url https://miyakojima-rentacar.net/ \\
      --min-position 20 \\
      --max-position 100 \\
      --output schedule_sc.csv
    ```
    
    ### 4️⃣ ダッシュボード起動
    
    ```bash
    streamlit run dashboard.py
    ```
    
    ---
    
    ## 📋 CSV ファイル形式
    
    | 項目 | 説明 | 例 |
    |------|------|-----|
    | keyword | 記事のメインキーワード | 宮古島 レンタカー 家族 |
    | theme | 記事のテーマ | ファミリー向けレンタカー選び方ガイド |
    | sub_keywords | 関連キーワード（パイプ区切り） | 子連れ\|安心ドライブ\|チャイルドシート |
    | publish_date | 投稿日（YYYY-MM-DD形式） | 2026-07-15 |
    | publish_time | 投稿時刻（HH:MM形式） | 09:00 |
    | execution_mode | 実行モード | schedule |
    
    ---
    
    ## 🔐 Google Search Console 認証設定
    
    1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
    2. プロジェクトを作成
    3. **Web Masters API** を有効化
    4. **サービスアカウント**を作成
    5. JSON キーをダウンロード
    6. Search Console に対象サイトを追加
    7. サービスアカウントメールをサイト所有者として追加
    
    ---
    
    ## ⚠️ トラブルシューティング
    
    **「schedule ライブラリが見つかりません」エラー**
    ```bash
    pip install schedule
    ```
    
    **「Google Auth ライブラリが見つかりません」エラー**
    ```bash
    pip install google-auth-oauthlib google-api-python-client
    ```
    
    **「Streamlit が見つかりません」エラー**
    ```bash
    pip install streamlit
    ```
    
    ---
    
    📧 **サポート:** issues でお知らせください！
    """)
