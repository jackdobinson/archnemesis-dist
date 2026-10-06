
from pathlib import Path

import argparse as ap

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
	
	ld_attrs_getters = ('p_ref', 'p_unit', 's_min', 's_unit', lambda x: x.get('t_str',x['t_ref'] if (x['s_min'] is not None) else None), lambda x:x.get('t_str_unit', x['t_unit']))
	pc_attrs_getters = (lambda x:x.get('p_cont',x['p_ref']), 'p_unit', 's_max', 's_unit', 't_cont', 't_unit')
	
	ld_pc_comps = (
		lambda x,y:x==y,
		lambda x,y:x==y,
		lambda x,y:x==y,
		lambda x,y:x==y,
		lambda x,y:False if x is None else (x==y if isinstance(x,float) else (x[0]==y if (len(x)==1) else y in x)),
		lambda x,y:x==y,
	)
	
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
	
	attrs_match_iso = ('mol_name', 'iso_id')
	
	cols = ('mol_name', 'iso_id', 'line_set_index', 'LD', 'PF', 'p_ref', 't_ref', 's_min', 't_cont')
	c_min_widths = (len(x) for x in cols)
	
	mol_name_width = len('mol_name')
	iso_id_width = len('iso_id')
	for (mol_name, iso_id) in mol_iso_pairs:
		if (a := len(mol_name)) > mol_name_width:
			mol_name_width = a
		
		if (a := len(iso_id)) > iso_id_width:
			iso_id_width = a
	
	c_last_widths = [0,0,0,0]
	for z in (ld_info_tpl, pf_info_tpl, pc_info_tpl):
		for x in z:
			for i, k in enumerate(('p_ref', 't_ref', 's_min', 't_cont')):
				if (a:=len(str(x.get(k, '')))) > c_last_widths[i]:
					c_last_widths[i] = a
	
	c_found_widths = (mol_name_width, iso_id_width, 0, 0, 0, *c_last_widths)
	c_widths = tuple(x if x>y else y for x,y in zip(c_min_widths, c_found_widths))
	c_fmt = tuple(f'{{: >{w}}}' for w in c_widths)
	
	sep = ' | '
	header_sep = sep.join('#'*w for w in c_widths)
	empty_entry = sep.join('-'*w for w in c_widths)
	head = sep.join(x.format(c) for x,c in zip(c_fmt, cols))
	
	c_key_fmt = sep.join(tuple(f'{{{c}: >{w}}}' for w, c in zip(c_widths,cols)))
	
	print(header_sep)
	print(head)
	print(header_sep)
	
	
	last_mol_name = None
	for mol_name, iso_id in mol_iso_pairs:
		if last_mol_name is None:
			last_mol_name = mol_name
	
		if last_mol_name != mol_name:
			if not no_separate_molecules:
				print(empty_entry)
			last_mol_name = mol_name
	
		for ld_info in ld_info_tpl:
			if (mol_name, iso_id) != (ld_info['mol_name'], ld_info['iso_id']):
				continue
				
			ld_attrs = tuple(ld_info[x] if type(x) is str else x(ld_info) for x in ld_attrs_getters)
			
		
			match_iso = tuple(ld_info[x] for x in attrs_match_iso)
			has_pf = False
			for pf_info in pf_info_tpl:
				if tuple(pf_info[x] for x in attrs_match_iso) == match_iso:
					has_pf = True
					break
			
			has_t_conts = []
			for pc_info in pc_info_tpl:
				pc_attrs = tuple(pc_info[x] if type(x) is str else x(pc_info) for x in pc_attrs_getters)
				if (tuple(pc_info[x] for x in attrs_match_iso) == match_iso) and all(f(x,y) for f,x,y in zip(ld_pc_comps, ld_attrs, pc_attrs)):
					has_t_conts.append(pc_info['t_cont'])
			
			v = {
				'mol_name' : mol_name,
				'iso_id' : iso_id,
				'line_set_index' : ld_info['leaf_grp_id'].rsplit('_',1)[1],
				'LD' : 'Y',
				'PF' : 'Y' if has_pf else 'N',
				'p_ref' : ld_info['p_ref'],
				't_ref' : ld_info['t_ref'],
				's_min' : ld_info.get('s_min', 0),
				't_cont' : str(has_t_conts) if len(has_t_conts) > 0 else 'No PC data'
			}
			#print(v)
			#print(c_key_fmt)
			print(c_key_fmt.format(**v))
			
	print(header_sep)