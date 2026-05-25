# AuraDesk 云端化部署说明

本次需求把原来的“手机和电脑必须同一局域网直连”升级成云端架构：

- 云端后端负责提醒存储、设备注册、事件推送。
- Android 端可以把捕获到的系统通知上传到云端。
- 桌面端可以连接云端事件流，接收手机端事件。
- 手机端只要能联网访问云端地址，就不要求和电脑在同一个 Wi‑Fi。

## 新增文件

```text
/Users/tt/Desktop/AuraDesk_数字人视觉与语音模块/cloud-server.js
/Users/tt/Desktop/AuraDesk_Android_FloatingPet/app/src/main/java/com/auradesk/floatingpet/CloudApi.java
/Users/tt/Desktop/AuraDesk_Android_FloatingPet/app/src/main/java/com/auradesk/floatingpet/AuraNotificationListenerService.java
```

## 架构

```text
Android 手机
  - 悬浮小精灵
  - 通知监听服务
  - 上传通知/事件
        |
        | HTTPS/HTTP
        v
云端后端 cloud-server.js
  - /api/devices/register
  - /api/reminders
  - /api/notifications/capture
  - /api/events 事件推送 SSE
        |
        | SSE 长连接
        v
桌面端 Electron AuraDesk
  - 接收云端事件
  - 小精灵播报/提醒
```

## 1. 本地启动云端后端测试

在当前 Mac 上可以先用本地端口模拟云服务器：

```bash
cd '/Users/tt/Desktop/AuraDesk_数字人视觉与语音模块'
AURADESK_CLOUD_TOKEN=dev-token AURADESK_CLOUD_PORT=8787 npm run cloud
```

健康检查：

```bash
curl http://127.0.0.1:8787/health
```

新增云端提醒：

```bash
curl -X POST http://127.0.0.1:8787/api/reminders \
  -H 'Authorization: Bearer dev-token' \
  -H 'Content-Type: application/json' \
  -d '{"title":"云端测试提醒","source":"curl"}'
```

查看云端提醒：

```bash
curl http://127.0.0.1:8787/api/reminders \
  -H 'Authorization: Bearer dev-token'
```

## 2. 桌面端连接云端

启动桌面端时加入云端地址和 token：

```bash
cd '/Users/tt/Desktop/AuraDesk_数字人视觉与语音模块'
AURADESK_CLOUD_URL=http://127.0.0.1:8787 \
AURADESK_CLOUD_TOKEN=dev-token \
npm start
```

如果部署到公网云服务器，把地址换成你的公网域名：

```bash
AURADESK_CLOUD_URL=https://api.your-domain.com \
AURADESK_CLOUD_TOKEN=你的token \
npm start
```

桌面端现在会：

- 启动时注册桌面设备。
- 本地新增/修改提醒时同步到云端。
- 监听云端 `/api/events` 事件流。
- 收到手机通知事件时，让桌面小精灵提示。
- 收到手机小精灵 `pet.speak` 事件时，让桌面小精灵播报。

## 3. Android 端云端配置

Android App 配置页新增了：

- 云端地址，例如：`https://api.your-domain.com`
- 云端 token
- 保存云端配置并注册设备
- 打开通知监听权限

使用方式：

1. 打开 Android App。
2. 填云端地址和 token。
3. 点“保存云端配置并注册设备”。
4. 点“打开通知监听权限”。
5. 在系统设置中允许 `AuraDesk 提醒监听`。
6. 点“启动悬浮小精灵”。

之后手机捕获到其他 App 的通知，会上传到云端：

```text
POST /api/notifications/capture
```

注意：Android 通知监听属于敏感权限，必须用户手动授权。App 不能偷偷开启。

## 4. 去局域网化说明

原方案：

```text
手机 -> http://电脑局域网IP:37821
```

问题：手机和电脑必须同一 Wi‑Fi，IP 变化就会失效。

新方案：

```text
手机 -> 云服务器
电脑 -> 云服务器
```

优点：

- 手机不需要和电脑同一 Wi‑Fi。
- 手机只要联网就能上传提醒和事件。
- 电脑端只要能访问同一个云端地址，就能接收事件。

## 5. 部署到云服务器

最简单的 Node.js 云服务器部署方式：

```bash
scp cloud-server.js user@server:/opt/auradesk/cloud-server.js
ssh user@server
cd /opt/auradesk
AURADESK_CLOUD_TOKEN=换成强随机token PORT=8787 node cloud-server.js
```

生产环境建议：

- 使用 HTTPS 域名。
- 使用强随机 token，不要用 `dev-token`。
- 用 pm2/systemd 保持服务常驻。
- 用 Nginx 反向代理到 `127.0.0.1:8787`。
- 后续把 JSON 文件存储替换为 SQLite/PostgreSQL。

## 6. WebRTC 说明

本次先落地“云服务器中转”方案，因为最稳定、最容易测试。

WebRTC 可以作为下一阶段：

- 云端只做信令服务器。
- 手机和桌面建立 P2P 连接。
- 适合实时语音/视频/低延迟控制。

但 WebRTC 对 NAT、断线重连、信令、ICE/STUN/TURN 要求更高，不适合作为当前 MVP 的第一步。

## 7. 已知限制

- 当前云端后端是小型 MVP，用 JSON 文件持久化，适合原型，不适合大量用户生产环境。
- Android 通知监听需要用户手动授权。
- iPhone 不能做 Android 这种系统级通知监听和全局悬浮窗。
- 如果修改 Android 原生代码，需要重新打包 APK。
