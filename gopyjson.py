import shutil
from typing import Tuple as PyTuple

from go import *


# Converts an expression that evaluates to a pointer to an expression that evaluates to dereference of that pointer
def dereference(pointer: str):
    return pointer[1:] if pointer[0] == '&' else '*' + pointer


# Given a pointer to a struct and field name, returns a pointer to the field in the struct
def field_pointer(struct_pointer: str, field: str):
    if struct_pointer[0] == '&':
        struct_pointer = struct_pointer[1:]
    return '&' + struct_pointer + '.' + field


# Given an expression evaluating to a pointer to a container (array/slice/map),
# returns an expression evaluating to the i-th element of the container.
def index(container_pointer: str, i: str):
    if container_pointer[0] == '&':
        return f'{container_pointer[1:]}[{i}]'
    else:
        return f'(*{container_pointer})[{i}]'


class GoType:
    def __init__(self, typename: str = ''):
        self.typename = typename  # The Go typename for this type, can be empty

    # Generates code that parses this type from b starting at index N, saves result to object located at pvar
    def trim(self, pvar: str):
        # Check if the parser was defined first
        new, f = Gopyjson.RegisterParser(self)
        assert not new
        wl(f'pTrim__{f}(b, N, {pvar})')

    # Generates code that parses this type from b starting at index N using a given function, saves result to pvar.
    # This is used by simple types like integers or floats in combination with predefined parsers from common.go.
    def trim_using(self, pvar, func: str):
        if self.typename:
            wl(f'{dereference(pvar)} = {self.typename}({func}(b, N))')
        else:
            wl(f'{dereference(pvar)} = {func}(b, N)')

    # Sets the value of pvar to zero.
    def zero(self, pvar: str):
        raise NotImplementedError()

    # Generates "long" type
    def long_typename(self):
        raise NotImplementedError()

    # Used for variable declarations
    def print_type(self):
        if self.typename:
            w(self.typename)
        else:
            self.long_typename()

    # Returns if the go types are equal
    def type_eq(self, other) -> bool:
        return type(self) == type(other) and self.typename == other.typename

    # Returns if the go types are equal and if their parser functions do the same thing
    # For example, strings can be parsed with/without UTF8 validation, with/without copying, with/without unquoting
    def parser_eq(self, other) -> bool:
        return self.type_eq(other)

    # Generates the type if the same type has not already been generated
    def generate_type(self):
        if self.typename and Gopyjson.RegisterType(self):
            wl(f'type {self.typename} ')
            self.long_typename()

    # Generates the parser if an equivalent parser has not already been generated
    def generate_parser(self):
        Gopyjson.RegisterParser(self)

    # Generates the Unmarshal method for this type
    def generate(self, func_name: str = 'Unmarshal'):
        assert self.typename
        self.generate_type()
        self.generate_parser()
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

    # Returns (self, json_field), used with Struct() when Go struct fields and json fields don't have same names
    def __floordiv__(self, json_field: str) -> PyTuple['GoType', str]:
        return self, json_field


# Used for parsing a boolean
class Bool(GoType):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimBool')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = false')

    def long_typename(self):
        w('bool')


# Used for parsing an int64
class Int64(GoType):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimInt64')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = 0')

    def long_typename(self):
        w('int64')


# Used for parsing an uint64
class UInt64(GoType):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimUint64')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = 0')

    def long_typename(self):
        w('uint64')


# Used for parsing a float32
class Float32(GoType):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimFloat32')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = 0')

    def long_typename(self):
        w('float32')


# Used for parsing a float64
class Float64(GoType):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimFloat64')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = 0')

    def long_typename(self):
        w('float64')


# Used for parsing a string
class String(GoType):
    # Arguments
    # copy: whether the result should be a copy or just a reference to a part of the buffer we are parsing from
    # validate_utf8: turn on/off UTF8 validation for this string
    # unquote: turn on/off unquoting for this string
    def __init__(self, copy: bool = True, validate_utf8: bool = True, unquote: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.copy = copy
        self.validate_utf8 = validate_utf8
        self.unquote = unquote

    def trim(self, pvar: str):
        if self.typename:
            if self.unquote:
                with BraceBlock():
                    wls('''
                    s := pTrimStringBytes(b, N)
                    s, ok := unquoteBytes((*b)[*N - len(s) - 2:*N])
                    if !ok {
                        panic(ParseError{*b, *N, errUnquote})
                    }
                    ''')
                    wl(f'{dereference(pvar)} = {self.typename}(s)')
            else:
                if self.copy:
                    wl(f'{dereference(pvar)} = {self.typename}(pTrimStringBytes(b, N))')
                else:
                    wl(f'{dereference(pvar)} = {self.typename}(bytesToString(pTrimStringBytes(b, N)))')
                if self.validate_utf8 and not self.unquote:
                    Import('unicode/utf8')
                    with If(f'!utf8.ValidString(string({dereference(pvar)}))'):
                        wl('panic(ParseError{*b, *N, errUTF8})')
        else:
            if self.unquote:
                with BraceBlock():
                    wls('''
                    s := pTrimStringBytes(b, N)
                    s, ok := unquoteBytes((*b)[*N - len(s) - 2:*N])
                    if !ok {
                        panic(ParseError{*b, *N, errUnquote})
                    }
                    ''')
                    wl(f'{dereference(pvar)} = string(s)')
            else:
                if self.copy:
                    wl(f'{dereference(pvar)} = string(pTrimStringBytes(b, N))')
                else:
                    wl(f'{dereference(pvar)} = bytesToString(pTrimStringBytes(b, N))')
                if self.validate_utf8 and not self.unquote:
                    Import('unicode/utf8')
                    with If(f'!utf8.ValidString({dereference(pvar)})'):
                        wl('panic(ParseError{*b, *N, errUTF8})')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = ""')

    def type_eq(self, other) -> bool:
        return isinstance(other, String) and self.typename == other.typename

    def parser_eq(self, other) -> bool:
        return self.type_eq(other) and other.copy == self.copy and other.validate_utf8 == self.validate_utf8

    def long_typename(self):
        w('string')


# Turns off all safety features. Parsing is faster as a result.
class UnsafeString(String):
    def __init__(self, **kwargs):
        super().__init__(copy=False, validate_utf8=False, unquote=False, **kwargs)


# Used for parsing arrays of known length and element type into a Go array.
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

    def generate_parser(self):
        self.element_type.generate_parser()
        new, f = Gopyjson.RegisterParser(self)
        if new:
            wl(f'func pTrim__{f}(b *[]byte, N *int, v *')
            self.print_type()
            w(') ')
            with BraceBlock():
                wls('''
                pTrimByte(b, N, '[')
                trimLeftSpace(b, N)
                ''')
                for i in range(self.size):
                    if i > 0:
                        wls('''
                        pTrimByte(b, N, ',')
                        trimLeftSpace(b, N)
                        ''')
                    self.element_type.trim('&' + index('v', str(i)))
                    wl('trimLeftSpace(b, N)')
                wl("pTrimByte(b, N, ']')")


# Used for parsing arrays of known length and variable element types into a Go struct
class Tuple(GoType):
    def __init__(self, fields: dict[str, GoType], typename: str = ''):
        super().__init__(typename=typename)
        self.fields: dict[str, GoType] = fields

    def type_eq(self, other) -> bool:
        return super().type_eq(other) and len(other.fields) == len(self.fields) and all(
            k1 == k2 and t1.type_eq(t2) for ((k1, t1), (k2, t2)) in zip(self.fields.items(), other.fields.items()))

    def parser_eq(self, other) -> bool:
        return self.type_eq(other) and all(
            k1 == k2 and t1.parser_eq(t2) for ((k1, t1), (k2, t2)) in zip(self.fields.items(), other.fields.items()))

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

    def generate_parser(self):
        for t in self.fields.values():
            t.generate_parser()
        new, f = Gopyjson.RegisterParser(self)
        if new:
            wl(f'func pTrim__{f}(b *[]byte, N *int, v *')
            self.print_type()
            w(') ')
            with BraceBlock():
                wls('''
                pTrimByte(b, N, '[')
                trimLeftSpace(b, N)
                ''')
                for i, (key, t) in enumerate(self.fields.items()):
                    if i > 0:
                        wls('''
                        pTrimByte(b, N, ',')
                        trimLeftSpace(b, N)
                        ''')
                    t.trim(field_pointer('v', key))
                    wl('trimLeftSpace(b, N)')
                wl("pTrimByte(b, N, ']')")

    def zero(self, pvar: str):
        for k, t in self.fields.items():
            t.zero(field_pointer(pvar, k))


# Used for parsing arrays of variable length and known element types into a Go slice
class Slice(GoType):
    def __init__(self, element_type: GoType, **kwargs):
        super().__init__(**kwargs)
        self.element_type = element_type

    def type_eq(self, other) -> bool:
        return super().type_eq(other) and self.element_type.type_eq(other.element_type)

    def zero(self, pvar: str):
        # Here we just slice the slice, to avoid garbage collection.
        # This way there are fewer allocations if the object is reused.
        wl(f'{dereference(pvar)} = {index(pvar, ":0")}')

    def long_typename(self):
        w(f'[]')
        self.element_type.print_type()

    def generate_type(self):
        self.element_type.generate_type()
        super().generate_type()

    def generate_parser(self):
        self.element_type.generate_parser()
        new, f = Gopyjson.RegisterParser(self)
        if new:
            wl(f'func pTrim__{f}(b *[]byte, N *int, v *')
            self.print_type()
            w(') ')
            with BraceBlock():
                element_var = f'var__{Gopyjson.RegisterParser(self.element_type)[1]}'
                wl(f'var {element_var} ')
                self.element_type.print_type()
                wls('''
                pTrimByte(b, N, '[')
                trimLeftSpace(b, N)
                if *N >= len(*b) {
                    panic(ParseError{*b, *N, "unexpected end of array"})
                }
                if (*b)[*N] == ']' {
                    *N++
                    return
                }
                ''')
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
                        return
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


# Used for parsing JSON objects with known keys and known value types into a Go struct
class Struct(GoType):
    def __init__(self, fields: dict[str, GoType | PyTuple[GoType, str]], typename: str = '', other_keys: str = 'skip'):
        assert other_keys == 'skip' or other_keys == 'fail'
        super().__init__(typename=typename)
        self.fields: dict[str, GoType] = {k: v[0] if type(v) == tuple else v for k, v in fields.items()}
        self.names: dict[str, str] = {k: v[1] if type(v) == tuple else k for k, v in fields.items()}
        self.other_keys = other_keys

    def type_eq(self, other) -> bool:
        return super().type_eq(other) and len(other.fields) == len(self.fields) and all(
            k1 == k2 and t1.type_eq(t2) for ((k1, t1), (k2, t2)) in
            zip(self.fields.items(), other.fields.items()))

    def parser_eq(self, other) -> bool:
        return self.type_eq(other) and all(k1 == k2 and t1.parser_eq(t2) for ((k1, t1), (k2, t2)) in
                                           zip(self.fields.items(), other.fields.items())) and self.names == other.names

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

    def generate_parser(self):
        for t in self.fields.values():
            t.generate_parser()
        new, f = Gopyjson.RegisterParser(self)
        if new:
            wl(f'func pTrim__{f}(b *[]byte, N *int, v *')
            self.print_type()
            w(') ')
            with BraceBlock():
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
                self.skip_or_fail()

    # Appears slower than full key switch
    def key_switch_by_first_byte(self, pvar: str):
        assert all(len(k.encode('utf-8')) >= 1 for k in self.names.values())
        assert len(set(k.encode('utf-8')[0] for k in self.names.values())) == len(self.names)
        with If('len(key) == 0'):
            self.skip_or_fail()
        with Switch('key[0]'):
            for k, t in self.fields.items():
                with Case(str(self.names[k].encode('utf-8')[0])):
                    with If('key != "' + self.names[k] + '"'):
                        self.skip_or_fail()
                    t.trim(field_pointer(pvar, k))
                    wl('trimLeftSpace(b, N)')
            with Default():
                self.skip_or_fail()

    def skip_or_fail(self):
        if self.other_keys == 'skip':
            wl('pTrimValue(b, N)')
        else:
            wl(r'panic(ParseError{*b, *N, errUnexpectedKey + key + "\""})')

    def key_switch_len1(self, pvar: str):
        assert all(len(k.encode('utf-8')) == 1 for k in self.names.values())
        assert len(set(k.encode('utf-8')[0] for k in self.names.values())) == len(self.names)
        with If('len(key) != 1'):
            self.skip_or_fail()
        with Switch('key[0]'):
            for k, t in self.fields.items():
                with Case(str(self.names[k].encode('utf-8')[0])):
                    t.trim(field_pointer(pvar, k))
                    wl('trimLeftSpace(b, N)')
            with Default():
                self.skip_or_fail()

    def zero(self, pvar: str):
        for k, t in self.fields.items():
            t.zero(field_pointer(pvar, k))


# Used for parsing JSON objects with known value types
class Map(GoType):
    def __init__(self, key_type: String, value_type: GoType, typename: str = ''):
        super().__init__(typename=typename)
        self.key_type: String = key_type
        self.value_type = value_type

    def type_eq(self, other) -> bool:
        return super().type_eq(other) and self.key_type.type_eq(other.key_type) and self.value_type.type_eq(
            other.value_type)

    def parser_eq(self, other) -> bool:
        return self.type_eq(other) and self.key_type.parser_eq(other.key_type) and self.value_type.parser_eq(
            other.value_type)

    def long_typename(self):
        w('map[')
        self.key_type.print_type()
        w(']')
        self.value_type.print_type()

    def generate_type(self):
        self.key_type.generate_type()
        self.value_type.generate_type()
        super().generate_type()

    def generate_parser(self):
        self.key_type.generate_parser()
        self.value_type.generate_parser()
        new, f = Gopyjson.RegisterParser(self)
        if new:
            wl(f'func pTrim__{f}(b *[]byte, N *int, v *')
            self.print_type()
            w(') ')
            with BraceBlock():
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
                    wl('var value ')
                    self.value_type.print_type()
                    self.value_type.trim('&value')
                    wl('trimLeftSpace(b, N)')
                    wl('(*v)[key] = value')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = make(')
        self.print_type()
        w(')')


# Used for parsing floats delimited by quotes
class QuotedFloat64(GoType):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimQuotedFloat64')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = 0')

    def long_typename(self):
        w('float64')

    def generate_parser(self):
        new, f = Gopyjson.RegisterParser(self)
        if new:
            wls('''
            func pTrimQuotedFloat64(b *[]byte, N *int) float64 {
                pTrimByte(b, N, '"')
                value, n, err := stof64(bytesToString((*b)[*N:]))
                if err != nil {
                    panic(ParseError{*b, *N, errStof64 + err.Error()})
                }
                *N += n
                pTrimByte(b, N, '"')
                return value
            }
            ''')


# Used for parsing floats into a structure
# struct {
#     Value float64
#     Src []byte
# }
# The float is saved to the Value field, and the original source JSON is saved to the Src field
class Float64WithSrc(GoType):
    def __init__(self, typename: str = ''):
        super().__init__(typename=typename)

    def zero(self, pvar: str):
        wl(f'{pvar.lstrip("&")}.Value = 0')
        wl(f'{pvar.lstrip("&")}.Src = {pvar.lstrip("&")}.Src[:0]')

    def long_typename(self):
        w('struct ')
        with BraceBlock():
            wl('Value float64')
            wl('Src []byte')

    def generate_parser(self):
        new, f = Gopyjson.RegisterParser(self)
        if new:
            wl(f'func pTrim__{f}(b *[]byte, N *int, v *')
            self.print_type()
            w(') ')
            with BraceBlock():
                wls('''
                n := *N
                v.Value = pTrimFloat64(b, N)
                v.Src = (*b)[n:*N]
                return
                ''')


# This context manager takes care of managing the set of defined types, parsers and unmarshalers.
# Also, it also takes care of writing all the generated code into Go files inside the provided directory path.
class Gopyjson:
    current: 'Gopyjson' = None

    # Argument output_dir is the directory where we want to save the generated code
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.types: list[GoType] = []  # List of defined types
        self.parsers: list[GoType] = []  # List of defined parser functions
        self.unmarshalers: set[str] = set()  # List of defined unmarshalers

    def __enter__(self):
        assert Gopyjson.current is None  # Nested context manager not allowed
        Gopyjson.current = self
        output_dir = Path(self.output_dir)
        if not output_dir.is_dir():
            raise Exception("Directory doesn't exist: " + str(output_dir))
        output_dir = output_dir.joinpath('gopyjson')
        # Create <output_dir>/gopyjson subdirectory if it doesn't already exist
        output_dir.mkdir(exist_ok=True)
        # Copy common code to <output_dir>/gopyjson/common.go
        shutil.copyfile('go/common.go', output_dir.joinpath('common.go'))
        self.file = File(output_dir.joinpath('gopyjson.go'), 'gopyjson')
        self.file.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.__exit__(exc_type, exc_val, exc_tb)
        Gopyjson.current = None

    # Registers the given type if an equal type was not registered already.
    # Returns whether the type was registered.
    @staticmethod
    def RegisterType(go_type: GoType) -> bool:
        for t in Gopyjson.current.types:
            if go_type.type_eq(t):
                return False
        Gopyjson.current.types.append(go_type)
        return True

    # Registers the parser for a given type if an equivalent parser was not registered already.
    # Returns whether if was registered and its unique index in the list of registered types
    @staticmethod
    def RegisterParser(go_type: 'GoType') -> tuple[bool, int]:
        for i, t in enumerate(Gopyjson.current.parsers):
            if go_type.parser_eq(t):
                return False, i
        Gopyjson.current.parsers.append(go_type)
        return True, len(Gopyjson.current.parsers) - 1
