#!/usr/bin/env python3
import argparse, os, re, signal, subprocess, sys, time, urllib.parse, urllib.request

CHUNK = 1024 * 1024
SOURCES = (
    ('OVH 欧洲', 'https://proof.ovh.net/files/1Gb.dat'),
    ('Vultr 阿姆斯特丹', 'https://ams-nl-ping.vultr.com/vultr.com.1000MB.bin'),
    ('Vultr 法兰克福', 'https://fra-de-ping.vultr.com/vultr.com.1000MB.bin'),
    ('Vultr 伦敦', 'https://lon-gb-ping.vultr.com/vultr.com.1000MB.bin'),
    ('Hetzner FSN', 'https://fsn1-speed.hetzner.com/1GB.bin'),
    ('Hetzner HEL', 'https://hel1-speed.hetzner.com/1GB.bin'),
    ('Vultr 东京', 'https://hnd-jp-ping.vultr.com/vultr.com.1000MB.bin'),
    ('Vultr 新加坡', 'https://sgp-ping.vultr.com/vultr.com.1000MB.bin'),
    ('Linode 东京', 'https://speedtest.tokyo2.linode.com/100MB-tokyo2.bin'),
    ('Linode 新加坡', 'https://speedtest.singapore.linode.com/100MB-singapore.bin'),
    ('Vultr 洛杉矶', 'https://lax-ca-us-ping.vultr.com/vultr.com.1000MB.bin'),
    ('Cloudflare', 'https://speed.cloudflare.com/__down?bytes={bytes}'),
)
MICROSOFT_PAGES = (
    'https://www.microsoft.com/software-download/windows11',
    'https://www.microsoft.com/en-us/software-download/windows11',
)
STOP = False
STATE_DIR = '/run' if os.access('/run', os.W_OK) else '/tmp'
LOG_DIR = '/var/log' if os.access('/var/log', os.W_OK) else '/tmp'
PID_FILE = os.path.join(STATE_DIR, 'traffic-burn-yundan.pid')
LOG_FILE = os.path.join(LOG_DIR, 'traffic-burn-yundan.log')

def stop(*_):
    global STOP
    STOP = True

def active_pid():
    try:
        pid = int(open(PID_FILE, encoding='ascii').read().strip())
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        try: os.unlink(PID_FILE)
        except OSError: pass
        return None

def start_background(target, source, limit):
    pid = active_pid()
    if pid: raise RuntimeError(f'已有任务正在运行（PID {pid}）。')
    command = [sys.executable, '-u', os.path.abspath(__file__), '--bytes', str(target),
               '--source', source, '--limit-mib', str(limit), '--worker']
    with open(LOG_FILE, 'a', encoding='utf-8') as log:
        log.write(f'\n--- {time.strftime("%Y-%m-%d %H:%M:%S")} 新任务 {fmt(target)} ---\n')
        log.flush()
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True,
                                   close_fds=True)
    with open(PID_FILE, 'w', encoding='ascii') as f: f.write(str(process.pid))
    print(f'后台任务已启动（PID {process.pid}）。现在可以退出 SSH。')
    print(f'再次运行 tb 可查看进度或停止任务。日志：{LOG_FILE}')

def show_status():
    pid = active_pid()
    print(f'运行状态：{"正在运行，PID " + str(pid) if pid else "当前没有任务"}')
    try:
        with open(LOG_FILE, encoding='utf-8', errors='replace') as f:
            lines = f.readlines()[-15:]
        if lines:
            print('最近日志：')
            print(''.join(lines), end='' if lines[-1].endswith('\n') else '\n')
    except OSError:
        print('暂无日志。')

def stop_background():
    pid = active_pid()
    if not pid:
        print('当前没有运行中的任务。'); return
    os.kill(pid, signal.SIGTERM)
    print(f'已向任务 PID {pid} 发送停止信号。')

def fmt(n):
    units = ('B', 'KiB', 'MiB', 'GiB', 'TiB')
    x = float(n)
    for u in units:
        if x < 1024 or u == units[-1]: return f'{x:.2f} {u}'
        x /= 1024

def ask_amount():
    choices = [1, 5, 10, 20, 50]
    print('1) 1 GiB\n2) 5 GiB\n3) 10 GiB\n4) 20 GiB\n5) 50 GiB\n6) 自定义')
    value = input('选择流量额度 [1-6]: ').strip()
    if value in '12345': return choices[int(value)-1] * 1024**3
    if value == '6':
        n = float(input('输入 GiB 数量（0.01-100）: ').strip())
        if not 0.01 <= n <= 100: raise ValueError('额度必须在 0.01-100 GiB。')
        return int(n * 1024**3)
    raise ValueError('无效选择。')

def cloudflare_url(amount):
    return dict(SOURCES)['Cloudflare'].format(bytes=amount)

def microsoft_iso_url():
    """Resolve a currently signed Windows ISO URL; never cache the result."""
    for page in MICROSOFT_PAGES:
        try:
            req = urllib.request.Request(page, headers={'User-Agent': 'Mozilla/5.0'})
            html = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'ignore')
            urls = re.findall(r'https?://[^\"\'<> ]+?\.iso(?:\?[^\"\'<> ]*)?', html, re.I)
            if urls:
                return urllib.parse.unquote(urls[0]).replace('\\u0026', '&')
        except Exception:
            continue
    raise RuntimeError('无法从微软官方页面获取当前 ISO 临时链接；未使用过期链接。')

def download(url, target, limit_mbps=20):
    separator = '&' if '?' in url else '?'
    url = f'{url}{separator}tb={time.time_ns()}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 TrafficBurn-YUNDAN/1.0'})
    started = time.monotonic(); total = 0; last = started; last_total = 0
    with urllib.request.urlopen(req, timeout=20) as r:
        while not STOP and total < target:
            data = r.read(min(CHUNK, target - total))
            if not data: break
            total += len(data)
            now = time.monotonic()
            if limit_mbps:
                expected = total / (limit_mbps * 1024 * 1024)
                elapsed = now - started
                if expected > elapsed: time.sleep(expected - elapsed)
            if now - last >= 1:
                speed = (total - last_total) / max(now - last, 0.001)
                print(f'已消耗 {fmt(total)}/{fmt(target)}，速度 {fmt(speed)}/s', flush=True)
                last, last_total = now, total
    return total, time.monotonic() - started

def source_pool(source, amount):
    public = [(name, cloudflare_url(amount) if name == 'Cloudflare' else url)
              for name, url in SOURCES]
    if source == 'cloudflare': return [public[-1]]
    if source == 'windows':
        try: return [('Windows 11 ISO', microsoft_iso_url())] + public
        except Exception as e: print(f'Windows 来源不可用：{e}\n切换到公开测速来源池。', file=sys.stderr)
    return public

def run(target, source, limit):
    remaining = target; total = 0; started = time.monotonic(); pool = source_pool(source, target); index = 0
    while remaining and not STOP:
        name, url = pool[index]
        print(f'使用来源：{name}')
        try:
            if name == 'Cloudflare': url = cloudflare_url(remaining)
            got, _ = download(url, remaining, limit)
        except Exception as e:
            print(f'{name} 失败：{e}', file=sys.stderr)
            index += 1
            if index >= len(pool):
                print('所有来源均不可用。', file=sys.stderr); break
            continue
        total += got; remaining -= got
        if got < min(remaining + got, CHUNK):
            print(f'{name} 返回数据过少，切换下一来源。', file=sys.stderr)
            index += 1
            if index >= len(pool): break
        elif remaining:
            print(f'{name} 本轮完成，继续下载剩余额度。')
    print(f'完成：{fmt(total)}，用时 {time.monotonic()-started:.1f}s' if not STOP else f'已停止：{fmt(total)}')

def menu():
    print('TrafficBurn-YUNDAN\n1) 后台消耗指定下载流量\n2) 查看任务状态和日志\n3) 停止后台任务\n4) 查看说明\n0) 退出')
    choice = input('请选择 [0-4]: ').strip()
    if choice == '0': return
    if choice == '2': show_status(); return
    if choice == '3': stop_background(); return
    if choice == '4':
        print('任务在后台运行，退出 SSH 不会中断；默认单线程、20 MiB/s、单次最多100 GiB。')
        return
    if choice != '1': raise ValueError('无效选择。')
    target = ask_amount()
    print('1) 自动来源池（推荐：OVH → Vultr → Hetzner → Linode → Cloudflare）')
    print('2) Windows 11 官方 ISO（失败后进入自动来源池）')
    source = input('选择来源 [1-2，默认 1]: ').strip() or '1'
    if source not in ('1', '2'): raise ValueError('无效来源。')
    limit = float(input('最大速度 MiB/s [默认 20]: ').strip() or '20')
    if not 0.1 <= limit <= 100: raise ValueError('速度必须在 0.1-100 MiB/s。')
    print(f'目标 {fmt(target)}，单线程，限速 {limit:g} MiB/s。确认开始？[y/N]')
    if input().strip().lower() != 'y': return
    start_background(target, 'auto' if source == '1' else 'windows', limit)

def main():
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    p = argparse.ArgumentParser()
    p.add_argument('--bytes', type=int)
    p.add_argument('--source', choices=('auto', 'cloudflare', 'windows'), default='auto')
    p.add_argument('--limit-mib', type=float, default=20)
    p.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = p.parse_args()
    if args.bytes:
        if not 10 * 1024**2 <= args.bytes <= 100 * 1024**3: raise SystemExit('额度必须在10 MiB-100 GiB。')
        try:
            run(args.bytes, args.source, args.limit_mib)
        finally:
            if args.worker:
                try:
                    if active_pid() == os.getpid(): os.unlink(PID_FILE)
                except OSError: pass
    else: menu()

if __name__ == '__main__':
    try: main()
    except (ValueError, KeyboardInterrupt) as e: print(f'错误：{e}', file=sys.stderr); sys.exit(1)
