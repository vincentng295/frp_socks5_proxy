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
    # Fallback if logging_site module is missing
    class RealtimeLogger:
        def __init__(self, **kwargs): pass
        def start(self): return "http://localhost:9999"
        def push_log(self, msg, prefix): print(f"[{prefix}] {msg}")

def main():
    # =========================================
    # CONFIG SERVER FRP, SOCKS5 & PORT FORWARD
    # =========================================
    def init_env_file():
        env_path = ".env"
        default_configs = {
            # SOCKS5 Proxy configurations
            "ENABLE_SOCKS5": "true",       # Set to "false" to disable SOCKS5 proxy
            "SOCKS5_USER": "",
            "SOCKS5_PASS": "",
            "REMOTE_PORT": "12345",         # Change this port as provided by freefrp
            
            # Common FRP configurations
            "FRP_SERVER_ADDR": "frp.freefrp.net",
            "FRP_SERVER_PORT": "7000",
            "FRP_TOKEN": "freefrp.net",
            "LOGGER_PASS": "admin123",
            
            # Port Forwarding configurations
            "ENABLE_PORT_FORWARD": "false", # Set to "true" to enable
            "LOCAL_FORWARD_IP": "127.0.0.1",
            "LOCAL_FORWARD_PORT": "8080",   # Local port you want to expose
            "REMOTE_FORWARD_PORT": "12346"  # Remote port on FRP server
        }

        if not os.path.exists(env_path):
            print("[*] Creating default .env file...")
            with open(env_path, "w", encoding="utf-8") as f:
                for key, value in default_configs.items():
                    f.write(f"{key}={value}\n")

    init_env_file()
    load_dotenv()

    # Read environment variables
    ENABLE_SOCKS5 = os.getenv("ENABLE_SOCKS5", "true").lower() == "true"
    SOCKS5_USER = os.getenv("SOCKS5_USER", "")
    SOCKS5_PASS = os.getenv("SOCKS5_PASS", "")
    REMOTE_PORT = int(os.getenv("REMOTE_PORT", 12345))

    FRP_SERVER_ADDR = os.getenv("FRP_SERVER_ADDR", "frp.freefrp.net")
    FRP_SERVER_PORT = int(os.getenv("FRP_SERVER_PORT", 7000))
    FRP_TOKEN = os.getenv("FRP_TOKEN", "freefrp.net")
    LOGGER_PASS = os.getenv("LOGGER_PASS", "admin123")

    # Port Forwarding variables
    ENABLE_PORT_FORWARD = os.getenv("ENABLE_PORT_FORWARD", "false").lower() == "true"
    LOCAL_FORWARD_IP = os.getenv("LOCAL_FORWARD_IP", "127.0.0.1")
    LOCAL_FORWARD_PORT = int(os.getenv("LOCAL_FORWARD_PORT", 8080))
    REMOTE_FORWARD_PORT = int(os.getenv("REMOTE_FORWARD_PORT", 12346))

    FRPC_BIN = "./frpc.exe" if platform.system().lower() == "windows" else "./frpc"
    CLF_BIN = "./cloudflared.exe" if platform.system().lower() == "windows" else "./cloudflared"

    # Ensure at least one service is active
    if not ENABLE_SOCKS5 and not ENABLE_PORT_FORWARD:
        print("[!] Error: Both SOCKS5 and Port Forwarding are disabled. Please enable at least one service in .env.")
        return

    # =========================================
    # GENERATE FRP CONFIGURATION (TOML)
    # =========================================
    def write_configs():
        # Base headers
        frp_toml = f"""serverAddr = "{FRP_SERVER_ADDR}"
serverPort = {FRP_SERVER_PORT}
auth.token = "{FRP_TOKEN}"
log.level = "trace"
"""

        # Append SOCKS5 proxy configuration if enabled
        if ENABLE_SOCKS5:
            auth_section = ""
            if SOCKS5_USER and SOCKS5_PASS:
                auth_section = f"""
    plugin.user = "{SOCKS5_USER}"
    plugin.password = "{SOCKS5_PASS}" """

            frp_toml += f"""
[[proxies]]
name = "socks5-proxy-{str(uuid.uuid4())[:6]}"
type = "tcp"
remotePort = {REMOTE_PORT}
[proxies.plugin]
type = "socks5"{auth_section}
"""

        # Append Port Forwarding proxy if enabled
        if ENABLE_PORT_FORWARD:
            frp_toml += f"""
[[proxies]]
name = "port-forward-{str(uuid.uuid4())[:6]}"
type = "tcp"
localIp = "{LOCAL_FORWARD_IP}"
localPort = {LOCAL_FORWARD_PORT}
remotePort = {REMOTE_FORWARD_PORT}
"""

        with open("frpc.toml", "w") as f:
            f.write(frp_toml)

    # =========================================
    # START SERVICES
    # =========================================
    def start_services():
        write_configs()
        
        # 1. Start FRPC
        if ENABLE_SOCKS5:
            print(f"[*] Launching SOCKS5 via FRP at {FRP_SERVER_ADDR}:{REMOTE_PORT}")
        if ENABLE_PORT_FORWARD:
            print(f"[*] Launching Port Forward: {LOCAL_FORWARD_IP}:{LOCAL_FORWARD_PORT} -> {FRP_SERVER_ADDR}:{REMOTE_FORWARD_PORT}")
            
        fp = subprocess.Popen(
            [FRPC_BIN, "-c", "frpc.toml"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # 2. Start Logger
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
        threading.Thread(target=log_push, args=(fp.stdout, "FRP-LOGS"), daemon=True).start()
        
        def log_reader(pipe, prefix):
            try:
                with pipe:
                    for line in iter(pipe.readline, ''):
                        print(f"[{prefix}] {line.strip()}")
            except Exception:
                pass
        threading.Thread(target=log_reader, args=(clp.stdout, "CLOUDFLARE"), daemon=True).start()
        
        return fp, clp

    # Print connection details
    print("\n" + "="*60)
    print("PROXY & FORWARD INFO:")
    if ENABLE_SOCKS5:
        print(f"SOCKS5 Target: {FRP_SERVER_ADDR}:{REMOTE_PORT}")
    if ENABLE_PORT_FORWARD:
        print(f"Port Forward:  {LOCAL_FORWARD_IP}:{LOCAL_FORWARD_PORT} -> {FRP_SERVER_ADDR}:{REMOTE_FORWARD_PORT}")
    print("="*60 + "\n")

    fp, clp = start_services()

    try:
        fp.wait()
    except KeyboardInterrupt:
        print("\n[*] Stopping services...")
        fp.terminate()
        clp.terminate()

if __name__ == "__main__":
    main()