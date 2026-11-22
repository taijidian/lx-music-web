# lx-music-web

一个为 [lx-music-server](https://github.com/lyswhut/lx-music-desktop)（社区增强版）打造的现代化 Web 前端：单文件 PWA 播放器 + 家庭多账号免密共享 + 跨音源竞速播放。

> 本项目只是**前端**，不包含任何音乐内容、音源或后端。你需要自备一个正在运行的 lx-music-server 后端和你自己的音源。

## 功能

- **完整播放器**：侧边栏（首页 / 歌单广场 / 我喜欢 / 播放历史）+ 底部播放条 + 全屏播放页（大封面、同步歌词、点歌词行跳转）、播放队列抽屉、顺序 / 随机 / 单曲循环三模式、键盘快捷键、MediaSession（锁屏控制）
- **聚合搜索与歌单**：多平台结果合并去重；歌单广场按分类与年代（70 后～20 年代）聚合各平台歌单；首页有继续听、按你的口味、推荐歌单、热门艺人、六大排行榜
- **跨源竞速播放**：点一首歌时，本源与其它平台的同名版本并行解析、先到先播；拿到链接还要用音频元素**验活**，死链自动换下一个候选；下一首预解析、列表推测预解析，起播更快
- **家庭多账号免密**：家里每人一个账号，点名字直接进入，不用输密码；「我喜欢」与后端同步账号打通，和 LX 桌面端 / 安卓端同一份数据跨设备同步；自建歌单（收藏歌单）按账号云端保存
- **PWA**：可安装到手机 / 桌面主屏幕，独立窗口运行（需要 HTTPS，见下文）

## 架构

```
浏览器 ──HTTPS──> nginx (lx-web)
                    ├── /            → 本前端（静态文件）
                    ├── /api/music/*、/api/user/* 等 → lx-sync-server（你的 LX 后端）
                    ├── /api/register、/api/family-users、/api/favpls → lx-register（本仓库附带的小服务）
                    └── 其余路径（LX 客户端同步协议、/admin 等）→ 透传后端
```

- `index.html` — 全部前端（HTML/CSS/JS 单文件，无构建步骤）
- `register_server.py` — 内部小服务：只开放「注册账号、账号名单、收藏歌单读写」三个口子。LX 的管理员口令只存在于这个服务里，**不下发到浏览器**
- `nginx.conf` — 含 HTTP(9527) / 域名 HTTP 跳转 / HTTPS 三个 server 块示例
- `docker-compose.yml` — lx-web + lx-register 两个容器；后端不在此 compose 内，通过外部网络 `lx-music_default` 互通（见部署说明）

## 账号模型（先读这一节）

免密的实现方式：注册时由 lx-register 调用后端管理接口建号，**账号的形式口令 = 账号名本身**；前端登录时用「账号名 + 同名口令」换取令牌，用户全程只点名字。

这适合**家庭内网 / 私人小圈子**场景：任何知道账号名的人都能登入该账号。请勿把注册接口暴露给不受信任的公网人群；确需公网使用时，建议在 nginx 层给 `/api/register` 与 `/api/family-users` 再加一层访问控制。

## 部署

前置：Docker（含 compose v2）、一个已在运行的 lx-music-server（容器名默认 `lx-sync-server`，其 compose 网络名为 `lx-music_default`；如你的不同，请改 `docker-compose.yml` 的 external network 与 `nginx.conf` 里的上游名）。

```bash
git clone https://github.com/taijidian/lx-music-web.git
cd lx-music-web

# 1) 生成 PWA 图标（PNG 是二进制文件，未直接入库）
pip install pillow
python3 icons/generate_icons.py

# 2) 准备口令文件：把你 LX 后端的管理口令（FRONTEND_PASSWORD）写进来
mkdir -p secrets
printf 'FRONTEND_PASSWORD=你的后端管理口令\n' > secrets/credentials.env
chmod 600 secrets/credentials.env

# 3) 启动
docker compose up -d
```

启动后访问 `http://<你的服务器>:9527/` 即是播放器。

### HTTPS（PWA 真安装与 Service Worker 必需）

`nginx.conf` 已含 443 块模板：把 `music.example.com` 换成你的域名，把证书放到 `./certs/fullchain.pem` 与 `./certs/key.pem`（例如用 acme.sh 以 webroot 方式签发，验证目录已挂载在 `./acme-webroot`）。iOS 的「添加到主屏幕」在 HTTP 下也能用，但安卓 / 桌面 Chrome 的完整安装必须 HTTPS。

## 说明与免责

- 本项目为个人自托管场景的非官方前端，与 LX Music 官方无关；音乐版权归各平台与权利方所有，请仅用于个人学习与家庭共享，并遵守所在地法律法规。
- 音频由浏览器直连各平台 CDN 播放，不经过你的服务器中转。

## License

MIT
