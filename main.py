import os
import json
import re
from dotenv import load_dotenv
import threading
import subprocess
import platform
import uuid
import time

try:
    from logging_site import RealtimeLogger
except ImportError:
    # Fallback nếu không có file logging_site
    class RealtimeLogger:
        def __init__(self, **kwargs): pass
        def start(self): return "http://localhost:9999"
        def push_log(self, msg, prefix): print(f"[{prefix}] {msg}")

def main():
    # =========================================
    # CONFIG SERVER FRP & SOCKS5
    # =========================================
    def init_env_file():
        env_path = ".env"
        default_configs = {
            "SOCKS5_USER": "",
            "SOCKS5_PASS": "",
            "FRP_SERVER_ADDR": "frp.freefrp.net",
            "FRP_SERVER_PORT": "7000",
            "FRP_TOKEN": "freefrp.net",
            "REMOTE_PORT": "12345", # Thay đổi port này theo freefrp cung cấp
            "LOGGER_PASS": "admin123"
        }

        if not os.path.exists(env_path):
            print("[*] Đang tạo file .env mặc định...")
            with open(env_path, "w", encoding="utf-8") as f:
                for key, value in default_configs.items():
                    f.write(f"{key}={value}\n")

    init_env_file()
    load_dotenv()

    # Đọc biến môi trường
    SOCKS5_USER = os.getenv("SOCKS5_USER", "")
    SOCKS5_PASS = os.getenv("SOCKS5_PASS", "")
    FRP_SERVER_ADDR = os.getenv("FRP_SERVER_ADDR", "frp.freefrp.net")
    FRP_SERVER_PORT = int(os.getenv("FRP_SERVER_PORT", 7000))
    FRP_TOKEN = os.getenv("FRP_TOKEN", "freefrp.net")
    REMOTE_PORT = int(os.getenv("REMOTE_PORT", 12345))
    LOGGER_PASS = os.getenv("LOGGER_PASS", "admin123")

    FRPC_BIN = "./frpc.exe" if platform.system().lower() == "windows" else "./frpc"
    CLF_BIN = "./cloudflared.exe" if platform.system().lower() == "windows" else "./cloudflared"

    # =========================================
    # TẠO FILE CẤU HÌNH FRP (SOCKS5 PLUGIN)
    # =========================================
    def write_configs():
        # Cấu hình Frpc sử dụng plugin socks5 tích hợp sẵn
        # Không cần file config.json của Xray nữa
        auth_section = ""
        if SOCKS5_USER and SOCKS5_PASS:
            auth_section = f"""
    plugin.user = "{SOCKS5_USER}"
    plugin.password = "{SOCKS5_PASS}" """

        frp_toml = f"""
serverAddr = "{FRP_SERVER_ADDR}"
serverPort = {FRP_SERVER_PORT}
auth.token = "{FRP_TOKEN}"
log.level = "trace"

[[proxies]]
name = "socks5-proxy-{str(uuid.uuid4())[:6]}"
type = "tcp"
remotePort = {REMOTE_PORT}
[proxies.plugin]
type = "socks5"{auth_section}
"""
        with open("frpc.toml", "w") as f:
            f.write(frp_toml)

    # =========================================
    # CHẠY DỊCH VỤ
    # =========================================
    def start_services():
        write_configs()
        
        # 1. Khởi chạy Frp (Handle luôn Socks5)
        print(f"[*] Khởi chạy SOCKS5 qua FRP tại {FRP_SERVER_ADDR}:{REMOTE_PORT}")
        fp = subprocess.Popen(
            [FRPC_BIN, "-c", "frpc.toml"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # 2. Khởi chạy Logger (Tùy chọn)
        logger = RealtimeLogger(port=9999, password=LOGGER_PASS)
        logger_url = logger.start()
        print(f"[*] Logger Web UI: {logger_url}")
        
        clp = subprocess.Popen(
            [CLF_BIN, "tunnel", "--url", logger_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        def log_push(pipe, prefix):
            try:
                with pipe:
                    ansi_escape = re.compile(r'\x1b\[[0-9;]*[mK]')
                    for line in iter(pipe.readline, ''):
                        clean_line = ansi_escape.sub('', line)
                        logger.push_log(clean_line.strip(), prefix)
            except: pass
        threading.Thread(target=log_push, args=(fp.stdout, "FRP-SOCKS5"), daemon=True).start()
        def log_reader(pipe, prefix):
            """Hàm đọc log từ pipe và in ra màn hình"""
            try:
                with pipe:
                    for line in iter(pipe.readline, ''):
                        print(f"[{prefix}] {line.strip()}")
            except Exception:
                pass
        threading.Thread(target=log_reader, args=(clp.stdout, "CLOUDFLARE"), daemon=True).start()
        
        return fp, clp

    # In thông tin kết nối
    print("\n" + "="*60)
    print("THÔNG TIN SOCKS5 PROXY:")
    print(f"Host: {FRP_SERVER_ADDR}")
    print(f"Port: {REMOTE_PORT}")
    print(f"URL: socks5://***:***@{FRP_SERVER_ADDR}:{REMOTE_PORT}" if SOCKS5_USER else f"socks5://{FRP_SERVER_ADDR}:{REMOTE_PORT}")
    print("="*60 + "\n")

    fp, clp = start_services()

    try:
        fp.wait()
    except KeyboardInterrupt:
        print("\n[*] Đang dừng dịch vụ...")
        fp.terminate()
        clp.terminate()

if __name__ == "__main__":
    main()