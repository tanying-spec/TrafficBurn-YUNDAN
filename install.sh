#!/bin/sh
set -eu
VERSION=1.0.6
PROGRAM_SHA256=5039ba3514fc418108d0c9391a40d03e964cf7b4d6b5ec83546e0188cf90b074
OPENWRT_SHA256=5391661d3430ad58cba922c2d1b886a4f818544d17dda487ba3dab9836d58723
DIR=/opt/traffic-burn-yundan
BIN=/usr/local/sbin/traffic-burn
ALIAS=/usr/local/sbin/tb
OPENWRT_ALIAS=/usr/bin/tb
URL="https://raw.githubusercontent.com/tanying-spec/TrafficBurn-YUNDAN/v$VERSION/traffic_burn.py"
MODE=python
if ! command -v python3 >/dev/null 2>&1 && command -v opkg >/dev/null 2>&1; then MODE=openwrt
elif ! command -v python3 >/dev/null 2>&1; then
    if command -v apk >/dev/null 2>&1; then apk add --no-cache python3 curl
    elif command -v apt-get >/dev/null 2>&1; then apt-get update && apt-get install -y --no-install-recommends python3 curl
    else echo '需要 Python3 和 curl。' >&2; exit 1; fi
fi
command -v curl >/dev/null 2>&1 || { echo '需要 curl。' >&2; exit 1; }
tmp=$(mktemp /tmp/traffic-burn.XXXXXX)
trap 'rm -f "$tmp"' EXIT
mkdir -p "$DIR" /usr/local/sbin
if [ "$MODE" = openwrt ]; then
  shell_url="https://raw.githubusercontent.com/tanying-spec/TrafficBurn-YUNDAN/v$VERSION/traffic_burn_openwrt.sh"
  curl -fLsS --proto '=https' --connect-timeout 12 --max-time 120 "$shell_url" -o "$tmp"
  [ "$(sha256sum "$tmp" | awk '{print $1}')" = "$OPENWRT_SHA256" ] || { echo 'OpenWrt 程序校验失败。' >&2; exit 1; }
  cp "$tmp" "$DIR/traffic_burn_openwrt.sh"; chmod 700 "$DIR/traffic_burn_openwrt.sh"
else
  curl -fLsS --proto '=https' --connect-timeout 12 --max-time 120 "$URL" -o "$tmp"
  [ "$(sha256sum "$tmp" | awk '{print $1}')" = "$PROGRAM_SHA256" ] || { echo '程序校验失败。' >&2; exit 1; }
  cp "$tmp" "$DIR/traffic_burn.py"; chmod 700 "$DIR/traffic_burn.py"
fi
if [ -e "$ALIAS" ] && [ "$(readlink -f "$ALIAS" 2>/dev/null || true)" != "$BIN" ]; then echo "$ALIAS 已被占用" >&2; exit 1; fi
if [ "$MODE" = openwrt ]; then
cat >"$BIN" <<EOF
#!/bin/sh
exec sh "$DIR/traffic_burn_openwrt.sh" "\$@"
EOF
else
cat >"$BIN" <<EOF
#!/bin/sh
exec python3 "$DIR/traffic_burn.py" "\$@"
EOF
fi
chmod 755 "$BIN"
[ -e "$ALIAS" ] || ln -s "$BIN" "$ALIAS"
if [ "$MODE" = openwrt ]; then
  [ ! -e "$OPENWRT_ALIAS" ] || [ "$(readlink -f "$OPENWRT_ALIAS" 2>/dev/null || true)" = "$BIN" ] || { echo "$OPENWRT_ALIAS 已被占用" >&2; exit 1; }
  [ -e "$OPENWRT_ALIAS" ] || ln -s "$BIN" "$OPENWRT_ALIAS"
fi
echo '安装完成，运行 tb 或 traffic-burn。'
