"""This file is part of nand2tetris, as taught in The Hebrew University,
and was written by Aviv Yaish according to the specifications given in  
https://www.nand2tetris.org (Shimon Schocken and Noam Nisan, 2017)
and as allowed by the Creative Common Attribution-NonCommercial-ShareAlike 3.0 
Unported License (https://creativecommons.org/licenses/by-nc-sa/3.0/).
"""
KEYWORDS = ['class', 'constructor', 'function', 'method', 'field',
            'static', 'var', 'int', 'char', 'boolean', 'void', 'true',
            'false', 'null', 'this', 'let', 'do', 'if', 'else',
            'while', 'return']
SYMBOLS = ['{', '}', '(', ')', '[', ']', '.', ',', ';', '+', '-', '*', '/',
           '&', '|', '<', '>', '=', '~', '#', '^']

import typing
import re


class JackTokenizer:
    """Removes all comments from the input stream and breaks it
    into Jack language tokens, as specified by the Jack grammar.
    """

    def __init__(self, input_stream: typing.TextIO) -> None:
        """Opens the input stream and gets ready to tokenize it.

        Args:
            input_stream (typing.TextIO): input stream.
        """
        self.all_tokens = []
        self.input_lines = input_stream.read().splitlines()
        # get all tokens (broken down into atoms)
        symReg = '[' + re.escape('|'.join(SYMBOLS)) + ']'
        keyReg = '(?!\w)|'.join(KEYWORDS) + '(?!\w)'
        intReg = r'\d+'
        idReg = r'[\w]+'
        strReg = r'"[^"\n]*"'
        self.pattern = re.compile(
            keyReg + '|' + symReg + '|' + intReg + '|' + strReg + '|' + idReg)
        self.all_tokens = self.tokenize()
        self.cur_ind = 0
        if len(self.all_tokens) != 0:
            self.cur_token = self.all_tokens[0]

    def tokenize(self):
        """
        A method that enables getting all relevant tokens per line,
        and returns all the tokens needed.
        """
        in_comment = False
        for line in self.input_lines:
            # avoiding empty lines and comments
            line = line.strip()
            line, in_comment = self.ignore_comments(line, in_comment)
            if not line:
                continue
            # append all atomized tokens
            self.all_tokens += self.tokenize_line(line)
        return self.all_tokens

    def has_more_tokens(self) -> bool:
        """Do we have more tokens in the input?

        Returns:
            bool: True if there are more tokens, False otherwise.
        """
        return self.cur_ind + 1 < len(self.all_tokens)

    def tokenize_line(self, line):
        """
        This method allows parsing the current line into chunks
        divided by space char, and later to be broken down into basic atoms
        thanks to the split_expression() method.
        """
        tokenized_line = []
        parsed_line = self.split_line(line)
        for chunk in parsed_line:
            if self.check_chunk(chunk) == "STR_CONST":
                tokenized_line.append(chunk)
                continue
            tokenized_line += self.split_to_atoms(chunk)
        return tokenized_line

    def split_to_atoms(self, cur_string):
        """
        This method allows breaking each chunk into identified atoms.
        """
        token_atoms = []
        j = 0
        for i in range(len(cur_string)):
            if cur_string[i] in SYMBOLS:
                if i != j: token_atoms.append(cur_string[j:i])
                token_atoms.append(cur_string[i])
                if i < len(cur_string): j = i + 1
        if cur_string[j:] != "":
            token_atoms.append(cur_string[j:])
        return token_atoms

    def advance(self) -> None:
        """Gets the next token from the input and makes it the current token.
        This method should be called if has_more_tokens() is true.
        Initially there is no current token.
        """
        # Your code goes here!
        if self.has_more_tokens():
            self.cur_ind += 1
            self.cur_token = self.all_tokens[self.cur_ind]
            self.token_type()

    def token_type(self) -> str:
        """
        Returns:
            str: the type of the current token, can be
            "KEYWORD", "SYMBOL", "IDENTIFIER", "INT_CONST", "STRING_CONST"
        """
        if self.cur_token in KEYWORDS:
            return "KEYWORD"
        elif self.cur_token in SYMBOLS:
            return "SYMBOL"
        else:
            return self.check_chunk(self.cur_token)

    def check_chunk(self, chunk):
        # returns INT_CONST, STR_CONST, IDENTIFIER
        # check if the chunk is an integer constant:
        if chunk.isdigit():
            return "INT_CONST"
        # check if the chunk is a string
        q = re.match('(".+")', chunk)
        if q:
            return "STR_CONST"
        id = re.match('(\D\w*)', chunk)
        if id:
            return "IDENTIFIER"

    def keyword(self) -> str:
        """
        Returns:
            str: the keyword which is the current token.
            Should be called only when token_type() is "KEYWORD".
            Can return "CLASS", "METHOD", "FUNCTION", "CONSTRUCTOR", "INT", 
            "BOOLEAN", "CHAR", "VOID", "VAR", "STATIC", "FIELD", "LET", "DO", 
            "IF", "ELSE", "WHILE", "RETURN", "TRUE", "FALSE", "NULL", "THIS"
        """
        return self.cur_token.upper()

    def symbol(self) -> str:
        """
        Returns:
            str: the character which is the current token.
            Should be called only when token_type() is "SYMBOL".
        """

        return self.cur_token

    def identifier(self) -> str:
        """
        Returns:
            str: the identifier which is the current token.
            Should be called only when token_type() is "IDENTIFIER".
        """
        return self.cur_token

    def int_val(self) -> int:
        """
        Returns:
            str: the integer value of the current token.
            Should be called only when token_type() is "INT_CONST".
        """
        return self.cur_token

    def string_val(self) -> str:
        """
        Returns:
            str: the string value of the current token, without the double 
            quotes. Should be called only when token_type() is "STRING_CONST".
        """
        return self.cur_token

    def split_line(self, line):
        """
        Gets the line from the given pattern.
        """
        return self.pattern.findall(line)

    def ignore_comments(self, line, in_comment):
        if not line or line.startswith('//'):  # empty line or inline comment
            return None, in_comment
        if in_comment:  # use flag
            if '*/' in line:
                line = re.split('\*\/', line)[1]
                in_comment = False
            else:
                return None, True
        if '//' in line:  # // comment to end of line.
            line = re.split('//', line)[0]
        if '/*' in line:  # /* comment until closing */ and /** API comments */
            if '*/' in line:
                line = re.sub(re.compile("/\*.*?\*/", re.DOTALL), "", line)
            else:
                line = re.split('\/\*+', line)[0]
                in_comment = True
        return line, in_comment
