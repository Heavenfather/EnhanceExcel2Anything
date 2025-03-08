import hashlib
import time
import re
from functools import wraps

# 预编译正则表达式以提升效率
CHINESE_CHAR_PATTERN = re.compile(
    r'['
    r'\u4e00-\u9fff'  # CJK Unified Ideographs (基本汉字)
    r'\u3400-\u4dbf'  # CJK Extension A (扩展A)
    r'\U00020000-\U0002a6df'  # CJK Extension B (扩展B)
    r'\U0002a700-\U0002b73f'  # CJK Extension C (扩展C)
    r'\U0002b740-\U0002b81f'  # CJK Extension D (扩展D)
    r'\U0002b820-\U0002ceaf'  # CJK Extension E (扩展E)
    r'\U0002ceb0-\U0002ebef'  # CJK Extension F (扩展F)
    r'\uf900-\ufaff'  # CJK Compatibility Ideographs (兼容汉字)
    r'\u3300-\u33ff'  # CJK Compatibility (兼容符号)
    r'\ufe30-\ufe4f'  # CJK Compatibility Forms (兼容形式)
    r'\U0002f800-\U0002fa1f'  # CJK Compatibility Supplement (兼容补充)
    r'\u3000-\u303f'  # CJK Symbols and Punctuation (符号和标点)
    r'\uff00-\uffef'  # Halfwidth and Fullwidth Forms (全角符号)
    r']',
    re.UNICODE
)

LANG_SUFFIX = '.i18n'

def is_contains_chinese(string):
    """
    检测字符串是否含有中文（包括中文符号）
    """
    return bool(CHINESE_CHAR_PATTERN.search(string))


@staticmethod
def get_file_mash(file_path):
    """获取文件hash"""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_str_legal(s):
    """
    验证字符串是否合法：仅允许ASCII字母数字，且不以数字开头
    """
    if not isinstance(s, str):
        return False, "输入必须是字符串"
    if not s:  # 检查空字符串
        return False, "字符串不能为空"
    if not (s.isascii() and s.isalnum()):
        return False, "输入只能包含ASCII字母和数字"
    if not s[0].isalpha():
        return False, "首字符必须为字母"
    return True, ""


def get_current_date():
    """获取当前时间，返回具体到秒的日期"""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def timer_decorator(func):
    """
    装饰器，用于计算函数运行时间
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} 运行时间：{end - start:.6f} 秒")
        return result

    return wrapper
