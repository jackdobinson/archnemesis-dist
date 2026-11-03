



import numpy as np

def get_edges_from_mids(a) -> np.ndarray:
	s0 = a.shape[0]
	e = np.empty((s0+1, *a.shape[1:]), dtype=a.dtype)
	e[0] = 1.5*a[0] - 0.5*a[1]
	e[1:-1] = 0.5*(a[:-1] + a[1:])
	e[-1] = 1.5*a[-1] - 0.5*a[-2]
	return e

def get_mids_from_edges(a) -> np.ndarray:
	return 0.5*(a[:-1]+a[1:])