import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path

from src.types import GameState

@dataclass
class PatternMetadata:
    """Metadata extracted from pattern files"""
    name: Optional[str] = None
    comments: List[str] = field(default_factory=list)
    rule: Optional[str] = None
    original_width: Optional[int] = None
    original_height: Optional[int] = None


class ConwayPatternParser:
    """Parser for Conway's Game of Life patterns from conwaylife.com database"""
    
    def __init__(self):
        self.rle_pattern = re.compile(r'(\d*)([bo$!])')
    
    def parse_file(self, file_path: str) -> Tuple[GameState, PatternMetadata]:
        """
        Parse a pattern file (either .rle or .cells format)
        
        Args:
            file_path: Path to the pattern file
            
        Returns:
            Tuple of (GameState, PatternMetadata)
        """
        path = Path(file_path)
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if path.suffix.lower() == '.rle':
            return self.parse_rle(content)
        elif path.suffix.lower() == '.cells':
            return self.parse_cells(content)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
    
    def parse_rle(self, content: str) -> Tuple[GameState, PatternMetadata]:
        """
        Parse RLE format pattern
        
        Args:
            content: RLE file content as string
            
        Returns:
            Tuple of (GameState, PatternMetadata)
        """
        lines = content.strip().split('\n')
        metadata = PatternMetadata()
        pattern_data = ""
        
        # Parse header and comments
        pattern_start_idx = 0
        for i, line in enumerate(lines):
            line = line.strip()
            
            if line.startswith('#N'):  # Name
                metadata.name = line[2:].strip()
            elif line.startswith('#C'):  # Comment
                metadata.comments.append(line[2:].strip())
            elif line.startswith('x ='):  # Header line
                # Parse header: x = width, y = height, rule = rule
                header_match = re.match(r'x\s*=\s*(\d+)\s*,\s*y\s*=\s*(\d+)(?:\s*,\s*rule\s*=\s*([^,\s]+))?', line)
                if header_match:
                    metadata.original_width = int(header_match.group(1))
                    metadata.original_height = int(header_match.group(2))
                    if header_match.group(3):
                        metadata.rule = header_match.group(3)
                pattern_start_idx = i + 1
                break
        
        # Collect pattern data (everything after header until !)
        for i in range(pattern_start_idx, len(lines)):
            line = lines[i].strip()
            if '!' in line:
                pattern_data += line[:line.index('!')]
                break
            pattern_data += line
        
        # Parse the RLE encoded pattern
        grid = self._decode_rle(pattern_data)
        
        return GameState(grid=grid), metadata
    
    def parse_cells(self, content: str) -> Tuple[GameState, PatternMetadata]:
        """
        Parse cells format pattern
        
        Args:
            content: Cells file content as string
            
        Returns:
            Tuple of (GameState, PatternMetadata)
        """
        lines = content.strip().split('\n')
        metadata = PatternMetadata()
        pattern_lines = []
        
        # Parse comments and pattern data
        for line in lines:
            line = line.rstrip()
            if line.startswith('!'):  # Comment line
                comment = line[1:].strip()
                if comment:
                    metadata.comments.append(comment)
                    # Try to extract name from first comment if it looks like a filename
                    if not metadata.name and len(metadata.comments) == 1:
                        if '.' in comment and not comment.startswith('http'):
                            metadata.name = comment.split('.')[0]
            else:
                # Pattern data line
                if line:  # Skip empty lines
                    pattern_lines.append(line)
        
        if not pattern_lines:
            raise ValueError("No pattern data found in cells file")
        
        # Convert cells format to grid
        grid = []
        max_width = max(len(line) for line in pattern_lines) if pattern_lines else 0
        
        for line in pattern_lines:
            row = []
            # Pad line to max width
            padded_line = line.ljust(max_width)
            for char in padded_line:
                if char == 'O':  # Live cell
                    row.append(1)
                elif char == '.' or char == ' ':  # Dead cell
                    row.append(0)
                else:
                    raise ValueError(f"Invalid character in cells file: '{char}'")
            grid.append(row)
        
        metadata.original_width = max_width
        metadata.original_height = len(grid)
        
        return GameState(grid=grid), metadata
    
    def _decode_rle(self, rle_data: str) -> List[List[int]]:
        """
        Decode RLE pattern data into a 2D grid
        
        Args:
            rle_data: RLE encoded pattern string
            
        Returns:
            2D list representing the pattern grid
        """
        # Remove whitespace
        rle_data = re.sub(r'\s+', '', rle_data)
        
        # Find all tokens (count + symbol)
        matches = self.rle_pattern.findall(rle_data)
        
        grid = []
        current_row = []
        
        for count_str, symbol in matches:
            count = int(count_str) if count_str else 1
            
            if symbol == 'b':  # Dead cells
                current_row.extend([0] * count)
            elif symbol == 'o':  # Live cells
                current_row.extend([1] * count)
            elif symbol == '$':  # End of line
                for _ in range(count):
                    grid.append(current_row)
                    current_row = []
            elif symbol == '!':  # End of pattern
                if current_row:
                    grid.append(current_row)
                break
        
        # Handle case where pattern doesn't end with $
        if current_row:
            grid.append(current_row)
        
        # Ensure all rows have the same width
        if grid:
            max_width = max(len(row) for row in grid)
            for row in grid:
                while len(row) < max_width:
                    row.append(0)
        
        return grid
    
    def parse_string(self, content: str, format_type: str) -> Tuple[GameState, PatternMetadata]:
        """
        Parse pattern from string content
        
        Args:
            content: Pattern content as string
            format_type: 'rle' or 'cells'
            
        Returns:
            Tuple of (GameState, PatternMetadata)
        """
        if format_type.lower() == 'rle':
            return self.parse_rle(content)
        elif format_type.lower() == 'cells':
            return self.parse_cells(content)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")


# Example usage and testing
def main():
    parser = ConwayPatternParser()
    
    # Test RLE parsing
    rle_example = """#N 1 beacon
#C Approximately the 32nd-most common oscillator.
#C www.conwaylife.com/wiki/index.php?title=1_beacon
x = 7, y = 7, rule = b3/s23
2b2o3b$bobo3b$o2bob2o$2obo2bo$bobo3b$bo2bo2b$2b2o!"""
    
    print("Parsing RLE example:")
    game_state, metadata = parser.parse_string(rle_example, 'rle')
    print(f"Pattern: {metadata.name}")
    print(f"Rule: {metadata.rule}")
    print(f"Size: {game_state.width}x{game_state.height}")
    print(f"Comments: {len(metadata.comments)} comment(s)")
    print("Grid:")
    for row in game_state.grid:
        print(''.join(['█' if cell else '·' for cell in row]))
    print()
    
    # Test cells parsing
    cells_example = """! 1x256schickengine.cells
! https://conwaylife.com/wiki/One-cell-thick_pattern  
! https://www.conwaylife.com/patterns/1x256schickengine.cells  
OOOOO.OOOO..OOO..OOOOO.OOOO.OOOO..........................OOOOO"""
    
    print("Parsing cells example:")
    game_state, metadata = parser.parse_string(cells_example, 'cells')
    print(f"Pattern: {metadata.name}")
    print(f"Size: {game_state.width}x{game_state.height}")
    print(f"Comments: {len(metadata.comments)} comment(s)")
    print("Grid:")
    for row in game_state.grid:
        print(''.join(['█' if cell else '·' for cell in row]))


if __name__ == "__main__":
    main()