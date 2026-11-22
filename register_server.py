#!/usr/bin/env python3
"""家庭多账号辅助服务（内部服务，不直接对外）。

开放的口子：
  POST /register {username}   -> 以「口令=用户名」在 LX 同步服务端建号（免密模型）
  GET  /users                 -> 只返回账号名列表（供前端账号选择器）
  GET  /favpls?user=<name>    -> 读该账号收藏的歌单（跨设备同步）
  POST /favpls {user, list}   -> 覆盖保存该账号收藏的歌单

管理员口令只在本服务内使用、永不下发到浏览器。
防护：用户名白名单字符、保留名拦截、账号总数上限、按 IP 限频、收藏条数/字段清洗。
"""
import json
import os
import re
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

UPSTREAM = "http://lx-sync-server:9527"
SECRETS = "/secrets/credentials.env"
DATA_DIR = "/data/favpls"
MAX_USERS = 20
RATE_LIMIT = 10          # 每 IP 每小时最多注册次数
RATE_WINDOW = 3600

NAME_RE = re.compile(r"^[\w\u4e00-\u9fff-]{1,16}$", re.UNICODE)
RESERVED = {"_open", "admin", "default", "user", "users"}
_hits = {}

os.makedirs(DATA_DIR, exist_ok=True)


def frontend_password():
    for line in open(SECRETS, encoding="utf-8"):
        if line.startswith("FRONTEND_PASSWORD="):
            return line.strip().split("=", 1)[1]
    raise RuntimeError("FRONTEND_PASSWORD not found")


ADMIN = frontend_password()


def upstream(method, path, body=None, timeout=15):
    r = urllib.request.Request(UPSTREAM + path, method=method)
    r.add_header("x-frontend-auth", ADMIN)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, data=data, timeout=timeout) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return None, str(e)[:100]


def list_names():
    st, body = upstream("GET", "/api/users")
    if st != 200:
        return None
    try:
        return [u.get("name") for u in json.loads(body) if u.get("name")]
    except Exception:
        return None


def rate_ok(ip):
    now = time.time()
    arr = [t for t in _hits.get(ip, []) if now - t < RATE_WINDOW]
    if len(arr) >= RATE_LIMIT:
        _hits[ip] = arr
        return False
    arr.append(now)
    _hits[ip] = arr
    return True


def favpls_path(user):
    return os.path.join(DATA_DIR, user + ".json")


def read_favpls(user):
    try:
        with open(favpls_path(user), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except Exception:
        return []


def write_favpls(user, items):
    clean = []
    for it in items[:300]:
        if not isinstance(it, dict):
            continue
        src = str(it.get("src") or "")
        pid = str(it.get("id") or "")
        name = str(it.get("name") or "")[:120]
        if src not in ("wy", "tx", "kg", "kw", "mg") or not pid or not name:
            continue
        clean.append({"src": src, "id": pid[:64], "name": name,
                      "img": str(it.get("img") or "")[:500],
                      "total": str(it.get("total") or "")[:20],
                      "play_count": str(it.get("play_count") or "")[:20]})
    tmp = favpls_path(user) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False)
    os.replace(tmp, favpls_path(user))
    return clean


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/users":
            names = list_names()
            if names is None:
                return self._json(502, {"success": False, "message": "服务器无响应"})
            return self._json(200, {"success": True, "names": names})
        if u.path == "/favpls":
            user = (parse_qs(u.query).get("user") or [""])[0]
            if not NAME_RE.match(user):
                return self._json(400, {"success": False, "message": "账号名不对"})
            return self._json(200, {"success": True, "list": read_favpls(user)})
        return self._json(404, {"success": False, "message": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n).decode() or "{}")
        except Exception:
            return self._json(400, {"success": False, "message": "请求格式不对"})
        if u.path == "/favpls":
            user = str(body.get("user") or "")
            items = body.get("list")
            if not NAME_RE.match(user) or not isinstance(items, list):
                return self._json(400, {"success": False, "message": "参数不对"})
            names = list_names()
            if names is None:
                return self._json(502, {"success": False, "message": "服务器无响应"})
            if user not in names:
                return self._json(404, {"success": False, "message": "账号不存在"})
            saved = write_favpls(user, items)
            return self._json(200, {"success": True, "list": saved})
        if u.path != "/register":
            return self._json(404, {"success": False, "message": "not found"})
        ip = self.headers.get("X-Real-IP") or self.client_address[0]
        name = str(body.get("username") or "").strip()
        if not NAME_RE.match(name) or name.lower() in RESERVED:
            return self._json(400, {"success": False, "message": "名字只能用文字、数字、下划线（1–16 字）"})
        if not rate_ok(ip):
            return self._json(429, {"success": False, "message": "注册太频繁了，歇一会儿再试"})
        names = list_names()
        if names is None:
            return self._json(502, {"success": False, "message": "服务器无响应"})
        if name in names:
            return self._json(409, {"success": False, "message": "这个名字已经被用了，换一个或直接点它登录"})
        if len(names) >= MAX_USERS:
            return self._json(403, {"success": False, "message": "账号数量已达上限"})
        st, _ = upstream("POST", "/api/users", body={"name": name, "password": name})
        if st == 200:
            return self._json(200, {"success": True})
        if st == 409:
            return self._json(409, {"success": False, "message": "这个名字已经被用了"})
        return self._json(502, {"success": False, "message": "创建失败，稍后再试"})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), H).serve_forever()
