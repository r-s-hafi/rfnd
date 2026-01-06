from lark import Lark, Transformer
import pandas as pd
from database import get_df
import sqlite3
import numpy as np

con_data = sqlite3.connect("process_data.db")

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

grammar = r"""
start: expression
expression: term ((ADD | SUBTRACT) term)*
term: factor ((MULTIPLY | DIVIDE) factor)*
factor: NUMBER
        | TAG_ID
        | function
        | "(" expression ")"

function: OPERATION "(" expression ("," expression)* ")"

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
    #initialize the class, store the tags in a dictionary
    def __init__(self):
        pass

    #when parser encounters the start node, return the expression result
    def start(self, args):
        return args[0]

    #every time the parser encounters a number token, return the number as a float (parser returns strings only)
    def NUMBER(self, token) -> float:
        return float(token)
    
    #everyt time the parser encounters a tag ID, return the df object for that tag
    def TAG_ID(self, token) -> pd.DataFrame:
        tag_id = str(token)
        tag_df = get_df(con_data, tag_id)
        print(f"this is the tag df: {tag_df}")
        return tag_df
    
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

            #perform operations on two dataframes
            if isinstance(result, pd.DataFrame) and isinstance(right, pd.DataFrame):
                #get the data column names (non-Time columns) from each dataframe
                result_data_col = [col for col in result.columns if col != 'Time'][0]
                right_data_col = [col for col in right.columns if col != 'Time'][0]
                
                if operator.type == 'MULTIPLY':
                    result[result_data_col] = result[result_data_col] * right[right_data_col]
                elif operator.type == 'DIVIDE':
                    result[result_data_col] = result[result_data_col] / right[right_data_col]

            #perform operations on a dataframe and a constant
            elif isinstance(result, pd.DataFrame):
                for column in result.columns:
                    if column != 'Time':
                        if operator.type == 'MULTIPLY':
                            result[column] = result[column] * right
                        elif operator.type == 'DIVIDE':
                            result[column] = result[column] / right
            
            #perform operations on a constant and a dataframe
            elif isinstance(right, pd.DataFrame):
                for column in right.columns:
                    if column != 'Time':
                        if operator.type == 'MULTIPLY':
                            right[column] = right[column] * result
                        elif operator.type == 'DIVIDE':
                            right[column] = right[column] / result
            
            #perform operations on two constants
            else:
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

            #perform operations on two dataframes
            if isinstance(result, pd.DataFrame) and isinstance(right, pd.DataFrame):
                #get the data column names (non-Time columns) from each dataframe
                result_data_col = [col for col in result.columns if col != 'Time'][0]
                right_data_col = [col for col in right.columns if col != 'Time'][0]
                
                if operator.type == 'ADD':
                    result[result_data_col] = result[result_data_col] + right[right_data_col]
                elif operator.type == 'SUBTRACT':
                    result[result_data_col] = result[result_data_col] - right[right_data_col]

            #perform operations on a dataframe and a constant
            elif isinstance(result, pd.DataFrame):
                for column in result.columns:
                    if column != 'Time':
                        if operator.type == 'ADD':
                            result[column] = result[column] + right
                        elif operator.type == 'SUBTRACT':
                            result[column] = result[column] - right
            
            #perform operations on a constant and a dataframe
            elif isinstance(right, pd.DataFrame):
                for column in right.columns:
                    if column != 'Time':
                        if operator.type == 'ADD':
                            right[column] = right[column] + result
                        elif operator.type == 'SUBTRACT':
                            right[column] = right[column] - result
            
            #perform operations on two constants
            else:
                if operator.type == 'ADD':
                    result = result + right
                elif operator.type == 'SUBTRACT':
                    result = result - right
            
            #index i by 2 to move along to the next operator and signal to the right of it
            i += 2
        return result
    
    #when parser encounters a function node, perform function operation
    #example input -> args = [Token(IDENTIFIER, 'max'), <Signal object for PI001>, <Signal object for TI042>]
    def function(self, args):
        func_name = str(args[0])
        func_args = args[1:]

        if func_name == 'derivative':
            print('hi')
        
        elif func_name == 'avg':
            pass
        
        elif func_name == 'sum':
            pass

        else:
            return(f'Unknown function: {func_name}')


parser = Lark(grammar, start='start')

def parse_formula(expression: str) -> str:
    tree = parser.parse(expression)
    answer = FormulaTransformer().transform(tree)
    return answer


