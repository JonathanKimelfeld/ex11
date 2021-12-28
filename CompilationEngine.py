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

OP = {"+": "add", "-": "sub", "*": "call Math.multiply 2",
      "/": "call Math.divide 2", '<': "lt", '>': "gt",
      '"': "&quot;", '&': "and", '=': "eq"}
#       "|", "="
UNARY_OP = {'-': "neg", '~': "not"}
STATEMENTS = {"let", "if", "while", "do", "return"}
# special_sym = {}

# --------------------------- CONSTANTS ---------------------------#
STATIC = "static"
FIELD = "field"
SYMBOL = "symbol"
KEYWORD = "keyword"
IDENTIFIER = "identifier"
CLASS_VAR = "classVarDec"
THIS = ""  # TODO: what should we send in "this"?


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
        self.label_counter = 0

    def get_cur_token(self, advance=False):
        cur_token = self.tokenizer.cur_token
        if advance:
            self.tokenizer.advance()
        return cur_token

    def compile_class(self) -> None:
        """Compiles a complete class."""
        self.tokenizer.advance()  # "class" # skip
        self.class_name = self.get_cur_token(True)
        self.tokenizer.advance()  # { # skip
        while self.get_cur_token() in {"field", "static"}:
            self.compile_class_var_dec()
        while self.get_cur_token() in {"constructor", "method", "function"}:
            self.compile_subroutine()
        self.tokenizer.advance()  # } # skip

    def compile_class_var_dec(self) -> None:
        """Compiles a static declaration or a field declaration."""
        field_kind = self.get_cur_token(True)  # kind
        field_type = self.get_cur_token(True)  # type
        field_name = self.get_cur_token(True)  # name
        self.symbol_table.define(field_name, field_type, field_kind)
        while self.get_cur_token() != ';':
            self.tokenizer.advance()  # , sym skip
            field_name = self.get_cur_token(True)  # name
            self.symbol_table.define(field_name, field_type, field_kind)
        self.tokenizer.advance()  # ;

    def compile_subroutine(self) -> None:
        """Compiles a complete method, function, or constructor."""
        self.symbol_table.start_subroutine()
        function_type = self.get_cur_token(True)
        self.tokenizer.advance()  # void
        function_name = self.class_name + "." + self.get_cur_token(
            True)  # name
        self.tokenizer.advance()  # ( # skip
        # self.compile_subroutine_call # TODO
        if self.get_cur_token() == ")":
            self.tokenizer.advance()  # ) # skip, no params given
        else:
            self.compile_parameter_list()
            self.tokenizer.advance()  # ) # skip, finished getting params
        self.tokenizer.advance()  # { # skip
        while self.get_cur_token() == "var":
            self.compile_var_dec()  # get number of locals
        n_locals = self.symbol_table.count_var
        self.writer.write_function(function_name, n_locals)
        if function_type == "constructor":
            self.alloc_constructor()  # num of fields extra space for "this"
        elif function_type == "method":
            self.alloc_method()  # should alloc 1 extra local space for "this": line below
            # self.symbol_table.define(THIS, self.class_name, ARG, 0)
        self.compile_statements()
        self.tokenizer.advance()  # } skip

    def compile_subroutine_call(self, sub_name=None):
        """
        Compiles a subroutine call, flag allows to add another subroutine
        name in case needed.
        """
        method_args = 0
        if sub_name:
            func_name = sub_name
        else:
            func_name = self.get_cur_token(True)
        if self.get_cur_token() == "(":
            func_name = self.class_name + "." + func_name
            self.writer.write_push("pointer", 0)  # push this as first arg
            method_args += 1
        elif self.get_cur_token() == ".":
            if self.symbol_table.does_exist(func_name):  # object method (b.foo())
                segment, ind = self.get_var_from_table(func_name)
                self.writer.write_push(segment, ind)  # push object as first arg
                func_name = self.symbol_table.type_of(func_name)
                method_args += 1
            func_name += self.get_cur_token(True)  # . add dot
            func_name += self.get_cur_token(True)  # subroutineName
        self.tokenizer.advance()  # skip (
        n_args = self.compile_expression_list() + method_args
        self.tokenizer.advance()  # skip )
        self.writer.write_call(func_name, n_args)

    def compile_var_dec(self) -> None:
        """Compiles a var declaration."""
        self.tokenizer.advance()  # always var
        var_type = self.get_cur_token(True)  # type
        var_name = self.get_cur_token(True)  # name
        self.symbol_table.define(var_name, var_type, VAR)
        while self.get_cur_token() != ';':
            self.tokenizer.advance()  # , sym skip
            var_name = self.get_cur_token(True)  # name
            self.symbol_table.define(var_name, var_type, VAR)
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

    def get_var_from_table(self, var):
        kind = self.symbol_table.kind_of(var)
        ind = self.symbol_table.index_of(var)
        if kind == VAR:
            segment = "local"
        elif kind == ARG:
            segment = "argument"
        elif kind == STATIC:
            segment = "static"
        elif kind == FIELD:
            segment = "this"
        return segment, ind

    def compile_do(self) -> None:
        """Compiles a do statement."""
        self.tokenizer.advance()  # do
        self.compile_subroutine_call()
        self.tokenizer.advance()  # ;
        self.writer.write_pop("temp", 0)

    def compile_let(self) -> None:
        """Compiles a let statement."""
        self.tokenizer.advance()  # (LET)
        var_name = self.get_cur_token(True)  # varName
        # if self.get_cur_token() == "[": # arrays #TODO
        #     # self.wrap_tag(SYMBOL)
        #     self.compile_expression() # put val on the stack
        #     # self.wrap_tag(SYMBOL)
        self.tokenizer.advance()  # skip (=)
        self.compile_expression()  # set val
        self.tokenizer.advance()  # skip (;)
        segment, ind = self.get_var_from_table(var_name)
        self.writer.write_pop(segment, ind)

    def compile_while(self, flag=True) -> None:
        """Compiles a while statement."""
        label_loop = "WHILE_EXP" + str(self.label_counter)
        label_break = "WHILE_END" + str(self.label_counter)
        self.label_counter += 1
        self.writer.write_label(label_loop)
        self.tokenizer.advance()  # "while"
        self.tokenizer.advance()  # (
        self.compile_expression()
        self.tokenizer.advance()  # )
        self.writer.write_arithmetic("not")
        self.writer.write_if(label_break)
        self.tokenizer.advance()  # {
        self.compile_statements()
        self.writer.write_goto(label_loop)
        self.writer.write_label(label_break)
        self.tokenizer.advance()  # }

    def compile_return(self) -> None:
        """Compiles a return statement."""
        self.tokenizer.advance()  # "return"
        if self.get_cur_token() != ';':  # not void
            self.compile_expression()
        else:
            self.writer.write_push("constant", 0)
        self.writer.write_return()
        self.tokenizer.advance()  # ;

    def compile_if(self) -> None:
        """Compiles a if statement, possibly with a trailing else clause."""
        self.label_counter += 1
        self.tokenizer.advance()  # if
        self.tokenizer.advance()  # (
        self.compile_expression()
        self.tokenizer.advance()  # )
        self.tokenizer.advance()  # {
        self.writer.write_arithmetic("not")
        false_label = "IF_FALSE" + str(self.label_counter)
        end_label = "IF_END" + str(self.label_counter)
        self.writer.write_if(false_label)  # go to else block
        self.compile_statements()
        self.tokenizer.advance()  # }
        self.writer.write_goto(end_label)  # end true block
        self.writer.write_label(false_label)
        if self.get_cur_token() == "else":
            self.tokenizer.advance()  # "else"
            self.tokenizer.advance()  # {
            self.compile_statements()
            self.tokenizer.advance()  # }
        self.writer.write_label(end_label)

    def compile_expression(self) -> None:
        """Compiles an expression."""
        self.compile_term()
        while self.get_cur_token() in OP:
            op = OP[self.get_cur_token(True)]
            self.compile_term()
            self.writer.write_arithmetic(op)

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
        if self.tokenizer.token_type() == "INT_CONST":
            self.writer.write_push("constant",
                                   self.get_cur_token(True))  # intConstant
        elif self.tokenizer.token_type() == "STR_CONST":
            var_seg, var_ind = self.get_var_from_table(
                self.get_cur_token())  # TODO
            self.writer.write_push(var_seg, var_ind)  # # stringConstant
        elif self.tokenizer.token_type() == "KEYWORD":  # TODO
            self.writer.write_constant(self.get_cur_token(True))
        elif self.tokenizer.token_type() == "IDENTIFIER":
            temp = self.get_cur_token(True)
            if self.get_cur_token() in {".", "("}:  # call subroutine
                self.compile_subroutine_call(temp)
            # if self.get_cur_token() == "[":
            # self.wrap_tag(SYMBOL)
            # self.compile_expression()
            # self.wrap_tag(SYMBOL)
            else:
                var_seg, var_ind = self.get_var_from_table(temp)
                self.writer.write_push(var_seg, var_ind)  # var name
        elif self.get_cur_token() == "(":
            self.tokenizer.advance()  # (
            self.compile_expression()
            self.tokenizer.advance()  # )
        elif self.get_cur_token() in UNARY_OP.keys():
            op = UNARY_OP[self.get_cur_token(True)]
            self.compile_term()
            self.writer.write_arithmetic(op)

    def compile_expression_list(self) -> int:
        """Compiles a (possibly empty) comma-separated list of expressions."""
        exp_counter = 0
        if self.get_cur_token() != ")":
            self.compile_expression()
            exp_counter += 1
            while self.get_cur_token() == ',':
                self.tokenizer.advance()  # ,
                self.compile_expression()
                exp_counter += 1
        return exp_counter

    # def skip_params(self):
    #     while self.get_cur_token() != ")":
    #         self.tokenizer.advance()

    def alloc_constructor(self):
        fields_num = self.symbol_table.count_field + \
                     self.symbol_table.count_static
        self.writer.write_push("constant", fields_num)
        self.writer.write_call("Memory.alloc", 1)
        self.writer.write_pop("pointer", 0)  # update "this"

    def alloc_method(self):
        self.writer.write_push("argument", 0)
        self.writer.write_pop("pointer", 0)

    def compile_parameter_list(self) -> None:
        """Compiles a (possibly empty) parameter list, not including the
        enclosing "()".
        """
        n_params = 0
        if self.get_cur_token() != ")":
            param_type = self.get_cur_token(True)  # type
            param_name = self.get_cur_token(True)  # param name
            n_params += 1
            self.symbol_table.define(param_name, param_type, "ARG")
            while self.get_cur_token() == ',':
                self.tokenizer.advance()  # ,
                param_type = self.get_cur_token(True)  # type
                param_name = self.get_cur_token(True)  # param name
                n_params += 1
                self.symbol_table.define(param_name, param_type, "ARG")
        return

# -------------------------------------------------------------------- #
# def print_open_tag(self, tag):

#     """
#     A method which allows us to print the routine labels, and advances
#     to the next token.
#     """
#     self.output_file.write("<" + tag + ">" + "\n")

# def print_close_tag(self, tag):
#     """
#     A method which allows us to print the routine labels, and advances
#     to the next token.
#     """
#     self.output_file.write("</" + tag + ">" + "\n")
#

#
# def wrap_tag(self, tag):
#     """
#     A method which allows us to print the routine labels, and advances
#     to the next token.
#     """
#     token = self.get_cur_token()
#     if token in special_sym:
#         token = special_sym[token]
#     token = token.replace("\"", "")
#     self.output_file.write(
#         "<" + tag + "> " + token + " </" + tag + ">" + "\n")
#     self.tokenizer.advance()

#
