import json
from pathlib import Path

import core.utils.utils


class CacheSystem:
    def __init__(self, input_dir):
        self.input_dir = input_dir

        # 创建缓存目录
        self.cache_dir = "./__cache__"
        self.cache_file = Path(self.cache_dir) / '__man_what_can_i_say.cache'
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        self.current_files = {}
        self.changed_list = []
        self.__init_cache_file()

    def is_modify_file(self, file_md5) -> bool:
        return file_md5 in self.changed_list

    def save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.current_files, f, indent=2)

    def __init_cache_file(self):
        """遍历所有文件并记录修改时间"""
        folder = Path(self.input_dir)
        for file_path in folder.glob('**/*.xlsx'):
            if file_path.name.startswith('~$'):
                continue
            if file_path.is_file():
                mtime = file_path.stat().st_mtime
                file_hash = core.utils.utils.get_file_mash(file_path)
                self.current_files[file_hash] = mtime

        cache_data = {}
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error reading cache file: {e}")

        # 比较差异 文件哈希和时间戳校验
        for md5, mtime in self.current_files.items():
            if cache_data.get(md5, -1) != mtime:
                self.changed_list.append(md5)
