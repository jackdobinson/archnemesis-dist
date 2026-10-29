

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


from archnemesis.enum import WaveUnitEnum
from archnemesis.helpers.wave_helper import waves_as_unit
from archnemesis.helpers.plot_helper import ShowPlotFnFactory

from .data import LblTableData
from .file import LblTableFile


import archnemesis.cfg.logs as logging
_lgr = logging.getLogger(__name__)
_lgr.setLevel(logging.DEBUG)

def plot(
		lbl_table_data : LblTableData, 
		wave_unit : WaveUnitEnum = WaveUnitEnum.Wavenumber_cm,
		path=None,
		save_plots : None | Path = None,
		no_show_plots : bool = False,
):
	
	fig = plt.figure(figsize=(12,8))
	
	
	_lgr.info(f'{lbl_table_data.mol_id=}')
	_lgr.info(f'{lbl_table_data.iso_id=}')
	_lgr.info(f'{lbl_table_data.wavenumbers.shape=}')
	_lgr.info(f'{lbl_table_data.pressures.shape=}')
	_lgr.info(f'{lbl_table_data.temperatures.shape=}')
	_lgr.info(f'{lbl_table_data.opacities.shape=}')
	
	_lgr.info(f'{lbl_table_data.wavenumbers=}')
	_lgr.info(f'{lbl_table_data.pressures=}')
	_lgr.info(f'{lbl_table_data.temperatures=}')
	_lgr.info(f'{lbl_table_data.opacities=}')
	
	_lgr.info(f'{save_plots=}')
	_lgr.info(f'{no_show_plots=}')
	# Get directory to save plots to
	show_plot_fn = ShowPlotFnFactory(save_plots, no_show_plots)
	
	if np.any(np.diff(lbl_table_data.pressures) <0):
		# pressures are not sorted in ascending order
		sorted_pressures_idxs = np.argsort(lbl_table_data.pressures)
	else:
		sorted_pressures_idxs = None
		
	sorted_pressures = np.sort(lbl_table_data.pressures)
	
	
	waves = waves_as_unit(lbl_table_data.wavenumbers, WaveUnitEnum.Wavenumber_cm, wave_unit)
	if wave_unit == WaveUnitEnum.Wavenumber_cm:
		wave_ax_label = 'Wavenumber (cm^{-1})'
	elif wave_unit == WaveUnitEnum.Wavelength_um:
		wave_ax_label = 'Wavelength (um)'
	else:
		raise RuntimeError(f'Unknown unit {wave_unit} cannot get xlabel')
	
	if np.any(np.diff(waves) <0):
		# wavenumbers are not sorted in ascending order
		sorted_wave_idxs = np.argsort(waves)
	else:
		sorted_wave_idxs = None
	
	sorted_waves = np.sort(waves)

	if lbl_table_data.temperatures.ndim == 1:
		ax_width = 0.7
	else:
		ax_width = 0.52

	ax = fig.add_axes((0.2,0.2,ax_width,0.7), )
	ax.xaxis.set_visible(False)
	ax.yaxis.set_visible(False)
	
	ax.set_xlabel(wave_ax_label)
	ax.set_ylabel('Pressure (atm)')
	
	
	ax_cbar = fig.add_axes((0.9,0.2,0.02,0.7),)
	#ax_cbar.set_ylabel()
	
	if lbl_table_data.temperatures.ndim != 1:
		ax_temp = fig.add_axes((0.73,0.2,0.15,0.7), sharey=ax)
		ax_temp.tick_params(axis='y', which='both',direction='out')
		ax_temp.yaxis.set_visible(False)
		ax_temp.set_xlabel('Temperature (Kelvin)')
		#ax_temp.set_ylabel('Pressure (atm)')
	
	

	wave_edges = np.empty(waves.size+1) # filled in later
	press_edges = np.empty(sorted_pressures.size+1) # filled in later
	opacity_grid = np.empty((sorted_pressures.size,waves.size)) # filled in later
	
	wave_edges[1:-1] = 0.5*(sorted_waves[:-1] + sorted_waves[1:])
	wave_edges[0] = 2*sorted_waves[0] - wave_edges[1]
	wave_edges[-1] = 2*sorted_waves[-1] - wave_edges[-2]
	
	# Use geometric means
	#press_edges[1:-1] = 0.5*(sorted_pressures[:-1] + sorted_pressures[1:])
	press_edges[1:-1] = np.sqrt(sorted_pressures[:-1]*sorted_pressures[1:])
	#press_edges[0] = 2*sorted_pressures[0] - press_edges[1]
	press_edges[0] = (sorted_pressures[0]**2)/press_edges[1]
	#press_edges[-1] = 2*sorted_pressures[-1] - press_edges[-2]
	press_edges[-1] = (sorted_pressures[-1]**2)/press_edges[-2]
	_lgr.info(f'{press_edges=}')
	
	
	ax_ymargin = fig.add_axes((0.07,0.2,0.1,0.7), sharey=ax)
	ax_xmargin = fig.add_axes((0.2,0.07,ax_width,0.1), sharex=ax)
	ax_ymargin.set_xscale('log')
	ax_xmargin.set_yscale('log')
	
	ax_ymargin.set_xlabel('Opacity\n(cm^2)')
	ax_ymargin.set_ylabel('Pressure (atm)')
	ax_xmargin.set_xlabel(wave_ax_label)
	#ax_xmargin.set_ylabel('Opacity\n(cm^2)')
	
	ax_ymargin.hlines(press_edges, np.min(lbl_table_data.opacities), np.max(lbl_table_data.opacities), lw=0.5, ls='--', color='red', alpha=0.3)
	
	ymargin_line, = ax_ymargin.plot(np.full_like(sorted_pressures, fill_value=np.nan), marker='none', lw=1)
	xmargin_line, = ax_xmargin.plot(np.full_like(sorted_waves, fill_value=np.nan), marker='none', lw=0.5)

	mouse_pos_xmargin = ax_xmargin.axvline(np.nan, ls=':', lw=0.5, color='black')
	mouse_pos_ymargin = ax_ymargin.axhline(np.nan, ls=':', lw=0.5, color='black')
	
	fig_state = {'closed' : False}
	
	def on_mouse_move(event):
		if ax.in_axes(event):
			#print(f'Pixel coords {event.x} {event.y}')
			#print(f'Data coords {event.xdata} {event.ydata}')
			
			w_idx = np.searchsorted(wave_edges, event.xdata) -1
			p_idx = np.searchsorted(press_edges, event.ydata) -1
			
			mouse_pos_ymargin.set_ydata((event.ydata,event.ydata))
			mouse_pos_xmargin.set_xdata((event.xdata,event.xdata))
			
			#print(f'{opacity_grid.shape=}')
			#print(f'{w_idx=} {p_idx=}')
			#print(f'{opacity_grid[:,w_idx].shape=} {opacity_grid[:,w_idx]=}')
			#print(f'{opacity_grid[p_idx,:].shape=} {opacity_grid[p_idx,:]=}')
			ymargin_line.set_data(opacity_grid[:,w_idx], sorted_pressures)
			xmargin_line.set_data(sorted_waves, opacity_grid[p_idx,:])
			
			fig.draw_artist(ax_ymargin)
			fig.draw_artist(ax_xmargin)
			fig.canvas.blit(ax_ymargin.bbox)
			fig.canvas.blit(ax_xmargin.bbox)
			#fig.canvas.draw_idle()
			#fig.canvas.flush_events()
	
	def on_close(event):
		fig_state['closed'] = True
	
	mouse_move_hdl = fig.canvas.mpl_connect('motion_notify_event', on_mouse_move)
	close_hdl = fig.canvas.mpl_connect('close_event', on_close)
	
	if lbl_table_data.temperatures.ndim == 1:
		n_temps = lbl_table_data.temperatures.size
	else:
		n_temps = lbl_table_data.temperatures.shape[1]
	
	
		ax_temp.set_title('Temperature profiles')
		for temp_idx in range(n_temps):
			ax_temp.plot(
				lbl_table_data.temperatures[:,temp_idx], 
				sorted_pressures, 
				marker='x',
				markersize=2, 
				lw=1, 
				alpha=0.6, 
				label=f't_prof {temp_idx}'
			)
		ax_temp.hlines(press_edges, *ax_temp.get_xlim(), lw=0.5, ls='--', color='red', alpha=0.3)
		ax_temp.legend()
	
	
	
	
	
	for temp_idx in range(n_temps):
		ax.clear()
		ax.yaxis.set_inverted(True)
		ax_cbar.clear()
		
		if lbl_table_data.temperatures.ndim == 1:
			ax.set_title(f'{path.name if path is not None else ""}\nOpacity at {lbl_table_data.temperatures[temp_idx]:.2f} K')
		else:
			ax.set_title(f'{path.name if path is not None else ""}\nOpacity at temperature profile {temp_idx}')
		
		if sorted_wave_idxs is None and sorted_pressures_idxs is None:
			opac_selector = (slice(None), slice(None))
		elif sorted_wave_idxs is None and sorted_pressures_idxs is not None:
			opac_selector = (slice(None), sorted_pressures_idxs)
		elif sorted_wave_idxs is not None and sorted_pressures_idxs is None:
			opac_selector = (sorted_wave_idxs, slice(None))
		else:
			opac_selector = (sorted_wave_idxs[:,None], sorted_pressures_idxs[None,:])
		
		_lgr.debug(f'{opac_selector=}')
		
		opacity_grid[...] = (lbl_table_data.opacities[
			*opac_selector,
			temp_idx
		]).T
		
		# TESTING
		#opacity_grid[5:10,100:200] = 0
		#opacity_grid[5:10,10000:20000] = 0
		
		opac_grid_nonzero_mask = opacity_grid > 0
		opac_lims = (np.min(opacity_grid[opac_grid_nonzero_mask]), np.max(opacity_grid[opac_grid_nonzero_mask]))
		ax_ymargin.set_xlim(opac_lims)
		ax_xmargin.set_ylim(opac_lims)
		
		opac_plot = ax.pcolormesh(
			wave_edges,
			press_edges,
			opacity_grid,
			norm='log'
		)
		
		ax.set_yscale('log')
		
		fig.colorbar(opac_plot, cax=ax_cbar, orientation='vertical', label='Opacity (cm^2)')
		
		w_idx = sorted_waves.size // 2
		p_idx = sorted_pressures.size // 2
		mouse_pos_ymargin.set_ydata((sorted_pressures[p_idx],sorted_pressures[p_idx]))
		mouse_pos_xmargin.set_xdata((sorted_waves[w_idx],sorted_waves[w_idx]))
		
		ymargin_line.set_data(opacity_grid[:,w_idx], sorted_pressures)
		xmargin_line.set_data(sorted_waves, opacity_grid[p_idx,:])
		
		fig.draw_artist(ax_ymargin)
		fig.draw_artist(ax_xmargin)
		fig.canvas.blit(ax_ymargin.bbox)
		fig.canvas.blit(ax_xmargin.bbox)
		
		if show_plot_fn(path.with_suffix('.png').name if path is not None else 'lbl.png', fig, interactive=True):
			fig.waitforbuttonpress()
			if fig_state['closed']:
				break
			
	fig.canvas.mpl_disconnect(mouse_move_hdl)
	fig.canvas.mpl_disconnect(close_hdl)
	plt.close(fig)






if __name__=='__main__':
	import sys, os
	import argparse as ap
	
	
	from archnemesis.helpers.argparse_helper import action_enum_choice
	
	
	print('TESTING :: lbltable_base.py')
	
	if True:
	#if False:
		TEMP_PATH_PLOT_DIR = Path(os.getenv('TMP', '/tmp')) / "archnemesis/spectral_data/plot"
	
		parser = ap.ArgumentParser()
				
		parser.add_argument('lbl_table_paths', type=Path, nargs='+',help='Paths of line-by-line tables to display')
		
		parser.add_argument('--read.wave_unit', action=action_enum_choice(WaveUnitEnum), help=f'The unit that the `wn` array is read as (default={WaveUnitEnum.Wavenumber_cm.name})', default=WaveUnitEnum.Wavenumber_cm)
		parser.add_argument('--display.wave_unit', action=action_enum_choice(WaveUnitEnum), help=f'The unit that the `wn` array is displayed in (default={WaveUnitEnum.Wavenumber_cm.name})', default=WaveUnitEnum.Wavenumber_cm)
		parser.add_argument('--save_plots', nargs='?', type=Path, help=f'If present will save plots to a temporary directory ({TEMP_PATH_PLOT_DIR}), if given with an argument will save plots to the specified directory, if not present will not save plots.', const=TEMP_PATH_PLOT_DIR, default=None)
		parser.add_argument('--no_show_plots', action='store_true', help='If present, will not show plots (default=False)', default=False)
	
		args = vars(parser.parse_args(sys.argv[1:]))
	
		read_args = dict((k[len('read.'):],v) for k,v in args.items() if k.startswith('read.'))
		display_args = dict((k[len('display.'):],v) for k,v in args.items() if k.startswith('display.'))
	
		_lgr.info(f'{read_args=}')
		_lgr.info(f'{display_args=}')
		
		[args.pop('read.'+k) for k in read_args]
		[args.pop('display.'+k) for k in display_args]
	
		for lbl_table_path in args.pop('lbl_table_paths'):
			_lgr.info(f'{lbl_table_path=}')
			with LblTableFile(lbl_table_path, 'r') as f:
				plot(
					f.read(**read_args),
					path = lbl_table_path,
					**display_args,
					**args,
				)
	