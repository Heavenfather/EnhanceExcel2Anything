from core.exporters.base import ExporterBase
from core.models import SheetConfig, FieldMeta
from core.utils.type_system import TypeSystem
from pathlib import Path
from dataclasses import replace
from core.i18n.i18n_manager import I18NManager
import core


class CSharpExporter(ExporterBase):
    def __init__(self, type_system: TypeSystem):
        super().__init__(type_system)
        self.current_config = None
        self.i18n = I18NManager()

        self._type_handlers = {
            "list": self.__handle_list_type,
            "dict": self.__handle_dict_type,
            "builtin": self.__handle_builtin_type,
            "custom": self.__handle_custom_type
        }

    def export_data(self, sheet_config: SheetConfig):
        """导出C#硬编码数据"""
        with open('./custom/TableScriptDataTemplate.txt', 'r', encoding='utf-8') as f:
            code_template = f.read()
        data_lines = []
        self.current_config = sheet_config
        for row_value in sheet_config.rows_values:
            data_lines.append(self.__parse_row_2_code_line(sheet_config.fields, row_value))

        (unique_map, unique_get, unique_type, unique_field_name, unique_method) = self.__get_unique_code(
            sheet_config.export_name,
            sheet_config.fields)
        all_using = self.__generate_using_statements(sheet_config.fields)
        if not unique_map == '':
            all_using.add('using System.Collections.Generic;')
        using_code = '\n    '.join(sorted(all_using)) + '\n' if all_using else ''
        final_code = code_template \
            .replace('$LastModifyDate$', core.utils.utils.get_current_date()) \
            .replace('$SourceTable$', Path(sheet_config.source_file).name) \
            .replace('$Usings$', using_code) \
            .replace('$TableName$', sheet_config.export_name) \
            .replace('$ConstructData$', ",\n".join(data_lines)) \
            .replace('$UniqueMap$', unique_map) \
            .replace('$UniqueGet$', unique_get) \
            .replace('$UniqueType$', unique_type) \
            .replace('$UniqueFieldName$', unique_field_name) \
            .replace('$UniqueMethod$', unique_method)

        with open(self.export_data_dir / f'{sheet_config.export_name}DB.cs', 'w', encoding='utf-8') as f:
            f.write(final_code)

        # 生成用户自定义服务代码
        service_file = self.export_data_dir / f'{sheet_config.export_name}Service.cs'
        if not service_file.exists():
            with open('./custom/TableServiceScriptTemplate.txt', 'r', encoding='utf-8') as f:
                service_code = f.read()
            service_final_code = service_code \
                .replace('$TableName$', f'{sheet_config.export_name}')
            with open(self.export_data_dir / f'{sheet_config.export_name}Service.cs', 'w', encoding='utf-8') as f:
                f.write(service_final_code)

    def before_export(self):
        pass

    def after_export(self):
        self.i18n.write_master_file()

    def __get_unique_code(self, export_name, fields: dict[str, FieldMeta]):
        for field_meta in fields.values():
            if 'CheckRepeat' in field_meta.checks:
                return self.__make_unique_code(export_name, field_meta)
        return self.__make_idx_code(export_name)

    def __make_unique_code(self, export_name, field_meta: FieldMeta):
        """生成通过唯一值获取数据的代码"""
        cs_type = self.type_system.map_to_csharp_type(field_meta.type)
        unique_map = f'private Dictionary<{cs_type}, int> _idToIdx;'
        unique_get = (f'var ok = _idToIdx.TryGetValue({field_meta.name}, out int idx);\n'
                      f'                if (!ok)\n'
                      f'                    UnityEngine.Debug.LogError($"[{export_name}] {field_meta.name}: {{{field_meta.name}}} not found");')
        unique_type = f'{cs_type}'
        unique_field_name = f'{field_meta.name}'
        unique_method = (f'_idToIdx = new Dictionary<{cs_type},int>(_data.Length);\n'
                         f'            for (int i = 0; i < _data.Length; i++)\n'
                         f'            {{\n'
                         f'                _idToIdx[_data[i].{unique_field_name}] = i;\n'
                         f'            }}')
        return (unique_map, unique_get, unique_type, unique_field_name, unique_method)

    def __make_idx_code(self, export_name):
        unique_map = ''
        unique_get = f'if(idx < 0 || idx >= _data.Length)\n                    UnityEngine.Debug.LogError($"[{export_name}] {{idx}} out of bounds");'
        unique_type = 'int'
        unique_field_name = 'idx'
        unique_method = ''
        return (unique_map, unique_get, unique_type, unique_field_name, unique_method)

    def __parse_row_2_code_line(self, fields: dict[str, FieldMeta], row_value: dict) -> str:
        """将单行数据转换为C#对象初始化代码"""
        init_values = []
        for field_name, value in row_value.items():
            field_meta = fields[field_name]
            handler = self.__get_type_handler(field_meta.type)
            code = handler(field_meta, value)
            init_values.append(f'{field_name}: {code}')
        return f'                new({", ".join(init_values)})'

    def __get_type_handler(self, type_name: str) -> callable:
        """获取类型处理器"""
        if self.type_system.is_custom_support_type(type_name):
            return self._type_handlers['custom']
        if type_name.lower().startswith('list'):
            return self._type_handlers['list']
        if type_name.lower().startswith('map'):
            return self._type_handlers['dict']
        return self._type_handlers['builtin']

    def __handle_builtin_type(self, field_meta: FieldMeta, value):
        type_name = field_meta.type.lower()
        if type_name == 'string':
            key = self.i18n.update_raw_master(self.current_config.export_name, field_meta.name, value)
            if key is None:
                return f'"{value}"'
            else:
                return f'LocalizationPool.Get("{key}")'
        if type_name == 'bool':
            return 'true' if value else 'false'
        if type_name == 'float':
            return f'{value}f'
        return f'{value}'

    def __handle_custom_type(self, field_meta: FieldMeta, value: dict):
        """处理自定义类型"""
        type_def = self.type_system.get_type_definition(field_meta.type)
        if type_def['type'] == 'enum':
            return f'{field_meta.type}.{value}'
        if type_def['type'] == 'struct':
            return self.__generate_struck_code(field_meta, type_def, value)
        if type_def['type'] == 'class':
            return self.__generate_class_code(field_meta, type_def, value)
        # 前面全都安全校验过了，不会走到这里
        return ''

    def __handle_list_type(self, field_meta: FieldMeta, value: list):
        """处理列表类型"""
        if value is None:
            return 'null'
        if len(value) <= 0:
            return 'null'
        element_type = field_meta.type[5:-1]
        elements = [self.__parse_element(field_meta, element_type, v) for v in value]
        return f'new List<{element_type}>() {{ {", ".join(elements)} }}'

    def __handle_dict_type(self, field_meta: FieldMeta, value: dict):
        """处理字典类型"""
        if value is None:
            return 'null'
        if len(value) <= 0:
            return 'null'
        key_type, value_type = field_meta.type[4:-1].split(',', 1)
        entries = [
            f'[{self.__parse_element(field_meta, key_type, k)}] = {self.__parse_element(field_meta, value_type, v)}'
            for k, v in value.items()
        ]
        return f'new Dictionary<{key_type}, {value_type}>() {{ {", ".join(entries)} }}'

    def __parse_element(self, field_meta: FieldMeta, element_type: str, value):
        """解析列表中的单个元素"""
        dummy_field = replace(field_meta, type=element_type)
        handler = self.__get_type_handler(element_type)
        return handler(dummy_field, value)

    def __generate_struck_code(self, field_meta: FieldMeta, type_def: dict, value: dict):
        """生成结构体初始化代码"""
        fields = [
            f"{field_name}: {self.__parse_element(field_meta, field_type, value.get(field_name))}"
            for field_name, field_type in type_def["fields"].items()
        ]
        return f"new {field_meta.type}({', '.join(fields)})"

    def __generate_class_code(self, field_meta: FieldMeta, type_def: dict, value: dict) -> str:
        """生成类初始化代码"""
        fields = [
            f"{field_name}: {self.__parse_element(field_meta, field_type, value.get(field_name))}"
            for field_name, field_type in type_def["fields"].items()
        ]
        return f"new {field_meta.type}({', '.join(fields)})"

    def __generate_using_statements(self, fields: dict[str, FieldMeta]):
        """生成需要的using语句"""
        using_statements = set()
        for config_type in fields.values():
            csharp_type = self.type_system.map_to_csharp_type(config_type.type)
            if 'List<' in csharp_type or 'Dictionary<' in csharp_type:
                using_statements.add('using System.Collections.Generic;')
            if csharp_type in ['Vector2', 'Vector3', 'Vector4', 'Color']:
                using_statements.add('using UnityEngine;')

        return using_statements
