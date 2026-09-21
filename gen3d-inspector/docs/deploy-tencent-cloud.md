# Gen3D Inspector — 迁出 ChatGPT Sites 部署手册

> 目标：让中国大陆用户**无需登录**、不带 ChatGPT 标识的独立域名直接访问。
> 备案本身的实操细节见 [`icp-filing.md`](./icp-filing.md)，本文聚焦部署。

---

## 1. 现状核实结果

以下内容均已实测确认，不是推测。

| 项目 | 结果 |
| --- | --- |
| 本地源码 HEAD | `2c1b63d` "Add static export and Tencent Cloud deployment tooling"（在 Sites 第 5 版 `33d2d8b` 之上新增部署工具链） |
| 作品集仓库 `main` HEAD | `b76fb2c`（已用 `git ls-remote` 核实） |
| 线上地址 | `https://gen3d-inspector.zoeyking0675.chatgpt.site` 返回 **200** |
| 是否需要登录 | **不需要**。匿名请求即拿到完整页面（49 KB HTML），无登录墙、无 `sign in` 字样 |
| 页面品牌元素 | 标题 `Gen3D Inspector`；页面内容中 **0 处** ChatGPT / OpenAI 字样 |
| 境外资源依赖 | **无**。页面只引用自身资源与 SVG 命名空间，没有 Google Fonts、没有第三方 CDN |
| 字体 | 构建期已自托管到 `/_next/static/_vinext_fonts/`（Geist / Geist Mono，woff2） |
| 旧域名硬编码位置 | 仅 og:image 与 twitter:image 两处绝对 URL（`app/layout.tsx` 的 `metadataBase`） |
| 服务端数据依赖 | 无。`.openai/hosting.json` 中 `d1` 与 `r2` 均为 `null` |
| 静态包产出 | `dist-static/` 实测 **26 个文件 / 4.95 MB**，冒烟测试 **7/7 通过** |
| GitHub 推送凭据 | **已存在且可用**。Windows 凭据管理器中有 `git:https://github.com`（用户 `zoeyking-zz`），系统级 `credential.helper=manager`；已用 `git push --dry-run` 验证通过 → **同步不再需要你提供 PAT** |

**结论：站点本身完全适合大陆部署。** 唯一没有境外依赖这一点非常关键——既没有 Google Fonts 也没有外部 CDN，静态化之后大陆访问不需要任何境外回源。

### 1.1 一个必须说明的技术前提

当前默认构建产物**不是静态站**，而是 Cloudflare Worker（项目用 `vinext` + RSC，`vite.config.ts` 里挂了 `@cloudflare/vite-plugin` 和 OpenAI Sites 插件）。所以不能直接把 `dist/` 丢进 COS。

已实测打通静态化路径：`output: 'export'` 下 `vinext build` 会把每个路由预渲染成 HTML，构建日志显示路由 `/` 标记为 **Static**，并产出 `dist/client/index.html`。为此新增了：

- `next.config.ts` — 由 `GEN3D_STATIC_EXPORT=1` 触发的静态导出开关（默认路径**完全不变**，Sites 构建不受影响）
- `scripts/build-static.mjs` — 一键构建 + 打包成 `dist-static/`（剥离 `_headers` / `.assetsignore` 等 Workers 专用文件）
- `scripts/deploy-cos.mjs` — 上传到 COS，按路径设置 Content-Type 与 Cache-Control
- `scripts/verify-static.mjs` — 本地静态服务冒烟测试
- `app/layout.tsx` — `metadataBase` 改为可由 `NEXT_PUBLIC_SITE_URL` 覆盖

---

## 2. 两条路线

|  | 路线 A：中国香港节点（过渡） | 路线 B：中国大陆节点（正式） |
| --- | --- | --- |
| ICP 备案 | **不需要** | **必须**（域名 + 大陆 CDN 加速域名都要） |
| 备案前置 | 无 | 需要有符合条件的**腾讯云大陆云资源**（见 §3.1） |
| 大陆访问质量 | 不保证，跨境外网波动，晚高峰可能差 | 好，走大陆 CDN 节点 |
| 上线时间 | **拿到账号当天可上线** | 备案下号通常 2–4 周 |
| 成本 | 域名 ¥30–80/年 + COS 存储流量（很小） | 同上 + 备案资质资源（最低配轻量约 ¥88/年） |
| 适合 | 想马上有一个自己的域名可用 | 最终目标 |

**建议：路线 A 立即上，路线 B 并行推进。** 两条路线用的是**同一份 `dist-static/` 产物**，备案下号后只需把域名解析切到大陆 bucket / 大陆 CDN，代码一行都不用改。

---

## 3. 路线 B 的前置条件（重要，容易踩）

### 3.1 COS 本身不能用于备案

腾讯云 ICP 备案要求账号下**存在符合条件的大陆云资源**：大陆节点的 CVM / 轻量应用服务器（包年包月 ≥ 3 个月）、云函数 SCF 资源包、云托管资源包，或他人账号生成的备案授权码。

> **对象存储 COS 不在可直接备案的云资源列表里。** 也就是说「买了 COS + 备案」这个顺序不成立。
> 完整对比与推荐组合见 [`icp-filing.md` §2](./icp-filing.md)。

### 3.2 域名本身的要求

- 域名后缀需在国家批复的可备案后缀列表内
- 域名需**已实名认证**，且实名主体与备案主体一致
- **境外注册商注册的域名不能直接备案**，需先转入境内有资质的服务商（如腾讯云）——如果你的域名在 Cloudflare / Namecheap / GoDaddy 注册，这一步要预留时间

### 3.3 COS 必须绑自定义域名

2024-01-01 之后创建的存储桶，用 COS 默认域名（含静态网站域名）访问**任意类型文件都会强制下载**（返回头带 `x-cos-force-download: true` 和 `Content-Disposition: attachment`）。所以：

- 必须绑定自定义域名才能在浏览器里正常打开网页
- 香港桶绑自定义域名**不需要备案**（服务器不在大陆）
- 大陆桶绑自定义域名则必须已完成备案

### 3.4 HTTPS 证书不用买

腾讯云免费 DV 证书：**90 天有效期、单域名、每账号 50 张、免费**。详细说明见 [`icp-filing.md` §7](./icp-filing.md)。

### 3.5 站点必须放在桶的根目录

`index.html` 里引用的资源是**绝对路径**（`/_next/...`、`/og.png`、`/favicon.svg`），
所以站点只能挂在域名的根路径上：

- ✅ 用**独立存储桶**，`COS_PREFIX` 留空，绑一个根域或子域
- ❌ 不要用 `COS_PREFIX=gen3d` 把站点塞进子目录 —— 除非 CDN 上配了对应的路径重写，
  否则 `/_next/*` 会全部 404

`.env.deploy` 里的 `COS_PREFIX` 默认留空，除非你清楚自己在做什么。

---

## 4. 现在只需要你提供什么

GitHub 推送凭据已经解决（见 §1），所以剩下的门槛只有两个：

### A. 一个域名（唯一的必选项）

1. 是否已有域名？如果没有，建议直接在**腾讯云**注册一个（省掉转入环节）。
2. 想要哪个主机名？例如 `gen3d.example.com`，或主域 `example.com` 根域。

> 如果你**已经有别的已备案域名**，可以直接拿一个子域指过来，**整个备案流程都能省掉**——这是最省事的情况，请优先确认这一点。

### B. 腾讯云账号（做路线 A 就需要，做路线 B 还要多买一个资源）

3. 腾讯云**主账号 UIN**（控制台右上角账号 ID）+ 实名认证状态（个人 / 企业）
4. COS 打算用哪个地域：
   - 过渡：`ap-hongkong`（无需备案，当天可上线）
   - 大陆：`ap-guangzhou` / `ap-shanghai` / `ap-beijing`（需备案）
5. 存储桶名称（形如 `gen3d-inspector-1250000000`），或授权我创建
6. **建议给我一个子账号（CAM）密钥而不是主账号密钥**，最小权限：
   - COS：`PutObject` / `GetObject` / `DeleteObject` / `ListBucket`（限定该 bucket）
   - CDN：域名配置权限（若走 CDN 加速）
   - SSL 证书：申请/绑定权限（若需要我代申请免费证书）

> 如果你更愿意自己操作，也可以只给控制台权限：我把每一步命令和操作说明准备到位，你复制执行，我负责验证。

### C. 拍板

7. 先跑**香港过渡**（当天可上线），还是直接等备案？
8. Sites 旧地址确认**保留**作为备用？
9. 新域名上线后，是否需要把 Sites 版本也一并重新发布保持一致？

---

## 5. 一键部署命令

凭据与域名统一放在**一个 git-ignored 文件**里，之后部署就是一条命令。

### 5.1 一次性配置

```powershell
Copy-Item .env.deploy.example .env.deploy
# 然后编辑 .env.deploy，填 4 个必填项：
#   NEXT_PUBLIC_SITE_URL=https://gen3d.example.com
#   COS_SECRET_ID=...
#   COS_SECRET_KEY=...
#   COS_BUCKET=gen3d-inspector-1250000000
#   COS_REGION=ap-hongkong
```

### 5.2 之后每次部署

```powershell
npm run deploy:cos                  # 构建 + 上传（读 .env.deploy）
npm run deploy:cos -- --website --cors   # 首次：顺带配静态网站托管与 CORS
node scripts/deploy-cos.mjs --dry-run    # 只想看会上传什么
npm run verify:static               # 本地起服务冒烟测试 dist-static/
```

也可以不用配置文件，直接在命令行指定域名：

```powershell
node scripts/build-static.mjs --site-url=https://gen3d.example.com
```

> 域名只影响 `og:image` / `twitter:image` 的绝对 URL，改域名不需要改代码。

---

## 6. 拿到信息后我会执行的动作

1. 构建静态包：`npm run build:static`（产出 `dist-static/`，实测 26 文件 / 4.95 MB）
2. 上传：`npm run deploy:cos`（自动设置 Content-Type 与缓存策略）
3. 配置存储桶：静态网站托管（索引文档 `index.html`）、CORS（GET/HEAD）
4. 绑定自定义域名（+ CDN 加速域名，如需）
5. DNS：在域名解析里加 CNAME 指向 COS / CDN 提供的目标
6. HTTPS：绑定证书，开启强制跳转
7. 缓存规则：
   - `/_next/static/**` → 一年、immutable（文件名带内容哈希，可放心长缓存）
   - `.woff2` → 一年
   - `index.html` → **no-cache**（否则新版本会一直发旧页面）
8. 全量回归验证（见 §7）
9. 同步作品集源码到 GitHub（凭据已就绪，可直接推）

---

## 7. 迁移后验证清单

- [ ] 首页在**未登录**的浏览器（无痕窗口）正常打开
- [ ] 控制台 Network 面板**无境外请求**、无 404
- [ ] 模型导入：GLB / glTF、FBX、OBJ+MTL、PLY、STL 各测一个
- [ ] Graphdeco 3DGS PLY 正常渲染（不黑屏、主体尺寸正常、不是一堆离群点）
- [ ] 四套灯光预设切换：中性棚拍 / 暖色夕阳 / 冷色天光 / 霓虹梦幻
- [ ] 自动环绕默认开启，暂停与恢复可用
- [ ] 结构统计、问题检查、JSON 报告导出
- [ ] 移动端布局（至少一台真机或 DevTools 设备模拟）
- [ ] HTTPS 证书有效、HTTP 自动跳 HTTPS
- [ ] `og:image` 指向新域名（用社交平台调试工具或查看 HTML 源码确认）
- [ ] `https://新域名/og.png` 可访问
- [ ] 对比加载性能：大陆直连首屏时间（可用第三方测速节点测）

---

## 8. 回滚

- 迁移期间**不动** Sites 项目，旧地址始终在线，可随时回退
- 新域名若出问题，DNS 改回或暂停 CDN 加速即可，源码与 Sites 构建路径不受影响
- `output: 'export'` 只在 `GEN3D_STATIC_EXPORT=1` 时生效，不影响 Sites 发布

---

## 9. 已知坑（已规避）

1. **本机构建会死锁**：这台机器设了 `HTTP_PROXY=http://127.0.0.1:64688` 且 `NO_PROXY` 为空。静态导出需要预渲染，预渲染会启动本机临时服务器并回连 `127.0.0.1`，该请求被塞进代理后**无限挂起**（实测卡住 6 分钟、CPU 仅 3.7 秒）。
   → 已在 `scripts/build-static.mjs` 中为子进程固定 `NO_PROXY=127.0.0.1,localhost,::1`。手动跑命令时也要注意这一点。

2. **COS 默认域名强制下载**：见 §3.3，必须绑自定义域名。

3. **index.html 缓存**：COS 没有 Workers 那样的 `_headers` 文件，响应头只能在上传时按对象设置 → 已在 `scripts/deploy-cos.mjs` 里按路径分别设置。

4. **字体不需要额外处理**：已在构建期自托管，无需改成国内字体源。

5. **`找工作/.git` 是一个空仓库**（`git init` 过但没有任何提交、也没有远程）。它跟本项目无关，容易误以为源码在这里；真正使用 Git 的目录是 `找工作/gen3d_viewer`（远程是 Sites 的 git）。
