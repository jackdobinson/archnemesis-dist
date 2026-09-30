
from pathlib import Path
import dataclasses as dc
from typing import Self

from .filename_format import iso_slug_to_iso_name, mol_spec_from_iso_name

@dc.dataclass
class PCDataFileSet:
	t_cont : float
	mol_spec : tuple
	iso_name : str
	ds_name : str
	s_max : float = 1E-26
	contbins : None | Path = None
	continuum : None | Path = None
	stronglines : None | Path = None
	
	@staticmethod
	def parse_fname(fname : str) -> tuple:
		x = fname
		x, ftype = x.rsplit('.', 1)
		x, s_max = x.rsplit('_S', 1)
		x, t_cont = x.rsplit('_T', 1)
		x, dsname = x.rsplit('__', 1)
		iso_slug = x
		
		known_ftypes = ('contbins', 'continuum', 'stronglines')
		if ftype not in known_ftypes:
			raise RuntimeError(f'Pseudo-continuum file extension {ftype} not recognised, must be one of {known_ftypes}')
		
		return (ftype, iso_slug, dsname, float(t_cont), float(s_max))
	
	@classmethod
	def from_path(cls, fpath : Path) -> Self:
		# 12C-1H4__YT10to10_T240.0.continuum
		# 12C-1H4__YT10to10_T240.0.contbins
		# 12C-1H4__YT10to10_T240.0.stronglines
		ftype, iso_slug, dsname, t_cont, s_max = cls.parse_fname(fpath.name)
		
		iso_name = iso_slug_to_iso_name(iso_slug)
		
		known_ftypes = ('.contbins', '.continuum', '.stronglines') # Must be in same order as in class definition
		found_ftype_paths = [None, None, None]
		
		for i, x in enumerate(known_ftypes):
			if fpath.with_suffix(x).exists():
				found_ftype_paths[i] = fpath.with_suffix(x)

		return cls(
			t_cont,
			mol_spec_from_iso_name(iso_name),
			iso_name,
			dsname,
			s_max,
			*found_ftype_paths
		)