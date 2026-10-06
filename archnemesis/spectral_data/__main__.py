
import sys
from pathlib import Path
import argparse as ap

from archnemesis.Data.path_data import archnemesis_path, archnemesis_resolve_path

from . import list

def create_parser() -> ap.ArgumentParser:
	
	
	parser = ap.ArgumentParser(
		prog='python -m archnemesis.spectral_data',
		description = 'Perform operations on spectral data',
	)
	
	parser.add_argument('line_database', metavar='<path>', type=archnemesis_resolve_path, help='HDF5 file that contains line data (required)')
	parser.add_argument('partition_function_database', metavar='<path>', nargs='?', type=archnemesis_resolve_path, help = f'HDF5 file that contains partition function data (if not present will use {archnemesis_path()+"/archnemesis/Data/partition_functions/tips2025.h5"})', default=Path(archnemesis_path()+'/archnemesis/Data/partition_functions/tips2025.h5'))
	parser.add_argument('pseudo_continuum_database', metavar='<path>', nargs='?', type=archnemesis_resolve_path, help = 'HDF5 file that contains pseudo-continuum data (if not present will use `line_database`)', default=None)
	
	
	
	subparsers = parser.add_subparsers(title='subcommands', description='All arguments after the subcommand will be intepreted by that subcommand.', required=True)
	list.add_subcommand_to(subparsers)
	
	return parser


if __name__=='__main__':
	print(f'{sys.argv[1:]=}')

	parser = create_parser()
	arg_dict = vars(parser.parse_args(sys.argv[1:]))
	
	func = arg_dict.pop('func')
	func(**arg_dict)