#!/usr/bin/env python3
"""
按章节拆分 MD 文件 + 生成 index.md
"""

import os
import re
import sys
import argparse

def split_md_by_chapters(input_md, output_dir):
    """按一级标题拆分 MD 文件"""
    os.makedirs(output_dir, exist_ok=True)
    
    with open(input_md, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按一级标题分割
    # 匹配行首的 # 标题
    pattern = r'(?m)^# (.+)$'
    splits = list(re.finditer(pattern, content))
    
    chapters = []
    for i, match in enumerate(splits):
        title = match.group(1).strip()
        start = match.start()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(content)
        chapter_content = content[start:end].strip()
        
        # 清理文件名
        safe_title = re.sub(r'[\/*?:"<>|]', '', title)
        safe_title = safe_title.strip()
        if not safe_title:
            safe_title = f"章节{i+1}"
        
        filename = f"{safe_title}.md"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(chapter_content)
        
        chapters.append((title, filename))
    
    # 如果没有一级标题，整个文件作为一个章节
    if not chapters:
        filename = "全文.md"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        chapters.append(("全文", filename))
    
    return chapters

def generate_index(chapters, output_dir):
    """生成 index.md 索引文件"""
    index_path = os.path.join(output_dir, "index.md")
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write("# 招标文件章节索引\n\n")
        f.write("| 序号 | 章节名称 | 文件 |\n")
        f.write("|------|---------|------|\n")
        for i, (title, filename) in enumerate(chapters, 1):
            f.write(f"| {i} | {title} | [{filename}]({filename}) |\n")
    
    return index_path

def main():
    parser = argparse.ArgumentParser(description='按章节拆分 MD 文件')
    parser.add_argument('input_md', help='输入的 MD 文件路径')
    parser.add_argument('output_dir', help='输出目录路径')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_md):
        print(f"错误: 输入文件不存在: {args.input_md}", file=sys.stderr)
        sys.exit(1)
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    chapters = split_md_by_chapters(args.input_md, args.output_dir)
    index_path = generate_index(chapters, args.output_dir)
    
    print(f"✅ 拆分完成: {len(chapters)} 个章节")
    print(f"📄 索引文件: {index_path}")
    for title, filename in chapters:
        print(f"   - {title} → {filename}")

if __name__ == "__main__":
    main()
