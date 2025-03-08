class ConfigError(Exception):
    """配置错误基类"""

    def __init__(self, message: str, location=None):
        super().__init__(f'配置错误:{location}:{message}' if location else message)


class FieldTypeConflictError(ConfigError):
    """字段类型冲突错误"""

    def __init__(self, field: str, type1: str, type2: str, location=None):
        super().__init__(f'合并时字段类型不一致：{field}，类型1：{type1}，类型2：{type2} 检查合并Sheet是否存在同字段不同数据类型', location)


class LinkerCheckError(ConfigError):
    """链接检查错误"""

    def __init__(self, field: str, check_str: str, value, location=None):
        super().__init__(f'链接检查错误：{field},检查表达式：{check_str}, 值：{value}', location)


class TypeCastError(ValueError):
    """类型转换专用异常"""

    def __init__(self, message):
        super().__init__(message)


class JsonTypeCastError(TypeCastError):
    """json类型转换异常"""

    def __init__(self, message, *,
                 data_type: str = None,
                 original_value=None,
                 missing_fields: list = None,
                 extra_fields: list = None,
                 error_position: str = None):
        super().__init__(message)
        self.metadata = {
            'data_type': data_type,
            'original_value': original_value,
            'missing_fields': missing_fields or [],
            'extra_fields': extra_fields or [],
            'error_position': error_position
        }

    def add_context(self, context: str):
        """添加上下文信息"""
        self.args = (f"{context}: {self.args[0]}",) + self.args[1:]
