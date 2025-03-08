import os
from typing import List
from core.models import SheetConfig, FieldMeta
from core.utils.exceptions import ConfigError
from abc import ABC, abstractmethod
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from core.utils.utils import timer_decorator
import threading
import core.utils


class Validator(ABC):
    @abstractmethod
    def validate(self, all_configs: List[SheetConfig]) -> list[str]:
        pass


class ExportNameValidator(Validator):
    """导出文件名校验"""

    def validate(self, all_configs: List[SheetConfig]):
        # 校验命名是否符合规范 是否含有特殊字段等
        errors = []
        name_map = {}
        for config in all_configs:
            result, msg = core.utils.utils.validate_str_legal(config.export_name)
            if result is False:
                errors.append(f'{msg} 导出名称: {config.export_name}')
            map_config = name_map.get(config.export_name, None)
            if map_config and map_config.source_file_md5 != config.source_file_md5:
                errors.append(
                    f'导出名称: {config.export_name} 重复,不允许跨Excel配置:[{config.source_file}] vs [{map_config.source_file}]')
            else:
                name_map[config.export_name] = config
        return errors


class RepeatValidator(Validator):
    """重复值校验"""

    def validate(self, all_configs: List[SheetConfig]) -> list[str]:
        errors = []
        lock = threading.Lock()  # 线程安全锁

        def process_config(config: SheetConfig):
            config_error = []
            # 是否有CheckRepeat标签
            repeat_fields = [
                field_name for field_name, field_meta in config.fields.items() if 'CheckRepeat' in field_meta.checks
            ]
            if not repeat_fields:
                return

            # 值存在检查字典
            seen = defaultdict(set)
            # 值重复记录器
            duplicates = defaultdict(set)

            # 遍历所有行记录重复值
            for row in config.rows_values:
                for field_name in repeat_fields:
                    value = row.get(field_name)
                    if value is None:
                        continue
                    if value in seen[field_name]:
                        duplicates[field_name].add(value)
                    else:
                        seen[field_name].add(value)
            # 生成错误信息
            for field_name, values in duplicates.items():
                for value in values:
                    error_msg = f'[{config.source_file}:{config.export_name}] 字段{field_name} 值重复: {value}'
                    config_error.append(error_msg)

            with lock:
                errors.extend(config_error)

        with ThreadPoolExecutor(max_workers=self.__auto_scale_workers(len(all_configs))) as executor:
            executor.map(process_config, all_configs)

        return errors

    def __auto_scale_workers(self, count):
        """根据CPU核数自动计算最优的线程数"""
        base = min(4, (os.cpu_count() or 1))
        return min(base + count // 5, 16)


class LinkValidator(Validator):
    """链接值校验"""

    def __init__(self):
        self.__cache = {}
        self.__lock = threading.Lock()

    def validate(self, all_configs: List[SheetConfig]) -> list[str]:
        errors = []
        self.__preload_target_values(all_configs)
        error_lock = threading.Lock()
        with ThreadPoolExecutor(max_workers=self.__auto_scale_workers(len(all_configs))) as executor:
            futures = []
            for config in all_configs:
                futures.append(executor.submit(self.__process_config, config, all_configs, errors, error_lock))
            _ = [f.result() for f in futures]

        return errors

    def __auto_scale_workers(self, count):
        """根据CPU核数自动计算最优的线程数"""
        base = min(4, (os.cpu_count() or 1))
        return min(base + count // 5, 16)

    def __process_config(self, config: SheetConfig, all_configs: List[SheetConfig], errors: List[str], error_lock):
        """处理单个配置表"""
        # 收集需要校验的字段
        link_fields = [
            (meta, check)
            for field_name, meta in config.fields.items()
            for check in meta.checks
            if check.startswith('CheckLink')
        ]

        # 当前表没有标签，直接跳过
        if not link_fields:
            return

        for row in config.rows_values:
            for meta, check_tag in link_fields:
                self.__validate_row_field(row, meta, check_tag, config, errors, error_lock)

    def __validate_row_field(self, row: dict, meta: FieldMeta, check_tag: str, config: SheetConfig, errors: List[str],
                             error_lock):
        """校验单个字段"""
        field_type = meta.type
        field_name = meta.name
        # 处理不同的type,获取每个校验值
        if field_type.startswith('list'):
            values = row.get(field_name, [])
        elif field_type.startswith('map'):
            # 字典不做处理，因为不知道是想要校验key还是value
            return
        else:
            values = [row.get(field_name)]

        target_table, target_field, ignores = self.__parse_check_tag(check_tag)
        ignore_set = set(ignores)
        for value in values:
            if value is None or str(value) in ignore_set:
                continue
            if not self.__check_value_exists(target_table, target_field, value):
                err_msg = (
                    f"[{config.source_file}:字段 {field_name}] 值 {value} "
                    f"不在 [{target_table}:{target_field}] 数据中"
                )
                with error_lock:
                    errors.append(err_msg)

    def __preload_target_values(self, all_configs: List[SheetConfig]):
        """预加载所有配置的值，以空间换时间"""
        cache = defaultdict(set)
        for config in all_configs:
            for field_name, meta in config.fields.items():
                key = (config.export_name, field_name)
                values = {str(row[field_name]) for row in config.rows_values}
                cache[key] = values
        self.__cache = cache

    def __parse_check_tag(self, tag: str) -> tuple:
        """解析校验标签"""
        parts = tag[len('CheckLink:'):].split('_')
        target_table = parts[0]
        target_field = parts[1]
        ignores = parts[2].split(',') if len(parts) > 2 else []
        return target_table, target_field, ignores

    def __check_value_exists(self, target_table, target_field, value) -> bool:
        """快速检查值是否存在"""
        cache_key = (target_table, target_field)
        return str(value) in self.__cache.get(cache_key, set())
