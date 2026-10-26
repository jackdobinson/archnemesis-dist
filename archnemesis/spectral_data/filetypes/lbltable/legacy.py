

from typing import NamedTuple

import numpy as np

from archnemesis.enum import (
	LblTableDataFormatEnum,
	WaveUnitEnum
)

from archnemesis.helpers import annotation_helper
from archnemesis.helpers.wave_helper import waves_as_unit

from .data import LblTableData
from .state import LblTableState



BINARY_K_ABS_PACK_INTO_FLOAT_FACTOR : float = 1.0E20




class LblLegacyHeaderData(NamedTuple):
	irec0  : int   # This is normally 9 instead of 8 Uses FORTRAN convention (1-based indexing). Non-header data starts at `hdr.irec0` "records" into the file, where "records" are usually 4 bytes long.
	nwave  : int   # Number of wavenumbers 
	vmin   : float # Minimum wavenumber (cm^{-1})
	delv   : float # Wavenumber step (cm^{-1})
	npress : int   # Number of pressure levels (bar)
	ntemp  : int   # Number of temperatures (Kelvin)
	gas_id : int   # RADTRAN molecule id number
	iso_id : int   # RADTRAN molecule isotopologue number


class LblLegacyBase:
	#_header_struct : struct.Struct = struct.Struct('<'+''.join([LblLegacyHeaderData.)
	store_int_type : np.dtype = np.dtype(np.int32).newbyteorder('<')
	store_float_type : np.dtype = np.dtype(np.float32).newbyteorder('<')
	return_float_type : np.dtype = np.float64
	
	header_class = LblLegacyHeaderData
	
	def __init__(self, state : LblTableState):
		self._state = state
	
	@classmethod
	def get_store_int_type(cls):
		return cls.store_int_type
	
	@classmethod
	def get_store_float_type(cls):
		return cls.store_float_type
	
	@classmethod
	def get_return_float_type(cls):
		return cls.return_float_type
	
	@classmethod
	def get_header_fields_and_types(cls) -> tuple[tuple[str,np.dtype],...]:
		annotations = annotation_helper.get_annotations(cls.header_class)
		fields = cls.header_class._fields
		ftypes = tuple(annotations.get(x,None) for x in fields)
		
		untyped_fields = tuple(x[0] for x in filter(lambda x: x[1] is None, zip(fields, ftypes)))
		if len(untyped_fields) > 0:
			raise TypeError(f'When reading header specified by a named tuple, must have type annotations for all fields. However, fields {untyped_fields} have no type specified.')
		
		fdtypes = []
		for field, ftype in zip(fields, ftypes):
			if np.issubdtype(ftype, np.integer):
				fdtypes.append((field,cls.get_store_int_type()))
			elif np.issubdtype(ftype, np.floating):
				fdtypes.append((field,cls.get_store_float_type()))
			else:
				raise TypeError(f'When reading header specified by named tuple, encountered unknown type "{ftype}" for field "{field}".')
		
		assert fdtypes[0] == ('irec0',cls.get_store_int_type()), "When reading header specified by a named tuple, first field must be `irec0` of type `int`"
		
		return fdtypes
	
	def get_header_size_bytes(self) -> int:
		assert self._state.n_hdr_fields != 0, "Must have header data"
		return self._state.n_hdr_fields*self._state.fortran_record_byte_size
	
	def get_pressures_size_bytes(self) -> int:
		assert self._state.npress != 0, "Must have header data"
		return self._state.npress * self._state.fortran_record_byte_size
	
	def get_temperatures_size_bytes(self) -> int:
		assert self._state.ntemp != 0, "Must have header data"
		if self._state.data_format == LblTableDataFormatEnum.T_P_GRID:
			return self._state.ntemp * self._state.fortran_record_byte_size
		elif self._state.data_format == LblTableDataFormatEnum.T_PROFILES_AT_P:
			return self._state.npress*(-1*self._state.ntemp) * self._state.fortran_record_byte_size
		else:
			raise AttributeError(f'Cannot get temperature size in bytes for unknown data format {self._state.data_format}')
	
	def get_opacities_size_items(self) -> int:
		assert self._state.nwave != 0 and self._state.npress != 0 and self._state.ntemp !=0, "Must have header data"
		return (self._state.nwave*self._state.npress*abs(self._state.ntemp))
	
	def get_opacities_size_bytes(self) -> int:
		assert self._state.nwave != 0 and self._state.npress != 0 and self._state.ntemp !=0, "Must have header data"
		if self._state.data_format == LblTableDataFormatEnum.UNDEFINED:
			raise AttributeError(f'Cannot get opacities size in bytes for unknown data format {self._state.data_format}')
		return (self._state.nwave*self._state.npress*abs(self._state.ntemp)) * self._state.fortran_record_byte_size
	
	def get_pressures_offset_bytes(self) -> int:
		return self.get_header_size_bytes()
	
	def get_temperatures_offset_bytes(self) -> int:
		return self.get_header_size_bytes() + self.get_pressures_size_bytes()
	
	def get_opacities_offset_bytes(self) -> int:
		return self.get_header_size_bytes() + self.get_pressures_size_bytes() + self.get_temperatures_size_bytes()
	
	def get_total_file_size_bytes(self) -> int:
		return self.get_header_size_bytes() + self.get_pressures_size_bytes() + self.get_temperatures_size_bytes() + self.get_opacities_size_bytes()



class LblLegacyReader(LblLegacyBase):
	"""
	def _read_header(self) -> LblLegacyHeaderData:
		buf = self._state.fptr.read(self._header_struct.size)    
		header_data = LblLegacyHeaderData(*self._header_struct.unpack_from(buf))
		self._state.n_hdr_fields = len(header_data)
		self._state.nwave = header_data.nwave
		self._state.npress = header_data.npress
		self._state.ntemp = header_data.ntemp
		if self._state.ntemp > 0:
			self._state.data_format = LblTableDataFormatEnum.T_P_GRID
		elif self._state.ntemp < 0:
			self._state.data_format = LblTableDataFormatEnum.T_PROFILES_AT_P
		return header_data
	"""
	
	def _read_header(
			self,
	) -> LblLegacyHeaderData:
		
		
		
		fdtypes = self.get_header_fields_and_types()
		
		self._state.fptr.seek(0,0)
		
		irec0 = np.fromfile(self._state.fptr, dtype=fdtypes[0][1], count=1)[0] # This is normally 9 instead of 8 Uses FORTRAN convention (1-based indexing). Non-header data starts at `hdr.irec0` "records" into the file, where "records" are usually 4 bytes long.
		irec0 = min(irec0, len(fdtypes)+1)
		
		header_data = LblLegacyHeaderData(
			irec0,
			*(np.fromfile(self._state.fptr, dtype=dtype, count=1)[0] for field, dtype in fdtypes[1:irec0])
		)
		
		print(f'{header_data=}')
		
		self._state.n_hdr_fields = (irec0-1)
		self._state.nwave = header_data.nwave
		self._state.npress = header_data.npress
		self._state.ntemp = header_data.ntemp
		
		if self._state.ntemp > 0:
			self._state.data_format = LblTableDataFormatEnum.T_P_GRID
		elif self._state.ntemp < 0:
			self._state.data_format = LblTableDataFormatEnum.T_PROFILES_AT_P
		
		return header_data
		
	
	def _read_pressures(self) -> np.ndarray:
		self._state.fptr.seek(self.get_pressures_offset_bytes())
		return np.frombuffer(self._state.fptr.read(self.get_pressures_size_bytes()), dtype=self.get_store_float_type(), count=-1, offset=0).astype(self.get_return_float_type())
	
	def _read_temperatures(self) -> np.ndarray:
		self._state.fptr.seek(self.get_temperatures_offset_bytes())
		if self._state.data_format == LblTableDataFormatEnum.T_P_GRID:
			return np.frombuffer(self._state.fptr.read(self.get_temperatures_size_bytes()), dtype=self.get_store_float_type(), count=-1, offset=0).astype(self.get_return_float_type())
		elif self._state.data_format == LblTableDataFormatEnum.T_PROFILES_AT_P:
			return np.frombuffer(self._state.fptr.read(self.get_temperatures_size_bytes()), dtype=self.get_store_float_type(), count=-1, offset=0).astype(self.get_return_float_type()).reshape(self._state.npress, -1*self._state.ntemp)
		else:
			raise AttributeError(f'Cannot get read temperature for UNDEFINED data format {self._state.data_format}')
	
	def _read_opacities(self) -> np.ndarray:
		self._state.fptr.seek(self.get_opacities_offset_bytes())
		return (
			np.frombuffer(self._state.fptr.read(self.get_opacities_size_bytes()), dtype=self.get_store_float_type(), count=-1, offset=0).astype(self.get_return_float_type()) / BINARY_K_ABS_PACK_INTO_FLOAT_FACTOR
		).reshape(self._state.nwave, self._state.npress, abs(self._state.ntemp), order='C')

	def read_header(
			self,
			wave_unit : WaveUnitEnum = WaveUnitEnum.Wavenumber_cm,
	) -> LblTableData:
		header_data = self._read_header()
		vmin = header_data.vmin
		vmax = vmin + header_data.delv * (header_data.nwave-1)
		
		waves = waves_as_unit(np.linspace(vmin, vmax, header_data.nwave), wave_unit, WaveUnitEnum.Wavenumber_cm)
		pressures = self._read_pressures()
		temperatures = self._read_temperatures()
		
		return LblTableData(
			header_data.gas_id, 
			header_data.iso_id, 
			waves, 
			pressures, 
			temperatures, 
			None
		)

	def read(self, 
			wave_unit : WaveUnitEnum = WaveUnitEnum.Wavenumber_cm,
		) -> LblTableData:
		header_data = self._read_header()
		vmin = header_data.vmin
		vmax = vmin + header_data.delv * (header_data.nwave-1)
		
		waves = waves_as_unit(np.linspace(vmin, vmax, header_data.nwave), wave_unit, WaveUnitEnum.Wavenumber_cm)
		
		pressures = self._read_pressures()
		temperatures = self._read_temperatures()
		opacities = self._read_opacities()
		
		return LblTableData(header_data.gas_id, header_data.iso_id, waves, pressures, temperatures, opacities)



class LblLegacyWriter(LblLegacyBase):
	atol = 1E-8
	rtol = 1E-6
	
	def _fill_empty(self):
		self._state.fptr.truncate(self.get_total_file_size_bytes())
	
	"""
	def _write_header(self, header_data : LblLegacyHeaderData):
		self._state.fptr.seek(0,0)
		self._state.n_hdr_fields = len(header_data)
		self._state.nwave = header_data.nwave
		self._state.npress = header_data.npress
		self._state.ntemp = header_data.ntemp
		if self._state.ntemp > 0:
			self._state.data_format = LblTableDataFormatEnum.T_P_GRID
		elif self._state.ntemp < 0:
			self._state.data_format = LblTableDataFormatEnum.T_PROFILES_AT_P
		self._state.fptr.write(self._header_struct.pack(*header_data))
		self._fill_empty()
	"""
	
	def _write_header(self, header_data : LblLegacyHeaderData):
		fdtypes = self.get_header_fields_and_types()
		
		# Ensure that any "None" values in the header are all at the end
		valid_field_count = 0
		found_first_none_value = False
		non_none_fields_after_first_none = []
		for field, dtype in fdtypes:
			if getattr(header_data, field, None) is None:
				found_first_none_value = True
			else:
				valid_field_count += 1
				if found_first_none_value:
					non_none_fields_after_first_none.append(field)
		
		assert len(non_none_fields_after_first_none) == 0, "When writing header, must have any `None` valued fields all at the end in a single block"
		
		irec0 = valid_field_count + 1
		self._state.n_hdr_fields = valid_field_count
		self._state.nwave = header_data.nwave
		self._state.npress = header_data.npress
		self._state.ntemp = header_data.ntemp
		
		header_data = (irec0,*header_data[1:valid_field_count])
		
		self._state.fptr.seek(0,0)
		for i, (field, dtype) in enumerate(fdtypes):
			self._state.fptr.write(np.array([header_data[i]], dtype=dtype).tobytes())
		
		
	
	def _write_pressures(self, pressures : np.ndarray):
		assert pressures.shape == (self._state.npress,), f"pressure array must have shape {(self._state.npress,)}"
		self._state.fptr.seek(self.get_pressures_offset_bytes(), 0)
		self._state.fptr.write(pressures.astype(self.get_store_float_type()).tobytes())
	
	def _write_temperatures(self, temperatures: np.ndarray):
		if self._state.data_format == LblTableDataFormatEnum.T_P_GRID:
			assert temperatures.shape == (self._state.ntemp,), f"temperature array must have shape {(self._state.ntemp,)}"
		elif self._state.data_format == LblTableDataFormatEnum.T_PROFILES_AT_P:
			assert temperatures.shape == (self._state.npress, -1*self._state.ntemp,), f"temperature array must have shape {(self._state.npress, -1*self._state.ntemp,)}"
		else:
			raise AttributeError(f'Cannot get write temperature for UNDEFINED data format {self._state.data_format}')
			
		self._state.fptr.seek(self.get_temperatures_offset_bytes(), 0)
		self._state.fptr.write(temperatures.astype(self.get_store_float_type()).tobytes())
	
	def _write_opacities(self, opacities : np.ndarray):
		assert opacities.shape == (self._state.nwave, self._state.npress, abs(self._state.ntemp),), f"opacity array must have shape {(self._state.nwave, self._state.npress, abs(self._state.ntemp),)}, but has {opacities.shape=}"
		self._state.fptr.seek(self.get_opacities_offset_bytes(), 0)
		self._state.fptr.write((BINARY_K_ABS_PACK_INTO_FLOAT_FACTOR*opacities).astype(self.get_store_float_type()).tobytes())
	
	def write(self, gas_id : int, iso_id: int, wavenumbers : np.ndarray, pressures : np.ndarray, temperatures : np.ndarray, opacities : np.ndarray):
		assert wavenumbers.size >= 2, "Must have at least two wavenumbers"
		delv = wavenumbers[1] - wavenumbers[0]
		assert np.allclose((wavenumbers[1:] - wavenumbers[:-1]), delv, rtol=self.rtol, atol=self.atol), "Wavenumbers must be on a linear grid"
	
		npress = pressures.size
		
		if self._state.data_format == LblTableDataFormatEnum.UNDEFINED:
			if temperatures.ndim == 1: #[ntemp]
				self._state.data_format = LblTableDataFormatEnum.T_P_GRID
				
			if temperatures.ndim == 2: #[npress, abs(ntemp)]
				self._state.data_format = LblTableDataFormatEnum.T_PROFILES_AT_P
				
		
		if self._state.data_format == LblTableDataFormatEnum.T_P_GRID:
			ntemp = temperatures.size
		elif self._state.data_format == LblTableDataFormatEnum.T_PROFILES_AT_P:
			assert temperatures.shape[0] == npress, f"When lbl data format is {self._state.data_format}, temperatures must be a 2d array with the size of the first dimension equal to {npress=}, but have {temperatures.shape[0]=}"
			ntemp = -1*temperatures.shape[1]
		else:
			raise RuntimeError(f'Cannot determine lbl table data format {self._state.data_format}')
	
		header_data = LblLegacyHeaderData(
			9, 
			wavenumbers.size, 
			wavenumbers[0],
			delv,
			npress,
			ntemp,
			gas_id,
			iso_id,
		)
		self._write_header(header_data)
		self._write_pressures(pressures)
		self._write_temperatures(temperatures)
		
		n_opacities = self.get_opacities_size_items()
		if opacities.size == n_opacities:
			self._write_opacities(opacities)
		elif opacities.size < n_opacities:
			self.write_opacities_chunk(opacities)
		else:
			raise RuntimeError(f'Expected {n_opacities=} but have {opacities.size=}. Therefore cannot write line-by-line opacities')
	
	def write_opacities_chunk_flat(self, opacities_chunk : np.ndarray, start_flat_idx : int):
		opac_shape = (self._state.nwave, self._state.npress, abs(self._state.ntemp))
		n_opac = self.get_opacities_size_items()
		
		if start_flat_idx == 0 and opacities_chunk == n_opac:
			self._write_opacities(opacities_chunk.reshape(*opac_shape))
			return
		
		pos = self.get_opacities_offset_bytes() + start_flat_idx*self.get_store_float_type().itemsize
		self._state.fptr.seek(pos, 0)
		self._state.fptr.write((BINARY_K_ABS_PACK_INTO_FLOAT_FACTOR*opacities_chunk).astype(self.get_store_float_type()).tobytes())
	
	def write_opacities_chunk(self, opacities_chunk : np.ndarray, start_idxs : None | tuple[int,int,int] = None):
		"""
		Write a chunk of opacities, assume it is contiguous
		
		start_idxs : None | tuple[int,int,int] - If None, will continue writing at current file position, otherwise will seek to starting indices and write from there.
			iwave : int - starting position in wave
			ipress : int - starting position in pressure
			itemp : int - starting position in temp
		"""
		if start_idxs is not None:
			iwave, ipress, itemp = start_idxs
			pos = self.get_opacities_offset_bytes() + iwave*(self._state.npress*abs(self._state.ntemp)) + ipress*abs(self._state.ntemp) + itemp
			self._state.fptr.seek(pos, 0)
		
		self._state.fptr.write((BINARY_K_ABS_PACK_INTO_FLOAT_FACTOR*opacities_chunk).astype(self.get_store_float_type()).tobytes())
	
