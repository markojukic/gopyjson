import shutil
from copy import copy as shallow_copy

from go import *


def AddGeneratedType(go_type: 'GoType') -> bool:
    for t in Gopyjson.current.types:
        if go_type.type_eq(t):
            return False
    Gopyjson.current.types.append(go_type)
    return True


func_counter = 0


def AddGeneratedFunc(go_type: 'GoType') -> tuple[bool, int]:
    for i, t in enumerate(Gopyjson.current.funcs):
        if go_type.func_eq(t):
            return False, i
    Gopyjson.current.funcs.append(go_type)
    return True, len(Gopyjson.current.funcs) - 1


def dereference(pointer: str):
    return pointer[1:] if pointer[0] == '&' else '*' + pointer


def field_pointer(struct_pointer: str, field: str):
    if struct_pointer[0] == '&':
        struct_pointer = struct_pointer[1:]
    return '&' + struct_pointer + '.' + field


def index(pointer: str, i: str):
    if pointer[0] == '&':
        return f'{pointer[1:]}[{i}]'
    else:
        return f'(*{pointer})[{i}]'


class GoType:
    def __init__(self, typename: str = '', omit_empty: bool = True, name: str = None):
        self.name = name
        self.omit_empty = omit_empty
        self.typename = typename

    def trim(self, pvar: str):
        new, f = AddGeneratedFunc(self)
        assert not new
        wl(f'pTrim__{f}(b, N, {pvar})')

    def trim_using(self, pvar, func: str):
        if self.typename:
            wl(f'{dereference(pvar)} = {self.typename}({func}(b, N))')
        else:
            wl(f'{dereference(pvar)} = {func}(b, N)')

    def zero(self, pvar: str):
        raise NotImplementedError()

    def long_typename(self):
        raise NotImplementedError()

    def print_type(self):
        if self.typename:
            w(self.typename)
        else:
            self.long_typename()

    # Returns if the go types are equal
    def type_eq(self, other) -> bool:
        return type(self) == type(other) and self.typename == other.typename

    # Returns if the go types are equal and if their parser functions do the same thing
    def func_eq(self, other) -> bool:
        return self.type_eq(other)

    def generate_type(self):
        if self.typename and AddGeneratedType(self):
            wl(f'type {self.typename} ')
            self.long_typename()

    # Returns if this parser or any child parser was generated
    def generate_func(self):
        pass

    def generate(self, func_name: str = 'Unmarshal'):
        assert self.typename
        self.generate_type()
        self.generate_func()
        if f'{self.typename}.{func_name}' in Gopyjson.current.unmarshalers:
            raise Exception(f'{self.typename}.{func_name} already defined')
        else:
            Gopyjson.current.unmarshalers.add(f'{self.typename}.{func_name}')
            with Func(f'(v *{self.typename}) {func_name}(data []byte) (err error)'):
                self.zero('v')
                wl('defer RecoverLater(&err)')
                wl('var n int')
                wl('N := &n')
                wl('b := &data')
                wl('trimLeftSpace(b, N)')
                self.trim('v')
                wl('return nil')

    def update(self, **kwargs) -> 'GoType':
        t = shallow_copy(self)
        for k, v in kwargs.items():
            if hasattr(t, k):
                setattr(t, k, v)
        return t


class Bool(GoType):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimBool')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = false')

    def long_typename(self):
        w('bool')


class Int64(GoType):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimInt64')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = 0')

    def long_typename(self):
        w('int64')


class Float32(GoType):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimFloat32')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = 0')

    def long_typename(self):
        w('float32')


class Float64(GoType):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimFloat64')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = 0')

    def long_typename(self):
        w('float64')


class QuotedFloat64(GoType):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimQuotedFloat64')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = 0')

    def long_typename(self):
        w('float64')


class Float64WithSrc(GoType):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimFloat64WithSrc')

    def zero(self, pvar: str):
        wl(f'{pvar.lstrip("&")}.Value = 0')
        wl(f'{pvar.lstrip("&")}.Src = {pvar.lstrip("&")}.Src[:0]')

    def long_typename(self):
        w('Float64WithSrc')


class String(GoType):
    def __init__(self, copy: bool = True, validate_utf8: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.copy = copy
        self.validate_utf8 = validate_utf8

    def trim(self, pvar: str):
        if self.typename:
            if self.copy:
                wl(f'{dereference(pvar)} = {self.typename}(pTrimStringBytes(b, N))')
            else:
                wl(f'{dereference(pvar)} = {self.typename}(bytesToString(pTrimStringBytes(b, N)))')
            if self.validate_utf8:
                Import('unicode/utf8')
                with If(f'!utf8.ValidString(string({dereference(pvar)}))'):
                    wl('panic(ParseError{*b, *N, errUTF8})')
        else:
            if self.copy:
                wl(f'{dereference(pvar)} = string(pTrimStringBytes(b, N))')
            else:
                wl(f'{dereference(pvar)} = bytesToString(pTrimStringBytes(b, N))')
            if self.validate_utf8:
                Import('unicode/utf8')
                with If(f'!utf8.ValidString({dereference(pvar)})'):
                    wl('panic(ParseError{*b, *N, errUTF8})')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = ""')

    def type_eq(self, other) -> bool:
        return isinstance(other, String) and self.typename == other.typename

    def func_eq(self, other) -> bool:
        return self.type_eq(other) and other.copy == self.copy and other.validate_utf8 == self.validate_utf8

    def long_typename(self):
        w('string')


class UnsafeString(String):
    def __init__(self, **kwargs):
        super().__init__(copy=False, validate_utf8=False, **kwargs)


class Array(GoType):
    def __init__(self, size: int, element_type: GoType, **kwargs):
        assert size > 0
        super().__init__(**kwargs)
        self.size = size
        self.element_type = element_type

    def long_typename(self):
        w(f'[{self.size}]')
        self.element_type.print_type()

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = ')
        self.print_type()
        w('{}')

    def type_eq(self, other) -> bool:
        return super().type_eq(other) and self.size == other.size and self.element_type.type_eq(other.element_type)

    def generate_type(self):
        self.element_type.generate_type()
        super().generate_type()

    def generate_func(self):
        self.element_type.generate_func()
        new, f = AddGeneratedFunc(self)
        if new:
            wl(f'func pTrim__{f}(b *[]byte, N *int, v *')
            self.print_type()
            w(') ')
            with Block(new_line=False):
                wls('''
                pTrimByte(b, N, '[')
                trimLeftSpace(b, N)
                ''')
                self.element_type.trim('&(*v)[0]')
                for i in range(1, self.size):
                    wls('''
                    trimLeftSpace(b, N)
                    pTrimByte(b, N, ',')
                    trimLeftSpace(b, N)
                    ''')
                    self.element_type.trim(f'&(*v)[{i}]')
                wls('''
                trimLeftSpace(b, N)
                pTrimByte(b, N, ']')
                ''')



# class Tuple(GoType):
#     def __init__(self, fields: dict[str, GoType], **kwargs):
#         super().__init__(**kwargs)
#         self.fields: dict[str, GoType] = fields
#
#     def type_eq(self, other) -> bool:
#         return super().type_eq(other) and len(other.fields) == len(self.fields) and all(k1 == k2 and t1.type_eq(t2) for ((k1, t1), (k2, t2)) in zip(self.fields.items(), other.fields.items()))
#
#     def long_typename(self):
#         w(f'struct {{')
#         if self.fields:
#             with Indent():
#                 for k, v in self.fields.items():
#                     wl(f'{k} ')
#                     v.print_type()
#             wl('}')
#         else:
#             w('}')
#
#     def generate_type(self):
#         for t in self.fields.values():
#             t.generate_type()
#         super().generate_type()
#
#     def generate_func(self):
#         for t in self.fields.values():
#             t.generate_func()
#         new, f = AddGeneratedFunc(self)
#         if new:
#             wl(f'func pTrim__{f}(b *[]byte, N *int, v *')
#             self.print_type()
#             w(') ')
#             with Block(new_line=False):
#                 wls('''
#                 var nonEmpty bool
#                 pTrimByte(b, N, '{')
#                 trimLeftSpace(b, N)
#                 ''')
# class Tuple(GoType):
#     def __init__(self, fields: dict[str, GoType], **kwargs):
#         super().__init__(**kwargs)
#         self.fields = fields
#
#     def generate_type(self):
#         for element_type in self.elements.values():
#             element_type.generate_type()
#         if not self.deep['type_defined'] and self.typename:
#             self.deep['type_defined'] = True
#             AddType(self.typename)
#             wl(f'type {self.typename} struct {{')
#             if self.fields:
#                 with Indent():
#                     for k, v in self.fields.items():
#                         wl(f'{k}')
#                         wl(f'{k} {v.typename}')
#                 wl('}')
#             else:
#                 w('}')
#
#             wl(f'type {self.typename} [{self.size}]{self.element_type.typename}')
#         if not self.deep['fun_defined']:
#             self.deep['fun_defined'] = True
#             with Func(f'pTrim__{self.gen_name}(b *[]byte, N *int, v *{self.typename})'):
#                 wls('''
#                 pTrimByte(b, N, '[')
#                 trimLeftSpace(b, N)
#                 ''')
#                 self.element_type.trim('&(*v)[0]')
#                 for i in range(1, self.size):
#                     wls('''
#                     trimLeftSpace(b, N)
#                     pTrimByte(b, N, ',')
#                     trimLeftSpace(b, N)
#                     ''')
#                     self.element_type.trim(f'&(*v)[{i}]')
#                 wls('''
#                 trimLeftSpace(b, N)
#                 pTrimByte(b, N, ']')
#                 ''')
#
#     def generate_type(self):
#         (self, pvar: str):
#
#     wls('''
#         pTrimByte(b, N, '[')
#         trimLeftSpace(b, N)
#         ''')
#     for i, (k, t) in enumerate(self.elements.items()):
#         if i > 0:
#             t.trim(field_pointer(pvar, k))
#     for i in range(1, self.size):
#         wls('''
#             trimLeftSpace(b, N)
#             pTrimByte(b, N, ',')
#             trimLeftSpace(b, N)
#             ''')
#         self.element_type.trim('&' + index(pvar, str(i)))
#     wls('''
#         trimLeftSpace(b, N)
#         pTrimByte(b, N, ']')
#         ''')
#
#
# def zero(self, pvar: str):
#     wl(f'{dereference(pvar)} = {self.typename}{{}}')
#
#
# def _gen(self):
#     self.element_type._gen()


class Slice(GoType):
    def __init__(self, element_type: GoType, **kwargs):
        super().__init__(**kwargs)
        self.element_type = element_type

    def type_eq(self, other) -> bool:
        return super().type_eq(other) and self.element_type.type_eq(other.element_type)

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = {index(pvar, ":0")}')

    def long_typename(self):
        w(f'[]')
        self.element_type.print_type()

    def generate_type(self):
        self.element_type.generate_type()
        super().generate_type()

    def generate_func(self):
        self.element_type.generate_func()
        new, f = AddGeneratedFunc(self)
        if new:
            wl(f'func pTrim__{f}(b *[]byte, N *int, v *')
            self.print_type()
            w(') ')
            with Block(new_line=False):
                element_var = f'var__{AddGeneratedFunc(self.element_type)[1]}'
                wl(f'var {element_var} ')
                self.element_type.print_type()
                with WLS('''
                pTrimByte(b, N, '[')
                trimLeftSpace(b, N)
                if *N >= len(*b) {
                    panic(ParseError{*b, *N, "unexpected end of array"})
                }
                if (*b)[*N] == ']' {
                    *N++
                } else {
                    {{}}
                }
                '''):
                    self.element_type.trim('&' + element_var)
                    with WLS('''
                    *v = append(*v, {0})
                    for {
                        trimLeftSpace(b, N)
                        if *N >= len(*b) {
                            panic(ParseError{*b, *N, "unexpected end of array"})
                        }
                        if (*b)[*N] == ']' {
                            *N++
                            break
                        }
                        pTrimByte(b, N, ',')
                        trimLeftSpace(b, N)
                        {{}}
                        *v = append(*v, {0})
                    }
                    ''', element_var):
                        wl(f'var {element_var} ')
                        self.element_type.print_type()
                        self.element_type.trim('&' + element_var)


class Struct(GoType):
    def __init__(self, fields: dict[str, GoType], typename: str = '', other_keys: str = 'skip', **kwargs):
        assert other_keys == 'skip' or other_keys == 'panic'
        super().__init__(typename=typename, **kwargs)
        self.fields: dict[str, GoType] = fields
        self.names: dict[str, str] = {k: k if t.name is None else t.name for k, t in fields.items()}
        self.other_keys = other_keys

    def type_eq(self, other) -> bool:
        return super().type_eq(other) and len(other.fields) == len(self.fields) and all(
            k1 == k2 and t1.type_eq(t2) for ((k1, t1), (k2, t2)) in
            zip(self.fields.items(), other.fields.items()))

    def func_eq(self, other) -> bool:
        return self.type_eq(other) and all(k1 == k2 and t1.func_eq(t2) for ((k1, t1), (k2, t2)) in zip(self.fields.items(), other.fields.items())) and self.names == other.names

    def long_typename(self):
        w(f'struct {{')
        if self.fields:
            with Indent():
                for k, v in self.fields.items():
                    wl(f'{k} ')
                    v.print_type()
            wl('}')
        else:
            w('}')

    def generate_type(self):
        for t in self.fields.values():
            t.generate_type()
        super().generate_type()

    def generate_func(self):
        for t in self.fields.values():
            t.generate_func()
        new, f = AddGeneratedFunc(self)
        if new:
            wl(f'func pTrim__{f}(b *[]byte, N *int, v *')
            self.print_type()
            w(') ')
            with Block(new_line=False):
                wls('''
                var nonEmpty bool
                pTrimByte(b, N, '{')
                trimLeftSpace(b, N)
                ''')
                with For():
                    wls(r'''
                    c := pNextByte(b, N)
                    if c == '}' {
                        break
                    }
                    if nonEmpty && c == ',' {
                        trimLeftSpace(b, N)
                        c = pNextByte(b, N)
                    }
                    *N--
                    key := pTrimKeyColon(b, N)
                    nonEmpty = true
                    ''')
                    if all(len(k.encode('utf-8')) == 1 for k in self.names.values()) and len(
                            set(k.encode('utf-8')[0] for k in self.names.values())) == len(self.names):
                        self.key_switch_len1('v')
                    else:
                        self.key_switch('v')

    def key_switch(self, pvar: str):
        with Switch('key'):
            for k, t in self.fields.items():
                with Case(f'"{self.names[k]}"'):
                    t.trim(field_pointer(pvar, k))
                    wl('trimLeftSpace(b, N)')
            with Default():
                self.skip_or_panic()

    # Appears slower than full key switch
    def key_switch_by_first_byte(self, pvar: str):
        assert all(len(k.encode('utf-8')) >= 1 for k in self.names.values())
        assert len(set(k.encode('utf-8')[0] for k in self.names.values())) == len(self.names)
        with If('len(key) == 0'):
            self.skip_or_panic()
        with Switch('key[0]'):
            for k, t in self.fields.items():
                with Case(str(self.names[k].encode('utf-8')[0])):
                    with If('key != "' + self.names[k] + '"'):
                        self.skip_or_panic()
                    t.trim(field_pointer(pvar, k))
                    wl('trimLeftSpace(b, N)')
            with Default():
                self.skip_or_panic()

    def skip_or_panic(self):
        if self.other_keys == 'skip':
            wl('pTrimValue(b, N)')
        else:
            wl(r'panic(ParseError{*b, *N, errUnexpectedKey + key + "\""})')

    def key_switch_len1(self, pvar: str):
        assert all(len(k.encode('utf-8')) == 1 for k in self.names.values())
        assert len(set(k.encode('utf-8')[0] for k in self.names.values())) == len(self.names)
        with If('len(key) != 1'):
            self.skip_or_panic()
        with Switch('key[0]'):
            for k, t in self.fields.items():
                with Case(str(self.names[k].encode('utf-8')[0])):
                    t.trim(field_pointer(pvar, k))
                    wl('trimLeftSpace(b, N)')
            with Default():
                self.skip_or_panic()

    def zero(self, pvar: str):
        for k, t in self.fields.items():
            t.zero(field_pointer(pvar, k))


class Gopyjson:
    current: 'Gopyjson' = None

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.types: list[GoType] = []
        self.funcs: list[GoType] = []
        self.unmarshalers: set[str] = set()

    def __enter__(self):
        Gopyjson.current = self
        output_dir = Path(self.output_dir)
        if not output_dir.is_dir():
            raise Exception("Directory doesn't exist: " + str(output_dir))
        output_dir = output_dir.joinpath('gopyjson')
        # Create <output_dir>/gopyjson subdirectory if it doesn't already exist
        output_dir.mkdir(exist_ok=True)
        # Copy common code to <output_dir>/gopyjson/common.go
        shutil.copyfile('go/common.go', output_dir.joinpath('common.go'))
        self.package = Package('gopyjson')
        self.package.__enter__()
        self.go_file = GoFile(output_dir.joinpath('gopyjson.go'))
        self.go_file.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.go_file.__exit__(exc_type, exc_val, exc_tb)
        self.package.__exit__(exc_type, exc_val, exc_tb)
        Gopyjson.current = None
