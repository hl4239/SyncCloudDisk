from pydantic import BaseModel, Field
from typing import Optional, List


class CloudFile(BaseModel):
    fid: Optional[str] = Field(None, description="文件或目录的唯一ID")
    file_name: Optional[str] = Field(None, description="文件或目录名称")
    file_type: Optional[int] = Field(None, description="类型: 0=目录, 1=文件")
    pdir_path:Optional[str]=Field(None,description='父目录的绝对路径')
    pdir_fid: Optional[str] = Field(None, description="父目录ID")
    children: Optional[List['CloudFile']] = Field(None, description="如果是目录，包含子文件或子目录")
    normalized_name: Optional[str] = Field(None, description='剧集标准化后的名字', pattern=r'^(\d{2}|\d{2}-\d{2})$')
    normalize_invalid:bool=False
    def normalize_name(self, normalized_name: Optional[str] = None):
        """
        对normalized_name赋值并不是file_name
        :param normalized_name:
        :return:
        """
        if normalized_name is not None:
            self.normalized_name = normalized_name

    def set_normalize_invalid(self):
        self.normalize_invalid = True

    def is_dir(self) -> bool:
        return self.file_type == 0

    def is_movie_file(self) -> bool:
        return self.file_type == 1 and self.file_name.lower().endswith(('.mp4', '.mkv','.torrent'))

    def update_cloud_field(self,cloud_file:'CloudFile'):
        """
        更新网盘相关的字段
        :return:
        """
        if cloud_file is None:
            return
        if cloud_file.fid is not None:
            self.fid = cloud_file.fid
        if cloud_file.file_type is not None:
            self.file_type = cloud_file.file_type
        if cloud_file.pdir_fid is not None:
            self.pdir_fid = cloud_file.pdir_fid

        if cloud_file.children is not None:
            if self.children is  None:
                self.children = cloud_file.children
            else:
                cloud_file_names=[f.file_name for f in cloud_file.children]

                cloud_file_name_maps={
                    f.file_name:f
                    for f in cloud_file.children
                }
                self_files_maps={
                    f.file_name:f
                    for f in self.children
                }
                # 删除self中多余的child
                self.children = list(filter(lambda x: x.file_name  in cloud_file_names, self.children))




                self_file_names=[f.file_name for f in self.children]
                # 对self已存在的递归更新
                exist_file_names=list(set(self_file_names)&set(cloud_file_names))
                for f in self_file_names:
                    self_child=self_files_maps[f]
                    cloud_child=cloud_file_name_maps[f]
                    self_child.update_cloud_field(cloud_child)



                # 添加self不存在的child
                for_add_file_names=list(set(cloud_file_names)-set(self_file_names))

                for f in for_add_file_names:
                    self.children.append(cloud_file_name_maps[f])

    def traverse(
            self,
            path: str,
            create_missing:bool=False,
            leaf_cloud_file:Optional['CloudFile']=None
    ) :
        """
        遍历指定的路径


        :param path: 要遍历的路径，如 '/dir1/dir2/dir3'
        :param create_missing:创建路径中间不存在的目录
        :param leaf_cloud_file:对叶节点网盘相关的字段更新
        :return: 如果找到返回对象 否则返回None
        """
        root=self
        parts = [part for part in path.split('/') if part]
        if not parts:
            return root

        current = root
        current_path = []

        for part in parts:
            current_path.append(part)
            full_path = '/' + '/'.join(current_path)

            # 查找子节点
            found = None
            if current.children:
                for child in current.children:
                    if child.file_name == part:
                        found = child
                        break
            if not found:
                if not create_missing:
                    return None

                # 创建缺失的目录节点
                found = CloudFile(
                    fid=None,
                    file_name=part,
                    file_type=0,
                    pdir_path='/' + '/'.join(current_path[:-1]) if len(current_path) > 1 else '/',
                    pdir_fid=None,

                    children=None
                )
                if current.children is None:
                    current.children = []
                current.children.append(found)
            found.pdir_path='/' + '/'.join(current_path[:-1]) if len(current_path) > 1 else '/'
            current = found

        # 对叶节点更新
        if leaf_cloud_file is not None:
            current.update_cloud_field(leaf_cloud_file)

        return current

    def flatten(self) -> List['CloudFile']:
        """
        拍平自身和所有子节点，返回 CloudFile 对象列表
        """
        files = [self]
        if self.children:
            for child in self.children:
                files.extend(child.flatten())
        return files




    def find_by_name(self, name: str) -> Optional['CloudFile']:
        if self.file_name == name:
            return self
        if self.children:
            for child in self.children:
                result = child.find_by_name(name)
                if result:
                    return result
        return None

class ShareFile(CloudFile):
    pass

class QuarkShareFile(ShareFile):
    share_fid_token: Optional[str] = Field(None, description="分享标识")

class ShareParseInfo(BaseModel):
    share_link :Optional[str]=Field(None,description='分享链接')
    passcode: Optional[str] = Field(None)
    root:Optional[ShareFile]=Field(None)

    is_valid:Optional[bool]=Field(None,description='判断链接是否有效')

class QuarkShareParseInfo(ShareParseInfo):
    pdir_fid: Optional[str] = Field(None)
    pwd_id: Optional[str] = Field(None)
    stoken:Optional[str] = Field(None)



