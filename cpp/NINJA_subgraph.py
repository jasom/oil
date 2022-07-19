#!/usr/bin/env python2
"""
cpp/NINJA_subgraph.py

Runtime options:

  CXXFLAGS     Additional flags to pass to the C++ compiler

Phony targets

  osh-eval-all   # all variants of the binary
  mycpp-all      # all mycpp/examples
  mycpp-typecheck, etc.

  TODO: unit tests

Directory structure:

_test/ 
  bin/
    unit/

_build/   # input source

  cpp/    # _build/gen is more consistent, but it would take a lot of renaming
    osh_eval.{h,cc}

  obj/
    # The obj folder is a 2-tuple {cxx,clang}-{dbg,opt,asan ...}

    cxx-asan/
      osh_eval.o
      osh_eval.d     # dependency file
      osh_eval.json  # when -ftime-trace is passed
    cxx-dbg/
    cxx-opt/

  preprocessed/
    cxx-dbg/
      leaky_posix.cc
    cxx-dbg.txt  # line counts


_bin/   # output binaries
  # The _bin folder is a 3-tuple {cxx,clang}-{dbg,opt,asan ...}-{,sh,together}
    osh_eval

  cxx-opt/
    osh_eval
    osh_eval.stripped              # The end user binary
    osh_eval.symbols

  cxx-opt-sh/                      # with shell script

  cxx-opt-together/                # one compiler invocation, could delete
    osh_eval
    osh_eval.{stripped,symbols}

TODO

- Could fold bloaty reports in here?  See metrics/native-code.sh
  - Takes both dbg and opt.  Depends on the symbolized, optimized file.
  - make bloaty report along with total size in the continuous build?
    - although it depends on R, and we don't have Clang
- Port test/cpp-unit.sh logic here
  - declare dependencies, could use same pattern as mycpp/build_graph.py
"""

from __future__ import print_function

import os
import sys


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


DEPS_CC = [
    'cpp/leaky_core_pyos.cc',
    'cpp/leaky_core_pyutil.cc',
    'cpp/leaky_frontend_flag_spec.cc',
    'cpp/leaky_frontend_match.cc',
    'cpp/leaky_frontend_tdop.cc',
    'cpp/leaky_osh_arith_parse.cc',
    'cpp/leaky_osh_bool_stat.cc',
    'cpp/leaky_pgen2_parse.cc',
    'cpp/leaky_pylib.cc',
    'cpp/leaky_dumb_alloc.cc',
    'cpp/leaky_fcntl_.cc',
    'cpp/leaky_posix.cc',
    'cpp/leaky_signal_.cc',
    'cpp/leaky_libc.cc',

    # generated
    # TODO: We're missing dependencies for these
    '_build/cpp/arg_types.cc',
    '_build/cpp/arith_parse.cc',
    '_build/cpp/consts.cc',
    '_build/cpp/osh_eval.cc',

    # ASDL generated
    '_build/cpp/runtime_asdl.cc',
    '_build/cpp/syntax_asdl.cc',
    '_build/cpp/hnode_asdl.cc',
    '_build/cpp/id_kind_asdl.cc',
]

# Note: also appears in mycpp/build_graph.py
GC_RUNTIME = [
    'mycpp/gc_heap.cc',
    'mycpp/mylib2.cc',
    'mycpp/my_runtime.cc',
]

OLD_RUNTIME = [
    'mycpp/gc_heap.cc',  # We need this?
    'mycpp/mylib_leaky.cc',
]


# -D DUMB_ALLOC: not sure why but only the _bin/cxx-opt/osh_eval binary needs it?
# -D NO_GC_HACK: Avoid memset().  TODO: remove this hack!
# -D OSH_EVAL: hack for leaky_osh_eval_stubs.h
# -D LEAKY_BINDINGS: for QSN, which is used by the ASDL runtime

# single quoted in Ninja/shell syntax
OSH_EVAL_FLAGS_STR = "'-D DUMB_ALLOC -D NO_GC_HACK -D OSH_EVAL -D LEAKY_BINDINGS'"


def NinjaGraph(n):

  n.comment('Build oil-native')
  n.comment('Generated by %s.' % __file__)
  n.newline()

  # Preprocess one translation unit
  n.rule('preprocess',
         # compile_one detects the _build/preprocessed path
         command='cpp/NINJA-steps.sh compile_one $compiler $variant $more_cxx_flags $in $out',
         description='PP $compiler $variant $more_cxx_flags $in $out')
  n.newline()

  # Preprocess one translation unit
  n.rule('line_count',
         command='cpp/NINJA-steps.sh line_count $out $in',
         description='line_count $out $in')
  n.newline()

  # 'together' build
  n.rule('compile_and_link',
         # multiple outputs
         command='cpp/NINJA-steps.sh compile_and_link $compiler $variant $more_cxx_flags $out $in',
         description='CXX,LINK $compiler $variant $more_cxx_flags $out $in')
  n.newline()

  # Compile one translation unit
  n.rule('compile_one',
         command='cpp/NINJA-steps.sh compile_one $compiler $variant $more_cxx_flags $in $out $out.d',
         depfile='$out.d',
         # no prefix since the compiler is the first arg
         description='$compiler $variant $more_cxx_flags $in $out')
  n.newline()

  # Link objects together
  n.rule('link',
         command='cpp/NINJA-steps.sh link $compiler $variant $out $in',
         description='LINK $compiler $variant $out $in')
  n.newline()

  # 1 input and 2 outputs
  n.rule('strip',
         command='cpp/NINJA-steps.sh strip_ $in $out',
         description='STRIP $in $out')
  n.newline()

  if 0:
    phony = {
        'osh-eval': [],  # build all osh-eval
        'strip': [],
    }

  binaries = []

  n.newline()

  for compiler in ['cxx', 'clang']:
    for variant in [
        'dbg', 'opt', 'asan', 'alloclog', 'malloc', 'uftrace',
        # leave out tcmalloc since it requires system libs to be installed
        # 'tcmalloc'
        ]:

      ninja_vars = [('compiler', compiler), ('variant', variant), ('more_cxx_flags', OSH_EVAL_FLAGS_STR)]

      sources = DEPS_CC + OLD_RUNTIME

      #
      # See how much input we're feeding to the compiler.  Test C++ template
      # explosion, e.g. <unordered_map>
      #

      preprocessed = []
      for src in sources:
        # e.g. _build/obj/dbg/posix.o
        base_name, _ = os.path.splitext(os.path.basename(src))

        pre = '_build/preprocessed/%s-%s/%s.cc' % (compiler, variant, base_name)
        preprocessed.append(pre)

        n.build(pre, 'preprocess', [src], variables=ninja_vars)
        n.newline()

      n.build('_build/preprocessed/%s-%s.txt' % (compiler, variant),
              'line_count', preprocessed, variables=ninja_vars)
      n.newline()

      #
      # TOGETHER
      #

      bin_together = '_bin/%s-%s-together/osh_eval' % (compiler, variant)
      binaries.append(bin_together)

      n.build(bin_together, 'compile_and_link',
              sources, variables=ninja_vars)
      n.newline()

      #
      # SEPARATE: Compile objects
      #

      objects = []
      for src in sources:
        # e.g. _build/obj/dbg/posix.o
        base_name, _ = os.path.splitext(os.path.basename(src))

        obj = '_build/obj/%s-%s/%s.o' % (compiler, variant, base_name)
        objects.append(obj)

        n.build(obj, 'compile_one', [src], variables=ninja_vars)
        n.newline()

      bin_separate = '_bin/%s-%s/osh_eval' % (compiler, variant)
      binaries.append(bin_separate)

      #
      # SEPARATE: Link objects into binary
      #

      link_vars = [('compiler', compiler), ('variant', variant)]  # no CXX flags
      n.build(bin_separate, 'link', objects, variables=link_vars)
      n.newline()

      # Strip the .opt binary
      if variant == 'opt':
        for b in [bin_together, bin_separate]:
          stripped = b + '.stripped'
          symbols = b + '.symbols'
          n.build([stripped, symbols], 'strip', [b])
          n.newline()

          binaries.append(stripped)

  n.default(['_bin/cxx-dbg/osh_eval'])

  # All groups
  n.build(['osh-eval-all'], 'phony', binaries)


def ShellFunctions(f, argv0):
  """
  Generate a shell script that invokes the same function that build.ninja does
  """
  print('''\
#!/usr/bin/env bash
#
# _build/oil-native.sh - generated by %s
#
# Usage
#   _build/oil-native COMPILER? VARIANT? SKIP_REBUILD?
#
#   COMPILER: 'cxx' for system compiler, or 'clang' [default cxx]
#   VARIANT: 'dbg' or 'opt' [default dbg]
#   SKIP_REBUILD: if non-empty, checks if the output exists before building
#
# Could run with /bin/sh, but use bash for now, bceause dash has bad errors messages!
#!/bin/sh

. cpp/NINJA-steps.sh

main() {
  ### Compile oil-native into _bin/$compiler-$variant-sh/ (not with ninja)

  local compiler=${1:-cxx}   # default is system compiler
  local variant=${2:-opt}    # default is optimized build
  local skip_rebuild=${3:-}  # if the output exists, skip build'

  local more_cxx_flags=%s
''' % (argv0, OSH_EVAL_FLAGS_STR), file=f)

  out = '_bin/$compiler-$variant-sh/osh_eval'
  print('  local out=%s' % out, file=f)

  print('''\
  if test -n "$skip_rebuild" && test -f "$out"; then
    echo
    echo "$0: SKIPPING build because $out exists"
    echo
    return
  fi

  echo
  echo "$0: Building oil-native: $out"
  echo

  mkdir -p "_build/obj/$compiler-$variant-sh" "_bin/$compiler-$variant-sh"
''', file=f)

  objects = []
  for src in DEPS_CC + OLD_RUNTIME:
    # e.g. _build/obj/dbg/posix.o
    base_name, _ = os.path.splitext(os.path.basename(src))

    obj_quoted = '"_build/obj/$compiler-$variant-sh/%s.o"' % base_name
    objects.append(obj_quoted)

    print("  echo 'CXX %s'" % src, file=f)
    print('  compile_one "$compiler" "$variant" "$more_cxx_flags" \\', file=f)
    print('    %s %s' % (src, obj_quoted), file=f)

  print('', file=f)

  print('  echo "LINK $out"', file=f)
  # note: can't have spaces in filenames
  print('  link "$compiler" "$variant" "$out" \\', file=f)
  # put each object on its own line, and indent by 4
  print('    %s' % (' \\\n    '.join(objects)), file=f)
  print('', file=f)

  # Strip opt binary
  # TODO: provide a way for the user to get symbols?

  print('''\
  if test "$variant" = opt; then
    strip -o "$out.stripped" "$out"
  fi
}

main "$@"
''', file =f)
