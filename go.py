from contextlib import contextmanager
from pathlib import Path
from typing import Optional


# Block objects represent a block of code
class Block:
    current: 'Block' = None  # Pointer to the current block

    def __init__(self, indent=1):
        self.parent: Optional['Block'] = Block.current  # Parent block
        self.buffer: str = ''  # Code contents of this block
        self.variables: dict[str, str] = {}  # Variables declared in this block
        self.indent: int = indent  # Indentation of this block
        if self.parent is not None:
            self.indent += self.parent.indent

    def __enter__(self):
        # Update the pointer to the current block
        Block.current = self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Add variable declarations to the start of the block
        with BlockPrepend():
            for k, v in self.variables.items():
                wl(f'var {k} {v}')
        # Append the generated code to the end of the parent block
        if self.parent is not None:
            self.parent.buffer += self.buffer
        # Update the pointer to the current block
        Block.current = self.parent


# Appends s to the end of current block
def w(s: str):
    Block.current.buffer += s


# Flushes the current line and writes string s to the next line (with indent)
def wl(s: str = ''):
    Block.current.buffer += '\n' + File.current.tab * Block.current.indent + s


# BraceBlock is the same as Block, but always increases indent by 1 and surrounds the generated code by braces
class BraceBlock(Block):
    def __enter__(self):
        super().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        with BlockPrepend():
            w('{')
        with Indent(-1):
            wl('}')
        super().__exit__(exc_type, exc_val, exc_tb)


# File objects are used to generate code and save the result in a file.
class File:
    current: 'File | GoFile' = None

    def __init__(self, filepath: str | Path):
        filepath = Path(filepath)
        assert File.current is None
        self.filepath: Path = filepath
        self.tab: str = '\t'  # Used for indenting generated code
        self.tabsize: int = 4  # Tab size for wl(), wls(), WLS()
        self.block = Block(0)

    def __enter__(self):
        assert File.current is None  # Nested files not allowed
        File.current = self
        self.block.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.block.__exit__(exc_type, exc_val, exc_tb)
        with open(self.filepath, 'w') as f:
            f.write(self.block.buffer)
        File.current = None


# Code generated inside "with" block will be prepended to the current content of the file
@contextmanager
def FilePrepend():
    buffer = File.current.block.buffer
    File.current.block.buffer = ''
    yield
    File.current.block.buffer += buffer


# Removes leading space (and tabs) from s, returns how much space
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
    s = s.lstrip('\n')  # Remove empty lines at the start
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


# Indents the generated code
@contextmanager
def Indent(indent: int = 1):
    Block.current.indent += indent
    yield
    Block.current.indent -= indent


@contextmanager
def WLS(s: str, *args: any, **kwargs: any):
    for tabs, line in zip(*_wls(s, *args, **kwargs)):
        with Indent(tabs // 4):
            if line == '{{}}':
                yield
            else:
                wl(line)


class Package:
    current: 'Package' = None

    def __init__(self, name: str):
        assert Package.current is None  # Nested Package context manager not allowed
        self.name = name

    def __enter__(self):
        Package.current = self

    def __exit__(self, exc_type, exc_val, exc_tb):
        Package.current = None


@contextmanager
def BlockPrepend():
    buffer = Block.current.buffer
    Block.current.buffer = ''
    yield
    Block.current.buffer += buffer


# GoFile objects are used with "with" statements to generate go files.
# When used, they must be nested inside a "with Package(...)" block.
class GoFile(File):
    def __init__(self, filepath: str | Path):
        filepath = Path(filepath)
        assert filepath.name.endswith('.go')
        super().__init__(filepath)
        self.imports: dict[str, str] = {}  # List of packages to import as a mapping package -> alias

    def __enter__(self):
        assert Package.current is not None  # Every GoFile must belong to some Package
        super().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        with FilePrepend():
            w('package ' + Package.current.name)
            wl('')
            if self.imports:
                wl('import (')
                with Indent():
                    for package, alias in sorted(self.imports.items()):
                        wl((alias + ' ' if alias else '') + '"' + package + '"')
                wl(')')
        super().__exit__(exc_type, exc_val, exc_tb)


# Adds an import statement that will be generated at the top of the file
def Import(package: str, alias: str = ''):
    assert isinstance(File.current, GoFile)
    GoFile.current.imports[package] = alias


# Adds a variable declaration that will be generated at the top of the current block of code
def Var(name: str, typename: str):
    Block.current.variables[name] = typename


# Wraps the code inside a "switch" block
@contextmanager
def Switch(s: str):
    wl('switch ' + s + ' {')
    yield
    wl('}')


# Wraps the code inside a "case" block (part of switch statement)
# Doesn't check if the "case" is inside a "switch" block.
@contextmanager
def Case(s: str):
    wl('case ' + s + ':')
    with Block():
        yield


# Wraps the code inside a "default" block (part of switch statement)
# Doesn't check if the "default" is inside a "switch" block.
@contextmanager
def Default():
    wl('default:')
    with Block():
        yield


# Wraps the code inside a "for" loop
@contextmanager
def For(s: str = ''):
    if s:
        wl('for ' + s + ' ')
    else:
        wl('for ')
    with BraceBlock():
        yield


# Wraps the code inside an "if" block
@contextmanager
def If(s: str):
    wl('if ' + s + ' ')
    with BraceBlock():
        yield


# Wraps the code inside an "else if" block.
# Doesn't check if there is a matching "if" block.
@contextmanager
def ElseIf(s: str):
    w(' else if ' + s + ' ')
    with BraceBlock():
        yield


# Wraps the code inside an "else" block.
# Doesn't check if there is a matching "if" block.
@contextmanager
def Else():
    w(' else ')
    with BraceBlock():
        yield


# Wraps the code inside a function with a given name and signature.
@contextmanager
def Func(s: str):
    wl('func ' + s + ' ')
    with BraceBlock():
        yield
