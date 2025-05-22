import asyncio
import json
import re

from QuarkDisk import ParseQuarkShareLInk, QuarkDisk


class QuarkShareDirTree:
    def __init__(self, share_link: str):
        self.tree = None
        self.share_link = share_link
        self.ParseQuarkShareLInk = None
        self.current_max_deep = -1  # Tracks the max_deep the current tree was built/expanded with

    async def _traverse_dir(self, current_deep: int, max_deep: int, fid='0'):
        # This message format is crucial for incremental parsing
        max_deep_reached_msg_template = "请增加max_deep以查看此目录,current_deep={cd},max_deep={md}"

        if current_deep > max_deep:
            # print(f"DEBUG: _traverse_dir for fid={fid}, current_deep={current_deep} > max_deep={max_deep}. Returning message.")
            return max_deep_reached_msg_template.format(cd=current_deep, md=max_deep)

        # print(f"DEBUG: _traverse_dir for fid={fid}, current_deep={current_deep}, max_deep={max_deep}")
        file_detail_list_response = await self.ParseQuarkShareLInk.ls_dir(fid)
        if not file_detail_list_response or 'list' not in file_detail_list_response:
            raise Exception(f"Warning: ls_dir for fid {fid} returned an unexpected response,可能为链接已失效: {file_detail_list_response}")

        file_detail_list = file_detail_list_response['list']
        if len(file_detail_list) == 0:
            return '该目录为空'

        result_detail_list = []
        for file_detail in file_detail_list:
            node_data = {
                'fid': file_detail['fid'],
                'file_name': file_detail['file_name'],
                'file_type': file_detail['file_type'],
                'pdir_fid': file_detail['pdir_fid'],
                'share_fid_token': file_detail['share_fid_token'],
            }
            if node_data['file_type'] == 0:  # 0 typically means directory
                node_data['child'] = await self._traverse_dir(current_deep + 1, max_deep, node_data['fid'])
            result_detail_list.append(node_data)
        return result_detail_list

    async def _expand_tree_incrementally(self, node_to_expand, depth_of_node_to_expand: int, new_max_deep: int):
        """
        Recursively expands parts of the tree that were previously limited by max_deep.
        :param node_to_expand: The current dictionary node in the tree to examine/expand.
        :param depth_of_node_to_expand: The depth of node_to_expand in the overall tree.
        :param new_max_deep: The new maximum depth to parse to.
        """
        if not isinstance(node_to_expand, dict) or node_to_expand.get('file_type') != 0:  # Only expand directories
            return

        children_content = node_to_expand.get('child')
        # Regex to parse the "max_deep reached" message
        max_deep_msg_regex = r"请增加max_deep以查看此目录,current_deep=(\d+),max_deep=(\d+)"

        if isinstance(children_content, str):
            match = re.fullmatch(max_deep_msg_regex, children_content)
            if match:
                msg_current_deep = int(
                    match.group(1))  # Depth at which original traversal stopped for this node's children
                # msg_original_max_deep = int(match.group(2)) # Original max_deep that caused the stop

                # If the depth where it previously stopped is now within the new_max_deep, we can expand this node's children
                if msg_current_deep <= new_max_deep:
                    print(
                        f"  Incrementally expanding children of '{node_to_expand.get('file_name')}' (fid: {node_to_expand['fid']}). Original stop depth for children: {msg_current_deep}, new_max_deep: {new_max_deep}")

                    # Re-fetch children for this node, starting traversal from where it left off (msg_current_deep)
                    node_to_expand['child'] = await self._traverse_dir(
                        current_deep=msg_current_deep,  # This is the depth of the children being fetched
                        max_deep=new_max_deep,
                        fid=node_to_expand['fid']
                    )
                    # After expanding this node, its new children (if they are directories) might also need expansion.
                    # The _traverse_dir call above would have placed new "max_deep_reached" messages if applicable.
                    # So, we need to recursively call _expand_tree_incrementally on these newly fetched children.
                    if isinstance(node_to_expand['child'], list):
                        for newly_fetched_child_node in node_to_expand['child']:
                            # The newly_fetched_child_node itself is at depth 'msg_current_deep'.
                            await self._expand_tree_incrementally(newly_fetched_child_node, msg_current_deep,
                                                                  new_max_deep)
        elif isinstance(children_content, list):
            # If children are already a list (not a message string), recurse into them
            # to see if their sub-branches need expansion.
            # The children of 'node_to_expand' are at depth 'depth_of_node_to_expand + 1'.
            child_depth = depth_of_node_to_expand + 1
            for child_node in children_content:
                await self._expand_tree_incrementally(child_node, child_depth, new_max_deep)

    async def parse(self, max_deep: int = 1,refresh: bool = False):
        if refresh:
            self.tree=None
        if self.ParseQuarkShareLInk is None:

            self.ParseQuarkShareLInk = await QuarkDisk.parse_share_url(self.share_link)

        if self.tree is None:
            print(f"Performing initial parse with max_deep={max_deep}...")
            self.tree = {
                'file_name': '/',
                'fid': '0',
                'file_type': 0,
                'pdir_fid': None,
                'share_fid_token': None,
                # Initial traversal for root's children starts at current_deep=0
                'child': await self._traverse_dir(current_deep=0, max_deep=max_deep, fid='0'),
            }
            self.current_max_deep = max_deep
        elif max_deep > self.current_max_deep:

            # The root node 'self.tree' is at an effective depth of -1 for its children to be at depth 0.
            await self._expand_tree_incrementally(self.tree, -1, max_deep)
            self.current_max_deep = max_deep  # Update to the new, greater max_deep
        elif max_deep <= self.current_max_deep:
            pass
            # The tree data is already sufficient or deeper than requested.
            # We don't prune the tree if max_deep is smaller; we just don't fetch more.
            # If you need to reflect a smaller max_deep in ls_dir, that would be a display-time adjustment.

    def _print_tree_recursive(self, node, prefix="", is_last=True, level=0) -> list[str]:
        """
        Recursive helper to generate lines for the tree.
        Returns a list of strings, where each string is a line in the tree.
        """
        lines = []
        if not node:
            return lines

        if not isinstance(node, dict):  # Handle string children like "该目录为空" or the max_deep message
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{node}")
            return lines

        connector = "└── " if is_last else "├── "
        name = node.get('file_name', 'Unknown Node')
        suffix = '/' if node.get('file_type') == 0 else ''
        lines.append(f"{prefix}{connector}{name}{suffix}")

        children = node.get('child')
        if isinstance(children, list):
            new_prefix = prefix + ("    " if is_last else "│   ")
            for i, child_node in enumerate(children):
                is_last_child_in_list = (i == len(children) - 1)
                lines.extend(self._print_tree_recursive(child_node, new_prefix, is_last_child_in_list, level + 1))
        elif isinstance(children, str):  # Child is a message string
            new_prefix = prefix + ("    " if is_last else "│   ")
            lines.append(f"{new_prefix}└── {children}")  # Display the message as a child item

        return lines

    def ls_dir(self) -> str:
        """
        画出完整目录树
        :return: A string representation of the directory tree.
        """
        if not self.tree:
            return "Tree has not been parsed yet. Call parse() first."

        output_lines = []
        output_lines.append(self.tree.get('file_name', '/'))  # Root directory name

        children = self.tree.get('child')
        if isinstance(children, list):
            for i, child_node in enumerate(children):
                is_last_child = (i == len(children) - 1)
                output_lines.extend(self._print_tree_recursive(child_node, "", is_last_child, level=0))
        elif isinstance(children, str):  # Root's child itself is a message
            output_lines.append(f"└── {children}")
        elif children is None:  # Should ideally not happen if parsed correctly
            output_lines.append("└── (目录信息不可用或为空)")

        return "\n".join(output_lines)

    def get_node_info(self, path: str):
        if not self.tree:
            print("Tree has not been parsed yet. Call parse() first.")
            return None

        if not path or path == '/':
            return self.tree

        components = [comp for comp in path.strip('/').split('/') if comp]
        if not components:
            return self.tree

        current_node = self.tree
        for component in components:
            if not isinstance(current_node, dict) or 'child' not in current_node:
                return None

            children = current_node.get('child')
            if not isinstance(children, list):  # Path leads into a branch that's a string message
                return None

            found_next_node = False
            for child_node in children:
                if isinstance(child_node, dict) and child_node.get('file_name') == component:
                    current_node = child_node
                    found_next_node = True
                    break

            if not found_next_node:
                return None

        return current_node

    async def close_(self):
        if self.ParseQuarkShareLInk:
            await self.ParseQuarkShareLInk.close()
            # self.ParseQuarkShareLInk = None # Reset to allow re-initialization if parse is called again.
            # self.tree = None # Also reset tree state if closing means full reset
            # self.current_max_deep = -1
            print("ParseQuarkShareLInk instance has been closed.")
        # To fully support re-parsing after close, you might want to uncomment the resets above,
        # or ensure parse() re-initializes ParseQuarkShareLInk if it's None.
        # The current parse() logic re-initializes ParseQuarkShareLInk if it's None.

    quark_share_tree_dict = {}

    @staticmethod
    def get_quark_share_tree(share_link: str):
        quark_share_tree = QuarkShareDirTree.quark_share_tree_dict.get(share_link, None)
        if quark_share_tree is None:
            quark_share_tree = QuarkShareDirTree(share_link)
            QuarkShareDirTree.quark_share_tree_dict.update({share_link: quark_share_tree})
        return quark_share_tree

    @staticmethod
    def get_video_node_info_from_tree(tree_node) -> list[dict]:
        """
        遍历给定的树节点，收集所有 mp4 或 mkv 文件的信息。
        :param tree_node: 目录树的根节点或子节点。
        :return: 所有视频文件节点的列表。
        """
        result = []

        def traverse(node):
            if not isinstance(node, dict):
                return

            # 判断当前节点是否是视频文件
            if node.get('file_type') != 0:
                file_name = node.get('file_name', '')
                if file_name.endswith('.mp4') or file_name.endswith('.mkv'):
                    result.append(node)
            else:  # 是文件夹，则递归遍历其子节点
                children = node.get('child')
                if isinstance(children, list):
                    for child in children:
                        traverse(child)

        traverse(tree_node)
        return result

    def get_video_node_info(self) -> list[dict]:
        """
        遍历整个目录树，获取所有 mp4/mkv 文件的节点信息。
        :return: 包含视频文件节点的列表。
        """
        if not self.tree:
            print("Tree has not been parsed yet. Call parse() first.")
            return []

        return self.get_video_node_info_from_tree(self.tree)
    @staticmethod
    async def close():
        for i in QuarkShareDirTree.quark_share_tree_dict.values():
            await i.close_()
async def main():
    quark_share_tree=QuarkShareDirTree('https://pan.quark.cn/s/b11805926008')
    await quark_share_tree.parse(max_deep=1)
    await quark_share_tree.parse(max_deep=2)

    await quark_share_tree.close()
if __name__ == '__main__':
    asyncio.run(main())