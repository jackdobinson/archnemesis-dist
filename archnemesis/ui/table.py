
from typing import Callable, Iterable, Self, Any

import numpy as np


class Table:
	def __init__(
			self,
			col_sep = '|',
			cell_pref = ' ',
			cell_suff = ' ',
			row_pref = '|',
			row_suff = '|',
			table_start = '-',
			table_end = '-',
			header_end_fill = '#',
			section_end_fill = '-',
			footer_start = '=',
			footer_pref = ' ',
			footer_suff = ' ',
	):
		self.col_sep = col_sep
		self.cell_pref = cell_pref
		self.cell_suff = cell_suff
		self.row_pref = row_pref
		self.row_suff = row_suff
		self.table_start = table_start
		self.table_end = table_end
		self.header_end_fill = header_end_fill
		self.section_end_fill = section_end_fill
		self.footer_start = footer_start
		self.footer_pref = footer_pref
		self.footer_suff = footer_suff
		self.default_cell_formatter = lambda x, w: f'{{: >{w}}}'.format(x)
		self.default_col_formatter = lambda x: f'{x}'
		
		self.data : None | Iterable[Iterable[Any]] | dict[str,Iterable[Any]] | np.recarray | np.ndarray = None
		self.footer = None
		
		self._output_col_names = None
		self._all_col_names = None
		self._all_col_extras = None
		self._all_col_descs = None
		self._all_col_formatters = None
		self._all_cell_formatters = None
		
		self._header_lines = None
		self.cell_widths = None
		
		self.section_end_fn : None | Callable[[tuple[Any,...]], bool] = None
		self.data_sort_fn : None | Callable[[tuple[Any,...]], Any] = None
	
	@classmethod
	def create(
			cls,
			data : None | Iterable[Iterable[Any]] | dict[str,Iterable[Any]] | np.recarray | np.ndarray,
			col_names : None | Iterable[str] = None,
			col_extras : None | Iterable[str] = None,
			col_descs : None | Iterable[str] = None,
			col_major : bool = True,
			**kwargs,
	) -> Self:
		instance = Table(**kwargs)
		instance.set(data, col_names, col_extras, col_descs, col_major)
		return instance
	
	@property
	def output_col_names(self) -> tuple[str,...]:
		return self._all_col_names if self._output_col_names is None else self._output_col_names
	
	@output_col_names.setter
	def output_col_names(self, *col_names):
		if len(col_names) == 0:
			self._output_col_names = None
		elif len(col_names) == 1 and col_names[0] is None:
			self._output_col_names = None
		else:
			for c in col_names:
				if c not in self._all_col_names:
					raise RuntimeError(f'When setting output columns, must be an already existing column. Existing columns: {self._all_col_names}. Trying to set {col_names}')
			self._output_col_names = col_names

	@property
	def output_col_extras(self) -> tuple[str,...]:
		if self._output_col_names is None:
			return self._all_col_extras
		return tuple(self._all_col_extras[self._all_col_names.index(x)] for x in self._output_col_names)
	
	@property
	def output_col_descs(self) -> tuple[str,...]:
		if self._output_col_names is None:
			return self._all_col_descs
		return tuple(self._all_col_descs[self._all_col_names.index(x)] for x in self._output_col_names)

	@property
	def output_col_formatters(self) -> tuple[Callable[[Any],str],...]:
		if self._all_col_formatters is None:
			return tuple(self.default_col_formatter for _ in self.output_col_names)
		else:
			return tuple(f if (f := self._all_col_formatters[self._all_col_names.index(x)]) is not None else self.default_col_formatter for x in self.output_col_names)

	@property
	def output_cell_formatters(self) -> tuple[Callable[[Any],str],...]:
		if self._all_cell_formatters is None:
			return tuple(self.default_cell_formatter for _ in self.output_col_names)
		else:
			return tuple(f if (f := self._all_cell_formatters[self._all_col_names.index(x)]) is not None else self.default_cell_formatter for x in self.output_col_names)

	@property
	def n_cols(self) -> int:
		return len(self.data)
	
	@property
	def n_output_cols(self) -> int:
		return len(self.output_col_names)
	
	@property
	def n_data_rows(self) -> int:
		return len(self.data[self._all_col_names[0]])
	
	@property
	def col_widths(self) -> tuple[int,...]:
		return tuple(len(self.cell_pref) + x + len(self.cell_suff) for x in self.cell_widths)
	
	@property
	def row_width(self) -> int:
		return sum(self.col_widths) + len(self.col_sep)*(self.n_cols - 1) + len(self.row_pref) + len(self.row_suff)
	
	def calc_header_lines(self, include_extras=True) -> tuple[tuple[str,...]]:
		if not include_extras or self.output_col_extras is None:
			self._header_lines = tuple(tuple(x.splitlines()) for x in self.output_col_names)
		else:
			self._header_lines = tuple(tuple(x.splitlines() + (y.splitlines() if y is not None else [])) for x, y in zip(self.output_col_names, self.output_col_extras))
		return self._header_lines
	
	def iter_row_tpls(self) -> Iterable[tuple[Any,...]]:
		col_names = self.output_col_names
		for j in range(self.n_data_rows):
			yield tuple(self.data[c][j] for c in col_names)
	
	def iter_row_tpls_sorted(self) -> Iterable[tuple[Any,...]]:
		if self.data_sort_fn is not None:
			yield from sorted(self.iter_row_tpls(), key=self.data_sort_fn)
		else:
			yield from self.iter_row_tpls()
	
	def iter_row_cell_strs(self) -> Iterable[None | tuple[str,...]]:
		col_formatters = self.output_col_formatters
		row_tpl_iterable = self.iter_row_tpls_sorted()
		if self.section_end_fn is None:
			for value_tpl in row_tpl_iterable:
				yield tuple(formatter(val) for val, formatter in zip(value_tpl, col_formatters))
		else:
			last_value_tpl = next(row_tpl_iterable)
			for value_tpl in row_tpl_iterable:
				if self.section_end_fn(last_value_tpl):
					yield None
				yield (formatter(v) for v, formatter in zip(last_value_tpl, col_formatters))
				last_value_tpl = value_tpl
			yield (formatter(v) for v, formatter in zip(last_value_tpl, col_formatters))
				
	
	def iter_col_cell_str_iter(self) -> Iterable[Iterable[str]]:
		col_names = self.output_col_names
		col_formatters = self.output_col_formatters
		for c, formatter in zip(col_names, col_formatters):
			yield (formatter(x) for x in self.data[c])
	
	def calc_widths(self) -> tuple[int,...]:
		cell_min_widths = tuple(min(len(y) for y in x) for x in (self._header_lines if self._header_lines is not None else self.calc_header_lines()))
		cell_max_widths = tuple(max(len(y) for y in x) for x in self.iter_col_cell_str_iter()) 
		
		self.cell_widths = tuple(max(x) for x in zip(cell_min_widths, cell_max_widths))
		return self.cell_widths
	
	def make_row_str(self, *xs):
		return self.row_pref + self.col_sep.join((self.cell_pref + formatter(x, col_width) +self.cell_suff) for x, formatter, col_width in zip(xs, self.output_cell_formatters, self.cell_widths)) + self.row_suff
	
	def make_row_section_end_str(self):
		return self.row_pref + self.col_sep.join(self.section_end_fill*((x:=(len(self.cell_pref)+col_width+len(self.cell_suff)))//len(self.section_end_fill)) + self.section_end_fill[:x%len(self.section_end_fill)] for col_width in self.cell_widths) + self.row_suff
	
	def make_header_end_str(self):
		return self.row_pref + self.col_sep.join(self.header_end_fill*((x:=(len(self.cell_pref)+col_width+len(self.cell_suff)))//len(self.header_end_fill)) + self.header_end_fill[:x%len(self.header_end_fill)] for col_width in self.cell_widths) + self.row_suff
	
	def iter_header_rows(self):
		header_lines = (self._header_lines if self._header_lines is not None else self.calc_header_lines())
		n_header_rows = 0
		for col_lines in header_lines:
			if len(col_lines) > n_header_rows:
				n_header_rows = len(col_lines)
		
		for j in range(n_header_rows):
			yield self.make_row_str(*(col_lines[j] for col_lines in header_lines))
		yield self.make_header_end_str()
	
	def iter_data_rows(self):
		for cell_str in self.iter_row_cell_strs():
			if cell_str is None:
				yield self.make_row_section_end_str()
			else:
				yield self.make_row_str(*cell_str)
	
	def get_col_desc_dict(self):
		col_descs = dict()
		if self.output_col_descs is not None:
			for c, d in zip(self.output_col_names, self.output_col_descs):
				if d is None:
					continue
				col_descs[c] = d
		return col_descs
	
	def make_footer_lines(self, d, width, expand_tabs = 4):
		result = []
		for k,v in d.items():
			k_str = f'{k}: '
			k_width = len(k_str)
			v_width = width - k_width
			if expand_tabs > 0:
				v = v.replace('\t', ' '*expand_tabs)
				
			
			z = []
			for line in v.splitlines():
				n = len(line)
				while n > v_width:
					# try to split on spaces, then on hypens, then just split mid word
					split_order = (' ', '\t', '\v', '-', '_')
					was_split = False
					for split_str in split_order:
						if (i:=line.rfind(split_str, 0, v_width)) > 0:
							z.append(line[:i]+(v_width-i)*' ')
							line = line[i:].lstrip()
							was_split=True
							break
					if not was_split:
						z.append(line[:v_width-1]+'-')
						line = line[v_width-1:].lstrip()
						
					n = len(line)
				z.append(line+(v_width-len(line))*' ')
			result.extend((k_str+x) if i==0 else (' '*len(k_str) + x) for i, x in enumerate(z))
			result.append(' '*width)
		
		return result
	
	def iter_footer_rows(self):
		col_desc_dict = self.get_col_desc_dict()
		
		footer_total_width = self.row_width - len(self.footer_pref) - len(self.footer_suff) - len(self.row_pref) - len(self.row_suff)
		
		yield self.row_pref + self.footer_start*(footer_total_width + len(self.footer_pref) + len(self.footer_suff)) + self.row_suff
		
		for footer_line in self.make_footer_lines(col_desc_dict, footer_total_width):
			yield self.row_pref + self.footer_pref + footer_line + self.footer_suff + self.row_suff
		
		if self.footer is not None:
			for footer_line in self.make_footer_lines(self.footer, footer_total_width):
				yield self.row_pref + self.footer_pref + footer_line + self.footer_suff + self.row_suff
	
	def iter_rows(self):
		self.calc_widths()
		row_width = self.row_width
		starting_row = self.table_start*(row_width//len(self.table_start)) + self.table_start[:(row_width % len(self.table_start))]
		ending_row = self.table_end*(row_width//len(self.table_end)) + self.table_end[:(row_width % len(self.table_end))]
		
		yield starting_row
		yield from self.iter_header_rows()
		yield from self.iter_data_rows()
		yield from self.iter_footer_rows()
		yield ending_row
	
	def display(self, display_fn : None | Callable[[str],None] = None):
		if display_fn is None:
			print('\n'.join(self.iter_rows()))
		else:
			display_fn('\n'.join(self.iter_rows()))
	
	def set(
			self,
			data : None | Iterable[Iterable[Any]] | dict[str,Iterable[Any]] | np.recarray | np.ndarray,
			col_names : None | Iterable[str] = None,
			col_extras : None | Iterable[str] = None,
			col_descs : None | Iterable[str] = None,
			col_major : bool = True,
	):
		self._all_col_names = tuple(col_names) if col_names is not None else None
		self._all_col_extras = tuple(col_extras) if col_extras is not None else None
		self._all_col_descs = tuple(col_descs) if col_descs is not None else None
		
		if isinstance(data, dict):
			if col_names is None:
				self._all_col_names = tuple(x for x in data.keys())
			n_rows = len(data[self._all_col_names[0]])
			assert all(len(data[x]) == n_rows for x in self._all_col_names), "When setting table data from dictionary, all used columns must have same number of entries"
			
			self.data = dict()
			for k in self._all_col_names:
				self.data[k] = data[k]
		
		elif isinstance(data, np.recarray):
			if col_names is None:
				self._all_col_names = tuple(data.dtype.names)
			self.data = data[*self._all_col_names]
		
		elif isinstance(data, np.ndarray):
			dtype_names = data.dtype.names
			is_struct_arr = dtype_names is not None
			if col_names is None:
				if is_struct_arr:
					self._all_col_names = dtype_names
				else:
					raise RuntimeError('When setting a table from an np.ndarray, if not a structured array must specify column names.')
			if is_struct_arr:
				self.data = data[*self._all_col_names]
			else:
				if col_major:
					self.data = data[:len(self._all_col_names)].view(dtype=[(k,data.dtype) for k in self._all_col_names])
				else:
					self.data = data[...,:len(self._all_col_names)].T.view(dtype=[(k,data.dtype) for k in self._all_col_names])
		else:
			assert col_names is not None, "When setting table data from iterables, must specify column names."
			if col_major:
				self.data = dict()
				for i, k in enumerate(self._all_col_names):
					self.data[k] = tuple(data[i])
			else:
				self.data = dict()
				for k in self._all_col_descs:
					self.data[k] = []
				
				for row in data:
					for i,k in enumerate(self._all_col_descs):
						self.data[k].append(row[i])
				
				for k in self.data.keys():
					self.data[k] = tuple(self.data[k])
			n_rows = len(self.data[self._all_col_names[0]])
			assert all(len(self.data[x]) == n_rows for x in self._all_col_names), "When setting table data from iterables, all columns must have same number of entries"
		
		self.output_col_names = None