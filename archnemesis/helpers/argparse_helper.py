
import argparse as ap
from typing import Any

import numpy as np

def action_enum_choice(enum_class):
	#print(f'{enum_class=}')
	class EnumChoiceAction(ap.Action):
		def __init__(self, option_strings, dest, **kwargs):
			# kwargs are the arguments passed to `ap.ArgumentParser.add_action(...)` except `action` itself.
			# Generally the defaults are `nargs=None, const=None, default=None, type=None, choices=None, required=False, help=None, metavar=None`
			
			self.enum_class = enum_class
			assert kwargs.get('choices',None) is None, "EnumChoiceAction sets `choices`, so it must not be set previously."
			assert kwargs.get('type',None) is None, "EnumChoiceAction sets `type`, so it must not be set previously."
			
			kwargs['choices'] = tuple(x.name for x in self.enum_class)
			#kwargs['type'] = lambda x: self.enum_class[x]
			
			super().__init__(option_strings, dest, **kwargs)
		
		def __call__(self, parser, namespace, values, option_string=None):
			#print(f'{(parser, namespace, values, option_string)=}')
			setattr(namespace, self.dest, enum_class[values] if isinstance(values, str) else [enum_class[x] for x in values])
	
	return EnumChoiceAction


class ArgArray1D:
	
	class GridAction(ap.Action):
		def __call__(self, parser, namespace, values, option_string=None):
			#print(f'{(parser, namespace, values, option_string)=}')
			assert len(values) == 3, "Must have 3 values to specify a 1d grid"
			setattr(namespace, self.dest, np.linspace(float(values[0]), float(values[1]), int(values[2])))
	
	class RangeAction(ap.Action):
		def __call__(self, parser, namespace, values, option_string=None):
			#print(f'{(parser, namespace, values, option_string)=}')
			assert len(values) == 3, "Must have 3 values to specify a 1d range"
			setattr(namespace, self.dest, np.arange(float(values[0]), float(values[1]), float(values[2])))
	
	class PointsAction(ap.Action):
		def __call__(self, parser, namespace, values, option_string=None):
			#print(f'{(parser, namespace, values, option_string)=}')
			assert len(values) > 0, "Must have some values to specify a set of 1d points"
			setattr(namespace, self.dest, np.array(values,dtype=float))
	
	class LogGridAction(ap.Action):
		def __call__(self, parser, namespace, values, option_string=None):
			#print(f'{(parser, namespace, values, option_string)=}')
			assert len(values) == 3, "Must have 3 values to specify a 1d grid"
			setattr(namespace, self.dest, np.geomspace(float(values[0]), float(values[1]), int(values[2])))
	
	class LogRangeAction(ap.Action):
		def __call__(self, parser, namespace, values, option_string=None):
			#print(f'{(parser, namespace, values, option_string)=}')
			assert len(values) == 3, "Must have 3 values to specify a 1d range"
			
			v0, v1, v2 = float(values[0]), float(values[1]), float(values[2])
			setattr(namespace, self.dest, np.exp(np.arange(np.log(v0), np.log(v1), np.log(v2)     )))
	
	@classmethod
	def add_to_parser(cls, parser : ap.ArgumentParser, name : str, dest : str = '', required=False, description : str = '', enable_linear : bool = True, enable_log : bool = False, default : Any = None):
		if len(dest) == 0:
			dest = f'{name}_array'
		
		containing_group = parser.add_argument_group('Select One'+' (required)' if required else ' (optional)', description)
		mutex_grp = containing_group.add_mutually_exclusive_group(required=required)
		
		if enable_linear:
			mutex_grp.add_argument(
				f"--{name}_grid", 
				nargs=3, 
				dest = dest,
				action=cls.GridAction,
				metavar=('<min>','<max>','<n>'), 
				help='Specified as a grid with `n` points between `min` and `max` (inclusive).', 
				default=default
			)
			
			mutex_grp.add_argument(
				f"--{name}_range", 
				nargs=3, 
				dest = dest,
				action = cls.RangeAction,
				metavar=('<min>','<max>','<delta>'), 
				help='Specified as a range of points `delta` apart between `min` and `max` (not inclusive).', 
				default=default
			)
			
			mutex_grp.add_argument(
				f"--{name}_points", 
				nargs='+', 
				dest = dest,
				action=cls.PointsAction,
				metavar=('<value>'), 
				help='Specified as a list of points', 
				default=default
			)
		if enable_log:
			mutex_grp.add_argument(
				f"--{name}_log_grid", 
				nargs=3, 
				dest = dest,
				action=cls.LogGridAction,
				metavar=('<min>','<max>','<n>'), 
				help='Specified as a logarithmically spaced grid with `n` points between `min` and `max` (inclusive).', 
				default=default
			)
			
			mutex_grp.add_argument(
				f"--{name}_log_range", 
				nargs=3, 
				dest = dest,
				action = cls.LogRangeAction,
				metavar=('<min>','<max>','<factor>'), 
				help='Specified as a logarithmically spaced range of points `factor` apart between `min` and `max` (not inclusive).', 
				default=default
			)

		return dest, containing_group, mutex_grp
		


