
from pathlib import Path

import argparse as ap

import numpy as np

from archnemesis.spectral_data.database.filetypes.ans_line_data_file import AnsLineDataFile
from archnemesis.spectral_data.database.filetypes.ans_partition_fn_data_file import AnsPartitionFunctionDataFile
from archnemesis.spectral_data.database.filetypes.ans_pseudo_continuum_file import AnsPseudoContinuumFile

import archnemesis.cfg.logs as logging
_lgr = logging.getLogger(__name__)
_lgr.setLevel(logging.INFO)


_subcommand_name = "list"
_subcommand_help = "List molecules and isotopologues for spectral data contained within the passed database files"

def add_subcommand_to(subparser_adder) -> ap.ArgumentParser:

	parser = subparser_adder.add_parser(_subcommand_name, help=_subcommand_help)
	parser.set_defaults(func = _action_list)
	parser.add_argument('-m', '--no_separate_molecules', action='store_true', help='If present, will not separate molecules in output table', default=False)

def _action_list(
	line_database : Path,
	partition_function_database : None | Path,
	pseudo_continuum_database : None | Path,
	no_separate_molecules : bool = False
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
	
	
	mol_iso_pairs = []
	for z in (ld_info_tpl, pf_info_tpl, pc_info_tpl):
		for x in z:
			a = (x['mol_name'], x['iso_id'])
			if x in mol_iso_pairs:
				continue
			else:
				mol_iso_pairs.append(a)
	
	
	cols = ('mol_name', 'iso_id', 'LD', 'PF', 'PC', 'p_ref', 't_ref', 's_min', 't_cont')
	
	
	table = dict((c,[]) for c in cols)
	table_add_row = lambda tbl, r: [tbl[k].append(r[k]) for k in tbl.keys()]
	
	
	pc_attrs = [(x['mol_name'], x['iso_id'], x['p_ref'], x['s_max'], x['t_cont'], x['p_unit'], x['s_unit'], x['t_unit'], x['leaf_grp_id'].rsplit('_',1)[1]) for x in pc_info_tpl]
	
	
	ld_attrs = []
	for x in ld_info_tpl:
		t_str = x.get('t_str', 0)
		t_str_unit = x.get('t_str_unit', x['t_unit'])
		if not isinstance(t_str, np.ndarray):
			t_str = np.array([t_str])
		for y in t_str:
			ld_attrs.append(
				(x['mol_name'], x['iso_id'], x['p_ref'], x['s_min'], y, x['p_unit'], x['s_unit'], t_str_unit, x['leaf_grp_id'].rsplit('_',1)[1], x['t_ref'])
			)
	

	pf_attrs = [(x['mol_name'], x['iso_id'], x['leaf_grp_id'].rsplit('_',1)[1], *x['t_domain']) for x in pf_info_tpl]



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
			't_ref' : 'X',
			's_min' : pc_attr[3],
			't_cont' : pc_attr[4],
		}
		
		# Find matching line data
		for i, ld_attr in enumerate(ld_attrs):
			print(f'{pc_attr=}')
			print(f'{ld_attr=}')
			if pc_attr[:8] == ld_attr[:8]:
				v['LD'] = ld_attr[8]
				v['t_ref'] = ld_attr[9]
				matched_ld_idxs.append(i)
				break
		
		# Find matching partition functions
		for i, pf_attr in enumerate(pf_attrs):
			if pc_attr[:2] == pf_attr[:2]:
				t_domain_min = min(pf_attr[-2:])
				t_domain_max = max(pf_attr[-2:])
				if (t_domain_min <= v['t_cont']) and (v['t_cont'] <= t_domain_max):
					v['PF'] = pf_attr[2]
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
			't_ref' : ld_attr[9],
			's_min' : ld_attr[3],
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
			't_ref' : 'X',
			's_min' : 'X',
			't_cont' : 'X',
		}
		table_add_row(table, v)
	
	r_pref = '|'
	d_pref = ' '
	d_suff = ' '
	sep = '|'
	r_suff = '|'
	c_min_widths = tuple(len(x) for x in cols)
	c_max_data_widths = tuple(max(len(str(x))for x in table[c]) for c in cols)
	c_data_widths = tuple(max(x,y) for x,y in zip(c_min_widths, c_max_data_widths))
	c_total_widths = tuple(w+len(d_pref)+len(d_suff) for w in c_data_widths) # includes a space on either end
	r_width = len(r_pref) + sum(c_total_widths) + (len(cols)-1)*len(sep) + len(r_suff)
	
	c_idx_fmt = r_pref + sep.join(tuple(f'{d_pref}{{{i}: >{w}}}{d_suff}' for i,w in enumerate(c_data_widths))) + r_suff
	print(f'{c_idx_fmt=}')
	
	frame_top_bottom = '-'*r_width
	header_sep = r_pref + sep.join('#'*w for w in c_total_widths) + r_suff
	empty_entry = r_pref + sep.join('-'*w for w in c_total_widths) + r_suff
	
	head = c_idx_fmt.format(*table.keys())
	
	
	print(frame_top_bottom)
	print(head)
	print(header_sep)
	last_mol = None
	for row in sorted(zip(*table.values()), key=lambda x: x[0]):
		if not no_separate_molecules:
			if last_mol is None:
				last_mol = row[0]
			elif last_mol != row[0]:
				print(empty_entry)
				last_mol = row[0]
		print(c_idx_fmt.format(*row))
	
	print(frame_top_bottom)