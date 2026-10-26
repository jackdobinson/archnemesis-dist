
from typing import NamedTuple

import numpy as np


class LblTableData(NamedTuple):
	mol_id       : int        # RADTRAN molecule id number
	iso_id       : int        # RADTRAN molecule isotopologue number
	wavenumbers  : np.ndarray # [nwave] Array of wavenumbers that opacities are calculated at (cm^{-1})
	pressures    : np.ndarray # [npress] Array of pressures that opacities are calculated at (atm)
	temperatures : np.ndarray # [ntemp] | [npress,ntemp] Array of temperatures of opacitiy calcs at each pressure level. if ndim==1, then temperatures are shared across pressure levels (Kelvin)
	opacities    : np.ndarray # [nwave, npress, ntemp] Opacities of specified molecule isotopologue at specified wavelengths, pressures, and temperatures (cm^2)




