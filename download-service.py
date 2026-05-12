import os
import platform
import zipfile
import tarfile
import requests
import shutil

def get_frp_arch():
    machine = platform.machine().lower()
    # Map các loại kiến trúc phổ biến
    if machine in ["aarch64", "arm64"]:
        return "arm64"
    elif machine in ["armv7l", "arm"]:
        return "arm"
    return "amd64" # Mặc định cho PC

def install_frp():
    sys = platform.system().lower()
    arch = get_frp_arch() # Tự động nhận diện thay vì gán cứng amd64
    version = "0.61.1"
    
    if sys == "windows":
        file_ext = "zip"
        os_name = "windows"
        bin_name = "frpc.exe"
    else:
        file_ext = "tar.gz"
        os_name = "linux" # Termux được nhận diện là linux
        bin_name = "frpc"

    url = f"https://github.com/fatedier/frp/releases/download/v{version}/frp_{version}_{os_name}_{arch}.{file_ext}"
    archive_name = f"frp_archive.{file_ext}"

    print(f"[*] Đang tải Frp v{version} từ GitHub...")
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(archive_name, "wb") as f:
        for chunk in r.iter_content(8192): f.write(chunk)

    print("[*] Giải nén...")
    extract_dir = "frp_temp"
    if archive_name.endswith(".zip"):
        with zipfile.ZipFile(archive_name, "r") as z: z.extractall(extract_dir)
    else:
        with tarfile.open(archive_name, "r:gz") as t: t.extractall(extract_dir)

    # Tìm file frpc trong thư mục vừa giải nén và đưa ra ngoài
    for root, dirs, files in os.walk(extract_dir):
        if bin_name in files:
            shutil.move(os.path.join(root, bin_name), os.path.join(".", bin_name))
            break
    
    # Dọn dẹp
    shutil.rmtree(extract_dir)
    os.remove(archive_name)
    if sys != "windows": os.chmod(bin_name, 0o755)
    print(f"[+] Đã cài đặt xong: {bin_name}")

if __name__ == "__main__":
    install_frp()