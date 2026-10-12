"""
Safe Calculator Tool using AST parsing to prohibit raw eval() execution.
Evaluates mathematical expressions securely with strict whitelisting.
"""
import ast
import math
import operator
from typing import Any, Dict
from pydantic import BaseModel, Field
from src.tools.base import BaseTool


class CalculatorInput(BaseModel):
    expression: str = Field(
        ...,
        description="The mathematical expression to evaluate (e.g. '125 * 8 + sqrt(144) - 2**5')."
    )


class SafeMathEvaluator:
    """Evaluates mathematical expressions using AST walking without raw eval()."""

    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    ALLOWED_FUNCTIONS = {
        "sqrt": math.sqrt,
        "abs": abs,
        "round": round,
        "floor": math.floor,
        "ceil": math.ceil,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "pow": pow,
    }

    ALLOWED_CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
    }

    def evaluate(self, expr_str: str) -> Any:
        try:
            tree = ast.parse(expr_str.strip(), mode="eval")
        except SyntaxError as e:
            raise ValueError(f"Invalid mathematical expression syntax: {e}")

        return self._eval_node(tree.body)

    def _eval_node(self, node: ast.AST) -> Any:
        # Numbers / Constants
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

        # Binary Operations (+, -, *, /, %, **, //)
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self.ALLOWED_OPERATORS:
                raise ValueError(f"Operator '{op_type.__name__}' is not permitted.")
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            
            # Guard against giant powers causing memory/CPU denial-of-service
            if op_type is ast.Pow:
                if abs(right) > 1000 or (isinstance(left, (int, float)) and abs(left) > 10000 and right > 10):
                    raise ValueError("Exponent too large to evaluate safely.")
            
            return self.ALLOWED_OPERATORS[op_type](left, right)

        # Unary Operations (-x, +x)
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self.ALLOWED_OPERATORS:
                raise ValueError(f"Unary operator '{op_type.__name__}' is not permitted.")
            operand = self._eval_node(node.operand)
            return self.ALLOWED_OPERATORS[op_type](operand)

        # Named constants (pi, e)
        if isinstance(node, ast.Name):
            if node.id in self.ALLOWED_CONSTANTS:
                return self.ALLOWED_CONSTANTS[node.id]
            raise ValueError(f"Undefined identifier or variable '{node.id}' in expression.")

        # Safe Math Function Calls
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Nested function attribute calls are not permitted.")
            func_name = node.func.id
            if func_name not in self.ALLOWED_FUNCTIONS:
                raise ValueError(f"Function '{func_name}' is not in the permitted math whitelist.")
            args = [self._eval_node(arg) for arg in node.args]
            return self.ALLOWED_FUNCTIONS[func_name](*args)

        raise ValueError(f"Syntax element '{type(node).__name__}' is strictly prohibited in math expressions.")


class CalculatorTool(BaseTool):
    """
    Safely calculates mathematical expressions using AST validation without eval().
    """
    name: str = "calculator"
    description: str = (
        "Use this tool to evaluate mathematical and arithmetic calculations accurately. "
        "Do not compute complex math in your head. Input must be an expression string (e.g., '14 * 25 + sqrt(144)')."
    )
    args_schema = CalculatorInput
    requires_approval: bool = False

    def __init__(self):
        self.evaluator = SafeMathEvaluator()

    def execute(self, expression: str) -> str:
        try:
            result = self.evaluator.evaluate(expression)
            # Format cleanly: if integer float (e.g. 42.0), format as 42 or standard precision
            if isinstance(result, float) and result.is_integer():
                result_str = str(int(result))
            elif isinstance(result, float):
                result_str = f"{result:.8g}"
            else:
                result_str = str(result)
            return result_str
        except ZeroDivisionError:
            return "Math Error: Division by zero is undefined."
        except Exception as e:
            return f"Math Evaluation Error: {str(e)}"

