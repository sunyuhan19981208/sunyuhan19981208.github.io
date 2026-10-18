# y'log

Yuhan Sun 的个人技术博客。使用 **Hugo 0.145.0** 与独立模板，输出纯静态网页，适用于 GitHub 个人主页和项目 Pages。

主页与目录组织参考 [Lil'Log](https://lilianweng.github.io/) / [源码](https://github.com/lilianweng/lilianweng.github.io)，文章页参考 [Dream-RSI](https://dream-rsi.com/) 的研究展示方式；未复制两站的模板代码。视觉采用暖白纸色、陶土色强调与衬线标题，日期、标题、摘要分栏对齐，正文保持独立的阅读宽度。

## 本地预览

Windows PowerShell：

```powershell
cd D:\Code\blog
.\dev.ps1
```

打开 http://localhost:1313/ 。首次运行脚本会在没有 Hugo 时，从官方 release 下载到项目的 `.tools/hugo/`，无需 Node.js、npm、Python 或 Hugo Extended。当前工作目录已准备好 Hugo。

macOS / Linux 安装 Hugo 后运行：

```sh
hugo server --disableFastRender
```

生产构建：

```powershell
.\build.ps1 -BaseURL 'https://你的用户名.github.io/'
```

输出在 `public/`；不要手工修改或提交这个目录。可选验证：`python scripts/check_site.py`（仅 Python 标准库）。域名与 GitHub 链接已配置为 `sunyuhan19981208`。

## 发布到 GitHub 个人主页

1. 使用已有仓库 **[sunyuhan19981208.github.io](https://github.com/sunyuhan19981208/sunyuhan19981208.github.io)**。检查时它的默认分支为 `master`，已有 `index.html`、`audio/`、`scripts/`、`styles/` 等文件。
2. 本项目的 `hugo.toml` 已设置 `baseURL = 'https://sunyuhan19981208.github.io/'` 和个人 GitHub 链接。
3. 在已有仓库的本地 checkout 中加入本项目的 Hugo 源文件。先检查同名 `README.md` 与 `scripts/` 的差异；按需保留旧站资源，不要覆盖仓库的 `.git` 或删除旧历史。将更新提交到 `master`（或自己的 `main` 分支）。
4. 仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。
5. `.github/workflows/pages.yml` 会构建并发布；以后向 `master` 或 `main` 推送就会自动更新。

```powershell
# 在已有主页仓库的 checkout 中，整合本项目文件后运行：
git status
git add .
git commit -m "Build y'log personal technical blog"
git push origin master
```

如果使用普通项目仓库 `blog`，同样支持 `https://用户名.github.io/blog/`。工作流自动使用 GitHub Pages 返回的正确 base URL，CSS、JS、搜索和 RSS 使用对应子路径。自定义域名则在仓库 Pages 设置中配置，并同步修改 `baseURL`。

工作流参考 [Hugo 官方 GitHub Pages 部署文档](https://gohugo.io/host-and-deploy/deploy-to-github-pages/)。本次完成本地项目与部署配置，尚未修改远程仓库或发布线上站点。

## 文件组织

```text
blog/
├── hugo.toml                 # 站名、域名、作者、GitHub 链接
├── content/
│   ├── posts/
│   │   ├── llm-barrage-interaction/
│   │   ├── llm-distillation-and-reasoning-compression/
│   │   ├── livethinking/
│   │   ├── agenticrl/
│   │   ├── harness-aware-training/
│   │   └── harness-aware-training-cn/
│   ├── about.md
│   ├── archives.md
│   ├── search.md
│   └── tags/_index.md
├── layouts/                  # Hugo 模板：主页、文章、归档、搜索、标签
├── static/css/editorial.css  # 全站排版、深浅色、响应式与打印样式
├── static/css/publications.css # 英文论文公式、图注、数据表格样式
├── static/js/main.js         # 搜索、筛选、目录、图片放大、引用复制
├── data/sources.json         # 六篇原文来源、论文版本和导入校验值
├── data/works.json           # 五篇独立文章与十个语言版本的对应关系
├── data/translations.json    # 四份新增译文的来源、覆盖块数与源文校验值
├── scripts/                  # Hugo 启动、内容导入、静态链接校验
├── .github/workflows/        # GitHub Pages 自动构建与发布
├── dev.ps1
└── build.ps1
```

每个语言版本是一个 Hugo leaf bundle：`index.md` 保存元数据和正文，`images/` 保存本地图表。两篇英文论文及 LiveThinking 中文译文另有 `source.html`（保留 TeX / MathML 的编辑源）和 `body.html`（排版后的完整正文）。`source-content` shortcode 插入 `body.html`，保留表格、参考文献及内部交叉引用。其他文章直接使用 Markdown。译文通过相邻路径复用原版图片，避免复制图表。原始抓取 HTML 和本地工具放在 `.tools/`，均不提交。

## 内容与维护

站点默认展示的是博客稿，而非完整论文转载。五篇工作的十个版本均已改写为较短的技术笔记：保留问题、关键方法、必要图表、实验结果与局限，省略论文摘要、相关工作和大段附录。文章开头只保留标题和一句简介，文末链接到原始出版物；BibTeX 默认折叠。

**日常改稿请编辑 `editorial/posts/<slug>.md`**：文件开头的 JSON 保存博客标题和简介，后面是正文。运行 `python scripts/build_editorial.py` 会生成各文章的 `blog.md` 及 `data/editorial.json`，自动更新阅读时长。插图标记引用原版资源，由脚本生成统一图号和图注，不复制或重绘原图。

完整的原始正文、四份完整翻译及论文排版资源仍保存在 `content/posts/` 的 `index.md`、`source.html`、`body.html` 中，便于查证和后续维护。模板、搜索、归档和 RSS 都以博客稿为准，不再把全文论文作为默认阅读页。

- 六个原始出版来源整合为 **五篇文章、十个中英文版本**。Harness 中文实践文章与英文技术报告归为同一篇工作的两个版本，其余四篇分别补齐缺少的语言。
- 首页、归档、标签、RSS 每篇工作只出现一次；文章页与列表提供中文 / English 链接，搜索覆盖全部十份正文。旧的 Harness 中文链接继续可用。
- 英文补充版本包括弹幕互动、模型蒸馏与路径压缩、AgenticRL；中文补充版本为 LiveThinking。完整翻译留作源稿，展示时使用逐篇编写的双语博客稿。
- 论文导入版本：LiveThinking **v1**；Harness-Aware Training **v5（2026-10-04）**。中文解读保持微信公众号原文，不强行同步为英文新版措辞。
- 文章标题、简介和目录以博客稿为准；详细论证和完整参考文献可通过文末原文链接查阅。
- 图片已本地化，不依赖微信防盗链；英文公式预先排为自包含的 SVG，行内公式保持基线，独立长公式分行对齐；读者浏览时无需数学脚本或第三方 CDN。
- 博客正文统一省略机构标识、重复的团队宣传介绍及公众号的跨栏目推荐；保留技术图表、论文署名、参考文献与原文出处。清理规则随导入和排版脚本执行，重新生成时不会恢复宣传模块。
- 全文搜索索引构建时生成，浏览器本地搜索，不向第三方发送搜索词。
- 深浅色主题保存在本地；长表格可以横向滚动；图表可点击放大；英文论文提供可复制 BibTeX。
- 无需 Hugo 外部主题、Git 子模块或 Node 构建依赖。
- 新增文章：复制一个现有 `content/posts/<slug>/`，修改 JSON front matter 中的 `title`、`date`、`description`、`source`、`tags`、`publicationType`、`language`、`lead`、`highlights`、`flow` 和正文。

`scripts/import_sources.py` 用于重新导入，需 Python 及 `beautifulsoup4`、`markdownify`、`requests`。它会覆盖已导入正文，手工编辑后不要直接重跑。初次构建不需要运行导入脚本，正文和图片已经包含在仓库中。

修改或重新导入英文论文后，运行 `scripts/typeset_publications.py`。仅此编辑步骤需要 Python（`beautifulsoup4`、`Pillow`）、Node.js 和本地 MathJax；普通预览、生产构建和 GitHub Actions 均直接使用已生成的正文，不需要这些依赖。

```powershell
# 首次准备排版依赖；保存在被 Git 忽略的 .tools/ 目录
python -m pip install beautifulsoup4 Pillow
npm install --prefix .tools/math-authoring --ignore-scripts mathjax-full@3.2.2
# 修改 source.html 后重新生成论文原版及中文译文的 body.html
python scripts/typeset_publications.py
```

长公式的人工分行位于 `scripts/typeset_publications.py` 的 `TEX_LAYOUTS` 中。脚本使用 MathJax 严格解析全部公式，并检查原有交叉引用锚点是否完整；更新后应一并提交 `source.html`、`body.html` 和新增图片。图号、图注和数据来自原论文，排版不改写数学定义或实验结果。

### 双语内容维护

`workId` 标识同一篇工作，`counterpart` 指向另一个语言版本，`secondaryVersion` 控制是否作为独立列表条目。`data/works.json` 记录五组对应关系；原有 URL 均保留。每个页面有自己的 canonical，并以 `hreflang` 关联语言版本。

四份完整源稿译文的逐段翻译保存在 `scripts/translations/*.json`。`scripts/translation_segments.py` 提取段落并保护公式、图片、交叉引用；`scripts/build_bilingual.py` 检查覆盖和占位符，然后生成源稿及版本元数据，不覆盖 `editorial/posts/` 的博客稿。普通构建不需要运行这些脚本。修改原文后需同步审校对应翻译和博客稿：

```powershell
python scripts/translation_segments.py
# 根据 .preview/*-segments.json 更新 scripts/translations/ 下的对应译文
python scripts/build_bilingual.py
python scripts/typeset_publications.py
```

Harness 的中文实践解读与英文 v5 报告来自不同的出版版本，原有章节与数值按各自来源保留，并在页面注明版本关系。

## 来源与权属

全部内容来自作者提供的六个公开出版链接，见 [data/sources.json](data/sources.json)；文章、图表与论文权利归原作者及原出版方所有，保留原有署名和引用。模板、样式与脚本是本项目新编写的代码。更新来源时请核对论文版本与对应中文解读。
