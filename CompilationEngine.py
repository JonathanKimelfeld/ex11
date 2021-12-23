"""This file is part of nand2tetris, as taught in The Hebrew University,
and was written by Aviv Yaish according to the specifications given in  
https://www.nand2tetris.org (Shimon Schocken and Noam Nisan, 2017)
and as allowed by the Creative Common Attribution-NonCommercial-ShareAlike 3.0 
Unported License (https://creativecommons.org/licenses/by-nc-sa/3.0/).
"""
import typing
from SymbolTable import *
from VMWriter import *

# ------------------------ DICTIONARIES -----------------------#

OP = {"+", "-", "*", "/", "&", "|", ">", "<", "="}
UNARY_OP = {"-", "~"}
STATEMENTS = {"let", "if", "while", "do", "return"}
special_sym = {'<': "&lt;", '>': "&gt;", '"': "&quot;", '&': "&amp;"}

# --------------------------- CONSTANTS ---------------------------#

SYMBOL = "symbol"
KEYWORD = "keyword"
IDENTIFIER = "identifier"
CLASS_VAR = "classVarDec"


class CompilationEngine:
    """Gets input from a JackTokenizer.py and emits its parsed structure into an
    output stream.
    """

    def __init__(self, jack_tokenizer, output_stream) -> None:
        """
        Creates a new compilation engine with the given input and output. The
        next routine called must be compileClass()
        :param input_stream: The input stream.
        :param output_stream: The output stream.
        """
        self.writer = VMWriter(output_stream)
        self.tokenizer = jack_tokenizer
        self.symbol_table = SymbolTable()
        self.class_name = ""

    def get_cur_token(self):
        return self.tokenizer.cur_token

    def compile_class(self) -> None:
        """Compiles a complete class."""
        self.tokenizer.advance()  # "class" # skip
        self.class_name = self.get_cur_token()
        self.tokenizer.advance()  # { # skip
        while self.get_cur_token() in {"field", "static"}:
            self.compile_class_var_dec()
        while self.get_cur_token() in {"constructor", "method", "function"}:
            self.compile_subroutine()
        self.tokenizer.advance()  # } # skip

    def compile_class_var_dec(self) -> None:
        """Compiles a static declaration or a field declaration."""
        field_kind = self.get_cur_token()  # kind
        field_type = self.get_cur_token()  # type
        field_name = self.get_cur_token()  # name
        self.symbol_table.define(field_name, field_type, field_kind)

    def compile_subroutine(self) -> None:
        """Compiles a complete method, function, or constructor."""
        is_void = False
        self.symbol_table.start_subroutine()
        function_type = self.get_cur_token()
        if self.get_cur_token() == "void":
            is_void = True
        function_name = self.class_name + "." + self.get_cur_token()  # name
        self.tokenizer.advance()  # ( # skip
        self.skip_params()  # skip all params - not relevant here
        self.tokenizer.advance()  # ) # skip
        self.tokenizer.advance()  # { # skip
        while self.get_cur_token() == "var":
            self.compile_var_dec()  # get number of locals
        n_locals = self.symbol_table.count_var
        self.writer.write_function(function_name, n_locals)
        if function_type == "constructor":
            self.alloc_constructor()  # num of fields extra space for "this"
        elif function_type == "method":
            self.alloc_method()  # should alloc 1 extra local space for "this"
        self.compile_statements()
        if is_void:
            self.writer.write_push("constant", 0)
        else:
            pass  # TODO push return value from body? "return something"
        self.writer.write_return()
        self.tokenizer.advance()  # } # skip

    def compile_subroutine_call(self, flag=True):
        """
        Compiles a subroutine call, flag allows to add another subroutine
        name in case needed.
        """
        if flag:
            self.wrap_tag(IDENTIFIER)  # Name (class\var\subroutine)
        if self.get_cur_token() == ".":
            self.tokenizer.advance()  # . skip the dot
            function_name = self.get_cur_token()  # subroutineName
        self.tokenizer.advance()  # skip (
        n_args = self.compile_expression_list()
        self.tokenizer.advance()  # skip )
        self.writer.write_call(function_name, n_args)  # TODO

    def compile_var_dec(self) -> None:
        """Compiles a var declaration."""
        self.tokenizer.advance()  # always var
        var_type = self.get_cur_token()  # type
        var_name = self.get_cur_token()  # name
        self.symbol_table.define(var_name, var_type, "VAR")
        while self.get_cur_token() != ';':
            self.tokenizer.advance()  # , sym skip
            var_name = self.get_cur_token()  # name
            self.symbol_table.define(var_name, var_type, "VAR")
        self.tokenizer.advance()  # ;

    def compile_statements(self) -> None:
        """Compiles a sequence of statements, not including the enclosing
        "{}".
        """
        while self.get_cur_token() in STATEMENTS:
            if self.get_cur_token() == "let":
                self.compile_let()
            elif self.get_cur_token() == "if":
                self.compile_if()
            elif self.get_cur_token() == "while":
                self.compile_while()
            elif self.get_cur_token() == "do":
                self.compile_do()
            elif self.get_cur_token() == "return":
                self.compile_return()

    def compile_do(self) -> None:
        """Compiles a do statement."""
        self.print_open_tag("doStatement")
        self.wrap_tag(KEYWORD)  # do
        self.compile_subroutine_call()
        self.wrap_tag(SYMBOL)  # ;
        self.print_close_tag("doStatement")

    def compile_let(self) -> None:
        """Compiles a let statement."""
        self.print_open_tag("letStatement")
        self.wrap_tag(KEYWORD)  # let
        self.wrap_tag(IDENTIFIER)  # varName
        if self.get_cur_token() == "[":
            self.wrap_tag(SYMBOL)
            self.compile_expression()
            self.wrap_tag(SYMBOL)
        self.wrap_tag(SYMBOL)  # compile =
        self.compile_expression()  # set val
        self.wrap_tag(SYMBOL)  # ;
        self.print_close_tag("letStatement")

    def compile_while(self, flag=True) -> None:
        """Compiles a while statement."""
        if flag:
            self.print_open_tag("whileStatement")
        self.wrap_tag(KEYWORD)  # while
        self.wrap_tag(SYMBOL)  # (
        self.compile_expression()
        self.wrap_tag(SYMBOL)  # )
        self.wrap_tag(SYMBOL)  # {
        self.compile_statements()
        self.wrap_tag(SYMBOL)  # }
        if flag:
            self.print_close_tag("whileStatement")

    def compile_return(self) -> None:
        """Compiles a return statement."""
        self.print_open_tag("returnStatement")
        self.wrap_tag(KEYWORD)  # return
        if self.get_cur_token() != ';':
            self.compile_expression()
        self.wrap_tag(SYMBOL)  # ;
        self.print_close_tag("returnStatement")

    def compile_if(self) -> None:
        """Compiles a if statement, possibly with a trailing else clause."""
        self.print_open_tag("ifStatement")
        self.compile_while(False)
        if self.get_cur_token() == "else":
            self.wrap_tag(KEYWORD)  # else
            self.wrap_tag(SYMBOL)  # {
            self.compile_statements()
            self.wrap_tag(SYMBOL)  # }
        self.print_close_tag("ifStatement")

    def compile_expression(self) -> None:
        """Compiles an expression."""
        self.print_open_tag("expression")
        self.compile_term()
        while self.get_cur_token() in OP:
            self.wrap_tag(SYMBOL)  # op
            self.compile_term()
        self.print_close_tag("expression")

    def compile_term(self) -> None:
        """Compiles a term.
        This routine is faced with a slight difficulty when
        trying to decide between some of the alternative parsing rules.
        Specifically, if the current token is an identifier, the routing must
        distinguish between a variable, an array entry, and a subroutine call.
        A single look-ahead token, which may be one of "[", "(", or "." suffices
        to distinguish between the three possibilities. Any other token is not
        part of this term and should not be advanced over.
        """
        self.print_open_tag("term")
        if self.tokenizer.token_type() == "INT_CONST":
            self.wrap_tag("integerConstant")  # integerConstant
        elif self.tokenizer.token_type() == "STR_CONST":
            self.wrap_tag("stringConstant")  # StringConstant
        elif self.tokenizer.token_type() == "KEYWORD":
            self.wrap_tag(KEYWORD)  # KeywordConstant
        elif self.tokenizer.token_type() == "IDENTIFIER":
            self.wrap_tag(IDENTIFIER)  # varName
            if self.get_cur_token() in {".", "("}:  # call subtoutine
                self.compile_subroutine_call(False)
            if self.get_cur_token() == "[":
                self.wrap_tag(SYMBOL)
                self.compile_expression()
                self.wrap_tag(SYMBOL)
        elif self.get_cur_token() == "(":
            self.wrap_tag(SYMBOL)  # (
            self.compile_expression()
            self.wrap_tag(SYMBOL)  # )
        elif self.get_cur_token() in UNARY_OP:
            self.wrap_tag(SYMBOL)  # op
            self.compile_term()
        self.print_close_tag("term")

    def compile_expression_list(self) -> None:
        """Compiles a (possibly empty) comma-separated list of expressions."""
        self.print_open_tag("expressionList")
        if self.get_cur_token() != ")":
            self.compile_expression()
            while self.get_cur_token() == ',':
                self.wrap_tag(SYMBOL)  # ,
                self.compile_expression()
        self.print_close_tag("expressionList")

    def skip_params(self):
        while self.get_cur_token() != "(":
            self.tokenizer.advance()

    def alloc_constructor(self):
        fields_num = self.symbol_table.count_field + \
                     self.symbol_table.count_static
        self.writer.write_push("constant", fields_num)
        self.writer.write_call("Memory.alloc", 1)
        self.writer.write_pop("pointer", 0)

    def alloc_method(self):
        self.writer.write_push("argument", 0)
        self.writer.write_pop("pointer", 0)


# -------------------------------------------------------------------- #
# def print_open_tag(self, tag):

#     """
#     A method which allows us to print the routine labels, and advances
#     to the next token.
#     """
#     self.output_file.write("<" + tag + ">" + "\n")

def print_close_tag(self, tag):
    """
    A method which allows us to print the routine labels, and advances
    to the next token.
    """
    self.output_file.write("</" + tag + ">" + "\n")


def wrap_tag(self, tag):
    """
    A method which allows us to print the routine labels, and advances
    to the next token.
    """
    token = self.get_cur_token()
    if token in special_sym:
        token = special_sym[token]
    token = token.replace("\"", "")
    self.output_file.write(
        "<" + tag + "> " + token + " </" + tag + ">" + "\n")
    self.tokenizer.advance()

#
# def compile_parameter_list(self) -> int:
#     """Compiles a (possibly empty) parameter list, not including the
#     enclosing "()".
#     """
#     n_params = 0
#     if self.get_cur_token() != ")":
#         param_type = self.get_cur_token()  # type
#         param_name = self.get_cur_token()  # param name
#         n_params += 1
#         self.symbol_table.define(param_name, param_type, "ARG")
#         while self.get_cur_token() == ',':
#             self.tokenizer.advance()  # ,
#             param_type = self.get_cur_token()  # type
#             param_name = self.get_cur_token()  # param name
#             n_params += 1
#             self.symbol_table.define(param_name, param_type, "ARG")
#     return n_params
