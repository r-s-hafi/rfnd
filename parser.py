from lark import Lark, Transformer
from lark.exceptions import VisitError, UnexpectedInput
import pandas as pd
from database import get_df
import sqlite3
import numpy as np

con_data = sqlite3.connect("process_data.db")


class FormulaEvaluationError(ValueError):
    pass


# start the parsing at expression
# expression is any term + or - any other term n(*) times
# term is any factor * or / any other factor n(*) times
# a factor can be a number, tag ID, a parenthesized expression, or a function call

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
TAG_ID: /[a-zA-Z_][a-zA-Z0-9_]*/
NUMBER: /[0-9]+(\.[0-9]+)?/

%import common.WS
%ignore WS
"""


class FormulaTransformer(Transformer):
    def __init__(self):
        super().__init__()

    def start(self, args):
        return args[0]

    def NUMBER(self, token) -> float:
        return float(token)

    def TAG_ID(self, token) -> pd.DataFrame:
        tag_id = str(token)
        tag_df = get_df(con_data, tag_id)
        if tag_df is None:
            raise FormulaEvaluationError(f"Unknown tag: {tag_id}")
        return self._normalize_signal(tag_df)

    def factor(self, args):
        return args[0]

    def term(self, args):
        return self._evaluate_binary_sequence(args, {"MULTIPLY", "DIVIDE"})

    def expression(self, args):
        return self._evaluate_binary_sequence(args, {"ADD", "SUBTRACT"})

    def function(self, args):
        func_name = str(args[0]).lower()
        func_args = args[1:]

        if func_name == "derivative":
            self._require_arg_count(func_name, func_args, 1)
            return self._func_derivative(func_args[0])
        if func_name == "avg":
            self._require_arg_count(func_name, func_args, 1)
            return self._func_avg(func_args[0])
        if func_name == "sum":
            self._require_arg_count(func_name, func_args, 1)
            return self._func_sum(func_args[0])
        if func_name == "min":
            self._require_min_args(func_name, func_args, 1)
            return self._func_minmax(func_args, use_min=True)
        if func_name == "max":
            self._require_min_args(func_name, func_args, 1)
            return self._func_minmax(func_args, use_min=False)
        if func_name == "abs":
            self._require_arg_count(func_name, func_args, 1)
            return self._func_abs(func_args[0])
        if func_name == "moving_avg":
            self._require_arg_count(func_name, func_args, 2)
            return self._func_moving_avg(func_args[0], func_args[1])

        raise FormulaEvaluationError(f"Unknown function: {func_name}")

    def _evaluate_binary_sequence(self, args, supported_ops):
        result = args[0]
        i = 1
        while i < len(args):
            operator = args[i]
            right = args[i + 1]
            if operator.type not in supported_ops:
                raise FormulaEvaluationError(f"Unsupported operator: {operator.type}")
            result = self._apply_binary(operator.type, result, right)
            i += 2
        return result

    def _is_signal(self, value) -> bool:
        return isinstance(value, pd.DataFrame)

    def _value_column(self, signal: pd.DataFrame) -> str:
        data_cols = [col for col in signal.columns if col != "Time"]
        if len(data_cols) != 1:
            raise FormulaEvaluationError("Signal must contain exactly one data column plus Time.")
        return data_cols[0]

    def _normalize_signal(self, signal: pd.DataFrame) -> pd.DataFrame:
        normalized = signal.copy()
        if "Time" not in normalized.columns:
            raise FormulaEvaluationError("Signal is missing required Time column.")
        normalized["Time"] = pd.to_datetime(normalized["Time"], errors="coerce")
        value_col = self._value_column(normalized)
        normalized[value_col] = pd.to_numeric(normalized[value_col], errors="coerce")
        normalized = normalized.dropna(subset=["Time"])
        return normalized.sort_values("Time").reset_index(drop=True)

    def _align_signals(self, left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
        left_norm = self._normalize_signal(left)
        right_norm = self._normalize_signal(right)
        left_col = self._value_column(left_norm)
        right_col = self._value_column(right_norm)
        aligned = left_norm.rename(columns={left_col: "left_value"}).merge(
            right_norm.rename(columns={right_col: "right_value"}),
            on="Time",
            how="inner",
        )
        return aligned.sort_values("Time").reset_index(drop=True)

    def _safe_divide(self, numerator, denominator):
        with np.errstate(divide="ignore", invalid="ignore"):
            result = numerator / denominator
        if isinstance(result, pd.Series):
            return result.replace([np.inf, -np.inf], np.nan)
        if np.isinf(result):
            return np.nan
        return result

    def _apply_binary(self, operator_type: str, left, right):
        op_map = {
            "ADD": lambda a, b: a + b,
            "SUBTRACT": lambda a, b: a - b,
            "MULTIPLY": lambda a, b: a * b,
            "DIVIDE": self._safe_divide,
        }
        operation = op_map[operator_type]

        if self._is_signal(left) and self._is_signal(right):
            aligned = self._align_signals(left, right)
            values = operation(aligned["left_value"], aligned["right_value"])
            return pd.DataFrame({"Time": aligned["Time"], "result": values})

        if self._is_signal(left):
            left_norm = self._normalize_signal(left)
            left_col = self._value_column(left_norm)
            left_norm[left_col] = operation(left_norm[left_col], right)
            return left_norm

        if self._is_signal(right):
            right_norm = self._normalize_signal(right)
            right_col = self._value_column(right_norm)
            right_norm[right_col] = operation(left, right_norm[right_col])
            return right_norm

        return operation(left, right)

    def _require_arg_count(self, func_name: str, args, expected_count: int):
        if len(args) != expected_count:
            raise FormulaEvaluationError(
                f"{func_name}() expects {expected_count} argument(s), got {len(args)}."
            )

    def _require_min_args(self, func_name: str, args, min_count: int):
        if len(args) < min_count:
            raise FormulaEvaluationError(
                f"{func_name}() expects at least {min_count} argument(s), got {len(args)}."
            )

    def _func_derivative(self, arg):
        if not self._is_signal(arg):
            raise FormulaEvaluationError("derivative() requires a signal argument.")
        signal = self._normalize_signal(arg)
        value_col = self._value_column(signal)
        dt_seconds = signal["Time"].diff().dt.total_seconds()
        dy = signal[value_col].diff()
        derivative = self._safe_divide(dy, dt_seconds)
        return pd.DataFrame({"Time": signal["Time"], "result": derivative})

    def _func_avg(self, arg):
        if self._is_signal(arg):
            signal = self._normalize_signal(arg)
            value_col = self._value_column(signal)
            return float(signal[value_col].mean(skipna=True))
        return float(np.mean(arg))

    def _func_sum(self, arg):
        if self._is_signal(arg):
            signal = self._normalize_signal(arg)
            value_col = self._value_column(signal)
            return float(signal[value_col].sum(skipna=True))
        return float(np.sum(arg))

    def _func_minmax(self, args, use_min: bool):
        comparator = np.minimum if use_min else np.maximum
        result = args[0]
        for item in args[1:]:
            result = self._apply_minmax_pair(result, item, comparator)
        return result

    def _apply_minmax_pair(self, left, right, comparator):
        if self._is_signal(left) and self._is_signal(right):
            aligned = self._align_signals(left, right)
            values = comparator(aligned["left_value"], aligned["right_value"])
            return pd.DataFrame({"Time": aligned["Time"], "result": values})
        if self._is_signal(left):
            signal = self._normalize_signal(left)
            value_col = self._value_column(signal)
            signal[value_col] = comparator(signal[value_col], right)
            return signal
        if self._is_signal(right):
            signal = self._normalize_signal(right)
            value_col = self._value_column(signal)
            signal[value_col] = comparator(left, signal[value_col])
            return signal
        return float(comparator(left, right))

    def _func_abs(self, arg):
        if self._is_signal(arg):
            signal = self._normalize_signal(arg)
            value_col = self._value_column(signal)
            signal[value_col] = signal[value_col].abs()
            return signal
        return float(abs(arg))

    def _func_moving_avg(self, signal_arg, window_arg):
        if not self._is_signal(signal_arg):
            raise FormulaEvaluationError("moving_avg() requires first argument to be a signal.")
        if self._is_signal(window_arg):
            raise FormulaEvaluationError("moving_avg() window must be a scalar number.")

        window = int(window_arg)
        if window <= 0:
            raise FormulaEvaluationError("moving_avg() window must be a positive integer.")

        signal = self._normalize_signal(signal_arg)
        value_col = self._value_column(signal)
        signal[value_col] = signal[value_col].rolling(window=window, min_periods=1).mean()
        return signal


parser = Lark(grammar, start='start')

def parse_formula(expression: str):
    try:
        tree = parser.parse(expression)
        result = FormulaTransformer().transform(tree)
        return result
    except VisitError as exc:
        original = exc.orig_exc
        if isinstance(original, FormulaEvaluationError):
            raise original
        raise FormulaEvaluationError(str(original)) from exc
    except UnexpectedInput as exc:
        raise FormulaEvaluationError(f"Syntax error near: {exc}") from exc


