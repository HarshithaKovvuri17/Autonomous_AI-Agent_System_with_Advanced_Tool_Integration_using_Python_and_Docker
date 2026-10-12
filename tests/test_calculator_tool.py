"""Unit tests for Safe Calculator Tool."""
import pytest
from src.tools.calculator import CalculatorTool
from src.tools.base import ToolValidationError


def test_calculator_basic_arithmetic():
    calc = CalculatorTool()
    assert calc.execute("2 + 2") == "4"
    assert calc.execute("10 - 4") == "6"
    assert calc.execute("7 * 8") == "56"
    assert calc.execute("100 / 4") == "25"
    assert calc.execute("2 ** 5") == "32"
    assert calc.execute("17 // 3") == "5"
    assert calc.execute("17 % 5") == "2"


def test_calculator_math_functions():
    calc = CalculatorTool()
    assert calc.execute("sqrt(144)") == "12"
    assert calc.execute("abs(-42)") == "42"
    assert calc.execute("round(3.14159, 2)") == "3.14"
    assert calc.execute("floor(9.8)") == "9"
    assert calc.execute("ceil(9.1)") == "10"


def test_calculator_constants():
    calc = CalculatorTool()
    res = calc.execute("pi")
    assert "3.14159" in res


def test_calculator_division_by_zero():
    calc = CalculatorTool()
    res = calc.execute("10 / 0")
    assert "Division by zero" in res


def test_calculator_blocks_eval_and_injection():
    calc = CalculatorTool()
    # Attempting to call unauthorized functions
    res = calc.execute("__import__('os').system('echo hacked')")
    assert "Error" in res or "prohibited" in res

    res2 = calc.execute("eval('2 + 2')")
    assert "Error" in res2 or "not in the permitted" in res2

    res3 = calc.execute("open('secrets.txt', 'w')")
    assert "Error" in res3


def test_calculator_schema_validation():
    calc = CalculatorTool()
    # Valid dict
    assert calc.run({"expression": "15 * 3"}) == "45"
    
    # Missing required expression
    with pytest.raises(ToolValidationError):
        calc.run({})
