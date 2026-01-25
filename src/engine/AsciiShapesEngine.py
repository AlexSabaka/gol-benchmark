"""
ASCII Shapes Engine for Visual Spatial Reasoning Tests

Generates ASCII-rendered shapes (rectangles, grids) with configurable:
- Dimensions (width × height)
- Symbols (*, #, █, X, 🟦, etc.)
- Spacing (space, tab, underscore)
- Coordinate labels (numbered axes)
- Fill type (filled vs hollow/border-only)

Tests three question types:
1. Dimensions: "What is the width and height?"
2. Count: "How many symbols in the shape?"
3. Position: "Is there a symbol at position (x, y)?"
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Literal, Optional
import random


@dataclass
class AsciiShape:
    """Represents a rendered ASCII shape with metadata."""
    width: int
    height: int
    symbol: str
    spacing: str
    filled: bool
    coordinate_labels: bool
    rendered: str  # The actual ASCII art
    
    def count_symbols(self) -> int:
        """Count total symbols in the shape."""
        if self.filled:
            return self.width * self.height
        else:
            # Hollow rectangle: perimeter only
            if self.height == 1:
                return self.width
            elif self.width == 1:
                return self.height
            else:
                return 2 * (self.width + self.height) - 4
    
    def has_symbol_at(self, x: int, y: int) -> bool:
        """Check if there's a symbol at 1-indexed coordinates (x, y)."""
        # Convert to 0-indexed
        x_idx = x - 1
        y_idx = y - 1
        
        # Bounds check
        if x_idx < 0 or x_idx >= self.width or y_idx < 0 or y_idx >= self.height:
            return False
        
        if self.filled:
            return True
        else:
            # Hollow: only on borders
            is_top_or_bottom = (y_idx == 0 or y_idx == self.height - 1)
            is_left_or_right = (x_idx == 0 or x_idx == self.width - 1)
            return is_top_or_bottom or is_left_or_right


class AsciiShapesGenerator:
    """Generate ASCII shape test cases with spatial reasoning questions."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize generator with optional reproducibility seed."""
        self.seed = seed
        self.rng = random.Random(seed)
    
    def render_shape(
        self,
        width: int,
        height: int,
        symbol: str,
        spacing: str = " ",
        filled: bool = True,
        coordinate_labels: bool = False
    ) -> str:
        """
        Render an ASCII shape with specified parameters.
        
        Args:
            width: Shape width (number of symbols)
            height: Shape height (number of rows)
            symbol: Character to use for rendering
            spacing: Separator between symbols in a row
            filled: If True, fill interior; if False, border only
            coordinate_labels: If True, add numbered axes
        
        Returns:
            Rendered ASCII art as a string
        """
        lines = []
        
        # Generate shape rows
        for y in range(height):
            row_symbols = []
            for x in range(width):
                if filled:
                    # Fill entire shape
                    row_symbols.append(symbol)
                else:
                    # Hollow: only borders
                    is_border = (y == 0 or y == height - 1 or x == 0 or x == width - 1)
                    row_symbols.append(symbol if is_border else spacing)
            
            lines.append(spacing.join(row_symbols))
        
        # Add coordinate labels if requested
        if coordinate_labels:
            # Calculate column width (for alignment)
            col_width = len(symbol) + len(spacing)
            
            # Top axis (column numbers)
            num_width = len(str(width))
            header_padding = " " * (num_width + 1)  # For row label space
            header = header_padding + spacing.join(str(i + 1).rjust(len(symbol)) for i in range(width))
            
            # Add row numbers
            labeled_lines = [header]
            for i, line in enumerate(lines):
                row_label = str(i + 1).rjust(num_width)
                labeled_lines.append(f"{row_label} {line}")
            
            return "\n".join(labeled_lines)
        else:
            return "\n".join(lines)
    
    def generate_dimension_question(
        self,
        shape: AsciiShape,
        language: str = "en",
        style: str = "casual"
    ) -> Tuple[str, str]:
        """
        Generate a dimension question (width × height).
        
        Returns:
            (question_text, expected_answer)
        """
        # Expected answer format: WxH
        expected = f"{shape.width}x{shape.height}"
        
        # Question already embedded in prompt template
        return ("dimensions", expected)
    
    def generate_count_question(
        self,
        shape: AsciiShape,
        language: str = "en",
        style: str = "casual"
    ) -> Tuple[str, str]:
        """
        Generate a counting question.
        
        Returns:
            (question_text, expected_answer)
        """
        expected = str(shape.count_symbols())
        return ("count", expected)
    
    def generate_position_question(
        self,
        shape: AsciiShape,
        language: str = "en",
        style: str = "casual"
    ) -> Tuple[str, str]:
        """
        Generate a position lookup question.
        
        Returns:
            (question_text with coordinates, expected_answer)
        """
        # Pick a random position to query
        x = self.rng.randint(1, shape.width)
        y = self.rng.randint(1, shape.height)
        
        has_symbol = shape.has_symbol_at(x, y)
        expected = "yes" if has_symbol else "no"
        
        # Return coordinates as part of question data
        return (f"position_{x}_{y}", expected)
    
    def generate_test_case(
        self,
        width: int,
        height: int,
        symbol: str,
        spacing: str = " ",
        filled: bool = True,
        coordinate_labels: bool = False,
        question_type: Literal["dimensions", "count", "position"] = "dimensions",
        language: str = "en",
        style: str = "casual"
    ) -> Dict:
        """
        Generate a complete test case with shape and question.
        
        Args:
            width: Shape width
            height: Shape height
            symbol: Symbol character
            spacing: Spacing between symbols
            filled: Fill interior or border-only
            coordinate_labels: Add axis labels
            question_type: Type of question to generate
            language: Prompt language
            style: Prompt style
        
        Returns:
            Dict with shape data, question, and expected answer
        """
        # Render the shape
        rendered = self.render_shape(
            width=width,
            height=height,
            symbol=symbol,
            spacing=spacing,
            filled=filled,
            coordinate_labels=coordinate_labels
        )
        
        shape = AsciiShape(
            width=width,
            height=height,
            symbol=symbol,
            spacing=spacing,
            filled=filled,
            coordinate_labels=coordinate_labels,
            rendered=rendered
        )
        
        # Generate appropriate question
        if question_type == "dimensions":
            question_key, expected = self.generate_dimension_question(shape, language, style)
        elif question_type == "count":
            question_key, expected = self.generate_count_question(shape, language, style)
        elif question_type == "position":
            question_key, expected = self.generate_position_question(shape, language, style)
        else:
            raise ValueError(f"Unknown question type: {question_type}")
        
        # Parse position coordinates if present
        position_x, position_y = None, None
        if question_key.startswith("position_"):
            parts = question_key.split("_")
            position_x = int(parts[1])
            position_y = int(parts[2])
        
        return {
            "shape": {
                "width": width,
                "height": height,
                "symbol": symbol,
                "spacing": spacing,
                "filled": filled,
                "coordinate_labels": coordinate_labels,
                "rendered": rendered
            },
            "question_type": question_type,
            "question_key": question_key,
            "position": {"x": position_x, "y": position_y} if position_x else None,
            "expected_answer": expected,
            "difficulty": self._estimate_difficulty(width, height, filled, coordinate_labels, question_type)
        }
    
    def _estimate_difficulty(
        self,
        width: int,
        height: int,
        filled: bool,
        coordinate_labels: bool,
        question_type: str
    ) -> str:
        """Estimate difficulty level based on shape complexity."""
        area = width * height
        
        # Base difficulty on area
        if area <= 12:
            base_difficulty = "easy"
        elif area <= 50:
            base_difficulty = "medium"
        else:
            base_difficulty = "hard"
        
        # Modifiers
        if not filled:
            # Hollow shapes are slightly harder for counting
            if question_type == "count" and base_difficulty == "easy":
                base_difficulty = "medium"
        
        if not coordinate_labels and question_type == "position":
            # Position questions harder without labels
            if base_difficulty == "easy":
                base_difficulty = "medium"
        
        return base_difficulty
    
    def generate_batch(
        self,
        width_range: Tuple[int, int],
        height_range: Tuple[int, int],
        symbols: List[str],
        spacings: List[str],
        filled_options: List[bool],
        coordinate_labels: bool,
        question_type: str,
        count: int,
        language: str = "en",
        style: str = "casual"
    ) -> List[Dict]:
        """
        Generate a batch of test cases with random parameters.
        
        Args:
            width_range: (min_width, max_width)
            height_range: (min_height, max_height)
            symbols: List of possible symbols
            spacings: List of possible spacings
            filled_options: List of filled/hollow options [True, False]
            coordinate_labels: Whether to add labels
            question_type: Question type to generate
            count: Number of test cases to generate
            language: Prompt language
            style: Prompt style
        
        Returns:
            List of test case dictionaries
        """
        test_cases = []
        
        for _ in range(count):
            width = self.rng.randint(width_range[0], width_range[1])
            height = self.rng.randint(height_range[0], height_range[1])
            symbol = self.rng.choice(symbols)
            spacing = self.rng.choice(spacings)
            filled = self.rng.choice(filled_options)
            
            test_case = self.generate_test_case(
                width=width,
                height=height,
                symbol=symbol,
                spacing=spacing,
                filled=filled,
                coordinate_labels=coordinate_labels,
                question_type=question_type,
                language=language,
                style=style
            )
            
            test_cases.append(test_case)
        
        return test_cases
