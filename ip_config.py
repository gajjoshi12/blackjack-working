"""
Helper module to read IP address from ip.txt file
"""
import os

# Fallback IP for the target PC (update this to the target machine's IP)
FALLBACK_IP = "192.168.10.2"

def get_ip_address():
    """
    Read IP address from ip.txt file in the same directory as this script.
    Returns the IP address as a string, or FALLBACK_IP if file not found.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ip_file = os.path.join(script_dir, "ip.txt")
    
    try:
        with open(ip_file, 'r') as f:
            ip = f.read().strip()
            # Remove any http:// or https:// prefix if present
            ip = ip.replace('http://', '').replace('https://', '')
            # Remove any port numbers if present
            if ':' in ip:
                ip = ip.split(':')[0]
            return ip.strip()
    except FileNotFoundError:
        print(f"Warning: ip.txt not found at {ip_file}, using FALLBACK_IP {FALLBACK_IP}")
        return FALLBACK_IP
    except Exception as e:
        print(f"Error reading ip.txt: {e}")
        return None

def get_web_url(port=3000):
    """Get the full web URL with port"""
    ip = get_ip_address()
    if ip:
        return f"http://{ip}:{port}"
    return None

def get_websocket_url(port=6790):
    """Get the WebSocket URL with port"""
    ip = get_ip_address()
    if ip:
        return f"ws://{ip}:{port}"
    return None



