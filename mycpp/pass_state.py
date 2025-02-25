"""
pass_state.py
"""
from __future__ import print_function

import sys

from collections import defaultdict

#from mycpp.util import log


class Virtual(object):
  """
  See unit test for example usage.
  """

  def __init__(self) -> None:
    self.methods: dict[str, list[str]] = defaultdict(list)
    self.subclasses: dict[str, list[str]] = defaultdict(list)
    self.virtuals: list[tuple[str, str]] = []
    self.has_vtable: dict[str, bool] = {}

    # _Executor -> vm::_Executor
    self.base_class_unique: dict[str, str] = {}

  # These are called on the Forward Declare pass
  def OnMethod(self, class_name: str, method_name: str) -> None:
    #log('OnMethod %s %s', class_name, method_name)
    self.methods[class_name].append(method_name)

  def OnSubclass(self, base_class: str, subclass: str) -> None:
    if '::' in base_class:
      # Hack for
      #
      # class _Executor: pass
      #   versus
      # class MyExecutor(vm._Executor): pass
      base_key = base_class.split('::')[1]

      # Fail if we have two base classes in different namespaces with the same
      # name.
      if base_key in self.base_class_unique:
        # Make sure we don't have collisions
        assert self.base_class_unique[base_key] == base_class
      else:
        self.base_class_unique[base_key] = base_class

    else:
      base_key = base_class

    self.subclasses[base_key].append(subclass)

  def Calculate(self) -> None:
    """
    Call this after the forward declare pass.
    """
    for base_class, subclasses in self.subclasses.items():
      for subclass in subclasses:
        b_methods = self.methods[base_class]
        s_methods = self.methods[subclass]
        overlapping = set(b_methods) & set(s_methods)
        for method in overlapping:
          self.virtuals.append((base_class, method))
          self.virtuals.append((subclass, method))
        if overlapping:
          self.has_vtable[base_class] = True
          self.has_vtable[subclass] = True

  # These is called on the Decl pass
  def IsVirtual(self, class_name: str, method_name: str) -> bool:
    return (class_name, method_name) in self.virtuals

  def HasVTable(self, class_name: str) -> bool:
    return class_name in self.has_vtable
