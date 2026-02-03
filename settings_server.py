from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os

PORT = 8000
CONFIG_FILE = 'config.json'
LOG_DIR = 'logs'

class ConfigHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
            return SimpleHTTPRequestHandler.do_GET(self)
        
        if self.path == '/api/config':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode())
            else:
                self.wfile.write(json.dumps({"notification_sets": [], "check_interval": 600}).encode())
            return
        
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/api/config':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                config_data = json.loads(post_data.decode())
                # バリデーションや整形が必要ならここで行う
                
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=4, ensure_ascii=False)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
            return

if __name__ == '__main__':
    print(f"設定画面サーバーを起動しました。ブラウザで http://localhost:{PORT} にアクセスしてください。")
    print("停止するには Ctrl+C を押してください。")
    httpd = HTTPServer(('localhost', PORT), ConfigHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバーを停止しました。")
