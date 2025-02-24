#!/usr/bin/env python2
"""
strings.py
"""
from __future__ import print_function

import os
from mycpp.mylib import log


class Foo(object):
  def __init__(self):
    # type: () -> None
    self.s = 'mystr'


def run_tests():
  # type: () -> None

  print('foo' + 'bar')
  print('foo' * 3)
  obj = Foo()
  print('foo' + obj.s)

  s = 'mystr'
  print('[%s]' % s)

  s = 'mystr'
  print('[%s, %s]' % (s, 'abc'))

  print('%s: 5%%-100%%' % 'abc')

  print('<a href="foo.html">%s</a>' % 'anchor')

  print("foo? %d" % ('f' in s))
  print("str? %d" % ('s' in s))

  print("int 5d %5d" % 35)


  print("'single'")
  print('"double"')

  # test escape codes
  print("a\tb\nc\td\n")

  x = 'x'
  print("%s\tb\n%s\td\n" % (x, x))


def run_benchmarks():
  # type: () -> None
  pass


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
