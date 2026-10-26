

import dataclasses as dc

from io import IOBase

import h5py

from archnemesis.enum import LblTableDataFormatEnum


@dc.dataclass(slots=True)
class LblTableState:
	fptr : None | IOBase | h5py.File = None
	data_format : LblTableDataFormatEnum = LblTableDataFormatEnum.UNDEFINED
	n_hdr_fields : int = 0
	nwave : int = 0
	npress : int = 0
	ntemp : int = 0
	fortran_record_byte_size : int  = 4