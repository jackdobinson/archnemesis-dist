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
	#print(f'{cont_bin_edge=}')
	cont_bin_center = 0.5*(cont_bin_edge[:-1] +cont_bin_edge[1:])
	#print(f'{cont_bin_center=}')
	cont_bin_width = np.diff(cont_bin_edge)
	#print(f'{cont_bin_width=}')

	cont_data = structured_array_from_file(pc_dfs.continuum)
	stronglines_data = structured_array_from_file(pc_dfs.stronglines)
	
	return cont_bin_center, cont_bin_width, cont_data, stronglines_data


def create_hdf5_linedata_file_from(
		dir : Path,
		ans_database_fpath : None | Path
) -> Path:
	pc_dfss = get_filesets(dir)
	
	pf_files = [fpath for fpath in dir.iterdir() if fpath.suffix == '.pf'] # e.g. 12C-1H4__YT10to10.pf
	
	ans_database_fpath = ans_database_fpath if ans_database_fpath is not None else (dir / "line_database.h5")
	
	ans_pf_file = AnsPartitionFunctionDataFile(ans_database_fpath)
	ans_pc_file = AnsPseudoContinuumFile(ans_database_fpath)
	ans_ld_file = AnsLineDataFile(ans_database_fpath)

	pfdh_dict = {}

	for pf_file in pf_files:
		iso_slug, ds_name = pf_file.stem.split('__', 1)[0]
		iso_name = iso_slug_to_iso_name(iso_slug)
		
		pfdh_tabulated = pfdh_dict.setdefault(
			ds_name,
			PartitionFunctionDataHolder(
				ds_name,
				f"This data was created from files at {dir}. With iso_slug `{iso_slug}`",
			)
		)
		
		rt_mol_id, rt_iso_id = get_rt_mol_iso_ids(
			mol_spec_from_iso_name(iso_name), 
			iso_name
		)
		
		pf_array = np.loadtxt(pf_file, dtype=float, sep=' ').reshape(-1,2)
		temp = pf_array[:,0]
		q = pf_array[:,1]
		
		tab_pf_data = TabulatedPFData(
			temp,
			q
		)
		
		pfdh_tabulated.add(
			rt_mol_id,
			rt_iso_id,
			tab_pf_data
		)
	
	for pfdh in pfdh_dict.values():
		ans_pf_file.add_source_data(pfdh.name, pfdh, pfdh.description)

	for iso_name, a in pc_dfss.items():
		for dsname, b in a.items():
			for pc_dfs in b.values():
				
				print(f'{pc_dfs=}')
				cont_bin_center, cont_bin_width, cont_data, stronglines_data = read_cont_data(pc_dfs)
				
				rt_mol_id, rt_iso_id = get_rt_mol_iso_ids(pc_dfs.mol_spec, pc_dfs.iso_name)
				print(f'LOOP: {rt_mol_id=} {rt_iso_id=}')
				
				broadener_names = tuple(x[len("strength_weighted_gamma_"):] for x in cont_data.dtype.names if (x.startswith("strength_weighted_gamma_") and not x.endswith('self')))

				pc_dh = PseudoContinuumDataHolder(
					pc_dfs.dsname,
					f"This data was created from files at {dir}. With iso_slug `{pc_dfs.contbins.name.split('__',1)[0]}`",
					
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
				
				print('ADDED PSEUDO CONTINUUM DATA...')
				
				
				ld_dh = LineDataHolder(
					"EXOMOL_test",
					"This data is a test that has been extracted from exomol",
					
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
				
				print('ADDED LINE DATA...')
	
	return ans_database_fpath
