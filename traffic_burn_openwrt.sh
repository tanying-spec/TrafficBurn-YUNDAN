#!/bin/sh
set -u
BASE=/tmp/traffic-burn-yundan
PIDFILE="$BASE.pid"
LOGFILE="$BASE.log"
CHUNK=1048576

fmt() { awk -v n="$1" 'BEGIN { if(n>=1073741824) printf "%.2f GiB",n/1073741824; else if(n>=1048576) printf "%.2f MiB",n/1048576; else printf "%.2f KiB",n/1024 }'; }
running() { [ -s "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE" 2>/dev/null)" 2>/dev/null; }
cleanup() { rm -f "$PIDFILE"; }
download_range() {
  url="$1"; start="$2"; end="$3"; size="$4"; limit="$5"
  curl -fL --silent --show-error --connect-timeout 15 --max-time 45 --limit-rate "${limit}M" \
    -H 'Cache-Control: no-cache' -A 'TrafficBurn-YUNDAN/1.0' \
    --range "$start-$end" "$url" | head -c "$size" | wc -c
}
worker() {
  target="$1"; limit="$2"; total=0; start_time=$(date +%s)
  sources="https://proof.ovh.net/files/1Gb.dat|https://ams-nl-ping.vultr.com/vultr.com.1000MB.bin|https://fra-de-ping.vultr.com/vultr.com.1000MB.bin|https://lon-gb-ping.vultr.com/vultr.com.1000MB.bin|https://fsn1-speed.hetzner.com/1GB.bin|https://hel1-speed.hetzner.com/1GB.bin|https://hnd-jp-ping.vultr.com/vultr.com.1000MB.bin|https://sgp-ping.vultr.com/vultr.com.1000MB.bin|https://speedtest.tokyo2.linode.com/100MB-tokyo2.bin|https://speedtest.singapore.linode.com/100MB-singapore.bin|https://lax-ca-us-ping.vultr.com/vultr.com.1000MB.bin"
  oldifs="$IFS"; IFS='|'
  for url in $sources; do
    [ "$total" -lt "$target" ] || break
    while [ "$total" -lt "$target" ]; do
      remain=$((target-total)); size=$CHUNK; [ "$remain" -lt "$size" ] && size=$remain
      end=$((size-1)); echo "使用来源：$url（已消耗 $(fmt "$total")/$(fmt "$target")）"
      got=$(download_range "$url" 0 "$end" "$size" "$limit") || got=0
      case "$got" in *[!0-9]*|'') got=0;; esac
      [ "$got" -gt 0 ] || break
      total=$((total+got))
      [ "$got" -lt "$size" ] && break
    done
  done
  IFS="$oldifs"; echo "完成：$(fmt "$total")，用时 $(( $(date +%s)-start_time ))s"
  cleanup
}
status() { if running; then echo "正在运行，PID $(cat "$PIDFILE")"; else echo '当前没有任务'; fi; [ -f "$LOGFILE" ] && tail -15 "$LOGFILE"; }
stop_task() { if running; then kill "$(cat "$PIDFILE")"; echo '已发送停止信号'; else echo '当前没有任务'; fi; }
start_task() {
  running && { echo "已有任务运行，PID $(cat "$PIDFILE")"; return; }
  target=$((1*1024*1024*1024)); echo '1) 1 GiB  2) 5 GiB  3) 10 GiB  4) 20 GiB  5) 50 GiB  6) 自定义'
  printf '选择流量额度 [1-6]: '; read -r n
  case "$n" in 1) target=$((1*1024*1024*1024));;2) target=$((5*1024*1024*1024));;3) target=$((10*1024*1024*1024));;4) target=$((20*1024*1024*1024));;5) target=$((50*1024*1024*1024));;6) printf '输入 GiB 数量 [0.01-100]: '; read -r g; target=$(awk -v g="$g" 'BEGIN{if(g<0.01||g>100) exit 1; printf "%.0f",g*1073741824}') || { echo '额度必须在 0.01-100 GiB'; return; };;*) echo '无效选择'; return;; esac
  printf '最大速度 MiB/s [默认20]: '; read -r limit; limit=${limit:-20}
  case "$limit" in *[!0-9.]*|'') echo '速度格式无效'; return;; esac
  awk -v l="$limit" 'BEGIN{exit !(l>=0.1&&l<=100)}' || { echo '速度必须在 0.1-100 MiB/s'; return; }
  printf '确认后台开始？[y/N] '; read -r ok; [ "$ok" = y ] || return
  mkdir -p "$(dirname "$LOGFILE")"; nohup sh "$0" --worker "$target" "$limit" >>"$LOGFILE" 2>&1 </dev/null & echo $! >"$PIDFILE"
  echo "后台任务已启动，PID $(cat "$PIDFILE")，现在可以退出 SSH。"
}
if [ "${1:-}" = --worker ]; then worker "$2" "$3"; exit; fi
echo 'TrafficBurn-YUNDAN (OpenWrt/Kwrt)'; echo '1) 后台消耗指定下载流量'; echo '2) 查看状态和日志'; echo '3) 停止任务'; echo '0) 退出'; printf '请选择 [0-3]: '; read -r c
case "$c" in 1) start_task;;2) status;;3) stop_task;; esac
