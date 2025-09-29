import sys
from pathlib import Path


def analyze_import_times(file_path: Path, sort_by: str = "self"):
    """
    解析并排序 python -X importtime 的输出文件。
    此版本能自动处理 UTF-8 和 UTF-16 编码。
    """
    if not file_path.exists():
        print(f"错误: 文件 '{file_path}' 不存在。")
        return

    parsed_data = []

    # --- 关键修改：尝试用多种编码打开文件 ---
    try:
        # 首先尝试 UTF-8，这是最常见的
        file_content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # 如果 UTF-8 失败，尝试 UTF-16，这是 Windows PowerShell 重定向的常见编码
        print("提示: 使用 UTF-16 编码读取文件...")
        file_content = file_path.read_text(encoding="utf-16")
    except Exception as e:
        print(f"读取文件时发生未知错误: {e}")
        return

    for line in file_content.splitlines():
        if not line.startswith("import time:"):
            continue

        try:
            parts = line.split("|")
            self_time_str = parts[0].replace("import time:", "").strip()
            cumulative_time_str = parts[1].strip()
            module_name = parts[2].strip()

            self_time = int(self_time_str)
            cumulative_time = int(cumulative_time_str)

            parsed_data.append((self_time, cumulative_time, module_name))
        except (IndexError, ValueError):
            continue

    # --- 排序逻辑 (无变化) ---
    if sort_by == "self":
        sorted_data = sorted(parsed_data, key=lambda x: x[0], reverse=True)
        print("--- 模块导入耗时 (按 self 时间排序, 单位: 微秒 μs) ---\n")
    elif sort_by == "cumulative":
        sorted_data = sorted(parsed_data, key=lambda x: x[1], reverse=True)
        print("--- 模块导入耗时 (按 cumulative 时间排序, 单位: 微秒 μs) ---\n")
    else:
        print(f"错误: 无效的排序依据 '{sort_by}'。请使用 'self' 或 'cumulative'。")
        return

    # --- 打印结果 (无变化) ---
    print(f"{'Self Time (μs)':>15} | {'Cumulative Time (μs)':>20} | Module Name")
    print("-" * 70)

    for self_t, cumulative_t, mod_name in sorted_data[:30]:
        print(f"{self_t:>15,} | {cumulative_t:>20,} | {mod_name}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-c", "--cumulative"]:
        sort_key = "cumulative"
    else:
        sort_key = "self"

    input_file = Path("import_timing.txt")
    analyze_import_times(input_file, sort_by=sort_key)