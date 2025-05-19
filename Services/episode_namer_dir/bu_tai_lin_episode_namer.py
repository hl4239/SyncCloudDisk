import asyncio
import re

from Services.episode_namer_dir.episode_namer import EpisodeNamer


class BuTaiLinEpisodeNamer(EpisodeNamer):
    @staticmethod
    def generate_name(original_name_list: list[str]) -> list[EpisodeNamer.FormatName]:
        format_name_list = [
            EpisodeNamer.FormatName(original_name=i, format_name=None) for i in original_name_list
        ]
        for format_name in format_name_list:
            name = format_name.original_name

            pattern_single = r'.*\[第(\d{1,2})集\].*'
            pattern_full = r'.*\[全(\d{1,2})集\]'
            pattern_range = r'.*\[第(\d{1,2}-\d{1,2})集\]'

            if match := re.search(pattern_single, name):
                episode_num = match.group(1).zfill(2)  # 补零
                format_name.format_name = f"{episode_num}"
            elif match := re.search(pattern_range, name):
                episode_range = match.group(1)
                format_name.format_name = f"{episode_range}"
            elif match := re.search(pattern_full, name):
                full_count = match.group(1).zfill(2)
                format_name.format_name = f"01-{full_count}"
            else:
                format_name.format_name = "UNKNOWN"

        return format_name_list
def main():
    result= BuTaiLinEpisodeNamer.generate_name(['的赛道送i[第1集]','cxzczxcxz[][全34集]','udiashiudshas[第1-2集]'])
    print(result)
if __name__ == '__main__':
    main()
