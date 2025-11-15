import random
from typing import List, Dict, Any, Optional, Tuple

try:
    from src.PromptEngine import PromptEngine, Language, create_math_context
except:
    from PromptEngine import PromptEngine, Language, create_math_context

class TreeNode:
    """Represents a node in an arithmetic expression tree."""
    
    def __init__(self, value=None, left=None, right=None, is_variable=False):
        self.value = value
        self.left = left
        self.right = right
        self.is_variable = is_variable  # Flag for equation variables
    
    def is_leaf(self):
        return self.left is None and self.right is None
    
    def __repr__(self):
        if self.is_variable:
            return f"Var({self.value})"
        return f"Node({self.value})"


class MathExpressionGenerator:
    """
    Unified class for generating arithmetic expressions and equations.
    
    Features:
    - Generate expression trees that evaluate to target values
    - Convert expressions to equations by replacing nodes with variables
    - Support multiple operators: +, -, *, /, %, ^
    - Generate prompts in different styles and languages
    """
    
    # Operator precedence for proper parenthesization
    PRECEDENCE = {'+': 1, '-': 1, '*': 2, '/': 2, '%': 2, '^': 3, '**': 3}
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the generator.
        
        Args:
            seed: Random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)
    
    # ==================== CORE TREE GENERATION ====================
    
    def generate_expression_tree(
        self, 
        depth: int, 
        target: int, 
        allowed_operators: List[str]
    ) -> TreeNode:
        """
        Generate a random arithmetic expression tree that evaluates to the target value.
        
        Args:
            depth: Maximum depth of the tree
            target: Target value the expression should evaluate to
            allowed_operators: List of allowed operators ['+', '-', '*', '/']
        
        Returns:
            TreeNode: Root of the generated expression tree
        """
        if depth <= 1:
            # Base case: create a simple operation
            op = random.choice(allowed_operators)
            left_target, right_target = self._generate_subtargets(target, op)
            
            left_subtree = TreeNode(value=left_target)
            right_subtree = TreeNode(value=right_target)
            root = TreeNode(value=op, left=left_subtree, right=right_subtree)
            
            return root
        
        # Recursive case: build deeper tree
        op = random.choice(allowed_operators)
        
        left_depth = random.randint(0, depth - 1)
        right_depth = random.randint(0, depth - 1)
        
        left_target, right_target = self._generate_subtargets(target, op)
        
        left_subtree = self.generate_expression_tree(left_depth, left_target, allowed_operators)
        right_subtree = self.generate_expression_tree(right_depth, right_target, allowed_operators)
        
        root = TreeNode(value=op, left=left_subtree, right=right_subtree)
        
        return root
    
    def _generate_subtargets(self, target: int, operator: str) -> Tuple[int, int]:
        """
        Generate left and right target values that will result in the given target
        when the operator is applied.
        
        Args:
            target: Desired result value
            operator: The operator to apply
        
        Returns:
            Tuple of (left_value, right_value)
        """
        if operator == '+':
            left = random.randint(-50, 50)
            right = target - left
            
        elif operator == '-':
            right = random.randint(-50, 50)
            left = target + right
            
        elif operator == '*':
            if target == 0:
                left = 0
                right = random.randint(-50, 50)
            else:
                factors = self._find_factors(target)
                if factors:
                    left = random.choice(factors)
                    right = target // left
                else:
                    left = random.randint(-20, 20)
                    if left == 0:
                        left = 1
                    right = target // left
                    
        elif operator == '/':
            right = random.choice([i for i in range(-20, 21) if i != 0])
            left = target * right
            if left % right != 0:
                left = (left // right) * right
                
        elif operator == '%':
            right = random.choice([i for i in range(-20, 21) if i != 0])
            q = random.randint(-10, 10)
            left = q * right + target
            
        elif operator in ['^', '**']:
            right = random.randint(0, 4)
            if right == 0:
                left = random.randint(1, 10)
            elif right == 1:
                left = target
            else:
                # For higher powers, try to find the root
                left = random.randint(-10, 10)
                # If it doesn't match, just use random values
                
        else:
            raise ValueError(f"Unknown operator: {operator}")
        
        return left, right
    
    def _find_factors(self, n: int) -> List[int]:
        """Find all factors of a number."""
        if n == 0:
            return []
        
        factors = []
        n_abs = abs(n)
        
        for i in range(1, int(n_abs**0.5) + 1):
            if n_abs % i == 0:
                factors.extend([i, -i])
                if i != n_abs // i:
                    factors.extend([n_abs // i, -(n_abs // i)])
        
        return factors
    
    # ==================== EQUATION GENERATION ====================
    
    def tree_to_equation(
        self, 
        node: TreeNode, 
        variable_name: str = "x",
        num_variables: int = 1
    ) -> Tuple[TreeNode, Dict[str, int]]:
        """
        Convert an expression tree to an equation by replacing random leaf nodes
        with variables.
        
        Args:
            node: The expression tree root
            variable_name: Base name for variables (e.g., "x", "y")
            num_variables: Number of leaf nodes to replace with variables
        
        Returns:
            Tuple of (modified_tree, variable_values_dict)
            where variable_values_dict maps variable names to their original values
        """
        # Collect all leaf nodes
        leaves = self._collect_leaves(node)
        
        if len(leaves) == 0:
            return node, {}
        
        # Randomly select nodes to replace
        num_to_replace = min(num_variables, len(leaves))
        nodes_to_replace = random.sample(leaves, num_to_replace)
        
        variable_values = {}
        
        for i, leaf_node in enumerate(nodes_to_replace):
            # Store the original value
            var_name = f"{variable_name}{i+1}" if num_variables > 1 else variable_name
            variable_values[var_name] = leaf_node.value
            
            # Replace with variable
            leaf_node.value = var_name
            leaf_node.is_variable = True
        
        return node, variable_values
    
    def _collect_leaves(self, node: TreeNode) -> List[TreeNode]:
        """Recursively collect all leaf nodes in the tree."""
        if node is None:
            return []
        
        if node.is_leaf():
            return [node]
        
        leaves = []
        leaves.extend(self._collect_leaves(node.left))
        leaves.extend(self._collect_leaves(node.right))
        
        return leaves
    
    # ==================== EVALUATION ====================
    
    def evaluate_tree(self, node: TreeNode, variable_values: Optional[Dict[str, int]] = None) -> int:
        """
        Evaluate the arithmetic expression represented by the tree.
        
        Args:
            node: Root of the expression tree
            variable_values: Optional dict mapping variable names to values
        
        Returns:
            The computed result
        """
        if node.is_leaf():
            if node.is_variable:
                if variable_values is None or node.value not in variable_values:
                    raise ValueError(f"Variable '{node.value}' has no assigned value")
                return variable_values[node.value]
            return node.value
        
        left_val = self.evaluate_tree(node.left, variable_values)
        right_val = self.evaluate_tree(node.right, variable_values)
        
        if node.value == '+':
            return left_val + right_val
        elif node.value == '-':
            return left_val - right_val
        elif node.value == '*':
            return left_val * right_val
        elif node.value == '/':
            if right_val == 0:
                raise ValueError("Division by zero!")
            return int(left_val / right_val)
        elif node.value == '%':
            if right_val == 0:
                raise ValueError("Modulo by zero!")
            return left_val % right_val
        elif node.value in ['^', '**']:
            return left_val ** right_val
        else:
            raise ValueError(f"Unknown operator: {node.value}")
    
    # ==================== STRING CONVERSION ====================
    
    def tree_to_expression(self, node: TreeNode) -> str:
        """Convert tree to a string expression with minimal parentheses.
        
        Only adds brackets where they affect operator precedence:
        - Around lower precedence operators when they're children of higher precedence operators
        - For right-associative issues (e.g., a - (b - c) vs a - b - c)
        - Specifically: additive operators (+, -) under multiplicative operators (*, /, %, ^)
        """
        if node.is_leaf():
            return str(node.value)
        
        left_expr = self.tree_to_expression(node.left)
        right_expr = self.tree_to_expression(node.right)
        
        op = node.value
        op_prec = self.PRECEDENCE.get(op, 0)
        
        # Check if left child needs brackets
        # Brackets needed if: child precedence < parent precedence OR right-associative issue
        left_needs_brackets = False
        if not node.left.is_leaf():
            left_child_op = node.left.value
            left_child_prec = self.PRECEDENCE.get(left_child_op, 0)
            
            # Lower precedence always needs brackets
            if left_child_prec < op_prec:
                left_needs_brackets = True
            # For right-associative issues: - or / need brackets on left if same precedence
            elif op in ['-', '/', '%'] and left_child_prec == op_prec:
                left_needs_brackets = True
        
        if left_needs_brackets:
            left_expr = f"({left_expr})"
        
        # Check if right child needs brackets
        # Brackets needed if: child precedence < parent precedence OR right-associative issue
        right_needs_brackets = False
        if not node.right.is_leaf():
            right_child_op = node.right.value
            right_child_prec = self.PRECEDENCE.get(right_child_op, 0)
            
            # Lower precedence always needs brackets
            if right_child_prec < op_prec:
                right_needs_brackets = True
            # For right-associative issues: -, /, %, ^ need brackets on right if same or lower precedence
            elif op in ['-', '/', '%', '^', '**'] and right_child_prec <= op_prec:
                right_needs_brackets = True
        
        if right_needs_brackets:
            right_expr = f"({right_expr})"
        
        return f"{left_expr} {op} {right_expr}"
    
    def print_tree(self, node: TreeNode, level: int = 0, prefix: str = "Root: ") -> None:
        """Print the tree structure in a readable format."""
        if node is not None:
            marker = "[VAR]" if node.is_variable else ""
            print(" " * (level * 4) + prefix + str(node.value) + marker)
            if not node.is_leaf():
                self.print_tree(node.left, level + 1, "L--- ")
                self.print_tree(node.right, level + 1, "R--- ")
    
    # ==================== BATCH GENERATION ====================
    
    def generate_expressions_for_target(
        self, 
        target: int, 
        complexity: int, 
        count: int = 10,
        allowed_operators: Optional[List[str]] = None
    ) -> List[str]:
        """
        Generate multiple expressions that evaluate to the target value.
        
        Args:
            target: The target result value
            complexity: Complexity level (1-5)
            count: Number of expressions to generate
            allowed_operators: List of operators to use (defaults to ['+', '-', '*', '/'])
        
        Returns:
            List of expression strings that all evaluate to target
        """
        if allowed_operators is None:
            allowed_operators = ['+', '-', '*', '/']
        
        expressions = []
        attempts = 0
        max_attempts = count * 50
        max_depth = complexity + 1
        
        while len(expressions) < count and attempts < max_attempts:
            tree = self.generate_expression_tree(max_depth, target, allowed_operators)
            expr = self.tree_to_expression(tree)
            
            if self._verify_expression(expr, target) and expr not in expressions:
                expressions.append(expr)
            
            attempts += 1
        
        return expressions
    
    def generate_equations_for_target(
        self,
        target: int,
        complexity: int,
        count: int = 10,
        num_variables: int = 1,
        variable_name: str = "x",
        allowed_operators: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate equations (expressions with variables) that evaluate to target.
        
        Args:
            target: The target result value
            complexity: Complexity level (1-5)
            count: Number of equations to generate
            num_variables: Number of variables per equation
            variable_name: Base name for variables
            allowed_operators: List of operators to use
        
        Returns:
            List of dicts with keys: 'equation', 'variables', 'target'
        """
        if allowed_operators is None:
            allowed_operators = ['+', '-', '*', '/']
        
        equations = []
        attempts = 0
        max_attempts = count * 50
        max_depth = complexity + 1
        
        while len(equations) < count and attempts < max_attempts:
            # Generate expression tree
            tree = self.generate_expression_tree(max_depth, target, allowed_operators)
            
            # Convert to equation
            eq_tree, var_values = self.tree_to_equation(tree, variable_name, num_variables)
            equation_str = self.tree_to_expression(eq_tree)
            
            # Verify it still evaluates correctly
            try:
                result = self.evaluate_tree(eq_tree, var_values)
                if result == target and equation_str not in [e['equation'] for e in equations]:
                    equations.append({
                        'equation': equation_str,
                        'variables': var_values,
                        'target': target
                    })
            except:
                pass
            
            attempts += 1
        
        return equations
    
    def _verify_expression(self, expression: str, target: int) -> bool:
        """Verify that the expression evaluates to the target."""
        try:
            allowed_chars = set('0123456789+-*/() .')
            if not all(c in allowed_chars for c in expression):
                return False
            
            result = eval(expression)
            return abs(result - target) < 0.0001
        except:
            return False
    
    # ==================== PROMPT GENERATION ====================
    
    def generate_test_case(
        self,
        target: int,
        complexity: int,
        language: str = "en",
        style: str = "linguistic",
        count: int = 1,
        mode: str = "expression"  # "expression" or "equation"
    ) -> Dict[str, Any]:
        """
        Generate a complete test case with expressions/equations and prompts.
        
        Args:
            target: Target value
            complexity: Complexity level (1-5)
            language: Language for prompts
            style: Prompt style
            count: Number of items to generate
            mode: "expression" for pure expressions, "equation" for equations with variables
        
        Returns:
            Dict containing test case data
        """
        test_case = {
            "target": target,
            "complexity": complexity,
            "language": language,
            "style": style,
            "mode": mode,
            "items": [],
            "prompts": [],
            "expressions": []
        }
        
        # Map language string to enum
        language_map = {
            'en': Language.EN,
            'fr': Language.FR,
            'es': Language.ES,
            'de': Language.DE,
            'zh': Language.ZH,
            'ua': Language.UA,
        }
        prompt_language = language_map.get(language, Language.EN)
        
        # Initialize PromptEngine for prompt generation
        prompt_engine = PromptEngine()
        
        if mode == "expression":
            expressions = self.generate_expressions_for_target(target, complexity, count)
            test_case["items"] = expressions
            test_case["expressions"] = expressions
            
            # Use PromptEngine to generate prompts
            for expr in expressions:
                context = create_math_context(
                    language=prompt_language.value,
                    style=style,
                    expression=expr
                )
                result = prompt_engine.generate(context)
                test_case["prompts"].append(result.user_prompt)
        
        elif mode == "equation":
            equations = self.generate_equations_for_target(target, complexity, count)
            test_case["items"] = equations
            
            # For equations, generate prompts with PromptEngine
            for eq_data in equations:
                context = create_math_context(
                    language=prompt_language.value,
                    style=style,
                    expression=eq_data['equation']
                )
                result = prompt_engine.generate(context)
                test_case["prompts"].append(result.user_prompt)
        
        return test_case


# ==================== CLI USAGE ====================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python MathExpressionGenerator.py <depth> <target> [operators...]")
        print("Example: python MathExpressionGenerator.py 3 42 + - *")
        print("\nModes:")
        print("  --expression : Generate pure expressions (default)")
        print("  --equation   : Generate equations with variables")
        sys.exit(1)
    
    depth = int(sys.argv[1])
    target = int(sys.argv[2])
    
    # Parse mode
    mode = "expression"
    if "--equation" in sys.argv:
        mode = "equation"
        sys.argv.remove("--equation")
    
    operators = sys.argv[3:] if len(sys.argv) > 3 else ['+', '-', '*', '/']
    
    gen = MathExpressionGenerator(seed=42)
    
    if mode == "expression":
        print(f" Generating expression tree (depth={depth}, target={target})")
        print(f"Operators: {operators}\n")
        
        tree = gen.generate_expression_tree(depth, target, operators)
        
        print("Tree structure:")
        gen.print_tree(tree)
        print()
        
        expression = gen.tree_to_expression(tree)
        print(f"Expression: {expression}")
        
        result = gen.evaluate_tree(tree)
        print(f"Evaluates to: {result}")
        print(f"Matches target: {result == target}")
    
    elif mode == "equation":
        print(f"Generating equation (depth={depth}, target={target})")
        print(f"Operators: {operators}\n")
        
        tree = gen.generate_expression_tree(depth, target, operators)
        eq_tree, var_values = gen.tree_to_equation(tree, variable_name="x", num_variables=1)
        
        print("Equation tree structure:")
        gen.print_tree(eq_tree)
        print()
        
        equation = gen.tree_to_expression(eq_tree)
        print(f"Equation: {equation} = {target}")
        print(f"Variables: {var_values}")
        
        result = gen.evaluate_tree(eq_tree, var_values)
        print(f"Verification: {result}")
        print(f"Correct: {result == target}")