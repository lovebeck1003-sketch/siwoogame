"""
점프맵 실행기 (Python) — love 계정(lovebeck1003-sketch/jumpmap)의 실제 게임을 파이썬으로 띄운다.

원본 게임은 Three.js 3D 웹 게임(../siwoo/pc/jumpmap.html)이다.
이 스크립트는 파이썬 표준 라이브러리만으로 로컬 서버를 열고
실제 점프맵을 기본 브라우저로 실행한다. (추가 설치 불필요)

사용법:
    python run.py            # PC 버전(siwoo/pc/jumpmap.html) 실행
    python run.py mobile     # 모바일 버전(siwoo/mobile/jumpmap.html) 실행
    python run.py fps        # 좀비 FPS(siwoo/fps/fps.html) 실행
    python run.py car        # 무한 드라이브(siwoo/drive/index.html) 실행
    python run.py menu       # 메뉴(index.html) 실행

Ctrl+C 로 서버 종료.
"""

import os
import sys
import time
import threading
import webbrowser
import http.server
import socketserver

# 이 파일 기준 저장소 루트 (../)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PAGES = {
    "menu":   "index.html",
    "pc":     "siwoo/pc/jumpmap.html",
    "jump":   "siwoo/pc/jumpmap.html",
    "mobile": "siwoo/mobile/jumpmap.html",
    "fps":    "siwoo/fps/fps.html",
    "car":    "siwoo/drive/index.html",
    "drive":  "siwoo/drive/index.html",
}

PORT = 8765


def pick_page():
    arg = (sys.argv[1].lower() if len(sys.argv) > 1 else "pc")
    return PAGES.get(arg, PAGES["pc"])


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, *a):
        pass   # 콘솔 조용히

    def end_headers(self):
        # 게임 파일을 고칠 때마다 브라우저가 옛날 버전을 캐시해서 헷갈리는 것 방지
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


class Server(socketserver.ThreadingTCPServer):
    """연결마다 스레드 — 브라우저가 keep-alive 로 연결을 붙들고 있어도 다른 요청이 막히지 않는다.
    (예전 TCPServer 는 한 번에 한 연결만 처리해서, 탭을 열어두면 서버가 먹통처럼 보였다.)"""
    daemon_threads = True
    allow_reuse_address = True


def main():
    page = pick_page()
    target = os.path.join(ROOT, page.replace("/", os.sep))
    if not os.path.exists(target):
        print(f"[오류] 게임 파일을 찾을 수 없습니다: {target}")
        sys.exit(1)

    # 포트 충돌 시 다음 포트로
    port = PORT
    for _ in range(10):
        try:
            httpd = Server(("127.0.0.1", port), Handler)
            break
        except OSError:
            port += 1
    else:
        print("[오류] 사용 가능한 포트를 찾지 못했습니다.")
        sys.exit(1)

    url = f"http://127.0.0.1:{port}/{page}"
    print("점프맵 서버 시작 (love 계정: lovebeck1003-sketch/jumpmap)")
    print(f"  실행 파일 : {page}")
    print(f"  주소      : {url}")
    print("  종료      : Ctrl+C")

    # 서버가 뜬 뒤 브라우저 열기
    threading.Thread(
        target=lambda: (time.sleep(0.6), webbrowser.open(url)),
        daemon=True,
    ).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
        httpd.shutdown()


if __name__ == "__main__":
    main()
