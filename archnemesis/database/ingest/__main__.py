

import sys
from pathlib import Path
import argparse as ap





def action_spectral_data_source_helper_ingest(
		dir : Path,
		ans_database_fpath : None | Path = None
):
	from .spectral_data_source_helper import create_hdf5_linedata_file_from
	
	output_fpath = create_hdf5_linedata_file_from(
		dir,
		ans_database_fpath=ans_database_fpath,
	)
	print(f'Ingested spectral data to "{output_fpath}"')
	

def create_parser():
	parser = ap.ArgumentParser(
		prog = 'python -m archnemesis.database.ingest',
		description = 'Ingest spectral data to a spectral database file. Ingestion format is specified by subcommand.',
	)

	subparsers = parser.add_subparsers(required=True)
	
	spectral_data_source_helper_sp = subparsers.add_parser(
		'binary_spec_data',
		help='Spectral data is specified by structured arrays in binary files (as output by the `spectral_data_source_helper` module).',
	)
	spectral_data_source_helper_sp.set_defaults(func = action_spectral_data_source_helper_ingest)
	spectral_data_source_helper_sp.add_argument('dir', metavar='<directory>', type=Path, help='Directory to look for structured array files within')
	spectral_data_source_helper_sp.add_argument('-o', '--output', metavar='<path>', type=Path, help='Path to the ArchNEMESIS spectral database file to add data to, will be created if does not exist. (default = "<directory> / line_database.h5")', default=None)
	
	return parser

if __name__ == '__main__':
	
	parser = create_parser()
	
	arg_dict = vars(parser.parse_args(sys.argv[1:]))
	func = arg_dict.pop('func')

	print('ARGUMENTS\n' + '\n'.join(f'\t{k} : {v}' for k,v in arg_dict.items())+'\nEND ARGUMENTS')
	
	func(**arg_dict)