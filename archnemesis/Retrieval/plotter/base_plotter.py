
import dataclasses as dc
from typing import TYPE_CHECKING, ClassVar

import numpy as np
import matplotlib as mpl

if TYPE_CHECKING:
	from ..Retrieval import Retrieval

@dc.dataclass(slots=True)
class BasePlotter:
	plot_name : ClassVar[str] = 'generic_plot'
	retrieval : "Retrieval"
	
	def plot(self, *args, **kwargs) -> tuple[str, mpl.figure.Figure, tuple[np.ndarray[mpl.axes.Axes]]]:
		"""
			Plotter interface.
			
			# ARGUMENTS #
				Specified by subclass
			
			# RETURNS #
				(plot_name, figure, tuple_of_axes) : tuple[str, mpl.figure.Figure, tuple[np.ndarray[mpl.axes.Axes]]]
					
		"""
		self._before_plot()
		
		try:
			result = (self.plot_name, *self._plot_impl(*args, **kwargs))
		except:
			result = (self.plot_name, None, tuple())
		
		self._after_plot()
		
		return result
		
	
	def can_plot(self) -> bool:
		"""
			Returns `True` if the plotter can create a plot with the current retrieval
		"""
		raise NotImplementedError()
	
	@classmethod
	def plot_fn(self, *args, **kwargs) -> tuple[mpl.figure.Figure, tuple[np.ndarray[mpl.axes.Axes]]]:
		"""
			Actually does the plotting
			
			# ARGUMENTS #
				Specified by subclass
			
			# RETURNS #
				(figure, tuple_of_axes) : tuple[mpl.figure.Figure, tuple[np.ndarray[mpl.axes.Axes]]]
		"""
		raise NotImplementedError()
	
	def _before_plot(self):
		"""
			Perform any setup calculations before `self._plot_impl` is called
		"""
		pass
	
	def _after_plot(self):
		"""
			Perform any teardown after `self._plot_impl` is called
		"""
		pass
	
	def _plot_impl(self) -> tuple[mpl.figure.Figure, tuple[np.ndarray[mpl.axes.Axes]]]:
		"""
			Arranges data from instance so `self.__class__.plot_fn` can work
			
			# RETURNS #
				(figure, tuple_of_axes) : tuple[mpl.figure.Figure, tuple[np.ndarray[mpl.axes.Axes]]]
		"""
		raise NotImplementedError()
	
	
		