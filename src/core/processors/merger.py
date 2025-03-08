from core.models import SheetConfig, FieldMeta
from typing import Dict, Any, List
from core.utils.exceptions import FieldTypeConflictError
from core.utils.type_system import TypeSystem
import core
from dataclasses import replace
from collections import defaultdict


class SheetMergerProcessor:
    def __init__(self, type_system: TypeSystem):
        self.type_system = type_system

    def merge(self, sheet_configs: List[SheetConfig]) -> List[SheetConfig]:
        # 对不同的导出名称进行分组，支持同个Excel配置中不同sheet的配置进行合并
        groups = defaultdict(list)
        for cfg in sheet_configs:
            groups[cfg.export_name].append(cfg)

        results = []
        for export_name, config_group in groups.items():
            # 跳过空配置组,理论上不会出现
            if not config_group:
                continue

            # 合并单个分组
            merged = self.__merge_single_sheet_group(config_group)
            results.append(merged)
        return results

    def __merge_single_sheet_group(self, sheet_configs: List[SheetConfig]) -> SheetConfig:
        """合并同导出名称的配置组"""
        base_config = sheet_configs[0]

        # 初始化合并容器
        merged_fields = dict(base_config.fields)  # 浅拷贝字段
        merged_rows = [row.copy() for row in base_config.rows_values]  # 浅拷贝行数据
        merged_sheets = [base_config.sheets[0]]

        # 遍历后续配置进行合并
        for cfg in sheet_configs[1:]:
            merged_fields = self.__merge_field_meta(merged_fields, cfg.fields, cfg.sheets[0])
            merged_rows.extend(row.copy() for row in cfg.rows_values)
            merged_sheets.append(cfg.sheets[0])

        # 填充所有行的缺失字段
        self.__populate_missing_fields(merged_rows, merged_fields)
        return SheetConfig(
            export_name=base_config.export_name,
            fields=merged_fields,
            rows_values=merged_rows,
            sheets=merged_sheets,
            source_file=base_config.source_file,
            source_file_md5=core.utils.utils.get_file_mash(base_config.source_file)
        )

    def __merge_field_meta(self, existing: Dict[str, FieldMeta], new: Dict[str, FieldMeta], sheet_name: str):
        """合并字段定义"""
        merged = dict(existing)
        for name, new_field in new.items():
            if name in merged:
                # 验证类型冲突
                existing_field = merged[name]
                self.__validate_merge_filed(existing_field, new_field, sheet_name)

                # 创建新的合并后字段元数据，避免修改原对象
                merged[name] = replace(existing_field,
                                       checks=list(set(existing_field.checks + new_field.checks)),
                                       comment=new_field.comment or existing_field.comment)
            else:
                # 直接添加新字段
                merged[name] = new_field

        return merged

    def __validate_merge_filed(self, existing: FieldMeta, new: FieldMeta, sheet_name: str):
        """验证字段兼容性"""
        if existing.type != new.type:
            raise FieldTypeConflictError(
                field=new.name,
                type1=existing.type,
                type2=new.type,
                location=f"{sheet_name}.{new.name}"
            )

    def __populate_missing_fields(self, rows: List[Dict], fields: Dict[str, FieldMeta]):
        """填充缺失字段的默认值"""
        required_fields = {name: meta for name, meta in fields.items() if not meta.is_ignored}
        for row in rows:
            for field_name, field_meta in required_fields.items():
                if field_name not in row:
                    row[field_name] = self.type_system.get_default_value(field_meta.type)
