import network
import socket
import gc

SSID = 'Pico2W'
KEY = 'captiveportal'

ap = network.WLAN(network.AP_IF)
ap.config(ssid=SSID, key=KEY, security=network.WLAN.SEC_WPA3)
ap.active(True)
while not ap.active():
    pass
print('AP is active, page served at', ap.ifconfig()[0])

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
server = socket.socket()
server.bind(addr)
server.listen(1)
print('HTTP server listening on', addr)

def get_mime(path):
    if path.endswith('.html'):   return 'text/html'
    if path.endswith('.css'):    return 'text/css'
    if path.endswith('.js'):     return 'application/javascript'
    if path.endswith('.png'):    return 'image/png'
    if path.endswith('.jpg') or path.endswith('.jpeg'):
        return 'image/jpeg'
    return 'application/octet-stream'

def serve(conn):
    try:
        req = conn.recv(1024)
        first_line = req.split(b'\r\n')[0]
        _, raw_path, _ = first_line.split()
        if raw_path == b'/':
            raw_path = b'/index.html'
        path = raw_path.decode()
        file_path = '/public' + path
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            mime = get_mime(path)
            header = (
                'HTTP/1.1 200 OK\r\n'
                'Content-Type: {}\r\n'
                'Content-Length: {}\r\n'
                'Connection: close\r\n'
                '\r\n'
            ).format(mime, len(content))
            conn.send(header.encode())
            conn.send(content)
        except OSError:
            err = b'<h1>404 Not Found</h1>'
            header = (
                'HTTP/1.1 404 Not Found\r\n'
                'Content-Type: text/html\r\n'
                'Content-Length: {}\r\n'
                'Connection: close\r\n'
                '\r\n'
            ).format(len(err))
            conn.send(header.encode())
            conn.send(err)
    finally:
        conn.close()

try:
    while True:
        conn, addr = server.accept()
        serve(conn)
        gc.collect()
except KeyboardInterrupt:
    print('\nShutting down server...')
    server.close()
    ap.active(False)
    print('Server stopped.')
