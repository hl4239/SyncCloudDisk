# clean_unused_packages.py
# 功能：检测 Python 项目中实际没用到的依赖包（兼容中文路径）
# 作者：GPT-5
# 使用：python clean_unused_packages.py

import os
import sys
import subprocess
import importlib.util
from pathlib import Path

def get_installed_packages():
    """获取当前环境中安装的包列表"""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore"
    )
    packages = set()
    for line in result.stdout.splitlines():
        if "==" in line:
            pkg = line.split("==")[0].strip().lower()
            packages.add(pkg)
    return packages


def get_imported_modules(project_path):
    """扫描项目所有 .py 文件中的 import 模块"""
    imported = set()
    for root, _, files in os.walk(project_path):
        # 跳过虚拟环境和缓存文件夹
        if any(x in root for x in [".venv", "venv", "__pycache__", "env"]):
            continue

        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                except UnicodeDecodeError:
                    # 兼容中文编码
                    with open(file_path, "r", encoding="gbk", errors="ignore") as f:
                        lines = f.readlines()

                for line in lines:
                    line = line.strip()
                    if line.startswith("import "):
                        parts = line.replace("import", "").strip().split(",")
                        for p in parts:
                            mod = p.split()[0].split(".")[0]
                            imported.add(mod)
                    elif line.startswith("from "):
                        mod = line.replace("from", "").split("import")[0].strip().split(".")[0]
                        imported.add(mod)
    return imported


def map_package_names(imported, installed):
    """把 import 的模块名映射到 pip 包名（近似匹配）"""
    used_pkgs = set()
    for imp in imported:
        for pkg in installed:
            if imp.lower() == pkg.lower():
                used_pkgs.add(pkg)
            elif imp.lower().replace("_", "-") == pkg.lower().replace("_", "-"):
                used_pkgs.add(pkg)
    return used_pkgs


def main():
    project_path = Path(__file__).parent
    print(f"📂 正在扫描项目路径: {project_path}")

    installed = get_installed_packages()
    print(f"📦 已安装包数量: {len(installed)}")

    imported = get_imported_modules(project_path)
    print(f"🧩 检测到 import 模块数量: {len(imported)}")

    used = map_package_names(imported, installed)
    unused = installed - used

    print("\n✅ 实际使用的依赖包:")
    print(", ".join(sorted(used)) or "（无）")

    print("\n🚫 未使用的依赖包:")
    print(", ".join(sorted(unused)) or "（无）")

    if unused:
        ans = input("\n是否卸载这些未使用的包？(y/N): ").strip().lower()
        if ans == "y":
            for pkg in unused:
                print(f"🧹 正在卸载 {pkg} ...")
                subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", pkg])
            print("\n✅ 清理完成！")
        else:
            print("\n💡 你可以手动运行以下命令卸载：")
            print("pip uninstall -y " + " ".join(unused))
    else:
        print("\n🎉 你的项目依赖非常干净，没有多余包！")


if __name__ == "__main__":
    main()
