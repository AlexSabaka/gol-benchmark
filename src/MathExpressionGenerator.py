import random
from typing import Any, Dict, List


# Multilingual prompt templates
PROMPT_STYLES_EN = {
    "linguistic": """
Given the mathematical expression: {expression}

Follow these EXACT steps:
1. Identify all operations in the expression following order of operations (PEMDAS/BODMAS)
2. Calculate each sub-expression step by step
3. Show your work for every intermediate calculation
4. Provide the final numerical result

Expression: {expression}
Step-by-step solution:""",

    "casual": """
Hey! Can you solve this math expression for me? Just work through it step by step.
{expression}

Show me how you get to the answer:""",

    "minimal": """
{expression} =""",

    "examples": """
{examples}
---
{expression} =
""",

    "rules_math": """$$
\\text{{Expression: }} {expression} \\\\
\\text{{Apply order of operations: }} \\\\
P: \\text{{Parentheses first}} \\\\
E: \\text{{Exponents}} \\\\
MD: \\text{{Multiplication and Division (left to right)}} \\\\
AS: \\text{{Addition and Subtraction (left to right)}} \\\\
\\rule{{100pt}}{{0.4pt}} \\\\
\\text{{Solution:}}
$$"""
}


class MathExpressionGenerator:
    def __init__(self, seed: int = None):
        if seed is not None:
            random.seed(seed)

    def generate_expressions_for_target(self, target: int, complexity: int, count: int = 10) -> List[str]:
        """
        Generate multiple expressions that evaluate to the target value.

        Args:
            target: The target result value
            complexity: Complexity level (1-5)
            count: Number of expressions to generate

        Returns:
            List of expression strings that all evaluate to target
        """
        expressions = []
        attempts = 0
        max_attempts = count * 50  # Avoid infinite loops

        while len(expressions) < count and attempts < max_attempts:
            expr = self._generate_single_expression(target, complexity)
            if expr and self._verify_expression(expr, target):
                if expr not in expressions:  # Avoid duplicates
                    expressions.append(expr)
            attempts += 1

        return expressions

    def _generate_single_expression(self, target: int, complexity: int) -> str:
        """Generate a single expression for the given target and complexity."""
        if complexity == 1:
            return self._generate_complexity_1(target)
        elif complexity == 2:
            return self._generate_complexity_2(target)
        elif complexity == 3:
            return self._generate_complexity_3(target)
        elif complexity == 4:
            return self._generate_complexity_4(target)
        else:
            return self._generate_complexity_5(target)

    def _generate_complexity_1(self, target: int) -> str:
        """Single operation expressions."""
        operations = [
            lambda: f"{target + random.randint(1, 10)} - {random.randint(1, 10)}",
            lambda: f"{target * random.randint(2, 5)} / {random.randint(2, 5)}",
            lambda: f"{random.randint(1, target)} + {target - random.randint(1, target) if target > 1 else 1}",
            lambda: f"{target} * 1",
            lambda: f"{target} + 0"
        ]

        # Try operations until we find one that works
        for _ in range(10):
            op = random.choice(operations)
            expr = op()
            if self._safe_eval(expr) == target:
                return expr

        # Fallback to simple addition
        a = random.randint(0, target)
        return f"{a} + {target - a}"

    def _generate_complexity_2(self, target: int) -> str:
        """Two operations, no parentheses."""
        # Try different patterns
        patterns = []

        # Pattern: a + b * c
        for b in range(1, 6):
            for c in range(1, 6):
                a = target - (b * c)
                if a >= 0:
                    patterns.append(f"{a} + {b} * {c}")

        # Pattern: a * b - c  
        for a in range(2, 6):
            for b in range(2, 6):
                c = (a * b) - target
                if c > 0:
                    patterns.append(f"{a} * {b} - {c}")

        # Pattern: a - b / c (integer division)
        for b in range(target + 1, target + 20):
            for c in range(2, 6):
                if b % c == 0:
                    a = target + (b // c)
                    patterns.append(f"{a} - {b} / {c}")

        if patterns:
            return random.choice(patterns)

        # Fallback
        return self._generate_complexity_1(target)

    def _generate_complexity_3(self, target: int) -> str:
        """Expressions with parentheses."""
        patterns = []

        # Pattern: (a + b) * c
        for c in range(2, 5):
            if target % c == 0:
                sum_val = target // c
                for a in range(1, sum_val):
                    b = sum_val - a
                    if b > 0:
                        patterns.append(f"({a} + {b}) * {c}")

        # Pattern: (a * b - c) / d
        for d in range(2, 5):
            product_target = target * d
            for a in range(2, 6):
                for b in range(2, 6):
                    c = (a * b) - product_target
                    if c > 0:
                        patterns.append(f"({a} * {b} - {c}) / {d}")

        # Pattern: a * (b + c) - d
        for a in range(2, 5):
            for b in range(1, 6):
                for c in range(1, 6):
                    d = a * (b + c) - target
                    if d > 0:
                        patterns.append(f"{a} * ({b} + {c}) - {d}")

        if patterns:
            return random.choice(patterns)

        return self._generate_complexity_2(target)

    def _generate_complexity_4(self, target: int) -> str:
        """Nested parentheses or longer chains."""
        patterns = []

        # Pattern: ((a + b) * c - d) / e
        for e in range(2, 4):
            for c in range(2, 4):
                for d in range(1, 10):
                    sum_needed = (target * e + d) // c
                    if sum_needed > 1 and (target * e + d) % c == 0:
                        for a in range(1, sum_needed):
                            b = sum_needed - a
                            if b > 0:
                                patterns.append(f"(({a} + {b}) * {c} - {d}) / {e}")

        # Pattern: a + b + c + d + e (long addition)
        if target >= 5:
            terms = []
            remaining = target
            for _ in range(4):
                term = random.randint(1, remaining - 1)
                terms.append(str(term))
                remaining -= term
            terms.append(str(remaining))
            random.shuffle(terms)
            patterns.append(" + ".join(terms))

        if patterns:
            return random.choice(patterns)

        return self._generate_complexity_3(target)

    def _generate_complexity_5(self, target: int) -> str:
        """Most complex expressions with multiple nested levels."""
        patterns = []

        # Pattern: (a * (b + c) - d) * e + f
        for e in range(2, 4):
            for a in range(2, 4):
                for b in range(1, 4):
                    for c in range(1, 4):
                        for d in range(1, 10):
                            f = target - (a * (b + c) - d) * e
                            if f >= 0:
                                patterns.append(f"({a} * ({b} + {c}) - {d}) * {e} + {f}")

        # Pattern: Complex fraction
        # ((a * b + c) * d - e) / f
        for f in range(2, 4):
            for d in range(2, 4):
                for a in range(2, 4):
                    for b in range(1, 4):
                        for c in range(1, 6):
                            for e in range(1, 20):
                                if ((a * b + c) * d - e) == target * f:
                                    patterns.append(f"(({a} * {b} + {c}) * {d} - {e}) / {f}")

        if patterns:
            return random.choice(patterns)

        return self._generate_complexity_4(target)

    def _safe_eval(self, expression: str) -> float:
        """Safely evaluate mathematical expressions."""
        try:
            # Only allow safe mathematical operations
            allowed_chars = set('0123456789+-*/() .')
            if not all(c in allowed_chars for c in expression):
                return None

            # Evaluate the expression
            result = eval(expression)
            return result
        except:
            return None

    def _verify_expression(self, expression: str, target: int) -> bool:
        """Verify that the expression evaluates to the target."""
        result = self._safe_eval(expression)
        return result is not None and abs(result - target) < 0.0001

    def generate_step_by_step_solution(self, expression: str) -> List[str]:
        """Generate a step-by-step solution for the given expression."""
        steps = []
        steps.append(f"Original expression: {expression}")

        # This is a simplified version - in full implementation, 
        # you'd want to parse the expression tree and show each step
        result = self._safe_eval(expression)
        if result is not None:
            steps.append(f"Evaluating step by step...")
            steps.append(f"Final result: {result}")

        return steps

    def get_prompt_template(self, language: str = "en", style: str = "linguistic") -> str:
        """Get prompt template for given language and style."""
        templates = {
            "en": PROMPT_STYLES_EN,
        }

        if language not in templates:
            raise ValueError()
        if style not in templates[language]:
            raise ValueError()

        return templates[language][style]

    def generate_test_case(self, target: int, complexity: int, language: str = "en",
                          style: str = "linguistic", count: int = 1) -> Dict[str, Any]:
        """Generate a complete test case with expressions and prompts."""
        expressions = self.generate_expressions_for_target(target, complexity, count)

        test_case = {
            "target": target,
            "complexity": complexity,
            "language": language,
            "style": style,
            "expressions": expressions,
            "prompts": []
        }

        prompt_template = self.get_prompt_template(language, style)

        for expr in expressions:
            # For examples style, we'd include other examples
            if style == "examples":
                examples = "Example: 2 + 2 = 4\nStep 1: Add 2 + 2\nStep 2: Result is 4"
                prompt = prompt_template.format(expression=expr, examples=examples)
            else:
                prompt = prompt_template.format(expression=expr)

            test_case["prompts"].append(prompt)

        return test_case
