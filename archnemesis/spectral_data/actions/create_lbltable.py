
import os
from pathlib import Path

import argparse as ap
import datetime as dt

import numpy as np
from joblib import Parallel, delayed

from archnemesis.enum import (
	WaveUnitEnum,
	AmbientGasEnum,
)

from archnemesis.helpers.argparse_helper import ArgArray1D, action_enum_choice
#from archnemesis.helpers.wave_helper import waves_as_unit

from archnemesis.Data.constants import atm_pascal
from archnemesis.LineData_0 import LineData_0, _MODULE_CACHE

from ..mol_selector import MolSelector
from ..filetypes.lbltable.file import LblTableFile

import archnemesis.cfg.logs as logging
_lgr = logging.getLogger(__name__)
_lgr.setLevel(logging.INFO)


_subcommand_name = "create_lbltable"
_subcommand_help = "Create line-by-line tables for specified molecules using data from specified database files."





def add_subcommand_to(subparser_adder) -> ap.ArgumentParser:

	parser = subparser_adder.add_parser(_subcommand_name, help=_subcommand_help)
	parser.set_defaults(func = _action_create_lbltable)
	
	parser.add_argument('-a', '--ambient_gas', nargs='+', choices=tuple(x.name for x in AmbientGasEnum), help='Ambient gasses to use when computing opacity (default="AIR")', default='AIR')
	parser.add_argument('-f', '--ambient_gas_fractions', type=float, help='Ambient gasses fractions to use when computing opacity (default=0.5)', default=None)
	ArgArray1D.add_to_parser(parser, 'wave', required=True, description='Waves at which to compute opacity. Unit set by `--wave_unit` (default is wavenumbers in cm^{-1})', default=np.empty((0,)))
	ArgArray1D.add_to_parser(parser, 'press', required=False, description='Pressures (atm) at which to compute opacity', enable_log=True, default=np.empty((0,)))
	ArgArray1D.add_to_parser(parser, 'temp', required=False, description='Temperatures (Kelvin) at which to compute opacity', default=np.empty((0,)))
	
	parser.add_argument(
		"--use_atm_profile", 
		type=Path,
		metavar='<path>', 
		help='Set the pressure and temperature arrays from a specified a atmospheric profile (`.prf` or `.h5`) file. NOTE: Conflicts with setting pressure and temperature via another means.', 
		default=None
	)
	parser.add_argument('--wave_unit', action=action_enum_choice(WaveUnitEnum), help=f'The unit that the `wave` array is specified in (default={WaveUnitEnum.Wavenumber_cm.name})', default=WaveUnitEnum.Wavenumber_cm)
	parser.add_argument('--wn_approx_window', type=float, help='Wavenumber (cm^{-1}) window within which to perform approximate calculations (default=75.0)', default=75.0)
	parser.add_argument('--wn_calc_window', type=float, help='Wavenumber (cm^{-1}) calculation window (default=25.0)', default=25.0)
	parser.add_argument('--s_min', type=float, help='Strength floor of non-continuum lines (default=0.0)', default=0.0)
	parser.add_argument('--output_prefix', help='Prefix of output file (default="lbl")', default="lbl")
	parser.add_argument('-n', '--n_cores', type=int, help='Number of cores to use when calculating line-by-line table. Special numbers: 0 = all available; -ve = number of cores on system minus specified number; +ve = number of cores to use. Always capped at number of logical cores on system. (default=-2)', default=-2)
	parser.add_argument('--no_cache', action='store_true', help='If present, not cache anything (may be useful to save memory)', default=False)


def _create_lbltable_name(output_prefix : str, mol_name : str, iso_id : int, wave_unit : str):
	return output_prefix+f'__{mol_name}_iso_{iso_id}_unit_{wave_unit}.lta'



def _action_create_lbltable(
	line_database : Path,
	partition_function_database : None | Path,
	pseudo_continuum_database : None | Path,
	mol_selector : MolSelector = MolSelector.create_match_all(),
	ambient_gas : str | tuple[str,...] = 'AIR',
	ambient_gas_fractions : None | list[float] = None,
	wave_array : np.ndarray = np.empty((0,)),
	press_array : np.ndarray = np.empty((0,)),
	temp_array : np.ndarray = np.empty((0,)),
	use_atm_profile : None | Path = None,
	wave_unit : WaveUnitEnum = WaveUnitEnum.Wavenumber_cm,
	wn_approx_window : float = 75.0,
	wn_calc_window : float = 25.0,
	s_min : float = 0.0,
	output_prefix : str = "lbl",
	n_cores : int = -2,
	no_cache : bool = False
):
	_lgr.info(f'{line_database=}')
	_lgr.info(f'{partition_function_database=}')
	_lgr.info(f'{pseudo_continuum_database=}')
	_lgr.info(f'{mol_selector=}')
	_lgr.info(f'{ambient_gas=}')
	_lgr.info(f'{wave_array=}')
	_lgr.info(f'{use_atm_profile=}')
	
	
	_lgr.info(f'{wn_approx_window=}')
	_lgr.info(f'{wn_calc_window=}')
	_lgr.info(f'{s_min=}')
	_lgr.info(f'{output_prefix=}')
	
	# n_cores = number of CPUs if 0, CPUs - |n_cores| if -ve (or 1); n_cores or CPUs if n_cores > CPUs
	n_cores = os.cpu_count() if (n_cores == 0) else (max(1,os.cpu_count()+n_cores) if (n_cores < 0) else min(os.cpu_count(),n_cores) )
	_lgr.info(f'{n_cores=}')
	
	if use_atm_profile is None and press_array.size ==0 and temp_array.size == 0:
		raise RuntimeError('Must set temperature and pressure via `--use_atm_profile` or one of the `--temp_*` `--press_*` arguments')
	
	if use_atm_profile is not None:
		if press_array.size !=0 or temp_array.size != 0:
			raise RuntimeError('Setting temperature and pressure via `--use_atm_profile` conflicts with setting T and P via any other means.')
		
		from archnemesis.Atmosphere_0 import Atmosphere_0
		if use_atm_profile.suffix == '.h5':
			atm = Atmosphere_0()
			atm.read_hdf5(use_atm_profile)
			
		elif use_atm_profile.suffix == '.ref':
			atm = Atmosphere_0(use_atm_profile)
			atm.read_ref()
		
		else:
			raise RuntimeError(f'Cannot read atmospheric profile from {use_atm_profile}')
		
		press_array = np.array(atm.P) / atm_pascal # Get pressure into atmospheres
		temp_array = np.array([atm.T, atm.T+5]).T

		del Atmosphere_0
		del atm
	
	_lgr.info(f'{press_array=}')
	_lgr.info(f'{temp_array=}')
	
	mol_iso_pairs = mol_selector.get_matching_mol_iso_pairs_from_enums()
	ambient_gas_tpl = (AmbientGasEnum[ambient_gas],) if isinstance(ambient_gas, str) else tuple(AmbientGasEnum[x] for x in ambient_gas)
	ambient_gas_fractions = np.array(ambient_gas_fractions if ambient_gas_fractions is not None else [0.5], dtype=float)
	
	_lgr.info(f'{ambient_gas_fractions=}')
	
	
	
	if n_cores != 1:
		k_result_index_list = []
		k_result_list = []
		
		lbl_file_handles = [
			LblTableFile(Path(_create_lbltable_name(output_prefix, mol_iso_pair[0].name, mol_iso_pair[1], wave_unit.name.lower())), "w") for mol_iso_pair in mol_iso_pairs]
		
		_lgr.info('Writing all data except opacity to lbl-table files...')
		for mol_iso_idx, lbl_file_handle in enumerate(lbl_file_handles):
			opac_shape = (wave_array.size, press_array.size, temp_array.shape[-1])
			lbl_file_handle.write(mol_iso_pairs[mol_iso_idx][0], mol_iso_pairs[mol_iso_idx][1], wave_array, press_array, temp_array, np.full(opac_shape, fill_value=np.nan))
		
		
		def perform_monochromatic_absorption_calculation(job_idx, line_data_instance, monochromatic_absorption_kwargs):
			dt_start = dt.datetime.now()
			print(f'create_lbltable :: [{dt_start}] Starting job {job_idx}')
			
			# Turn off some logging to avoid loads of output
			import warnings
			import archnemesis.cfg.logs as logging
			logging.pkg_lgr.setLevel(logging.ERROR)
			
			with warnings.catch_warnings():
				warnings.filterwarnings('ignore')
				line_data_instance.fetch_linedata()
				
				k_partial = line_data_instance.calculate_monochromatic_absorption(
					**monochromatic_absorption_kwargs
				)
			return job_idx, dt.datetime.now() - dt_start, k_partial
		
		def generate_calculation_args():
			
			for mol_iso_idx, mol_iso_pair in enumerate(mol_iso_pairs):
				_lgr.info(f'Getting calculation arguments for {mol_iso_pair} [{mol_iso_idx}/{len(mol_iso_pairs)}]')

				k_result_list.append(
					np.full((wave_array.size, press_array.size, (temp_array.shape[1] if temp_array.ndim == 2 else temp_array.size)), fill_value=np.nan)
				)
				
				for i, p_calc in enumerate(press_array):
					temp_array_part = temp_array[i] if temp_array.ndim == 2 else temp_array
					for j, t_calc in enumerate(temp_array_part):
						
						k_result_index_list.append(
							(mol_iso_idx, i, j)
						)
						
						# Each parallel calculation needs its own LineData_0 instance as we cannot be sure of the execution order
						line_data_instance = LineData_0(
							ID = mol_iso_pair[0],
							ISO = mol_iso_pair[1],
							ambient_gasses = ambient_gas_tpl,
							LINE_DATABASE = line_database,
							PARTITION_FUNCTION_DATABASE = partition_function_database if partition_function_database is not None else line_database,
							CONTINUUM_DATABASE = pseudo_continuum_database if pseudo_continuum_database is not None else line_database,
							cache=None if no_cache else _MODULE_CACHE,
						)
						
						# may as well set this here instead of later
						line_data_instance.set_params( 
							vmin = np.min(wave_array) - 2*wn_approx_window,
							vmax = np.max(wave_array) + 2*wn_approx_window,
							s_min = s_min,
							t_req = t_calc,
							p_req = p_calc,
							wave_unit = wave_unit,
						)
						
						yield (
								line_data_instance,
								dict(
									wave_grid=wave_array, 
									t_calc=t_calc, 
									p_calc=p_calc, 
									amb_frac = ambient_gas_fractions,
									wave_unit = wave_unit,
									wn_calc_window = wn_calc_window,
									wn_approx_window = wn_approx_window,
									combined_output=True,
									use_cache=False,
								)
							)
	
		n_total_jobs = len(mol_iso_pairs) * press_array.size * temp_array.shape[-1]
		_lgr.info(f'Will execute {n_total_jobs} jobs using {n_cores} cores.')
	
		dt_start = dt.datetime.now()
		workers = Parallel(n_jobs=n_cores, prefer="threads", return_as='generator_unordered')(
			delayed(perform_monochromatic_absorption_calculation)(
				job_idx,
				*calc_args,
			)
			for job_idx, calc_args in enumerate(generate_calculation_args())
		)

		for zz, (job_idx, elapsed_time, k_partial) in enumerate(workers):
			dt_end=dt.datetime.now()
			print(f'create_lbltable :: [{dt_end}] Finished job {job_idx} [{zz+1}/{n_total_jobs}] :: job elapsed time {elapsed_time} :: total elapsed time {dt_end - dt_start}')
			
			
			# set values from result
			mol_iso_idx, i, j = k_result_index_list[job_idx]
			
			assert not np.any(np.isnan(k_partial)), f"Absorption coefficients for {mol_iso_pairs[mol_iso_idx][0].name}[{mol_iso_pairs[mol_iso_idx][1]}] must not be NAN at any point but have NANs at indices {np.argwhere(np.isnan(k_partial))} at press_idx {i} temp_idx {j}"
			
			lbl_file_handles[mol_iso_idx].write_opacities_part(k_partial, i, j)
			
			#k_result_list[mol_iso_idx][:,i,j] = k_partial
			
		
		
		
		# Reset logging level
		logging.pkg_lgr.setLevel(logging.DEBUG)
		
		# Close files
		for lbl_file_handle in lbl_file_handles:
			lbl_file_handle.close()
			_lgr.info(f'Writte line-by-line file at "{lbl_file_handle.path}"')
		
		#for mol_iso_idx, k in enumerate(k_result_list):
		#	assert not np.any(np.isnan(k)), f"Absorption coefficients for {mol_iso_pairs[mol_iso_idx][0].name}[{mol_iso_pairs[mol_iso_idx][1]}] must not be NAN at any point but have NANs at indices {np.argwhere(np.isnan(k))}"
		#	with LblTableFile(Path(output_prefix+f'__{mol_iso_pairs[mol_iso_idx][0].name}_iso_{mol_iso_pairs[mol_iso_idx][1]}_unit_wavelength_um.lta'), "w") as f:
		#		f.write(mol_iso_pairs[mol_iso_idx][0], mol_iso_pairs[mol_iso_idx][1], wave_array, press_array, temp_array, k)
		
	
	else:
		for mol_iso_idx, mol_iso_pair in enumerate(mol_iso_pairs):
			_lgr.info(f'Loading line data for {mol_iso_pair} [{mol_iso_idx}/{len(mol_iso_pairs)}]')
			line_data_instance = LineData_0(
				ID = mol_iso_pair[0],
				ISO = mol_iso_pair[1],
				ambient_gasses = ambient_gas_tpl,
				LINE_DATABASE = line_database,
				PARTITION_FUNCTION_DATABASE = partition_function_database if partition_function_database is not None else line_database,
				CONTINUUM_DATABASE = pseudo_continuum_database if pseudo_continuum_database is not None else line_database,
				cache=None if no_cache else _MODULE_CACHE,
			)
			
			
			k = np.full((wave_array.size, press_array.size, temp_array.shape[1] if temp_array.ndim == 2 else temp_array.size), fill_value=np.nan)
			
			for i, p_calc in enumerate(press_array):
				temp_array_part = temp_array[i] if temp_array.ndim == 2 else temp_array
				for j, t_calc in enumerate(temp_array_part):
					_lgr.info(f'Getting line data for {p_calc=} [{i}/{press_array.size}] {t_calc=} [{j}/{temp_array_part.size}]')
					line_data_instance.set_params(
						vmin = np.min(wave_array) - 2*wn_approx_window,
						vmax = np.max(wave_array) + 2*wn_approx_window,
						s_min = s_min,
						t_req = t_calc,
						p_req = p_calc,
						wave_unit = wave_unit,
					)
					
					line_data_instance.fetch_linedata()
					
					_lgr.info(f'Calculating absorption coefficients for {wave_array.size} wavenumbers at {p_calc=} [{i}/{press_array.size}] {t_calc=} [{j}/{temp_array_part.size}]')
					
					k[:,i,j] = line_data_instance.calculate_monochromatic_absorption(
						wave_array, 
						t_calc=t_calc, 
						p_calc=p_calc, 
						amb_frac = ambient_gas_fractions,
						wave_unit = wave_unit,
						wn_calc_window = wn_calc_window,
						wn_approx_window = wn_approx_window,
						combined_output=True,
						use_cache=False,
					)
			
			assert not np.any(np.isnan(k)), f"Absorption coefficient must not be NAN at any point but have NANs at indices {np.argwhere(np.isnan(k))}"
			with LblTableFile(Path(_create_lbltable_name(output_prefix, mol_iso_pair[0].name, mol_iso_pair[1], wave_unit.name.lower())), "w") as f:
				f.write(mol_iso_pair[0], mol_iso_pair[1], wave_array, press_array, temp_array, k)