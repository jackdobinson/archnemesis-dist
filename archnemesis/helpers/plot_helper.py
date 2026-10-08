
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

PYTHON_IN_INTERACTIVE_MODE : bool = hasattr(sys, "ps1") # Only defined when in iteractive mode (https://docs.python.org/3/library/sys.html#sys.ps1)

class ShowPlotFnFactory:
	registry = dict()
	
	def __new__(cls, save_plots_dir : None | Path = None, no_show_plots : bool = False):
		if (instance := cls.registry.get((save_plots_dir, no_show_plots),None)) is None:
			instance = super().__new__(cls)
			instance.save_plots_dir = save_plots_dir
			instance.show_plots = not no_show_plots
		return instance
	
	def __call__(self, name : str, figure : None | mpl.figure.Figure, savefig_kwargs=dict(), show_kwargs=dict()):
		if self.save_plots_dir is not None:
			plot_fpath = self.save_plots_dir / name
			if figure is None:
				plt.savefig(plot_fpath, **savefig_kwargs)
			else:
				figure.savefig(plot_fpath, **savefig_kwargs)
		if self.show_plots:
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
				
		