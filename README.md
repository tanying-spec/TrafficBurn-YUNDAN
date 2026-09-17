# TrafficBurn-YUNDAN

用于你自己控制或明确允许测试的服务器，按指定额度产生下载流量。默认后台运行，退出 SSH 不会中断；任务单线程、限速、达到额度自动停止，不接受任意第三方 URL。

## 安装

```sh
curl -fsSL https://raw.githubusercontent.com/tanying-spec/TrafficBurn-YUNDAN/main/install.sh -o /tmp/traffic-burn-install.sh && sh /tmp/traffic-burn-install.sh
tb
```

在菜单中可以启动后台任务、查看进度日志和停止任务。

OpenWrt/Kwrt 路由器会自动使用原生 Shell 模式，不需要安装 Python3，也不占用额外的 Python 依赖空间。

也可直接运行：

```sh
python3 traffic_burn.py --bytes $((5*1024*1024*1024)) --source auto --limit-mib 20
```

默认使用公开测速来源池：OVH、Vultr、Hetzner、Linode、Cloudflare，优先使用已在欧洲小型 VPS 上验证兼容性较好的 OVH，遇到 403、超时或连接失败自动切换。大文件读完后继续循环，直到达到指定额度。Windows 源每次运行时尝试从微软官方页面提取当天的临时签名链接，不缓存过期地址；解析失败进入测速来源池。

安全限制：单次 10 MiB–100 GiB，默认 20 MiB/s，最大 100 MiB/s，单线程；Ctrl+C 可停止。不要用于压测、攻击或消耗不属于你的站点资源。
