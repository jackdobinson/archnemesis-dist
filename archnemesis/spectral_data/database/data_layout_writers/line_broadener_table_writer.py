

from archnemesis.spectral_data.database.data_layouts.record_layout import RecordLayout
from archnemesis.spectral_data.database.data_layouts.line_broadener_record_layout import LineBroadenerRecordLayout

from .base import BaseTableWriter


class LineBroadenerTableWriter(BaseTableWriter):
	record_format : type[RecordLayout] = LineBroadenerRecordLayout