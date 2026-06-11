#!/usr/bin/env python3
"""
MD → DOCX conversion script.
Priority:
  1. Use docx npm package (better formatting)
  2. Fallback to pure stdlib (assets/deps/scripts/pack_docx_std.py)

Supports --heading-offset N to shift all heading levels by N.
When merging chapters into a single DOCX, use --heading-offset 1
so each chapter's # becomes H2 (chapter name = H1 from plan.md).
"""

import os
import sys
import shutil
import subprocess
import argparse
import json
import re


def _escape_js_path(path):
    """转义路径用于嵌入 JS 字符串字面量"""
    return json.dumps(os.path.abspath(path))


def _get_node_path_env():
    """通过 pnpm root -g 或 npm root -g 获取全局 node_modules 路径"""
    for tool in ['pnpm', 'npm']:
        exe = shutil.which(tool)
        if not exe:
            continue
        try:
            r = subprocess.run(
                [exe, 'root', '-g'],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                root = r.stdout.strip()
                if os.path.isdir(root):
                    return root
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return None


def _build_node_env():
    """构建包含 NODE_PATH 的环境变量"""
    env = dict(os.environ)
    node_path = _get_node_path_env()
    if node_path:
        existing = env.get('NODE_PATH', '')
        env['NODE_PATH'] = node_path if not existing else f"{node_path}{os.pathsep}{existing}"
    return env


def use_npm(md_file, output_path, assets_dir=None, heading_offset=0):
    """Use docx npm package to create DOCX."""
    md_file_js = _escape_js_path(md_file)
    output_path_js = _escape_js_path(output_path)

    # 读取 MD 内容，提取图片实际尺寸用于等比缩放
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()

    img_dimensions = {}
    try:
        from PIL import Image as PILImage
        md_dir = os.path.dirname(os.path.abspath(md_file))
        for match in re.finditer(r'<img\s+src="([^"]+)"', md_content):
            img_rel = match.group(1)
            img_path = os.path.join(md_dir, img_rel)
            if os.path.exists(img_path):
                try:
                    with PILImage.open(img_path) as im:
                        img_dimensions[img_rel] = [im.width, im.height]
                except Exception:
                    pass
    except ImportError:
        pass
    img_dims_js = json.dumps(img_dimensions)

    js_code = f'''
const fs = require("fs");
const {{ Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
         AlignmentType, HeadingLevel, BorderStyle, WidthType, ImageRun }} = require("docx");

const MAX_IMG_W = 420;
const MAX_IMG_H = 560;
const headingOffset = {heading_offset};
const maxLevel = 7;
const imgDimensions = {img_dims_js};

const mdContent = fs.readFileSync({md_file_js}, "utf-8");
const lines = mdContent.split(/\\r?\\n/);

// 标题规范化：只保留第一个 H1，后续 H1 降为 H2
let foundFirstH1 = false;
for (let j = 0; j < lines.length; j++) {{
    const hm2 = lines[j].match(/^(#{{1,6}})\\s+(.+)$/);
    if (hm2 && hm2[1] === '#') {{
        if (!foundFirstH1) {{
            foundFirstH1 = true;
        }} else {{
            lines[j] = '## ' + hm2[2];
        }}
    }}
}}

const children = [];

const PAGE_WIDTH = 11906;
const PAGE_HEIGHT = 16838;
const MARGIN = 1440;
const CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN;

function stripNumbering(text) {{
    text = text.replace(/^[\\d]+[\\.\\d]*\\s+/, "");
    text = text.replace(/^[一二三四五六七八九十]+[、.]\\s*/, "");
    text = text.replace(/^[（(][一二三四五六七八九十\\d]+[）)]\\s*/, "");
    return text;
}}

function addText(text, opts = {{}}) {{
    children.push(new Paragraph({{
        spacing: {{ line: 280 }},
        ...opts,
        children: [new TextRun({{ text, font: "FangSong", size: 24, ...opts.run }})]
    }}));
}}

function addHeading(rawText, mdLevel) {{
    const text = stripNumbering(rawText);
    const effectiveLevel = Math.min(mdLevel + headingOffset, maxLevel);
    const headingLevels = [
        HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3
    ];
    const headingIds = ["Heading1","Heading2","Heading3","Heading4","Heading5","Heading6","Heading7"];
    const fontSizes = [32, 28, 24, 22, 21, 20, 20];
    const idx = effectiveLevel - 1;
    const hl = idx < 3 ? headingLevels[idx] : headingIds[idx];
    children.push(new Paragraph({{
        heading: hl,
        spacing: {{ before: 200, after: 100, line: 280 }},
        children: [new TextRun({{ text, font: "SimHei", size: fontSizes[idx], bold: true }})]
    }}));
}}

function addTable(rows) {{
    if (rows.length === 0) return;
    const colCount = Math.max(...rows.map(r => r.length));
    const colWidth = Math.floor(CONTENT_WIDTH / colCount);
    const border = {{ style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" }};
    const borders = {{ top: border, bottom: border, left: border, right: border }};

    children.push(new Table({{
        width: {{ size: CONTENT_WIDTH, type: WidthType.DXA }},
        columnWidths: Array(colCount).fill(colWidth),
        rows: rows.map((row, ri) => new TableRow({{
            children: row.map((cell, ci) => new TableCell({{
                borders,
                width: {{ size: colWidth, type: WidthType.DXA }},
                shading: ri === 0 ? {{ fill: "D5E8F0", type: "clear" }} : undefined,
                margins: {{ top: 80, bottom: 80, left: 120, right: 120 }},
                children: [new Paragraph({{ children: [new TextRun({{ text: cell, font: "FangSong", size: 20 }})] }})]
            }}))
        }}))
    }}));
}}

function addImage(imgPath, actualW, actualH) {{
    if (!fs.existsSync(imgPath)) return;
    const imgData = fs.readFileSync(imgPath);
    const ext = imgPath.split(".").pop().toLowerCase();
    let w, h;
    if (actualW && actualH) {{
        const scaleW = MAX_IMG_W / actualW;
        const scaleH = MAX_IMG_H / actualH;
        const scale = Math.min(scaleW, scaleH, 1);
        w = Math.round(actualW * scale);
        h = Math.round(actualH * scale);
    }} else {{
        w = MAX_IMG_W;
        h = Math.round(MAX_IMG_W * 2 / 3);
    }}
    children.push(new Paragraph({{
        children: [new ImageRun({{
            type: ext === "png" ? "png" : "jpeg",
            data: imgData,
            transformation: {{ width: w, height: h }},
            altText: {{ title: "img", description: "img", name: "img" }}
        }})],
        alignment: AlignmentType.CENTER
    }}));
}}

let i = 0;
while (i < lines.length) {{
    const line = lines[i].trim();
    if (!line) {{ i++; continue; }}

    const hm = line.match(/^(#{{1,6}})\\s+(.+)$/);
    if (hm) {{
        addHeading(hm[2], hm[1].length);
        i++;
        continue;
    }}

    if (line.startsWith("|")) {{
        const rows = [];
        while (i < lines.length && lines[i].trim().startsWith("|")) {{
            const l = lines[i].trim();
            if (!l.match(/^\\|[\\s:-]+\\|/)) {{
                const cells = l.split("|").slice(1, -1).map(c => c.trim());
                rows.push(cells);
            }}
            i++;
        }}
        addTable(rows);
        continue;
    }}

    const imgMatch = line.match(/<img\\s+src="([^"]+)"\\s*\\/?>/i);
    if (imgMatch) {{
        const dims = imgDimensions[imgMatch[1]] || [null, null];
        addImage(imgMatch[1], dims[0], dims[1]);
        i++;
        continue;
    }}

    addText(line);
    i++;
}}

const doc = new Document({{
    styles: {{
        default: {{ document: {{ run: {{ font: "FangSong", size: 24 }} }} }},
        paragraphStyles: [
            {{ id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
               run: {{ size: 32, bold: true, font: "SimHei" }},
               paragraph: {{ spacing: {{ before: 240, after: 120 }}, outlineLevel: 0 }} }},
            {{ id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
               run: {{ size: 28, bold: true, font: "SimHei" }},
               paragraph: {{ spacing: {{ before: 200, after: 100 }}, outlineLevel: 1 }} }},
            {{ id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
               run: {{ size: 24, bold: true, font: "SimHei" }},
               paragraph: {{ spacing: {{ before: 160, after: 80 }}, outlineLevel: 2 }} }},
            {{ id: "Heading4", name: "Heading 4", basedOn: "Normal", next: "Normal", quickFormat: true,
               run: {{ size: 22, bold: true, font: "SimHei" }},
               paragraph: {{ spacing: {{ before: 120, after: 60 }}, outlineLevel: 3 }} }},
            {{ id: "Heading5", name: "Heading 5", basedOn: "Normal", next: "Normal", quickFormat: true,
               run: {{ size: 21, bold: true, font: "SimHei" }},
               paragraph: {{ spacing: {{ before: 100, after: 50 }}, outlineLevel: 4 }} }},
            {{ id: "Heading6", name: "Heading 6", basedOn: "Normal", next: "Normal", quickFormat: true,
               run: {{ size: 20, bold: true, font: "SimHei" }},
               paragraph: {{ spacing: {{ before: 80, after: 40 }}, outlineLevel: 5 }} }},
            {{ id: "Heading7", name: "Heading 7", basedOn: "Normal", next: "Normal", quickFormat: true,
               run: {{ size: 20, bold: false, font: "SimHei" }},
               paragraph: {{ spacing: {{ before: 60, after: 30 }}, outlineLevel: 6 }} }},
        ]
    }},
    sections: [{{
        properties: {{
            page: {{
                size: {{ width: 11906, height: 16838 }},
                margin: {{ top: 1440, right: 1440, bottom: 1440, left: 1440 }}
            }}
        }},
        children
    }}]
}});

Packer.toBuffer(doc).then(buffer => {{
    fs.writeFileSync({output_path_js}, buffer);
    console.log("OK");
}});
'''

    js_path = md_file + '.gen.js'
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js_code)

    env = _build_node_env()
    result = subprocess.run(
        ['node', js_path],
        capture_output=True, text=True, timeout=60,
        env=env
    )

    if os.path.exists(js_path):
        os.unlink(js_path)

    if os.path.exists(output_path):
        print(f'DOCX created (npm): {output_path}')
        return True
    else:
        print(f'Node.js error: {result.stderr}', file=sys.stderr)
        return False


def use_stdlib(md_file, output_path, assets_dir, heading_offset=0):
    """Fallback to pure stdlib packer."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'assets', 'deps', 'scripts'))
    from pack_docx_std import pack
    pack(md_file, output_path, assets_dir, heading_offset=heading_offset)
    return True


def main():
    p = argparse.ArgumentParser(description='Convert MD to DOCX')
    p.add_argument('md_file', help='Input .md file')
    p.add_argument('output', help='Output .docx file')
    p.add_argument('--media-dir', help='Media/assets directory')
    p.add_argument('--force-stdlib', action='store_true', help='Force stdlib')
    p.add_argument('--heading-offset', type=int, default=0,
                   help='Shift heading levels by N (e.g. 1 makes # → H2, ## → H3)')
    args = p.parse_args()

    if not args.force_stdlib:
        if use_npm(args.md_file, args.output, args.media_dir,
                   heading_offset=args.heading_offset):
            return
        print('npm method failed, falling back to stdlib...', file=sys.stderr)

    use_stdlib(args.md_file, args.output, args.media_dir,
               heading_offset=args.heading_offset)


if __name__ == '__main__':
    main()
