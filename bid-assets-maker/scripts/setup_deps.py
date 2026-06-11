#!/usr/bin/env python3
"""
依赖安装脚本 - 检测缺失依赖并通过国内镜像安装
层级2: 国内镜像一键安装
"""

import subprocess
import sys
import os
import shutil

def check_pandoc():
    """检查 pandoc 是否可用"""
    return shutil.which("pandoc") is not None

def check_docx_npm():
    """检查 docx npm 包是否可用"""
    if not check_node():
        return False
    try:
        result = subprocess.run(
            ["node", "-e", "require('docx'); console.log('ok')"],
            capture_output=True, text=True, timeout=10
        )
        return "ok" in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def check_chrome():
    """检查 Chrome 是否可用"""
    for cmd in ["google-chrome", "chrome", "chromium", "chromium-browser"]:
        if shutil.which(cmd):
            return True
    # Windows 路径检查
    chrome_paths = [
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        os.path.expanduser("~/AppData/Local/Google/Chrome/Application/chrome.exe"),
    ]
    return any(os.path.exists(p) for p in chrome_paths)

def check_node():
    """检查 Node.js 是否可用"""
    node = shutil.which("node")
    if not node:
        return False
    try:
        result = subprocess.run(
            [node, "--version"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def check_npm():
    """检查 npm 是否可用"""
    npm = shutil.which("npm")
    if not npm:
        return False
    try:
        result = subprocess.run(
            [npm, "--version"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def ensure_pnpm():
    """
    确保 pnpm 可用。优先使用已有 pnpm，否则通过 npm 自动安装。
    返回 pnpm 可执行文件路径，或 None 表示不可用。
    """
    pnpm = shutil.which("pnpm")
    if pnpm:
        return pnpm

    npm = shutil.which("npm")
    if not npm:
        return None

    print("  pnpm 未安装，正在通过 npm 自动安装 pnpm...")
    result = subprocess.run(
        [npm, "install", "-g", "pnpm"],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0:
        pnpm = shutil.which("pnpm")
        if pnpm:
            print("  ✅ pnpm 安装成功")
            return pnpm
    print(f"  ❌ pnpm 自动安装失败: {result.stderr}")
    return None

def check_python_deps():
    """检查 Python 依赖"""
    missing = []
    for pkg in ["defusedxml", "lxml"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    # Pillow 的包名与导入名不同，需单独检测
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        missing.append("Pillow")
    return missing

def check_python():
    """检查 Python 是否可用且版本 >= 3.10"""
    try:
        result = subprocess.run(
            [sys.executable, "--version"],
            capture_output=True, text=True, timeout=10
        )
        # 输出格式: "Python 3.12.0"
        version_str = result.stdout.strip().split()[-1]
        major, minor = map(int, version_str.split(".")[:2])
        return major >= 3 and minor >= 10
    except (IndexError, ValueError, subprocess.TimeoutExpired):
        return False

def install_docx_npm():
    """通过 npmmirror 安装 docx 包（使用 pnpm，自动安装 pnpm）"""
    pnpm = ensure_pnpm()
    if not pnpm:
        print("  ❌ Node.js/npm/pnpm 均不可用，无法安装 docx 包")
        print("  请安装 Node.js: https://nodejs.org/ （推荐 LTS 版本）")
        print("  安装后重新运行此脚本即可自动配置")
        return False

    print("  正在安装 docx 包（使用 pnpm 国内镜像）...")
    cmd = [pnpm, "add", "-g", "docx", "--registry=https://registry.npmmirror.com"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("  ✅ docx 包安装成功")
        return True
    else:
        print(f"  ❌ 安装失败: {result.stderr}")
        return False

def install_python_deps(missing):
    """通过国内 PyPI 镜像安装 Python 依赖"""
    print(f"正在安装 Python 依赖: {', '.join(missing)}（使用清华镜像）...")
    pip_cmd = [sys.executable, "-m", "pip", "install"]
    # 优先使用 uv
    uv_path = shutil.which("uv")
    if uv_path:
        pip_cmd = [uv_path, "add"]
    
    result = subprocess.run(
        pip_cmd + missing + ["-i", "https://pypi.tuna.tsinghua.edu.cn/simple"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"✅ Python 依赖安装成功: {', '.join(missing)}")
        return True
    else:
        print(f"❌ 安装失败: {result.stderr}")
        return False

def check_puppeteer_chrome():
    """检查项目内 Puppeteer 下载的 Chromium"""
    search_roots = [
        os.getcwd(),
        os.path.dirname(os.path.abspath(__file__)),
    ]
    for start in search_roots:
        for root, dirs, files in os.walk(start):
            basename = os.path.basename(root)
            if basename == '.local-chromium':
                for f in files:
                    if f.endswith('.exe') and ('chrome' in f.lower() or 'chromium' in f.lower()):
                        return os.path.join(root, f)
            relative = os.path.relpath(root, start)
            if relative.count(os.sep) > 8:
                break
    return None


def install_puppeteer():
    """在当前项目安装 Puppeteer（自动下载 Chromium，自动安装 pnpm）"""
    pnpm = ensure_pnpm()
    if not pnpm:
        print("  ❌ Node.js/npm/pnpm 均不可用，无法安装 Puppeteer")
        print("  请安装 Node.js: https://nodejs.org/ （推荐 LTS 版本）")
        print("  安装后重新运行此脚本即可自动配置")
        return False

    print("  正在安装 Puppeteer（使用国内镜像下载 Chromium）...")
    env = dict(os.environ)
    env["PUPPETEER_DOWNLOAD_HOST"] = "https://cdn.npmmirror.com/binaries/chrome-for-testing"
    env["PUPPETEER_CHROME_BASE_URL"] = "https://cdn.npmmirror.com/binaries/chrome-for-testing"
    result = subprocess.run(
        [pnpm, "add", "-D", "puppeteer"],
        capture_output=True, text=True, timeout=120,
        env=env
    )
    if result.returncode == 0:
        print("  ✅ Puppeteer 安装成功")
        return True
    else:
        print(f"  ❌ 安装失败: {result.stderr}")
        return False


def main():
    print("bid-assets-maker 依赖检测与自动安装脚本")
    print("=" * 50)
    print()

    # 前置: 检查 Python
    print("[前置] 检查 Python...", end=" ")
    if check_python():
        py_ver = subprocess.run(
            [sys.executable, "--version"], capture_output=True, text=True, timeout=10
        )
        print(f"✅ {py_ver.stdout.strip()}")
    else:
        print("❌ Python 3.10+ 未找到")
        print("  请安装 Python: https://www.python.org/downloads/")
        sys.exit(1)

    # 前置: 检查 Node.js
    node_available = check_node()
    print("[前置] 检查 Node.js...", end=" ")
    if node_available:
        ver = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, timeout=10
        )
        print(f"✅ 已安装 ({ver.stdout.strip()})")
    else:
        print("❌ 未安装")
        print("  请安装 Node.js LTS: https://nodejs.org/")
        sys.exit(1)

    if node_available:
        print("[前置] 检查 npm...", end=" ")
        if check_npm():
            npm_ver = subprocess.run(
                ["npm", "--version"], capture_output=True, text=True, timeout=10
            )
            print(f"✅ 已安装 ({npm_ver.stdout.strip()})")
        else:
            print("❌ 未安装")
            print("  npm 通常随 Node.js 一起安装，请重新安装 Node.js。")
            sys.exit(1)

    # 前置: 检查 pandoc
    print("[前置] 检查 pandoc...", end=" ")
    if check_pandoc():
        print("✅ 已安装")
    else:
        print("❌ 未安装")
        print("  请安装 pandoc: https://mirrors.tuna.tsinghua.edu.cn/github-release/jgm/pandoc")
        sys.exit(1)

    print()
    print("所有前置环境已就绪，开始安装可选依赖...")
    print()

    # 2. 检查 docx npm
    print("[1/3] 检查 docx npm 包...", end=" ")
    if check_docx_npm():
        print("✅ 已安装")
    else:
        print("❌ 未安装，正在自动安装...")
        install_docx_npm()

    # 3. 检查 Chrome / Puppeteer
    print("[2/3] 检查 Chrome/Puppeteer Chromium...", end=" ")
    if check_chrome() or check_puppeteer_chrome():
        print("✅ 已安装")
    else:
        print("❌ 未安装")
        print("  正在自动安装 Puppeteer...")
        install_puppeteer()

    # 4. 检查 Python 依赖
    print("[3/3] 检查 Python 依赖 (defusedxml, lxml, Pillow)...", end=" ")
    missing_pkg = check_python_deps()
    if not missing_pkg:
        print("✅ 已安装")
    else:
        print(f"❌ 缺失: {', '.join(missing_pkg)}，正在自动安装...")
        install_python_deps(missing_pkg)

    print()
    print("=" * 50)
    print("✅ 所有依赖已就绪！")
    print("=" * 50)

if __name__ == "__main__":
    main()
