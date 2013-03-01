from tdparser import Lexer, Token, ParserError


class InvalidExpression(ValueError):
    """Error while parsing an expression.
    """
    def __init__(self, *args):
        if len(args) >= 2:
            self.pos = args[1]
        ValueError.__init__(self, *args)


SYMBOL = 1
NUMBER = 2
OP = 3
ASSIGN = 4


class Symbol(Token):
    regexp = r'[A-Za-z_$@][A-Za-z_$@0-9]*'
    def __init__(self, text):
        self.value = text

    def nud(self, context):
        return (SYMBOL, self.value)


class Integer(Token):
    regexp = r'\d+'

    def __init__(self, text):
        self.value = int(text)

    def nud(self, context):
        return (NUMBER, self.value)


class Addition(Token):
    regexp = r'\+'
    lbp = 20 # Precedence

    def led(self, left, context):
        right = context.expression(self.lbp)
        return (OP, '+', left, right)


class Substraction(Token):
    regexp = r'-'
    lbp = 20 # Precedence: same as addition

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
    lbp = 30 # Precedence: higher than addition

    def led(self, left, context):
        right = context.expression(self.lbp)
        return (OP, '*', left, right)


class Division(Token):
    regexp = r'/'
    lbp = 30 # Precedence: same as multiplication

    def led(self, left, context):
        right = context.expression(self.lbp)
        return (OP, '/', left, right)


class Equal(Token):
    regexp = r'='
    lbp = 10 # Precedence: lowest

    def led(self, left, context):
        right = context.expression(self.lbp)
        return (ASSIGN, left, right)


lexer = Lexer(with_parens=True)
lexer.register_tokens(
        Symbol, Integer,
        Addition, Substraction, Multiplication, Division,
        Equal)


def parse_expression(expression):
    try:
        tree = lexer.parse(expression)
    except (ParserError, ValueError):
        raise InvalidExpression("Error while parsing expression")
    if tree[0] == ASSIGN:
        if tree[1][0] == SYMBOL:
            return tree[1][1], tree[2]
        else:
            raise InvalidExpression("Assignment to non-symbol")
    else:
        return None, tree


def perform_operation(controller, expression):
    """Perform a variable operation from the given string.
    """
    # First, parse the expressions
    target, expr_tree = parse_expression(expression)
