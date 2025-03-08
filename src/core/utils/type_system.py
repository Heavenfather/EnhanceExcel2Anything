import core.utils.utils
from core.utils.exceptions import ConfigError
from enum import Enum, auto
from core.models import FieldMeta
import yaml
from pathlib import Path


class TypeKind(Enum):
    """类型种类
    """
    STRUCT = auto()
    CLASS = auto()
    ENUM = auto()


class TypeSystem:
    """类型系统
    支持自定义新增enum、struck、class
    """

    def __init__(self, input_dir, output_dir, base_language, export_type):
        self.custom_types = {}
        self.base_language = base_language
        self.export_type = export_type
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.builtin_types = {
            'int': 0,
            'float': 0.0,
            'long': 0,
            'string': '',
            'bool': False,
            'double': 0.0,
            'char': '\0',
            'byte': 0,
            'sbyte': 0,
            'short': 0,
            'uint': 0,
            'ulong': 0,
            'ushort': 0,
            'decimal': 0,
            'datetime': 0,
        }

        self.validation_logic = {
            TypeKind.STRUCT: self.__validate_composite_type,
            TypeKind.CLASS: self.__validate_composite_type,
            TypeKind.ENUM: self.__validate_enum_type,
        }

    def load_custom_types(self, file_path: str):
        """加载自定义类型
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            types = yaml.safe_load(f) or {}

        for type_name, defs in types.items():
            self.__validate_custom_type_definition(type_name, defs)
            self.custom_types[type_name] = defs

    def get_default_value(self, type_name: str):
        """
        获取配置默认值，包含内置和自定义的
        """
        # 处理泛型类型 (如 list<int>)
        if type_name.lower().startswith('list<'):
            return []
        if type_name.lower().startswith('map<'):
            return {}

        if self.is_custom_support_type(type_name):
            return self.__get_custom_type_default_value(type_name)

        return self.__get_builtin_type_default_value(type_name)

    def is_support_type(self, type_name: str) -> bool:
        """判断是否支持的类型
        """
        return self._is_valid_field_type(type_name)

    def is_builtin_support_type(self, type_name: str) -> bool:
        """判断是否支持的类型
        """
        return type_name in self.builtin_types

    def is_custom_support_type(self, type_name: str) -> bool:
        """判断是否支持的类型
        """
        return type_name in self.custom_types

    def get_type_definition(self, type_name: str) -> dict:
        """获取类型定义
        """
        if type_name in self.builtin_types:
            return self.builtin_types[type_name]
        elif type_name in self.custom_types:
            return self.custom_types.get(type_name, {})
        else:
            raise ConfigError(f'未定义的类型: {type_name}')

    def get_custom_type_fields(self, type_name: str) -> dict:
        """获取自定义类型定义的所有属性字段"""
        if type_name in self.custom_types:
            defs = self.custom_types.get(type_name, {})
            return defs.get('fields', {})
        else:
            raise ConfigError(f'未定义的类型: {type_name}')

    def export_all_custom_cs(self):
        Path(f'{self.output_dir}/scripts').mkdir(parents=True, exist_ok=True)
        with open('./custom/TableCustomTypeTemplate.txt', 'r', encoding='utf-8') as f:
            code_template = f.read()
        for type_name, type_defs in self.custom_types.items():
            # 有忽略标签就不导出
            if type_defs.get('ignore', False):
                continue
            type_kind_enum = self.__parse_2_type_kind_enum(type_defs['type'])
            fields = type_defs.get('fields', {})
            final_code = None
            if type_kind_enum in [TypeKind.STRUCT, TypeKind.CLASS]:
                all_using = set()
                field_lines = []
                assignments = []
                ctor_fields = []
                for field, yaml_type in fields.items():
                    code_line, usings = self.generate_field_code_cs(field, yaml_type, False)
                    all_using.update(usings)
                    field_lines.append(code_line)
                    csharp_type = self.map_to_csharp_type(yaml_type)
                    ctor_fields.append(f'{csharp_type} {field}')
                    assignments.append(f'this.{field} = {field};')

                using_code = '\n    '.join(sorted(all_using)) + '\n' if all_using else ''
                fields_code = '\n        '.join(field_lines)

                ctor_code = f'\n        internal {type_name}({", ".join(ctor_fields)})\n        ' + '{\n            ' + '\n            '.join(
                    assignments) + '\n        }'

                final_code = code_template \
                    .replace('$AttributeType$', type_defs['type']) \
                    .replace('$AttributeName$', type_name) \
                    .replace('$Usings$', using_code) \
                    .replace('$Fields$', fields_code) \
                    .replace('$Constructor$', ctor_code)
            elif type_kind_enum == TypeKind.ENUM:
                enum_items = ',\n        '.join(fields)
                final_code = code_template \
                    .replace('$AttributeType$', 'enum') \
                    .replace('$AttributeName$', type_name) \
                    .replace('$Usings$', '') \
                    .replace('$Fields$', enum_items) \
                    .replace('$Constructor$', '')
            if not final_code is None:
                with open(f'{self.output_dir}/scripts/{type_name}.cs', 'w', encoding='utf-8') as f:
                    f.write(final_code)

    def map_to_csharp_type(self, config_type: str) -> str:
        """核心转换类型，将配置类型转成C#识别的类型"""
        generic_type, inner_types = self.__parse_generic_type(config_type)
        # 递归处理泛型类型
        if generic_type.lower() == 'list':
            return f'List<{self.map_to_csharp_type(inner_types[0])}>'
        elif generic_type.lower() == 'map':
            key_type = self.map_to_csharp_type(inner_types[0])
            value_type = self.map_to_csharp_type(inner_types[1])
            return f'Dictionary<{key_type}, {value_type}>'
        elif generic_type.lower() == 'datetime':
            # 日期类型是转换成时间戳long
            return f'long'
        return config_type

    def generate_field_code_cs(self, field_name: str, config_type: str, pascal=False):
        """生成字段代码和需要的using语句"""
        using_statements = set()
        csharp_type = self.map_to_csharp_type(config_type)
        if 'List<' in csharp_type or 'Dictionary<' in csharp_type:
            using_statements.add('using System.Collections.Generic;')
        if csharp_type in ['Vector2', 'Vector3', 'Vector4', 'Color']:
            using_statements.add('using UnityEngine;')

        # 属性名称转换
        prop_name = field_name
        if pascal:
            prop_name = self.__snake_to_pascal(field_name)
        return f'public {csharp_type} {prop_name} {{ get; }}', using_statements

    def __snake_to_pascal(self, name: str) -> str:
        """转换成驼峰命名"""
        return ''.join([word.title() for word in name.split('_')])

    def __parse_generic_type(self, yaml_type: str) -> tuple:
        """解析泛型类型声明 如List、Dictionary"""
        if yaml_type.lower().startswith(('list<', 'map<')):
            bracket_index = yaml_type.find('<')
            type_name = yaml_type[:bracket_index]
            inner_types = yaml_type[bracket_index + 1:-1].split(',')
            return type_name, [t.strip() for t in inner_types]
        return '', []

    def __get_builtin_type_default_value(self, type_name: str):
        """获取内置类型默认值
        """
        if type_name in self.builtin_types:
            return self.builtin_types[type_name]
        else:
            raise ConfigError(f'获取内置类型默认值失败，未定义的内置类型: {type_name}')

    def __get_custom_type_default_value(self, type_name: str):
        """获取自定义类型默认值
        """
        if type_name in self.custom_types:
            defs = self.custom_types.get(type_name, {})
            if 'default' in defs:
                return self.__parse_default_value(type_name, defs['default'], defs)

            type_kind_enum = self.__parse_2_type_kind_enum(defs['type'])
            if type_kind_enum == TypeKind.ENUM:
                return defs['fields'][0]
            elif type_kind_enum == TypeKind.STRUCT:
                return self.__generate_struct_default_value(defs)
            elif type_kind_enum == TypeKind.CLASS:
                return {}
            else:
                raise ConfigError(f'未知的类型种类: {defs["type"]}')
        else:
            raise ConfigError(f'未定义的类型: {type_name}')

    def __parse_default_value(self, type_name: str, default_spec, defs: dict):
        """解析自定义类型默认值配置"""
        type_kind_enum = self.__parse_2_type_kind_enum(defs['type'])
        if type_kind_enum == TypeKind.ENUM:
            if default_spec not in defs['fields']:
                raise ConfigError(
                    f"自定义类型 {type_name} 字段 '{default_spec}' 的默认值 '{default_spec}' 不在枚举值列表中")
        elif type_kind_enum == TypeKind.STRUCT or type_kind_enum == TypeKind.CLASS:
            required_fields = set(defs['fields'].keys())
            provided_fields = set(default_spec.keys())
            missing = required_fields - provided_fields
            if missing:
                raise ConfigError(
                    f"自定义类型 {type_name} 字段 '{default_spec}' 的默认值 '{missing}' 不在字段列表中")

            return {
                field: self.get_default_value(defs['fields'][field])
                for field in required_fields
            }

        return default_spec

    def __generate_struct_default_value(self, defs: dict):
        return {
            field_name: self.get_default_value(field_type)
            for field_name, field_type in defs['fields'].items()
        }

    def __validate_composite_type(self, type_name: str, defs: dict):
        """
        验证结构体和类类型的字段定义
        """
        for field_name, field_def in defs.get('fields', {}).items():
            if not self._is_valid_field_type(field_def):
                raise ConfigError(
                    f"自定义类型 {type_name} 字段 '{field_name}' 的类型 '{field_def}' 不支持"
                )

    def __validate_enum_type(self, type_name: str, defs: dict):
        """
        验证枚举类型的值定义
        """
        if len(defs['fields']) == 0:
            raise ConfigError(f"枚举类型 '{type_name}' 缺少值定义,至少要有一个值")

        if len(set(defs['fields'])) != len(defs['fields']):
            duplicates = [v for i, v in enumerate(defs['fields']) if v in defs['fields'][:i]]
            raise ConfigError(
                f"自定义枚举类型 '{type_name}' 的值定义有重复项: {duplicates}"
            )

    def __validate_custom_type_definition(self, type_name: str, defs):
        """
        验证自定义类型配置是否正确
        """
        self.__validate_type_structure(type_name, defs)

        # 具体的类型验证逻辑
        type_kind_enum = self.__parse_2_type_kind_enum(defs['type'])
        self.validation_logic[type_kind_enum](type_name, defs)

    def __validate_type_structure(self, type_name: str, defs: dict):
        """验证类型定义基础结构"""
        if 'type' not in defs:
            raise ConfigError(f"缺少必要字段 'type' (类型: {type_name})")

        type_kind = defs['type']
        type_kind_enum = self.__parse_2_type_kind_enum(type_kind)
        required_fields = self.__get_required_fields(type_kind_enum)

        missing_fields = [f for f in required_fields if f not in defs]
        if missing_fields:
            raise ConfigError(
                f"类型 '{type_name}' 缺少必要字段: {missing_fields} "
                f"(类型种类: {type_kind})"
            )
        # 字段名称是否合法
        fields_name = []
        if type_kind_enum == TypeKind.STRUCT or type_kind_enum == TypeKind.CLASS:
            fields_name = defs['fields'].keys()
        if type_kind_enum == TypeKind.ENUM:
            fields_name = defs['fields']
        for field_name in fields_name:
            if not core.utils.utils.validate_str_legal(field_name):
                raise ConfigError(f"自定义类型[{type_name}],字段名称 '{field_name}' 不合法")

    def _is_valid_field_type(self, field_type: str) -> bool:
        """递归验证字段类型有效性"""
        # 处理泛型类型 例如list<int>
        if field_type.lower().startswith('list<'):
            if not field_type.endswith('>'):
                return False
            inner_type = field_type[5:-1]
            return self._is_valid_field_type(inner_type)
        if field_type.lower().startswith('map<'):
            if not field_type.endswith('>'):
                return False
            key_type, value_type = field_type[4:-1].split(',')
            return self._is_valid_field_type(key_type) and self._is_valid_field_type(value_type)

        # 基础类型检查
        return self.is_builtin_support_type(field_type) or self.is_custom_support_type(field_type)

    def __parse_2_type_kind_enum(self, type_kind):
        if type_kind == 'struct':
            return TypeKind.STRUCT
        elif type_kind == 'class':
            return TypeKind.CLASS
        elif type_kind == 'enum':
            return TypeKind.ENUM
        else:
            raise ValueError(f'未支持的自定义类型: {type_kind}')

    def __get_required_fields(self, type_kind):
        """获取类型定义必须包含的字段"""
        if type_kind in [TypeKind.STRUCT, TypeKind.CLASS, TypeKind.ENUM]:
            return ['fields']
        else:
            raise ValueError(f'未支持的自定义类型: {type_kind}')


if __name__ == '__main__':
    pass
    # ts = TypeSystem()
    # ts.load_custom_types('custom_types.yaml')
    # print(ts.get_type_definition('int'))
    # print(ts.get_type_definition('string'))
    # print(ts.get_type_definition('AttributeData'))
    # print(ts.get_type_definition('ItemType'))
    # print(ts.get_type_definition('CharacterClass'))
