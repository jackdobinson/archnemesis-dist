

import numpy as np


from archnemesis.enum import (
	LblTableDataFormatEnum,
	WaveUnitEnum,
	SpectralCalculationModeEnum
)

from archnemesis.helpers import h5py_helper
from archnemesis.helpers.wave_helper import waves_as_unit

from .data import LblTableData
from .state import LblTableState



BINARY_K_ABS_PACK_INTO_FLOAT_FACTOR : float = 1.0E20


class LblHDF5Base:

	dset_attrs = {
		'ILBL' : {
			'title' : 'Spectroscopy calculation type',
			'type' : 'Line-by-line pre-tabulated look-up tables',
		},
		'WAVE' : {
			'title' : 'Spectral points at which the cross sections are defined (wavenumber cm^{-1})'
		},
		'NP' : {
			'title' : 'Number of pressure levels present in the lookup table',
		},
		'NT' : {
			'title' : 'Number of temperature levels in the lookup table',
		},
		'ID' : {
			'title' : 'ID (radtran) of molecule',
		},
		'ISO' : {
			'title' : 'Isotope ID (radtran) of molecule isotopologue',
		},
		'PRESS' : {
			'title' : 'Pressure levels of the lookup table (atm)',
		},
		'TEMP' : {
			'title' : 'Temperature levels of the lookup table, if 1D all pressures share the same temperatures (Kelvin)',
		},
		'K' : {
			'title' : 'Tabulated cross sections / cm2 multiplied by a factor of 1.0 x 10^20'
		}
	}

	def __init__(self, state : LblTableState):
		self._state = state
	
class LblHDF5Reader(LblHDF5Base):
	def read_header(
			self,
			wave_unit : WaveUnitEnum = WaveUnitEnum.Wavenumber_cm,
	) -> LblTableData:
		ilbl = mol_id = h5py_helper.retrieve_data(self._state.fptr, 'ILBL', np.int32)
		assert ilbl == SpectralCalculationModeEnum.LINE_BY_LINE_TABLES, f"Must have ILBL={SpectralCalculationModeEnum.LINE_BY_LINE_TABLES} for line-by-line tables, but have {ilbl}"
		
		mol_id = h5py_helper.retrieve_data(self._state.fptr, 'ID', np.int32)
		iso_id = h5py_helper.retrieve_data(self._state.fptr, 'ISO', np.int32)
		wavenumbers = h5py_helper.retrieve_data(self._state.fptr, 'WAVE', np.array)
		npress = h5py_helper.retrieve_data(self._state.fptr, 'NP', np.int32)
		ntemp = h5py_helper.retrieve_data(self._state.fptr, 'NT', np.int32)
		pressures = h5py_helper.retrieve_data(self._state.fptr, 'PRESS', np.array)
		temperatures = h5py_helper.retrieve_data(self._state.fptr, 'TEMP', np.array)
		
		wavenumbers = waves_as_unit(wavenumbers, wave_unit, WaveUnitEnum.Wavenumber_cm)

		self._state.nwave = wavenumbers.size
		self._state.npress = npress
		self._state.ntemp = ntemp
		
		assert pressures.size == self._state.npress
		
		if ntemp > 0:
			self._state.data_format = LblTableDataFormatEnum.T_P_GRID
			assert temperatures.size == self._state.ntemp
		elif ntemp < 0:
			self._state.data_format = LblTableDataFormatEnum.T_PROFILES_AT_P
			assert temperatures.shape == (self._state.npress, abs(self._state.ntemp))
		else:
			raise RuntimeError(f'Cannot determine line-by-line data format from {self._state.ntemp=}')
		
		
		return LblTableData(
			mol_id,
			iso_id,
			wavenumbers,
			pressures,
			temperatures,
			None
		)

	def read(
			self,
			wave_unit : WaveUnitEnum = WaveUnitEnum.Wavenumber_cm,
	) -> LblTableData:
		lbl_table_header_data = self.read_header(wave_unit=wave_unit)[:-1]
		
		opacities = h5py_helper.retrieve_data(self._state.fptr, 'K', np.array)
		
		assert opacities.shape == (self._state.nwave, self._state.npress, abs(self._state.ntemp))
		
		return LblTableData(
			*lbl_table_header_data,
			opacities
		)


class LblHDF5Writer(LblHDF5Base):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		self._opac_attrs_written : bool = False
		
	def write(self, mol_id : int, iso_id: int, wavenumbers : np.ndarray, pressures : np.ndarray, temperatures : np.ndarray, opacities : np.ndarray):
		
		self._state.nwave = wavenumbers.size
		self._state.npress = pressures.size
		
		
		if self._state.data_format == LblTableDataFormatEnum.UNDEFINED:
			if temperatures.ndim == 1:
				self._state.ntemp = temperatures.size
				self._state.data_format = LblTableDataFormatEnum.T_P_GRID
			elif temperatures.ndim == 2:
				self._state.ntemp = -1*temperatures.shape[1]
				self._state.data_format = LblTableDataFormatEnum.T_PROFILES_AT_P
			else:
				raise RuntimeError(f'Cannot determine line-by-line table data format from {temperatures.shape=}')
		
		elif self._state.data_format == LblTableDataFormatEnum.T_P_GRID:
			assert temperatures.ndim == 1
			self._state.ntemp = temperatures.size
		
		elif self._state.data_format == LblTableDataFormatEnum.T_PROFILES_AT_P:
			assert temperatures.ndim == 2
			self._state.ntemp = -1*temperatures.shape[1]
		
		else:
			raise RuntimeError(f'Unknown line-by-line data format {self._state.data_format}')
		
		for dset_name, data in (
			('ILBL', SpectralCalculationModeEnum.LINE_BY_LINE_TABLES),
			('ID', mol_id),
			('ISO', iso_id),
			('NP', self._state.npress),
			('NT', self._state.ntemp),
			('WAVE', wavenumbers),
			('PRESS', pressures),
			('TEMP', temperatures),
			('K', opacities)
		):
			dset = h5py_helper.store_data(self._state.fptr, dset_name, data=data)
			for attr_name, attr_val in self.dset_attrs.get(dset_name, dict()).items():
				dset.attrs[attr_name] = attr_val
			if dset_name == 'K':
				self._opac_attrs_written = True

	def write_opacities_part(self, opacities_part : np.ndarray, idxs : tuple[int,int,int]):
		opac_shape = (self._state.nwave, self._state.npress, abs(self._state.ntemp))
		self.write_opacities_chunk_flat(
			np.ravel(opacities_part), 
			np.ravel_multi_index(idxs,dims=opac_shape)
		)

	def write_opacities_chunk_flat(self, opacities_chunk : np.ndarray, start_flat_idx : int):
		opac_shape = (self._state.nwave, self._state.npress, abs(self._state.ntemp))
		n_opac = self.get_opacities_size_items()
		assert start_flat_idx > 0, "Cannot start at non positive index"
		assert start_flat_idx + opacities_chunk.size <= n_opac, "cannot write beyond end of array"
		
		
		
		if start_flat_idx == 0 and opacities_chunk.size == n_opac:
			# we just write the whole array
			dset = h5py_helper.store_data(self._state.fptr, 'K', data=opacities_chunk)
		
		if start_flat_idx != 0 or opacities_chunk.size != n_opac:
			# must write partial array
			if 'K' not in self._state.fptr:
				dset = self._state.fptr.create_dataset('K', shape=opac_shape, dtype=np.float64)
			else:
				dset = self._state.fptr['K']
			
			mask = np.zeros(opac_shape, dtype=bool)
			mask_flat_view = mask.reshape(-1)
			assert mask_flat_view.base is mask, "Must have a view of the array, not a copy"
			
			mask_flat_view[start_flat_idx:(start_flat_idx+opacities_chunk.size)] = True
			data = dset[tuple()]
			data_flat_view = data.reshape(-1)
			assert data_flat_view.base is data, "Must have a view of the array, not a copy"
			
			data_flat_view[mask_flat_view] = opacities_chunk
			
			dset[mask] = data
		
		
		if not self._opac_attrs_written:
			for attr_name, attr_val in self.dset_attrs.get('K', dict()).items():
				dset.attrs[attr_name] = attr_val
			self._opac_attrs_written = True
		
