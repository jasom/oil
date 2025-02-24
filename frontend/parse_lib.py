"""
parse_lib.py - Consolidate various parser instantiations here.
"""

from _devbuild.gen.id_kind_asdl import Id_t
from _devbuild.gen.syntax_asdl import (
    Token, compound_word, expr_t, word_t, redir, ArgList, name_type,
)
from _devbuild.gen.types_asdl import lex_mode_e
from _gen.oil_lang import grammar_nt

from core.pyerror import p_die
from core import state
from frontend import lexer
from frontend import reader
from frontend import match

from oil_lang import expr_parse
from oil_lang import expr_to_ast
from osh import tdop
from osh import arith_parse
from osh import cmd_parse
from osh import word_parse
from mycpp import mylib

from typing import Any, List, Tuple, Dict, Optional, IO, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import (
      command__VarDecl, command__PlaceMutation, command__Proc, command__Func,
      command__Data, command__Enum, command__Class, command__Import
  )
  from core.alloc import Arena
  from core.util import DebugFile
  from core import optview
  from frontend.lexer import Lexer
  from frontend.reader import _Reader
  from osh.tdop import TdopParser
  from osh.word_parse import WordParser
  from osh.cmd_parse import CommandParser
  from pgen2.grammar import Grammar
  from pgen2.pnode import PNode

class _BaseTrail(object):
  """Base class has members, but no-ops for methods."""

  def __init__(self):
    # type: () -> None
    # word from a partially completed command.
    # Filled in by _ScanSimpleCommand in osh/cmd_parse.py.
    self.words = []  # type: List[compound_word]
    self.redirects = []  # type: List[redir]
    # TODO: We should maintain the LST invariant and have a single list, but
    # that I ran into the "cases classes are better than variants" problem.

    # Non-ignored tokens, after PushHint translation.  Used for variable name
    # completion.  Filled in by _Peek() in osh/word_parse.py.
    #
    # Example:
    # $ echo $\
    # f<TAB>   
    # This could complete $foo.
    # Problem: readline doesn't even allow that, because it spans more than one
    # line!
    self.tokens = []  # type: List[Token]

    self.alias_words = []  # type: List[compound_word]  # words INSIDE an alias expansion
    self._expanding_alias = False

  def Clear(self):
    # type: () -> None
    pass

  def SetLatestWords(self, words, redirects):
    # type: (List[compound_word], List[redir]) -> None
    pass

  def AppendToken(self, token):
    # type: (Token) -> None
    pass

  def BeginAliasExpansion(self):
    # type: () -> None
    pass

  def EndAliasExpansion(self):
    # type: () -> None
    pass

  if mylib.PYTHON:
    def PrintDebugString(self, debug_f):
      # type: (DebugFile) -> None

      # note: could cast DebugFile to IO[str] instead of ignoring?
      debug_f.log('  words:')
      for w in self.words:
        w.PrettyPrint(f=debug_f)  # type: ignore
      debug_f.log('')

      debug_f.log('  redirects:')
      for r in self.redirects:
        r.PrettyPrint(f=debug_f)  # type: ignore
      debug_f.log('')

      debug_f.log('  tokens:')
      for p in self.tokens:
        p.PrettyPrint(f=debug_f)  # type: ignore
      debug_f.log('')

      debug_f.log('  alias_words:')
      for w in self.alias_words:
        w.PrettyPrint(f=debug_f)  # type: ignore
      debug_f.log('')

  def __repr__(self):
    # type: () -> str
    return '<Trail %s %s %s %s>' % (
        self.words, self.redirects, self.tokens, self.alias_words)


class ctx_Alias(object):
  """Used by CommandParser so we know to be ready for FIRST alias word.

  For example, for

  alias ll='ls -l'

  Then we want to capture 'ls' as the first word.

  We do NOT want SetLatestWords or AppendToken to be active, because we don't
  need other tokens from 'ls -l'.
  
  It would also probably cause bugs in history expansion, e.g. echo !1 should
  be the first word the user typed, not the first word after alias expansion.
  """

  def __init__(self, trail):
    # type: (_BaseTrail) -> None
    trail._expanding_alias = True
    self.trail = trail

  def __enter__(self):
    # type: () -> None
    pass

  def __exit__(self, type, value, traceback):
    # type: (Any, Any, Any) -> None
    self.trail._expanding_alias = False


class Trail(_BaseTrail):
  """Info left by the parser to help us complete shell syntax and commands.

  It's also used for history expansion.
  """
  def __init__(self):
    # type: () -> None
    """Empty constructor for mycpp."""
    _BaseTrail.__init__(self)

  def Clear(self):
    # type: () -> None
    del self.words[:]
    del self.redirects[:]
    # The other ones don't need to be reset?
    del self.tokens[:]
    del self.alias_words[:]

  def SetLatestWords(self, words, redirects):
    # type: (List[compound_word], List[redir]) -> None
    if self._expanding_alias:
      self.alias_words = words  # Save these separately
      return
    self.words = words
    self.redirects = redirects

  def AppendToken(self, token):
    # type: (Token) -> None
    if self._expanding_alias:  # We don't want tokens inside aliases
      return
    self.tokens.append(token)


if TYPE_CHECKING:
  AliasesInFlight = List[Tuple[str, int]]


if mylib.PYTHON:
  def MakeGrammarNames(oil_grammar):
    # type: (Grammar) -> Dict[int, str]

    # TODO: Break this dependency
    from frontend import lexer_def

    names = {}

    #from _devbuild.gen.id_kind_asdl import _Id_str
    # This is a dictionary

    # _Id_str()

    for id_name, k in lexer_def.ID_SPEC.id_str2int.items():
      # Hm some are out of range
      #assert k < 256, (k, id_name)

      # HACK: Cut it off at 256 now!  Expr/Arith/Op doesn't go higher than
      # that.  TODO: Change NT_OFFSET?  That might affect C code though.
      # Best to keep everything fed to pgen under 256.  This only affects
      # pretty printing.
      if k < 256:
        names[k] = id_name

    for k, v in oil_grammar.number2symbol.items():
      # eval_input == 256.  Remove?
      assert k >= 256, (k, v)
      names[k] = v

    return names


class ParseContext(object):
  """Context shared between the mutually recursive Command and Word parsers.

  In constrast, STATE is stored in the CommandParser and WordParser instances.
  """

  def __init__(self, arena, parse_opts, aliases, oil_grammar):
    # type: (Arena, optview.Parse, Dict[str, str], Grammar) -> None
    self.arena = arena
    self.parse_opts = parse_opts
    self.aliases = aliases
    self.oil_grammar = oil_grammar

    # NOTE: The transformer is really a pure function.
    if oil_grammar:
      self.tr = expr_to_ast.Transformer(oil_grammar)
      if mylib.PYTHON:
        names = MakeGrammarNames(oil_grammar)
    else:  # hack for unit tests, which pass None
      self.tr = None
      if mylib.PYTHON:  # TODO: Simplify
        names = {}

    if mylib.PYTHON:
      self.p_printer = expr_parse.ParseTreePrinter(names)  # print raw nodes

    # Completion state lives here since it may span multiple parsers.
    self.trail = _BaseTrail()  # no-op by default
    self.one_pass_parse = False

  def Init_Trail(self, trail):
    # type: (_BaseTrail) -> None
    self.trail = trail

  def Init_OnePassParse(self, b):
    # type: (bool) -> None
    self.one_pass_parse = b

  def MakeLexer(self, line_reader):
    # type: (_Reader) -> Lexer
    """Helper function.

    NOTE: I tried to combine the LineLexer and Lexer, and it didn't perform
    better.
    """
    line_lexer = lexer.LineLexer('', self.arena)
    return lexer.Lexer(line_lexer, line_reader)

  def MakeOshParser(self, line_reader, emit_comp_dummy=False):
    # type: (_Reader, bool) -> CommandParser
    lx = self.MakeLexer(line_reader)
    if emit_comp_dummy:
      lx.EmitCompDummy()  # A special token before EOF!

    w_parser = word_parse.WordParser(self, lx, line_reader)
    c_parser = cmd_parse.CommandParser(self, self.parse_opts, w_parser, lx,
                                       line_reader)
    return c_parser

  def MakeConfigParser(self, line_reader):
    # type: (_Reader) -> CommandParser
    lx = self.MakeLexer(line_reader)
    parse_opts = state.MakeOilOpts()
    w_parser = word_parse.WordParser(self, lx, line_reader)
    c_parser = cmd_parse.CommandParser(self, parse_opts, w_parser, lx,
                                       line_reader)
    return c_parser

  def MakeWordParserForHereDoc(self, line_reader):
    # type: (_Reader) -> WordParser
    lx = self.MakeLexer(line_reader)
    return word_parse.WordParser(self, lx, line_reader)

  def MakeWordParser(self, lx, line_reader):
    # type: (Lexer, _Reader) -> WordParser
    return word_parse.WordParser(self, lx, line_reader)

  def MakeArithParser(self, code_str):
    # type: (str) -> TdopParser
    """Used for a[x+1]=foo in the CommandParser."""
    line_reader = reader.StringLineReader(code_str, self.arena)
    lx = self.MakeLexer(line_reader)
    w_parser = word_parse.WordParser(self, lx, line_reader)
    w_parser.Init(lex_mode_e.Arith)  # Special initialization
    a_parser = tdop.TdopParser(arith_parse.Spec(), w_parser, self.parse_opts)
    return a_parser

  def MakeParserForCommandSub(self, line_reader, lexer, eof_id):
    # type: (_Reader, Lexer, Id_t) -> CommandParser
    """To parse command sub, we want a fresh word parser state."""
    w_parser = word_parse.WordParser(self, lexer, line_reader)
    c_parser = cmd_parse.CommandParser(self, self.parse_opts, w_parser, lexer,
                                       line_reader)
    c_parser.Init_EofId(eof_id)
    return c_parser

  def MakeWordParserForPlugin(self, code_str):
    # type: (str) -> WordParser
    """For $PS1, $PS4, etc."""
    line_reader = reader.StringLineReader(code_str, self.arena)
    lx = self.MakeLexer(line_reader)
    return word_parse.WordParser(self, lx, line_reader)

  def _ParseOil(self, lexer, start_symbol):
    # type: (Lexer, int) -> Tuple[PNode, Token]
    """Helper for Oil expression parsing."""

    # TODO: maybe pool these ExprParser instances to reduce allocations?
    e_parser = expr_parse.ExprParser(self, self.oil_grammar, False)
    return e_parser.Parse(lexer, start_symbol)

  def _ParseTea(self, lexer, start_symbol):
    # type: (Lexer, int) -> Tuple[PNode, Token]
    """Helper for Tea parsing."""

    e_parser = expr_parse.ExprParser(self, self.oil_grammar, True)
    return e_parser.Parse(lexer, start_symbol)

  def ParseVarDecl(self, kw_token, lexer):
    # type: (Token, Lexer) -> Tuple[command__VarDecl, Token]
    """ var mylist = [1, 2, 3] """
    pnode, last_token = self._ParseOil(lexer, grammar_nt.oil_var_decl)

    if 0:
      self.p_printer.Print(pnode)

    ast_node = self.tr.MakeVarDecl(pnode)
    ast_node.keyword = kw_token  # VarDecl didn't fill this in
    return ast_node, last_token

  def ParsePlaceMutation(self, kw_token, lexer):
    # type: (Token, Lexer) -> Tuple[command__PlaceMutation, Token]
    """ setvar d['a'] += 1 """
    pnode, last_token = self._ParseOil(lexer, grammar_nt.oil_place_mutation)
    if 0:
      self.p_printer.Print(pnode)
    ast_node = self.tr.MakePlaceMutation(pnode)
    ast_node.keyword = kw_token  # VarDecl didn't fill this in
    return ast_node, last_token

  def ParseOilArgList(self, lexer, out):
    # type: (Lexer, ArgList) -> Token
    """ $f(x, y) """
    pnode, last_token = self._ParseOil(lexer, grammar_nt.oil_arglist)

    if 0:
      self.p_printer.Print(pnode)

    self.tr.ToArgList(pnode, out)
    return last_token

  def ParseOilExpr(self, lexer, start_symbol):
    # type: (Lexer, int) -> Tuple[expr_t, Token]
    """ if (x > 0) { ... }, while, etc. """
    pnode, last_token = self._ParseOil(lexer, start_symbol)

    if 0:
      self.p_printer.Print(pnode)

    ast_node = self.tr.Expr(pnode)
    return ast_node, last_token

  def ParseOilForExpr(self, lexer, start_symbol):
    # type: (Lexer, int) -> Tuple[List[name_type], expr_t, Token]
    """ for (x Int, y Int in foo) """
    pnode, last_token = self._ParseOil(lexer, start_symbol)

    if 0:
      self.p_printer.Print(pnode)

    lvalue, iterable = self.tr.OilForExpr(pnode)
    return lvalue, iterable, last_token

  def ParseProc(self, lexer, out):
    # type: (Lexer, command__Proc) -> Token
    """ proc f(x, y, @args) { """
    pnode, last_token = self._ParseOil(lexer, grammar_nt.oil_proc)

    if 0:
      self.p_printer.Print(pnode)

    out.sig = self.tr.Proc(pnode)
    return last_token

  def ParseFunc(self, lexer, out):
    # type: (Lexer, command__Func) -> Token
    """ func f(x Int, y Int = 0, ...args; z Int = 3, ...named) { x = 42 } """
    pnode, last_token = self._ParseTea(lexer, grammar_nt.named_func)

    if 0:
      self.p_printer.Print(pnode)

    self.tr.NamedFunc(pnode, out)
    return last_token

  def ParseDataType(self, lexer, out):
    # type: (Lexer, command__Data) -> Token
    """ data Point(x Int, y Int) """
    pnode, last_token = self._ParseTea(lexer, grammar_nt.tea_data)

    if 0:
      self.p_printer.Print(pnode)

    self.tr.Data(pnode, out)
    return last_token

  def ParseEnum(self, lexer, out):
    # type: (Lexer, command__Enum) -> Token
    """ enum cflow { Break, Continue, Return(status Int) } """
    pnode, last_token = self._ParseTea(lexer, grammar_nt.tea_enum)

    if 0:
      self.p_printer.Print(pnode)

    self.tr.Enum(pnode, out)
    return last_token

  def ParseClass(self, lexer, out):
    # type: (Lexer, command__Class) -> Token
    """ class Lexer { var Token; func Next() { echo } } """
    pnode, last_token = self._ParseTea(lexer, grammar_nt.tea_class)

    if 0:
      self.p_printer.Print(pnode)

    self.tr.Class(pnode, out)
    return last_token

  def ParseImport(self, lexer, out):
    # type: (Lexer, command__Import) -> Token
    """ use 'foo/bar' as spam, Foo, Z as Y """
    pnode, last_token = self._ParseTea(lexer, grammar_nt.tea_import)

    if 0:
      self.p_printer.Print(pnode)

    self.tr.Import(pnode, out)
    return last_token

  if mylib.PYTHON:
    def ParseTeaModule(self, line_reader):
      # type: (_Reader) -> None
      """ An entire .tea file """
      line_lexer = lexer.LineLexer('', self.arena)
      lx = lexer.Lexer(line_lexer, line_reader)

      pnode, last_token = self._ParseTea(lx, grammar_nt.tea_module)

      if 1:
        self.p_printer.Print(pnode)

      #out = command.Use()  # TODO: make a node
      #self.tr.TeaModule(pnode, out)
      return None

# Another parser instantiation:
# - For Array Literal in word_parse.py WordParser:
#   w_parser = WordParser(self.lexer, self.line_reader)
