# TrafficBurn-YUNDAN

用于你自己控制或明确允许测试的服务器，按指定额度产生下载流量。默认单线程、限速、达到额度自动停止，不接受任意第三方 URL。

## 安装

```sh
curl -fsSL https://raw.githubusercontent.com/tanying-spec/TrafficBurn-YUNDAN/main/install.sh -o /tmp/traffic-burn-install.sh && sh /tmp/traffic-burn-install.sh
tb
```

也可直接运行：

```sh
python3 traffic_burn.py --bytes $((5*1024*1024*1024)) --source cloudflare --limit-mib 20
```

来源：Cloudflare Speed Test 精确端点；Windows 11 官方 ISO 大文件源。Windows 源每次运行时尝试从微软官方页面提取当天的临时签名链接，不缓存过期地址；解析失败自动回退到 Cloudflare 精确源。公开源可能限速或临时不可用，程序不会无限重试。

安全限制：单次 10 MiB–100 GiB，默认 20 MiB/s，最大 100 MiB/s，单线程；Ctrl+C 可停止。不要用于压测、攻击或消耗不属于你的站点资源。
