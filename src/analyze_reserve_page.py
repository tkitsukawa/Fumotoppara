from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from dotenv import load_dotenv

load_dotenv()
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
PASSWORD = os.getenv('PASSWORD')

def analyze_reserve_flow():
    options = Options()
    options.add_argument('--headless') 
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--lang=ja-JP')
    
    current_dir = os.getcwd()
    user_data_dir = os.path.join(current_dir, 'chrome_data')
    options.add_argument(f'--user-data-dir={user_data_dir}')
    options.add_argument('--profile-directory=Default')

    driver = webdriver.Chrome(options=options)

    try:
        print("予約ページ解析を開始します...")
        driver.get('https://reserve.fumotoppara.net/reserved/reserved-date-selection')
        time.sleep(5)

        print(f"現在のURL: {driver.current_url}")

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
                    print("ログインしました。")
                else:
                    print("ログインボタンが見つかりません")
                    return
            else:
                print("入力欄が見つかりません")
                return

        # 3月のカレンダーを表示
        print("3月のカレンダーを表示...")
        buttons = driver.find_elements(By.TAG_NAME, 'button')
        target_month_btn = None
        for btn in buttons:
            if '3月' in btn.text:
                target_month_btn = btn
                break
        
        if target_month_btn:
            target_month_btn.click()
            time.sleep(3)
            
            # 3/27のセルを探してクリック
            # ヘッダーから列を探す
            rows = driver.find_elements(By.TAG_NAME, 'tr')
            header_row = rows[0]
            header_cells = header_row.find_elements(By.TAG_NAME, 'th')
            if not header_cells: header_cells = header_row.find_elements(By.TAG_NAME, 'td')
            
            target_col_index = -1
            for i, cell in enumerate(header_cells):
                if '27' in cell.text and ('3/' in cell.text or '3月' in cell.text or not '/' in cell.text): 
                    # ヘッダーテキストが "3/27" とか "27" とか色々あり得るので、
                    # 先ほどのログ "Col 86: 3/27 金" を参考に "3/27" を探す
                    if '3/27' in cell.text:
                        target_col_index = i
                        break
            
            if target_col_index != -1:
                # データ行（キャンプ宿泊）
                target_row = None
                for row in rows:
                    if 'キャンプ宿泊' in row.text:
                        target_row = row
                        break
                
                if target_row:
                    cells = target_row.find_elements(By.TAG_NAME, 'td')
                    # インデックス補正 -1
                    click_index = target_col_index - 1
                    
                    if 0 <= click_index < len(cells):
                        target_cell = cells[click_index]
                        print(f"3/27のセルをクリックします... (Status: {target_cell.text})")
                        
                        # クリック可能な要素を探す（tdの中のdivやspanなど）
                        # おそらくセル自体か、その中の要素がクリック可能
                        try:
                            target_cell.click()
                        except:
                            # セルの中の要素をクリックしてみる
                            target_cell.find_element(By.TAG_NAME, 'div').click()
                            
                        time.sleep(3)
                        
                        # 泊数選択などのポップアップが出るか確認
                        # スクリーンショットを撮る
                        driver.save_screenshot('popup_check.png')
                        print("ポップアップ画面を保存しました (popup_check.png)")
                        
                        # HTMLも保存
                        with open('popup_page.html', 'w', encoding='utf-8') as f:
                            f.write(driver.page_source)

                        # 「予約へ進む」ボタンなどを探して、次のページ（詳細入力）へ行けるか試す
                        # ここはサイトの構造次第だが、"予約する" などのボタンがあるはず
                        # 汎用的にボタンを探して、テキストを表示してみる
                        buttons = driver.find_elements(By.TAG_NAME, 'button')
                        print("画面上のボタン一覧:")
                        for btn in buttons:
                            if btn.is_displayed():
                                print(f" - {btn.text}")
                                if "予約" in btn.text and "進む" in btn.text or "予約する" in btn.text:
                                    print("予約ボタンを発見！クリックします...")
                                    btn.click()
                                    time.sleep(5)
                                    
                                    # 予約詳細ページに到達
                                    print("予約詳細ページに到達しました。情報を保存します。")
                                    driver.save_screenshot('detail_page.png')
                                    with open('detail_page.html', 'w', encoding='utf-8') as f:
                                        f.write(driver.page_source)
                                    break
                                    
                    else:
                        print("セルが見つかりません")
                else:
                    print("行が見つかりません")
            else:
                print("3/27が見つかりません")
        else:
            print("3月ボタンが見つかりません")

    except Exception as e:
        print(f"エラー: {e}")
        driver.save_screenshot('error_analyze.png')
    
    finally:
        driver.quit()

if __name__ == "__main__":
    analyze_reserve_flow()
