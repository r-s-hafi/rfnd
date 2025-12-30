####PARSER 101#####

# 1. Define grammar
# 2. Create parser instance
# 3. Run input thrui parser which gives a tree representation of input
# 4. Process tree

from lark import Lark, Transformer

class SumTransform(Transformer):

    def addend(self, intList):
        return int(intList[0])

    #parent method always gets the children's return values as a list
    def sum(self, leftRight):
        return leftRight[0] + leftRight[1]

expression = '45 + 33'

#start the parsing at expression
#expression is any term + or - any other term n(*) times
#term is a any factor * or / any other factor n(*) times
#a factor can be a number, tag ID, a parenthesized expression, or a tagID wrapped within a function (derivative(PI001))

#a function is any identifier with a set of parentheses after (can have n (*) tags within separated by a comma)

#the operations defined within expression and term are mapped to the appropriate symbols

#regex for operations like avg, derivative, add, subtract
#regex for tagIDs in the form of two uppercase letters + 3 digits (PI001, TI001)
#regex for numbers, includes decimal points and digits after

#import whitespace definition
#ignore it

grammar = """
start: expression
expression: term ((ADD | SUBTRACT) term)*
term: factor ((MULTIPLY | DIVIDE) factor)*
factor: NUMBER
        | TAG_ID
        | function
        | "(" expression ")"

function: IDENTIFIER "(" expression ("," expression)* ")"

ADD: "+"
SUBTRACT: "-"
MULTIPLY: "*"
DIVIDE: "/"

OPERATION: /[a-zA-Z_][a-zA-Z0-9_]*/
TAG_ID: /[A-Z]{2}[0-9]{3}/
NUMBER: /[0-9]+(\.[0-9]+)?/

%import common.WS
%ignore WS
"""

#create the formula transformer class
class FormulaTransformer(Transformer):
    #initialize the class with list of tags and their datapoints
    def __init__(self, tags):
        self.tags = tags

    #every time the parser encounters a number token, return the number as a float (parser returns strings only)
    def NUMBER(self, token):
        return float(token)
    
    #everyt time the parser encounters a tag ID, return it as a string
    def TAG_ID(self, token):
        return str(token)

    #every time the parser encounters a factor node, return the factor
    def factor(self, args):
        return args[0]
    
    #every time the parser encounters a term node, perform term operation
    #example input -> args = [<Signal A>, Token(MUL, '*'), <Signal B>, Token(DIV, '/'), <Signal C>]
    def term(self, args):
        result = args[0]
        i = 1

        #as long as i is not out of range of the arguments list, continue to multiply and divide factors
        while i < len(args):

            #declare the operator as a Lark token with built-in function .type that returns operator
            operator = args[i]
            right = args[i + 1]

            if operator.type == 'MULTIPLY':
                result = result * right
            elif operator.type == 'DIVIDE':
                result = result / right
            
            #index i by 2 to move along to the next operator and signal to the right of it
            i += 2
            return result

    #when parser encounters an expression node, perform expression operation
    #similar logic to term method
    def expression(self, args):
        result = args[0]
        i = 1

        while i < len(args):

            operator = args[i]
            right = args[i + 1]

            if operator.type == 'ADD':
                result = result + right
            elif operator.type == 'SUBTRACT':
                result = result / right
            
            #index i by 2 to move along to the next operator and signal to the right of it
            i += 2
            return result
    
    #when parser encounters a function node, perform function operation
    #example input -> args = [Token(IDENTIFIER, 'max'), <Signal object for PI001>, <Signal object for TI042>]
    def function(self, args):
        func_name = args[0]
        func_args = args[1:]

        if func_name == 'derivative':
            pass
        
        elif func_name == 'avg':
            pass
        
        elif func_name == 'sum':
            pass

        else:
            return(f'Unknown function: {func_name}')


    
    


# parser = Lark(grammar, start='sum')
# tree = parser.parse(expression)
# answer = SumTransform().transform(tree)
# print(answer)