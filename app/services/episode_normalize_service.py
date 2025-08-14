import json
import logging
import re
from typing import Optional, Set, List

from pydantic import BaseModel, Field, field_validator

from app.domain.models.episode_normalized import EpisodeNormalized
from app.infrastructure.call_ai import CallAI


logger = logging.getLogger()
class EpisodeNormalizeService:
    class OutPutNormalizedName(BaseModel):
        id: int = Field(description='Matches the ID from the question input ID')
        normalized_name: Optional[str] = Field(description="Episode number or range extracted from the filename (e.g. '05', '11-15', '01-48'). Non-numeric characters removed, 'XX集全' normalizedted as '01-XX'.",pattern=r'^(\d{2}|\d{2}-\d{2})$')

   

    @staticmethod
    async def generate_name(original_name_list: list[str]) -> list[EpisodeNormalized]:
        logger.debug(f'使用ai标准化：{original_name_list}')
        instruction = instruction = "从现在开始，你将把输入的文件名标准化为剧集信息"

        input_name_list = [
            {
                'id': index + 1,
                'input_name': value
            }
            for index, value in enumerate(original_name_list)
        ]
        input_name_maps = {
            i['id']: i['input_name']
            for i in input_name_list
        }
        tools = []
        normalized_output = list[EpisodeNormalizeService.OutPutNormalizedName]

        try:
            resp, final_output = await CallAI.ask(
                instruction,
                input=json.dumps(input_name_list),
                tools=tools,
                format_output=normalized_output
            )
            result = []
            # 对结果进行后处理校验
            for item in resp:
                is_valid=False
                if item.normalized_name is not None:
                    is_valid=True

                id = item.id
                input_name = input_name_maps[id]
                result.append(EpisodeNormalized(original_name=input_name, normalized_name=item.normalized_name,is_valid=is_valid))
            result_input_name_list=[
                f.original_name
                for f in result
            ]
            for  o in original_name_list:
                if o not in result_input_name_list:
                    result.append(EpisodeNormalized(original_name=o,normalized_name=None,is_valid=False))

            return result

        except Exception as e:
            result=[]
            for o in original_name_list:
                result.append(EpisodeNormalized(original_name=o,normalized_name=None,is_valid=False))
            logger.error(f"标准化 episode 发生错误: {e}")
            return result


    @staticmethod
    def normalized_name_to_num_list(range_episode):
        '''
        将剧集集合转为list int
        :param range_episode:
        :return: 例如['01','02-03']转为[1,2,3]
        '''
        results = range_episode.split('-')
        if len(results) == 1:
            return [int(range_episode)]
        if len(results) == 2:
            start, end = results
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
            expanded.update(EpisodeNormalizeService.normalized_name_to_num_list(ep))
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
        target_episodes = EpisodeNormalizeService.expand_and_deduplicate(target_collection_episode)
        collection_episode = EpisodeNormalizeService.expand_and_deduplicate(collection_episode)

        # 3. 计算差集并转为列表
        not_exists = list(collection_episode - target_episodes)

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
            num_set = set(EpisodeNormalizeService.normalized_name_to_num_list(ep))
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
            num_set = set(EpisodeNormalizeService.normalized_name_to_num_list(ep))
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

    @staticmethod
    def num_list_to_ranges(numbers: List[int]) -> List[str]:
        """
        将数字列表合并为尽量少的范围段，例如 [1,2,3,5,6,9] -> ['01-03', '05-06', '09']
        """
        if not numbers:
            return []

        sorted_numbers = sorted(set(numbers))
        ranges = []
        start = sorted_numbers[0]
        end = sorted_numbers[0]

        for num in sorted_numbers[1:]:
            if num == end + 1:
                end = num
            else:
                # 添加当前段
                if start == end:
                    ranges.append(f"{start:02d}")
                else:
                    ranges.append(f"{start:02d}-{end:02d}")
                start = end = num

        # 添加最后一段
        if start == end:
            ranges.append(f"{start:02d}")
        else:
            ranges.append(f"{start:02d}-{end:02d}")

        return ranges




