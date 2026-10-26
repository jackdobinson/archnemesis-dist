
import re
from typing import Self

from .database.filetypes.ans_base import AnsDatabaseFile
from archnemesis.enum import GasEnum
from archnemesis.Data.gas_data import gas_info

class MolSelector:

	arg_meta : str = "<mol_regex>#[<iso_regex>]"
	arg_description = "Molecule isotopologue selector, unspecified regexes will assume all should be matched."
	
	def __init__(self, mol_regex : re.Pattern, iso_regex : re.Pattern):
		self.mol_regex = mol_regex
		self.iso_regex = iso_regex
	
	@classmethod
	def create_match_all(cls) -> Self:
		cls(re.compile(r'.*'), re.compile(r'.*'))
	
	@classmethod
	def from_str(cls, s : str) -> Self:
		if len(s) ==0 or s == '#':
			return cls(re.compile(r'.*'), re.compile(r'.*'))
		
		escape_char = False
		hash_idxs = []
		for i, c in enumerate(s):
			if c == '#' and not escape_char:
				hash_idxs.append(i)
			elif c == '\\':
				escape_char = not escape_char
			else:
				escape_char = False
			
		if len(hash_idxs) > 1:
			raise RuntimeError(f'Malformed molecule specifier `{s}`. More than one unescaped hash')

		elif len(hash_idxs) == 0:
			mol_regex = re.compile(s.replace('\#', '#'))
			iso_regex = re.compile(r'.*')
			
		else:
			if s[0] == '#':
				mol_regex = re.compile(r'.*')
			else:
				mol_regex = re.compile(s[:hash_idxs[0]].replace('\#','#'))
			if len(s) == hash_idxs[0]+1:
				iso_regex = re.compile(r'.*')
			else:
				iso_regex = re.compile(s[hash_idxs[0]+1:].replace('\#','#'))
		
		return cls(mol_regex, iso_regex)
	
	def __repr__(self) -> str:
		return f'{self.mol_regex.pattern}#{self.iso_regex.pattern}'
	
	def str_str_pair_filter_fn(self, x) -> bool:
		return (self.mol_regex.fullmatch(x['mol_name']) is not None) and (self.iso_regex.fullmatch(x['iso_id']) is not None)
	
	def enum_mol_filter_fn(self, x) -> bool:
		return self.mol_regex.fullmatch(x.name) is not None
	
	def str_iso_filter_fn(self, x) -> bool:
		return self.iso_regex.fullmatch(x) is not None
	
	def get_matching_mol_iso_pairs_from_ans_database_files(
			self,
			*ans_database_files : tuple[AnsDatabaseFile,...],
			return_info_tuples = False,
	) -> list[tuple[str,int]]:
		mol_iso_pairs = []
		
		if return_info_tuples:
			filtered_info_tuples_iterable = tuple(tuple(filter(self.str_str_pair_filter_fn, ans_database_file.iter_contents_info())) for ans_database_file in ans_database_files)
		else:
			filtered_info_tuples_iterable = (filter(self.str_str_pair_filter_fn, ans_database_file.iter_contents_info()) for ans_database_file in ans_database_files)
		
		for filtered_info_tuple in filtered_info_tuples_iterable:
			for info in filtered_info_tuple:
				pair = (info['mol_name'], info['iso_id'])
				if pair in mol_iso_pairs:
					continue
				else:
					mol_iso_pairs.append(pair)
		
		if return_info_tuples:
			return mol_iso_pairs, filtered_info_tuples_iterable
		else:
			return mol_iso_pairs
	
	def get_matching_mol_iso_pairs_from_enums(
			self,
	) -> list[tuple[GasEnum,int]]:
		mol_iso_pairs = []
		
		for mol_enum in filter(self.enum_mol_filter_fn, (x for x in GasEnum)):
			if self.str_iso_filter_fn('0'):
				mol_iso_pairs.append((mol_enum,0))
			else:
				mol_iso_pairs.extend([(mol_enum, int(iso)) for iso in filter(self.str_iso_filter_fn, gas_info[str(mol_enum.value)]['isotope'].keys())])
		
		return mol_iso_pairs
