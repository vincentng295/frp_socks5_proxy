# FRP SOCKS5 Proxy & Port Forwarding with Real-time Web Logging

A lightweight, automated solution to deploy and maintain a **SOCKS5 Proxy** and/or a custom **Port Forwarding tunnel** routed through an FRP (Fast Reverse Proxy) server. This repository includes cross-platform binary auto-downloaders, an integrated lightweight HTTP log viewer, and a built-in mechanism to achieve near-infinite uptime on **GitHub Actions** by automatically chaining workflow dispatches.

---

## 🚀 Features

* **Dual-Mode Connectivity:** * **Native SOCKS5 Plugin:** Utilizes FRP's built-in SOCKS5 plugin—no extra overhead or heavy external dependencies (Default mode).
* **Port Forwarding (New):** Easily expose any local service (HTTP, SSH, Database, etc.) to a public remote port over the internet via TCP tunneling.


* **Cross-Platform Auto-Installer:** Automatically detects operating systems (Windows, Linux, macOS, Termux) and architectures (amd64, 386, arm64, armv7l) to fetch the correct `frpc` and `cloudflared` binaries.
* **Real-time Web Dashboard:** A secure, password-protected HTTP server built natively in Python to monitor real-time traffic and proxy logs.
* **Public Web UI via Cloudflare:** Automatically spins up a Cloudflare Tunnel (`cloudflared`) to expose the local log dashboard safely over the web.
* **GitHub Actions Workflow Bridging:** Circumvents the GitHub Actions 6-hour runtime limitation by automatically re-triggering itself every 5.5 hours, passing configurations and states along seamlessly.

---

## 🛠️ Repository Architecture

* `main.py`: The application orchestrator. Generates configurations (`frpc.toml`), spawns background processes, and links streaming logs.
* `download-service.py` & `download-cloudflared.py`: Handles platform identification and downloads specific executable binaries for FRP (`v0.61.1`) and Cloudflared (`v2026.3.0`).
* `logging_site.py`: A native, multi-threaded HTTP server presenting a sleek dark-themed log UI with basic authentication.
* `github-workflows.py`: Manages secret migrations to runtime environments and executes the automated pipeline loop.

---

## ⚙️ Configuration (`.env`)

Create a `.env` file in the root directory (or let the script generate a default one for you on its first local run).

```env
# =====================================================================
# FRP SERVER CONFIGURATIONS
# =====================================================================
FRP_SERVER_ADDR=frp.freefrp.net
FRP_SERVER_PORT=7000
FRP_TOKEN=freefrp.net

# =====================================================================
# SOCKS5 AUTHENTICATION (Default Mode)
# =====================================================================
ENABLE_SOCKS5=true
SOCKS5_USER=
SOCKS5_PASS=
REMOTE_PORT=12345

# =====================================================================
# PORT FORWARDING CONFIGURATIONS (Optional)
# =====================================================================
ENABLE_PORT_FORWARD=false
LOCAL_FORWARD_IP=127.0.0.1
LOCAL_FORWARD_PORT=8080
REMOTE_FORWARD_PORT=12346

# =====================================================================
# WEB LOG DASHBOARD PROTECTION
# =====================================================================
LOGGER_PASS=admin123

```

### Modes Explained:

1. **SOCKS5 Proxy (Default):** Runs automatically out of the box using your credentials and `REMOTE_PORT`.
2. **Port Forwarding:** Set `ENABLE_PORT_FORWARD=true` to tunnel your local application (e.g., a local server running at `127.0.0.1:8080`) to the public internet via `REMOTE_FORWARD_PORT`. Both modes can run simultaneously!

---

## 💻 Local Setup & Usage

### 1. Prerequisites

Make sure you have Python 3.10+ installed on your system.

### 2. Installation

Clone the repository and install the required dependencies:

```bash
git clone https://github.com/vincentng295/frp_socks5_proxy.git
cd frp_socks5_proxy
pip install -r requirements.txt

```

### 3. Fetch Binaries

Run the download scripts to grab the latest supported version of `frpc` and `cloudflared` for your specific machine architecture:

```bash
python3 download-service.py
python3 download-cloudflared.py

```

### 4. Run the Core Script

Launch the main process:

```bash
python3 main.py

```

Upon startup, the console will print your active proxy/forwarding information and initialize a secure Cloudflare Tunnel URL so you can monitor your logs remotely.

---

## 🌌 Continuous Deployment (GitHub Actions)

This project can run indefinitely in the cloud using GitHub Actions without breaking a sweat over timeout limits.

### How the Workflow Chaining Works:

GitHub Actions caps job durations to 6 hours. To bypass this, `github-workflows.py` watches the clock. At the **5 hours and 30 minutes** mark, it utilizes the GitHub API to trigger a fresh `workflow_dispatch` instance of itself, effectively passing the baton to a new workflow runner before the current one terminates.

### Deployment Steps:

1. **Add Repository Secrets:**
Go to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**.

* Name: `ENV_CONFIG`
* Value: Paste the *entire* raw content of your configured `.env` file.

2. **Trigger the Action:**

* Navigate to the **Actions** tab.
* Select the **SOCKS5 FRP** workflow.
* Click **Run workflow**.
* Toggle **Bridge the workflows** to `true` to enable the endless auto-restart loop.

---

## 🔒 Security & Disclaimers

* **Dashboard Security:** The Web UI is protected using Basic Authentication via the `LOGGER_PASS` environment variable. Do not share your Cloudflare Tunnel URL and make sure to change your password from the default `admin123`.
* **Usage Policy:** This tool is built for network debugging, performance optimization, and educational research regarding proxy protocols. Ensure your usage complies with your cloud provider's Terms of Service.