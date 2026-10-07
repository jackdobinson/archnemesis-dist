from pathlib import Path

import argparse as ap
import re

#import numpy as np

from matplotlib import pyplot as plt

from archnemesis import LineData_0
from archnemesis.enum import (
	GasEnum,
	AmbientGasEnum,
	WaveUnitEnum,
)

from archnemesis.spectral_data.database.datatypes.wave_range import WaveRange

import archnemesis.cfg.logs as logging
_lgr = logging.getLogger(__name__)
_lgr.setLevel(logging.DEBUG)


_subcommand_name = "plot"
_subcommand_help = "Plot spectral data contained within these files"

def add_subcommand_to(subparser_adder) -> ap.ArgumentParser:

	parser = subparser_adder.add_parser(_subcommand_name, help=_subcommand_help)
	parser.set_defaults(func = _action_plot)
	parser.add_argument('-a', '--ambient_gas', nargs='+', choices=(x.name for x in AmbientGasEnum), help='Ambient gasses to use when computing line absorption parameters (default="AIR")', default='AIR')
	parser.add_argument('-w', '--waves', type=float, nargs=2, help='Minimum and maximum waves to include in plots, unit set by `--wave_unit` (default=[1E-2,2])', default=None)
	parser.add_argument('-u', '--wave_unit', type=lambda x: WaveUnitEnum[x], choices=(x.name for x in WaveUnitEnum), help='Unit of `--waves` (default="Wavelength_um")', default=WaveUnitEnum.Wavelength_um)
	parser.add_argument('-s', '--s_min', type=float, help='Strength floor above which a line is treated as a discrete line, not part of a continuum (default=0)', default=0.0)
	parser.add_argument('-T', '--t_calc', type=float, help='Temperature (Kelvin) at which to perform calculations (default=296)', default=296.0)
	parser.add_argument('-P', '--p_calc', type=float, help='Pressure at which to perform calculations, unit is set via `--p_unit` (default=1)', default=1.0)
	parser.add_argument('--p_unit', type=str, choices=('atm', 'bar'), help='Unit of pressure to perform calculations with (default="bar")', default='bar')
	
	
def _action_plot(
	line_database : Path,
	partition_function_database : None | Path,
	pseudo_continuum_database : None | Path,
	mol_regex : re.Pattern = re.compile('.*'),
	iso_regex : re.Pattern = re.compile('.*'),
	ambient_gas : str | tuple[str,...] = 'AIR',
	waves : None | tuple[float,float] = None,
	wave_unit : WaveUnitEnum = WaveUnitEnum.Wavelength_um,
	s_min : float = 0.0,
	t_calc : float = 296.0,
	p_calc : float = 1.0,
	p_unit : str = 'bar',

):
	if waves is None:
		waves = (1E-2, 2)
	_lgr.info(f'{line_database=}')
	_lgr.info(f'{partition_function_database=}')
	_lgr.info(f'{pseudo_continuum_database=}')
	_lgr.info(f'{mol_regex=}')
	_lgr.info(f'{iso_regex=}')
	_lgr.info(f'{ambient_gas=}')
	_lgr.info(f'{waves=}')
	_lgr.info(f'{wave_unit=}')
	_lgr.info(f'{s_min=}')
	_lgr.info(f'{t_calc=}')
	_lgr.info(f'{p_calc=}')
	_lgr.info(f'{p_unit=}')
	
	# Get pressure into units of `bar` before doing anything else
	known_p_units = ('bar', 'atm')
	if p_unit not in known_p_units:
		raise RuntimeError(f'Cannot plot spectra data. Pressure unit `p_unit` is unknown ({p_unit}), it must be one of {known_p_units}')
	p_calc = p_calc if p_unit == 'bar' else (p_calc*0.986923)
	
	# Get waves into wavenumbers for all subsequent calcs
	vmin, vmax = WaveRange(*waves, WaveUnitEnum.Wavelength_um).as_unit(WaveUnitEnum.Wavenumber_cm).values()
	
	match_mol_regex = lambda x: mol_regex.fullmatch(x.name) is not None
	match_iso_regex = lambda x: mol_regex.fullmatch(str(x)) is not None
	
	gas_enums = tuple(filter(match_mol_regex, (x for x in GasEnum)))
	iso_ids = (0,) if iso_regex.pattern == '.*' else tuple(filter(match_iso_regex, range(1,100)))
	ambient_gas_tpl = (AmbientGasEnum[ambient_gas],) if isinstance(ambient_gas, str) else tuple(AmbientGasEnum[x] for x in ambient_gas)

	if len(gas_enums) == 0:
		_lgr.warn(f"Cannot plot spectral data. No gasses were selected. `mol_regex` is '{mol_regex.pattern}'")
		return
	
	if len(iso_ids) == 0:
		_lgr.warn(f"Cannot plot spectral data. No iso_ids were selected. `iso_regex` is '{iso_regex.pattern}'")
		return
	
	_lgr.info(f'{gas_enums=}')
	_lgr.info(f'{iso_ids=}')
	_lgr.info(f'{ambient_gas_tpl=}')


	mol_iso_pairs = []
	for mol_enum in gas_enums:
		for iso_id in iso_ids:
			mol_iso_pairs.append((mol_enum, iso_id))
			_lgr.debug(f'mol_iso_pairs[{len(mol_iso_pairs)-1}] = ({mol_enum}, {iso_id})')
	
	
	line_data_instances = dict()
	for mol_iso_pair in mol_iso_pairs:
		line_data_instances[mol_iso_pair] = LineData_0(
			ID = mol_iso_pair[0],
			ISO = mol_iso_pair[1],
			ambient_gasses = ambient_gas_tpl,
			LINE_DATABASE = line_database,
			PARTITION_FUNCTION_DATABASE = partition_function_database if partition_function_database is not None else line_database,
			CONTINUUM_DATABASE = pseudo_continuum_database if pseudo_continuum_database is not None else line_database
		)
		
		
	for mol_iso_pair, line_data_instance in line_data_instances.items():
		line_data_instance.set_params(
			vmin = vmin,
			vmax = vmax,
			s_min = s_min,
			t_req = t_calc,
			p_req = p_calc,
		)
		
		line_data_instance.fetch_linedata()
		
		line_strengths = line_data_instance.calculate_line_strength(t_calc=t_calc, combined_output=True)

		print(f'{line_strengths.shape=}')
		print(f'{line_data_instance.combined_line_data.NU.shape=}')

		plt.plot(line_data_instance.combined_line_data.NU, line_strengths, linestyle='none', marker='.', markersize=2)
		plt.title(f'Line strength for ({line_data_instance.ID}, {line_data_instance.ISO})\n{t_calc=} t_ref={[int(x.t_ref) for x in line_data_instance.line_data]}')
		plt.xlabel('Wavenumber (cm^{-1})')
		plt.ylabel('Line Strength (cm^{-1} / [molec cm^{-2}])')
		plt.yscale('log')
		plt.show()
	
	
	
	