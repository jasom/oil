"""
prebuilt/NINJA_subgraph.py
"""

from __future__ import print_function

from build import ninja_lib
from build.ninja_lib import log
from cpp.NINJA_subgraph import ASDL_H, GENERATED_H

_ = log


# TODO: remove this; probably should be sh_binary
RULES_PY = 'build/ninja-rules-py.sh'

def NinjaGraph(ru):
  n = ru.n

  ru.comment('Generated by %s' % __name__)

  #
  # osh_eval.  Could go in bin/NINJA_subgraph.py
  #

  with open('_build/NINJA/osh_eval/translate.txt') as f:
    deps = [line.strip() for line in f]

  prefix = '_gen/bin/osh_eval.mycpp'
  # header exports osh.cmd_eval
  outputs = [prefix + '.cc', prefix + '.h']
  n.build(outputs, 'gen-osh-eval', deps,
          implicit=['_bin/shwrap/mycpp_main', RULES_PY],
          variables=[('out_prefix', prefix)])

  # Main program!
  ru.cc_binary(
      '_gen/bin/osh_eval.mycpp.cc',
      preprocessed = True,
      implicit = ASDL_H + GENERATED_H,
      matrix = ninja_lib.COMPILERS_VARIANTS,
      top_level = True,  # _bin/cxx-dbg/osh_eval
      deps = [
        '//cpp/leaky_core',
        '//cpp/leaky_bindings',
        '//frontend/arg_types',
        '//ASDL_CC',
        '//GENERATED_CC',
        '//mycpp/runtime',
        ]
      )
