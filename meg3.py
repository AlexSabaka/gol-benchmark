"""
Procedural Equation Generator for Mathematical Benchmark
Generates equations with specified solutions and complexity levels
"""

from sympy import *
import random
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from pprint import pprint
from enum import Enum


class EquationType(Enum):
    LINEAR = "linear"
    POLYNOMIAL = "polynomial"
    TRIGONOMETRIC = "trigonometric"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    MIXED = "mixed"


@dataclass
class EquationConfig:
    """Configuration for equation generation"""
    equation_type: EquationType = EquationType.POLYNOMIAL
    degree: int = 2
    operations_count: int = 3
    nesting_level: int = 2
    allow_fractions: bool = True
    allow_roots: bool = True
    integer_solutions_only: bool = True
    max_coefficient: int = 10
    min_coefficient: int = -10


class MathEquationGenerator:
    """
    Generator for procedural mathematical equations with controlled complexity
    and specified target solutions.
    """
    
    def __init__(self, seed: int = None):
        if seed is not None:
            random.seed(seed)
        init_printing(use_unicode=True)
    
    def generate_equations_for_target(
        self,
        target: Union[int, float, List],
        symbols: str = "x",
        difficulty: int = 1,
        equation_type: EquationType = EquationType.POLYNOMIAL,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple equations that have the specified target solution(s).
        
        Args:
            target: Target solution value(s)
            symbols: Variable symbols (e.g., "x" or "x y" for multiple variables)
            difficulty: Difficulty level (1-5)
            equation_type: Type of equation to generate
            count: Number of equations to generate
            
        Returns:
            List of equation dictionaries with equations, solutions, and steps
        """
        # Parse symbols
        sym_list = symbols.split()
        sym_objects = [Symbol(s) for s in sym_list]
        
        # Handle multiple variables
        if len(sym_objects) > 1:
            if not isinstance(target, list) or len(target) != len(sym_objects):
                raise ValueError(f"For {len(sym_objects)} variables, target must be a list of {len(sym_objects)} values")
            target_values = target
        else:
            target_values = [target] if not isinstance(target, list) else target
        
        # Configure based on difficulty
        config = self._get_config_for_difficulty(difficulty, equation_type)
        
        equations = []
        attempts = 0
        max_attempts = count * 50
        
        while len(equations) < count and attempts < max_attempts:
            try:
                eq = self._generate_single_equation(
                    target_values, sym_objects, config, equation_type
                )
                if eq and self._verify_equation(eq['equation'], sym_objects, target_values):
                    # Generate solution steps
                    eq['steps'] = self._generate_solution_steps(
                        eq['equation'], sym_objects, target_values
                    )
                    equations.append(eq)
            except Exception as e:
                # Silently continue on generation failures
                pass
            attempts += 1
        
        return equations
    
    def _get_config_for_difficulty(self, difficulty: int, equation_type: EquationType) -> EquationConfig:
        """Get configuration based on difficulty level."""
        configs = {
            1: EquationConfig(
                equation_type=equation_type,
                degree=1 if equation_type == EquationType.POLYNOMIAL else 1,
                operations_count=1,
                nesting_level=1,
                max_coefficient=5,
                min_coefficient=-5
            ),
            2: EquationConfig(
                equation_type=equation_type,
                degree=2 if equation_type == EquationType.POLYNOMIAL else 1,
                operations_count=2,
                nesting_level=1,
                max_coefficient=10,
                min_coefficient=-10
            ),
            3: EquationConfig(
                equation_type=equation_type,
                degree=2 if equation_type == EquationType.POLYNOMIAL else 2,
                operations_count=3,
                nesting_level=2,
                max_coefficient=15,
                min_coefficient=-15
            ),
            4: EquationConfig(
                equation_type=equation_type,
                degree=3 if equation_type == EquationType.POLYNOMIAL else 2,
                operations_count=4,
                nesting_level=2,
                max_coefficient=20,
                min_coefficient=-20
            ),
            5: EquationConfig(
                equation_type=equation_type,
                degree=4 if equation_type == EquationType.POLYNOMIAL else 3,
                operations_count=5,
                nesting_level=3,
                max_coefficient=25,
                min_coefficient=-25
            ),
        }
        return configs.get(difficulty, configs[3])
    
    def _generate_single_equation(
        self,
        target_values: List[Union[int, float]],
        symbols: List[Symbol],
        config: EquationConfig,
        equation_type: EquationType
    ) -> Optional[Dict[str, Any]]:
        """Generate a single equation with the specified parameters."""
        
        if equation_type == EquationType.LINEAR:
            return self._generate_linear_equation(target_values[0], symbols[0], config)
        elif equation_type == EquationType.POLYNOMIAL:
            return self._generate_polynomial_equation(target_values[0], symbols[0], config)
        elif equation_type == EquationType.TRIGONOMETRIC:
            return self._generate_trig_equation(target_values[0], symbols[0], config)
        elif equation_type == EquationType.EXPONENTIAL:
            return self._generate_exponential_equation(target_values[0], symbols[0], config)
        elif equation_type == EquationType.LOGARITHMIC:
            return self._generate_logarithmic_equation(target_values[0], symbols[0], config)
        else:
            return self._generate_mixed_equation(target_values, symbols, config)
    
    def _generate_linear_equation(
        self, target: Union[int, float], symbol: Symbol, config: EquationConfig
    ) -> Dict[str, Any]:
        """Generate a linear equation ax + b = c with solution target."""
        a = random.randint(1, config.max_coefficient)
        if a == 0:
            a = 1
        
        # Choose RHS value
        c = random.randint(config.min_coefficient, config.max_coefficient)
        
        # Calculate b such that x = target satisfies the equation
        b = c - a * target
        
        # Build the equation
        lhs = a * symbol + b
        equation = Eq(lhs, c)
        
        return {
            'equation': equation,
            'solution': [target],
            'type': 'linear',
            'complexity': config.operations_count
        }
    
    def _generate_polynomial_equation(
        self, target: Union[int, float], symbol: Symbol, config: EquationConfig
    ) -> Dict[str, Any]:
        """Generate a polynomial equation with solution target."""
        
        # For polynomials, we can construct them using factored form
        # (x - target) * (other factors) = 0
        
        factors = [symbol - target]
        
        # Add additional factors for higher degrees
        for _ in range(config.degree - 1):
            # Add another root
            other_root = random.randint(config.min_coefficient, config.max_coefficient)
            if other_root != target:  # Avoid duplicate roots
                factors.append(symbol - other_root)
        
        # Expand the polynomial
        poly = expand(prod(factors))
        
        # Optionally move some terms to RHS
        if random.choice([True, False]) and config.operations_count > 1:
            # Split polynomial into LHS and RHS
            terms = Add.make_args(poly)
            if len(terms) > 1:
                split_point = random.randint(1, len(terms) - 1)
                lhs = Add(*terms[:split_point])
                rhs = -Add(*terms[split_point:])
                equation = Eq(lhs, rhs)
            else:
                equation = Eq(poly, 0)
        else:
            equation = Eq(poly, 0)
        
        # Get all solutions
        all_solutions = solve(equation, symbol)
        
        return {
            'equation': equation,
            'solution': all_solutions,
            'type': 'polynomial',
            'complexity': config.degree * config.operations_count
        }
    
    def _generate_trig_equation(
        self, target: Union[int, float], symbol: Symbol, config: EquationConfig
    ) -> Dict[str, Any]:
        """Generate a trigonometric equation."""
        
        # Simple trig equations like a*sin(bx + c) = d
        trig_func = random.choice([sin, cos, tan])
        
        a = random.randint(1, config.max_coefficient)
        b = 1  # Keep frequency simple
        c = 0  # Phase shift
        
        # For simplicity, ensure target is in valid range for trig functions
        if trig_func in [sin, cos]:
            # sin and cos range is [-1, 1]
            d = a * trig_func(b * target + c)
            d = simplify(d)
            if hasattr(d, 'evalf'):
                d = round(float(d.evalf()), 2)
        else:
            # tan can be any value
            d = random.randint(config.min_coefficient, config.max_coefficient)
        
        lhs = a * trig_func(b * symbol + c)
        equation = Eq(lhs, d)
        
        return {
            'equation': equation,
            'solution': [target],  # Simplified - actual trig equations have infinite solutions
            'type': 'trigonometric',
            'complexity': config.operations_count * 2
        }
    
    def _generate_exponential_equation(
        self, target: Union[int, float], symbol: Symbol, config: EquationConfig
    ) -> Dict[str, Any]:
        """Generate an exponential equation."""
        
        # Simple exponential like a * b^x = c
        a = random.randint(1, config.max_coefficient)
        b = random.choice([2, 3, E])  # Base
        
        # Calculate c such that x = target is a solution
        c = a * b**target
        if hasattr(c, 'evalf'):
            c = simplify(c)
        
        lhs = a * b**symbol
        equation = Eq(lhs, c)
        
        return {
            'equation': equation,
            'solution': [target],
            'type': 'exponential',
            'complexity': config.operations_count * 2
        }
    
    def _generate_logarithmic_equation(
        self, target: Union[int, float], symbol: Symbol, config: EquationConfig
    ) -> Dict[str, Any]:
        """Generate a logarithmic equation."""
        
        # Ensure target gives a valid logarithm argument
        if target <= 0:
            target = abs(target) + 1
        
        # Simple log equation like log(ax + b) = c
        a = random.randint(1, config.max_coefficient)
        c = random.randint(1, 3)  # Keep log result simple
        
        # Calculate b such that x = target is a solution
        # log(a*target + b) = c => a*target + b = e^c
        b = exp(c) - a * target
        if hasattr(b, 'evalf'):
            b = round(float(b.evalf()), 2)
        
        lhs = log(a * symbol + b)
        equation = Eq(lhs, c)
        
        return {
            'equation': equation,
            'solution': [target],
            'type': 'logarithmic',
            'complexity': config.operations_count * 2
        }
    
    def _generate_mixed_equation(
        self, target_values: List[Union[int, float]], symbols: List[Symbol], config: EquationConfig
    ) -> Dict[str, Any]:
        """Generate equations with mixed types."""
        
        # For now, default to polynomial
        return self._generate_polynomial_equation(target_values[0], symbols[0], config)
    
    def _verify_equation(
        self, equation: Eq, symbols: List[Symbol], target_values: List[Union[int, float]]
    ) -> bool:
        """Verify that the equation has the target solution."""
        try:
            if len(symbols) == 1:
                # Single variable
                lhs_val = equation.lhs.subs(symbols[0], target_values[0])
                rhs_val = equation.rhs.subs(symbols[0], target_values[0])
                
                # Handle symbolic expressions
                if hasattr(lhs_val, 'evalf'):
                    lhs_val = complex(lhs_val.evalf())
                if hasattr(rhs_val, 'evalf'):
                    rhs_val = complex(rhs_val.evalf())
                
                # Check if they're approximately equal (accounting for floating point)
                return abs(lhs_val - rhs_val) < 1e-6
            else:
                # Multiple variables
                substitutions = dict(zip(symbols, target_values))
                lhs_val = equation.lhs.subs(substitutions)
                rhs_val = equation.rhs.subs(substitutions)
                
                if hasattr(lhs_val, 'evalf'):
                    lhs_val = complex(lhs_val.evalf())
                if hasattr(rhs_val, 'evalf'):
                    rhs_val = complex(rhs_val.evalf())
                    
                return abs(lhs_val - rhs_val) < 1e-6
        except:
            return False
    
    def _generate_solution_steps(
        self, equation: Eq, symbols: List[Symbol], target_values: List[Union[int, float]]
    ) -> List[str]:
        """Generate step-by-step solution for the equation."""
        steps = []
        
        if len(symbols) == 1:
            symbol = symbols[0]
            target = target_values[0]
            
            # Start with the original equation
            steps.append(f"{str(equation.lhs)} = 0")
            
            # Try to solve symbolically
            try:
                # Rearrange to standard form
                with evaluate(False):
                    standard_form = Eq(equation.lhs - equation.rhs, 0)
                    steps.append(latex(standard_form))
                
                # Simplify
                simplified = Eq(simplify(standard_form.lhs), 0)
                if simplified != standard_form:
                    steps.append(latex(simplified))
                
                # If it's a polynomial, try factoring
                if simplified.lhs.is_polynomial(symbol):
                    factored = factor(simplified.lhs)
                    if factored != simplified.lhs:
                        steps.append(latex(Eq(factored, 0)))
                
                # Show the solution
                solutions = solve(equation, symbol)
                if solutions:
                    if len(solutions) == 1:
                        steps.append(f"Therefore: {symbol} = {solutions[0]}")
                    else:
                        steps.append(f"Solutions: {symbol} = {', '.join(str(s) for s in solutions)}")
                
            except Exception:
                # Fallback to showing that target works
                steps.append(f"Substituting {symbol} = {target}:")
                lhs_val = equation.lhs.subs(symbol, target)
                rhs_val = equation.rhs.subs(symbol, target)
                steps.append(f"LHS = {lhs_val}")
                steps.append(f"RHS = {rhs_val}")
                if hasattr(lhs_val, 'evalf'):
                    lhs_val = lhs_val.evalf()
                if hasattr(rhs_val, 'evalf'):
                    rhs_val = rhs_val.evalf()
                steps.append(f"Verified: {lhs_val} = {rhs_val}")
        
        else:
            # Multiple variables - show substitution
            steps.append(f"Given: {equation}")
            steps.append(f"Solution: {dict(zip(symbols, target_values))}")
            
            substitutions = dict(zip(symbols, target_values))
            lhs_val = equation.lhs.subs(substitutions)
            rhs_val = equation.rhs.subs(substitutions)
            steps.append(f"Substituting values:")
            steps.append(f"LHS = {lhs_val}")
            steps.append(f"RHS = {rhs_val}")
            
        return steps
    
    def generate_test_case(
        self,
        target: Union[int, float, List],
        difficulty: int,
        symbols: str = "x",
        equation_type: EquationType = EquationType.POLYNOMIAL,
        count: int = 1
    ) -> Dict[str, Any]:
        """Generate a complete test case with equations and metadata."""
        
        equations = self.generate_equations_for_target(
            target=target,
            symbols=symbols,
            difficulty=difficulty,
            equation_type=equation_type,
            count=count
        )
        
        test_case = {
            "target": target,
            "difficulty": difficulty,
            "symbols": symbols,
            "equation_type": equation_type.value,
            "equations": []
        }
        
        for eq_data in equations:
            test_case["equations"].append({
                "equation": latex(eq_data['equation']),
                "solution": eq_data['solution'],
                "steps": eq_data['steps'],
                "complexity": eq_data['complexity']
            })
        
        return test_case


# Example usage and testing
if __name__ == "__main__":
    generator = MathEquationGenerator()
    
    print("=== Procedural Equation Generator Test ===\n")
    
    # Test 1: Linear equations with target solution 2
    print("Linear equations with solution x=3:")
    test_case = generator.generate_test_case(
        target=3,
        difficulty=2,
        symbols="x",
        equation_type=EquationType.POLYNOMIAL,
        count=1
    )
    
    for i, eq in enumerate(test_case['equations'], 1):
        print(f"\nEquation {i}: {eq['equation']}")
        print("Solution steps:")
        for step in eq['steps']:
            print(f"  {step}")
    
    print("\n" + "="*50 + "\n")
    
    # # Test 2: Polynomial equations with target solution 3
    # print("Polynomial equations with solution x=3:")
    # test_case = generator.generate_test_case(
    #     target=3,
    #     difficulty=2,
    #     symbols="x",
    #     equation_type=EquationType.POLYNOMIAL,
    #     count=2
    # )
    
    # for i, eq in enumerate(test_case['equations'], 1):
    #     print(f"\nEquation {i}: {eq['equation']}")
    #     print(f"All solutions: {eq['solution']}")
    #     print("Solution steps:")
    #     for step in eq['steps']:
    #         print(f"  {step}")
    
    # print("\n" + "="*50 + "\n")
    
    # # Test 3: Trigonometric equation
    # print("Trigonometric equation with solution x=0:")
    # test_case = generator.generate_test_case(
    #     target=0,
    #     difficulty=2,
    #     symbols="x",
    #     equation_type=EquationType.TRIGONOMETRIC,
    #     count=1
    # )
    
    # for eq in test_case['equations']:
    #     print(f"Equation:")
    #     print(eq['equation'])
    #     print("Solution steps:")
    #     for step in eq['steps']:
    #         print(f"  {step}")