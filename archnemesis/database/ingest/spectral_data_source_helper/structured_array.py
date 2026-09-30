"""
A binary file holding an array based on a numpy array.

FORMAT:
Header that is always a multiple of 4 bytes and ends with a null '\0' byte.
Data in the format described by the header.

"""
from typing import Literal, Self, Type, Protocol
from pathlib import Path

import numpy as np

import archnemesis.cfg.logs as logging
_lgr = logging.getLogger(__name__)
_lgr.setLevel(logging.INFO)

HDR_MAX_SIZE = 1024 * 1024
NULL_BYTE =  b'\0'[0]

class BinaryReader(Protocol):
	def set_source(IOBase):
		...
	def read(n : int) -> bytes:
		...



def dtype_is_structured(dtype) -> bool:
	"""
	Returns True if `dtype` is structured, False otherwise
	"""
	return dtype.names is not None # recommended way to check if a dtype is a structured dtype

def dtype_field_names(dtype) -> tuple[str,...]:
	"""
	Returns a tuple of field names of a structured dtype
	"""
	x = dtype.names
	if x is None:
		raise RuntimeError(f'{dtype=} is not a structured dtype and therefore has no field names')
	return x

def dtype_field_dtypes(dtype) -> tuple[np.dtype,...]:
	"""
	Returns the np.dtype instances of the fields of a structured dtype
	"""
	x = dtype.fields
	if x is None:
		raise RuntimeError(f'{dtype} is not a structured dtype and therefore has no fields')
	return tuple(y[0] for y in x.values())

def dtype_field_offsets(dtype) -> tuple[int,...]:
	"""
	Returns the offsets of the fields of a structured dtype
	"""
	x = dtype.fields
	if x is None:
		raise RuntimeError(f'{dtype} is not a structured dtype and therefore has no fields')
	return tuple(y[1] for y in x.values())

def dtype_field_types(dtype) -> tuple[Type]:
	"""
	Returns the types of the fields of a structured dtype
	"""
	return tuple(x.type for x in dtype_field_dtypes(dtype))

def dtype_field_type_strings(dtype) -> tuple[Type]:
	"""
	Returns the numpy string representation of the types of the fields of a structured dtype
	"""
	return tuple(x.str for x in dtype_field_dtypes(dtype))
	
def dtype_to_string(dtype) -> str:
	s = []
	if dtype_is_structured(dtype):
		s.append('STRUCTURED{')
		for field_name, (field_dtype, field_offset) in dtype.fields.items():
			s.append(f'{field_name}')
			s.append(f'{field_offset}')
			s.append(dtype_to_string(field_dtype))
		s.append('}')
	else:
		if (x := dtype.subdtype )is not None:
			s.append('ARRAY{')
			s.append(f'{x[1]}') # shape
			s.append(dtype_to_string(x[0])) # subdtype
			s.append('}')
		else:
			s.append(f'TYPE{{;{dtype.str};}}')
	return ';'.join(s)


class DtypeStringParser:
	def __init__(self):
		self.TOK_SEP = ';'
		self.TOK_EOF = 'END_OF_FILE'
		
		self.reset()
		
	
	def reset(self, s : str | None = None) -> Self:
		self.pos = 0
		self.end = len(s) if s is not None else None
		self.current_token = None
		self.exhausted = False
		return self
		
	def next_token(self, s) -> str:
		idx = s.find(self.TOK_SEP, self.pos, self.end)
		
		if idx > 0:
			self.current_token = s[self.pos:idx]
			self.pos = idx + len(self.TOK_SEP)
		else:
			if not self.exhausted:
				self.pos = len(s)
				self.current_token = '}'
				self.exhausted = True
			else:
				self.current_token = self.TOK_EOF
		
		return self.current_token
	
	def is_exhausted(self, s) -> bool:
		return self.exhausted
	
	def parse_structured(self, s : str) -> np.dtype:
		"""
		Parse a string for a structured dtype
		"""
		fnames = []
		foffsets = []
		fdtypes = []
		
		while (tok := self.next_token(s)) != '}':
			#print(f'110 :: {tok}')
			fnames.append(tok)
			
			tok = self.next_token(s)
			#print(f'120 :: {tok}')
			foffsets.append(int(tok))
			
			fdtype = self.parse(s)
			fdtypes.append(fdtype)
		
		result = np.dtype({'names':fnames, 'formats' : fdtypes, 'offsets':foffsets})
		
		#print(f'130 :: {self.current_token}')
		assert self.current_token == '}', f'Expected token "}}", but got token "{tok}"'
		return result
	
	def parse_array(self, s : str) -> np.dtype:
		"""
		Parse a string for an array dtype
		"""
		
		tok = self.next_token(s)
		#print(f'210 :: {tok}')
		shape = tuple(int(x.strip()) for x in tok[1:-1].split(','))
		
		fdtype = self.parse(s)
		
		result = np.dtype((fdtype,shape))
		
		tok = self.next_token(s)
		#print(f'220 :: {tok}')
		assert tok == '}', f'Expected token "}}", but got token "{tok}"'
		return result
	
	def parse_type(self, s : str) -> np.dtype:
		"""
		Parse a string for a simple dtype
		"""
		tok = self.next_token(s)
		#print(f'310 :: {tok}')
		result = np.dtype(tok)
		
		tok = self.next_token(s)
		#print(f'320 :: {tok}')
		assert tok == '}', f'Expected token "}}", but got token "{tok}"'
		return result
	
	def parse(self, s : str) -> np.dtype:
		"""
		Parse a string that specifies a general dtype
		"""
		tok = self.next_token(s)
		
		result = None
		
		if tok == 'STRUCTURED{':
			#print(f'100 :: {tok}')
			result = self.parse_structured(s)
		elif tok == 'ARRAY{':
			#print(f'200 :: {tok}')
			result = self.parse_array(s)
		elif tok == 'TYPE{':
			#print(f'300 :: {tok}')
			result = self.parse_type(s)
		elif tok == '}':
			raise RuntimeError('Unexpected end of section')
		elif tok == self.TOK_EOF:
			raise RuntimeError('Unexpected end of input')
		else:
			raise RuntimeError(f'Unknown Token "{tok}"')
		
		return result


_dtype_string_parser = DtypeStringParser()

def dtype_from_string(string : str) -> np.dtype:
	return _dtype_string_parser.reset().parse(string)



class StructuredArrayFile:
	class_writable_modes : tuple[str,...] = ('wb', 'rb+', 'ab')
	class_readable_modes : tuple[str,...] = ('rb', 'rb+')
	class_updateable_modes : tuple[str,...] = ('ab', 'rb+')
	
	def __init__(
			self, 
			fpath, mode : None | Literal['wb', 'rb', 'ab', 'rb+'] = None,
			reader : None | BinaryReader = None,
	):
		self.fpath = fpath
		self.reader = reader
		
		self.mode = None
		self.fhdl = None
		self.header_written = None
		self.n_records_read = 0
		self.n_records_written = 0
		
		if mode is not None:
			self.open(mode)
	
	def __enter__(self) -> Self:
		return self
	
	def __exit__(self, type, value, traceback):
		self.close()
	
	def __del__(self):
		self.close()
	
	def open(self, mode : Literal['wb', 'rb', 'ab', 'rb+']) -> Self:
		
		assert mode in ('wb', 'rb', 'ab', 'rb+'), "`mode` must be one of ('wb', 'rb', 'ab', 'rb+')"
		
		if self.fhdl is not None:
			assert self.mode == mode, "Cannot reopen file with a different mode before closing it"
			return self
		
		self.mode = mode

		self.fhdl = open(self.fpath, self.mode)
		
		if self.mode in self.class_readable_modes:
			self.n_records_read = 0
			if self.reader is not None:
				self.reader.set_source(self.fhdl)
		
		if self.mode in self.class_writable_modes:
			self.n_records_written = 0
		
		self.header_byte_end = 0
		self.header_written = False
		self.arr_dtype = None
		
		if self.mode in self.class_updateable_modes:
			if self.mode == 'rb+':
				self.arr_dtype = self.read_dtype()
				if self.arr_dtype is not None:
					self.header_written = True
			else:
				self.header_written = True # assume header is written
		
		return self
	
	def close(self):
		if self.fhdl is not None:
			self.fhdl.close()
		self.header_written = None
	
	def write_header(self, arr : np.ndarray | np.dtype, encoding : str = 'ascii'):
		if isinstance(arr, np.dtype):
			_dtype = arr
		else:
			_dtype = arr.dtype
		
		dtype_bytes = dtype_to_string(_dtype).encode(encoding)
		
		# align to 32 bit boundary, always end with atleast one null byte
		dtype_bytes += b'\0'*(4 - (len(dtype_bytes) % 4))
		
		
		self.header_byte_end = len(dtype_bytes)+1
		self.fhdl.write(dtype_bytes)
		self.header_written = True
		
	def write(self, arr : np.ndarray):
		assert self.mode in self.class_writable_modes, f"Must have `mode` in {self.class_writable_modes} to write"
		
		if not self.header_written:
			self.write_header(arr)
		
		arr.tofile(self.fhdl)
		self.n_records_written += arr.size
		
		return
	
	def read_bytes(self, n : int = -1) -> bytes:
		if self.reader is None:
			return self.fhdl.read(n if n >=0 else -1)
		else:
			return self.reader.read(n if n >=0 else -1)
	
	def read_header(self, encoding : str = 'ascii') -> str:
		#print(f'reading dtype {self.fhdl.name=}', flush=True)
		# Read 4 bytes at a time until string ends with null character
		_lgr.debug(f'{self.fpath=}')
		_lgr.debug(f'{self.fhdl.tell()=}')
		hdr_part = self.read_bytes(4)
		_lgr.debug(f'four_bytes={hdr_part}')
		if len(hdr_part) == 0:
			self.header_byte_end = 0
			return None
		
		while hdr_part[-1] != NULL_BYTE and len(hdr_part) <= HDR_MAX_SIZE:
			four_bytes = self.read_bytes(4)
			_lgr.debug(f'{four_bytes=}')
			hdr_part += four_bytes
		
		_lgr.debug(f'{len(hdr_part)=}')
		_lgr.debug(f'{hdr_part=}')
		
		if len(hdr_part) > HDR_MAX_SIZE:
			raise RuntimeError(f'Header exceeded maximum size ({HDR_MAX_SIZE} bytes). First 128 bytes: {hdr_part[:128]}')
		
		#print(f'{hdr_part=}')
		
		self.header_byte_end = len(hdr_part)+1
		return hdr_part.decode(encoding)
	
	def read_dtype(self, encoding : str = 'ascii') -> np.dtype:
		hdr = self.read_header(encoding=encoding)
		return dtype_from_string(hdr) if hdr is not None else None
	
	def read(self, count : int = -1) -> np.ndarray:
		if self.arr_dtype is None:
			self.arr_dtype = self.read_dtype()

		#print(f'{self.arr_dtype=}')

		result = np.frombuffer(
			self.read_bytes(count*self.arr_dtype.itemsize), 
			dtype=self.arr_dtype, 
			count=-1
		)

		self.n_records_read += result.size
		
		return result
	
	def tell(self) -> int:
		return self.fhdl.tell()
	
	def seek(self, offset : int, whence : int):
		result = self.fhdl.seek(offset, whence)
		
		if self.header_written:
			if self.tell() < self.header_byte_end:
				self.header_written = False
				self.header_byte_end = 0
				self.seek(0,0)
		
		return result
	
	
	
	
	


def tofile(fpath : Path, arr : np.ndarray):
	_lgr.debug(f'{fpath=}')
	with StructuredArrayFile(fpath, 'wb') as f:
		f.write(arr)


def fromfile(fpath : Path):
	_lgr.debug(f'{fpath=}')
	with StructuredArrayFile(fpath, 'rb') as f:
		return f.read()

