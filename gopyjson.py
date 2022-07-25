import shutil

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


class Parser:
    def __init__(self, typename: str = ''):
        self.typename = typename  # The Go typename for this type, can be empty

    # Sets the value of pvar to zero. Used before parsing.
    def zero(self, pvar: str):
        raise NotImplementedError()

    # Generates the type definition (the part that comes after "type <typename> ")
    def long_typename(self):
        raise NotImplementedError()

    # Returns a hashable object such that if x.type_id() == y.type_id(),
    # then pointers to underlying types of x and y can be converted one to another.
    # Used to avoid duplicate code.
    def type_id(self):
        return type(self)

    # Returns a hashable object such that if x.type_id() == y.type_id() and x.parser_id() == y.parser_id(),
    # Then x and y generate equivalent parser code.
    # Used to avoid duplicate code.
    def parser_id(self):
        return None

    # Generates code that parses from b starting at index N and saves result to Go object located at pvar
    def trim(self, pvar: str):
        # Checks if the type was defined first
        new, t = Package.RegisterType(self)
        assert not new
        # Check if the parser was defined first
        new, f = Package.RegisterParser(self)
        assert not new
        wl(f'pTrim{f}(b, N, (*type{t})({pvar}))')

    # Generates code that parses this type from b starting at index N using a given function, saves result to pvar.
    # This is used by simple types like integers or floats in combination with predefined parsers from common.go.
    def trim_using(self, pvar, func: str):
        if self.typename:
            wl(f'{dereference(pvar)} = {self.typename}({func}(b, N))')
        else:
            wl(f'{dereference(pvar)} = {func}(b, N)')

    # Generates either the typename or type definition, used for variable declarations
    def print_type(self):
        if self.typename:
            w(self.typename)
        else:
            self.long_typename()

    # Generates the type declaration if not already generated
    # Also generates a type alias that is common to all parsers with same type_id.
    # This type alias is used in the generated parser functions, which can then be reused.
    def generate_type(self):
        new, t = Package.RegisterType(self)
        if self.typename and self.typename not in Package.current.typenames:
            Package.current.typenames.add(self.typename)
            wl(f'type {self.typename} ')
            self.long_typename()
        if new:
            if self.typename:
                wl(f'type type{t} {self.typename}')
            else:
                wl(f'type type{t} ')
                self.long_typename()

    # Generates the parser if an equivalent parser has not already been generated
    def generate_parser(self):
        pass

    # Generates the Unmarshal method for this type
    def generate(self, func_name: str = 'Unmarshal'):
        assert self.typename
        if f'{self.typename}.{func_name}' in Package.current.unmarshalers:
            raise Exception(f'{self.typename}.{func_name} already defined')

        Package.current.unmarshalers.add(f'{self.typename}.{func_name}')
        self.generate_type()
        self.generate_parser()
        with Func(f'(v *{self.typename}) {func_name}(data []byte) (err error)'):
            self.zero('v')
            wl('defer RecoverLater(&err)')
            wl('var n int')
            wl('N := &n')
            wl('b := &data')
            wl('trimLeftSpace(b, N)')
            self.trim('v')
            wl('return nil')

    # Syntactic sugar for (self, json_field), used with Struct() fields that don't have the same name as json field
    def __floordiv__(self, json_field: str) -> tuple['Parser', str]:
        return self, json_field


# Used for parsing a boolean
class Bool(Parser):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimBool')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = false')

    def long_typename(self):
        w('bool')


# Used for parsing an int64
class Int64(Parser):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimInt64')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = 0')

    def long_typename(self):
        w('int64')


# Used for parsing an uint64
class UInt64(Parser):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimUint64')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = 0')

    def long_typename(self):
        w('uint64')


# Used for parsing a float32
class Float32(Parser):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimFloat32')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = 0')

    def long_typename(self):
        w('float32')


# Used for parsing a float64
class Float64(Parser):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimFloat64')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = 0')

    def long_typename(self):
        w('float64')


# Used for parsing a string
class String(Parser):
    # Arguments
    # copy: whether the result should be a copy or just a reference to a part of the buffer we are parsing from
    # validate_utf8: turn on/off UTF8 validation for this string
    # unquote: turn on/off unquoting for this string, which makes substitutions like '\\\\' -> '\\', '\\t' -> '\t'...
    def __init__(self, copy: bool = True, validate_utf8: bool = True, unquote: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.copy = copy
        self.validate_utf8 = validate_utf8
        self.unquote = unquote

    def type_id(self):
        return String

    def parser_id(self):
        return self.copy, self.validate_utf8, self.unquote

    def generate_parser(self):
        new, t = Package.RegisterType(self)
        assert not new
        new, f = Package.RegisterParser(self)
        if new:
            with Func(f'pTrim{f}(b *[]byte, N *int, v *type{t})'):
                if self.unquote:
                    wl('s := pTrimStringBytes(b, N)')
                    wl('s, ok := unquoteBytes((*b)[*N - len(s) - 2:*N])')  # Copy made here
                    with If('!ok'):
                        wl('panic(ParseError{*b, *N, errUnquote})')
                    wl(f'*v = type{t}(s)')  # Compiler avoids a copy here, no need to use bytesToString()
                else:
                    if self.copy:
                        wl(f'*v = type{t}(pTrimStringBytes(b, N))')
                    else:
                        wl(f'*v = type{t}(bytesToString(pTrimStringBytes(b, N)))')
                if self.validate_utf8:
                    Import('unicode/utf8')
                    with If(f'!utf8.ValidString(string(*v))'):
                        wl('panic(ParseError{*b, *N, errUTF8})')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = ""')

    def long_typename(self):
        w('string')


# Turns off all safety features and avoids copying. Parsing is faster as a result.
class UnsafeString(String):
    def __init__(self, **kwargs):
        super().__init__(copy=False, validate_utf8=False, unquote=False, **kwargs)


# Used for parsing arrays of known length and element type into a Go array.
class Array(Parser):
    def __init__(self, size: int, element_parser: Parser, **kwargs):
        assert size > 0
        super().__init__(**kwargs)
        self.size = size
        self.element_parser = element_parser

    def long_typename(self):
        w(f'[{self.size}]')
        self.element_parser.print_type()

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = ')
        self.print_type()
        w('{}')

    def type_id(self):
        return Array, self.size, self.element_parser.type_id(), self.element_parser.typename

    def parser_id(self):
        return self.size, self.element_parser.parser_id()

    def generate_type(self):
        self.element_parser.generate_type()
        super().generate_type()

    def generate_parser(self):
        self.element_parser.generate_parser()
        new, t = Package.RegisterType(self)
        assert not new
        new, f = Package.RegisterParser(self)
        if new:
            with Func(f'pTrim{f}(b *[]byte, N *int, v *type{t})'):
                wl("pTrimByte(b, N, '[')")
                wl('trimLeftSpace(b, N)')
                for i in range(self.size):
                    if i > 0:
                        wl("pTrimByte(b, N, ',')")
                        wl('trimLeftSpace(b, N)')
                    self.element_parser.trim('&' + index('v', str(i)))
                    wl('trimLeftSpace(b, N)')
                wl("pTrimByte(b, N, ']')")


# Used for parsing arrays of known length and variable element types into a Go struct
class Tuple(Parser):
    def __init__(self, fields: dict[str, Parser], typename: str = ''):
        super().__init__(typename=typename)
        self.fields: dict[str, Parser] = fields

    def type_id(self):
        return Tuple, tuple((k, v.type_id()) for k, v in self.fields.items())

    def parser_id(self):
        return super().parser_id(), tuple((k, v.parser_id()) for k, v in self.fields.items())

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
        new, t = Package.RegisterType(self)
        assert not new
        new, f = Package.RegisterParser(self)
        if new:
            with Func(f'pTrim{f}(b *[]byte, N *int, v *type{t})'):
                wl("pTrimByte(b, N, '[')")
                wl('trimLeftSpace(b, N)')
                for i, (key, t) in enumerate(self.fields.items()):
                    if i > 0:
                        wl("pTrimByte(b, N, ',')")
                        wl('trimLeftSpace(b, N)')
                    t.trim(field_pointer('v', key))
                    wl('trimLeftSpace(b, N)')
                wl("pTrimByte(b, N, ']')")

    def zero(self, pvar: str):
        for k, t in self.fields.items():
            t.zero(field_pointer(pvar, k))


# Used for parsing arrays of variable length and known element types into a Go slice
class Slice(Parser):
    def __init__(self, element_parser: Parser, **kwargs):
        super().__init__(**kwargs)
        self.element_parser = element_parser

    def type_id(self):
        return Slice, self.element_parser.type_id(), self.element_parser.typename

    def parser_id(self):
        return self.element_parser.parser_id()

    def zero(self, pvar: str):
        # Here we just slice the slice, to avoid garbage collection.
        # This way there are fewer allocations if the object is reused.
        wl(f'{dereference(pvar)} = {index(pvar, ":0")}')

    def long_typename(self):
        w(f'[]')
        self.element_parser.print_type()

    def generate_type(self):
        self.element_parser.generate_type()
        super().generate_type()

    def generate_parser(self):
        self.element_parser.generate_parser()
        new, t = Package.RegisterType(self)
        assert not new
        new, f = Package.RegisterParser(self)
        if new:
            with Func(f'pTrim{f}(b *[]byte, N *int, v *type{t})'):
                wl(f'var element ')
                self.element_parser.print_type()
                wl("pTrimByte(b, N, '[')")
                wl('trimLeftSpace(b, N)')
                with If('*N >= len(*b)'):
                    wl('panic(ParseError{*b, *N, "unexpected end of array"})')
                with If("(*b)[*N] == ']'"):
                    wl('*N++')
                    wl('return')
                self.element_parser.trim('&element')
                wl(f'*v = append(*v, element)')
                with For():
                    wl('trimLeftSpace(b, N)')
                    with If('*N >= len(*b)'):
                        wl('panic(ParseError{*b, *N, "unexpected end of array"})')
                    with If("(*b)[*N] == ']'"):
                        wl('*N++')
                        wl('return')
                    wl("pTrimByte(b, N, ',')")
                    wl('trimLeftSpace(b, N)')
                    self.element_parser.trim('&element')
                    wl(f'*v = append(*v, element)')


# Used for parsing JSON objects with known keys and known value types into a Go struct
class Struct(Parser):
    def __init__(self, fields: dict[str, Parser | tuple[Parser, str]], typename: str = '', other_keys: str = 'skip'):
        assert other_keys == 'skip' or other_keys == 'fail'
        super().__init__(typename=typename)
        self.fields: dict[str, Parser] = {k: v[0] if type(v) == tuple else v for k, v in fields.items()}
        self.names: dict[str, str] = {k: v[1] if type(v) == tuple else k for k, v in fields.items()}
        self.other_keys = other_keys

    def type_id(self):
        return Struct, tuple((k, v.type_id(), v.typename) for k, v in self.fields.items())

    def parser_id(self):
        return tuple(v.parser_id() for v in self.fields.values()), self.other_keys

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

        new, t = Package.RegisterType(self)
        assert not new
        new, f = Package.RegisterParser(self)
        if new:
            with Func(f'pTrim{f}(b *[]byte, N *int, v *type{t})'):
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

    def skip_or_fail(self):
        if self.other_keys == 'skip':
            wl('pTrimValue(b, N)')
        else:
            wl(r'panic(ParseError{*b, *N, errUnexpectedKey + key + "\""})')

    # Detects the field corresponding to an object key by using a string switch.
    def key_switch(self, pvar: str):
        with Switch('key'):
            for k, t in self.fields.items():
                with Case(f'"{self.names[k]}"'):
                    t.trim(field_pointer(pvar, k))
                    wl('trimLeftSpace(b, N)')
            with Default():
                self.skip_or_fail()

    # Detects the field corresponding to an object key by a switch on first characters,
    # if all fields have different first characters. Appears slower than string switch.
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

    # Detects the field corresponding to an object key by a switch on first characters,
    # if all fields have length 1. Faster than full string switch.
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
class Map(Parser):
    def __init__(self, key_parser: String, value_parser: Parser, typename: str = ''):
        super().__init__(typename=typename)
        self.key_parser: String = key_parser
        self.value_parser = value_parser

    def type_id(self):
        return Map, self.key_parser.type_id(), self.key_parser.typename, self.value_parser.type_id(), self.value_parser.typename

    def parser_id(self):
        return self.key_parser.parser_id(), self.value_parser.parser_id()

    def long_typename(self):
        w('map[')
        self.key_parser.print_type()
        w(']')
        self.value_parser.print_type()

    def generate_type(self):
        self.key_parser.generate_type()
        self.value_parser.generate_type()
        super().generate_type()

    def generate_parser(self):
        self.key_parser.generate_parser()
        self.value_parser.generate_parser()

        new, t = Package.RegisterType(self)
        assert not new
        new, f = Package.RegisterParser(self)
        if new:
            with Func(f'pTrim{f}(b *[]byte, N *int, v *type{t})'):
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
                    self.value_parser.print_type()
                    self.value_parser.trim('&value')
                    wl('trimLeftSpace(b, N)')
                    wl('(*v)[key] = value')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = make(')
        self.print_type()
        w(')')


# Used for parsing floats delimited by quotes
class QuotedFloat64(Parser):
    def trim(self, pvar: str):
        self.trim_using(pvar, 'pTrimQuotedFloat64')

    def zero(self, pvar: str):
        wl(f'{dereference(pvar)} = 0')

    def long_typename(self):
        w('float64')

    def generate_parser(self):
        new, f = Package.RegisterParser(self)
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
class Float64WithSrc(Parser):
    def __init__(self, typename: str = ''):
        super().__init__(typename=typename)

    def zero(self, pvar: str):
        wl(f'{pvar.lstrip("&")}.Value = 0')
        wl(f'{pvar.lstrip("&")}.Src = {pvar.lstrip("&")}.Src[:0]')

    def long_typename(self):
        w('struct ')
        with Braces():
            wl('Value float64')
            wl('Src []byte')

    def generate_parser(self):
        new, t = Package.RegisterType(self)
        assert not new
        new, f = Package.RegisterParser(self)
        if new:
            with Func(f'pTrim{f}(b *[]byte, N *int, v *type{t})'):
                wls('''
                n := *N
                v.Value = pTrimFloat64(b, N)
                v.Src = (*b)[n:*N]
                return
                ''')


# This context manager takes care of managing the set of defined types, parsers and unmarshalers.
# Also, it also takes care of writing all the generated code into Go files inside the provided directory path.
class Package:
    current: 'Package' = None

    # Argument output_dir is the directory where we want to save the generated code
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.types: dict[any, int] = {}  # Defined types, saved as a mapping type_id -> unique integer
        self.parsers: dict[any, int] = {}  # Defined parsers, saved as a mapping (type_id, parser_id) -> unique integer
        self.typenames: set[str] = set()  # Defined typenames
        self.unmarshalers: set[str] = set()  # Defined unmarshalers

    def __enter__(self):
        assert Package.current is None  # Nested context manager not allowed
        Package.current = self
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
        Package.current = None

    # Registers the given type if an equal type was not registered already.
    # Returns whether the type was registered.
    @staticmethod
    def RegisterType(parser: Parser) -> tuple[bool, int]:
        pid = parser.type_id()
        if pid in Package.current.types:
            return False, Package.current.types[pid]
        Package.current.types[pid] = len(Package.current.types)
        return True, len(Package.current.types) - 1

    # Registers the parser for a given type if an equivalent parser was not registered already.
    # Returns whether if was registered and its unique index in the list of registered types
    @staticmethod
    def RegisterParser(parser: Parser) -> tuple[bool, int]:
        pid = (parser.type_id(), parser.parser_id())
        if pid in Package.current.parsers:
            return False, Package.current.parsers[pid]
        Package.current.parsers[pid] = len(Package.current.parsers)
        return True, len(Package.current.parsers) - 1
