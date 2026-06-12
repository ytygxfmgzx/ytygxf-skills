# bid-assets-maker — 投标素材发动机

只要给它招标文件，你想要的页码数量，它就给你输出包含图文形式的投标素材的 docx 文档，你就可以直接复制粘贴了，再也不需要到处去找材料来复制粘贴，还要担心重复了。

## 功能特性

- **自动解析招标文件** — 将 DOCX 招标文件转换为结构化 Markdown，按章节拆分
- **智能评分解析** — 自动提取技术评分项，按分值比例分配页数和字数
- **图文并茂生成** — 自动生成流程图、柱状图、饼图等配图，每个末级标题至少 1 张图
- **串行章节制作** — 逐章节独立 subagent 生成，避免上下文溢出
- **标书格式规范** — 符合中国标书标准（仿宋正文、黑体标题、A4 页面、固定行距）
- **一键打包 DOCX** — 最终输出可直接使用的投标素材文档

## 环境依赖

### 前置依赖（必须手动安装）

| 依赖 | 最低版本 | 安装方式 |
|------|---------|---------|
| **Python** | 3.10+ | [python.org/downloads](https://www.python.org/downloads/) |
| **Node.js** | 18+（含 npm） | [nodejs.org](https://nodejs.org/)（推荐 LTS） |
| **pnpm** | — | `npm install -g pnpm`（若缺失会自动安装） |
| **pandoc** | — | [清华镜像下载](https://mirrors.tuna.tsinghua.edu.cn/github-release/jgm/pandoc) |

### 可选依赖（自动安装）

以下依赖通过一键安装脚本自动完成，无需手动操作：

| 依赖 | 用途 | 安装源 |
|------|------|--------|
| **docx**（npm 包） | DOCX 文档生成 | npmmirror 国内镜像 |
| **Puppeteer** | HTML 截图生成图片 | npmmirror 国内镜像 + Chromium |
| **defusedxml** | XML 安全解析 | 清华 PyPI 镜像 |
| **lxml** | XML 高性能处理 | 清华 PyPI 镜像 |
| **Pillow** | 图片裁剪处理 | 清华 PyPI 镜像 |

## 安装流程

### 1. 安装前置依赖

确保以下命令均可正常运行：

```bash
python --version    # Python 3.10+
node --version      # Node.js 18+
pnpm --version      # 若无，会自动安装
pandoc --version    # pandoc
```

如果有缺失项，按上方表格的链接安装。

### 2. 安装 Skill

将 `bid-assets-maker` 目录复制或软链接到 Claude Code/opencode等agent工具 的 skill 目录：

```bash
# 方式一：复制
cp -r bid-assets-maker ~/.claude/skills/

# 方式二：软链接（推荐，方便更新）
ln -s "$(pwd)/bid-assets-maker" ~/.claude/skills/bid-assets-maker
```

### 3. 运行一键安装脚本

启动 Claude Code/opencode等agent工具 后，在对话中触发 skill（说出"标书"、"投标"等关键词），skill 会自动执行前置检查。

也可以手动运行依赖安装脚本：

```bash
python bid-assets-maker/scripts/setup_deps.py
```

脚本会自动检测并安装所有可选依赖（docx、Puppeteer、Python 包），全程使用国内镜像源。

## 使用方式

### 触发方式

在 Claude Code/opencode等agent工具 对话中，使用以下关键词触发 skill：

> 标书、投标、招标文件、投标文件、技术方案、商务标、bid、tender、标书制作

### 使用流程

1. **提供招标文件** — 将 `.docx` 格式的招标文件放入对话或指定路径
2. **告知页数要求** — 说明技术部分投标文件要求的总页数
3. **自动解析规划** — skill 自动解析评分办法，生成章节框架和页数分配方案
4. **确认方案** — 查看并确认生成的 `plan.md`，可提出修改意见
5. **自动生成内容** — 确认后逐章节生成图文并茂的投标素材
6. **获取 DOCX** — 最终打包为可直接使用的 `.docx` 文件

### 输出结构

```
output/
├── rfq-docs/              # 解析后的招标文件（Markdown + 图片）
│   ├── index.md           # 章节索引
│   ├── 采购需求.md
│   ├── 评标办法.md
│   └── media/
├── plan.md                # 投标文件编制计划
└── bid-docs/              # 生成的投标素材
    ├── 章节1-项目管理方案/
    │   ├── 流程控制.md
    │   ├── assets/
    │   │   ├── flow_01.html
    │   │   └── flow_01.png
    │   └── 章节1-complete.md
    ├── 章节2-服务接管方案/
    └── ...
```

### 页数计算规则

- **1 页 = 700 字**（不含标题）
- 标题占行：一级标题 ≈ 2 行，二级 ≈ 1.5 行，三级 ≈ 1 行
- 图片/表格：每张 ≈ 1/4 页
- 章节字数按评分分值比例自动分配

## 目录结构

```
bid-assets-maker/
├── SKILL.md                           # Skill 定义文件（Claude Code 使用）
├── README.md                          # 本文档
├── scripts/                           # 核心脚本
│   ├── convert_docx_to_md.py          # DOCX → Markdown 转换
│   ├── split_by_chapter.py            # 按章节拆分 Markdown
│   ├── html_to_img.py                 # HTML 生成图表 + 截图
│   ├── md_to_docx.py                  # Markdown → DOCX 打包
│   └── setup_deps.py                  # 依赖一键安装脚本
├── assets/                            # 资源文件
│   └── deps/
│       └── scripts/
│           ├── pack_docx_std.py       # 纯 Python DOCX 打包（零依赖后备方案）
│           └── unpack_docx_std.py     # 纯 Python DOCX 解包（零依赖后备方案）
└── references/                        # 参考文档
    ├── bid-template-references.md     # 中国标书格式规范
    └── scoring-criteria-parsing.md    # 评分办法解析指南
```

## 工作流程

```
招标文件.docx
    │
    ▼  阶段1: DOCX → MD 转换
output/rfq-docs/ (Markdown + 图片)
    │
    ▼  阶段2: 解析评分 + 生成规划
output/plan.md (章节框架 + 页数分配)
    │
    ▼  阶段3: 用户确认
确认/修改 plan.md
    │
    ▼  阶段4: 逐章节串行制作
output/bid-docs/ (Markdown + 图表 + 图片)
    │
    ▼  阶段5: 打包为 DOCX
投标文件.docx ✅
```

## 标书格式规范

输出文档严格遵循中国标书标准：

| 项目 | 规格 |
|------|------|
| 页面 | A4（210mm × 297mm） |
| 正文字体 | 仿宋_GB2312 / 仿宋，四号（14pt） |
| 标题字体 | 黑体，一级三号（16pt），二级小三（15pt） |
| 行距 | 固定值 28 磅 |
| 页边距 | 上下 2.54cm，左右 3.17cm |

## 许可

本项目基于 [MIT 许可证](./LICENSE) 开源。

## 赞赏支持

如果这个项目对你有帮助，欢迎请作者喝杯咖啡 ☕

<div align="center">
  <img src="../assets/appreciation_qrcode.png" width="200" alt="赞赏码" />
</div>
