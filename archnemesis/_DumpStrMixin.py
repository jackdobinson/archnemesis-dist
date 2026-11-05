
import inspect
from typing import Generator, Any

import numpy as np

class DumpStrMixin:

    def _iter_pub_attrs_and_properties(self) -> Generator[tuple[str, Any]]:
        for attr_name in dir(self):
            if attr_name.startswith('_'):
                continue
            
            try:
                value = getattr(self, attr_name)
            except:
                value = '[ERROR WHEN ACCESSING ATTRIBUTE]'
            
            if isinstance(getattr(self.__class__, attr_name, None), property):
                yield attr_name, value
            
            
            elif inspect.ismethod(value) or inspect.isfunction(value):
                continue
            
            else:
                yield attr_name, value

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(' + ', '.join(f'{k}={v}' for k,v in self._iter_pub_attrs_and_properties()) + ')'
    
    
    def _gen_attr_dumps(self, indent_level=0, indent='    ', width=140) -> Generator[str]:
        w1 = width - len((indent_level+1)*indent)
        break_strs = (':', ',', '(', '[', '{', ')', ']', '}', ' ', '\t', ) # these are checked in order from left to right
        
        with np.printoptions(threshold=7, edgeitems=3):
            
            for attr_name, value in self._iter_pub_attrs_and_properties():
                yield indent_level*indent+attr_name
                
                if (dump_str_method := getattr(value, 'dump_str', None)) is not None:
                    yield dump_str_method(indent_level=indent_level+1, indent=indent)
                
                else:
                    str_value = str(value)
                    
                    for str_value_line in str_value.split('\n'):
                        n = len(str_value_line)
                        
                        if n <= w1:
                            yield (indent_level+1)*indent + str_value_line
                        
                        else:
                            i = 0
                            m = n
                            while m > w1:
                                end = -1
                                for break_str in break_strs:
                                    end = str_value_line.rfind(break_str, i, i+w1)
                                    if end != -1:
                                        end += 1
                                        break
                                if end == -1:
                                    end = i+w1
                                yield (indent_level+1)*indent + str_value_line[i:end]
                                i = end
                                m = n - i
                            
                            yield (indent_level+1)*indent + str_value_line[i:]
                    
    
    def dump_str(self, indent_level=0, indent='    ', width=140) -> str:
        return (
            indent_level*indent+self.__class__.__name__+' {\n'
            + '\n'.join(self._gen_attr_dumps(indent_level=indent_level+1, indent=indent, width=width))
            + ('\n'+indent_level*indent+'}')
        )