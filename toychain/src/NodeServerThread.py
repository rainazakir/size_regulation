import os
import pickle
import psutil
import socket
import struct
import threading
import time
import urllib.parse
from queue import Queue
from time import sleep

from toychain.src import constants
from toychain.src.MessageHandler import MessageHandler
from toychain.src.constants import ENCODING


def log_memory_background():
    """Daemon thread to log process memory usage periodically."""
    proc = psutil.Process(os.getpid())
    while True:
        try:
            rss = proc.memory_info().rss / (1024 * 1024)  # in MB
            #print(f"[Memory] {rss:.2f} MB used")
            time.sleep(5)
        except Exception as e:
            print(f"[Memory logger error] {e}")
            break


# Start memory logging once at import
threading.Thread(target=log_memory_background, daemon=True).start()


class NodeServerThread(threading.Thread):
    """Thread answering to requests, every node has one."""

    def __init__(self, node, host, port, id):
        super().__init__()
        self.sock = None
        self.id = id
        self.node = node
        self.host = host
        self.port = port
        self.max_packet = 6000000
        self.message_handler = MessageHandler(self)
        self.terminate_flag = threading.Event()
        print(f"Node {self.id} starting on port {self.port}")

    def run(self):
        """Waiting for one other Node to connect."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))

        while not self.terminate_flag.is_set():
            try:
                self.sock.settimeout(5)
                self.sock.listen(1)
                client_sock, client_address = self.sock.accept()
                self.handle_connection(client_sock)
            except socket.timeout:
                pass
            except Exception as e:
                print(f"[Node {self.id}] Exception in run: {e}")
                raise e

            sleep(0.00001)

        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass

        self.sock.close()
        #print(f"Node {self.id} stopped")

    def handle_connection(self, sock):
        """Answer with the asked information."""
        try:
            request = self.receive(sock)  # already returns the Python object
            #print(f"[Node {self.id}] Received request: {type(request)}")
            answer = self.message_handler.handle_request(request)
            self.send(answer, sock)  # pass object, let send() pickle
        except Exception as e:
            print(f"[Node {self.id}] Error in handle_connection: {e}")

    def send_request(self, enode, request):
        """Sends a request and returns the answer."""
        parsed_enode = urllib.parse.urlparse(enode)
        address = (parsed_enode.hostname, parsed_enode.port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            sock.connect(address)
            self.send(request, sock)  # pass object, not pre-pickled
            answer = self.receive(sock)
            if answer is not None:
                self.message_handler.handle_answer(answer)
            return answer
        except Exception as e:
            print(f"[Node {self.id}] Error in send_request to {address}: {e}")
        finally:
            sock.close()

        return None

    def send(self, obj, sock):
        """Send a Python object with a length prefix."""
        data = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

        if len(data) > 5 * 1024 * 1024:  # 5 MB hard cap
            raise MemoryError(f"Refusing to send object of {len(data)} bytes")

        length_prefix = struct.pack("!I", len(data))
        sock.sendall(length_prefix + data)

    def receive(self, sock):
        """Receive a complete pickled object with a length prefix."""
        raw_len = self._recv_exact(sock, 4)
        if not raw_len:
            raise ConnectionError("Socket closed before reading length")

        (length,) = struct.unpack("!I", raw_len)

        if length > 5 * 1024 * 1024:  # 5 MB hard cap
            raise MemoryError(f"Refusing to receive object of {length} bytes")

        data = self._recv_exact(sock, length)

        if len(data) != length:
            raise ConnectionError(
                f"Incomplete message: expected {length}, got {len(data)}"
            )

        return pickle.loads(data)

    def _recv_exact(self, sock, n):
        """Helper to receive exactly n bytes from the socket."""
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                break
            buf += chunk
        return buf
