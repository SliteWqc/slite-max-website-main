# SLITE Product Showcase

这是一个适合长期维护的静态多页面产品站。源码和部署产物已经分开：你平时只需要修改内容源文件，构建后的可发布站点统一输出到 `dist/`。

## 目录说明

- `assets/`: 站点共享静态资源，例如图片、CSS、前端脚本
- `content/products.json`: 产品内容、下载链接、首页卡片配置
- `templates/`: 首页和产品详情页模板
- `scripts/build.py`: 静态站生成脚本
- `public/`: 直接复制到最终站点根目录的文件
- `public/downloads/`: 后续放安装包、压缩包、说明附件的推荐位置
- `dist/`: 构建产物目录，部署平台发布这个目录
- `Product’s Picture/`: 原始设计素材，仅作为源素材保留，不参与部署

## 本地预览方法

在项目根目录运行：

```bash
python3 scripts/build.py
python3 -m http.server 4173 --directory dist
```

然后打开：

`http://127.0.0.1:4173`

如果你只改了内容或模板，重新运行一次 `python3 scripts/build.py`，再刷新浏览器即可。

## 内容更新方法

最常改的地方：

- 改产品文案、简介、下载链接：`content/products.json`
- 改页面结构：`templates/index.html.tmpl`、`templates/product.html.tmpl`
- 改样式和动效：`assets/styles/site.css`、`assets/scripts/site.js`
- 放下载文件：`public/downloads/`

每次更新后执行：

```bash
python3 scripts/build.py
```

构建完成后，最终可发布文件都会出现在 `dist/`。

## Git 提交流程

如果这是第一次初始化 Git：

```bash
git init
git branch -M main
git add .
git commit -m "Initial static site setup"
```

以后每次更新网站，最简单的流程就是：

```bash
python3 scripts/build.py
git add .
git commit -m "Update site content"
git push
```

说明：

- `dist/` 已经写进 `.gitignore`，不会被提交到 GitHub
- 你提交的是源码、模板、内容和配置文件
- GitHub 上的托管平台会自动执行构建命令，再发布 `dist/`

## Cloudflare Pages 自动发布

推荐优先使用 Cloudflare Pages。

### 连接 GitHub

1. 把项目推到 GitHub 仓库
2. 登录 Cloudflare Dashboard
3. 进入 `Workers & Pages` -> `Create` -> `Pages` -> `Connect to Git`
4. 选择你的 GitHub 仓库

### Cloudflare Pages 配置

- Framework preset: `None`
- Build command: `python3 scripts/build.py`
- Build output directory: `dist`
- Root directory: 留空，或者填写仓库根目录

项目里也已经提供了 `wrangler.toml`，其中包含：

- `pages_build_output_dir = "./dist"`

这能帮助你后续用 Cloudflare 相关工具时保持配置一致。

## Netlify 自动发布

如果你以后不用 Cloudflare，也可以直接接 Netlify。

### 连接 GitHub

1. 登录 Netlify
2. 选择 `Add new project` -> `Import an existing project`
3. 连接 GitHub 并选择仓库

### Netlify 配置

项目根目录已经提供了 `netlify.toml`，主要配置是：

- Build command: `python3 scripts/build.py`
- Publish directory: `dist`

如果在 Netlify 后台手动填写，也填这两个值即可。

## 以后更新网站的最简单步骤

日常只要记住这 4 步：

1. 改内容或下载链接
2. 本地执行 `python3 scripts/build.py`
3. 浏览器预览确认
4. `git add .` -> `git commit` -> `git push`

推送完成后：

- Cloudflare Pages 会自动重新构建并上线
- Netlify 也会自动重新构建并上线

## 特别说明

当前项目路径名里包含特殊字符：`Slite‘max Website Main` 中的 `‘` 不是普通英文单引号。

这不会直接阻止 Git 或静态托管，但它在下面这些场景里可能带来麻烦：

- 终端命令复制时容易转义出错
- 某些脚本、CI 配置或第三方工具对特殊字符路径兼容性一般
- 新手后续在命令行里操作会更不顺手

建议你后续在一个合适的时机，把目录名改成纯 ASCII，例如：

- `slite-max-website-main`
- `Slite-max-Website-Main`

这不是必须马上做的事，所以我这次没有擅自移动目录。
