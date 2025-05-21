import asyncio
import json
import re
from typing import Optional, List, Set

from pydantic import BaseModel, Field, validator, field_validator

from Services.call_ai import CallAI


class EpisodeNamer:
    class FormatName(BaseModel):
        original_name: Optional[str] = Field(description='input_name')
        format_name: Optional[str] = Field(description='after extraction name')

        @field_validator('format_name')
        def validate_format_name(cls, v):
            if v is None:
                return v

            # 验证格式是否符合规范
            pattern = r'^(\d{1,4})(-\d{1,4})?$'
            if not re.fullmatch(pattern, v):
                raise ValueError(f"Invalid format_name: {v}. Must be in format 'XX' or 'XX-XX'")

            # 如果是范围格式，检查起始值小于结束值
            if '-' in v:
                start, end = map(int, v.split('-'))
                if start >= end:
                    raise ValueError(f"Invalid range: {v}. Start must be less than end")

            return v
    class OutPutFormatName(BaseModel):
        id: int = Field(description='Matches the ID from the question input ID')
        format_name: Optional[str] = Field( description="Episode number or range extracted from the filename (e.g. '05', '11-15', '01-48'). Non-numeric characters removed, 'XX集全' formatted as '01-XX'.")

        @field_validator('format_name')
        def validate_format_name(cls, v):
            if v is None:
                return v

            # 验证格式是否符合规范
            pattern = r'^(\d{1,4})(-\d{1,4})?$'
            if not re.fullmatch(pattern, v):
                raise ValueError(f"Invalid format_name: {v}. Must be in format 'XX' or 'XX-XX'")

            # 如果是范围格式，检查起始值小于结束值
            if '-' in v:
                start, end = map(int, v.split('-'))
                if start >= end:
                    raise ValueError(f"Invalid range: {v}. Start must be less than end")

            return v
    @staticmethod
    async def generate_name(original_name_list: list[str]) -> list[FormatName]:

        instruction = instruction = """
                                    Extract only the episode numbers/ranges from filenames. 
                                    Rules:
                                    1. Keep all numeric patterns matching:
                                       - Single episodes (e.g. "05" from "...05...")
                                       - Episode ranges (e.g. "11-15" from "...11-15...")
                                       - Episode All (e.g. "36集全" → "01-36")
                                       - Any digit combinations (e.g. "E01", "EP23-25","01.4K.mp4","02-4K.mkv"→ "01", "23-25","01","02")
                                    2. Remove ALL non-numeric characters (including "E", "EP", "集", etc.)
                                    3. No suffixes or extra text
                                    Special Cases:
                                    - For "XX集全" format, convert to "01-XX"
                                    - For single digits, pad with leading zero (e.g. "5" → "05")
                                    Examples:
                                    Input: "鹿鼎记11-15.mkv" → Output: "11-15"
                                    Input: "S01E05" → Output: "05" 
                                    Input: "EP23-25" → Output: "23-25"
                                    Input: "48集全" → Output: "01-48"
                                    Input: "E5" → Output: "05"
                                    """
        input_name_list=[
            {
                'id':index+1,
                'input_name':value
            }
            for index,value in enumerate(original_name_list)
        ]
        input_name_maps={
        i['id']:i['input_name']
        for i in input_name_list
        }
        tools = []
        format_output = list[EpisodeNamer.OutPutFormatName]

        try:
            resp ,final_output= await CallAI.ask(
                instruction,
                input=json.dumps(input_name_list),
                tools=tools,
                format_output=format_output
            )
            result=[]
            # 对结果进行后处理校验
            for item in resp:
                if item.format_name:
                    # 确保单集是两位数格式
                    if '-' not in item.format_name and len(item.format_name) == 1:
                        item.format_name = f"0{item.format_name}"

                    # 确保范围格式的起始集是两位数
                    if '-' in item.format_name:
                        start, end = item.format_name.split('-')
                        if len(start) == 1:
                            start = f"0{start}"
                        if len(end) == 1:
                            end = f"0{end}"
                        item.format_name = f"{start}-{end}"
                    id=item.id
                    input_name= input_name_maps[id]
                    result.append(EpisodeNamer.FormatName(original_name=input_name, format_name=item.format_name))
            if len(original_name_list)!=len(result):
                raise Exception(f'ai 格式化名称时发生缺漏,input:{input_name_list}\nresult:{resp}\nfinal_output:{final_output}')
            return result

        except Exception as e:
            raise ValueError(f"格式化 episode 发生错误: {e}") from e

    @staticmethod
    def format_name_to_num_list( range_episode):
        '''
        将剧集集合转为list int
        :param range_episode:
        :return: 例如['01','02-03']转为[1,2,3]
        '''
        results= range_episode.split('-')
        if len(results) == 1:
            return [int(range_episode)]
        if len(results) == 2:
            start, end =results
            start_num = int(start)
            end_num = int(end)

            # 生成范围内的所有数字，保持前导零
            length = len(start)  # 获取原始数字的位数
            return [num for num in range(start_num, end_num + 1)]
        raise ValueError(f"Invalid range: {range_episode}")


    @staticmethod
    def expand_and_deduplicate(episodes: List[str]) -> Set[int]:
        """
        # 1. 展开所有剧集范围并去重

        :param episodes:
        :return:
        """
        expanded = set()
        for ep in episodes:
            expanded.update(EpisodeNamer.format_name_to_num_list(ep))
        return expanded

    @staticmethod
    def is_collection_episode_in_other_collection(target_collection_episode: List[str],
                                 collection_episode: List[str]) -> List[int]:
        """
        检查目标剧集集合是否在已存在的剧集集合中，返回不存在的剧集列表（自动去重）

        参数:
            target_collection_episode: 要检查的剧集列表（如 ["01", "02-03", "02"]）
            collection_episode: 剧集列表（如 ["01-04"]）

        返回:
            不存在的剧集列表（去重后），如 [4]
        """



        # 2. 处理目标剧集和已存在剧集
        target_episodes =EpisodeNamer. expand_and_deduplicate(target_collection_episode)
        collection_episode =EpisodeNamer. expand_and_deduplicate(collection_episode)

        # 3. 计算差集并转为列表
        not_exists = list( collection_episode-target_episodes)

        # 4. 按数字顺序排序（可选）
        not_exists.sort(key=lambda x: int(x))

        return not_exists

    @staticmethod
    def find_collection_episode_by_list_num(
            target_numbers: List[int],
            collection_episodes: List[str]
    ) -> List[str]:
        """
        返回与 target_numbers 尽可能匹配的 collection_episodes，避免无关数字
        """
        target_set = set(target_numbers)
        covered = set()
        result = []

        # 预处理所有候选剧集为：原始字符串 + 集合 + 范围长度
        episode_items = []
        for ep in collection_episodes:
            num_set = set(EpisodeNamer.format_name_to_num_list(ep))
            episode_items.append({
                'str': ep,
                'set': num_set,
                'match': len(num_set & target_set),
                'extra': len(num_set - target_set),
            })

        # 贪心选择：每次选择 覆盖目标多、包含额外少 的剧集
        while covered != target_set:
            best = None
            best_score = float('-inf')
            for item in episode_items:
                if item['str'] in result:
                    continue
                new_cover = item['set'] & (target_set - covered)
                if not new_cover:
                    continue
                score = len(new_cover) - item['extra']  # 可调策略
                if score > best_score:
                    best_score = score
                    best = item

            if best is None:
                break  # 无法再覆盖更多

            result.append(best['str'])
            covered.update(best['set'])

        return result

    @staticmethod
    def remove_duplicates(collection_episodes: List[str]) -> List[str]:
        # 1. 全部展开成集合表示
        items = []
        for ep in collection_episodes:
            num_set = set(EpisodeNamer.format_name_to_num_list(ep))
            items.append({'str': ep, 'set': num_set})

        # 2. 去重（保留最早出现的）
        seen = {}
        for item in items:
            seen[item['str']] = item
        items = list(seen.values())

        # 3. 统计全集
        full_set: Set[int] = set()
        for item in items:
            full_set |= item['set']

        covered: Set[int] = set()
        selected = []

        while covered != full_set:
            # 找出当前能覆盖最多未覆盖元素的集合
            best_item = max(
                items,
                key=lambda x: len(x['set'] - covered),
                default=None
            )

            if not best_item or len(best_item['set'] - covered) == 0:
                break  # 没有能继续贡献新元素的集合了

            selected.append(best_item['str'])
            covered |= best_item['set']
            items.remove(best_item)

        return selected
async def main():
    input=[
        '15.mp4'
]

    # result=  EpisodeNamer.remove_duplicates(input)
    # # result= EpisodeNamer.is_collection_episode_in_other_collection(['01','02','03'],['01-03'])
    # # print(result)
    # # result1=EpisodeNamer.find_collection_episode_by_list_num(result,['01-03'])
    result=await EpisodeNamer.generate_name(input)
    print(result)
if __name__ == '__main__':
    asyncio.run(main())