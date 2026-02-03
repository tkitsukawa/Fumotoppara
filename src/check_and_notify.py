from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import requests
from dotenv import load_dotenv

# .envファイルから情報を読み込む
load_dotenv()
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
PASSWORD = os.getenv('PASSWORD')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def send_line_message(message):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    data = {
        'to': LINE_USER_ID,
        'messages': [
            {
                'type': 'text',
                'text': message
            }
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        print(f"LINE通知を送信しました: {message}")
    except Exception as e:
        print(f"LINE通知の送信に失敗しました: {e}")

def check_calendar():
    options = Options()
    options.add_argument('--headless') 
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--lang=ja-JP')
    
    current_dir = os.getcwd()
    user_data_dir = os.path.join(current_dir, 'chrome_data')
    options.add_argument(f'--user-data-dir={user_data_dir}')
    options.add_argument('--profile-directory=Default')

    print("ブラウザを起動します...")
    driver = webdriver.Chrome(options=options)

    try:
        print("予約サイトにアクセスしています...")
        driver.get('https://reserve.fumotoppara.net/reserved/reserved-date-selection')
        time.sleep(5)

        # ログイン確認
        if "reserved-date-selection" not in driver.current_url:
            print("ログインが必要です。ログイン処理を開始します...")
            if "login" not in driver.current_url and driver.current_url != 'https://reserve.fumotoppara.net/':
                 driver.get('https://reserve.fumotoppara.net/')
                 time.sleep(3)
            
            wait = WebDriverWait(driver, 10)
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
                    login_btn.click()
                    time.sleep(5)
                else:
                    print("ログインボタンが見つかりません")
                    return
            else:
                print("入力欄が見つかりません")
                return

        # 3月を表示
        print("3月のカレンダーをチェックします...")
        buttons = driver.find_elements(By.TAG_NAME, 'button')
        target_month_btn = None
        for btn in buttons:
            if '3月' in btn.text:
                target_month_btn = btn
                break
        
        if target_month_btn:
            target_month_btn.click()
            time.sleep(3)
            
            # テーブルの解析
            # 日付行と状況行を取得
            # テーブル構造が複雑そうなので、行ごとにテキストを取得して解析する
            rows = driver.find_elements(By.TAG_NAME, 'tr')
            
            available_dates = []
            
            # ログを見ると、行データは以下のようになっていると推測される
            # 1行目: ヘッダー（日付など）
            # 2行目以降: 各施設の空き状況
            # ただし、スマホ表示とPC表示でテーブル構造が変わる可能性があるため、
            # シンプルに「セルの中に日付」と「セルの中に状況」があるとして探す
            
            # まず全日付を取得
            # 日付のセルは '3/1', '3/2' のようなテキストを含むはず
            # 状況のセルは '〇', '△', '×' を含むはず
            
            # 構造をシンプルに捉える:
            # 1. すべてのセルを取得する
            # 2. '3/XX' という形式のセルを見つけたら、それが日付
            # 3. その日付に対応する列（または行）の状況を見る...というのは難しいので
            #    もっと単純に、'〇' か '△' が画面に含まれているかだけをまずは見る？
            #    いや、それだと「どの日」かが分からない。
            
            # ログの出力から再構成：
            # ヘッダー行に日付が並んでいる（はず）
            # Row 0: ... 1/24 土 1/25 日 ...
            # Row 1: キャンプ日帰り ... 〇 〇 ...
            # Row 2: キャンプ宿泊 ... △ 〇 ...
            
            # なので、Row 0 (ヘッダー) から日付リストを作る
            header_row = rows[0]
            header_cells = header_row.find_elements(By.TAG_NAME, 'th')
            if not header_cells:
                header_cells = header_row.find_elements(By.TAG_NAME, 'td')
            
            date_map = {} # index: date_string
            for i, cell in enumerate(header_cells):
                text = cell.text.replace('\n', ' ')
                if '/' in text: # 日付っぽいセル
                    date_map[i] = text
            
            print(f"日付マップ: {date_map}")

            # 宿泊の行を探す（「キャンプ宿泊」を含む行）
            target_row = None
            for row in rows:
                if 'キャンプ宿泊' in row.text:
                    target_row = row
                    break
            
            if target_row:
                cells = target_row.find_elements(By.TAG_NAME, 'td')
                for i, cell in enumerate(cells):
                    if i in date_map:
                        status = cell.text
                        date = date_map[i]
                        # 空き判定
                        if '〇' in status or '△' in status:
                            available_dates.append(f"{date} ({status})")
            
            if available_dates:
                message = "【ふもとっぱら空き通知】\n3月の以下の日程で「キャンプ宿泊」に空きがあります！\n\n" + "\n".join(available_dates)
                send_line_message(message)
            else:
                print("残念ながら、3月のキャンプ宿泊に空きはありませんでした。")

        else:
            print("3月ボタンが見つかりませんでした。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        send_line_message(f"エラーが発生しました: {e}")
    
    finally:
        print("ブラウザを終了します。")
        driver.quit()

if __name__ == "__main__":
    check_calendar()
