import os
import random
import shutil
import subprocess
import hashlib
import sys
import tempfile
import uuid
from pathlib import Path

import xml.etree.ElementTree as ET
from mutagen.mp4 import MP4
from mutagen import File  # 用于MKV基础操作
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select
from database import engine
from models.resource import Resource
import os
import subprocess
import shutil
from typing import List, Optional, Dict
AP_TAG_MAPPING= {
    "TITLE": "--title",         # 映射到 MP4 的 ©nam 原子
    "ARTIST": "--artist",       # 映射到 MP4 的 ©ART 原子
    "ALBUM": "--album",         # 映射到 MP4 的 ©alb 原子
    "GENRE": "--genre",         # 映射到 MP4 的 ©gen 原子
    "COMMENT": "--comment",     # 映射到 MP4 的 ©cmt 原子
    "DESCRIPTION": "--description", # 映射到 MP4 的 desc 原子
    "LONGDESCRIPTION": "--longDescription", # 映射到 MP4 的 ldes 原子
    "YEAR": "--year",           # 映射到 MP4 的 ©day 原子 (通常是发行日期)
    "DIRECTOR": "--director",   # 映射到 MP4 的 ©dir 原子
    "PRODUCER": "--producer",   # 映射到 MP4 的 ©prd 原子
    "WRITER": "--writer",       # 映射到 MP4 的 ©wrt 原子
    "PUBLISHER": "--publisher", # 映射到 MP4 的 ©pub 原子
    # 可以根据需要添加更多标签映射，但要确保 AtomicParsley 支持它们
    # 例如，对于自定义标签或更复杂的元数据，可能需要 exiftool 或其他工具。
}

class MP4TagModifier:

    @staticmethod
    def _check_atomicparsley_installed() -> bool:
        """
        检查 AtomicParsley 命令是否存在于系统的 PATH 中。
        """
        try:
            # 在 Windows 上通常使用 'where'，在 Unix/Linux/macOS 上使用 'which' 或 'command -v'
            cmd = ['where', 'AtomicParsley'] if sys.platform == "win32" else ['which', 'AtomicParsley']
            # 尝试运行命令，如果成功则表示找到
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            # 如果命令未找到或执行失败，则返回 False
            return False

    @staticmethod
    def change_mp4_hash_by_modifying_tag(mp4_filepath: str,
                                         tag_to_modify: str = "COMMENT",
                                         new_value_prefix: str = "ModifiedTag_") -> bool:
        """
        通过修改 MP4 文件的指定标准标签来改变其哈希值。
        使用 AtomicParsley 进行就地修改，不涉及完整文件拷贝。

        注意：AtomicParsley 支持的标准标签有限。如果指定的标签不支持，将失败。
        不涉及创建临时XML文件。

        :param mp4_filepath: MP4 文件的路径。
        :param tag_to_modify: 要修改的标准全局标签的名称 (例如 "COMMENT", "TITLE", "ARTIST").
        :param new_value_prefix: 新标签值的前缀，后面会附加唯一标识。
        :return: 布尔值，表示操作是否成功。
        """
        if not os.path.exists(mp4_filepath):
            print(f"错误: 文件未找到 - {mp4_filepath}")
            raise FileNotFoundError(f"文件未找到: {mp4_filepath}")

        # 检查 AtomicParsley 是否安装
        if not MP4TagModifier._check_atomicparsley_installed():
             print("错误: AtomicParsley 命令未找到。请确保已安装并在系统 PATH 中。")
             print("通常可以通过包管理器安装，例如 apt-get install atomicparsley (Debian/Ubuntu) 或 brew install atomicparsley (macOS)。")
             print("Windows 用户可能需要手动下载并添加到 PATH。")
             # 直接抛出 FileNotFoundError，以便调用者知道依赖未满足
             raise FileNotFoundError("AtomicParsley executable not found.")

        # 将输入的标签名转换为大写，以便在映射中查找
        tag_name_upper = tag_to_modify.upper()
        # 查找对应的 AtomicParsley 命令行参数
        ap_arg = AP_TAG_MAPPING.get(tag_name_upper)

        if ap_arg is None:
            print(f"错误: 不支持修改标签 '{tag_to_modify}'。AtomicParsley 只支持一组标准的标签。")
            print("目前支持的标签 (根据内部映射):", list(AP_TAG_MAPPING.keys()))
            return False # 返回 False 表示由于标签不支持而失败

        # 生成一个新的、唯一的值来修改标签
        unique_suffix = uuid.uuid4().hex[:8]
        new_tag_value = f"{new_value_prefix}{unique_suffix}"

        # 构建 AtomicParsley 命令
        cmd = [
            "AtomicParsley",
            str(mp4_filepath), # 确保文件路径是字符串，避免 WindowsPath 错误
            ap_arg,            # 例如 "--comment"
            new_tag_value,     # 新的标签值
            "--overWrite"      # 这个标志告诉 AtomicParsley 尝试原地修改文件
        ]

        print(f"执行命令: {' '.join([str(arg) for arg in cmd])}")

        try:
            # 执行命令
            # check=True 会在返回码非零时抛出 CalledProcessError
            # capture_output=True 捕获 stdout 和 stderr
            # text=True 解码 stdout/stderr 为文本
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')

            # 打印 AtomicParsley 的输出和错误信息 (如果有)
            if result.stdout: print(f"AtomicParsley 输出: {result.stdout.strip()}")
            if result.stderr: print(f"AtomicParsley 信息: {result.stderr.strip()}")

            # 如果 check=True 没有抛异常，且返回码为 0，则认为成功
            if result.returncode == 0:
                print(f"文件 '{str(mp4_filepath)}' 的标签 '{tag_to_modify.upper()}' 已成功修改为 '{new_tag_value}'。由于元数据被修改，文件的哈希值应该已改变。")
                return True
            else:
                 # 理论上因为 check=True 这个分支不会被常规错误达到
                 # 但作为安全措施，如果返回码非零但没抛异常，也视为失败
                 print(f"AtomicParsley 命令执行完成，返回码非零: {result.returncode}")
                 return False

        except FileNotFoundError:
            # 这里的 FileNotFoundError 主要捕获 AtomicParsley 命令本身找不到的情况
            # 尽管前面已经检查了一次，这里留着以防万一或捕获其他 PATH 问题
            print("错误: AtomicParsley 命令未找到。请确保已安装并在系统 PATH 中。")
            raise # 重新抛出异常，告知调用者问题所在
        except subprocess.CalledProcessError as e:
            # 捕获 AtomicParsley 执行过程中发生的错误
            print(f"AtomicParsley 命令执行失败，返回码: {e.returncode}")
            if e.stdout: print(f"STDOUT: {e.stdout.strip()}")
            if e.stderr: print(f"STDERR: {e.stderr.strip()}")
            print(f"请检查 AtomicParsley 是否支持修改 '{tag_to_modify}' 标签，或文件是否存在写入权限。")
            raise # 重新抛出异常，包含子进程的输出信息
        except Exception as e_gen:
            # 捕获其他意外的 Python 异常
            print(f"修改MP4标签时发生未知错误: {e_gen}")
            raise # 重新抛出异常

class MKVTagModifier:

    @staticmethod
    def _create_mkv_tags_xml(tags_to_set: dict) -> str:
        """
        从字典创建 Matroska 标签 XML 字符串。
        tags_to_set: 字典，例如 {'COMMENT': 'New comment', 'ARTIST': 'New Artist'}
        """
        if not tags_to_set:
            return ""

        root = ET.Element("Tags")
        for tag_name, tag_value in tags_to_set.items():
            if tag_value is None:
                continue

            tag_element = ET.SubElement(root, "Tag")
            targets_element = ET.SubElement(tag_element, "Targets")
            target_type_value_element = ET.SubElement(targets_element, "TargetTypeValue")
            target_type_value_element.text = "70"  # 70 for GLOBAL tags

            simple_element = ET.SubElement(tag_element, "Simple")
            name_element = ET.SubElement(simple_element, "Name")
            # 遵循 ffprobe 输出的标签名大小写，或者统一为大写（MKV标签名通常不区分大小写，但推荐大写）
            name_element.text = str(tag_name).upper()
            string_element = ET.SubElement(simple_element, "String")
            string_element.text = str(tag_value)

        return ET.tostring(root, encoding='unicode', xml_declaration=True)

    @staticmethod
    def _write_string_to_temp_file(content_string: str, suffix=".xml", encoding="utf-8") -> str:
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=suffix, encoding=encoding)
        temp_file.write(content_string)
        temp_file.close()
        return temp_file.name

    @staticmethod
    def change_mkv_hash_by_modifying_tag(mkv_filepath: str,
                                         tag_to_modify: str = "COMMENT",
                                         new_value_prefix: str = "ModifiedComment_") -> bool:
        """
        通过修改 MKV 文件的指定全局标签来改变其哈希值。
        使用 mkvpropedit 和临时XML文件进行就地修改。

        :param mkv_filepath: MKV 文件的路径。
        :param tag_to_modify: 要修改的全局标签的名称 (例如 "COMMENT", "TITLE", "ARTIST").
        :param new_value_prefix: 新标签值的前缀，后面会附加唯一标识。
        :return: 布尔值，表示操作是否成功。
        """
        if not os.path.exists(mkv_filepath):
            print(f"错误: 文件未找到 - {mkv_filepath}")
            raise FileNotFoundError(f"文件未找到: {mkv_filepath}")

        unique_suffix = uuid.uuid4().hex[:8]
        new_tag_value = f"{new_value_prefix}{unique_suffix}"

        tags_to_set = {
            tag_to_modify.upper(): new_tag_value # 使用大写标签名
        }
        # 如果要确保不覆盖其他标签，而是合并，需要更复杂的逻辑：
        # 1. 先用 mkvmerge -J file.mkv 导出所有标签为JSON
        # 2. 修改JSON中的特定标签
        # 3. 将修改后的JSON转回MKV标签XML格式 (mkvmerge --tags old_tags.json new_tags.xml 可以帮忙，但这是个多步骤)
        # 4. 用 mkvpropedit --tags all:new_tags.xml 应用
        # 为了简单地达到“改变哈希”的目的，直接设置一个标签（会覆盖该标签，但其他标签不受影响，因为XML只包含这一个）
        # 或者，如果你知道原始值，可以读取它，附加后缀，然后设置。
        # 为了纯粹改变哈希，设置一个全新的值给一个标签（如 COMMENT）是最简单的。
        # mkvpropedit 的 --tags all:your_file.xml 会将 your_file.xml 中的标签与现有标签合并。
        # 如果 your_file.xml 中有与现有标签同名的标签，则现有标签的值会被更新。
        # 如果 your_file.xml 中有新的标签，则会被添加。
        # 原有的、但在 your_file.xml 中未提及的标签将保持不变。

        xml_content = MKVTagModifier._create_mkv_tags_xml(tags_to_set)
        if not xml_content:
            print("未能生成XML标签内容。")
            return False

        temp_xml_file_path = None
        try:
            temp_xml_file_path = MKVTagModifier._write_string_to_temp_file(xml_content)

            cmd = [
                "mkvpropedit",
                mkv_filepath,
                "--tags", f"all:{temp_xml_file_path}" # 'all:' 表示合并/更新所有全局标签
            ]

            print(f"执行命令: {' '.join(cmd)}")
            print(f"使用临时XML标签文件: {temp_xml_file_path} 内容:\n{xml_content}")


            result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
            if result.stderr: print(f"mkvpropedit 信息: {result.stderr.strip()}")
            if result.stdout: print(f"mkvpropedit 输出: {result.stdout.strip()}")
            print(f"文件 '{mkv_filepath}' 的标签 '{tag_to_modify.upper()}' 已成功修改为 '{new_tag_value}'。哈希值应该已改变。")
            return True
        except FileNotFoundError:
            print("错误: mkvpropedit 命令未找到。请确保 MKVToolNix 已安装并在系统 PATH 中。")
            raise
        except subprocess.CalledProcessError as e:
            print(f"mkvpropedit 命令执行失败，返回码: {e.returncode}")
            if e.stdout: print(f"STDOUT: {e.stdout.strip()}")
            if e.stderr: print(f"STDERR: {e.stderr.strip()}")
            raise
        except Exception as e_gen:
            print(f"修改MKV标签时发生未知错误: {e_gen}")
            raise
        finally:
            if temp_xml_file_path and os.path.exists(temp_xml_file_path):
                try:
                    os.remove(temp_xml_file_path)
                    print(f"已删除临时XML文件: {temp_xml_file_path}")
                except OSError as e_remove:
                    print(f"删除临时XML文件 {temp_xml_file_path} 失败: {e_remove}")
class VideoMetadataEditor:
    # 方法1：直接转换（推荐）
    unc_path = Path(r"\\FNOS\downloads")
    download_base_path =unc_path


    @staticmethod
    def modify_metadata(input_filename):

        """
               统一修改MP4/MKV的元数据
               所有文件路径都基于 download_base_path
               """
        # 确保 downloads 目录存在
        print(f'正在编辑：{input_filename}')
        VideoMetadataEditor.download_base_path.mkdir(exist_ok=True)
        input_filename=input_filename.lstrip('/')
        # 构建完整输入/输出路径
        input_path = VideoMetadataEditor.download_base_path / input_filename
        # 检查输入文件是否存在
        if not input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")

        # 根据格式调用对应方法
        if input_path.suffix.lower() == '.mp4':
            random.Random()
            unique_suffix = uuid.uuid4().hex[:8]
            try:
                FFmpegProcessor.modify(str(input_path),title=f'1{unique_suffix}',artist='llll')
            except Exception as e:
                raise e
        elif input_path.suffix.lower() == '.mkv':
            # VideoMetadataEditor._modify_mkv_mkvpropedit(input_filename, title, artist)
            MKVTagModifier.change_mkv_hash_by_modifying_tag(mkv_filepath=str(input_path),tag_to_modify='t',new_value_prefix='1')
        else:
            raise ValueError("仅支持 MP4/MKV 格式")
        print(f'已成功编辑：{input_filename}')


    @staticmethod
    def _modify_mp4(input_path, output_path, title, artist):
        """处理MP4文件"""
        video = MP4('')
        if title: video["\xa9nam"] = [title]  # 标题
        if artist: video["\xa9ART"] = [artist]  # 艺术家
        video.save(output_path)

    @staticmethod
    def _modify_mkv(input_path, output_path, title, artist):
        """处理MKV文件（通过FFmpeg），确保输出文件不存在"""

        # 检查输出路径是否存在，若存在则删除
        if os.path.exists(output_path):
            os.remove(output_path)  # 删除已存在的文件

        # 构建FFmpeg命令
        metadata_args = []
        if title: metadata_args.extend(["-metadata", f"title={title}"])
        if artist: metadata_args.extend(["-metadata", f"artist={artist}"])

        cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-map", "0",  # 保留输入文件的所有流
            *metadata_args,
            "-c", "copy",  # 直接复制流（不重新编码）
            str(output_path)
        ]

        # 执行FFmpeg命令
        subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)

    @staticmethod
    def _modify_media_metadata(input_path, title, artist):
        """修改媒体文件（如MKV或MP4）的元数据，修改后覆盖原始文件（支持NAS路径）"""
        import os
        import tempfile
        import subprocess
        import shutil

        # 获取文件扩展名
        _, ext = os.path.splitext(input_path)

        # 创建临时文件（确保唯一性）
        temp_output_path = None
        try:
            temp_output_path = os.path.join(
                tempfile.gettempdir(),
                f"temp_{os.getpid()}_{next(tempfile._get_candidate_names())}{ext}"
            )

            # 构建FFmpeg命令
            metadata_args = []
            if title:
                metadata_args.extend(["-metadata", f"title={title}"])
            if artist:
                metadata_args.extend(["-metadata", f"artist={artist}"])

            cmd = [
                "ffmpeg",
                "-i", str(input_path),
                "-map", "0",  # 保留所有流
                "-map_metadata", "-1",  # 丢弃原始metadata
                *metadata_args,
                "-c", "copy",  # 不重新编码
                str(temp_output_path)
            ]


            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='ignore'
            )
            if result.stderr:
                print(f"FFmpeg警告: {result.stderr}")
            # 替换原始文件（跨设备安全操作）
            shutil.move(temp_output_path, input_path)

        except subprocess.CalledProcessError as e:


            print(f"FFmpeg执行失败{e.stderr}")

            raise  # 重新抛出异常

        except Exception as e:
            print(f"未知错误: {e}")

            raise

        finally:
            # 确保临时文件被删除（如果未被移动）
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)

    @staticmethod
    def _modify_mkv_mkvpropedit(input_path, title, artist):  # 注意这里不需要 output_path
        """处理MKV文件元数据（通过 mkvpropedit，就地修改）"""

        # mkvpropedit 直接修改输入文件
        # 构建 mkvpropedit 命令
        args = []
        if title:
            args.extend(["--edit", "info", "--set", f"title={title}"])
        if artist:
            args.extend(["--edit", "info", "--set", f"artist={artist}"])
            # 或者针对 track 的元数据:
            # args.extend(["--edit", "track:v1", "--set", f"name={title}"]) # 修改视频轨道的名称
            # args.extend(["--edit", "track:a1", "--set", f"name=Artist Name - Song Title"]) # 修改音频轨道的名称

        if not args:
            print("没有提供元数据进行修改 (MKV - mkvpropedit)")
            return

        cmd = [
            "mkvpropedit",
            str(input_path),
            *args
        ]

        print(f"执行 mkvpropedit 命令: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"mkvpropedit STDOUT: {result.stdout}")
            print(f"mkvpropedit STDERR: {result.stderr}")
            print(f"MKV元数据使用 mkvpropedit 修改成功: {input_path}")
        except subprocess.CalledProcessError as e:
            print(f"mkvpropedit 命令执行失败，返回码: {e.returncode}")
            print(f"mkvpropedit STDOUT: {e.stdout}")
            print(f"mkvpropedit STDERR: {e.stderr}")
            raise
        except FileNotFoundError:
            print("错误: mkvpropedit 命令未找到。请确保 mkvtoolnix 已安装并在系统PATH中。")
            raise

    @staticmethod
    def modify_hash(input_path):
        input_path = VideoMetadataEditor.download_base_path / input_path
        ByteModifier.append_random_byte(str(input_path))

class ByteModifier:
    @staticmethod
    def append_random_byte(filepath):
        """向文件末尾追加一个随机字节（文件不存在则抛出FileNotFoundError）"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")

        with open(filepath, 'ab') as f:
            f.write(os.urandom(1))  # 写入1个随机字节


class FFmpegProcessor:
    @staticmethod
    def _get_temp_output_path(input_path: str) -> str:
        """生成临时输出路径"""
        _, ext = os.path.splitext(input_path)
        return os.path.join(
            tempfile.gettempdir(),
            f"temp_{os.getpid()}_{next(tempfile._get_candidate_names())}{ext}"
        )

    @staticmethod
    def _build_ffmpeg_command(
            input_path: str,
            output_path: str,
            extra_args: Optional[List[str]] = None,
            metadata: Optional[Dict[str, str]] = None
    ) -> List[str]:
        """构建FFmpeg命令基础结构"""
        cmd = ["ffmpeg", "-i", input_path]

        # 添加元数据参数
        if metadata:
            for key, value in metadata.items():
                cmd.extend(["-metadata", f"{key}={value}"])

        # 添加额外参数
        if extra_args:
            cmd.extend(extra_args)

        # 输出文件路径
        cmd.append(output_path)
        return cmd

    @staticmethod
    def execute_ffmpeg(
            input_path: str,
            output_path: Optional[str] = None,
            *,
            in_place: bool = False,
            extra_args: Optional[List[str]] = None,
            metadata: Optional[Dict[str, str]] = None,
            overwrite: bool = False
    ) -> str:
        """
        执行FFmpeg命令的高级封装

        参数:
            input_path: 输入文件路径
            output_path: 输出文件路径（None时自动生成；若in_place=True，则作为临时文件路径）
            in_place: 是否原地修改文件（会覆盖原文件）
            extra_args: 额外的FFmpeg参数
            metadata: 元数据字典（如 {'title':'...', 'artist':'...'}）
            overwrite: 是否覆盖已存在的输出文件

        返回:
            最终输出文件路径
        """
        # 验证输入文件
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"输入文件不存在: {input_path}")

        temp_output_path = None
        final_output_path = None

        try:
            # 处理输出路径逻辑
            if in_place:
                # 如果 in_place=True，优先使用 output_path 作为临时文件路径
                temp_output_path = output_path if output_path else FFmpegProcessor._get_temp_output_path(input_path)
                actual_output_path = temp_output_path
                final_output_path = input_path  # 最终目标始终是 input_path
            else:
                # 非 in_place 模式，直接使用 output_path（或自动生成）
                actual_output_path = output_path if output_path else FFmpegProcessor._get_temp_output_path(input_path)
                final_output_path = actual_output_path
                # 检查是否覆盖已存在文件
                if os.path.exists(actual_output_path) :
                    if overwrite:
                        os.remove(actual_output_path)
                    else:
                        raise FileExistsError(f"输出文件已存在: {actual_output_path}")

            # 构建命令
            cmd = FFmpegProcessor._build_ffmpeg_command(
                input_path=str(input_path),
                output_path=str(actual_output_path),
                extra_args=extra_args,
                metadata=metadata
            )

            # 执行命令
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='ignore'
            )

            if result.stderr:
                print(f"FFmpeg警告: {result.stderr}")

            # 处理输出文件（仅 in_place 时需要移动）
            if in_place:
                shutil.move(temp_output_path, input_path)

            return final_output_path

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg执行失败: {e.stderr}") from e
        except Exception as e:
            raise
        finally:
            # 清理临时文件（仅限自动生成的临时文件）
            if temp_output_path and temp_output_path != output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    @staticmethod
    def modify(input_path,title:str="1",artist:str="2"):
        try:
            # 示例1：修改元数据（原地修改）
            FFmpegProcessor.execute_ffmpeg(
                input_path=str(input_path),
                in_place=True,
                extra_args=["-map", "0", "-map_metadata", "-1", "-c", "copy"],
                metadata={"title": title, "artist": artist},
                overwrite=True
            )

        except Exception as e:
            try:
                FFmpegProcessor.modify_export_mp4_to_mov(input_path=input_path, title=title, artist=artist)
            except Exception as e:
                raise

    @staticmethod
    def modify_export_mp4_to_mov(input_path,title:str="1",artist:str="2"):
        '''
        让ffmpeg导出为mov格式，再通过该后缀名改回mp4
        :param input_path:
        :param title:
        :param artist:
        :return:
        '''
        try:
            input_path=Path(input_path)
            output_path=input_path.parent / f"temp-{input_path.stem}.mov"
            # 示例1：修改元数据（原地修改）
            FFmpegProcessor.execute_ffmpeg(
                input_path=str(input_path),
                in_place=False,
                extra_args=["-map", "0", "-map_metadata", "-1", "-c", "copy"],
                metadata={"title": title, "artist": artist},
                output_path=str(output_path),
                overwrite=True
            )
            shutil.move(output_path, input_path)



        except Exception as e:
            raise


def modify_hash(retry:bool):
    """

    :param retry: 尝试编辑 上次编辑失败的视频
    :return:
    """
    with Session(engine) as session:
        resources=  session.exec(select(Resource).where(Resource.has_detect_risk==True)).all()
        for resource in resources:
            base_path=resource.storage_path
            iteration=True
            need_iteration_risk_file=[f['file_name'] for f in resource.risk_file_handle]

            while iteration:
                iteration=False
                for file_handle in resource.risk_file_handle:
                    if file_handle['status']=='downloaded' or file_handle['status']=='modify_error' and file_handle['file_name'] in need_iteration_risk_file:
                        need_iteration_risk_file.remove(file_handle['file_name'])
                        input_filename =f"{base_path}/{file_handle['file_name']}"
                        output_filename =f"{base_path}/modified-{file_handle['file_name']}"
                        try:
                            # VideoMetadataEditor.modify_metadata(input_filename=input_filename, output_filename=output_filename,artist='hhh',is_cover=True)
                            VideoMetadataEditor.modify_metadata(input_filename,)
                            file_handle['status']='modified'

                        except Exception as e:
                            file_handle['status']='modify_error'
                            print(e)
                        try:
                            flag_modified(resource, "risk_file_handle")
                            session.add(resource)
                            session.commit()
                            session.refresh(resource)
                            iteration=True

                            break
                        except Exception as e:
                            print(e)



def main():
    # modify_hash(True)
    VideoMetadataEditor.modify_hash(r'\\FNOS\downloads\A.Better.Life.S01E28.2025.2160p.WEB-DL.H265.AAC_2.mp4')


# 使用示例
if __name__ == "__main__":
   main()
