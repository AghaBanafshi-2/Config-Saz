import socket
import threading
import os
import struct
import time

USERNAME = os.environ.get('PROXY_USER', 'admin')
PASSWORD = os.environ.get('PROXY_PASS', 'change_me')
PORT = int(os.environ.get('PORT', 1080))

def get_proxy_uri():
    """ساخت آدرس کامل SOCKS5 از متغیرهای Railway"""
    domain = os.environ.get('RAILWAY_TCP_PROXY_DOMAIN') or os.environ.get('RAILWAY_PUBLIC_DOMAIN')
    proxy_port = os.environ.get('RAILWAY_TCP_PROXY_PORT') or str(PORT)

    if not domain:
        return None, None

    uri = f"socks5://{USERNAME}:{PASSWORD}@{domain}:{proxy_port}"
    return domain, uri

def print_proxy_info():
    domain, uri = get_proxy_uri()
    print("=" * 70, flush=True)
    if uri:
        print("✅ SOCKS5 PROXY IS READY", flush=True)
        print(f"🔗 URI: {uri}", flush=True)
        print(f"🌐 Host: {domain}", flush=True)
        print(f"🔌 Port: {os.environ.get('RAILWAY_TCP_PROXY_PORT', PORT)}", flush=True)
        print(f"👤 User: {USERNAME}", flush=True)
        print(f"🔒 Pass: {PASSWORD}", flush=True)
    else:
        print("⚠️  TCP Proxy variables not found yet.", flush=True)
        print("   Enable TCP Proxy on port 1080 in Railway Settings,", flush=True)
        print("   then redeploy. The public address will be printed.", flush=True)
    print("=" * 70, flush=True)

def handle_client(client_socket):
    try:
        version, nmethods = struct.unpack('!BB', client_socket.recv(2))
        if version != 5:
            client_socket.close()
            return

        methods = client_socket.recv(nmethods)
        if 2 not in methods:
            client_socket.sendall(struct.pack('!BB', 5, 0xFF))
            client_socket.close()
            return

        client_socket.sendall(struct.pack('!BB', 5, 2))

        auth_version, ulen = struct.unpack('!BB', client_socket.recv(2))
        uname = client_socket.recv(ulen).decode()
        plen = struct.unpack('!B', client_socket.recv(1))[0]
        passwd = client_socket.recv(plen).decode()

        if uname != USERNAME or passwd != PASSWORD:
            client_socket.sendall(struct.pack('!BB', 1, 1))
            client_socket.close()
            return

        client_socket.sendall(struct.pack('!BB', 1, 0))

        ver, cmd, rsv, atyp = struct.unpack('!BBBB', client_socket.recv(4))
        if cmd != 1:
            client_socket.close()
            return

        if atyp == 1:
            addr = socket.inet_ntoa(client_socket.recv(4))
        elif atyp == 3:
            addr_len = struct.unpack('!B', client_socket.recv(1))[0]
            addr = client_socket.recv(addr_len).decode()
        else:
            client_socket.close()
            return

        port = struct.unpack('!H', client_socket.recv(2))[0]

        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.connect((addr, port))

        reply = struct.pack('!BBBB', 5, 0, 0, 1) + socket.inet_aton('0.0.0.0') + struct.pack('!H', 0)
        client_socket.sendall(reply)

        def forward(source, destination):
            try:
                while True:
                    data = source.recv(4096)
                    if not data:
                        break
                    destination.sendall(data)
            except:
                pass
            finally:
                source.close()
                destination.close()

        t1 = threading.Thread(target=forward, args=(client_socket, remote))
        t2 = threading.Thread(target=forward, args=(remote, client_socket))
        t1.start()
        t2.start()

    except Exception as e:
        print(f"Error: {e}", flush=True)
        client_socket.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', PORT))
    server.listen(100)
    print(f"SOCKS5 Proxy listening on 0.0.0.0:{PORT}", flush=True)

    # چاپ اولیه
    print_proxy_info()

    # یک تایمر برای چاپ مجدد بعد از ۲۰ ثانیه (در صورتی که متغیرها دیرتر set شوند)
    def delayed_print():
        time.sleep(20)
        print("\n🔁 Re-checking proxy info...", flush=True)
        print_proxy_info()
    threading.Thread(target=delayed_print, daemon=True).start()

    while True:
        client, addr = server.accept()
        threading.Thread(target=handle_client, args=(client,)).start()

if __name__ == '__main__':
    main()
