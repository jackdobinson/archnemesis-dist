


import re

from archnemesis.Data.gas_data import gas_info, atom_mass

import archnemesis.cfg.logs as logging
_lgr = logging.getLogger(__name__)
_lgr.setLevel(logging.INFO)

atom_names = tuple(atom_mass.keys())

iso_slug_regex = re.compile(r'(\d+)([A-Z][a-zA-Z]*)(\d*)')
atom_num_regex = re.compile(r'\((\d+)([A-Z][a-zA-Z]*)\)(\d*)')

def iso_slug_to_iso_name(iso_slug) -> str:
	iso_name = ''
	for match in iso_slug_regex.finditer(iso_slug):
		iso_mass = int(match[1])
		iso_atom = match[2]
		iso_multiplicity = match[3]
		iso_name += f'({iso_mass}{iso_atom}){iso_multiplicity}'
	return iso_name

def iso_name_to_iso_spec(iso_name) -> tuple:
	iso_spec = []
	for match in atom_num_regex.finditer(iso_name):
		iso_spec.append(
			((int(match[1]), match[2]), int(match[3]) if len(match[3]) > 0 else 1)
		)
	return tuple(iso_spec)

def mol_spec_from_iso_name(iso_name) -> tuple:
	mol_spec : dict[str,int] = dict()
	for match in atom_num_regex.finditer(iso_name):
		atom_name = match[2]
		atom_multiplicity = int(match[3]) if len(match[3]) > 0 else 1
		mol_spec[atom_name] = mol_spec.get(atom_name, 0) + atom_multiplicity
	
	for k in tuple(mol_spec.keys()):
		if mol_spec[k] == 0:
			del mol_spec
	
	return tuple(sorted((k,mol_spec[k]) for k in sorted(mol_spec.keys())))


def mol_name_to_mol_spec(mol_name, atom_names = atom_names):
	mol_spec = dict()
	
	while len(mol_name) > 0:
		#atom_name_found = False
		for atom_name in atom_names:
			
			if mol_name.startswith(atom_name):
				#print(f'{atom_name=}')
				#atom_name_found = True
				atom_multiplicity = 1
				mol_name = mol_name[len(atom_name):]
				#print(f'{mol_name=}')
				i=0
				while i<len(mol_name) and mol_name[i].isdigit():
					i+=1
				if i > 0:
					atom_multiplicity = int(mol_name[:i])
					mol_name = mol_name[i:]
				mol_spec[atom_name] = mol_spec.get(atom_name, 0) + atom_multiplicity
	
	return tuple(sorted((k,v) for k,v in mol_spec.items()))
	
	
def get_rt_mol_iso_ids(mol_spec, iso_name, gas_info=gas_info):
	rt_mol_id = None
	rt_iso_id = None
	
	_lgr.info(f'{mol_spec=}')
	_lgr.info(f'{iso_name=}')
	_lgr.info(f'{gas_info=}')

	uncontained_iso_atom_regex = re.compile(r'[A-Z][a-zA-Z]*(?!\))')
	uncontained_iso_atom_subs = {'H' : '(1H)', 'D' : '(2H)'}

	for mol_id, mol_data in gas_info.items():
		mol_name = mol_data['name']
		_lgr.info(f'{mol_id=} {mol_name=}')
		
		rt_mol_spec = mol_name_to_mol_spec(mol_name, atom_names=atom_names)
		_lgr.info(f'{rt_mol_spec=}')
		if rt_mol_spec != mol_spec:
			continue
		
		print(f'Found molecule name {mol_name} {mol_id}')
		rt_mol_id = int(mol_id)
		
		for iso_id, iso_data in mol_data['isotope'].items():
			iso_name = iso_data['name']
			_lgr.info(f'{iso_id=} {iso_name=}')
			canonical_iso_name = ''
			i = 0
			j = 0
			for match in uncontained_iso_atom_regex.finditer(iso_name):
				j = match.start()
				canonical_iso_name += iso_name[i:j]
				canonical_iso_name += uncontained_iso_atom_subs[match[0]]
				i = match.end()
			canonical_iso_name += iso_name[i:]
			_lgr.info(f'{canonical_iso_name=}')
			#print(f'{iso_name=}')
			#print(f'{canonical_iso_name=}')
			if canonical_iso_name != iso_name:
				continue
			rt_iso_id = int(iso_id)
			break
		
		if rt_iso_id is None:
			raise RuntimeError(f'Could not fine RADTRAN local iso id for {iso_name}')
		
		break

	if rt_mol_id is None:
		raise RuntimeError(f'Could not fine RADTRAN molecule id for {mol_spec}')
	
	print(f'{rt_mol_id=} {rt_iso_id=}')
	return rt_mol_id, rt_iso_id