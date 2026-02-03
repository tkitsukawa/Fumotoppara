import os
import requests
from dotenv import load_dotenv

# .envファイルから情報を読み込む
load_dotenv()
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
        response.raise_for_status() # エラーがあれば例外を発生させる
        print(f"メッセージを送信しました: {message}")
        print(f"ステータスコード: {response.status_code}")
    except Exception as e:
        print(f"メッセージ送信に失敗しました: {e}")
        if 'response' in locals():
             print(f"詳細: {response.text}")

if __name__ == "__main__":
    send_line_message("これはふもとっぱら通知システムからのテストメッセージです！")
