import random
import warnings

from pypinyin import pinyin, Style
from hanzi_chaizi import HanziChaizi

# --- 新增代码：用于忽略特定的警告 ---
# 过滤掉来自 hanzi_chaizi 库中关于 pkg_resources 的 UserWarning
warnings.filterwarnings("ignore", category=UserWarning, module='hanzi_chaizi')
def obfuscate_title_pro(title: str,
                        pinyin_ratio: float = 0.4,
                        decompose_ratio: float = 0.3,  # 新增参数：拆字的概率
                        keep_char_ratio: float = 0.2,
                        separator: str = '-',
                        add_random_digit: bool = False) -> str:
    """
    一个更强大的通用标题混淆函数，支持汉字拆分。

    Args:
        title (str): 原始标题。
        pinyin_ratio (float): 转换为拼音首字母的概率。
        decompose_ratio (float): 汉字被拆分的概率。
        keep_char_ratio (float): 保留原样的概率 (在pinyin_ratio和decompose_ratio之后计算)。
                                 剩下的概率将被处理为全拼音。
        separator (str): 用于连接各部分的分隔符。
        add_random_digit (bool): 是否在分隔符后随机添加一位数字。

    Returns:
        str: 混淆后的标题。
    """
    obfuscated_parts = []
    # 初始化拆字工具
    hc = HanziChaizi()

    # 获取每个字的拼音
    pinyin_list = pinyin(title, style=Style.TONE3)

    for i, char in enumerate(title):
        # 仅处理中文汉字
        if '\u4e00' <= char <= '\u9fff':
            rand_val = random.random()

            # 策略1: 转换为拼音首字母
            if rand_val < pinyin_ratio:
                initial = pinyin_list[i][0][0]
                obfuscated_parts.append(initial.upper())

            # 策略2: 拆分汉字
            elif rand_val < pinyin_ratio + decompose_ratio:
                try:
                    # 尝试拆分，取第一个拆分结果
                    decomposed_parts = hc.query(char)
                    # 如果成功拆分且结果不止一个部分，则使用
                    if len(decomposed_parts) > 1:
                        # 将拆分的部分用分隔符连接起来
                        obfuscated_parts.append(separator.join(decomposed_parts))
                    else:
                        # 如果无法拆分（例如“一”），则退回到保留原字
                        obfuscated_parts.append(char)
                except KeyError:
                    # 如果字库里没有这个字，也退回到保留原字
                    obfuscated_parts.append(char)

            # 策略3: 保留原始汉字或转换为全拼音
            else:
                if random.random() < keep_char_ratio:
                    obfuscated_parts.append(char)
                else:
                    full_pinyin = pinyin(char, style=Style.NORMAL)[0][0]
                    obfuscated_parts.append(full_pinyin)
        else:
            # 非汉字字符直接保留
            obfuscated_parts.append(char)

    # 用分隔符连接最终结果
    final_string = ""
    for part in obfuscated_parts:
        final_string += part
        if separator:
            final_string += separator
        if add_random_digit and random.choice([True, False]):
            final_string += str(random.randint(0, 9))
            if separator:
                final_string += separator

    # 清理末尾多余的分隔符
    if final_string.endswith(separator):
        final_string = final_string[:-len(separator)]
    if final_string.endswith(separator):
        final_string = final_string[:-len(separator)]

    return final_string


@staticmethod
def obfuscate_title_kongge(original_name: str, _retry: int = 0) -> str:
    while _retry < 10:
        name_part = original_name.replace(" ", "")
        # 如果名字太短（少于3个字符），无法插入两个空格
        if len(name_part) < 3:
            return name_part

        # 随机选择两个不同的位置插入空格
        positions = sorted(random.sample(range(1, len(name_part)), 2))

        # 构建新名称
        new_name = (
            name_part[:positions[0]] + " " +
            name_part[positions[0]:positions[1]] + " " +
            name_part[positions[1]:]
        )

        # 如果新名字和原始名字不同，则返回
        if new_name != original_name:
            return new_name

        _retry += 1

    # 如果重试10次仍未成功（理论上几乎不可能）
    return original_name

if __name__ == '__main__':
    # --- 使用示例 ---

    original_title = "漫威丧尸"

    # 示例1: 模拟 "Y-1-笑-S-哥欠" 的风格
    # 提高首字母和拆字的概率
    print(f"原始标题: {original_title}")
    confused_title_1 = obfuscate_title_pro(original_title, pinyin_ratio=0.3, decompose_ratio=0.3, keep_char_ratio=0.4,
                                           separator='-')
    print(f"模拟拆字风格: {confused_title_1}")

    original_title_2 = "黑暗荣耀"
    # 示例2: 对另一个标题应用多种混淆
    print(f"\n原始标题: {original_title_2}")
    confused_title_2 = obfuscate_title_pro(original_title_2, pinyin_ratio=0.3, decompose_ratio=0.5, keep_char_ratio=0.2)
    print(f"多种混淆风格: {confused_title_2}")

    # 示例3: 极端拆字风格
    original_title_3 = "繁花"
    print(f"\n原始标题: {original_title_3}")
    confused_title_3 = obfuscate_title_pro(original_title_3, pinyin_ratio=0.0, decompose_ratio=1.0, keep_char_ratio=0.0,
                                           separator='_')
    print(f"极端拆字风格: {confused_title_3}")