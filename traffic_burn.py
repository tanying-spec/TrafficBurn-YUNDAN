#!/usr/bin/env python3
import argparse, os, re, signal, sys, time, urllib.parse, urllib.request

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

def stop(*_):
    global STOP
    STOP = True

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
    print('TrafficBurn-YUNDAN\n1) 消耗指定下载流量\n2) 查看说明\n0) 退出')
    choice = input('请选择 [0-2]: ').strip()
    if choice == '0': return
    if choice == '2':
        print('仅用于你控制或明确允许测试的网络；默认单线程、20 MiB/s、单次最多100 GiB。')
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
    run(target, 'auto' if source == '1' else 'windows', limit)

def main():
    signal.signal(signal.SIGINT, stop)
    p = argparse.ArgumentParser()
    p.add_argument('--bytes', type=int)
    p.add_argument('--source', choices=('auto', 'cloudflare', 'windows'), default='auto')
    p.add_argument('--limit-mib', type=float, default=20)
    args = p.parse_args()
    if args.bytes:
        if not 10 * 1024**2 <= args.bytes <= 100 * 1024**3: raise SystemExit('额度必须在10 MiB-100 GiB。')
        run(args.bytes, args.source, args.limit_mib)
    else: menu()

if __name__ == '__main__':
    try: main()
    except (ValueError, KeyboardInterrupt) as e: print(f'错误：{e}', file=sys.stderr); sys.exit(1)
