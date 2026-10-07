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
_lgr.setLevel(logging.INFO)


_subcommand_name = "plot"
_subcommand_help = "Plot spectral data contained within these files"

def add_subcommand_to(subparser_adder) -> ap.ArgumentParser:

	parser = subparser_adder.add_parser(_subcommand_name, help=_subcommand_help)
	parser.set_defaults(func = _action_plot)
	#parser.add_argument('-m', '--no_separate_molecules', action='store_true', help='If present, will not separate molecules in output table', default=False)
	#parser.add_argument('-u', '--include_units', action='store_true', help='If present, will include units in the output table', default=False)

def _action_plot(
	line_database : Path,
	partition_function_database : None | Path,
	pseudo_continuum_database : None | Path,
	mol_regex : re.Pattern = re.compile('.*'),

):
	_lgr.info(f'{line_database=}')
	_lgr.info(f'{partition_function_database=}')
	_lgr.info(f'{pseudo_continuum_database=}')
	

	ans_ld_file = AnsLineDataFile(line_database)
	ans_pf_file = AnsPartitionFunctionDataFile(partition_function_database if partition_function_database is not None else line_database)
	ans_pc_file = AnsPseudoContinuumFile(pseudo_continuum_database if pseudo_continuum_database is not None else line_database)
	