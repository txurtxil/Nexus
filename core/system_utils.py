import os
import socket

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_android_root():
    paths = ["/storage/emulated/0", os.path.expanduser("~/storage/shared")]
    for p in paths:
        try:
            os.listdir(p)
            return p
        except:
            pass
    return os.path.dirname(os.path.abspath(__file__))

def get_sys_info():
    cpu = 0.0
    ram = 0.0
    cores = os.cpu_count() or 1
    if HAS_PSUTIL:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
    return cpu, ram, cores
