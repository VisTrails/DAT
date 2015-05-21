import re
from tdparser import Lexer, Token, LexerError, Error

from dat import variable_format
from dat.utils import iswhitespace

from dat.operations import InvalidOperation


SYMBOL = 1
NUMBER = 2
STRING = 3
OP = 4


class Symbol(Token):
    regexp = variable_format

    def __init__(self, text):
        self.value = text
        Token.__init__(self, text)

    def nud(self, context):
        return (SYMBOL, self.value)


class Number(Token):
    regexp = r'\d+(?:\.\d+)?'

    def __init__(self, text):
        self.value = float(text)
        Token.__init__(self, text)

    def nud(self, context):
        return (NUMBER, self.value)


class String(Token):
    regexp = r'"(?:[^\\"]|\\\\|\\")*"'

    def __init__(self, text):
        self.value = text[1:-1].replace('\\"', '"').replace('\\\\', '\\')

    def nud(self, context):
        return (STRING, self.value)


class Addition(Token):
    regexp = r'\+'
    lbp = 20  # Precedence

    def led(self, left, context):
        right = context.expression(self.lbp)
        return (OP, '+', left, right)


class Substraction(Token):
    regexp = r'-'
    lbp = 20  # Precedence: same as addition

    def led(self, left, context):
        # Binary operator
        right = context.expression(self.lbp)
        return (OP, '-', left, right)

    def nud(self, context):
        # Unary operator
        expr = context.expression(self.lbp)
        if expr[0] == NUMBER:
            return (NUMBER, -expr[1])
        else:
            return (OP, '_', expr)


class Multiplication(Token):
    regexp = r'\*'
    lbp = 30  # Precedence: higher than addition

    def led(self, left, context):
        right = context.expression(self.lbp)
        return (OP, '*', left, right)


class Division(Token):
    regexp = r'/'
    lbp = 30  # Precedence: same as multiplication

    def led(self, left, context):
        right = context.expression(self.lbp)
        return (OP, '/', left, right)


class LeftParen(Token):
    regexp = r'\('
    lbp = 100  # Left binding power: highest
    rbp = 10  # Right binding power: lowest

    def led(self, left, context):
        # Binary operator: corresponds to the function call contruct, as in
        # 2 * abc(7, 31) + 18
        params = []
        if left[0] != SYMBOL:
            raise InvalidOperation("Function call syntax only allowed on "
                                   "symbols")
        if not isinstance(context.current_token, RightParen):
            while True:
                params.append(context.expression(self.rbp))
                if not isinstance(context.current_token, Comma):
                    break
                context.consume(expect_class=Comma)
        context.consume(RightParen)
        return (OP, left[1]) + tuple(params)

    def nud(self, context):
        # Unary operator: corresponds to the parenthesized construct, as in
        # 2 * (3 + 1)

        # Fetch the next expression
        expr = context.expression()
        # Eat the next token, that should be a ')'
        context.consume(expect_class=RightParen)
        return expr


class RightParen(Token):
    regexp = r'\)'


class Comma(Token):
    regexp = r','


lexer = Lexer()
lexer.register_tokens(
    Symbol, Number, String,
    Addition, Substraction, Multiplication, Division,
    LeftParen, RightParen, Comma)


_variable_format = re.compile('^' + variable_format + '$')


def parse_expression(expression):
    equal = expression.find('=')
    if equal == -1:
        raise InvalidOperation("Missing target variable name",
                               "new_var = %s" % expression,
                               (0, 7))
    else:
        target = expression[:equal].strip()
        if not _variable_format.match(target):
            right = equal
            if right > 0 and expression[right - 1] == ' ':
                right -= 1
            if iswhitespace(expression[0:right]):
                raise InvalidOperation("Missing target variable name",
                                       "new_var %s" % expression.lstrip(),
                                       (0, 7))
            else:
                raise InvalidOperation("Invalid target variable name",
                                       None,
                                       (0, right))
        expression = expression[equal + 1:]
    try:
        return target, lexer.parse(expression)
    except LexerError, e:
        raise InvalidOperation("Error while parsing expression",
                               None,
                               select=(equal + 1 + e.position,
                                       equal + 1 + len(expression)))
    except Error:
        raise InvalidOperation("Error while parsing expression")
