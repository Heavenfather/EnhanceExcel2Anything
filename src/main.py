import argparse
import traceback
from pathlib import Path
from typing import List

from core.excel_reader import ExcelProcessor
from core.utils.type_system import TypeSystem
from core.models import SheetConfig
from core.processors.merger import SheetMergerProcessor
from core.utils.utils import timer_decorator
from core.utils.cache import CacheSystem


def process_cache_system(args):
    # 1.初始化缓存系统，文件变更检测
    cache_system = CacheSystem(args.input_dir)
    return cache_system


def process_type_system(args):
    # 2.初始化并注册类型系统
    errors = []
    type_system = None
    try:
        type_system = TypeSystem(args.input_dir, args.output_dir, args.base_language, args.export_type)
        type_system.load_custom_types('./custom/custom_types.yaml')
        type_system.export_all_custom_cs()
    except Exception as e:
        errors.append(f"[自定义类型系统] 初始化失败 错误信息: {e} \n异常堆栈: {traceback.format_exc()}")
    return type_system, errors


def process_single_file(file_path, type_system) -> tuple[List[SheetConfig], list[str]]:
    # 3.处理单个Excel文件
    errors = []
    config = None
    try:
        excel_processor = ExcelProcessor(type_system)
        configs = excel_processor.process_workbook(file_path)

        # 4.合并跨Sheet数据
        merger = SheetMergerProcessor(type_system)
        config = merger.merge(configs)
    except Exception as e:
        errors.append(f"[{file_path}] 转换失败 错误信息: {e} \n异常堆栈: {traceback.format_exc()}")
    finally:
        return config, errors


@timer_decorator
def process_valid_configs(configs: List[SheetConfig]) -> list[str]:
    # 5.各种校验
    from core.processors.validators import RepeatValidator, LinkValidator, ExportNameValidator
    validators = [RepeatValidator(), LinkValidator(), ExportNameValidator()]
    errors = []
    try:
        for validator in validators:
            es = validator.validate(configs)
            if es and len(es) > 0:
                for e in es:
                    errors.append(e)
    except Exception as e:
        errors.append(f"数据校验失败，异常信息: {e} \n异常堆栈: {traceback.format_exc()}")
    finally:
        return errors


@timer_decorator
def process_export_configs(configs: List[SheetConfig], type_system: TypeSystem, cache_system: CacheSystem) -> list[str]:
    # 6.导出数据及基类
    from core.exporters.json import JsonExporter
    from core.exporters.csharp import CSharpExporter
    from core.exporters.bin import BinaryExporter

    errors = []
    try:
        # 创建导出目录
        Path(type_system.output_dir).mkdir(parents=True, exist_ok=True)
        exporter = None
        if type_system.export_type == 'json':
            exporter = JsonExporter(type_system)
        elif type_system.export_type == 'csharp':
            exporter = CSharpExporter(type_system)
        elif type_system.export_type == 'bin':
            exporter = BinaryExporter(type_system)
        else:
            errors.append(f'暂未支持的导出类型: {type_system.export_type}')
            return errors

        exporter.before_export()
        for config in configs:
            if cache_system.is_modify_file(config.source_file_md5):
                print(f'文件[ {config.source_file} ]有更新，开始导出数据')
                exporter.export_base_language_class(config)
                exporter.export_data(config)
        exporter.after_export()
    except Exception as e:
        errors.append(f'导出数据失败，异常信息: {e} \n异常堆栈: {traceback.format_exc()}')
    return errors


@timer_decorator
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=str)
    parser.add_argument("output_dir", type=str)
    parser.add_argument("--base_language", choices=['cs', 'cpp'], type=str, default='cs')
    parser.add_argument("--export_type", choices=['json', 'csharp', 'bin'], type=str, default='csharp')
    args = parser.parse_args()
    errors = []
    cache_system = process_cache_system(args)

    type_system, es = process_type_system(args)
    if len(es) > 0:
        print("自定义类型系统初始化失败,已停止导出!")
        exit(1)

    configs = []
    for excel_file in Path(type_system.input_dir).glob('**/*.xlsx'):
        if excel_file.name.startswith('~$'):
            continue
        config, es = process_single_file(str(excel_file), type_system)
        if len(es):
            errors.append(es)
        if not config is None and len(config) > 0:
            for c in config:
                configs.append(c)

    if len(errors) > 0:
        for es in errors:
            print(es)
        print("Excel处理失败,已停止导出!")
        exit(1)

    # 这里可以再合并一次，以实现可以跨Excel配置合并数据，不过现在的处理还是不允许跨Excel配置

    errors = process_valid_configs(configs)
    if len(errors) > 0:
        for es in errors:
            print(es)
        print("数据校验失败,已停止导出!")
        exit(1)

    errors = process_export_configs(configs, type_system, cache_system)
    if len(errors) > 0:
        for es in errors:
            print(es)
        print("导出数据失败,已停止导出!")
        exit(1)
    cache_system.save_cache()


if __name__ == '__main__':
    main()
    print("导出完成!")
