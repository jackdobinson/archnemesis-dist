

from archnemesis.enum import WaveUnitEnum


def waves_as_unit(waves, from_unit : WaveUnitEnum, to_unit : WaveUnitEnum):
	if from_unit == to_unit:
		return waves
	
	if from_unit != WaveUnitEnum.Wavenumber_cm:
		if from_unit == WaveUnitEnum.Wavelength_um:
			wn = 1.0/(waves*1E-4)
		else:
			raise RuntimeError(f'Unknown unit {from_unit}')
	else:
		wn = waves
	
	if to_unit == WaveUnitEnum.Wavenumber_cm:
		return wn
	elif to_unit == WaveUnitEnum.Wavelength_um:
		return 1E4 / waves
	else:
		raise RuntimeError(f'Unknown unit {to_unit}')
