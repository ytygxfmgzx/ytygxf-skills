---
name: bid-assets-maker
description: "帮助投标人员快速理解招标文件（DOCX格式），制作标书框架和草稿。适用场景：用户提供招标文件(.docx)和页数要求，需要：1) 转换DOCX为可阅读的Markdown；2) 解析评分办法，构建目录框架；3) 生成标书编制计划；4) 逐章节制作标书内容（图文结合）；5) 打包为DOCX。触发词包括：'标书'、'投标'、'招标文件'、'投标文件'、'技术方案'、'商务标'、'bid'、'tender'、'标书制作'。用户提到docx文件要做标书时请务必使用此技能。"
---

# 投标文件制作助手 (bid-assets-maker)

## 概述

帮助投标人员快速理解招标文件（DOCX 格式），制作标书框架和草稿。核心流程：

1. **DOCX → MD 转换** — 将招标文件转换为 Markdown
2. **解析评分 + 生成规划** — subagent 解析评分办法并生成 `plan.md`（防止上下文溢出）
3. **用户确认** — 调整 plan.md 直到用户确认
4. **制作标书** — 逐章节串行制作（每章节独立 subagent）
5. **打包 DOCX** — 合并输出为 .docx

---

## 前置环境检查（必须通过才能继续）

Skill 启动时，**必须**先运行以下检查。任何一项不通过则 **停止执行**，提示用户安装后再来。

### 检查清单

```
1. Python 检查: `python --version`
   → 需要 Python 3.10+
   → 无/版本过低: 提示 "请安装 Python 3.12: https://www.python.org/downloads/"，停止

2. Node.js 检查: `node --version`
   → 需要 Node.js 18+
   → 无: 提示 "请安装 Node.js LTS: https://nodejs.org/"，停止
   → 有: 检查 npm → `npm --version`
     → 无: 提示 "npm 通常随 Node.js 一起安装，请重新安装 Node.js"，停止
     → 有: 检查 pnpm → `pnpm --version`
       → 无: 自动安装 `npm install -g pnpm`，继续
       → 有: 继续

3. pandoc 检查: `pandoc --version`
   → 无: 提示 "请安装 pandoc: https://mirrors.tuna.tsinghua.edu.cn/github-release/jgm/pandoc"，停止
```

### 通过检查后

运行一键安装脚本自动安装可选依赖（docx npm 包、Puppeteer、Python libs）：

```bash
python scripts/setup_deps.py
```

### 未通过检查时

停止执行，向用户输出清晰的安装指引：
- 列出所有缺失项及安装链接
- 告知 "安装完成后重新启动 skill 即可"

> **注意**: 本项目统一使用 `pnpm` 管理 Node.js 包。

---

## 页数定义

- **1 页 = 700 字（不含标题）**
- 标题占行：一级标题 ≈ 2 行，二级 ≈ 1.5 行，三级 ≈ 1 行
- 图片/表格占位：每张图/表 ≈ 1/4 页版面
- 每章节可分配字数 = (该章节分值 ÷ 技术部分总分) × (总页数 × 700 - 标题占行 - 图表占版)

---

## 工作流程

### 阶段 1: 转换招标文件为 MD

**输入**: 招标文件.docx
**输出**: `output/rfq-docs/` 目录

**步骤（严格按顺序执行）**：

1. 确认 pandoc 已就绪（前置检查已通过）
2. 转换 DOCX → 完整 MD:
   ```bash
   # extract-media 指向 rfq-docs 目录本身（不含 media 子路径），pandoc 会自动创建 media/ 目录
   pandoc --extract-media=output/rfq-docs 招标文件.docx -o output/rfq-docs/output.md --wrap=none
   ```
3. **必须**调用 `split_by_chapter.py` 按标题拆分章节：
   ```bash
   python scripts/split_by_chapter.py output/rfq-docs/output.md output/rfq-docs/
   ```
   这会自动生成 `index.md` 和多个章节文件。
4. 删除过渡用的 `output.md`
5. 确认 `output/rfq-docs/` 下包含 `index.md` 和各个章节的 `.md` 文件

**图片/表格处理**：
- pandoc 会自动提取图片到 `output/rfq-docs/media/`（含子目录）
- 表格在 MD 中以 Markdown 表格或 pandoc 的 grid 表格呈现
- 图片引用路径为 `media/xxx.png`

**输出结构**：
```
output/rfq-docs/
├── index.md          # index（章节名 → 文件名映射，必须）
├── 采购需求.md       # 按一级标题拆分的章节文件
├── 评标办法.md
├── ...
└── media/            # pandoc 提取的图片（可能含子目录）
```

---

### 阶段 2: 解析评分办法 + 生成标书规划（subagent）

> **⚠️ 必须使用 Agent 工具启动独立 subagent 完成此阶段。禁止主 agent 自己读取 rfq-docs 章节文件，防止上下文溢出。**

招标文件通常数百页，rfq-docs 拆分后仍有大量文本。如果主 agent 直接读取，上下文会迅速耗尽。因此阶段 2 必须委托给 subagent 执行。

#### 主 agent 执行步骤


1. [主agent] 读取 output/rfq-docs/index.md（仅索引文件，很轻量）
2. [主agent] 询问用户：技术部分投标文件要求总页数是多少？
3. [主agent] 调用 Agent 工具启动 subagent，传递以下 prompt：


**Subagent Prompt 模板**

```
你是标书评审专家。请完成以下两项任务：

## 任务 1：解析评分办法

读取 output/rfq-docs/ 目录下的所有章节文件，搜索评分相关内容。

搜索关键字：
"评标办法"、"评分项"、"评分标准"、"评标方法"、"评审细则"、
"评标办法前附表"、"评分表"、"评审因素"

对每个技术评分项提取：
- 评分项名称（如"服务方案"）
- 细项名称（如"项目管理方案"）
- 分值
- 评审细则原文
- 评审要素拆解

注意：只关注技术部分，忽略商务部分（报价、资质、业绩、财务）。

## 任务 2：生成标书规划

基于解析出的评分项，结合以下要求生成 output/plan.md：

- 要求总页数: {用户提供的页数} 页
- 页数定义: 1页 = 700字（不含标题），标题/图表另计
- 按分值比例分配页数和字数

plan.md 必须包含以下结构：

# 投标文件编制计划

## 项目信息
- 招标文件：{文件名}
- 要求总页数：{页数} 页
- 技术部分总分：{总分} 分

## 目录框架与页数分配
| 章节 | 分值 | 分配页数 | 分配字数 | 内容摘要 |
|------|------|---------|---------|---------|

**要求**：章节的名称要求来自技术评分项中提到的词语或短语

## 各章节与招标文件响应关系
（每个章节列出：对应的评分项、招标要求原文、投标要点）

## 计划进展
| 章节 | 状态 | 负责人 | 完成日期 | 备注 |
|------|------|--------|---------|------|
（所有章节初始状态为 ⏳ 待开始）

## 评审细则原文（供 Stage 5 参考）
（每个评分项的完整评审细则原文，用于后续章节制作时引用）
```

#### Subagent 完成后

```
4. [主agent] 确认 output/plan.md 已生成，用 Read 工具读取并展示给用户
5. 进入阶段 3（用户确认）
```

#### 评分项解析示例

```markdown
## 技术评分项: 服务方案 (总分 24 分)
- 项目管理方案 (4分): 需包含流程控制、计划管理、岗位标准化、质量管控...
- 服务接管方案 (4分): 需包含整体流程、时间安排、组织架构与职责...
```

---

### 阶段 3: 用户确认（关键步骤，禁止跳过）

**这是整个流程中最关键的节点，必须严格遵守以下规则：**

1. **plan.md 生成后，必须立即停止**，向用户完整展示 plan.md 内容
2. **等待用户主动反馈**：
   - 用户可能提出修改意见
   - 用户可能补充要求或信息
   - 用户可能对分配方案有疑问
3. **如果用户提出问题或建议**：
   - 逐一解答用户的疑问
   - 评估用户建议的合理性和可行性
   - 根据合理建议调整 plan.md 内容
   - 更新后再次向用户展示修改后的 plan.md
4. **重复步骤 2-3**，直到用户**明确说出以下形式的确认词**：
   - "确认" / "可以" / "没问题" / "开始" / "就这样" / "✅"
   - 或者用户明确表示"可以开始了"
5. **只有用户明确确认后**，才能进入阶段 4（制作标书内容）
6. **任何时候用户还未确认，禁止主动进入阶段 4**

---

### 阶段 4: 制作标书内容（串行执行）

**输入**: `output/plan.md` + `output/rfq-docs/`
**输出**: `output/bid-docs/` 目录

**⚠️ 核心规则（必须严格遵守）**:

> **每个章节必须使用 Agent 工具启动独立 subagent 制作。禁止主 agent 自己直接编写章节内容。**

#### 执行步骤（严格按顺序）

> **主 agent 在此阶段只读 plan.md（轻量），禁止读取 rfq-docs 章节文件。所有文件读取由 subagent 完成。**

```
1. [主agent] 读取 output/plan.md，提取「目录框架与页数分配」表格中的所有章节行
   （仅提取表格数据，不读取 plan.md 中的「评审细则原文」等大段内容）
2. 对每个章节，按表格顺序执行以下循环：

   FOR EACH 章节 IN 章节列表:

     a. [主agent] 用 Edit 工具更新 plan.md：该章节状态 → 🔄 进行中

     b. [主agent] 仅从 plan.md 表格中提取该章节的：
        - 章节名称
        - 分配页数 / 分配字数
        - 内容摘要
        （禁止读取 rfq-docs，禁止读取评审细则原文）

     c. [主agent] 调用 Agent 工具，传递以下 prompt：

        ┌──────────────────────────────────────────────────┐
        │ Subagent Prompt 模板（主agent必须按此格式传递）    │
        │                                                  │
        │ 你是标书制作专家。请制作以下章节的投标文件内容。   │
        │                                                  │
        │ ## 章节信息                                      │
        │ - 章节名称: {从plan.md表格提取}                   │
        │ - 分配字数: {字数}字                              │
        │ - 内容摘要: {内容摘要}                            │
        │                                                  │
        │ ## 上下文准备（你必须自己完成，不要向主agent请求） │
        │ 请依次执行以下读取操作：                           │
        │ 1. Read output/rfq-docs/index.md — 找到与「{章节 │
        │    名称}」相关的源文件                            │
        │ 2. Read 对应的 rfq-docs 章节文件 — 提取该章节     │
        │    的评审细则原文和采购需求                        │
        │ 3. Read output/plan.md 的「各章节与招标文件响应   │
        │    关系」和「评审细则原文」部分 — 获取该章节的    │
        │    招标要求和投标要点                              │
        │ 以上是你的核心参考资料，必须全部阅读后再开始写作。 │
        │                                                  │
        │ ## 任务                                          │
        │ 1. 创建目录: output/bid-docs/{章节目录}/          │
        │ 2. 为每个末级标题创建独立 .md 文件                 │
        │    （内容必须详实具体，禁止只列提纲）               │
        │ 3. 标题格式与层级映射：                               │
        │    - 标题使用纯文字，不加序号                      │
        │    - ⚠️ 章节内只有第一个标题用 #（即章节名称），   │
        │      其余所有标题从 ## 开始                       │
        │    - 标题会经 --heading-offset 1 偏移后合成到 DOCX：│
        │      | 你写的 MD | DOCX 实际层级 | 用途            │
        │      |-----------|---------------|-----------------│
        │      | # 章节名称 | H2            | 章节标题（仅一个）│
        │      | ## 分类    | H3            | 章节内大分类    │
        │      | ### 内容   | H4            | 分类下具体内容  │
        │      | #### 细节  | H5            | 一般不使用      │
        │                                                   │
        │    ✗ 禁止: ## 1.1 项目管理方案                    │
        │    ✗ 禁止: 在章节内使用多个 # 标题                │
        │    ✓ 正确: # 章节名称（仅一个），后续用 ##、###... │
        │    ✓ 正确: ## 项目管理方案                         │
        │ 4. 表格要求:可以用表格展示内容的，优先用表格进行内容展示                                     │
        │ 5. 配图要求:                                     │
        │    - 每个末级标题至少 1 张图/表                   │
        │    - 流程类内容必须有流程图                       │
        │    - 使用 python .claude/skills/bid-assets-maker/ │
        │      scripts/html_to_img.py gen 和 shot 命令      │
        │    - 图片保存到当前章节的 assets/ 子目录           │
        │    - 在 md 中用 <img src="assets/xxx.png"> 引用   │
        │    - HTML 源文件必须保留（gen 生成后不可删除）     │
        │    - 每个 assets/ 下必须同时有 .html 和 .png     │
        │    - ⚠️ HTML 资产文件名使用英文或拼音，禁止中文    │
        │    - ⚠️ 自定义 HTML 内容必须设置                   │
        │      max-width:760px 的容器，总宽度不超过 800px   │
        │ 5. 创建 {章节}-complete.md 合并所有小节内容       │
        │ 6. 字数控制在分配字数 ±10% 以内                   │
        │                                                  │
        │ ⚠️ 禁止创建 output/bid-docs/assets/ 主目录       │
        │ 所有资源只保留在各自章节的 assets/ 子目录下       │
        │                                                  │
        │ ## 配图命令参考                                  │
        │ ⚠️ 截图必须且只能使用以下 shot 命令，              │
        │ 禁止直接调用 Chrome 或其他截图工具！              │
        │                                                  │
        │ 生成流程图:                                      │
        │   python .claude/skills/bid-assets-maker/         │
        │     scripts/html_to_img.py gen flow "标题"        │
        │     assets/xxx.html --steps "步骤1" "步骤2"       │
        │                                                  │
        │ 生成柱状图:                                      │
        │   python .claude/skills/bid-assets-maker/         │
        │     scripts/html_to_img.py gen bar "标题"         │
        │     assets/xxx.html --labels "A" "B"              │
        │     --values 10 20                               │
        │                                                  │
        │ 生成饼图:                                        │
        │   python .claude/skills/bid-assets-maker/         │
        │     scripts/html_to_img.py gen pie "标题"         │
        │     assets/xxx.html --labels "A" "B"              │
        │     --values 30 70                               │
        │                                                  │
        │ 截图:                                            │
        │   python .claude/skills/bid-assets-maker/         │
        │     scripts/html_to_img.py shot assets/xxx.html   │
        │     assets/xxx.png                               │
        │                                                  │
        │ ## 自查清单（完成后逐项检查）                     │
        │ - [ ] 标题无序号（禁止"1.1"、"2.3.1"等前缀）      │
        │ - [ ] 标题层级正确：章节内仅一个 #（章节名，      │
        │       最终为 H2），其余从 ## 开始（最终为 H3），    │
        │       一般不超过 ###                                │
        │ - [ ] 每个末级标题至少有 1 张图/表                │
        │ - [ ] 流程类内容都有流程图                        │
        │ - [ ] 内容详实具体，不是提纲                      │
        │ - [ ] 图表无编号（禁止"图1-1"等）                 │
        │ - [ ] 图表无引导词（禁止"以下图表展示了"）        │
        │ - [ ] assets/ 下 .html 和 .png 成对存在           │
        │ - [ ] HTML 文件名均为英文/拼音，无中文字符        │
        │ - [ ] 所有截图通过 html_to_img.py shot 生成       │
        │ - [ ] 没有创建 output/bid-docs/assets/ 主目录     │
        └──────────────────────────────────────────────────┘

     d. [主agent] 等待 subagent 完成

     e. [主agent] 用 Edit 工具更新 plan.md：该章节状态 → ✅ 已完成，填入完成日期

3. 所有章节完成后，进入阶段 5
```

#### 输出结构（严格按此结构）

```
output/bid-docs/
├── 章节1-项目管理方案/
│   ├── 流程控制.md          # 每个末级标题一个独立文件
│   ├── 计划管理.md
│   ├── 岗位标准化.md
│   ├── 质量管控.md
│   ├── 工作衔接方案.md
│   ├── assets/
│   │   ├── flow_01.png      # 截图图片
│   │   ├── flow_01.html     # 对应的 HTML 源文件
│   │   └── chart_01.png
│   └── 章节1-complete.md    # 该章节所有小节合并后的完整文件
├── 章节2-服务接管方案/
│   ├── 整体流程安排.md
│   ├── ...
│   └── 章节2-complete.md
└── ...
```

**⚠️ 禁止**：将所有内容塞入一个 `complete.md` 而不拆分小节。

#### 内容质量要求

1. **针对性**：内容必须扣合招标文件要求，逐条响应评审细则
2. **详实性**：可操作、不空洞、不列提纲；涉及执行层面的内容必须有具体措施
3. **图文结合**：
   - 所有流程必须有流程图
   - 数据用图表呈现（柱状图、饼图、趋势图等）
   - 管理类内容尽量使用架构图、流程图
   - 可以用表格展示内容的，优先用表格进行内容展示

#### 配图规则

- 每个末级标题至少配 1 张图（流程图/架构图/表格等）
- 涉及流程的必须有流程图，不能只用文字描述步骤
- 数据类内容尽量用图表呈现，配合文字说明
- 图表禁止有标题和编号，如"图1-1 XXXX"、"表2-3 XXX"
- 图表禁止使用"以下图表展示了"等引导词

#### 进度更新规则

- 状态值：⏳ 待开始 → 🔄 进行中 → ✅ 已完成 / ❌ 失败
- 每个 subagent 启动前：用 Edit 工具将 plan.md 中该章节状态改为 🔄 进行中
- 每个 subagent 完成后：用 Edit 工具将状态改为 ✅ 已完成，填入完成日期时间（YYYY-MM-DD HH:MM）
- 格式：更新 plan.md 中「计划进展」表格的「状态」和「完成日期」列

#### 错误处理

- subagent 执行失败：重试最多 2 次，仍失败则标记 ❌ 失败，继续下一章节
- 截图失败（Chrome 不可用）：保留 HTML 文件，在 md 中用 `[图：assets/xxx.html]` 占位
- 所有失败记录到 `output/errors.md`

---

### 阶段 5: 打包为 DOCX

**输入**: `output/bid-docs/` 各章节 complete.md + assets
**输出**: `output/招标文件名称-投标文件.docx`

**标题层级映射规则（通过 `--heading-offset 1` + `--title` 自动实现）**：

`md_to_docx.py` 接受多个 MD 文件，每个文件独立解析图片路径。`--title` 插入文档总标题 H1，`--heading-offset 1` 将每个章节的标题自动偏移：

| MD 中的标题 | 加偏移后在 DOCX 中 | 含义 |
|-------------|-------------------|------|
| `# 章节名` | H2 | 章节标题（如"日常值班巡检过程管理"） |
| `## 分类` | H3 | 章节下的分类（如"方案概述"） |
| `### 内容` | H4 | 小节内容（如"方案目标"） |
| `#### 细节` | H5 | 更细内容 |

**方法**：

1. **截图裁剪验证**（在打包前执行）：
   ```bash
   python .claude/skills/bid-assets-maker/scripts/html_to_img.py crop-all output/bid-docs/
   ```
   扫描所有 PNG，自动裁剪高度 == 10800 的未裁剪图片。如果全部已裁剪则无操作。

2. **一次性转换所有章节为 DOCX**：
   按 plan.md 中章节顺序，将所有章节的 `*-complete.md` 一次性传入 `md_to_docx.py`，脚本内部自动按顺序合并，每个章节的图片基于各自文件所在目录独立解析。
   示例
   ```bash
   python scripts/md_to_docx.py \
     -o output/投标文件.docx \
     --title "值班巡检方案" \
     --heading-offset 1 \
     output/bid-docs/值班巡检方案概述/值班巡检方案概述-complete.md \
     output/bid-docs/日常值班巡检过程管理/日常值班巡检过程管理-complete.md \
     output/bid-docs/巡检表单管理/巡检表单管理-complete.md \
     output/bid-docs/问题管理/问题管理-complete.md \
     output/bid-docs/交接班管理/交接班管理-complete.md \
     output/bid-docs/值班巡检保障措施/值班巡检保障措施-complete.md
   ```
   - `--title`：文档总标题，作为 H1 插入（来自 plan.md 中制作章节的父级名称）
   - `--heading-offset 1`：每个章节内的 `# 章节名` 自动变为 H2
   - 无需生成 combined.md，无需修正图片路径

3. **打包后验证**：
   - 检查生成的 DOCX 文件大小是否合理（应明显大于纯文本 DOCX）
   - 打开 DOCX 确认图片已正确嵌入

**中国标书格式规范**：
- 页面：A4（210mm × 297mm）
- 正文字体：仿宋_GB2312 或 仿宋，四号（14pt）或小四（12pt）
- 标题字体：黑体，一级标题三号（16pt），二级标题小三（15pt）
- 行距：固定值 28磅
- 页边距：上下 2.54cm，左右 3.17cm

---

## 参考文档

- `references/bid-template-references.md` — 标书模板参考
- `references/scoring-criteria-parsing.md` — 评分办法解析指南

## 依赖脚本

- `scripts/convert_docx_to_md.py` — DOCX → MD 转换
- `scripts/split_by_chapter.py` — 按章节拆分 MD
- `scripts/html_to_img.py` — HTML → 截图
- `scripts/md_to_docx.py` — MD → DOCX 打包
- `scripts/setup_deps.py` — 可选依赖自动安装（docx npm、Puppeteer、Python libs）
