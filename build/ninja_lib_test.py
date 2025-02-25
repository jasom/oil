#!/usr/bin/env python2
"""
ninja_lib_test.py: Tests for ninja_lib.py
"""
from __future__ import print_function

import sys
import unittest

from build import ninja_lib  # module under test
from vendor import ninja_syntax


class NinjaTest(unittest.TestCase):
  def setUp(self):
    pass

  def tearDown(self):
    pass

  def testBuild(self):
    n = ninja_syntax.Writer(sys.stdout)
    ru = ninja_lib.Rules(n)

    config = ('cxx', 'dbg')
    ru.compile('foo.o', 'foo.cc', [], config)

    matrix = [
        ('cxx', 'dbg'),
        ('cxx', 'opt'),
        ]
    # TODO: eliminate matrix arg
    ru.cc_library('//mycpp/ab', ['mycpp/a.cc', 'mycpp/b.cc'], matrix=matrix)
    ru.cc_library('//mycpp/z', ['mycpp/z.cc'], matrix=matrix)

    ru.cc_binary('mycpp/a_test.cc', matrix=matrix)

    ru.asdl_cc('mycpp/examples/foo.asdl')

    # TODO:
    # - Make cc_library lazy
    # - Make ASDL lazily produce a 'compile' action, in addition to the 'asdl-cpp'
    # - Both are with respect to a configuration

    # Should we also have WritePhony() and so forth?

  def testShWrap(self):
    # TODO: add py_binary and so forth
    pass

  def testAdvanced(self):
    # TODO:
    # - Transitive deps with cc_library()
    # - Diamond dependencies
    # - Circular dependencies
    pass


if __name__ == '__main__':
  unittest.main()
