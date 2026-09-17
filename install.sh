#!/bin/sh
set -eu
VERSION=1.0.0
PROGRAM_SHA256=13e6549c82846cae3836c03cdbc536ab51082c857b53a3877b78565684e2e52e
DIR=/opt/traffic-burn-yundan
BIN=/usr/local/sbin/traffic-burn
ALIAS=/usr/local/sbin/tb
URL="https://raw.githubusercontent.com/tanying-spec/TrafficBurn-YUNDAN/v$VERSION/traffic_burn.py"
if ! command -v python3 >/dev/null 2>&1; then
    if command -v apk >/dev/null 2>&1; then apk add --no-cache python3 curl
    elif command -v apt-get >/dev/null 2>&1; then apt-get update && apt-get install -y --no-install-recommends python3 curl
    else echo '需要 Python3 和 curl。' >&2; exit 1; fi
fi
command -v curl >/dev/null 2>&1 || { echo '需要 curl。' >&2; exit 1; }
tmp=$(mktemp /tmp/traffic-burn.XXXXXX)
trap 'rm -f "$tmp"' EXIT
curl -fLsS --proto '=https' --connect-timeout 12 --max-time 120 "$URL" -o "$tmp"
[ "$(sha256sum "$tmp" | awk '{print $1}')" = "$PROGRAM_SHA256" ] || { echo '程序校验失败。' >&2; exit 1; }
mkdir -p "$DIR" /usr/local/sbin
cp "$tmp" "$DIR/traffic_burn.py"
chmod 700 "$DIR/traffic_burn.py"
if [ -e "$ALIAS" ] && [ "$(readlink -f "$ALIAS" 2>/dev/null || true)" != "$BIN" ]; then echo "$ALIAS 已被占用" >&2; exit 1; fi
cat >"$BIN" <<EOF
#!/bin/sh
exec python3 "$DIR/traffic_burn.py" "\$@"
EOF
chmod 755 "$BIN"
[ -e "$ALIAS" ] || ln -s "$BIN" "$ALIAS"
echo '安装完成，运行 tb 或 traffic-burn。'
