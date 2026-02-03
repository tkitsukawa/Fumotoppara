from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
import time
import datetime
import requests
import json
import csv
import re
from dotenv import load_dotenv

# プロジェクトのルートディレクトリを取得 (srcの親ディレクトリ)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# .envファイルから情報を読み込む
load_dotenv(os.path.join(BASE_DIR, '.env'))
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
PASSWORD = os.getenv('PASSWORD')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

# 曜日マップ
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]

# 通知済みセットを記憶しておく
previous_ok_sets = set()

def load_config():
    try:
        config_path = os.path.join(BASE_DIR, 'config', 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"設定ファイルの読み込みに失敗しました: {e}")
        return {"notification_sets": [], "check_interval": 600}

def send_line_message(message):
    url = 'https://api.line.me/v2/bot/message/broadcast'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
    }
    data = {
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
        print(f"LINE通知(ブロードキャスト)を送信しました")
    except Exception as e:
        print(f"LINE通知の送信に失敗しました: {e}")

def get_weekday(date_str):
    date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    return WEEKDAYS[date_obj.weekday()]

def parse_status(status_text):
    status_text = status_text.replace('\n', ' ').strip()
    if '〇' in status_text:
        return '〇', 999
    elif '△' in status_text:
        match = re.search(r'残(\d+)', status_text)
        if match:
            return '△', int(match.group(1))
        else:
            return '△', 1
    else:
        return '×', 0

def save_log_csv(all_statuses):
    log_dir = os.path.join(BASE_DIR, "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    today_str = datetime.datetime.now().strftime('%Y-%m-%d')
    csv_path = os.path.join(log_dir, f"{today_str}.csv")
    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
    sorted_dates = sorted(all_statuses.keys())
    file_exists = os.path.exists(csv_path)
    
    try:
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                header = ["Timestamp"] + sorted_dates
                writer.writerow(header)
            row = [timestamp]
            for date in sorted_dates:
                row.append(all_statuses[date])
            writer.writerow(row)
    except Exception as e:
        print(f"ログ保存エラー: {e}")

def perform_auto_reservation(driver, n_set):
    """
    自動予約処理を実行する
    """
    try:
        print(f"自動予約処理を開始します: {n_set['name']}")
        
        # 1. カレンダーページにいるはずなので、対象の日付セルをクリック
        # ※直前のチェック処理でカレンダー画面にいる前提
        
        # 3/27のような日付を探してクリックするロジック
        # 既に check_calendar_once で画面は見ているが、クリックするために再度要素を探す
        
        target_date_str = n_set['start_date']
        target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
        target_month = target_date.month
        
        # 月ボタンをクリックして対象月へ移動（念のため）
        buttons = driver.find_elements(By.TAG_NAME, 'button')
        target_month_btn = None
        for btn in buttons:
            if f'{target_month}月' in btn.text:
                target_month_btn = btn
                break
        if target_month_btn:
            target_month_btn.click()
            time.sleep(3)
        else:
            raise Exception(f"{target_month}月のボタンが見つかりません")

        # 日付セルを探してクリック
        rows = driver.find_elements(By.TAG_NAME, 'tr')
        header_row = rows[0]
        header_cells = header_row.find_elements(By.TAG_NAME, 'th')
        if not header_cells: header_cells = header_row.find_elements(By.TAG_NAME, 'td')
        
        target_col_index = -1
        # 日付マッチング（"3/27" 形式）
        search_date_text = f"{target_date.month}/{target_date.day}"
        
        for i, cell in enumerate(header_cells):
            text = cell.text.replace('\n', ' ')
            if search_date_text in text:
                target_col_index = i
                break
        
        if target_col_index == -1:
            raise Exception(f"日付 {search_date_text} がカレンダーに見つかりません")

        # データ行（キャンプ宿泊）
        target_row = None
        for row in rows:
            if 'キャンプ宿泊' in row.text:
                target_row = row
                break
        
        if not target_row:
             raise Exception("「キャンプ宿泊」の行が見つかりません")

        cells = target_row.find_elements(By.TAG_NAME, 'td')
        # インデックス補正 -1
        click_index = target_col_index - 1
        
        if not (0 <= click_index < len(cells)):
             raise Exception("クリック対象のセルインデックスが不正です")

        target_cell = cells[click_index]
        print(f"予約日 {search_date_text} のセルをクリックします...")
        
        # クリック（div要素をクリックするのが確実かも）
        try:
            target_cell.find_element(By.TAG_NAME, 'div').click()
        except:
            target_cell.click()
            
        time.sleep(3)

        # 2. 泊数選択（ポップアップが出た場合）
        # ポップアップが出るかどうかはサイトの仕様によるが、出た場合は処理
        # 「1泊」「2泊」などのタブがあるはず
        nights = n_set.get('nights', 1)
        
        # ポップアップが表示されているか確認（厳密にはモーダルダイアログなどを探す）
        # ここでは「予約へ進む」的なボタンを探すことで代用
        
        # 泊数選択が必要な場合、ここで選択処理
        # "1泊", "2泊" といったテキストを持つ要素を探してクリック
        if nights > 1:
            try:
                # 泊数選択タブを探す（クラス名などは推測）
                # 単純にテキストで探す
                night_labels = driver.find_elements(By.XPATH, f"//div[contains(text(), '{nights}泊')]")
                if night_labels:
                    for label in night_labels:
                        if label.is_displayed():
                            label.click()
                            print(f"{nights}泊を選択しました")
                            time.sleep(1)
                            break
            except Exception as e:
                print(f"泊数選択でエラー（スキップします）: {e}")

        # 「予約へ進む」ボタンをクリック
        buttons = driver.find_elements(By.TAG_NAME, 'button')
        next_btn = None
        for btn in buttons:
            if btn.is_displayed() and ("予約" in btn.text and "進む" in btn.text or "予約する" in btn.text):
                next_btn = btn
                break
        
        if next_btn:
            next_btn.click()
            time.sleep(5)
        else:
             raise Exception("「予約へ進む」ボタンが見つかりません")

        # 3. 予約詳細ページでの入力
        print("予約詳細ページ: 入力を開始します...")

        # 到着時刻の選択 (11:00 ～ 13:59)
        # el-select をクリックしてドロップダウンを開く
        # ID: matterBasicInfo.arrivalTime に対応するラベルの近くのコンボボックス
        # 簡便のため、画面内の "11:00 ～ 13:59" を含む要素を探してクリックする手もあるが、
        # まずコンボボックスを開く必要がある
        
        # 'el-select' クラスを持つ要素を探す
        selects = driver.find_elements(By.CLASS_NAME, 'el-select')
        # おそらく最初のselectが到着時刻（画面構成による）
        # ラベル「到着時刻」の親要素から辿るのが確実
        arrival_label = driver.find_elements(By.XPATH, "//label[contains(text(), '到着時刻')]")
        if arrival_label:
            # ラベルの兄弟要素にある el-select を探す
            pass 
        
        # とりあえず全ての el-select を順にクリックして、ドロップダウンが出たら "11:00" を選ぶ作戦
        arrival_time_text = "11:00 ～ 13:59"
        time_selected = False
        
        for select in selects:
            if not select.is_displayed(): continue
            try:
                select.click()
                time.sleep(1)
                # ドロップダウン内の候補を探す
                options = driver.find_elements(By.CLASS_NAME, 'el-select-dropdown__item')
                for opt in options:
                    if arrival_time_text in opt.text:
                        opt.click()
                        time_selected = True
                        print(f"到着時刻 {arrival_time_text} を選択しました")
                        break
                if time_selected: break
            except:
                continue
        
        if not time_selected:
             print("警告: 到着時刻の選択に失敗しました（デフォルトまたは未選択のまま進みます）")

        # 人数入力
        # 大人の入力欄: input[type=text] で readonly でないもの、かつ数値入力っぽいもの
        # 以前の解析でIDが判明している: reservedUserList[0].planQty (大人)
        
        adults = n_set.get('adults', 1)
        children = n_set.get('children', 0)
        preschoolers = n_set.get('preschoolers', 0)
        
        # ID指定で探すのが確実だが、動的IDの可能性もあるため、
        # ラベル「大人」「小学生」「未就学児」の近くの input を探すアプローチ
        
        def set_input_by_label(label_text, value):
            try:
                # ラベルを探す
                labels = driver.find_elements(By.TAG_NAME, 'label')
                target_label = None
                for l in labels:
                    if label_text in l.text:
                        target_label = l
                        break
                
                if target_label:
                    # 親の親...と辿って、同じ行にある input を探す
                    # el-form-item 構造を想定
                    parent = target_label.find_element(By.XPATH, "./..") # el-form-item
                    inputs = parent.find_elements(By.TAG_NAME, 'input')
                    
                    target_input = None
                    for inp in inputs:
                         if inp.is_displayed() and not inp.get_attribute('readonly'):
                             target_input = inp
                             break
                    
                    if target_input:
                        target_input.clear()
                        target_input.send_keys(str(value))
                        print(f"{label_text}: {value}人 を入力しました")
                        return True
            except Exception as e:
                print(f"{label_text} の入力中にエラー: {e}")
            return False

        # 大人
        set_input_by_label("大人", adults)
        # 小学生
        set_input_by_label("小学生", children)
        # 未就学児
        set_input_by_label("未就学児", preschoolers)

        # 4. 「次へ」ボタン
        print("次へ進みます...")
        buttons = driver.find_elements(By.TAG_NAME, 'button')
        next_page_btn = None
        for btn in buttons:
            if "次へ" in btn.text and btn.is_displayed():
                next_page_btn = btn
                break
        
        if next_page_btn:
            next_page_btn.click()
            time.sleep(5)
            
            # 5. 確定ボタン（確認画面）
            print("確認画面: 予約を確定します...")
            buttons = driver.find_elements(By.TAG_NAME, 'button')
            confirm_btn = None
            for btn in buttons:
                # "確定" または "予約する"
                if ("確定" in btn.text or "予約する" in btn.text) and btn.is_displayed():
                    confirm_btn = btn
                    break
            
            if confirm_btn:
                # ★★★ ここでクリックすると本当に予約される ★★★
                # テスト時は注意が必要だが、要件通り実装する
                confirm_btn.click()
                print("予約確定ボタンをクリックしました！")
                time.sleep(10) # 完了画面待ち
                
                # 完了通知
                send_line_message(f"【自動予約完了】\nセット「{n_set['name']}」の予約を完了しました！\n確認メールまたはサイトで予約状況を確認してください。")
                return True

            else:
                 raise Exception("確定ボタンが見つかりません")
        else:
             raise Exception("「次へ」ボタンが見つかりません")

    except Exception as e:
        error_msg = f"【自動予約失敗】\nセット「{n_set['name']}」の自動予約中にエラーが発生しました。\n詳細: {str(e)}"
        print(error_msg)
        send_line_message(error_msg)
        # スクリーンショット保存
        try:
            log_dir = os.path.join(BASE_DIR, "logs")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            driver.save_screenshot(os.path.join(log_dir, 'reserve_error.png'))
        except:
            pass
        return False

def check_calendar_once():
    global previous_ok_sets
    
    options = Options()
    options.add_argument('--headless') 
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--lang=ja-JP')
    
    user_data_dir = os.path.join(BASE_DIR, 'chrome_data')
    options.add_argument(f'--user-data-dir={user_data_dir}')
    options.add_argument('--profile-directory=Default')

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        
        config = load_config()
        notification_sets = config.get("notification_sets", [])
        
        if not notification_sets:
            print("通知セットが設定されていません。")
            return

        # チェック対象の月をリストアップ
        target_months = set()
        for n_set in notification_sets:
            start_date = datetime.datetime.strptime(n_set['start_date'], "%Y-%m-%d")
            nights = n_set.get('nights', 1)
            for i in range(nights):
                check_date = start_date + datetime.timedelta(days=i)
                target_months.add((check_date.year, check_date.month))
        
        sorted_target_months = sorted(list(target_months))

        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] チェック開始...")
        
        driver.get('https://reserve.fumotoppara.net/reserved/reserved-date-selection')
        time.sleep(5)

        # ログイン確認
        if "reserved-date-selection" not in driver.current_url:
            print("ログインが必要です。ログイン処理を開始します...")
            if "login" not in driver.current_url and driver.current_url != 'https://reserve.fumotoppara.net/':
                 driver.get('https://reserve.fumotoppara.net/')
                 time.sleep(3)
            
            # ... (ログイン処理省略: 既存コードと同じ) ...
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

        # 全日付のステータス取得
        all_date_statuses = {}
        for year, month in sorted_target_months:
            print(f"{year}年{month}月のカレンダーを取得中...")
            buttons = driver.find_elements(By.TAG_NAME, 'button')
            target_month_btn = None
            for btn in buttons:
                if f'{month}月' in btn.text:
                    target_month_btn = btn
                    break
            
            if not target_month_btn:
                continue

            target_month_btn.click()
            time.sleep(3)
            
            rows = driver.find_elements(By.TAG_NAME, 'tr')
            header_row = rows[0]
            header_cells = header_row.find_elements(By.TAG_NAME, 'th')
            if not header_cells: header_cells = header_row.find_elements(By.TAG_NAME, 'td')
            
            date_col_indices = {} 
            for i, cell in enumerate(header_cells):
                text = cell.text.replace('\n', ' ').strip()
                parts = text.split(' ')
                if parts and '/' in parts[0]:
                     date_str = parts[0]
                     date_col_indices[date_str] = i
            
            target_row = None
            for row in rows:
                if 'キャンプ宿泊' in row.text:
                    target_row = row
                    break
            
            if target_row:
                cells = target_row.find_elements(By.TAG_NAME, 'td')
                index_offset = -1

                for date_md, header_index in date_col_indices.items():
                    data_index = header_index + index_offset
                    if 0 <= data_index < len(cells):
                        status = cells[data_index].text.strip()
                        m, d = map(int, date_md.split('/'))
                        full_date_str = f"{year}-{m:02d}-{d:02d}"
                        all_date_statuses[full_date_str] = status

        save_log_csv(all_date_statuses)
        print(f"ステータス取得完了: {len(all_date_statuses)}日分")

        # 通知 & 自動予約判定
        current_ok_sets = set()
        messages = []
        auto_reserve_target = None # 自動予約するセットが見つかったらこれに入れる

        for n_set in notification_sets:
            set_id = n_set['id']
            name = n_set['name']
            start_date_str = n_set['start_date']
            nights = n_set.get('nights', 1)
            # required_count は使用しない
            auto_reserve = n_set.get('auto_reserve', False)
            
            is_set_available = True
            available_details = []
            
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
            
            # 7日以内チェック
            today = datetime.datetime.now()
            days_diff = (start_date - today).days
            if auto_reserve and 0 <= days_diff <= 7:
                 print(f"警告: セット「{name}」は7日以内の予約です。キャンセル料が発生する可能性があります。")

            for i in range(nights):
                check_date = start_date + datetime.timedelta(days=i)
                check_date_str = check_date.strftime('%Y-%m-%d')
                weekday = WEEKDAYS[check_date.weekday()]
                
                status = all_date_statuses.get(check_date_str, "不明")
                mark, count = parse_status(status)
                
                available_details.append(f"{check_date_str}({weekday}): {status}")
                
                # 空き判定: 〇か△ならOK
                if mark == '×':
                    is_set_available = False
            
            if is_set_available:
                current_ok_sets.add(set_id)
                
                # 自動予約モードONなら、対象としてマーク（最初に見つかった1つだけ実行する方針）
                if auto_reserve and not auto_reserve_target:
                    auto_reserve_target = n_set
                    # 通知メッセージにもその旨を追加
                    msg = f"【空き発見！自動予約を開始します】\nセット: {name}\n" + "\n".join(available_details)
                    messages.append(msg)
                
                # 前回NGだった場合のみ通知（自動予約対象でない場合）
                elif set_id not in previous_ok_sets:
                    msg = f"【空きが出ました！】\nセット: {name}\n" + "\n".join(available_details)
                    messages.append(msg)

        # 通知送信
        if messages:
            reserve_url = "https://reserve.fumotoppara.net/reserved/reserved-calendar-list"
            full_message = "\n\n".join(messages) + f"\n\n予約はこちら:\n{reserve_url}"
            print("条件を満たす空きが見つかりました！通知を送ります。")
            send_line_message(full_message)
        
        # 自動予約実行
        if auto_reserve_target:
            print(f"自動予約を実行します: {auto_reserve_target['name']}")
            # ここで予約処理関数を呼び出す
            perform_auto_reservation(driver, auto_reserve_target)
        else:
            print("新たな条件を満たす空きはありませんでした（または自動予約対象外）。")
        
        # 状態更新
        previous_ok_sets = current_ok_sets

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()

def monitor_loop():
    config = load_config()
    print("ふもとっぱら予約監視システムを開始します。")
    print(f"チェック間隔: {config.get('check_interval', 600)}秒")
    print("停止するには Ctrl+C を押してください。")
    
    check_calendar_once()
    
    while True:
        try:
            config = load_config()
            interval = config.get('check_interval', 600)
            time.sleep(interval)
            check_calendar_once()
        except KeyboardInterrupt:
            print("\n監視を終了します。")
            break

if __name__ == "__main__":
    monitor_loop()
