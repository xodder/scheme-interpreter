class Environment:
    def __init__(self, parent):
        self._parent = parent
        self._frames = {}

    def add_variable(self, name, value):
        self._frames[name] = value

    def lookup_variable(self, name):
        if name in self._frames:
            return self._frames[name]
        elif self._parent:
            return self._parent.lookup_variable(name)
        else:
            eval_error('Undefined variable: %s' % (name))


class Procedure:
    def __init__(self, params, body, env):
        self._params = params
        self._env = env
        self._body = body

    def getParams(self):
        return self._params

    def getBody(self):
        return self._body

    def getEnvironment(self):
        return self._env


def main():
    eval_loop()


def eval_loop():
    genv = Environment(None)
    genv.add_variable('true', True)
    genv.add_variable('false', False)
    genv.add_variable('+', primitive_plus)
    genv.add_variable('-', primitive_minus)
    genv.add_variable('*', primitive_times)
    genv.add_variable('=', primitive_equals)
    genv.add_variable('<', primitive_less_than)
    genv.add_variable('>', primitive_greater_than)

    while True:
        inp = input('>')
        if inp == 'quit':
            break

        for expr in parse(inp):
            print(str(meval(expr, genv)))


# implements the evaluation rules for charme
def meval(expr, env):
    if is_primitive(expr):
        return eval_primitive(expr, env)
    elif is_if(expr):
        return eval_if(expr, env)
    elif is_definition(expr):
        return eval_definition(expr, env)
    elif is_name(expr):
        return eval_name(expr, env)
    elif is_lambda(expr):
        return eval_lambda(expr, env)
    elif is_application(expr):
        return eval_application(expr, env)
    else:
        error('Unknown expression type: ' + str(expr))


def is_primitive(expr):
    # a natural number or a primitive procedure [e.g +, -, *]
    return is_number(expr) or is_primitive_procedure(expr)


def is_number(expr):
    return isinstance(expr, str) and expr.isdigit()


def is_primitive_procedure(expr):
    return callable(expr)


# Charme Evaluation Rule 1: Primitive
# A primitive expression evaluates to its pre-defined value.
def eval_primitive(expr, env):
    if is_number(expr):
        return int(expr)
    else:
        # other primitives [primitive procedures, booleans] self-evaluate
        return expr


# defining primitive procedures evaluators
def primitive_plus(operands):
    if len(operands) == 0:
        return 0
    else:
        return operands[0] + primitive_plus(operands[1:])


def primitive_times(operands):
    if len(operands) == 0:
        return 1
    else:
        return operands[0] * primitive_times(operands[1:])


def primitive_minus(operands):
    if len(operands) == 1:
        return -1 * operands[0]
    elif len(operands) == 2:
        return operands[0] - operands[1]
    else:
        eval_error('- expects 1 or 2 operands, but got %s: %s' %
                   (len(operands), str(operands)))


def primitive_equals(operands):
    validate_primitive_operands('=', operands, 2)
    return operands[0] == operands[1]


def primitive_less_than(operands):
    validate_primitive_operands('<', operands, 2)
    return operands[0] < operands[1]


def primitive_greater_than(operands):
    validate_primitive_operands('>', operands, 2)
    return operands[0] > operands[1]


def validate_primitive_operands(target_primitive, operands, expected_length):
    if len(operands) != expected_length:
        eval_error(
            '%s expected %s operands, but got %s: %s' %
            (target_primitive, expected_length, len(operands), str(operands)))


def is_if(expr):
    # expr is a list and the first entry is an 'if' string
    return is_special_form(expr, 'if')


def eval_if(expr, env):
    # ['if', pred, consequent, alternate]
    if meval(expr[1], env) is not False:
        return meval(expr[2], env)
    else:
        return meval(expr[3], env)


def is_definition(expr):
    return is_special_form(expr, 'define')


def eval_definition(expr, env):
    name = expr[1]
    value = meval(expr[2], env)
    env.add_variable(name, value)


def is_name(expr):
    return isinstance(expr, str)


def eval_name(expr, env):
    return env.lookup_variable(expr)


def is_lambda(expr):
    return is_special_form(expr, 'lambda')


def eval_lambda(expr, env):
    return Procedure(expr[1], expr[2], env)


# requires all special forms checked first
def is_application(expr):
    return isinstance(expr, list)


def eval_application(expr, env):
    # evaluate all subexpressions of expr and then apply the result of
    # evaluating the first subexpression to the values of the
    # other subexpressions
    evaluated_subexprs = list(map(lambda subexpr: meval(subexpr, env), expr))
    return mapply(evaluated_subexprs[0], evaluated_subexprs[1:])


def mapply(procedure, operands):
    if is_primitive_procedure(procedure):
        return procedure(operands)
    elif isinstance(procedure, Procedure):
        # create a new environment with the procedure's environment as parent
        env = Environment(procedure.getEnvironment())
        params = procedure.getParams()

        # check for params mismatch
        if len(params) != len(operands):
            eval_error('Parameter length mismatch: %s given operands %s' %
                       (str(procedure), str(operands)))
        else:
            for i in range(0, len(params)):
                env.add_variable(params[i], operands[i])
            return meval(procedure.getBody(), env)
    else:
        eval_error('Application of non-procedure: %s' % (procedure))


def is_special_form(expr, keyword):
    # [keyword, ...rest]
    return isinstance(expr, list) and len(expr) > 0 and expr[0] == keyword


def parse(str):
    # '(' -> start, ')' -> end

    def parse_tokens(tokens, is_inner):
        parse_tree = []

        while len(tokens) > 0:
            current_token = tokens.pop(0)
            if current_token == '(':
                parse_tree.append(parse_tokens(tokens, True))
            elif current_token == ')':
                if is_inner:
                    return parse_tree
                else:
                    error('Unmatched close paren: ' + str)
            else:
                parse_tree.append(current_token)

        if is_inner:
            error('Unmatched open paren: ' + str)
            return None
        else:
            return parse_tree

        return parse_tree

    return parse_tokens(tokenize(str), False)


def eval_error(message):
    raise RuntimeError(message)


def error(message):
    raise SyntaxError(message)


# Tokenizing (tokens are separated by spaces, tabs, newlines)
def tokenize(str):
    current_token = ''
    tokens = []

    for char in str:
        if char.isspace():
            if len(current_token) > 0:
                tokens.append(current_token)
                current_token = ''
        elif char in '()':
            if len(current_token) > 0:
                tokens.append(current_token)
                current_token = ''
            tokens.append(char)
        else:
            current_token = current_token + char

    if len(current_token) > 0:
        tokens.append(current_token)

    return tokens


if __name__ == "__main__":
    main()
