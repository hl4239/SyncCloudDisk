import asyncio
import re

from Services.episode_namer_dir.episode_namer import EpisodeNamer


class PublicEpisodeNamer(EpisodeNamer):
    @staticmethod
    async def generate_name(original_name_list: list[str]) -> list[EpisodeNamer.FormatName]:
        format_name_list = [
            EpisodeNamer.FormatName(original_name=i, format_name=None) for i in original_name_list
        ]
        format_error_list=[]
        for format_name in format_name_list:


            name = format_name.original_name

            # xxxS01E01xxx
            pattern_1= r'.*\s\d{2}e(\d{2}).*'
            # 02.mkv
            pattern_2=r'(\d{2})\.(mkv|mp4)'
            #
            pattern_3=r'(\d{2}) 4k\.(mkv|mp4)'

            pattern_4=r'更新至(\d{1,2})集'

            pattern_5=r'(\d{1,2})集全'

            pattern_6 = r'(\d{2})_r{\d+}\.(mkv|mp4)'
            if match := re.search(pattern_1,name.lower()):
                episode_num = match.group(1).zfill(2)  # 补零
                format_name.format_name = f"{episode_num}"

            elif match := re.search(pattern_2, name.lower()):
                episode_num = match.group(1)
                format_name.format_name = f"{episode_num}"
            elif match := re.search(pattern_3, name.lower()):
                episode_num = match.group(1)
                format_name.format_name = f"{episode_num}"
            elif match := re.search(pattern_4, name.lower()):
                full_count = match.group(1).zfill(2)
                format_name.format_name = f"01-{full_count}"
            elif match := re.search(pattern_5, name.lower()):
                full_count = match.group(1).zfill(2)
                format_name.format_name = f"01-{full_count}"
            else:

                format_error_list.append(format_name)
        format_name_list=[format_name for format_name in format_name_list if format_name.format_name is not None]
        ori_name_list=[i.original_name for i in format_error_list]
        if len(ori_name_list)>0:
            format_error_handle_list= await EpisodeNamer.generate_name(ori_name_list)
            format_name_list.extend(format_error_handle_list)



        return format_name_list

async def main():
    input=[
        '15.4K.mp4','15.mp4'
]


    result=await PublicEpisodeNamer.generate_name(input)
    print(result)
if __name__ == '__main__':
    asyncio.run(main())


