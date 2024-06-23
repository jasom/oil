#!/usr/bin/env python2
"""
func_misc.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import (scope_e)
from _devbuild.gen.value_asdl import (value, value_e, value_t, value_str)

from core import error
from core import num
from core import state
from core import ui
from core import vm
from data_lang import j8
from frontend import match
from frontend import typed_args
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import NewDict, iteritems, log, tagswitch
from ysh import expr_eval
from ysh import val_ops

from typing import TYPE_CHECKING, Dict, List, cast
if TYPE_CHECKING:
    from osh import glob_
    from osh import split

_ = log


class Len(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        x = rd.PosValue()
        rd.Done()

        UP_x = x
        with tagswitch(x) as case:
            if case(value_e.List):
                x = cast(value.List, UP_x)
                return num.ToBig(len(x.items))

            elif case(value_e.Dict):
                x = cast(value.Dict, UP_x)
                return num.ToBig(len(x.d))

            elif case(value_e.Str):
                x = cast(value.Str, UP_x)
                return num.ToBig(len(x.s))

        raise error.TypeErr(x, 'len() expected Str, List, or Dict',
                            rd.BlamePos())


class Join(vm._Callable):
    """Both free function join() and List->join() method."""

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        li = rd.PosList()
        delim = rd.OptionalStr(default_='')
        rd.Done()

        strs = []  # type: List[str]
        for i, el in enumerate(li):
            strs.append(val_ops.Stringify(el, rd.LeftParenToken()))

        return value.Str(delim.join(strs))


class Maybe(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        if val == value.Null:
            return value.List([])

        s = val_ops.ToStr(
            val, 'maybe() expected Str, but got %s' % value_str(val.tag()),
            rd.LeftParenToken())
        if len(s):
            return value.List([val])  # use val to avoid needlessly copy

        return value.List([])


class Type(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        return value.Str(ui.ValType(val))


class Bool(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        return value.Bool(val_ops.ToBool(val))


class Int(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                return val

            elif case(value_e.Bool):
                val = cast(value.Bool, UP_val)
                return value.Int(mops.FromBool(val.b))

            elif case(value_e.Float):
                val = cast(value.Float, UP_val)
                return value.Int(mops.FromFloat(val.f))

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)
                if not match.LooksLikeInteger(val.s):
                    raise error.Expr('Cannot convert %s to Int' % val.s,
                                     rd.BlamePos())

                return value.Int(mops.FromStr(val.s))

        raise error.TypeErr(val, 'int() expected Bool, Int, Float, or Str',
                            rd.BlamePos())


class Float(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                val = cast(value.Int, UP_val)
                return value.Float(mops.ToFloat(val.i))

            elif case(value_e.Float):
                return val

            elif case(value_e.Str):
                val = cast(value.Str, UP_val)
                if not match.LooksLikeFloat(val.s):
                    raise error.Expr('Cannot convert %s to Float' % val.s,
                                     rd.BlamePos())

                return value.Float(float(val.s))

        raise error.TypeErr(val, 'float() expected Int, Float, or Str',
                            rd.BlamePos())


class Str_(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        # TODO: Should we call Stringify here?  That would handle Eggex.

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Int):
                val = cast(value.Int, UP_val)
                return value.Str(mops.ToStr(val.i))

            elif case(value_e.Float):
                val = cast(value.Float, UP_val)
                return value.Str(str(val.f))

            elif case(value_e.Str):
                return val

        raise error.TypeErr(val, 'str() expected Str, Int, or Float',
                            rd.BlamePos())


class List_(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        l = []  # type: List[value_t]
        it = None  # type: val_ops._ContainerIter
        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.List):
                val = cast(value.List, UP_val)
                it = val_ops.ListIterator(val)

            elif case(value_e.Dict):
                val = cast(value.Dict, UP_val)
                it = val_ops.DictIterator(val)

            elif case(value_e.Range):
                val = cast(value.Range, UP_val)
                it = val_ops.RangeIterator(val)

            else:
                raise error.TypeErr(val,
                                    'list() expected Dict, List, or Range',
                                    rd.BlamePos())

        assert it is not None
        while not it.Done():
            l.append(it.FirstValue())
            it.Next()

        return value.List(l)


class Dict_(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        rd.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Dict):
                d = NewDict()  # type: Dict[str, value_t]
                val = cast(value.Dict, UP_val)
                for k, v in iteritems(val.d):
                    d[k] = v

                return value.Dict(d)

            elif case(value_e.BashAssoc):
                d = NewDict()
                val = cast(value.BashAssoc, UP_val)
                for k, s in iteritems(val.d):
                    d[k] = value.Str(s)

                return value.Dict(d)

        raise error.TypeErr(val, 'dict() expected Dict or BashAssoc',
                            rd.BlamePos())


class Split(vm._Callable):

    def __init__(self, splitter):
        # type: (split.SplitContext) -> None
        vm._Callable.__init__(self)
        self.splitter = splitter

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        s = rd.PosStr()

        ifs = rd.OptionalStr()

        rd.Done()

        l = [
            value.Str(elem)
            for elem in self.splitter.SplitForWordEval(s, ifs=ifs)
        ]  # type: List[value_t]
        return value.List(l)


class Glob(vm._Callable):

    def __init__(self, globber):
        # type: (glob_.Globber) -> None
        vm._Callable.__init__(self)
        self.globber = globber

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        s = rd.PosStr()
        rd.Done()

        out = []  # type: List[str]
        self.globber._Glob(s, out)

        l = [value.Str(elem) for elem in out]  # type: List[value_t]
        return value.List(l)


class Shvar_get(vm._Callable):
    """Look up with dynamic scope."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        name = rd.PosStr()
        rd.Done()
        return state.DynamicGetVar(self.mem, name, scope_e.Dynamic)


class GetVar(vm._Callable):
    """Look up normal scoping rules."""

    def __init__(self, mem):
        # type: (state.Mem) -> None
        vm._Callable.__init__(self)
        self.mem = mem

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        name = rd.PosStr()
        rd.Done()
        return state.DynamicGetVar(self.mem, name, scope_e.LocalOrGlobal)


class Assert(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()

        msg = rd.OptionalStr(default_='')

        rd.Done()

        if not val_ops.ToBool(val):
            raise error.AssertionErr(msg, rd.LeftParenToken())

        return value.Null


class EvalExpr(vm._Callable):

    def __init__(self, expr_ev):
        # type: (expr_eval.ExprEvaluator) -> None
        self.expr_ev = expr_ev

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        lazy = rd.PosExpr()
        rd.Done()

        result = self.expr_ev.EvalExpr(lazy, rd.LeftParenToken())

        return result


class ToJson8(vm._Callable):

    def __init__(self, is_j8):
        # type: (bool) -> None
        self.is_j8 = is_j8

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        val = rd.PosValue()
        space = mops.BigTruncate(rd.NamedInt('space', 0))
        rd.Done()

        # Convert from external JS-like API to internal API.
        if space <= 0:
            indent = -1
        else:
            indent = space

        buf = mylib.BufWriter()
        try:
            if self.is_j8:
                j8.PrintMessage(val, buf, indent)
            else:
                j8.PrintJsonMessage(val, buf, indent)
        except error.Encode as e:
            # status code 4 is special, for encode/decode errors.
            raise error.Structured(4, e.Message(), rd.LeftParenToken())

        return value.Str(buf.getvalue())


class FromJson8(vm._Callable):

    def __init__(self, is_j8):
        # type: (bool) -> None
        self.is_j8 = is_j8

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        s = rd.PosStr()
        rd.Done()

        p = j8.Parser(s, self.is_j8)
        try:
            val = p.ParseValue()
        except error.Decode as e:
            # Right now I'm not exposing the original string, because that
            # could lead to a memory leak in the _error Dict.
            # The message quotes part of the string, and we could improve
            # that.  We could have a substring with context.
            props = {
                'start_pos': num.ToBig(e.start_pos),
                'end_pos': num.ToBig(e.end_pos),
            }  # type: Dict[str, value_t]
            # status code 4 is special, for encode/decode errors.
            raise error.Structured(4, e.Message(), rd.LeftParenToken(), props)

        return val


class BashArrayToSparse(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        strs = rd.PosBashArray()
        rd.Done()

        # List[str] with holes -> Dict[int, str]
        result = value.SparseArray({})
        for i, item in enumerate(strs):
            if item is not None:
                result.d[mops.IntWiden(i)] = item

        return result


class DictToSparse(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        strs = rd.PosBashArray()
        rd.Done()

        # List[str] with holes -> Dict[int, str]
        result = value.SparseArray({})
        for i, s in enumerate(strs):
            if s is not None:
                # result.d[i] = s
                mylib.BashArraySet(result.d, mops.IntWiden(i), s)

        return result


class SparseOp(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        d = rd.PosSparseArray()
        #i = mops.BigTruncate(rd.PosInt())
        op_name = rd.PosStr()

        if op_name == 'len':  # ${#a[@]}
            rd.Done()
            return num.ToBig(len(d))

        elif op_name == 'get':  # ${a[42]}
            index = rd.PosInt()
            rd.Done()

            s = mylib.BashArrayGet(d, index)
            if s is None:
                return value.Null
            else:
                return value.Str(s)

        elif op_name == 'set':  # a[42]=foo
            index = rd.PosInt()
            s = rd.PosStr()
            rd.Done()

            #d[index] = s
            mylib.BashArraySet(d, index, s)
            return value.Int(mops.ZERO)

        elif op_name == 'subst':  # "${a[@]}"
            keys = d.keys()
            mylib.BigIntSort(keys)
            items = []  # type: List[str]
            for i in keys:
                s = mylib.BashArrayGet(d, i)
                assert s is not None
                items.append(s)
            return value.BashArray(items)

        elif op_name == 'slice':  # "${a[@]:0:5}"
            start = rd.PosInt()
            end = rd.PosInt()
            rd.Done()

            #log('start %d - end %d', start.i, end.i)

            items2 = []  # type: List[str]
            i = start
            while mops.Greater(end, i):  # i < end
                s = mylib.BashArrayGet(d, i)
                #log('s %s', s)
                if s is not None:
                    items2.append(s)

                i = mops.Add(i, mops.ONE)  # i += 1

            return value.BashArray(items2)

        else:
            print('Invalid SparseArray operation %r' % op_name)
            return value.Int(mops.ZERO)
