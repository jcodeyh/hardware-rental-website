import json
import os
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "default.conf.template"
NGINX = os.environ.get("NGINX_BIN") or shutil.which("nginx")


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _stub(routes):
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def _reply(self):
            seen.append((self.command, self.path, dict(self.headers)))
            status, body = routes(self)
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = _reply
        do_POST = _reply

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, seen


def _bff_routes(handler):
    if handler.path == "/auth/me":
        if "haas_session=good" in handler.headers.get("Cookie", ""):
            return 200, {"user": {"userId": "1"}}
        return 401, {"error": "Please log in"}
    return 200, {"bff": handler.path}


def _data_routes(handler):
    return 200, {"data": handler.path}


def _client_routes(handler):
    return 200, {"client": handler.path}


def _render(port, bff, data, client):
    text = TEMPLATE.read_text()
    values = {
        "NGINX_LOCAL_RESOLVERS": "127.0.0.1",
        "CLIENT_UPSTREAM": f"http://127.0.0.1:{client}",
        "SERVER_UPSTREAM": f"http://127.0.0.1:{bff}",
        "DATA_UPSTREAM": f"http://127.0.0.1:{data}",
    }
    for key, value in values.items():
        text = text.replace("${" + key + "}", value)
    assert "${" not in text
    return text.replace("listen 8080;", f"listen 127.0.0.1:{port};")


@pytest.fixture(scope="module")
def gateway(tmp_path_factory):
    if not NGINX:
        pytest.skip("nginx is not installed; set NGINX_BIN")
    root = tmp_path_factory.mktemp("nginx")
    bff, bff_seen = _stub(_bff_routes)
    data, data_seen = _stub(_data_routes)
    client, _ = _stub(_client_routes)
    port = _free_port()
    (root / "site.conf").write_text(_render(port, bff.server_port, data.server_port, client.server_port))
    for name in ("client_body", "proxy", "fastcgi", "uwsgi", "scgi", "logs"):
        (root / name).mkdir()
    (root / "nginx.conf").write_text(f"""
daemon off;
master_process off;
pid {root}/nginx.pid;
error_log {root}/logs/error.log;
events {{}}
http {{
    access_log off;
    client_body_temp_path {root}/client_body;
    proxy_temp_path {root}/proxy;
    fastcgi_temp_path {root}/fastcgi;
    uwsgi_temp_path {root}/uwsgi;
    scgi_temp_path {root}/scgi;
    include {root}/site.conf;
}}
""")
    check = subprocess.run([NGINX, "-t", "-p", str(root), "-c", str(root / "nginx.conf")],
                           capture_output=True, text=True)
    assert check.returncode == 0, check.stderr
    process = subprocess.Popen([NGINX, "-p", str(root), "-c", str(root / "nginx.conf")])
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(base + "/healthz", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    yield base, bff_seen, data_seen, bff
    process.terminate()
    process.wait(timeout=10)
    for server in (bff, data, client):
        server.shutdown()


def _get(url, cookie=None, method="GET"):
    request = urllib.request.Request(url, method=method)
    if cookie:
        request.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"null")


def test_data_requires_a_session(gateway):
    base, _, data_seen, _ = gateway
    before = len(data_seen)
    status, body = _get(base + "/api/data/governments")
    assert status == 401
    assert body == {"success": False, "message": "Please log in"}
    status, _ = _get(base + "/api/data/governments", cookie="haas_session=bad")
    assert status == 401
    assert len(data_seen) == before


def test_data_passes_with_a_session_and_strips_prefix(gateway):
    base, bff_seen, data_seen, _ = gateway
    status, body = _get(base + "/api/data/governments/Austin/summary?match=laptop", cookie="haas_session=good")
    assert status == 200
    assert body == {"data": "/governments/Austin/summary?match=laptop"}
    assert bff_seen[-1][1] == "/auth/me"
    assert "haas_session=good" in bff_seen[-1][2].get("Cookie", "")


def test_app_routes_go_to_bff_without_auth_check(gateway):
    base, bff_seen, _, _ = gateway
    status, body = _get(base + "/api/app/auth/login", method="POST")
    assert status == 200
    assert body == {"bff": "/auth/login"}


def test_budget_context_stub_is_gone(gateway):
    base, _, _, _ = gateway
    status, body = _get(base + "/api/projects/get_budget_context", method="POST")
    assert status == 503
    assert body["success"] is False


def test_front_end_and_health(gateway):
    base, _, _, _ = gateway
    assert _get(base + "/dashboard")[1] == {"client": "/dashboard"}
    with urllib.request.urlopen(base + "/healthz", timeout=5) as response:
        assert response.read() == b"ok\n"


def test_bff_down_gives_json_service_down(gateway):
    base, _, _, bff = gateway
    bff.shutdown()
    bff.server_close()
    status, body = _get(base + "/api/data/governments", cookie="haas_session=good")
    assert status == 503
    assert body["success"] is False
