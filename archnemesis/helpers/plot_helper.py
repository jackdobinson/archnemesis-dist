
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

import archnemesis.logs as logging
_lgr = logging.getLogger(__name__)
_lgr.setLevel(logging.INFO)

PYTHON_IN_INTERACTIVE_MODE : bool = hasattr(sys, "ps1") # Only defined when in iteractive mode (https://docs.python.org/3/library/sys.html#sys.ps1)

class ShowPlotFnFactory:
	registry = dict()
	
	def __new__(cls, save_plots_dir : None | Path = None, no_show_plots : bool = False):
		if (instance := cls.registry.get((save_plots_dir, no_show_plots),None)) is None:
			instance = super().__new__(cls)
			instance._save_plots_dir = save_plots_dir
			instance._show_plots = not no_show_plots
		return instance
	
	def __call__(self, name : str, figure : None | mpl.figure.Figure, savefig_kwargs=dict(), show_kwargs=dict()):
		if self._save_plots_dir is not None:
			plot_fpath = self._save_plots_dir / name
			if figure is None:
				plt.savefig(plot_fpath, **savefig_kwargs)
			else:
				figure.savefig(plot_fpath, **savefig_kwargs)
			_lgr.info(f'Saved plot to "{plot_fpath}"')
		if self._show_plots:
			if figure is None:
				plt.show(**show_kwargs)
			elif PYTHON_IN_INTERACTIVE_MODE:
				figure.show(**show_kwargs)
			else:
				prev_figure = plt.gcf()
				plt.figure(figure)
				plt.show(**show_kwargs)
				plt.figure(prev_figure)
		return
				
		