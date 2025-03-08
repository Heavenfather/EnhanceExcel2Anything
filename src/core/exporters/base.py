import core.utils.utils
from core.models import SheetConfig, FieldMeta
from abc import ABC, abstractmethod
from core.utils.type_system import TypeSystem
from pathlib import Path


class ExporterBase(ABC):
    def __init__(self, type_system: TypeSystem):
        self.type_system = type_system
        # 准备好数据导出目录
        self.export_data_dir = Path(self.type_system.output_dir) / 'data'
        Path(self.export_data_dir).mkdir(parents=True, exist_ok=True)
        self.__export_base_logic = {
            'cs': self.__export_base_cs,
            'cpp': self.__export_base_cpp
        }

    @abstractmethod
    def export_data(self, sheet_config: SheetConfig):
        """导出可读取数据"""
        pass

    @abstractmethod
    def before_export(self):
        """导出数据前"""
        pass

    @abstractmethod
    def after_export(self):
        """导出数据后"""
        pass

    def export_base_language_class(self, sheet_config: SheetConfig):
        """导出基础的可序列化的语言类"""
        self.__export_base_logic[self.type_system.base_language](sheet_config)

    def __export_base_cs(self, sheet_config: SheetConfig):
        """导出基础的可序列化的C#类"""
        Path(f'{self.type_system.output_dir}/scripts').mkdir(parents=True, exist_ok=True)
        with open('./custom/TableScriptTemplate.txt', 'r', encoding='utf-8') as f:
            code_template = f.read()
        all_using = set()
        field_lines = []
        assignments = []
        ctor_fields = []
        fields_values = self.__sort_fields_cs(sheet_config.fields)
        for field in fields_values:
            code_line, usings = self.type_system.generate_field_code_cs(field.name, field.type)
            all_using.update(usings)
            if field.comment:
                comment = field.comment.strip().replace('\n',' ')
                code_line = f'\n        /// <summary>\n        /// {comment}\n        /// </summary>\n        {code_line}'
            field_lines.append(code_line)
            csharp_type = self.type_system.map_to_csharp_type(field.type)
            ctor_fields.append(f'{csharp_type} {field.name}')
            assignments.append(f'this.{field.name} = {field.name};')
        using_code = '\n    '.join(sorted(all_using)) + '\n' if all_using else ''
        field_code = '\n        '.join(field_lines)
        ctor_code = f'\n        internal {sheet_config.export_name}({", ".join(ctor_fields)})\n        ' + '{\n            ' + '\n            '.join(
            assignments) + '\n        }'

        finale_code = code_template \
            .replace('$LastModifyDate$', core.utils.utils.get_current_date()) \
            .replace('$SourceTable$', sheet_config.source_file.replace('\\', '/').split('/')[-1]) \
            .replace('$Usings$', using_code) \
            .replace('$TableName$', sheet_config.export_name) \
            .replace('$Filed$', field_code) \
            .replace('$Constructor$', ctor_code)
        with open(f'{self.type_system.output_dir}/scripts/{sheet_config.export_name}.cs', 'w', encoding='utf-8') as f:
            f.write(finale_code)

    def __export_base_cpp(self, sheet_config: SheetConfig):
        """导出基础的可序列化的C++类"""
        # 根据需求扩展
        pass

    def __sort_fields_cs(self, fields: dict[str, FieldMeta]) -> list:
        """对字段进行排序
        值类型和引用类型统一布局
        使值类型在内存中连续存储无需堆分配，以减少内存碎片提升CPU缓存命中率
        使引用类型减少对象头的分散，降低GC压力"""
        return sorted(fields.values(),
                      key=lambda x: (
                          not (self.type_system.is_builtin_support_type(x.type) and not self.__is_string_type(x.type)),
                          not self.__is_string_type(x.type),
                          self.__custom_value_type_sort_weight(x.type),
                          not self.__is_builtin_ref_type(x.type),
                          self.__custom_ref_type_sort_weight(x.type),
                          x.name
                      ))

    def __is_string_type(self, type_name: str):
        return type_name.lower() == 'string'

    def __is_builtin_ref_type(self, type_name: str):
        return type_name.lower().startswith(('list', 'dict', 'map'))

    def __custom_value_type_sort_weight(self, type_name: str):
        if not self.type_system.is_custom_support_type(type_name):
            return 2
        custom_types = self.type_system.get_type_definition(type_name)
        if custom_types['type'] == 'enum':
            return 0
        elif custom_types['type'] == 'struct':
            return 1
        else:
            return 2

    def __custom_ref_type_sort_weight(self, type_name: str):
        if not self.type_system.is_custom_support_type(type_name):
            return 0
        custom_types = self.type_system.get_type_definition(type_name)
        if custom_types['type'] == 'class':
            return 0
        return 1
