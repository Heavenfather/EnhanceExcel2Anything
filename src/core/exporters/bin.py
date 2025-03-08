from core.exporters.base import ExporterBase
from core.models import SheetConfig


class BinaryExporter(ExporterBase):

    def before_export(self):
        pass

    def after_export(self):
        pass

    def export_data(self, sheet_config: SheetConfig):
        pass
