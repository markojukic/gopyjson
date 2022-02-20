from contextlib import contextmanager
from pathlib import Path
from typing import Iterable


@contextmanager
def FilePrepend():
    buffer = File.current.buffer
    File.current.buffer = ''
    yield
    File.current.buffer += buffer


class File:
    current: 'File' = None

    def __init__(self, filepath: str | Path):
        filepath = Path(filepath)
        assert File.current is None
        self.filepath = filepath
        self.tab: str = '\t'  # Used for indenting generated code
        self.tabsize: int = 4  # Tab size for wls(), WLS()
        self.flush: bool = True
        self.buffer: str = ''
        self.indent: int = 0

    def __enter__(self):
        File.current = self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with open(self.filepath, 'w') as f:
            f.write(self.buffer)
        File.current = None


def w(s: str):
    File.current.buffer += s


def wl(s: str = ''):
    if s:
        assert not s[0].isspace()
        if File.current.flush:
            w('\n' + File.current.tab * File.current.indent)
        w(s)
    else:
        if File.current.flush:
            w('\n')


def leading_space(s) -> tuple[int, str]:
    n = 0
    for i in range(len(s)):
        if s[i] == ' ':
            n += 1
        elif s[i] == '\t':
            n += File.current.tabsize
        else:
            return n, s[i:]
    return n, ''


def _wls(s: str, *args: any, **kwargs: any) -> tuple[list[int], list[str]]:
    s = '\n'.join(line.rstrip() for line in s.rstrip().split('\n'))  # Remove trailing whitespace
    while s and s[0] == '\n':  # Remove empty lines at the start
        s = s[1:]
    if not s:
        return [], []
    for i, arg in enumerate(args):  # Substitute arguments
        s = s.replace('{' + str(i) + '}', str(args[i]))
    for k, v in kwargs.items():  # Substitute keyword arguments
        s = s.replace('{' + k + '}', str(v))
    spaces, lines = map(list, zip(*(leading_space(line) for line in s.splitlines())))
    min_space = min(space for space, line in zip(spaces, lines) if line)
    spaces = [i - min_space for i in spaces]  # Remove common indent
    assert all(i % 4 == 0 for i in spaces)
    return spaces, lines


def wls(s: str, *args: any, **kwargs: any):
    for tabs, line in zip(*_wls(s, *args, **kwargs)):
        with Indent(tabs // 4):
            wl(line)


@contextmanager
def Indent(indent: int = 1):
    File.current.indent += indent
    yield
    File.current.indent -= indent


@contextmanager
def WLS(s: str, *args: any, **kwargs: any):
    for tabs, line in zip(*_wls(s, *args, **kwargs)):
        with Indent(tabs // 4):
            if line == '{{}}':
                yield
            else:
                wl(line)


def cum_sum(seq: Iterable[int]):
    s = 0
    result = []
    for i in seq:
        s += i
        result.append(s)
    return result


def subset(a: Iterable[str], b: Iterable[str]) -> bool:
    return all(i in b for i in a)


def minus(a: Iterable[str], b: Iterable[str]) -> list[str]:
    return list(i for i in a if i not in b)


class Package:
    current: 'Package' = None

    def __init__(self, name: str):
        assert Package.current is None  # Nested Package context manager not allowed
        self.name = name

    def __enter__(self):
        Package.current = self

    def __exit__(self, exc_type, exc_val, exc_tb):
        Package.current = None


class Block:
    current: 'Block' = None

    def __init__(self, braces: bool = True, new_line: bool = True):
        assert File.current is not None
        self.variables: dict[str, str] = {}
        self.outer_block = Block.current
        self.n = len(File.current.buffer)
        self.braces = braces
        self.new_line = new_line

    def __enter__(self):
        Block.current = self
        if self.braces:
            File.current.indent += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        with BlockPrepend():
            if self.braces:
                if self.new_line:
                    with Indent(-1):
                        wl('{')
                else:
                    w('{')
            for k, v in self.variables.items():
                wl(f'var {k} {v}')
        Block.current = self.outer_block
        if self.braces:
            File.current.indent -= 1
            wl('}')


@contextmanager
def BlockPrepend():
    buffer = File.current.buffer
    File.current.buffer = ''
    yield
    File.current.buffer = buffer[:Block.current.n] + File.current.buffer + buffer[Block.current.n:]


class GoFile(File):
    current: 'GoFile' = None

    def __init__(self, filepath: str | Path):
        filepath = Path(filepath)
        assert filepath.name.endswith('.go')
        assert Package.current is not None
        super().__init__(filepath)
        self.imports: dict[str, str] = {}

    def __enter__(self):
        GoFile.current = self
        super().__enter__()
        self.block = Block(False)  # Block for global variables
        self.block.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.block.__exit__(exc_type, exc_val, exc_tb)
        with FilePrepend():
            w(f'package {Package.current.name}')
            if self.imports:
                with WLS('''
                import (
                    {{}}
                )
                '''):
                    for package in sorted(self.imports):
                        alias = self.imports[package]
                        wl((alias + ' ' if alias else '') + '"' + package + '"')
        super().__exit__(exc_type, exc_val, exc_tb)
        GoFile.current = None


def Import(package: str, alias: str = ''):
    GoFile.current.imports[package] = alias


def Var(name: str, typename: str):
    Block.current.variables[name] = typename


@contextmanager
def Switch(s: str):
    wl('switch ' + s + ' {')
    yield
    wl('}')


@contextmanager
def Case(s: str):
    wl('case ' + s + ':')
    with Indent():
        with Block(braces=False):
            yield


@contextmanager
def Default():
    wl('default:')
    with Indent():
        with Block(braces=False):
            yield


@contextmanager
def For(s: str = ''):
    if s:
        wl('for ' + s + ' ')
    else:
        wl('for ')
    with Block(new_line=False):
        yield


@contextmanager
def If(s: str):
    wl('if ' + s + ' ')
    with Block(new_line=False):
        yield


@contextmanager
def ElseIf(s: str):
    w(' else if ' + s + ' ')
    with Block(new_line=False):
        yield


@contextmanager
def Else():
    w(' else ')
    with Block(new_line=False):
        yield


@contextmanager
def Func(s: str):
    wl('func ' + s + ' ')
    with Block(new_line=False):
        yield
