from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import os
from dotenv import load_dotenv
import time

# プロジェクトのルートディレクトリを取得 (srcの親ディレクトリ)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# .envファイルからログイン情報を読み込む
load_dotenv(os.path.join(BASE_DIR, '.env'))
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
PASSWORD = os.getenv('PASSWORD')

def login_and_check():
    # ブラウザの設定
    options = Options()
    # ヘッドレスモード（画面を表示しないモード）で実行する場合は以下のコメントアウトを外す
    options.add_argument('--headless') 
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # 日本語フォントなどの設定が必要な場合があるため、言語設定を追加
    options.add_argument('--lang=ja-JP')
    
    # ユーザーデータディレクトリの設定（ログイン状態を保持するため）
    # プロジェクトルートに 'chrome_data' というフォルダを作ってそこに保存する
    user_data_dir = os.path.join(BASE_DIR, 'chrome_data')
    options.add_argument(f'--user-data-dir={user_data_dir}')
    options.add_argument('--profile-directory=Default')

    print(f"ユーザーデータディレクトリ: {user_data_dir}")
    print("ブラウザを起動します...")
    driver = webdriver.Chrome(options=options)

    try:
        # 1. 予約サイト（カレンダーページ）に直接アクセス
        print("予約サイトにアクセスしています...")
        driver.get('https://reserve.fumotoppara.net/reserved/reserved-date-selection')
        
        # 画面遷移を待つ（少し長めに）
        time.sleep(5)

        # 現在のURLを確認
        print(f"現在のURL: {driver.current_url}")

        # ログイン済みかどうかを確認（URLで判断）
        if "reserved-date-selection" in driver.current_url:
            print("既にログインしています。")
        else:
            # カレンダーページにいなかったら、ログインが必要と判断
            print("ログインが必要です。ログイン処理を開始します...")
            
            # トップページにいるかもしれないし、ログインページにリダイレクトされているかもしれない
            # とりあえずトップページへ移動してからログインフローを開始する
            if "login" not in driver.current_url and driver.current_url != 'https://reserve.fumotoppara.net/':
                 driver.get('https://reserve.fumotoppara.net/')
                 time.sleep(3)
            # ログイン処理
            # メールアドレス入力欄を探す
            wait = WebDriverWait(driver, 10)
            
            print("ログイン情報を入力しています...")
            
            inputs = driver.find_elements(By.TAG_NAME, 'input')
            
            email_input = None
            password_input = None
            
            for inp in inputs:
                input_type = inp.get_attribute('type')
                placeholder = inp.get_attribute('placeholder')
                
                if input_type == 'text' or input_type == 'email':
                    if placeholder and ('メール' in placeholder or 'mail' in placeholder.lower()):
                        email_input = inp
                    elif email_input is None and input_type != 'password':
                        email_input = inp
                
                if input_type == 'password':
                    password_input = inp
            
            if email_input and password_input:
                email_input.clear()
                email_input.send_keys(EMAIL_ADDRESS)
                
                password_input.clear()
                password_input.send_keys(PASSWORD)
                
                buttons = driver.find_elements(By.TAG_NAME, 'button')
                login_btn = None
                for btn in buttons:
                    if 'ログイン' in btn.text:
                        login_btn = btn
                        break
                
                if login_btn:
                    print("ログインボタンをクリックします...")
                    login_btn.click()
                    time.sleep(5)
                else:
                    print("ログインボタンが見つかりませんでした。")
                    return
            else:
                print("入力欄が見つかりませんでした。")
                return

        # 3. カレンダーの情報を取得
        # 例として「3月」ボタンをクリックしてみる
        print("3月のカレンダーを表示します...")
        buttons = driver.find_elements(By.TAG_NAME, 'button')
        target_month_btn = None
        for btn in buttons:
            if '3月' in btn.text:
                target_month_btn = btn
                break
        
        if target_month_btn:
            target_month_btn.click()
            time.sleep(3) # 読み込み待ち
            
            # カレンダーが表示された状態でスクリーンショット
            print("3月のカレンダーを保存します...")
            log_dir = os.path.join(BASE_DIR, 'logs')
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            driver.save_screenshot(os.path.join(log_dir, 'calendar_march.png'))
            print("スクリーンショット 'calendar_march.png' を保存しました。")
            
            # 日付ごとの状況を取得（まだ詳細は実装せず、まずはHTML構造を見る）
            # テーブルの行を取得してみる
            rows = driver.find_elements(By.TAG_NAME, 'tr')
            print(f"カレンダーの行数: {len(rows)}")
            
            # 各行の中身を少し詳しく見てみる（最初の数行だけ）
            for i, row in enumerate(rows):
                print(f"Row {i}: {row.text}")
                # セルの中身も見る
                cells = row.find_elements(By.TAG_NAME, 'td')
                if not cells:
                    cells = row.find_elements(By.TAG_NAME, 'th') # ヘッダー行の場合
                print(f"  Cells: {[c.text for c in cells]}")
            
        else:
            print("3月ボタンが見つかりませんでした。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        driver.save_screenshot('error_screenshot.png')
    
    finally:
        print("ブラウザを終了します。")
        driver.quit()

if __name__ == "__main__":
    login_and_check()
