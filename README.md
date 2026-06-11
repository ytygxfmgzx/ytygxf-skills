# ytygxf-skills

ytygxf 个人制作的 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Skill 合集。

这里收录的都是实际工作中沉淀出来的自动化技能——解决重复劳动、提升文档质量、让 AI 真正融入工作流。

## Skill 列表

| Skill | 简介 | 文档 |
|-------|------|------|
| [bid-assets-maker](./bid-assets-maker/) | 投标素材发动机——给它招标文件和页数要求，自动生成图文并茂的投标素材 DOCX | [README](./bid-assets-maker/README.md) |

> 随着 skill 持续增加，此表会同步更新。

## 如何使用

1. 将本仓库克隆到本地
2. 将目标 skill 目录复制或软链接到 Claude Code/opencode/codex等agent工具 的 skill 目录（通常是 `.claude/skills/`）
3. 进入对应 skill 的 README 查看依赖安装和使用说明

```bash
# 示例：将 bid-assets-maker 安装到 Claude Code skill 目录
cp -r bid-assets-maker ~/.claude/skills/
```

## 许可

仅供个人学习和使用。
