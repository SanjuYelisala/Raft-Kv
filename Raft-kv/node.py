import socket
import sys
import selectors
import json

from connection.py import feed


class NodeServer():
    def __init__(self, host, port, on_tick, on_message):
        self.host = host
        self.port = port
        self.on_tick = on_tick
        self.on_message = on_message

        self.sel = selectors.DefaultSelector()


    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setblocking(False)
        server.bind((self.host, self.port))
        server.listen(1024)

        self.sel.register(server, selectors.EVENT_READ,self.accept)
        while True:
            events = self.sel.select(timeout=0.1) # returns after 0.1 seconds even if no events

            if not events:
                self.on_tick()
            for key, mask in events:
                if key.data is self.accept:  # server socket
                    self.accept(key.fileobj)
                else:  # client socket
                    self.read(key)
                    
    def accept(self, sock):
        conn, addr = sock.accept()
        conn.setblocking(False)
        connection = Connection()
        self.sel.register(conn, selectors.EVENT_READ, connection)

    def read(self, key):
        raw = key.fileobj.recv(128)
        if not raw:
            self.sel.unregister(key.fileobj)
            key.fileobj.close()
            return
        message = key.data.feed(raw)
        

        for msg in message:
            decoded_message = msg.decode().strip()
            self.on_message(json.loads(decoded_message))
            key.fileobj.sendall((decoded_message + "\n").encode())
            

    
    def send(self, host, port, message):
        election_socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        election_socket_server.connect((host, port))
        election_socket_server.sendall((json.dumps(message) + "\n").encode())
            


