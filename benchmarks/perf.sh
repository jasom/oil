#!/usr/bin/env bash
#
# Run the 'perf' tool and associated reports on OSH.
#
# Usage:
#   benchmarks/perf.sh <function name>
#
# Deps:
#
#   Clone https://github.com/brendangregg/FlameGraph
#   Put it in ~/git/other/FlameGraph, or edit the paths below
#
# Examples:
#
#   $0 install  # install perf, including matching kernel symbols
#
#   $0 profile-osh-parse       # make flame graph
#
#   Then look at _tmp/perf/osh-parse.svg in the browser

#   $0 profile-osh-parse flat  # make flat text report
#
#   perf report -i _tmp/perf/osh-parse.perf  #  interactive
#
# Likewise for
#
#   $0 profile-example escape
#     => _tmp/perf/example-escape.svg
#   $0 profile-example escape flat
#     => _tmp/perf/example-escape.report.txt

set -o nounset
set -o pipefail
set -o errexit

readonly BASE_DIR=_tmp/perf

# TODO:
# - kernel symbols.  Is that why there are a lot of [unknown] in opt mode?
# - grep for call_function in collapsed.  I don't see it?
#   - it's inlined I guess?

# Question: PyEval_EvalFrameEx doesn't appear recursive in opt mode?  At least
# according to 'perf'.  Or maybe you don't have enough samples to catch it?

# NOTES:
# - dbg vs. opt matters a lot
# - function-level performance categorization is bad for bytecode interpreters,
#   which have a single function and a big switch statement.
# - a longer file like configure-coreutils hit garbage collection!  collect()
# - reference counting functions: visit_decref, visit_reachable

install() {
  # linux-tools-generic is the kernel module
  # Apparently you need a package specific to the kernel, not sure why.
  sudo apt install linux-tools-common linux-tools-$(uname -r) linux-tools-generic
}

debug-symbols() {
  #dpkg --listfiles linux-tools-4.13.0-36-generic
  #sudo apt install python-dbg

  # I don't see symbols files here?  Just the interpreter?  They're built into the ELF file?
  #dpkg --listfiles python-dbg

  # has files in /usr/lib/debug
  # file /usr/lib/debug/.build-id/8d/9bd4ce26e45ef16075c67d5f5eeafd8b562832.debug
  # /usr/lib/debug/.build-id/8d/9bd4ce26e45ef16075c67d5f5eeafd8b562832.debug: ELF 64-bit LSB shared object, x86-64, version 1 (SYSV), dynamically linked, BuildID[sha1]=8d9bd4ce26e45ef16075c67d5f5eeafd8b562832, not stripped
  #
  # https://sourceware.org/gdb/onlinedocs/gdb/Separate-Debug-Files.html

  # Does perf also support separate debug files?
  # How do I set the debug link in oil.ovm?  Or should I set build ID?

  # The GNU binary utilities (Binutils) package includes the ‘objcopy’ utility
  # that can produce the separated executable / debugging information file
  # pairs using the following commands:
  # objcopy --only-keep-debug foo foo.debug
  # strip -g foo

  sudo apt install zlib1g-dbg
  dpkg --listfiles zlib1g-dbg
  #libpython2.7-dbg 
}

# TODO: Link these two tools in ../oil_DEPS/bin or something
# Make them work on CI

# NOTE: I used this before with python-flamegraph too.
flamegraph() {
  ~/git/other/FlameGraph/flamegraph.pl "$@"
}

stackcollapse-perf() {
  ~/git/other/FlameGraph/stackcollapse-perf.pl "$@"
}

# http://www.brendangregg.com/FlameGraphs/cpuflamegraphs.html
make-graph() {
  local name=${1:-osh-parse}

  local dir=$BASE_DIR
  perf script -i $dir/$name.perf | stackcollapse-perf > $dir/$name.perf-folded

  flamegraph $dir/$name.perf-folded > $dir/$name.svg

  echo "Wrote $dir/$name.svg"
}

_make-readable() {
  local perf_raw=$1

  chmod 644 $perf_raw

  # original user
  chown $USER $perf_raw
}

make-readable() {
  # This gets run as root
  local name=$1

  local perf_raw=$BASE_DIR/$name.perf

  sudo $0 _make-readable $perf_raw

  file $perf_raw
  ls -l $perf_raw
}

_record-cpp() {
  local name=$1  # e.g. osh_eval, escape
  local mode=$2
  shift 2

  # Can repeat 13 times without blowing heap
  local freq=10000
  #export REPEAT=13 

  # call graph mode: needed to make flame graph
  local flag='-g'  

  #local flag='' # flat mode?

  local extra_flags=''
  case $mode in 
    (graph) extra_flags='-g' ;;
    (flat)  extra_flags='' ;;
    (*)     die "Mode should be graph or flat, got $mode" ;;
  esac

  time perf record $extra_flags -F $freq -o $BASE_DIR/$name.perf -- "$@"

  make-readable $name
}

profile-cpp() { 
  local name=$1
  local mode=$2
  shift

  mkdir -p $BASE_DIR

  # -E preserve environment like BENCHMARK=1
  sudo -E $0 _record-cpp $name "$@";

  case $mode in 
    (graph)
      make-graph $name
      ;;
    (flat)
      local out=$BASE_DIR/$name.report.txt
      text-report $name | tee $out
      echo "Wrote $out"
      ;;
    (*)
      die "Mode should be graph or flat, got $mode"
      ;;
  esac
}

profile-osh-parse() {
  # Profile parsing a big file.  More than half the time is in malloc
  # (_int_malloc in GCC), which is not surprising!

  local mode=${1:-graph}

  local bin='_bin/cxx-opt/osh_eval'
  ninja $bin
  profile-cpp 'osh-parse' $mode $bin --ast-format none -n benchmarks/testdata/configure
}

profile-example() {
  local example=${1:-escape}
  local mode=${2:-graph}

  local bin="_bin/cxx-opt/mycpp/examples/$example.mycpp"

  ninja $bin
  echo

  BENCHMARK=1 profile-cpp "example-$example" $mode $bin
}

profile-hash-table() {
  local mode=${1:-graph}

  local bin='_bin/cxx-opt/mycpp/hash_table'
  ninja $bin
  profile-cpp 'hash_table' $mode $bin -t hash_speed_test
}

# Perf note: Without -o, for some reason osh output is shown on the console.
# It doesn't go to wc?
#perf record -o perf.data -- _bin/osh -n benchmarks/testdata/abuild | wc -l

text-report() {
  ### Show a batch report; 'perf report' is interactive

  local name=$1
  shift

  local perf_raw=$BASE_DIR/$name.perf

  # Flat report
  perf report -i $perf_raw -n --stdio "$@"
}

# Shows instruction counts, branch misses, and so forth
#
# Wow 11 billion instructions!  9 billion cycles.  2.3 billion branches.  Crazy.
# Only 21M branch misses, or 0.9%.  Interesting.
_stat() {
  perf stat -- "$@" | wc -l
  # -e cache-misses only shows that stat
}
stat() { sudo $0 _stat "$@"; }

stat-osh-parse() {
  stat _bin/cxx-opt/osh_eval --ast-format none -n benchmarks/testdata/configure
}


#
# OLD OVM stuff
#

# Parsing abuild in Debug mode:
# 14%  PyEval_EvalFrameEx  -- hm.  Interpreter dispatch is a lot?  More than I
#      thought.  Maybe need my own loop.
# 8%   type_call -- hm introspection?
# 7%   PyObject_GetAttr.  My intitution.  Should be done at compile time!
# 6%   do_richcmp  -- hm interesting
# 5%   PyObject_Malloc.

# More benchmarks:
# OPy running under OVM, compiling itself, compiling Oil, compiling OPy ports,
# etc.

# Parsing abuild, the optimized version.
#
# 80% PyEval_EvalFramEx.  Woah everything is inlined?
# 12.5%  PyObject_GenericGetAtr.  PyObject_GetAttr is much lower down.
# Some kernel.
# 0.76%  lookdict_string is not a bottleneck.  Hm.
#
# Wow.
# Maybe I need counters in optimized mode?
# Yeah what I really want is per opcode total!

_record() {

  # TODO: The optimized build should have symbols!  Don't build with -s.  And
  # then put symbols next to the binary somehow?  How do the symbols packages
  # work?
  #perf record -o perf.data -- _bin/oil.ovm-dbg osh -n benchmarks/testdata/abuild | wc -l

  # call graph recording.  This helps it be less "flat" in opt mode.  Otherwise
  # everything is PyEval_EvalFrameEx.
  local flag='-g'
  local bin=_bin/oil.ovm-opt 
  #local bin=_bin/oil.ovm-dbg  # This shows more details

  local freq=1000  # 1000 Hz

  #local file=benchmarks/testdata/abuild  # small file

  local file=benchmarks/testdata/configure-coreutils  # big file

  time perf record $flag -F $freq -o perf.data -- $bin osh --ast-format none -n $file
  #perf record -o perf.data -- _bin/osh --ast-format none -n benchmarks/testdata/abuild
}
record() { sudo $0 _record; }


"$@"
