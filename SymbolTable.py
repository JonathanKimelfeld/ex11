"""This file is part of nand2tetris, as taught in The Hebrew University,
and was written by Aviv Yaish according to the specifications given in  
https://www.nand2tetris.org (Shimon Schocken and Noam Nisan, 2017)
and as allowed by the Creative Common Attribution-NonCommercial-ShareAlike 3.0 
Unported License (https://creativecommons.org/licenses/by-nc-sa/3.0/).
"""
import typing

ARG = "ARG"

# dictionary indices
TYPE = 0
KIND = 1
INDEX = 2


class SymbolTable:
    """A symbol table that associates names with information needed for Jack
    compilation: type, kind and running index. The symbol table has two nested
    scopes (class/subroutine).
    """

    def __init__(self) -> None:
        """Creates a new empty symbol table."""
        self.class_table = {}
        self.method_table = {}
        self.count_var = 0
        self.count_arg = 0
        self.count_field = 0
        self.count_static = 0

    def start_subroutine(self) -> None:
        """Starts a new subroutine scope (i.e., resets the subroutine's 
        symbol table).
        """
        self.method_table = {}
        # TODO: add this


    def define(self, name: str, type: str, kind: str) -> None:
        """Defines a new identifier of a given name, type and kind and assigns 
        it a running index. "STATIC" and "FIELD" identifiers have a class scope, 
        while "ARG" and "VAR" identifiers have a subroutine scope.

        Args:
            name (str): the name of the new identifier.
            type (str): the type of the new identifier.
            kind (str): the kind of the new identifier, can be:
            "STATIC", "FIELD", "ARG", "VAR".
        """
        cur_sym = (type, kind, self.var_count(kind))
        if kind in {"ARG", "VAR"}:
            self.method_table[name] = cur_sym #add identifier to table
            # and increment the relevant counter
        elif kind in {"STATIC", "FIELD"}:
            self.class_table[name] = cur_sym

    def var_count(self, kind: str) -> int:
        """
        Args:
            kind (str): can be "STATIC", "FIELD", "ARG", "VAR".

        Returns:
            int: the number of variables of the given kind already defined in 
            the current scope.
        """
        if kind == "VAR":
            return self.count_var
        elif kind == "ARG":
            return self.count_arg
        elif kind == "FIELD":
            return self.count_field
        elif kind == "STATIC":
            return self.count_static

    def kind_of(self, name: str) -> str:
        """
        Args:
            name (str): name of an identifier.

        Returns:
            str: the kind of the named identifier in the current scope, or None
            if the identifier is unknown in the current scope.
        """
        if name in self.method_table.keys():
            return self.method_table[name][KIND]
        else:  # TODO we assume hat name in self.class_table.keys(): - is this true?
            return self.class_table[name][KIND]

    def type_of(self, name: str) -> str:
        """
        Args:
            name (str):  name of an identifier.

        Returns:
            str: the type of the named identifier in the current scope.
        """
        if name in self.method_table.keys():
            return self.method_table[name][TYPE]
        else:  # TODO we assume hat name in self.class_table.keys(): - is this true?
            return self.class_table[name][TYPE]

    def index_of(self, name: str) -> int:
        """
        Args:
            name (str):  name of an identifier.

        Returns:
            int: the index assigned to the named identifier.
        """
        if name in self.method_table.keys():
            return self.method_table[name][INDEX]
        else:  # TODO we assume hat name in self.class_table.keys(): - is this true?
            return self.class_table[name][INDEX]
