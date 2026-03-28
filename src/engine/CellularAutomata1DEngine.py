"""
1D Cellular Automata Engine

Implements elementary cellular automata (Wolfram rules 0-255) for benchmark testing.
Each cell's next state depends on itself and its two immediate neighbors (3-bit pattern).

Rule encoding:
- Rules 0-255 map 8 possible 3-bit neighborhoods to binary outputs
- Neighborhood pattern: (left, center, right) → output
- Rule number encodes the truth table as 8-bit binary

Famous rules:
- Rule 30: Chaotic, pseudo-random
- Rule 110: Turing complete, complex patterns
- Rule 90: Fractal (Sierpiński triangle)
- Rule 184: Traffic flow model
"""

from typing import List, Tuple, Literal, Dict, Optional
import random


class CellularAutomata1DEngine:
    """Engine for 1D elementary cellular automata (Wolfram rules)."""
    
    # Rule difficulty classification
    DIFFICULTY_RULES = {
        "easy": [0, 51, 204, 255],           # Trivial: all dead, identity, all alive
        "medium": [90, 150, 184, 105],       # Fractal/predictable patterns
        "hard": [30, 110, 45, 73, 54]        # Chaotic/complex behavior
    }
    
    # Rule characteristics for test generation
    RULE_DESCRIPTIONS = {
        0: "All cells die",
        30: "Chaotic pattern generator",
        51: "Identity (cells copy left neighbor)",
        54: "Sierpiński triangle variant",
        60: "XOR with left neighbor",
        90: "Sierpiński triangle (fractal)",
        94: "Traffic-like patterns",
        102: "Identity (cells stay same)",
        105: "Identity with shift",
        110: "Turing complete automaton",
        150: "XOR of neighbors",
        184: "Traffic flow model",
        204: "Identity (cells copy center)",
        255: "All cells alive"
    }
    
    @staticmethod
    def get_neighborhood(
        state: List[int],
        idx: int,
        boundary: Literal["wrap", "dead", "alive"] = "wrap"
    ) -> Tuple[int, int, int]:
        """
        Get the 3-bit neighborhood (left, center, right) for a cell.
        
        Args:
            state: Current state as list of 0s and 1s
            idx: Index of the cell
            boundary: Boundary condition handling
                - "wrap": Periodic boundary (toroidal)
                - "dead": Fixed boundary with 0s
                - "alive": Fixed boundary with 1s
        
        Returns:
            Tuple of (left, center, right) cell values
        """
        n = len(state)
        center = state[idx]
        
        if boundary == "wrap":
            left = state[(idx - 1) % n]
            right = state[(idx + 1) % n]
        elif boundary == "dead":
            left = state[idx - 1] if idx > 0 else 0
            right = state[idx + 1] if idx < n - 1 else 0
        elif boundary == "alive":
            left = state[idx - 1] if idx > 0 else 1
            right = state[idx + 1] if idx < n - 1 else 1
        else:
            raise ValueError(f"Unknown boundary condition: {boundary}")
        
        return (left, center, right)
    
    @staticmethod
    def apply_rule(rule_number: int, neighborhood: Tuple[int, int, int]) -> int:
        """
        Apply a Wolfram rule to a 3-bit neighborhood.
        
        The rule number encodes the truth table:
        - Neighborhood patterns: 111, 110, 101, 100, 011, 010, 001, 000
        - Pattern index: left*4 + center*2 + right
        - Output: bit at position [pattern_index] in rule_number
        
        Args:
            rule_number: Wolfram rule (0-255)
            neighborhood: (left, center, right) tuple of 0s and 1s
        
        Returns:
            Next state of the center cell (0 or 1)
        
        Example:
            Rule 30 = 00011110₂
            Neighborhood (0,1,1) → index 3 → bit 3 of 30 → 1
        """
        if not 0 <= rule_number <= 255:
            raise ValueError(f"Rule number must be 0-255, got {rule_number}")
        
        left, center, right = neighborhood
        pattern_index = left * 4 + center * 2 + right
        
        # Extract bit at position pattern_index from rule_number
        return (rule_number >> pattern_index) & 1
    
    @staticmethod
    def next_state(
        state: List[int],
        rule_number: int,
        boundary: Literal["wrap", "dead", "alive"] = "wrap"
    ) -> List[int]:
        """
        Compute the next generation of the cellular automaton.
        
        Args:
            state: Current state as list of 0s and 1s
            rule_number: Wolfram rule to apply (0-255)
            boundary: Boundary condition
        
        Returns:
            Next generation state
        """
        new_state = []
        for idx in range(len(state)):
            neighborhood = CellularAutomata1DEngine.get_neighborhood(state, idx, boundary)
            new_cell = CellularAutomata1DEngine.apply_rule(rule_number, neighborhood)
            new_state.append(new_cell)
        
        return new_state
    
    @staticmethod
    def evolve(
        initial_state: List[int],
        rule_number: int,
        steps: int,
        boundary: Literal["wrap", "dead", "alive"] = "wrap"
    ) -> List[List[int]]:
        """
        Evolve the cellular automaton for multiple steps.
        
        Args:
            initial_state: Initial configuration
            rule_number: Wolfram rule to apply
            steps: Number of generations to compute
            boundary: Boundary condition
        
        Returns:
            List of states, including initial state and all subsequent generations
        """
        history = [initial_state]
        current_state = initial_state
        
        for _ in range(steps):
            current_state = CellularAutomata1DEngine.next_state(
                current_state, rule_number, boundary
            )
            history.append(current_state)
        
        return history
    
    @staticmethod
    def generate_random_state(width: int, density: float = 0.5) -> List[int]:
        """
        Generate a random initial state.
        
        Args:
            width: Number of cells
            density: Probability of a cell being alive (1)
        
        Returns:
            Random state as list of 0s and 1s
        """
        return [1 if random.random() < density else 0 for _ in range(width)]
    
    @staticmethod
    def generate_centered_state(width: int, pattern: str = "single") -> List[int]:
        """
        Generate a state with a centered pattern.
        
        Args:
            width: Number of cells
            pattern: Pattern type
                - "single": Single alive cell at center
                - "pair": Two adjacent alive cells at center
                - "triplet": Three adjacent alive cells at center
        
        Returns:
            State with centered pattern
        """
        state = [0] * width
        center = width // 2
        
        if pattern == "single":
            state[center] = 1
        elif pattern == "pair":
            state[center] = 1
            state[center + 1] = 1
        elif pattern == "triplet":
            state[center - 1] = 1
            state[center] = 1
            state[center + 1] = 1
        else:
            raise ValueError(f"Unknown pattern: {pattern}")
        
        return state
    
    @staticmethod
    def state_to_string(state: List[int], alive_char: str = "1", dead_char: str = "0") -> str:
        """Convert state to string representation."""
        return " ".join(alive_char if cell else dead_char for cell in state)
    
    @staticmethod
    def string_to_state(s: str, alive_char: str = "1") -> List[int]:
        """Parse string representation to state list."""
        tokens = s.strip().split()
        return [1 if token == alive_char else 0 for token in tokens]
    
    @staticmethod
    def get_rule_difficulty(rule_number: int) -> str:
        """
        Classify a rule's difficulty.
        
        Args:
            rule_number: Wolfram rule (0-255)
        
        Returns:
            "easy", "medium", or "hard"
        """
        for difficulty, rules in CellularAutomata1DEngine.DIFFICULTY_RULES.items():
            if rule_number in rules:
                return difficulty
        return "medium"  # Default for unclassified rules
    
    @staticmethod
    def get_rule_description(rule_number: int) -> str:
        """Get human-readable description of a rule."""
        return CellularAutomata1DEngine.RULE_DESCRIPTIONS.get(
            rule_number,
            f"Elementary cellular automaton rule {rule_number}"
        )
    
    @staticmethod
    def format_rule_table(rule_number: int, alive_char: str = "1", dead_char: str = "0") -> str:
        """
        Format the rule as a visual truth table.
        
        Returns ASCII representation like:
        111 110 101 100 011 010 001 000
         0   0   0   1   1   1   1   0   (Rule 30)

        When alive_char/dead_char differ from '1'/'0', the markers are
        substituted in both the neighbourhood patterns and the output row.
        """
        def _m(v):
            return alive_char if v else dead_char

        neighborhoods = [
            (1,1,1), (1,1,0), (1,0,1), (1,0,0),
            (0,1,1), (0,1,0), (0,0,1), (0,0,0)
        ]
        
        pattern_rules = "\n".join(
            f"{_m(l)}{_m(c)}{_m(r)} -> {_m(CellularAutomata1DEngine.apply_rule(rule_number, (l, c, r)))}"
            for l, c, r in neighborhoods
        )
        
        return pattern_rules
        
        # pattern_line = " ".join(f"{_m(l)}{_m(c)}{_m(r)}" for l, c, r in neighborhoods)
        # output_line = " ".join(
        #     f" {_m(CellularAutomata1DEngine.apply_rule(rule_number, n))} "
        #     for n in neighborhoods
        # )
        
        # return f"{pattern_line}\n{output_line}  (Rule {rule_number})"


class CellularAutomataTestGenerator:
    """Generate test cases for 1D cellular automata benchmarks."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize generator with optional random seed."""
        self.seed = seed
        if seed is not None:
            random.seed(seed)
    
    def generate_test_case(
        self,
        rule_number: int,
        width: int = 16,
        steps: int = 1,
        boundary: Literal["wrap", "dead", "alive"] = "wrap",
        initial_pattern: Literal["random", "centered_single", "centered_pair", "centered_triplet"] = "random",
        density: float = 0.5
    ) -> Dict:
        """
        Generate a single test case.
        
        Args:
            rule_number: Wolfram rule to test
            width: Number of cells
            steps: Number of generations to predict
            boundary: Boundary condition
            initial_pattern: How to initialize the state
            density: For random initialization, probability of alive cells
        
        Returns:
            Dictionary with initial_state, expected_states (for each step), and metadata
        """
        # Generate initial state
        if initial_pattern == "random":
            initial_state = CellularAutomata1DEngine.generate_random_state(
                width, density
            )
        elif initial_pattern.startswith("centered_"):
            pattern_type = initial_pattern.replace("centered_", "")
            initial_state = CellularAutomata1DEngine.generate_centered_state(width, pattern_type)
        else:
            raise ValueError(f"Unknown initial pattern: {initial_pattern}")
        
        # Compute expected evolution
        history = CellularAutomata1DEngine.evolve(initial_state, rule_number, steps, boundary)
        
        return {
            "rule_number": rule_number,
            "width": width,
            "steps": steps,
            "boundary": boundary,
            "initial_state": initial_state,
            "expected_states": history[1:],  # Exclude initial state
            "difficulty": CellularAutomata1DEngine.get_rule_difficulty(rule_number),
            "rule_description": CellularAutomata1DEngine.get_rule_description(rule_number)
        }
    
    def generate_batch(
        self,
        rule_numbers: List[int],
        width: int = 16,
        steps: int = 1,
        cases_per_rule: int = 5,
        **kwargs
    ) -> List[Dict]:
        """
        Generate a batch of test cases for multiple rules.
        
        Args:
            rule_numbers: List of Wolfram rules to test
            width: Number of cells
            steps: Number of generations
            cases_per_rule: Number of test cases per rule
            **kwargs: Additional arguments for generate_test_case
        
        Returns:
            List of test case dictionaries
        """
        test_cases = []
        
        for rule_number in rule_numbers:
            for _ in range(cases_per_rule):
                test_case = self.generate_test_case(
                    rule_number, width, steps, **kwargs
                )
                test_cases.append(test_case)
        
        return test_cases
