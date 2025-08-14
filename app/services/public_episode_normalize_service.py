import asyncio
import logging
import re

from app.domain.models.episode_normalized import EpisodeNormalized
from app.services.episode_normalize_service import EpisodeNormalizeService

logger=logging.getLogger()
class PublicEpisodeNormalizeService(EpisodeNormalizeService):
    @staticmethod
    async def generate_name(original_name_list: list[str]) -> list[EpisodeNormalized]:
        normalized_name_list = [
            EpisodeNormalized(original_name=i, normalized_name=None,is_valid=False) for i in original_name_list
        ]
        normalized_error_list=[]
        for item in normalized_name_list:
            name = item.original_name.lower()

            # --- 单集匹配规则 ---
            single_patterns = [
                r's\d{2}e(\d{2})',  # xxxS01E01xxx
                r'^(\d{2})\.(mkv|mp4|torrent)$',  # 02.mkv
                r'^(\d{2})[ -]4k([\. ].*|\.(mkv|mp4|torrent))$',  # 02 4k
                r'^(\d{2})_r{\d+}\.(mkv|mp4)$'  # 02_r123.mkv
            ]

            matched = False
            for pattern in single_patterns:
                if match := re.search(pattern, name):
                    episode_num = match.group(1).zfill(2)
                    item.normalized_name = episode_num
                    item.is_valid = True
                    matched = True
                    logger.debug(f'使用pattern标准化:{name} | {pattern}')
                    break

            # --- 范围匹配规则（如01-12） ---
            if not matched:
                range_patterns = [
                    r'更新至(\d{1,2})集',  # 更新至10集
                    r'(\d{1,2})集全',  # 12集全
                    r'全(\d{1,2})集',  # 全12集
                    r'(\d{1,2})[ ]*[-~—][ ]*(\d{1,2})',  # 01-12, 03 ~ 08, 01—06（em-dash）
                    r'(\d{1,2})集打包'

                ]
                for pattern in range_patterns:
                    if match := re.search(pattern, name):
                        if len(match.groups()) == 1:
                            # 单一数字，格式化为 01-XX
                            full_count = match.group(1).zfill(2)
                            item.normalized_name = f"01-{full_count}"
                            item.is_valid = True
                        else:
                            # 匹配到两个数字范围
                            start = match.group(1).zfill(2)
                            end = match.group(2).zfill(2)
                            item.normalized_name = f"{start}-{end}"
                            item.is_valid = True
                        logger.debug(f'使用pattern标准化:{name} | {pattern}')
                        matched = True
                        break

            if not matched:
                range_patterns = [
                    r'全集种子'
                ]
                for pattern in range_patterns:
                    if match := re.search(pattern, name):
                        item.normalized_name='01-99'
                        item.is_valid = True
                        logger.debug(f'使用pattern标准化:{name} | {pattern}')
                        matched = True
                        break

            if not matched:
                normalized_error_list.append(item)
        normalized_name_list=[normalized_name for normalized_name in normalized_name_list if normalized_name.is_valid ]
        ori_name_list=[i.original_name for i in normalized_error_list]
        if len(ori_name_list)>0:
            normalized_error_handle_list= await EpisodeNormalizeService.generate_name(ori_name_list)
            normalized_name_list.extend(normalized_error_handle_list)


        return normalized_name_list

async def main():
    input=[
        'zxcxzS01E02.mkv8908',
        'sad40集全',
        '02-05',
        '更新至4集'

]


    result=await PublicEpisodeNormalizeService.generate_name(input)
    print(result)
if __name__ == '__main__':
    asyncio.run(main())


