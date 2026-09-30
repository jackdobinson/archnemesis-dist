


# Different versions of python handle annotations differently
import sys
if (sys.version_info.major, sys.version_info.minor) >= (3, 14):
	import annotationlib
	def get_annotations(obj):
		return annotationlib.get_annotations(obj, format=annotationlib.Format.FORWARDREF)
	
	def get_annotations_from_dict(d):
		annotations = d.get('__annotations__', None)
		annotate_fn = annotationlib.get_annotate_from_class_namespace(d)
		if annotate_fn is None:
			annotate_fn = d.get('__annotate_func__',None)
		
		if annotations is None:
			if annotate_fn is None:
				return dict()
			else:
				annotationlib.call_annotate_function(annotate_fn, annotationlib.Format.FORWARDREF)
		else:
			if annotate_fn is not None:
				if '__annotate__' in d:
					d['__annotate__'] = None
			return annotations
else:
	def get_annotations(obj):
		return obj.__annotations__
	def get_annotations_from_dict(d):
		return d.get('__annotations__', dict())