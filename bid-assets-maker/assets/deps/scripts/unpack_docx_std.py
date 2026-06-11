#!/usr/bin/env python3
"""
Pure stdlib DOCX unpacker - zero external dependencies.
Extracts text, tables, and media from .docx files.
"""

import zipfile
import xml.etree.ElementTree as ET
import os
import re
import shutil
import argparse


def extract_docx(input_path, output_dir):
    """Extract DOCX content using only Python stdlib."""
    os.makedirs(output_dir, exist_ok=True)
    media_dir = os.path.join(output_dir, "media")
    os.makedirs(media_dir, exist_ok=True)

    with zipfile.ZipFile(input_path, 'r') as z:
        # Extract media files
        for name in z.namelist():
            if name.startswith('word/media/'):
                media_name = os.path.basename(name)
                data = z.read(name)
                with open(os.path.join(media_dir, media_name), 'wb') as f:
                    f.write(data)

        # Parse document.xml
        doc_xml = z.read('word/document.xml')
        root = ET.fromstring(doc_xml)
        ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

        output = []

        def get_text(elem):
            parts = []
            for t in elem.iter('{%s}t' % ns):
                if t.text:
                    parts.append(t.text)
            return ''.join(parts)

        for child in root.iter('{%s}body' % ns):
            for elem in child:
                tag = elem.tag
                if tag == '{%s}p' % ns:
                    # Heading or paragraph
                    ppr = elem.find('{%s}pPr' % ns)
                    hs = None
                    if ppr is not None:
                        ps = ppr.find('{%s}pStyle' % ns)
                        if ps is not None and ps.get('{%s}val' % ns):
                            sv = ps.get('{%s}val' % ns)
                            m = re.match(r'heading(\d)', sv)
                            if m:
                                hs = int(m.group(1))
                    text = get_text(elem)
                    if text.strip():
                        if hs:
                            output.append(('h', hs, text.strip()))
                        else:
                            output.append(('p', 0, text.strip()))

                elif tag == '{%s}tbl' % ns:
                    # Table
                    rows = []
                    for tr in elem.iter('{%s}tr' % ns):
                        cells = []
                        for tc in tr.iter('{%s}tc' % ns):
                            cells.append(get_text(tc))
                        rows.append(cells)
                    output.append(('table', rows))

    return output


def to_markdown(extracted, output_path):
    """Convert extracted content to Markdown."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in extracted:
            if item[0] == 'h':
                _, level, text = item
                f.write('\n' + '#' * level + ' ' + text + '\n\n')
            elif item[0] == 'p':
                _, _, text = item
                f.write(text + '\n\n')
            elif item[0] == 'table':
                _, rows = item
                if not rows:
                    continue
                # Header
                f.write('| ' + ' | '.join(rows[0]) + ' |\n')
                f.write('| ' + ' | '.join(['---'] * len(rows[0])) + ' |\n')
                for row in rows[1:]:
                    # Pad row to match header width
                    while len(row) < len(rows[0]):
                        row.append('')
                    f.write('| ' + ' | '.join(row) + ' |\n')
                f.write('\n')


def main():
    p = argparse.ArgumentParser(description='Unpack DOCX using stdlib only')
    p.add_argument('input', help='Input .docx file')
    p.add_argument('output_dir', help='Output directory')
    args = p.parse_args()

    extracted = extract_docx(args.input, args.output_dir)
    md_path = os.path.join(args.output_dir, 'output.md')
    to_markdown(extracted, md_path)
    print(f'Extracted: {md_path}')
    print(f'Media: {os.path.join(args.output_dir, "media")}')


if __name__ == '__main__':
    main()
