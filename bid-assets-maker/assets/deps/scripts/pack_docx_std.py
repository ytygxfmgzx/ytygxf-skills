#!/usr/bin/env python3
"""
Pure stdlib DOCX packer - zero external dependencies.
Creates a minimal valid .docx from Markdown content.
"""

import zipfile
import os
import xml.etree.ElementTree as ET
import re
import argparse
from xml.sax.saxutils import escape as xml_escape


def create_minimal_docx(output_path, title="Document"):
    """Create a minimal valid DOCX with proper structure."""
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    # Content types
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Default Extension="jpg" ContentType="image/jpeg"/>
  <Default Extension="jpeg" ContentType="image/jpeg"/>
  <Default Extension="gif" ContentType="image/gif"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>'''

    # Relationships
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''

    # Word relationships
    word_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''

    # Minimal styles
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:rPr><w:rFonts w:ascii="FangSong" w:eastAsia="FangSong"/><w:sz w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="200" w:after="100"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="28"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="160" w:after="80"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading4">
    <w:name w:val="heading 4"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="120" w:after="60"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading5">
    <w:name w:val="heading 5"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="100" w:after="50"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="21"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading6">
    <w:name w:val="heading 6"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="80" w:after="40"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="20"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading7">
    <w:name w:val="heading 7"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="60" w:after="30"/></w:pPr>
    <w:rPr><w:sz w:val="20"/></w:rPr>
  </w:style>
</w:styles>'''

    # Minimal document
    doc = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
      <w:r><w:t>''' + xml_escape(title) + '''</w:t></w:r>
    </w:p>
  </w:body>
</w:document>'''

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', content_types)
        z.writestr('_rels/.rels', rels)
        z.writestr('word/_rels/document.xml.rels', word_rels)
        z.writestr('word/styles.xml', styles)
        z.writestr('word/document.xml', doc)

    return output_path


def _strip_heading_number(text):
    """剥离标题序号前缀：1.1、2.3.1、一、（一）等"""
    # 数字序号: "1.1 "、"2.3.1 "、"1 "
    text = re.sub(r'^[\d]+[\.\d]*\s+', '', text)
    # 中文序号: "一、"、"二."
    text = re.sub(r'^[一二三四五六七八九十]+[、.]\s*', '', text)
    # 括号序号: "（一）"、"（1）"、"(1)"
    text = re.sub(r'^[（(][一二三四五六七八九十\d]+[）)]\s*', '', text)
    return text


def md_to_body(md_text, heading_offset=0):
    """Convert Markdown text to DOCX body XML."""
    ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    body_elems = []

    lines = md_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Heading
        hm = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if hm:
            level = min(len(hm.group(1)) + heading_offset, 7)
            text = _strip_heading_number(hm.group(2))
            body_elems.append(('h', level, text))
            i += 1
            continue

        # Table
        if '|' in stripped and stripped.startswith('|'):
            table_rows = []
            while i < len(lines):
                l = lines[i].strip()
                if l.startswith('|'):
                    # Skip separator row
                    if not re.match(r'^\|[\s:-]+\|', l):
                        cells = [c.strip() for c in l.split('|')[1:-1]]
                        table_rows.append(cells)
                    i += 1
                else:
                    break
            if table_rows:
                body_elems.append(('table', table_rows))
            continue

        # Empty line
        if not stripped:
            i += 1
            continue

        # Paragraph
        body_elems.append(('p', 0, stripped))
        i += 1

    return body_elems


def build_docx_xml(body_elems, media_dir=None):
    """Build document.xml from parsed body elements."""
    ns_w = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    ns_r = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

    # Build XML manually for simplicity
    parts = ['<w:body>']

    img_id = 2  # Start from 2 (1 is used for styles)
    added_images = []

    for elem in body_elems:
        if elem[0] == 'h':
            _, level, text = elem
            parts.append(f'''<w:p><w:pPr><w:pStyle w:val="Heading{min(level, 7)}"/></w:pPr><w:r><w:t>{xml_escape(text)}</w:t></w:r></w:p>''')

        elif elem[0] == 'p':
            _, _, text = elem
            # Check for image references
            img_match = re.search(r'<img\s+src="([^"]+)"', text)
            if img_match and media_dir:
                img_src = img_match.group(1)
                img_path = os.path.join(media_dir, os.path.basename(img_src))
                if os.path.exists(img_path):
                    rel_id = f'rId{img_id}'
                    img_id += 1
                    added_images.append((rel_id, img_path))
                    # 图片尺寸: A4 内容宽度 ~15cm = 540万 EMU
                    # 标书配图统一限制在合理范围内
                    try:
                        from PIL import Image as PILImg
                        with PILImg.open(img_path) as _img:
                            w_px, h_px = _img.size
                        # 目标宽度: 450万 EMU (~12.5cm), 高度等比例
                        target_cx = 4500000
                        ratio = target_cx / (w_px * 9525) if w_px else 1  # 1px ≈ 9525 EMU at 96dpi
                        extent_cx = min(target_cx, 5400000)
                        extent_cy = min(int(h_px * 9525 * ratio), 3600000)
                    except ImportError:
                        extent_cx = 4500000
                        extent_cy = 2800000
                    parts.append(f'''<w:p><w:r><w:drawing><wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{extent_cx}" cy="{extent_cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="1" name="Image"/><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="0" name="Image"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="{rel_id}"/></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{extent_cx}" cy="{extent_cy}"/></a:xfrm><a:prstGeom prst="rect"/></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>''')
                    continue
            # Regular paragraph
            parts.append(f'''<w:p><w:r><w:t xml:space="preserve">{xml_escape(text)}</w:t></w:r></w:p>''')

        elif elem[0] == 'table':
            _, rows = elem
            if not rows:
                continue
            cols = len(rows[0]) if rows else 1
            parts.append(f'<w:tbl><w:tblPr><w:tblW w:w="9000" w:type="dxa"/><w:tblBorders><w:top w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/><w:left w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/><w:right w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/><w:insideV w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/></w:tblBorders></w:tblPr>')
            for ri, row in enumerate(rows):
                parts.append('<w:tr>')
                for cell in row:
                    shd = '<w:shd w:val="clear" w:color="auto" w:fill="D5E8F0"/>' if ri == 0 else ''
                    parts.append(f'<w:tc><w:tcPr><w:tcW w:w="{9000//cols}" w:type="dxa"/>{shd}</w:tcPr><w:p><w:r><w:t>{xml_escape(cell)}</w:t></w:r></w:p></w:tc>')
                parts.append('</w:tr>')
            parts.append('</w:tbl>')

    parts.append('</w:body>')
    body_xml = '\n'.join(parts)

    doc_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{ns_w}" xmlns:r="{ns_r}">
{body_xml}
</w:document>'''

    return doc_xml, added_images


def build_rels(added_images):
    """Build word/_rels/document.xml.rels with image relationships."""
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
'''
    for rel_id, img_path in added_images:
        ext = os.path.splitext(img_path)[1].lstrip('.')
        rels += f'  <Relationship Id="{rel_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{os.path.basename(img_path)}"/>\n'
    rels += '</Relationships>'
    return rels


def build_content_types(added_images):
    """Build [Content_Types].xml with image types."""
    cts = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
'''
    seen_exts = set()
    for _, img_path in added_images:
        ext = os.path.splitext(img_path)[1].lstrip('.')
        if ext not in seen_exts:
            seen_exts.add(ext)
            ct_map = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif'}
            ct = ct_map.get(ext, 'application/octet-stream')
            cts += f'  <Default Extension="{ext}" ContentType="{ct}"/>\n'
    cts += '''  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>'''
    return cts


def pack(md_file, output_path, media_dir=None, heading_offset=0):
    """Pack MD file into DOCX."""
    with open(md_file, 'r', encoding='utf-8') as f:
        md_text = f.read()

    body_elems = md_to_body(md_text, heading_offset=heading_offset)
    doc_xml, added_images = build_docx_xml(body_elems, media_dir)
    word_rels = build_rels(added_images)
    content_types = build_content_types(added_images)

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', content_types)
        z.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')
        z.writestr('word/_rels/document.xml.rels', word_rels)
        z.writestr('word/document.xml', doc_xml)
        z.writestr('word/styles.xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:rPr><w:rFonts w:ascii="FangSong" w:eastAsia="FangSong"/><w:sz w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="200" w:after="100"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="28"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="160" w:after="80"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading4">
    <w:name w:val="heading 4"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="120" w:after="60"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading5">
    <w:name w:val="heading 5"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="100" w:after="50"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="21"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading6">
    <w:name w:val="heading 6"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="80" w:after="40"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="20"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading7">
    <w:name w:val="heading 7"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="60" w:after="30"/></w:pPr>
    <w:rPr><w:sz w:val="20"/></w:rPr>
  </w:style>
</w:styles>''')
        # Add images
        for rel_id, img_path in added_images:
            arcname = f'word/media/{os.path.basename(img_path)}'
            z.write(img_path, arcname)

    print(f'DOCX created: {output_path}')
    return output_path


def main():
    p = argparse.ArgumentParser(description='Pack MD to DOCX using stdlib only')
    p.add_argument('md_file', help='Input .md file')
    p.add_argument('output', help='Output .docx file')
    p.add_argument('--media-dir', help='Media directory for images')
    args = p.parse_args()

    pack(args.md_file, args.output, args.media_dir)


if __name__ == '__main__':
    main()
