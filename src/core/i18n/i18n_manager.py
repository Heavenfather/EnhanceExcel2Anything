import hashlib
import core.utils.utils
from core.utils.utils import is_contains_chinese
from pathlib import Path


class I18NManager:
    def __init__(self):
        self.root_dir = Path('localization')
        # 首包包含的所有多语言
        self.master_file = self.root_dir / f'master{core.utils.utils.LANG_SUFFIX}'
        self.__ensure_dir()
        self.master_i18 = self.parse_file(self.master_file)

    def __ensure_dir(self):
        self.root_dir.mkdir(parents=True, exist_ok=True)
        (self.root_dir / 'patch').mkdir(exist_ok=True)

    def __generate_key(self, table_name, col_name, value):
        """生成多语言唯一的哈希值"""
        unique_str = f'{table_name}_{col_name}_{value}'
        key = hashlib.sha256(unique_str.encode()).hexdigest()[:4]
        return f'{table_name}/{key}'

    def update_raw_master(self, table_name, col_name, value):
        """更新配置多语言信息"""
        if not is_contains_chinese(value):
            return None
        key = self.__generate_key(table_name, col_name, value)
        if self.master_i18.get('Raw') is None:
            self.master_i18['Raw'] = {}
        self.master_i18['Raw'][key] = value
        return key

    def parse_file(self, file_path: Path) -> dict:
        """解析多语言文件"""
        sections = {}
        current_section = None
        if file_path.exists():
            for line in file_path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line.startswith('['):
                    current_section = line[1:-1]
                    sections[current_section] = {}
                elif '=' in line and current_section:
                    key, value = line.split('=', 1)
                    sections[current_section][key.strip()] = value.strip()
        return sections

    def write_file(self, file_path: Path, data: dict):
        """写入多语言文件"""
        contents = []
        for section, items in data.items():
            contents.append(f'[{section}]')
            for key, value in items.items():
                contents.append(f'{key}={value}')
        file_path.write_text('\n'.join(contents), encoding='utf-8')

    def write_master_file(self):
        """写入配置多语言"""
        self.write_file(self.master_file, self.master_i18)
