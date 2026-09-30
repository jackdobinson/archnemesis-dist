from pathlib import Path

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
_lgr.setLevel(logging.DEBUG)

def get_filesets(dir : Path) -> dict[dict[str,list[PCDataFileSet]]]:

	exts = ('.contbins', '.continuum', '.stronglines')
	filesets : dict[dict[str,list[PCDataFileSet]]] = {}
	
	
	for fpath in dir.iterdir():
		if fpath.suffix == exts[0]:
			pc_data_file_set = PCDataFileSet.from_path(fpath)
			x = filesets.setdefault(pc_data_file_set.iso_name, dict())
			y = x.setdefault(pc_data_file_set.ds_name, list())
			y.append(pc_data_file_set)
	
	for ext in exts[1:]:
		for fpath in dir.iterdir():
			if fpath.suffix == ext:
				if not fpath.with_suffix(exts[0]).exists:
					pc_data_file_set = PCDataFileSet.from_path(fpath)
					x = filesets.setdefault(pc_data_file_set.iso_name, dict())
					y = x.setdefault(pc_data_file_set.ds_name, list())
					y.append(pc_data_file_set)
	
	return filesets


def read_cont_data(pc_dfs):
	cont_bin_edge = np.fromfile(pc_dfs.contbins)
	#_lgr.debug(f'{cont_bin_edge=}')
	cont_bin_center = 0.5*(cont_bin_edge[:-1] +cont_bin_edge[1:])
	#_lgr.debug(f'{cont_bin_center=}')
	cont_bin_width = np.diff(cont_bin_edge)
	#_lgr.debug(f'{cont_bin_width=}')

	stronglines_data = structured_array_from_file(pc_dfs.stronglines)
	cont_data = structured_array_from_file(pc_dfs.continuum)
	
	return cont_bin_center, cont_bin_width, cont_data, stronglines_data


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
				f"This data was created from files at {dir}. With iso_slug `{iso_slug}` dataset name {ds_name}",
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

	for iso_name, a in pc_dfss.items():
		for ds_name, pc_dfs_list in a.items():
			for pc_dfs in pc_dfs_list:
				
				_lgr.debug(f'{pc_dfs=}')
				cont_bin_center, cont_bin_width, cont_data, stronglines_data = read_cont_data(pc_dfs)
				_lgr.debug(f'{cont_bin_center[:10]=} {cont_bin_width[:10]=} {cont_data[:10]=}')
				
				rt_mol_id, rt_iso_id = get_rt_mol_iso_ids(pc_dfs.mol_spec, pc_dfs.iso_name)
				_lgr.debug(f'LOOP: {rt_mol_id=} {rt_iso_id=}')
				
				broadener_names = tuple(x[len("strength_weighted_gamma_"):] for x in cont_data.dtype.names if (x.startswith("strength_weighted_gamma_") and not x.endswith('self')))
				_lgr.debug(f'{broadener_names=}')

				pc_dh = PseudoContinuumDataHolder(
					pc_dfs.ds_name,
					f"This data was created from files at {dir}. With iso_slug `{pc_dfs.contbins.name.split('__',1)[0]}` dataset name `{pc_dfs.ds_name}`",
					
					t_cont = pc_dfs.t_cont,
					s_max = pc_dfs.s_max, 
					
					mol_id = rt_mol_id * np.ones_like(cont_bin_center, dtype=int),
					local_iso_id = rt_iso_id * np.ones_like(cont_bin_center, dtype=int),
					
					wn_bin_center = cont_bin_center,
					wn_bin_width = cont_bin_width,
					line_strength_sum = cont_data['line_strength_sum'],
					line_strength_weighted_mean_lower_energy_state = cont_data['strength_weighted_sum_E"'] / cont_data['line_strength_sum'],
					
					# self broadening
					line_strength_weighted_gamma_self = cont_data['strength_weighted_gamma_self'] / cont_data['line_strength_sum'],
					line_strength_weighted_n_self = cont_data['strength_weighted_n_self'] / cont_data['line_strength_sum'],
					
					# foreign broadening
					broadeners = tuple(
						PseudoContinuumBroadenerPart(
							name = x,
							line_strength_weighted_gamma_amb = cont_data[f'strength_weighted_gamma_{x}'] / cont_data['line_strength_sum'],
							line_strength_weighted_n_amb = cont_data[f'strength_weighted_n_{x}'] / cont_data['line_strength_sum'],
						) for x in broadener_names
					),
					
				)


				ans_pc_file.add_source_data(
					pc_dh.name,
					pc_dh,
					pc_dh.description
				)
				
				_lgr.info(f'ADDED PSEUDO CONTINUUM DATA FOR {iso_name} {ds_name} ...')
				
				
				ld_dh = LineDataHolder(
					pc_dfs.ds_name,
					f"This data was created from files at {dir}. With iso_slug `{pc_dfs.contbins.name.split('__',1)[0]}` dataset name `{pc_dfs.ds_name}`",
					
					s_min = pc_dfs.s_max,
					t_ref = pc_dfs.t_cont,
					
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
				
				ans_ld_file.add_source_data(
					ld_dh.name,
					ld_dh,
					ld_dh.description
				)
				
				_lgr.info(f'ADDED LINE DATA FOR {iso_name} {ds_name} ...')
	
	return ans_database_fpath
