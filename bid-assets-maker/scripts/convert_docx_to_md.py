#!/usr/bin/env python3
"""
DOCX → MD 转换脚本
层级0/1: 纯 Python 标准库方案（无外部依赖）
如果 pandoc 可用，优先使用 pandoc（更好效果）
"""

import zipfile
import os
import sys
import shutil
import xml.etree.ElementTree as ET
import re
import argparse

def extract_doc_elements(xml_content):
    """从 DOCX XML 中按文档顺序提取段落和表格"""
    ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    root = ET.fromstring(xml_content)

    elements = []
    body = root.find(f'{{{ns}}}body')
    if body is None:
        return elements

    for child in body:
        tag = child.tag
        if tag == f'{{{ns}}}p':
            texts = []
            for t in child.iter(f'{{{ns}}}t'):
                if t.text:
                    texts.append(t.text)
            text = ''.join(texts)
            if not text.strip():
                continue
            # 检测标题级别
            heading_level = 0
            pPr = child.find(f'{{{ns}}}pPr')
            if pPr is not None:
                pStyle = pPr.find(f'{{{ns}}}pStyle')
                if pStyle is not None:
                    val = pStyle.get(f'{{{ns}}}val', '')
                    m = re.match(r'heading(\d)', val)
                    if m:
                        heading_level = int(m.group(1))
            if heading_level:
                elements.append(('heading', heading_level, text.strip()))
            else:
                elements.append(('paragraph', 0, text.strip()))

        elif tag == f'{{{ns}}}tbl':
            rows = []
            for tr in child.iter(f'{{{ns}}}tr'):
                cells = []
                for tc in tr.iter(f'{{{ns}}}tc'):
                    cell_text = []
                    for t in tc.iter(f'{{{ns}}}t'):
                        if t.text:
                            cell_text.append(t.text)
                    cells.append(''.join(cell_text))
                rows.append(cells)
            if rows:
                elements.append(('table', rows))

    return elements

def use_pandoc(input_path, output_dir):
    """使用 pandoc 转换（最佳效果）"""
    output_md = os.path.join(output_dir, "output.md")
    media_dir = os.path.join(output_dir, "media")
    
    result = os.system(
        f'pandoc --extract-media="{media_dir}" "{input_path}" -o "{output_md}" --wrap=none'
    )
    
    if result != 0:
        print("pandoc 转换失败，降级到纯 Python 方案", file=sys.stderr)
        return use_stdlib(input_path, output_dir)
    
    print(f"✅ pandoc 转换完成: {output_md}")
    return output_md

def use_stdlib(input_path, output_dir):
    """使用 Python 标准库转换（零依赖方案）"""
    os.makedirs(output_dir, exist_ok=True)
    media_dir = os.path.join(output_dir, "media")
    os.makedirs(media_dir, exist_ok=True)

    output_md = os.path.join(output_dir, "output.md")

    with zipfile.ZipFile(input_path, 'r') as z:
        # 提取图片
        for name in z.namelist():
            if name.startswith('word/media/'):
                media_name = os.path.basename(name)
                z.extract(name, output_dir)
                src = os.path.join(output_dir, name)
                dst = os.path.join(media_dir, media_name)
                if os.path.exists(src):
                    shutil.move(src, dst)

        # 读取文档内容
        doc_xml = z.read('word/document.xml')

        # 按文档顺序提取段落和表格
        elements = extract_doc_elements(doc_xml)

    # 写入 MD 文件
    with open(output_md, 'w', encoding='utf-8') as f:
        for elem in elements:
            if elem[0] == 'heading':
                _, level, text = elem
                prefix = '#' * level
                f.write(f'\n{prefix} {text}\n\n')
            elif elem[0] == 'paragraph':
                _, _, text = elem
                f.write(f'{text}\n\n')
            elif elem[0] == 'table':
                _, rows = elem
                if not rows:
                    continue
                # 表头
                f.write('| ' + ' | '.join(rows[0]) + ' |\n')
                f.write('| ' + ' | '.join(['---'] * len(rows[0])) + ' |\n')
                # 表体
                for row in rows[1:]:
                    # 补齐列数
                    while len(row) < len(rows[0]):
                        row.append('')
                    f.write('| ' + ' | '.join(row) + ' |\n')
                f.write('\n')

    print(f"✅ 纯 Python 转换完成: {output_md}")
    return output_md

def main():
    parser = argparse.ArgumentParser(description='转换 DOCX 到 MD')
    parser.add_argument('input', help='输入 DOCX 文件路径')
    parser.add_argument('output_dir', help='输出目录路径')
    parser.add_argument('--force-stdlib', action='store_true', 
                        help='强制使用纯 Python 标准库方案')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 优先使用 pandoc
    if not args.force_stdlib and shutil.which("pandoc"):
        use_pandoc(args.input, args.output_dir)
    else:
        use_stdlib(args.input, args.output_dir)

if __name__ == "__main__":
    main()
