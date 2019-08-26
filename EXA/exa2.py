#!/usr/bin/env python3.7

import operator as ops
import os

from pprint import pprint


FILES = {
    "100": [1, 265, 3, 6, 557, 4],
    "200": [],
    "400": [],
}


class InvalidFileError(FileNotFoundError):
    pass


class F_RegisterAccessError(Warning):
    pass


def load(file):
    if not file.endswith(".exa"):
        raise InvalidFileError(file)
    with open(file, "r") as f:
        data = f.readlines()
        data = [line for line in data if line != "\n"]
    return data


class Ops:
    """ Execute EXA mathematical and assignment statement.
    """

    def __init__(self, function, args, state):
        self.state = state
        self.function = function
        self.value_1 = self.get_value(args[0])
        self.value_2 = self.get_value(args[1])
        self.register = args[-1]
        if args[0] == "F" and self.state.eof > self.state.location:
            self.state.read()
        self.factory()

    def get_value(self, value):
        if value not in "TXF" and not value.isdigit():
            _ = "Invalid R/N (Register/Number): {}".format(value)
            raise RuntimeError(_)
        if value == "T":
            return self.state.T
        if value == "X":
            return self.state.X
        if value == "F":
            return self.state.F
        return int(value)

    def factory(self):
        operations = {
            "ADDI": self.addi,
            "SUBI": self.subi,
            "MULI": self.muli,
            "DIVI": self.divi,
            "MODI": self.modi,
            "COPY": self.copy,
        }
        for function, method in operations.items():
            if self.function == function:
                result = method()
                self.state.store(self.register, result)
                break
        self.state.registry["location"] += 1
        if self.register == "F":
            self.state.write()

    def divi(self):
        return self.value_1 // self.value_2 if self.value_2 else None

    def modi(self):
        return self.value_1 % self.value_2 if self.value_2 else None

    def muli(self):
        return self.value_1 * self.value_2

    def addi(self):
        return self.value_1 + self.value_2

    def subi(self):
        return self.value_1 - self.value_2

    def copy(self):
        return self.value_1


class Test:
    """ Compare EXA register/number values via test statement.
    """

    def __init__(self, func, args, functions, state):
        self.state = state
        self.value_1 = self.get_value(args[0])
        self.op = args[1] if not args[0] == "EOF" else None
        self.register = self.get_value(args[-1])
        if self.op:
            self.factory()
        else:
            self.end_of_file()

    def get_value(self, value):
        if value not in "TXEOF" and not value.isdigit():
            _ = "Invalid R/N (Register/Number): {}".format(value)
            raise RuntimeError(_)
        if value == "T":
            return self.state.T
        if value == "X":
            return self.state.X
        if value == "EOF":
            return self.state.eof
        return int(value)

    def end_of_file(self):
        if self.state.location > self.state.eof:
            self.state.store("T", 1)
        else:
            self.state.store("T", 0)

    def factory(self):
        operator_funcs = {">": ops.gt, "<": ops.lt, "=": ops.eq}
        operator = self.op
        for symbol, function in operator_funcs.items():
            if operator == symbol:
                true = function(self.value_1, self.register)
                self.state.store("T", 1 if true else 0)
                break


class File:
    """ Execute EXA file statements.
    """

    def __init__(self, *args):
        self.function, self.args, self.state = args
        if self.args:
            self.value = self.args[0]
        self.factory()

    def factory(self):
        functions = {
            "GRAB": self.grab,
            "SEEK": self.seek,
            "VOID": self.void,
            "FILE": self.set_id,
            "DROP": self.drop,
        }
        for function, method in functions.items():
            if function == self.function:
                method()
                break

    def grab(self):
        self.state.store("file_id", self.value)
        file = FILES[self.value]
        if file:
            self.state.store("EOF", len(file))
        self.state.store("held", 1)

    def set_id(self):
        self.state.store(self.value, self.state.file_id)

    def void(self):
        FILES[self.state.file_id].remove(self.state.F)

    def seek(self):
        idx = int(self.value)
        if idx > self.state.eof:
            self.state.store("location", self.state.eof)
        elif idx < 0:
            self.state.store("location", 0)
        else:
            self.state.registry["location"] += self.value

    def drop(self):
        self.state.store("F", 0)
        self.state.store("location", 0)
        self.state.store("held", 0)


class State:
    """ Return the state of the EXA registers
    """

    def __init__(self):

        self.registry = {
            "T": 0,
            "X": 0,
            "F": 0,
            "EOF": 0,
            "file_id": None,
            "held": 0,
            "location": 0,
        }

    def __str__(self):
        return "Registers: T = {:3,} | X = {:3,}".format(self.T, self.X)

    @property
    def location(self):
        return self.registry["location"]

    @property
    def T(self):
        return self.registry["T"]

    @property
    def X(self):
        return self.registry["X"]

    @property
    def F(self):
        if not self.held:
            raise F_RegisterAccessError(
                "Atempting to access F register while no file held"
            )
        return self.registry["F"]

    @property
    def eof(self):
        return self.registry["EOF"]

    @property
    def file_id(self):
        return self.registry["file_id"]

    @property
    def held(self):
        return self.registry["held"]

    def store(self, register, value):
        self.registry[register] = value

    def read(self):
        if not self.held:
            raise F_RegisterAccessError("Atempting to read while no file held")
        self.store("F", FILES[self.file_id][self.location])

    def write(self):
        if not self.held:
            raise F_RegisterAccessError("Atempting to write while no file held")
        FILES[self.file_id].insert(self.location, self.F)


class Jumper:
    """ Execute EXA jump statement.
    """

    def jump(self, label):
        index = self.marks[label]
        self.idx = index

    def tjmp(self, label):
        index = self.marks[label]
        if self.state.T:
            self.idx = index
        else:
            pass

    def fjmp(self, label):
        index = self.marks[label]
        if self.state.T:
            pass
        else:
            self.idx = index


class Interpreter(Jumper):
    """ Parse, validate, pre-process, and deligate EXA commands
    """

    def __init__(self, *args, **kwd):
        file = args[0]
        self.verbose = kwd["verbose"]
        self.state = State()
        self.marks = {}
        self.data = [
            (line_number, line.replace("\n", ""))
            for line_number, line in enumerate(file)
        ]
        self.idx = 0
        self._functions = {
            # operations
            "ADDI": Ops,
            "COPY": Ops,
            "MULI": Ops,
            "SUBI": Ops,
            "MODI": Ops,
            "DIVI": Ops,
            # Tests
            "TEST": Test,
            # Jumps
            "JUMP": self.jump,
            "TJMP": self.tjmp,
            "FJMP": self.fjmp,
            # File handling
            "GRAB": File,
            "FILE": File,
            "SEEK": File,
            "VOID": File,
            "DROP": File,
            # EXA marks and comments
            "NOTE": None,
            "MARK": None,
        }
        self.operations = self.get_slice(b=6)
        self.jumps = self.get_slice(7, -7)
        self.code = self.parse()

    def get_slice(self, a=0, b=0):
        return [function for function in self._functions.keys()][a:b]

    def parse(self):
        code = []
        for index, statement in self.data:
            line = statement.split()
            function, args = line[0], line[1:]

            if "MARK" == function:
                label = args[0]
                if label in self.marks:
                    raise RuntimeError("Label {}, already in use".format(label))
                self.marks[label] = index

            if function not in self._functions:
                raise RuntimeError(
                    "Invalid function: {} in line {}. {}".format(
                        function, index, statement
                    )
                )

            if function in self.operations and args[-1] not in "TXF":
                raise RuntimeError("Invalid Register: {}".format(args[-1]))

            code.append([index, function, args])
        return code

    def run(self):
        while True:
            if self.idx >= len(self.code):
                break
            line = self.code[self.idx]
            exa_function = line[1]
            if self.verbose:
                print(self.state, "\n")
                print("FUNCTION:", exa_function)
                print(
                    " ".join(
                        "{}".format(item)
                        if not isinstance(item, list)
                        else " ".join(item for item in item)
                        for item in line
                    )
                )
            args = line[2]
            for function, method in self._functions.items():
                if function == "MARK" or function == "NOTE":
                    continue

                if exa_function == function == "TEST":
                    method(exa_function, args, self._functions, self.state)
                    break

                elif exa_function == function and exa_function in self.jumps:
                    label = args[0]
                    method(label)
                    break

                elif exa_function == function:
                    method(exa_function, args, self.state)
                    break

            self.idx += 1

        return self.state


if __name__ == "__main__":

    files = [file for file in os.listdir() if file.endswith(".exa")]
    files.sort()

    for idx, file in enumerate(files):
        print(idx + 1, file)

    number = input("\nFile? -> ")

    try:
        menu_idx = int(number) - 1
        file_name = files[menu_idx]
        file = load(file_name)
        instance = Interpreter(file, verbose=0)
        result = instance.run()
        if menu_idx + 1 in (5, 6):
            pprint(FILES)
        print(result)
    except (ValueError, IndexError):
        print("Invalid choice", number)
