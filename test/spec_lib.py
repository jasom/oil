"""
spec_lib.py

Shared between sh_spec.py (Python 2) and interactive.py (Python 3)!
"""
from __future__ import print_function

import optparse
import os
import re
import sys


def log(msg, *args):
  # type: (str, *Any) -> None
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def MakeShellPairs(shells):
  shell_pairs = []
  saw_osh = False
  saw_oil = False
  for path in shells:
    if 'osh_eval' in path:
      name = path
      if '_bin' in path:
        label = 'osh_.cc'
      elif 'bin' in path:
        label = 'osh_.py'
      else:
        raise AssertionError(path)
    else:
      name, _ = os.path.splitext(path)
      label = os.path.basename(name)
    #log('path = %s, label = %s', path, label)

    if label == 'osh':
      # change the second 'osh' to 'osh_ALT' so it's distinct
      if saw_osh:
        label = 'osh_ALT'
      else:
        saw_osh = True

    elif label == 'oil':
      if saw_oil:
        label = 'oil_ALT'
      else:
        saw_oil = True

    shell_pairs.append((label, path))
  return shell_pairs


RANGE_RE = re.compile('(\d+) \s* - \s* (\d+)', re.VERBOSE)


def ParseRange(range_str):
  try:
    d = int(range_str)
    return d, d  # singleton range
  except ValueError:
    m = RANGE_RE.match(range_str)
    if not m:
      raise RuntimeError('Invalid range %r' % range_str)
    b, e = m.groups()
    return int(b), int(e)


class RangePredicate(object):
  """Zero-based indexing, inclusive ranges."""

  def __init__(self, begin, end):
    self.begin = begin
    self.end = end

  def __call__(self, i, case):
    return self.begin <= i <= self.end


class RegexPredicate(object):
  """Filter by name."""

  def __init__(self, desc_re):
    self.desc_re = desc_re

  def __call__(self, i, case):
    return bool(self.desc_re.search(case['desc']))



def DefineCommon(p):
  """Flags shared between sh_spec.py and stateful/harness.py."""
  p.add_option(
      '-v', '--verbose', dest='verbose', action='store_true', default=False,
      help='Show details about test failures')
  p.add_option(
      '-r', '--range', dest='range', default=None,
      help='Execute only a given test range, e.g. 5-10, 5-, -10, or 5')
  p.add_option(
      '--regex', dest='regex', default=None,
      help='Execute only tests whose description matches a given regex '
           '(case-insensitive)')
  p.add_option(
      '--list', dest='do_list', action='store_true', default=None,
      help='Just list tests')
  p.add_option(
      '--osh-failures-allowed', dest='osh_failures_allowed', type='int',
      default=0, help="Allow this number of osh failures")


def DefineStateful(p):
  p.add_option(
      '--num-retries', dest='num_retries', 
      type='int', default=4, 
      help='Number of retries (for spec/stateful only)')
  p.add_option(
      '--pexpect-timeout', dest='pexpect_timeout', 
      type='float', default=1.0, 
      help='In seconds')
  p.add_option(
      '--results-file', dest='results_file', default=None,
      help='Write table of results to this file.  Default is stdout.')


def DefineShSpec(p):
  p.add_option(
      '-d', '--details', dest='details', action='store_true', default=False,
      help='Show details even for successful cases')
  p.add_option(
      '-t', '--trace', dest='trace', action='store_true', default=False,
      help='trace execution of shells to diagnose hangs')
  p.add_option(
      '-p', '--print', dest='do_print', action='store_true', default=None,
      help="Print test code, but don't run it")
  p.add_option(
      '--format', dest='format', choices=['ansi', 'html'],
      default='ansi', help="Output format (default 'ansi')")
  p.add_option(
      '--stats-file', dest='stats_file', default=None,
      help="File to write stats to")
  p.add_option(
      '--tsv-output', dest='tsv_output', default=None,
      help="Write a TSV log to this file.  Subsumes --stats-file.")
  p.add_option(
      '--stats-template', dest='stats_template', default='',
      help="Python format string for stats")

  p.add_option(
      '--path-env', dest='path_env', default='',
      help="The full PATH, for finding binaries used in tests.")
  p.add_option(
      '--tmp-env', dest='tmp_env', default='',
      help="A temporary directory that the tests can use.")

  # Notes:
  # - utf-8 is the Ubuntu default
  # - this flag has limited usefulness.  It may be better to simply export LANG=
  #   in this test case itself.
  p.add_option(
      '--lang-env', dest='lang_env', default='en_US.UTF-8',
      help="The LANG= setting, which affects various libc functions.")
  p.add_option(
      '--env-pair', dest='env_pair', default=[], action='append',
      help='A key=value pair to add to the environment')

  p.add_option(
      '--timeout', dest='timeout', default='',
      help="Prefix shell invocation with 'timeout N'")
  p.add_option(
      '--timeout-bin', dest='timeout_bin', default=None,
      help="Use the smoosh timeout binary at this location.")

  p.add_option(
      '--posix', dest='posix', default=False, action='store_true',
      help='Pass -o posix to the shell (when applicable)')

  p.add_option(
      '--sh-env-var-name', dest='sh_env_var_name', default='SH',
      help="Set this environment variable to the path of the shell")
  p.add_option(
      '--rm-tmp', dest='rm_tmp', default=False, action='store_true',
      help='clear the tmp dir after running each test case')

  p.add_option(
      '--pyann-out-dir', dest='pyann_out_dir', default=None,
      help='Run OSH with PYANN_OUT=$dir/$case_num.json')
