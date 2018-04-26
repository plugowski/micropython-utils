import os
import socket
import network
from time import sleep
import uselect
import uasyncio as asyncio
import websocket_helper
from websocket import websocket


class ClientClosedError(Exception):
    pass


class WebSocketConnection:
    def __init__(self, addr, s, close_callback):
        self.client_close = False
        self._need_check = False

        self.address = addr
        self.socket = s
        self.ws = websocket(s, True)
        self.poll = uselect.poll()
        self.close_callback = close_callback

        self.socket.setblocking(False)
        self.poll.register(self.socket, uselect.POLLIN)

    def read(self):
        poll_events = self.poll.poll(0)

        if not poll_events:
            return

        # Check the flag for connection hung up
        if poll_events[0][1] & uselect.POLLHUP:
            self.client_close = True

        msg_bytes = None
        try:
            msg_bytes = self.ws.read()
        except OSError:
            self.client_close = True

        # If no bytes => connection closed. See the link below.
        # http://stefan.buettcher.org/cs/conn_closed.html
        if not msg_bytes or self.client_close:
            raise ClientClosedError()

        return msg_bytes

    def write(self, msg):
        try:
            self.ws.write(msg)
        except OSError:
            self.client_close = True

    def is_closed(self):
        return self.socket is None

    def close(self):
        print("Closing connection.")
        self.poll.unregister(self.socket)
        self.socket.close()
        self.socket = None
        self.ws = None
        if self.close_callback:
            self.close_callback(self)


class WebSocketClient:
    def __init__(self, conn):
        self.connection = conn

    def process(self):
        pass


class WebSocketServer:

    def __init__(self, max_connections: int = 1):
        self._listen_s = None
        self._listen_poll = None
        self._clients = []
        self._max_connections = max_connections
        self._web_dir = 'www'

    def _setup_conn(self, port):
        self._listen_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listen_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listen_poll = uselect.poll()
        self._listen_s.bind(socket.getaddrinfo("0.0.0.0", port)[0][4])
        self._listen_s.listen(1)
        self._listen_poll.register(self._listen_s)
        for i in (network.AP_IF, network.STA_IF):
            iface = network.WLAN(i)
            if iface.active():
                self._address = (iface.ifconfig()[0], port)
                print("WebSocket started on ws://%s:%d" % self._address)

    def _check_new_connections(self, accept_handler):
        poll_events = self._listen_poll.poll(0)
        if not poll_events:
            return

        if poll_events[0][1] & uselect.POLLIN:
            accept_handler()

    def _accept_conn(self):
        cl, remote_addr = self._listen_s.accept()
        data = cl.recv(32)

        print("Client connection from:", remote_addr)
        print('data', data)

        if len(self._clients) >= self._max_connections:
            # Maximum connections limit reached
            cl.setblocking(True)
            cl.sendall("HTTP/1.1 503 Too many connections\n\n")
            cl.sendall("\n")
            # TODO: Make sure the data is sent before closing
            sleep(0.1)
            cl.close()
            return

        try:
            websocket_helper.server_handshake(cl)
        except OSError:
            # Not a websocket connection, serve webpage
            requested_file = request_method = None

            if data:
                # data should looks like GET /index.html HTTP/1.1\r\nHost: 19'
                data = data.decode()
                request_method = data.split(' ')[0]

            if request_method == "GET":
                # requested file is on second position in data, ignore all get parameters after question mark
                requested_file = data.split(' ')[1].split('?')[0]

            requested_file = "/index.html" if requested_file in [None, '/'] else requested_file
            self._serve_file(requested_file, cl)

            return

        self._clients.append(self._make_client(WebSocketConnection(remote_addr, cl, self.remove_connection)))

    def _make_client(self, conn):
        return WebSocketClient(conn)

    def _serve_file(self, file: str, sock: socket):
        try:
            # todo: check if file is in subdirectory
            # check if file exists ( file always contains / at the beginning
            if file[1:] not in os.listdir(self._web_dir):
                sock.sendall(self._generate_headers(404))
                sock.sendall(b'<h1>404 Not Found</h1>')
                sock.close()
                return

            file_path = self._web_dir + file
            length = os.stat(file_path)[6]
            sock.sendall(self._generate_headers(200, file_path, length))
            # Process page by lines to avoid large strings
            with open(file_path, 'r') as f:
                for line in f:
                    sock.sendall(line)
        except OSError:
            sock.sendall(self._generate_headers(500))

        sock.close()

    @staticmethod
    def _generate_headers(code: int, file_name: str = None, length: int = None) -> str:

        header = ''
        content_type = 'text/html'

        http_codes = {
            200: 'OK',
            404: 'Not Found',
            500: 'Internal Server Error'
        }

        mime_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'html': 'text/html',
            'htm': 'text/html',
            'css': 'text/css',
            'js': 'application/javascript'
        }

        if code in http_codes:
            header = 'HTTP/1.1 {} {}\n'.format(code, http_codes[code])

        if file_name is not None:
            ext = file_name.split('.')[1]
            if ext in mime_types:
                content_type = mime_types[ext]

        header += 'Content-Type: {}\n'.format(content_type)
        header += 'Content-Length: {}\n'.format(length)
        header += 'Server: ESPServer\n'
        header += 'Connection: close\n\n'  # Close connection after completing the request
        return header

    def stop(self):
        if self._listen_poll:
            self._listen_poll.unregister(self._listen_s)
        self._listen_poll = None
        if self._listen_s:
            self._listen_s.close()
        self._listen_s = None

        for client in self._clients:
            client.connection.close()
        print("Stopped WebSocket server.")

    def start(self, port=80):
        if self._listen_s:
            self.stop()
        self._setup_conn(port)
        print("Started WebSocket server.")

    async def process_all(self):
        while True:
            self._check_new_connections(self._accept_conn)

            for client in self._clients:
                client.process()

            await asyncio.sleep_ms(10)

    def remove_connection(self, conn):
        for client in self._clients:
            if client.connection is conn:
                self._clients.remove(client)
                return
