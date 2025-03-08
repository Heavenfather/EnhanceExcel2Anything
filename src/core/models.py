from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class FieldMeta:
    name: str
    type: str
    checks: List[str]
    comment: str
    is_ignored: bool = False
    col_index: int = -1


@dataclass
class SheetConfig:
    export_name: str
    fields: Dict[str, FieldMeta]
    rows_values: List[Dict[str, Any]]
    sheets: List[str]
    source_file: str
    source_file_md5: int
