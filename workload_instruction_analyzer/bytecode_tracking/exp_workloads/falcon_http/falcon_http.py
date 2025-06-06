import falcon
import requests
import time
import threading
from wsgiref import simple_server


class HealthResource:
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.media = {'status': 'healthy', 'timestamp': time.time()}


# Falcon 앱 생성
app = falcon.App()
app.add_route('/health', HealthResource())


def run_server():
    # 웹서버 실행 (포트 8000)
    httpd = simple_server.make_server('127.0.0.1', 8000, app)
    print("Falcon server running on http://127.0.0.1:8000")
    httpd.serve_forever()


def health_check():
    time.sleep(2)  # 서버 시작 대기
    while True:
        try:
            response = requests.get('http://127.0.0.1:8000/health')
            print(f"Health check: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"Health check failed: {e}")

        time.sleep(5)


# 서버를 백그라운드에서 실행
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Health check 실행
health_check()
