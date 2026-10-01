from pathlib import Path
from typing import Iterable, Any

import numpy as np

from .filesets import PCDataFileSet
from .structured_array import fromfile as structured_array_from_file
from .filename_format import get_rt_mol_iso_ids, iso_slug_to_iso_name, mol_spec_from_iso_name


from archnemesis.database.filetypes.ans_pseudo_continuum_file import AnsPseudoContinuumFile
from archnemesis.database.filetypes.ans_line_data_file import AnsLineDataFile
from archnemesis.database.filetypes.ans_partition_fn_data_file import AnsPartitionFunctionDataFile



from archnemesis.database.data_holders.partition_function_data_holder import PartitionFunctionDataHolder
from archnemesis.database.datatypes.pf_data.tabulated_pf_data import TabulatedPFData
from archnemesis.database.data_holders.pseudo_continuum_data_holder import PseudoContinuumDataHolder
from archnemesis.database.data_holders.pseudo_continuum_broadener_part import PseudoContinuumBroadenerPart
from archnemesis.database.data_holders.line_data_holder import LineDataHolder
from archnemesis.database.data_holders.line_broadener_holder import LineBroadenerHolder

import archnemesis.cfg.logs as logging
_lgr = logging.getLogger(__name__)
_lgr.setLevel(logging.INFO)
#_lgr.setLevel(logging.DEBUG)

class ATTR_MISSING:
	pass

class ATTR_REQUIRED:
	pass


def get_filesets(dir : Path) -> dict[dict[str,list[PCDataFileSet]]]:

	progress_fpaths = []
	for fpath in dir.iterdir():
		if fpath.suffix == ".cont_progress":
			progress_fpaths.append(fpath)
	
	pc_data_files = []
	
	for progress_fpath in progress_fpaths:
		pc_data_files_list = []
		with open(progress_fpath, 'r') as f:
			x = f.readline().strip()
			assert x.endswith('.stronglines'), "Stronglines file should be first entry in progress file"
			stronglines_fpath = progress_fpath.parent / x
			
			
			x = f.readline().strip()
			assert x.endswith('.continuum'), "Stronglines file should be first entry in progress file"
			continuum_fpath = progress_fpath.parent / x
			
			x = f.readline().strip()
			assert x.endswith('.contbins'), "Stronglines file should be first entry in progress file"
			#contbins_path = progress_fpath.parent / x
			
			pc_data_files_list.append(PCDataFileSet.from_path(continuum_fpath))
			
			expect_ending = ('.contbins', '.continuum')
			
			i=0
			for aline in f:
				x = aline.strip()
				if x.endswith(expect_ending[i]) :
					if i==0:
						pc_data_files_list.append(PCDataFileSet.from_path(progress_fpath.parent / x))
					i = (i+1)%2
			
		pc_data_file_entry = (
			stronglines_fpath,
			pc_data_files_list
		)

		pc_data_files.append(pc_data_file_entry)
	
	filesets : dict[dict[str,tuple(Path,list[PCDataFileSet])]] = {}
	
	
	for stronglines_fpath, pc_dfs in pc_data_files:
		x = filesets.setdefault(pc_dfs[0].iso_name, dict())
		x[pc_dfs[0].ds_name] = (stronglines_fpath, pc_dfs)
	
	return filesets


def read_cont_data(pc_dfs):
	cont_bin_edge = np.fromfile(pc_dfs.contbins)
	#_lgr.debug(f'{cont_bin_edge=}')
	cont_bin_center = 0.5*(cont_bin_edge[:-1] +cont_bin_edge[1:])
	#_lgr.debug(f'{cont_bin_center=}')
	cont_bin_width = np.diff(cont_bin_edge)
	#_lgr.debug(f'{cont_bin_width=}')

	cont_data = structured_array_from_file(pc_dfs.continuum)
	
	return cont_bin_center, cont_bin_width, cont_data



def add_partition_files_to(
		ans_pf_file : AnsPartitionFunctionDataFile, 
		pf_files : Iterable[Path,...]
):
	pfdh_dict = {}
	
	for pf_file in pf_files:
		iso_slug, ds_name = pf_file.stem.split('__', 1)
		iso_name = iso_slug_to_iso_name(iso_slug)
		_lgr.debug(f'{pf_file=}')
		_lgr.debug(f'{iso_slug=} {ds_name=} {iso_name=}')
		
		pfdh_tabulated = pfdh_dict.setdefault(
			(iso_name, ds_name),
			PartitionFunctionDataHolder(
				ds_name,
				f"This data was created from files at {pf_file.parent}. With iso_slug `{iso_slug}` dataset name {ds_name}",
			)
		)
		
		rt_mol_id, rt_iso_id = get_rt_mol_iso_ids(
			mol_spec_from_iso_name(iso_name), 
			iso_name
		)
		
		pf_array = np.loadtxt(pf_file, dtype=float).reshape(-1,2)
		temp = pf_array[:,0]
		q = pf_array[:,1]
		
		_lgr.debug(f'{temp[:10]=}')
		_lgr.debug(f'{q[:10]=}')
		
		tab_pf_data = TabulatedPFData(
			temp,
			q
		)
		
		pfdh_tabulated.add(
			rt_mol_id,
			rt_iso_id,
			tab_pf_data
		)
	
	for (iso_name, ds_name), pfdh in pfdh_dict.items():
		ans_pf_file.add_source_data(pfdh.name, pfdh, pfdh.description)
		_lgr.info(f'ADDED PARTITION FUNCTION DATA FOR {iso_name} {ds_name} ...')
	
	return




def get_attrs_from_sdsh_filename(fname : str) -> dict[str,Any]:
	"""
	Get the attributes stored in "spectral data source helper" filename.
	
	Assume filename is always of format `<pos_attr_1><pos_sep><pos_attr_2><prefix_sep><attr_3_prefix><attr_3_value><prefix_sep><attr_4_prefix><attr_4_value><ext>`
	"""
	attrs = dict()
	ext_attr_parser_map = { # Keys are tuple of strings that extension should match to apply values
		('.continuum', '.contbins', '.stronglines') : {
			'pos_attrs' : { # positional attributes
				'sep' : '__', # Separator for positional attributes
				'names' : ('iso_slug', 'ds_name'), # Attribute names
				'parsers' : (str, str), # functions that parse the attribute string representation and return the values we want
			}
		},
		('.continuum', '.contbins') : {
			'prefix_attrs' : { # Prefixed attributes
				'sep'   : '_', # Separator between prefixed attributes
				'names' : { # Map from attribute prefix to attribute name
					'S' : 's_max', # Maximum strength included in pseudo-continuum, 
					'T' : 't_cont', # Temperature that pseudo-continuum was calculated at
				},
				'parsers' : {  # functions that parse the attribute string representation and return the values we want
					's_max' : float,
					't_cont' : float,
				},
				'defaults' : {
					's_max' : ATTR_REQUIRED,
					't_cont' : ATTR_REQUIRED,
				}
			}
		},
		('.stronglines',) : {
			'prefix_attrs' : {
				'sep'   : '_', # Separator between prefixed attributes
				'names' : {
					'S' : 's_min', # Line strength lower bound. The line strength of all lines is larger than this value (when calculated at pseudo-continuum temperature)
					'T' : 't_str', # If present, the temperature that `s_min` is calculated at. If omitted, the file contains the union of all lines for all pseudo-continuum temperatures, therefore must compute line strength at `t_cont` and ignore lines with strength equal to or lower than `s_min` (as those are already included in the pseudo-continuum).
				},
				'parsers' : {  # functions that parse the attribute string representation and return the values we want
					's_min' : float,
					't_str' : float,
				},
				'defaults' : {
					's_min' : ATTR_REQUIRED,
					't_str' : ATTR_MISSING,
				}
			}
		}
	}
	
	stem, ext = fname.rsplit('.',1) if '.' in fname else (fname,None)
	ext = '.'+ext
	
	remainder = stem
	
	default_attrs = dict() # names and defaults of all arguments we should have
	
	last_positional_name = None
	last_positional_parser = None
	
	for exts, attr_parser_dict in ext_attr_parser_map.items():
		_lgr.debug(f'{ext=} {exts=}')
		if ext in exts:
			_lgr.debug('HIT')
			if (pos_attrs := attr_parser_dict.get('pos_attrs',None)) is not None:
				# Positional attributes are always at the start, so consume from left to right
				for n in pos_attrs['names']:
					default_attrs[n] = ATTR_REQUIRED # Positional arguments are always required
				
				if ((pos_attrs['sep'] in remainder) and ((len(pos_attrs['names'])-1) > 0)):
					i = remainder.rindex(pos_attrs['sep'])
					x = remainder[:i]
					one_less_positionals = tuple(x.split(pos_attrs['sep']))
					remainder = remainder[i+len(pos_attrs['sep']):]
				else:
					one_less_positionals = tuple()
				
				_lgr.debug(f'{one_less_positionals=}')
				last_positional_name = pos_attrs['names'][-1]
				last_positional_parser = pos_attrs['parsers'][-1]
				
				for x, n, p in zip(one_less_positionals, pos_attrs['names'][:-1], pos_attrs['parsers'][:-1]):
					attrs[n] = p(x)
				
			if (prefix_attrs := attr_parser_dict.get('prefix_attrs',None)) is not None:
				for n in prefix_attrs['names'].values():
					default_attrs[n] = prefix_attrs['defaults'][n]
				
				p_sep = prefix_attrs['sep']
				p_idxs = []
				p_names = []
				p_tags = []
				for prefix, name in prefix_attrs['names'].items():
					s = p_sep+prefix
					if s in remainder:
						p_idxs.append(remainder.index(s))
						p_names.append(name)
						p_tags.append(s)
				
				for idx in sorted(p_idxs, reverse=True):
					j = p_idxs.index(idx)
					n = p_names[j]
					q = remainder[idx:]
					remainder = remainder[:idx]
					attrs[n] = prefix_attrs['parsers'][n](q[len(p_tags[j]):])
	
	# Finally deal with last positional if present
	if last_positional_name is not None:
		attrs[last_positional_name] = last_positional_parser(remainder)
	
	# Now validate that we have the correct attrs, and add defaults if needed
	for n, d in default_attrs.items():
		if n not in attrs:
			if d is ATTR_REQUIRED:
				raise AttributeError(f'String "{fname}" must include required attribute {n}')
			else:
				attrs[n] = d
	
	return attrs
	
	

def add_line_data_file_to(
		ans_ld_file : AnsLineDataFile,
		ld_fpath : Path,
):
	_lgr.info(f'Adding line data from "{ld_fpath!s}" to "{ans_ld_file.path!s}"')
	ld_attrs = get_attrs_from_sdsh_filename(ld_fpath.name)
	iso_slug = ld_attrs['iso_slug']
	ds_name = ld_attrs['ds_name']
	s_min = ld_attrs['s_min']
	assert ld_attrs['t_str'] is ATTR_MISSING, f"Expected no `t_str` attribute in filename of '{ld_fpath}'"
	
	_lgr.info(f'{iso_slug=} {ds_name=} {s_min=}')
	iso_name = iso_slug_to_iso_name(iso_slug)
	_lgr.info(f'{iso_name=}')
	mol_spec = mol_spec_from_iso_name(iso_name)
	_lgr.info(f'{mol_spec=}')
	
	rt_mol_id, rt_iso_id = get_rt_mol_iso_ids(mol_spec, iso_name)
	
	_lgr.info(f'Loading line data from "{ld_fpath.name}"...')
	stronglines_data = structured_array_from_file(ld_fpath)
	_lgr.info(f'Loaded line data from "{ld_fpath.name}".')
	
	broadener_names = tuple(x[len("gamma_"):] for x in stronglines_data.dtype.names if (x.startswith("gamma_") and not x.endswith('self')))
	
	_lgr.info(f'Creating line data holder for iso_slug `{iso_slug}` dataset name `{ds_name}`')
	ld_dh = LineDataHolder(
		ds_name,
		f"This data was created from files at {ld_fpath.parent!s}. With iso_slug `{iso_slug}` dataset name `{ds_name}`",
		
		s_min = s_min,
		t_ref = 296, # TODO: Make this vary with whatever the source is
		
		mol_id = np.ones_like(stronglines_data['wavenumber'], dtype=int)*rt_mol_id,
		local_iso_id = np.ones_like(stronglines_data['wavenumber'], dtype=int)*rt_iso_id,
		nu = stronglines_data['wavenumber'],
		sw = stronglines_data['spec_line_intensity'],
		a = stronglines_data['einstein_A'],
		elower = stronglines_data['E"'],
		
		gamma_self = stronglines_data['gamma_self'],
		n_self = stronglines_data['n_self'],
		
		broadeners = tuple(
			LineBroadenerHolder(
				name = x.upper() if x in ('air',) else x,
				gamma_amb = stronglines_data[f'gamma_{x}'],
				n_amb = stronglines_data[f'n_{x}'],
				delta_amb = np.zeros_like(stronglines_data[f'gamma_{x}']),
			) for x in broadener_names
		),
	)
	
	_lgr.info('Adding line data to database ...')
	ans_ld_file.add_source_data(
		ld_dh.name,
		ld_dh,
		ld_dh.description
	)
	
	_lgr.info(f'ADDED LINE DATA FOR {iso_name} {ds_name} ...')
	
	return

def add_pseudo_continuum_data_file_set_to(
		ans_pc_file : AnsPseudoContinuumFile,
		pc_dfs : PCDataFileSet,
):
	iso_slug = pc_dfs.continuum.name.split('__',1)[0]
	
	cont_bin_center, cont_bin_width, cont_data = read_cont_data(pc_dfs)
	_lgr.debug(f'{cont_bin_center[:10]=} {cont_bin_width[:10]=} {cont_data[:10]=}')
	
	rt_mol_id, rt_iso_id = get_rt_mol_iso_ids(pc_dfs.mol_spec, pc_dfs.iso_name)
	_lgr.debug(f'LOOP: {rt_mol_id=} {rt_iso_id=}')
	
	broadener_names = tuple(x[len("strength_weighted_gamma_"):] for x in cont_data.dtype.names if (x.startswith("strength_weighted_gamma_") and not x.endswith('self')))
	_lgr.debug(f'{broadener_names=}')


	zeros = np.zeros_like(cont_data['line_strength_sum'])
	nonzero_line_strength_sum = cont_data['line_strength_sum'] != 0
	
	
	
	_lgr.info(f'Creating pseudo-continuum line data holder for iso_slug `{iso_slug}` dataset name `{pc_dfs.ds_name}`')
	pc_dh = PseudoContinuumDataHolder(
		pc_dfs.ds_name,
		f"This data was created from files at {pc_dfs.continuum.parent}. With iso_slug `{iso_slug}` dataset name `{pc_dfs.ds_name}`",
		
		t_cont = pc_dfs.t_cont,
		s_max = pc_dfs.s_max, 
		
		mol_id = rt_mol_id * np.ones_like(cont_bin_center, dtype=int),
		local_iso_id = rt_iso_id * np.ones_like(cont_bin_center, dtype=int),
		
		wn_bin_center = cont_bin_center,
		wn_bin_width = cont_bin_width,
		line_strength_sum = cont_data['line_strength_sum'],
		line_strength_weighted_mean_lower_energy_state = np.where(nonzero_line_strength_sum, cont_data['strength_weighted_sum_E"'] / cont_data['line_strength_sum'], zeros),
		
		# self broadening
		line_strength_weighted_gamma_self = np.where(nonzero_line_strength_sum, cont_data['strength_weighted_gamma_self'] / cont_data['line_strength_sum'], zeros),
		line_strength_weighted_n_self = np.where(nonzero_line_strength_sum, cont_data['strength_weighted_n_self'] / cont_data['line_strength_sum'], zeros),
		
		# foreign broadening
		broadeners = tuple(
			PseudoContinuumBroadenerPart(
				name = x,
				line_strength_weighted_gamma_amb = np.where(nonzero_line_strength_sum, cont_data[f'strength_weighted_gamma_{x}'] / cont_data['line_strength_sum'], zeros),
				line_strength_weighted_n_amb = np.where(nonzero_line_strength_sum, cont_data[f'strength_weighted_n_{x}'] / cont_data['line_strength_sum'], zeros),
			) for x in broadener_names
		),
		
	)

	_lgr.info('Adding pseudo-continuum line data to database...')
	ans_pc_file.add_source_data(
		pc_dh.name,
		pc_dh,
		pc_dh.description
	)
	
	_lgr.info(f'ADDED PSEUDO CONTINUUM DATA FOR {pc_dfs.iso_name} {pc_dfs.ds_name} ...')

	
def create_hdf5_linedata_file_from(
		dir : Path,
		ans_database_fpath : None | Path
) -> Path:
	_lgr.debug(f'{dir=}')
	_lgr.debug(f'{ans_database_fpath=}')
	
	pc_dfss = get_filesets(dir)
	_lgr.debug(f'{len(pc_dfss)=}')
	
	pf_files = [fpath for fpath in dir.iterdir() if fpath.suffix == '.pf'] # e.g. 12C-1H4__YT10to10.pf
	_lgr.debug(f'{pf_files=}')
	
	ans_database_fpath = ans_database_fpath if ans_database_fpath is not None else (dir / "line_database.h5")
	
	ans_pf_file = AnsPartitionFunctionDataFile(ans_database_fpath)
	ans_pc_file = AnsPseudoContinuumFile(ans_database_fpath)
	ans_ld_file = AnsLineDataFile(ans_database_fpath)

	add_partition_files_to(ans_pf_file, pf_files)

	

	for iso_name, a in pc_dfss.items():
		for ds_name, (stronglines_fpath, pc_dfs_list) in a.items():
			_lgr.info(f'Working on iso {iso_name} dataset {ds_name} {stronglines_fpath=!s}')
			
			add_line_data_file_to(ans_ld_file, stronglines_fpath)
		
			for pc_dfs in pc_dfs_list:
				_lgr.info(f'    t_cont {pc_dfs.t_cont}')
				_lgr.debug(f'{pc_dfs=}')
				add_pseudo_continuum_data_file_set_to(ans_pc_file, pc_dfs)
			
			
			
	
	return ans_database_fpath
