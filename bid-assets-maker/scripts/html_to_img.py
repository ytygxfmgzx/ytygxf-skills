#!/usr/bin/env python3
"""
HTML to PNG tool using Chrome headless.
- 视口截图 (800x10800) 避免内容被截断，宽度适配 docx
- 阈值法自动裁剪空白区域（灰度 >= 250 视为背景）
- file:// URL 编码中文路径，兼容中文文件名
- 优先检测项目内 Puppeteer Chromium
Fallback: keep HTML file for manual viewing if Chrome unavailable.
"""

import subprocess
import os
import sys
import shutil
import argparse
from urllib.parse import quote

PILLOW_AVAILABLE = False
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    pass


def _find_puppeteer_chrome():
    """检测项目 node_modules 中 Puppeteer 下载的 Chromium"""
    search_roots = [
        os.getcwd(),
        os.path.dirname(os.path.abspath(__file__)),  # scripts 目录
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # skill 根目录
    ]
    for start in search_roots:
        # 向上查找包含 node_modules 的目录
        for root, dirs, files in os.walk(start):
            basename = os.path.basename(root)
            if basename == '.local-chromium':
                for f in files:
                    if f.endswith('.exe') and ('chrome' in f.lower() or 'chromium' in f.lower()):
                        return os.path.join(root, f)
            # 不要走太深
            relative = os.path.relpath(root, start)
            if relative.count(os.sep) > 8:
                break
    return None


def find_chrome():
    """查找 Chrome/Chromium 可执行文件"""
    # 1. 优先项目内的 Puppeteer Chromium
    pc = _find_puppeteer_chrome()
    if pc:
        return pc

    # 2. 环境变量
    env_chrome = os.environ.get('CHROME_PATH') or os.environ.get('CHROMIUM_PATH')
    if env_chrome and os.path.exists(env_chrome):
        return env_chrome

    # 3. PATH 搜索
    for cmd in ["google-chrome", "chrome", "chromium", "chromium-browser"]:
        p = shutil.which(cmd)
        if p:
            return p

    # 4. Windows 默认路径
    for p in [
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        os.path.expanduser("~/AppData/Local/Google/Chrome/Application/chrome.exe"),
        os.path.expanduser("~/AppData/Local/Chromium/Application/chrome.exe"),
    ]:
        if os.path.exists(p):
            return p
    return None


def html_to_png(html_path, output_path, view_width=800, view_height=10800):
    """截图并自动裁剪空白区域"""
    chrome = find_chrome()
    if not chrome:
        print(f"Warning: Chrome not found, HTML kept at: {html_path}")
        return False

    abs_html = os.path.abspath(html_path)
    abs_output = os.path.abspath(output_path)
    file_url = f"file:///{quote(abs_html.replace(os.sep, '/'), safe='/:')}"
    cmd = [
        chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
        f"--screenshot={abs_output}",
        f"--window-size={view_width},{view_height}",
        file_url
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=60, cwd=os.path.dirname(abs_output))
        if not os.path.exists(output_path):
            print(f"FAIL: {r.stderr.decode('utf-8', errors='replace') if r.stderr else 'None'}")
            return False

        # 用 Pillow 裁剪白色空白区域（如果可用）
        if PILLOW_AVAILABLE:
            try:
                img = Image.open(output_path)
                if img.mode == 'RGBA':
                    bbox = img.getbbox()
                else:
                    # 阈值法：灰度 >= 250 视为背景（白），< 250 视为内容
                    gray = img.convert('L')
                    binary = gray.point(lambda p: 0 if p >= 250 else 255)
                    bbox = binary.getbbox()
                if bbox:
                    pad = 8
                    x1 = max(bbox[0] - pad, 0)
                    y1 = max(bbox[1] - pad, 0)
                    x2 = min(bbox[2] + pad, img.width)
                    y2 = min(bbox[3] + pad, img.height)
                    cropped = img.crop((x1, y1, x2, y2))
                    cropped.save(output_path)
                    print(f"OK (cropped to {cropped.size}): {output_path}")
                else:
                    print(f"OK (no content found): {output_path}")
            except Exception as e:
                print(f"OK (crop failed: {e}): {output_path}")
        else:
            print(f"OK (no Pillow for crop): {output_path}")

        return True
    except subprocess.TimeoutExpired:
        print(f"ERROR: Chrome timeout for {html_path}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def gen_flowchart_html(title, steps, out):
    items_html = ""
    for s in steps:
        items_html += f'<div style="background:#E8F0FE;border:2px solid #4A90D9;border-radius:8px;padding:10px 20px;font-size:14px;text-align:center;min-width:200px;background:#fff">{s}</div>\n'
        items_html += '<div style="color:#4A90D9;font-size:20px;font-weight:bold;text-align:center">↓</div>\n'
    items_html = items_html.rsplit('<div style="color:#4A90D9;font-size:20px;font-weight:bold;text-align:center">↓</div>\n', 1)[0]
    html = f"""<!DOCTYPE html><html><meta charset="UTF-8"><body style="font-family:sans-serif;padding:20px;background:#fff;max-width:760px;margin:0 auto">
<div style="text-align:center;font-weight:bold;font-size:16px;margin-bottom:15px">{title}</div>
<div style="display:flex;flex-direction:column;align-items:center;gap:4px">
{items_html}</div></body></html>"""
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Flowchart HTML: {out}")


def gen_barchart_html(title, labels, values, out):
    mx = max(values) if values else 1
    bars = ""
    for l, v in zip(labels, values):
        pct = (v / mx) * 100
        bars += (
            f'<div style="display:flex;align-items:center;margin:6px 0;gap:8px">'
            f'<div style="width:100px;text-align:right;font-size:12px;color:#333">{l}</div>'
            f'<div style="flex:1;height:24px;background:#f0f0f0;border-radius:4px;overflow:hidden">'
            f'<div style="height:100%;width:{pct:.0f}%;background:linear-gradient(90deg,#4A90D9,#357ABD);border-radius:4px"></div></div>'
            f'<div style="width:40px;font-size:12px;color:#333">{v}</div></div>\n'
        )
    html = f"""<!DOCTYPE html><html><meta charset="UTF-8"><body style="font-family:sans-serif;padding:20px;background:#fff;max-width:760px;margin:0 auto">
<div style="text-align:center;font-weight:bold;font-size:16px;margin-bottom:15px">{title}</div>
{bars}</body></html>"""
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Barchart HTML: {out}")


def gen_piechart_html(title, labels, values, out):
    total = sum(values)
    if not total:
        return
    colors = ["#4A90D9", "#F5A623", "#7ED321", "#D0021B", "#9013FE", "#50E3C2", "#B8E986", "#F8E71C"]
    cur_pct = 0.0
    stops = []
    legend = ""
    for i, (l, v) in enumerate(zip(labels, values)):
        if not v:
            continue
        c = colors[i % len(colors)]
        next_pct = cur_pct + (v / total) * 100
        stops.append(f"{c} {cur_pct:.2f}% {next_pct:.2f}%")
        cur_pct = next_pct
        legend += f'<div style="display:flex;align-items:center;gap:4px;font-size:12px"><div style="width:12px;height:12px;background:{c};border-radius:2px"></div>{l} ({v})</div>\n'
    gradient = ", ".join(stops)
    html = f"""<!DOCTYPE html><html><meta charset="UTF-8"><body style="font-family:sans-serif;padding:20px;background:#fff;max-width:760px;margin:0 auto">
<div style="display:flex;align-items:center;gap:20px">
<div style="width:300px;height:300px;border-radius:50%;background:conic-gradient({gradient})"></div>
<div>{legend}</div></div>
<div style="text-align:center;font-weight:bold;margin-top:10px">{title}</div></body></html>"""
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Piechart HTML: {out}")


def crop_png(png_path):
    """对已有的 PNG 重新裁剪白边（无 Chrome 依赖，纯 Pillow 操作）"""
    if not PILLOW_AVAILABLE:
        print(f"SKIP (no Pillow): {png_path}")
        return False

    img = Image.open(png_path)
    if img.height != 10800:
        print(f"SKIP (already cropped, {img.width}x{img.height}): {png_path}")
        return True

    gray = img.convert('L')
    binary = gray.point(lambda p: 0 if p >= 250 else 255)
    bbox = binary.getbbox()
    if not bbox:
        print(f"WARN (no content found): {png_path}")
        return False

    pad = 8
    x1 = max(bbox[0] - pad, 0)
    y1 = max(bbox[1] - pad, 0)
    x2 = min(bbox[2] + pad, img.width)
    y2 = min(bbox[3] + pad, img.height)
    cropped = img.crop((x1, y1, x2, y2))
    cropped.save(png_path)
    print(f"CROPPED ({img.width}x{img.height} -> {cropped.width}x{cropped.height}): {png_path}")
    return True


def crop_all(directory):
    """批量扫描目录下所有 PNG，裁剪高度 == 10800 的未裁剪图片"""
    if not PILLOW_AVAILABLE:
        print("ERROR: Pillow not available, cannot crop")
        return

    total = 0
    cropped_count = 0
    for root, dirs, files in os.walk(directory):
        for f in files:
            if not f.lower().endswith('.png'):
                continue
            png_path = os.path.join(root, f)
            img = Image.open(png_path)
            total += 1
            if img.height != 10800:
                continue
            # 发现未裁剪图片，执行裁剪
            gray = img.convert('L')
            binary = gray.point(lambda p: 0 if p >= 250 else 255)
            bbox = binary.getbbox()
            if bbox:
                pad = 8
                x1 = max(bbox[0] - pad, 0)
                y1 = max(bbox[1] - pad, 0)
                x2 = min(bbox[2] + pad, img.width)
                y2 = min(bbox[3] + pad, img.height)
                c = img.crop((x1, y1, x2, y2))
                c.save(png_path)
                print(f"CROPPED ({img.width}x{img.height} -> {c.width}x{c.height}): {png_path}")
                cropped_count += 1
            else:
                print(f"WARN (no content found): {png_path}")

    print(f"\nDone: {total} PNGs scanned, {cropped_count} cropped")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd")
    s = sp.add_parser("shot", help="HTML to PNG")
    s.add_argument("html")
    s.add_argument("out")
    s.add_argument("--w", type=int, default=800)
    s.add_argument("--h", type=int, default=10800)
    g = sp.add_parser("gen", help="Generate chart HTML")
    g.add_argument("type", choices=["flow", "bar", "pie"])
    g.add_argument("title")
    g.add_argument("out")
    g.add_argument("--labels", nargs="+", required=True)
    g.add_argument("--values", nargs="+", type=float)
    g.add_argument("--steps", nargs="+")
    c = sp.add_parser("crop", help="Re-crop a single PNG (remove whitespace)")
    c.add_argument("png", help="Path to the PNG file to crop")
    ca = sp.add_parser("crop-all", help="Scan directory and crop all 800x10800 PNGs")
    ca.add_argument("directory", help="Root directory to scan for PNGs")
    a = p.parse_args()
    if a.cmd == "shot":
        html_to_png(a.html, a.out, a.w, a.h)
    elif a.cmd == "gen":
        if a.type == "flow":
            gen_flowchart_html(a.title, a.steps or [], a.out)
        elif a.type == "bar":
            gen_barchart_html(a.title, a.labels, a.values or [], a.out)
        elif a.type == "pie":
            gen_piechart_html(a.title, a.labels, a.values or [], a.out)
    elif a.cmd == "crop":
        crop_png(a.png)
    elif a.cmd == "crop-all":
        crop_all(a.directory)
