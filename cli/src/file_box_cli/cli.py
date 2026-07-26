"""CLI for the shared file-box — list, download, upload, delete files."""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
import mimetypes
from pathlib import Path

CONFIG_PATH = Path.home() / '.config' / 'file-box.json'

def _load_config():
    try:
        if CONFIG_PATH.is_file():
            return json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {}

def _save_config(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    CONFIG_PATH.chmod(0o600)

def _get_url():
    cfg = _load_config()
    return cfg.get('url') or os.environ.get('FILE_BOX_URL', '')

def _get_token():
    cfg = _load_config()
    return cfg.get('token') or os.environ.get('FILE_BOX_TOKEN', '')

def _headers():
    h = {'Accept': 'application/json'}
    t = _get_token()
    if t:
        h['X-Auth-Token'] = t
    return h

def _url(path):
    base = _get_url().rstrip('/')
    t = _get_token()
    if t:
        sep = '&' if '?' in path else '?'
        path = f"{path}{sep}token={urllib.parse.quote(t)}"
    return f"{base}{path}"

def _req(method, url, data=None, headers=None):
    h = _headers()
    if data is not None:
        h['Content-Type'] = 'application/json'
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
            msg = err.get('error', err)
        except json.JSONDecodeError:
            msg = body or str(e)
        print(f"\u274c Error {e.code}: {msg}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"\u274c Connection failed: {e.reason}", file=sys.stderr)
        sys.exit(1)

def cmd_config_set(key, value):
    cfg = _load_config()
    cfg[key] = value
    _save_config(cfg)
    print(f"\u2705 \u5df2\u4fdd\u5b58: {key}")

def cmd_config_get():
    cfg = _load_config()
    env_url = os.environ.get('FILE_BOX_URL', '')
    env_token = os.environ.get('FILE_BOX_TOKEN', '')
    print("Configuration")
    print(f"  URL:   {cfg.get('url') or env_url or '(not set)'}")
    print(f"  Token: {'set' if cfg.get('token') or env_token else 'not set'}")
    print(f"  File:  {CONFIG_PATH}")

def cmd_config_login(url, password):
    try:
        req = urllib.request.Request(
            f"{url.rstrip('/')}/api/auth",
            data=json.dumps({"password": password}).encode(),
            headers={"Content-Type": "application/json"},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        if not data.get('ok'):
            print("\u274c \u5bc6\u7801\u9519\u8bef", file=sys.stderr)
            sys.exit(1)
        token = data.get('token', '')
        cfg = _load_config()
        cfg['url'] = url.rstrip('/')
        if token:
            cfg['token'] = token
        _save_config(cfg)
        print(f"\u2705 \u5df2\u8fde\u63a5\u5230: {url}")
        print("\u2705 Token \u5df2\u4fdd\u5b58")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
            msg = err.get('error', err)
        except json.JSONDecodeError:
            msg = body or str(e)
        print(f"\u274c \u8fde\u63a5\u5931\u8d25 ({e.code}): {msg}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"\u274c \u8fde\u63a5\u5931\u8d25: {e.reason}", file=sys.stderr)
        sys.exit(1)

def cmd_list(json_out):
    data = _req('GET', _url('/api/files'))
    files = data.get('files', [])
    if json_out:
        print(json.dumps(files, ensure_ascii=False, indent=2))
        return
    if not files:
        print("\U0001f4c2 \u6682\u65e0\u6587\u4ef6")
        return
    print(f"\U0001f4c2 \u5171 {len(files)} \u4e2a\u6587\u4ef6\n")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f['name']}  ({f['size']})")
    print()

def cmd_download(names, output_dir=None):
    ok, fail = 0, []
    for name in names:
        enc = urllib.parse.quote(name)
        url = _url(f'/api/files/{enc}')
        dest = os.path.join(output_dir, name) if output_dir else name
        print(f"\u2b07  {name} ...", file=sys.stderr)
        try:
            req = urllib.request.Request(url, headers=_headers())
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            with open(dest, 'wb') as f:
                f.write(data)
            sz = len(data)
            size_str = f"{sz/1048576:.1f} MB" if sz > 1048576 else f"{sz/1024:.1f} KB"
            print(f"  \u2705 {dest}  ({size_str})")
            ok += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            try:
                err = json.loads(body)
                msg = err.get('error', err)
            except json.JSONDecodeError:
                msg = body or str(e)
            print(f"  \u274c {name}: {msg}", file=sys.stderr)
            fail.append(name)
        except urllib.error.URLError as e:
            print(f"  \u274c {name}: {e.reason}", file=sys.stderr)
            fail.append(name)
    if ok > 0:
        print(f"\u2705 \u4e0b\u8f7d\u5b8c\u6210: {ok} \u4e2a\u6587\u4ef6")
    if fail:
        print(f"\u274c {len(fail)} \u4e2a\u5931\u8d25", file=sys.stderr)
        if ok == 0:
            sys.exit(1)

def cmd_upload(paths):
    import io
    import uuid
    boundary = '----' + uuid.uuid4().hex
    body = io.BytesIO()
    for fp in paths:
        fpath = Path(fp)
        if not fpath.is_file():
            print(f"\u26a0  \u8df3\u8fc7: {fp} (\u4e0d\u662f\u6587\u4ef6)", file=sys.stderr)
            continue
        fname = fpath.name
        body.write(f'--{boundary}\r\n'.encode())
        body.write(f'Content-Disposition: form-data; name="file"; filename="{fname}"\r\n'.encode())
        ctype, _ = mimetypes.guess_type(fname)
        body.write(f'Content-Type: {ctype or "application/octet-stream"}\r\n\r\n'.encode())
        body.write(fpath.read_bytes())
        body.write(b'\r\n')
    body.write(f'--{boundary}--\r\n'.encode())
    data = body.getvalue()
    url = _url('/api/upload')
    headers = {'Content-Type': f'multipart/form-data; boundary={boundary}'}
    t = _get_token()
    if t:
        headers['X-Auth-Token'] = t
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode())
        uploaded = result.get('files', [])
        for f in uploaded:
            print(f"\u2705 \u5df2\u4e0a\u4f20: {f['filename']}  ({f['size']})")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
            msg = err.get('error', err)
        except json.JSONDecodeError:
            msg = body or str(e)
        print(f"\u274c \u4e0a\u4f20\u5931\u8d25 ({e.code}): {msg}", file=sys.stderr)
        sys.exit(1)

def cmd_delete(names):
    ok, fail = 0, []
    for name in names:
        enc = urllib.parse.quote(name)
        url = _url(f'/api/files/{enc}')
        try:
            data = _req('DELETE', url)
            if data.get('success'):
                ok += 1
            else:
                fail.append(name)
        except SystemExit:
            fail.append(name)
    if ok > 0:
        print(f"\u2705 \u5df2\u5220\u9664 {ok} \u4e2a\u6587\u4ef6")
    if fail:
        print(f"\u274c {len(fail)} \u4e2a\u5220\u9664\u5931\u8d25: {', '.join(fail)}", file=sys.stderr)
        if ok == 0:
            sys.exit(1)

def cmd_storage(json_out):
    data = _req('GET', _url('/api/storage'))
    if json_out:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("\U0001f4be \u5b58\u50a8\u7a7a\u95f4")
    print(f"   \u5df2\u7528: {data['used']}")
    print(f"   \u603b\u91cf: {data['total']}")
    print(f"   \u7a7a\u95f2: {data['free']}")
    print(f"   \u5360\u6bd4: {data['usagePercent']}")
    print(f"   \u6587\u4ef6\u6570: {data['files']}")

def main():
    parser = argparse.ArgumentParser(
        description='\U0001f4c2 File Box CLI \u2014 list / download / upload / delete files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='First use:\n  file-box config login https://your-box.up.railway.app <password>\n'
    )

    sub = parser.add_subparsers(dest='command', required=True)

    p_cfg = sub.add_parser('config', help='Manage configuration')
    cfg_sub = p_cfg.add_subparsers(dest='config_cmd', required=True)
    p_login = cfg_sub.add_parser('login', help='Login and save URL + token')
    p_login.add_argument('url', help='File box URL')
    p_login.add_argument('password', help='Access password')
    p_set = cfg_sub.add_parser('set', help='Set config key manually')
    p_set.add_argument('key', choices=['url', 'token'])
    p_set.add_argument('value', help='Value')
    p_get = cfg_sub.add_parser('get', help='Show current config')

    p_list = sub.add_parser('list', aliases=['ls'], help='List all files')
    p_down = sub.add_parser('download', aliases=['dl', 'get'], help='Download file(s)')
    p_down.add_argument('files', nargs='+', help='File name(s)')
    p_down.add_argument('-o', '--output-dir', help='Output directory (default: current)')
    p_up = sub.add_parser('upload', aliases=['up', 'put'], help='Upload file(s)')
    p_up.add_argument('files', nargs='+')
    p_del = sub.add_parser('delete', aliases=['rm', 'del'], help='Delete file(s)')
    p_del.add_argument('files', nargs='+', help='File name(s)')
    p_st = sub.add_parser('storage', aliases=['df', 'space'], help='Show storage usage')

    args = parser.parse_args()

    if args.command == 'config':
        if args.config_cmd == 'login':
            cmd_config_login(args.url, args.password)
        elif args.config_cmd == 'set':
            cmd_config_set(args.key, args.value)
        elif args.config_cmd == 'get':
            cmd_config_get()
        return

    if not _get_url():
        print("\u274c \u672a\u914d\u7f6e\u6587\u4ef6\u7bb1\u5730\u5740", file=sys.stderr)
        print("   \u8bf7\u5148\u8fd0\u884c: file-box config login <URL> <\u5bc6\u7801>", file=sys.stderr)
        sys.exit(1)

    cmd = args.command
    if cmd in ('list', 'ls'):
        cmd_list(getattr(args, 'json', False))
    elif cmd in ('download', 'dl', 'get'):
        cmd_download(args.files, args.output_dir)
    elif cmd in ('upload', 'up', 'put'):
        cmd_upload(args.files)
    elif cmd in ('delete', 'rm', 'del'):
        cmd_delete(args.files)
    elif cmd in ('storage', 'df', 'space'):
        cmd_storage(getattr(args, 'json', False))

if __name__ == '__main__':
    main()
