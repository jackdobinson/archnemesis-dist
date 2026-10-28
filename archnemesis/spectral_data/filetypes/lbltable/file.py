


from pathlib import Path
from io import IOBase
from typing import Literal, Self

import numpy as np
import h5py

from archnemesis.enum import (
	LblTableFileFormatEnum,
	WaveUnitEnum
)

from .state import LblTableState
from .data import LblTableData
from .legacy import LblLegacyReader, LblLegacyWriter
from .hdf5 import LblHDF5Reader, LblHDF5Writer


import archnemesis.cfg.logs as logging
_lgr = logging.getLogger(__name__)
_lgr.setLevel(logging.DEBUG)



class LblTableFile:


	def __init__(self, 
			path : Path, # Path to the line-by-line table file
			mode : None | Literal['r','w','rb','wb','r+','a'] = None
	):
		self.path = path
		self.mode = mode
		self._file_format : LblTableFileFormatEnum = LblTableFileFormatEnum.UNDEFINED
		self._state : LblTableState = LblTableState()
		self._reader : None | LblLegacyReader | LblHDF5Reader
		self._writer : None | LblLegacyWriter | LblHDF5Writer
		
		self._set_file_format_from_path()
		
		if mode is not None:
			self.open(mode)
	
	def __enter__(self) -> Self:
		return self
	
	def __exit__(self, type, value, traceback):
		self.close()
	
	
	def __repr__(self):
		return f'{self.__class__.__name__}(path={self.path!s})'
	
	
	@property
	def file_format(self) -> None | LblTableFileFormatEnum:
		return self._file_format
	
	@file_format.setter
	def file_format(self, value : LblTableFileFormatEnum):
		self._file_format = value
		self._set_readers_and_writers()

	
	def _set_readers_and_writers(self):
		if self._file_format == LblTableFileFormatEnum.LEGACY:
			self._reader = LblLegacyReader(self._state)
			self._writer = LblLegacyWriter(self._state)
		elif self._file_format == LblTableFileFormatEnum.HDF5:
			self._reader = LblHDF5Reader(self._state)
			self._writer = LblHDF5Writer(self._state)
		else:
			raise RuntimeError(f'Cannot read or write line-by-line table with format {self._file_format=}')
				
	def _set_file_format_from_path(self):
		if self._file_format == LblTableFileFormatEnum.UNDEFINED:
			#_lgr.dev(f'{self.path.suffix=}')
			if self.path.suffix == '.h5':
				self.file_format = LblTableFileFormatEnum.HDF5
			elif self.path.suffix == '.lta':
				self.file_format = LblTableFileFormatEnum.LEGACY
			else:
				self.file_format = LblTableFileFormatEnum.UNDEFINED
	
	def _open(self, mode) -> IOBase:
		if self._file_format == LblTableFileFormatEnum.LEGACY:
			mode_alterations = {'r' :'rb', 'w':'wb', 'r+': 'rb+'}
			mode = mode_alterations.get(mode, mode)
			return open(self.path, mode)
		elif self._file_format == LblTableFileFormatEnum.HDF5:
			return h5py.File(self.path, mode)
		else:
			raise RuntimeError(f'Cannot open line-by-line table with format {self._file_format=}')
	
	def open(self,mode) -> Self:
		self._state.fptr = self._open(mode)
		return self
	
	def close(self):
		self._state.fptr.close()
	
	

	def write(self, mol_id, iso_id, wavenumbers, pressures, temperatures, opacities):
		self._writer.write(mol_id, iso_id, wavenumbers, pressures, temperatures, opacities)
		_lgr.info(f'Written line-by-line table to "{self.path}"')
	
	def write_opacities_part(self, opacities_part : np.ndarray, idxs : tuple[int,int,int]):
		"""
		idxs : tuple[int,int,int] = wave_idx, press_idx, temp_idx
		"""
		self._writer.write_opacities_part(opacities_part, idxs)
	
	def read_header(
			self,
			wave_unit : WaveUnitEnum = WaveUnitEnum.Wavenumber_cm,
	) -> LblTableData:
		return self._reader.read_header(wave_unit=wave_unit)
	
	def read(self,
			wave_unit : WaveUnitEnum = WaveUnitEnum.Wavenumber_cm,
	) -> LblTableData:
		return self._reader.read(wave_unit=wave_unit)

