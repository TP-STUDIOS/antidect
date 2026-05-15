import base64
import socket
import ssl
import threading

def _pipe(src: socket.socket, dst: socket.socket) -> None:
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except Exception:
            pass

class HttpAuthRelay:

    def __init__(
        self,
        upstream_host: str,
        upstream_port: int,
        user: str,
        password: str,
        upstream_scheme: str = "http",
    ) -> None:
        self._upstream_host = upstream_host
        self._upstream_port = int(upstream_port)
        self._upstream_tls = upstream_scheme.lower() == "https"
        auth = f"{user}:{password}".encode("utf-8")
        self._auth_header = b"Proxy-Authorization: Basic " + base64.b64encode(auth) + b"\r\n"
        self._server: socket.socket | None = None
        self._stop = False
        self._port = 0

    def start(self) -> int:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        srv.listen(64)
        self._server = srv
        self._port = srv.getsockname()[1]
        threading.Thread(target=self._accept_loop, daemon=True).start()
        return self._port

    def stop(self) -> None:
        self._stop = True
        try:
            if self._server is not None:
                self._server.close()
        except Exception:
            pass

    def _accept_loop(self) -> None:
        assert self._server is not None
        while not self._stop:
            try:
                client, _addr = self._server.accept()
            except Exception:
                break
            threading.Thread(target=self._handle, args=(client,), daemon=True).start()

    def _connect_upstream(self) -> socket.socket:
        raw = socket.create_connection(
            (self._upstream_host, self._upstream_port), timeout=15
        )
        if self._upstream_tls:
            ctx = ssl.create_default_context()
            return ctx.wrap_socket(raw, server_hostname=self._upstream_host)
        return raw

    def _handle(self, client: socket.socket) -> None:
        try:
            client.settimeout(15)
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = client.recv(8192)
                if not chunk:
                    return
                data += chunk
                if len(data) > 65536:
                    return
            head, _, body_after = data.partition(b"\r\n\r\n")
            first, _, headers_blob = head.partition(b"\r\n")

            clean = []
            for line in headers_blob.split(b"\r\n"):
                lname = line.split(b":", 1)[0].strip().lower()
                if lname == b"proxy-authorization":
                    continue
                if lname == b"proxy-connection":
                    continue
                clean.append(line)
            if clean and clean[-1] == b"":
                clean.pop()

            rebuilt = first + b"\r\n"
            if clean:
                rebuilt += b"\r\n".join(clean) + b"\r\n"
            rebuilt += self._auth_header + b"\r\n" + body_after

            try:
                upstream = self._connect_upstream()
            except Exception:
                try:
                    client.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                except Exception:
                    pass
                return

            try:
                upstream.sendall(rebuilt)
            except Exception:
                try:
                    upstream.close()
                except Exception:
                    pass
                return

            client.settimeout(None)
            try:
                upstream.settimeout(None)
            except Exception:
                pass

            t1 = threading.Thread(target=_pipe, args=(client, upstream), daemon=True)
            t2 = threading.Thread(target=_pipe, args=(upstream, client), daemon=True)
            t1.start()
            t2.start()
            t1.join()
            t2.join()
            try:
                upstream.close()
            except Exception:
                pass
        except Exception:
            pass
        finally:
            try:
                client.close()
            except Exception:
                pass
