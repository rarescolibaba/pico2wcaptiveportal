import _thread
import time
import network
import socket
import uselect
import errno
import utime

MAX_CLIENTS = 10

stop_flag = False
stop_lock = _thread.allocate_lock()

def get_mime_type(filename):
    if filename.endswith('.html'):
        return 'text/html'
    if filename.endswith('.css'):
        return 'text/css'
    if filename.endswith('.js'):
        return 'application/javascript'
    if filename.endswith('.png'):
        return 'image/png'
    if filename.endswith('.jpg') or filename.endswith('.jpeg'):
        return 'image/jpeg'
    return 'application/octet-stream'

def open_ap():
    wlan = network.WLAN(network.AP_IF)
    wlan.active(True)
    wlan.config(
        ssid='Pico2W',
        key='captiveportal',
        security=network.WLAN.SEC_WPA3
    )
    print("Access point started:", wlan.config('ssid'))
    return wlan

def serve_static_file(sock, file_path):
    try:
        with open(file_path, 'rb') as f:
            mime = get_mime_type(file_path)
            header = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: {}\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).format(mime)
            sock.sendall(header.encode())
            while True:
                chunk = f.read(512)
                if not chunk:
                    break
                sent = 0
                while sent < len(chunk):
                    try:
                        sent_now = sock.send(chunk[sent:])
                        if sent_now is None:
                            sent_now = 0
                        sent += sent_now
                    except OSError as e:
                        if hasattr(e, 'errno') and e.errno == errno.EAGAIN:
                            print("Socket send EAGAIN, sleeping 100ms...")
                            utime.sleep_ms(100)
                            continue
                        else:
                            raise
    except Exception as e:
        print("File not found:", file_path, e)
        sock.sendall(b"HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n404 Not Found")

def process_http_request(sock, req_str, probe_paths, redir):
    lines = req_str.split('\r\n')
    if lines:
        parts = lines[0].split()
        if len(parts) >= 2 and parts[0] == 'GET':
            path = parts[1]
            # captive portal probe paths
            if path in probe_paths:
                sock.sendall(redir.encode())
            else:  # Serve static files
                if path == '/':
                    path = '/index.html'
                file_path = '/public' + path
                serve_static_file(sock, file_path)
        else:
            sock.sendall(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n")

def run_web_server(wlan_ap):
    dns_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dns_sock.bind(('0.0.0.0', 53))

    http_sock = socket.socket()
    http_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    http_sock.bind(('0.0.0.0', 80))
    http_sock.listen(MAX_CLIENTS - 1)

    poll = uselect.poll()
    poll.register(dns_sock, uselect.POLLIN)
    poll.register(http_sock, uselect.POLLIN)
    client_socks = set()

    print("Captive portal running (DNS + HTTP)...")

    probe_paths = [
        "/redirect", "/connecttest.txt", "/ncsi.txt", "/hotspot-detect.html",
        "/generate_204", "/library/test/success.html"
    ]

    redir = (
    "HTTP/1.1 302 Found\r\n"
    "Location: http://192.168.4.1/\r\n"
    "Connection: close\r\n"
    "\r\n"
    )

    try:
        while True:
            with stop_lock:
                if stop_flag:
                    break
            events = poll.poll(100)
            for sock, event in events:
                if sock == dns_sock:
                    try:
                        data, addr = dns_sock.recvfrom(512)
                        if data:
                            txid = data[:2]
                            flags = b'\x81\x80'
                            qdcount = b'\x00\x01'
                            ancount = b'\x00\x01'
                            response = txid + flags + qdcount + ancount + b'\x00\x00\x00\x00'
                            query = data[12:]
                            response += query
                            response += b'\xC0\x0C\x00\x01\x00\x01\x00\x00\x00\x3C\x00\x04'
                            response += bytes([192, 168, 4, 1])
                            dns_sock.sendto(response, addr)
                    except Exception as e:
                        print("DNS loop error:", e)
                elif sock == http_sock:
                    try:
                        conn, addr = http_sock.accept()
                        if len(client_socks) >= MAX_CLIENTS:
                            print("Too many clients, refusing connection from", addr)
                            try:
                                conn.sendall(b"HTTP/1.1 503 Service Unavailable\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nServer busy, try again later.")
                            except Exception:
                                pass
                            conn.close()
                            continue
                        conn.setblocking(False)
                        print("New HTTP connection from", addr)
                        poll.register(conn, uselect.POLLIN)
                        client_socks.add(conn)
                    except Exception as e:
                        print("HTTP loop error:", e)
                elif sock in client_socks:
                    try:
                        req = sock.recv(1024)
                        if not req:
                            poll.unregister(sock)
                            client_socks.remove(sock)
                            sock.close()
                            continue
                        req_str = req.decode()
                        # captive portal magic
                        if any(x in req_str for x in [
                            "connectivitycheck.android.com",
                            "captive.apple.com",
                            "msftncsi.com"
                        ]):
                            sock.sendall(redir.encode())
                        else:
                            process_http_request(sock, req_str, probe_paths, redir)
                        poll.unregister(sock)
                        client_socks.remove(sock)
                        sock.close()
                    except Exception as e:
                        print("HTTP client error:", e)
                        try:
                            poll.unregister(sock)
                        except Exception:
                            pass
                        client_socks.discard(sock)
                        sock.close()
    finally:
        dns_sock.close()
        http_sock.close()
        wlan_ap.active(False)
        print("Captive portal stopped")

def main_thread():
    while True:
        with stop_lock:
            if stop_flag:
                break
        t = utime.localtime()
        print("{:02d}:{:02d}:{:02d}: main thread loop".format(t[3], t[4], t[5]))
        time.sleep(5) # just to reduce logging, you can change this

def captive_portal_thread():
    global stop_flag
    wlan_ap = open_ap()
    run_web_server(wlan_ap)

_thread.start_new_thread(captive_portal_thread, ())

try:
    main_thread()
except KeyboardInterrupt:
    with stop_lock:
        stop_flag = True
    print("Main thread stopped")

print("Finished")