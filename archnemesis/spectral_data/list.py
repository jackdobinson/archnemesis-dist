
from pathlib import Path

import argparse as ap

import re

import numpy as np

from archnemesis.ui.table import Table
from archnemesis.spectral_data.database.filetypes.ans_line_data_file import AnsLineDataFile
from archnemesis.spectral_data.database.filetypes.ans_partition_fn_data_file import AnsPartitionFunctionDataFile
from archnemesis.spectral_data.database.filetypes.ans_pseudo_continuum_file import AnsPseudoContinuumFile

import archnemesis.cfg.logs as logging
_lgr = logging.getLogger(__name__)
_lgr.setLevel(logging.DEBUG)


_subcommand_name = "list"
_subcommand_help = "List molecules and isotopologues for spectral data contained within the passed database files"

def add_subcommand_to(subparser_adder) -> ap.ArgumentParser:

	parser = subparser_adder.add_parser(_subcommand_name, help=_subcommand_help)
	parser.set_defaults(func = _action_list)
	parser.add_argument('-m', '--no_separate_molecules', action='store_true', help='If present, will not separate molecules in output table', default=False)
	parser.add_argument('-u', '--include_units', action='store_true', help='If present, will include units in the output table', default=False)

def _action_list(
	line_database : Path,
	partition_function_database : None | Path,
	pseudo_continuum_database : None | Path,
	mol_regex : re.Pattern = re.compile('.*'),
	no_separate_molecules : bool = False,
	include_units : bool = False,
):
	_lgr.info(f'{line_database=}')
	_lgr.info(f'{partition_function_database=}')
	_lgr.info(f'{pseudo_continuum_database=}')
	

	ans_ld_file = AnsLineDataFile(line_database)
	ans_pf_file = AnsPartitionFunctionDataFile(partition_function_database if partition_function_database is not None else line_database)
	ans_pc_file = AnsPseudoContinuumFile(pseudo_continuum_database if pseudo_continuum_database is not None else line_database)
	
	ld_info_tpl = tuple(ans_ld_file.iter_contents_info())
	pf_info_tpl = tuple(ans_pf_file.iter_contents_info())
	pc_info_tpl = tuple(ans_pc_file.iter_contents_info())
	
	if len(ld_info_tpl) == 0 and len(pc_info_tpl) == 0 and len(pf_info_tpl) == 0:
		_lgr.warn(f"Cannot list spectral data. No data was present in files: '{ans_ld_file.path}' '{ans_pf_file.path}' '{ans_pc_file.path}'")
		return

	ld_info_tpl = tuple(filter(lambda x: mol_regex.fullmatch(x['mol_name']) is not None, ld_info_tpl))
	pf_info_tpl = tuple(filter(lambda x: mol_regex.fullmatch(x['mol_name']) is not None, pf_info_tpl))
	pc_info_tpl = tuple(filter(lambda x: mol_regex.fullmatch(x['mol_name']) is not None, pc_info_tpl))

	if len(ld_info_tpl) == 0 and len(pc_info_tpl) == 0 and len(pf_info_tpl) == 0:
		_lgr.warn(f"Cannot list spectral data. No data was selected for listing. `mol_regex` is '{mol_regex.pattern}'")
		return
	
	mol_iso_pairs = []
	for z in (ld_info_tpl, pf_info_tpl, pc_info_tpl):
		for x in z:
			a = (x['mol_name'], x['iso_id'])
			if x in mol_iso_pairs:
				continue
			else:
				mol_iso_pairs.append(a)
	
	
	cols = ('mol_name', 'iso_id', 'LD', 'PF', 'PC', 'p_ref', 't_ref', 's_min', 't_cont')
	if include_units:
		cols = ('mol_name', 'iso_id', 'LD', 'PF', 'PC', 'p_ref', 'p_unit', 't_ref', 't_unit', 's_min', 's_unit', 't_cont')
	
	column_descriptions = {
		'mol_name' : 'Name of the molecule',
		'iso_id' : 'Isotopologue ID (radtrans ID number)',
		'LD' : 'HDF5 `/line_data/<mol>/<iso>` leaf group index for the dataset',
		'PF' : 'HDF5 `/partition_function/<mol>/<iso>` leaf group index of the dataset',
		'PC' : 'HDF5 `/pseudo_continuum/<mol>/<iso>` leaf group index of the dataset',
		'p_ref' : 'Reference pressure of the line data',
		'p_unit' : 'Unit of pressure (specified in `line_data` and `pseudo_continuum` datasets)',
		't_ref' : 'Reference temperature of the line data',
		't_unit' : 'Unit of temperature (specified in `line_data` and `pseudo_continuum` datasets)',
		's_min' : 'Lines with strength equal to or less than this value (at `t_cont`) are part of the pseudo-continuum',
		's_unit' : 'Unit of line strength (specified in `line_data` and `pseudo_continuum` datasets)',
		't_cont' : 'The strength of the lines that are part of the pseudo-continuum are calculated at this temperature',
	}
	
	
	table = dict((c,[]) for c in cols)
	table_add_row = lambda tbl, r: [tbl[k].append(r[k]) for k in tbl.keys()]
	
	
	pc_attrs = [(x['mol_name'], x['iso_id'], x['p_ref'], x['s_max'], x['t_cont'], x['p_unit'], x['s_unit'], x['t_unit'], x['leaf_grp_id'].rsplit('_',1)[1]) for x in pc_info_tpl]
	
	
	ld_attrs = []
	for x in ld_info_tpl:
		#print(f'{x=}')
		t_str = x.get('t_str', (0,))
		t_str_unit = x.get('t_str_unit', x['t_unit'])
		if not isinstance(t_str, np.ndarray):
			t_str = np.array(t_str)
		elif len(t_str) == 0:
			t_str = np.array((0,))
		for y in t_str:
			ld_attrs.append(
				(x['mol_name'], x['iso_id'], x['p_ref'], x['s_min'], y, x['p_unit'], x['s_unit'], t_str_unit, x['leaf_grp_id'].rsplit('_',1)[1], x['t_ref'])
			)
	

	pf_attrs = [(x['mol_name'], x['iso_id'], x['leaf_grp_id'].rsplit('_',1)[1], *x['t_domain']) for x in pf_info_tpl]

	#print(f'{len(ld_attrs)=}')
	#print(f'{len(pc_attrs)=}')
	#print(f'{len(pf_attrs)=}')

	matched_ld_idxs = []
	matched_pf_idxs = []
	
	
	for pc_attr in pc_attrs:
		v = {
			'mol_name' : pc_attr[0],
			'iso_id' : pc_attr[1],
			'LD' : 'X',
			'PF' : 'X',
			'PC' : pc_attr[8],
			'p_ref' : pc_attr[2],
			'p_unit' : pc_attr[5],
			't_ref' : 'X',
			't_unit' : pc_attr[7],
			's_min' : pc_attr[3],
			's_unit' : pc_attr[6],
			't_cont' : pc_attr[4],
		}
		
		# Find matching line data
		for i, ld_attr in enumerate(ld_attrs):
			#print(f'{pc_attr=}')
			#print(f'{ld_attr=}')
			if pc_attr[:8] == ld_attr[:8]:
				v['LD'] = ld_attr[8]
				v['t_ref'] = ld_attr[9]
				if i not in matched_ld_idxs:
					matched_ld_idxs.append(i)
				break
		
		# Find matching partition functions
		for i, pf_attr in enumerate(pf_attrs):
			if pc_attr[:2] == pf_attr[:2]:
				t_domain_min = min(pf_attr[-2:])
				t_domain_max = max(pf_attr[-2:])
				if (t_domain_min <= v['t_cont']) and (v['t_cont'] <= t_domain_max):
					v['PF'] = pf_attr[2]
					if i not in matched_pf_idxs:
						matched_pf_idxs.append(i)
					break
		
		table_add_row(table, v)
	
	# remove already matched line data
	for idx in sorted(matched_ld_idxs, reverse=True):
		ld_attrs.pop(idx)
	
	# Loop over unmatched line data 
	for ld_attr in ld_attrs:
		v = {
			'mol_name' : ld_attr[0],
			'iso_id' : ld_attr[1],
			'LD' : ld_attr[8],
			'PF' : 'X',
			'PC' : 'X',
			'p_ref' : ld_attr[2],
			'p_unit' : ld_attr[5],
			't_ref' : ld_attr[9],
			't_unit' : ld_attr[7],
			's_min' : ld_attr[3],
			's_unit' : ld_attr[6],
			't_cont' : ld_attr[4],
		}
	
		# Find matching partition functions
		for i, pf_attr in enumerate(pf_attrs):
			if ld_attr[:2] == pf_attr[:2]:
				t_domain_min = min(pf_attr[-2:])
				t_domain_max = max(pf_attr[-2:])
				if (t_domain_min <= v['t_ref']) and (v['t_ref'] <= t_domain_max):
					v['PF'] = pf_attr[2]
					if i not in matched_pf_idxs:
						matched_pf_idxs.append(i)
					break
		
		table_add_row(table, v)
	
	# Remove already matched partition data
	for idx in sorted(matched_pf_idxs, reverse=True):
		_lgr.debug(f'{idx=}')
		pf_attrs.pop(idx)

	# Loop over unmatched partition function data
	for pf_attr in pf_attrs:
		v = {
			'mol_name' : pf_attr[0],
			'iso_id' : pf_attr[1],
			'LD' : 'X',
			'PF' : pf_attr[2],
			'PC' : 'X',
			'p_ref' : 'X',
			'p_unit' : 'X',
			't_ref' : 'X',
			't_unit' : 'X',
			's_min' : 'X',
			's_unit' : 'X',
			't_cont' : 'X',
		}
		table_add_row(table, v)
	
	
	
	table_instance = Table.create(
		table,
		col_descs = tuple(column_descriptions[c] for c in cols)
	)
	
	class MolNameSectionBreaker:
		def __init__(self):
			self.last_mol_name = None
		def __call__(self, x):
			if self.last_mol_name is None:
				self.last_mol_name = x[0]
				return False
			if self.last_mol_name != x[0]:
				self.last_mol_name = x[0]
				return True
			return False
		
	if not no_separate_molecules:
		table_instance.section_end_fn = MolNameSectionBreaker()
	table_instance.data_sort_fn = lambda x: x[0]
	table_instance.display()
	
