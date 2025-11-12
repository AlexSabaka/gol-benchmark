from typing import List, Dict, Any, Optional, Union, Literal, Tuple
from dataclasses import dataclass
from enum import Enum
import random
import sympy as sp
from sympy import sympify, IndexedBase, symbols, simplify, evaluate, N
from sympy.parsing.sympy_parser import parse_expr
from sympy.core.expr import Expr
import re


class NumberMode(Enum):
    INTEGER = "integer"
    RATIONAL = "rational"
    REAL = "real"

@dataclass
class PatternConfig:
    pattern: str
    variable_count: int
    max_parenthesis_depth: int = 3
    number_mode: NumberMode = NumberMode.INTEGER
    number_range: Tuple[float, float] = (-10.0, 10.0)

class SymbolicMathExpressionGenerator:
    def __init__(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            random.seed(seed)
        
        # Define available operations
        self.operations = {
            'add': lambda x, y: x + y,
            'sub': lambda x, y: x - y,
            'mul': lambda x, y: x * y,
            'div': lambda x, y: x / y,
            'pow': lambda x, y: x ** y,
            'sqrt': lambda x: sp.sqrt(x),
            'abs': lambda x: sp.Abs(x),
            'sin': lambda x: sp.sin(x),
            'cos': lambda x: sp.cos(x),
            'tan': lambda x: sp.tan(x),
            'log': lambda x: sp.log(x),
            'exp': lambda x: sp.exp(x),
        }
        
        # Predefined patterns for different complexity levels
        self.complexity_patterns = {
            1: [
                "a[0] + a[1]",
                "a[0] - a[1]", 
                "a[0] * a[1]",
                "a[0] / a[1]"
            ],
            2: [
                "a[0] + a[1] * a[2]",
                "a[0] * a[1] - a[2]",
                "(a[0] + a[1]) / a[2]",
                "a[0] ** 2 + a[1]"
            ],
            3: [
                "(a[0] + a[1]) * (a[2] - a[3])",
                "a[0] ** 2 + a[1] ** 2",
                "sqrt(a[0] ** 2 + a[1] ** 2)",
                "(a[0] + a[1]) ** 2 / (a[0] - a[1])"
            ],
            4: [
                "a[0] ** 3 + a[1] * a[2] ** 2 + a[3]",
                "(a[0] + a[1]) ** 2 + (a[2] - a[3]) ** 2",
                "a[0] * (a[1] + a[2]) ** 2 - a[3] ** 3",
                "sqrt((a[0] + a[1]) ** 2 + (a[2] * a[3]) ** 2)"
            ],
            5: [
                "a[0] ** 4 + a[1] ** 3 + a[2] ** 2 + a[3] + a[4]",
                "((a[0] + a[1]) ** 2 - a[2]) / (a[3] + a[4])",
                "a[0] * sin(a[1]) + a[2] * cos(a[3])",
                "exp(a[0]) + log(abs(a[1]) + 1) * a[2]"
            ]
        }

    def generate_number(self, mode: NumberMode, range_vals: Tuple[float, float]) -> Union[int, sp.Rational, float]:
        """
        Generate a random number based on the specified mode.
        
        Args:
            mode: Number generation mode
            range_vals: Tuple of (min, max) values
            
        Returns:
            Generated number of appropriate type
        """
        min_val, max_val = range_vals
        
        if mode == NumberMode.INTEGER:
            return random.randint(int(min_val), int(max_val))
        elif mode == NumberMode.RATIONAL:
            numerator = random.randint(int(min_val * 10), int(max_val * 10))
            denominator = random.randint(1, 10)
            return sp.Rational(numerator, denominator)
        else:  # REAL
            return round(random.uniform(min_val, max_val), 3)

    def substitute_pattern_variables(self, pattern: str, config: PatternConfig) -> sp.Expr:
        """
        Substitute variables in a pattern with generated values.
        
        Args:
            pattern: Symbolic pattern string
            config: Pattern configuration
            
        Returns:
            SymPy expression with substituted values
        """
        # Create IndexedBase for pattern parsing
        a = IndexedBase('a')
        
        # Parse the pattern
        expr = sympify(pattern, locals={'a': a})
        
        # Find all indexed variables in the pattern
        indexed_vars = [atom for atom in expr.atoms() if str(atom) == 'a']
        
        # Generate substitution values
        substitutions = { }
        for var in indexed_vars:
            values = []
            for i in range(config.variable_count):
                value = self.generate_number(config.number_mode, config.number_range)
                # Avoid division by zero
                if 'div' in pattern or '/' in pattern:
                    while abs(float(value)) < 0.001:
                        value = self.generate_number(config.number_mode, config.number_range)
                values.append(value)
                
            substitutions[var] = tuple(values)
        
        # Substitute values
        with evaluate(False):
            expr = expr.subs(substitutions)

        return expr

    def generate_expressions_for_target(
        self, 
        target: Union[int, float], 
        config: PatternConfig, 
        count: int = 10,
        tolerance: float = 1e-6
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple expressions that evaluate close to the target value.
        
        Args:
            target: Target result value
            config: Pattern configuration
            count: Number of expressions to generate
            tolerance: Acceptable difference from target
            
        Returns:
            List of dictionaries containing expression info
        """
        expressions = []
        
        while len(expressions) < count:
            # Generate expression from pattern
            expr = self.substitute_pattern_variables(config.pattern, config)
            
            # Evaluate the expression
            result = self._safe_evaluate(expr)
            
            if result is not None and abs(float(result) - float(target)) <= tolerance:
                expr_info = {
                    'expression': str(expr),
                    'sympy_expr': expr,
                    'evaluated': result,
                    'pattern': config.pattern,
                    'variables_used': self._extract_variables(expr)
                }
                
                # Avoid duplicates
                if not any(e['expression'] == expr_info['expression'] for e in expressions):
                    expressions.append(expr_info)

        return expressions

    def generate_by_complexity(
        self, 
        target: Union[int, float], 
        complexity: int, 
        number_mode: NumberMode = NumberMode.INTEGER,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate expressions using predefined complexity patterns.
        
        Args:
            target: Target result value
            complexity: Complexity level (1-5)
            number_mode: Number generation mode
            count: Number of expressions to generate
            
        Returns:
            List of generated expressions
        """
        if complexity not in self.complexity_patterns:
            raise ValueError(f"Complexity level {complexity} not supported. Use 1-5.")
        
        patterns = self.complexity_patterns[complexity]
        all_expressions = []
        
        expressions_per_pattern = max(1, count // len(patterns))
        
        for pattern in patterns:
            # Determine variable count from pattern
            var_count = len(re.findall(r'a\[(\d+)\]', pattern)) + 1
            
            config = PatternConfig(
                pattern=pattern,
                variable_count=var_count,
                number_mode=number_mode,
                number_range=(-10.0, 10.0)
            )
            
            expressions = self.generate_expressions_for_target(
                target, config, expressions_per_pattern
            )
            all_expressions.extend(expressions)
            
            if len(all_expressions) >= count:
                break
        
        return all_expressions[:count]

    def _safe_evaluate(self, expr: sp.Expr) -> Optional[Union[int, float, sp.Rational]]:
        """
        Safely evaluate a SymPy expression.
        
        Args:
            expr: SymPy expression to evaluate
            
        Returns:
            Evaluated result or None if evaluation fails
        """
        result = expr.evalf()
        
        # Check for complex numbers or invalid results
        if result.is_real and result.is_finite:
            return result
        return None


    def _extract_variables(self, expr: sp.Expr) -> List[str]:
        """
        Extract variable names from a SymPy expression.
        
        Args:
            expr: SymPy expression
            
        Returns:
            List of variable names
        """
        return [str(var) for var in expr.free_symbols]

    def simplify_expression(self, expr: sp.Expr) -> sp.Expr:
        """
        Simplify a SymPy expression.
        
        Args:
            expr: Expression to simplify
            
        Returns:
            Simplified expression
        """
        return simplify(expr)

    def generate_step_by_step_solution(self, expr_info: Dict[str, Any]) -> List[str]:
        """
        Generate a step-by-step solution for the given expression.
        
        Args:
            expr_info: Expression information dictionary
            
        Returns:
            List of solution steps
        """
        steps = []
        expr = expr_info['sympy_expr']
        
        steps.append(f"Original expression: {expr_info['expression']}")
        steps.append(f"Pattern used: {expr_info['pattern']}")
        
        # Show simplification if possible
        simplified = self.simplify_expression(expr)
        if simplified != expr:
            steps.append(f"Simplified: {simplified}")
        
        steps.append(f"Evaluating numerically...")
        steps.append(f"Final result: {expr_info['evaluated']}")
        
        return steps

    def create_custom_pattern_config(
        self, 
        pattern: str, 
        number_mode: NumberMode = NumberMode.INTEGER,
        number_range: Tuple[float, float] = (-10.0, 10.0),
        max_parenthesis_depth: int = 3
    ) -> PatternConfig:
        """
        Create a custom pattern configuration.
        
        Args:
            pattern: Symbolic pattern string
            number_mode: Number generation mode
            number_range: Range for number generation
            max_parenthesis_depth: Maximum parenthesis nesting depth
            
        Returns:
            Pattern configuration object
        """
        # Count variables in pattern
        var_matches = re.findall(r'a\[(\d+)\]', pattern)
        var_count = len(set(var_matches)) if var_matches else 0
        
        return PatternConfig(
            pattern=pattern,
            variable_count=var_count,
            max_parenthesis_depth=max_parenthesis_depth,
            number_mode=number_mode,
            number_range=number_range
        )

    def generate_test_case(
        self, 
        target: Union[int, float], 
        config: PatternConfig,
        count: int = 5
    ) -> Dict[str, Any]:
        """
        Generate a complete test case with expressions and metadata.
        
        Args:
            target: Target value
            config: Pattern configuration
            count: Number of expressions to generate
            
        Returns:
            Complete test case dictionary
        """
        expressions = self.generate_expressions_for_target(target, config, count)
        
        return {
            "target": target,
            "pattern": config.pattern,
            "number_mode": config.number_mode.value,
            "number_range": config.number_range,
            "expressions": expressions,
            "generation_success_rate": len(expressions) / count if count > 0 else 0
        }


# Example usage and demonstration
if __name__ == "__main__":
    # Create generator
    generator = SymbolicMathExpressionGenerator(seed=42)
    
    # Example 1: Using predefined complexity patterns
    print("=== Complexity-based Generation ===")
    expressions = generator.generate_by_complexity(
        target=10, 
        complexity=2,
        count=10,
        number_mode=NumberMode.INTEGER
    )
    for i, expr_info in enumerate(expressions):
        print(f"{i+1}. {expr_info['expression']} = {expr_info['evaluated']:.2f}")
    
    # # Example 2: Using custom patterns
    # print("\n=== Custom Pattern Generation ===")
    # custom_config = generator.create_custom_pattern_config(
    #     pattern="(a[0] + a[1])^2 / (a[0] - a[1])",
    #     number_mode=NumberMode.RATIONAL,
    #     number_range=(-5.0, 5.0)
    # )
    
    # custom_expressions = generator.generate_expressions_for_target(
    #     target=2.5, 
    #     config=custom_config,
    #     count=3,
    # )
    
    # for expr_info in custom_expressions:
    #     print(f"Expression: {expr_info['expression']}")
    #     print(f"Result: {expr_info['evaluated']}")
    #     steps = generator.generate_step_by_step_solution(expr_info)
    #     for step in steps:
    #         print(f"  {step}")
    #     print()