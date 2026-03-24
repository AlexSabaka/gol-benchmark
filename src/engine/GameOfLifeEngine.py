from typing import List


class GameOfLifeEngine:
    """Core Game of Life logic with optimized neighbor counting"""

    @staticmethod
    def count_neighbors(grid: List[List[int]], row: int, col: int) -> int:
        """Count live neighbors for a cell with bounds checking"""
        count = 0
        height, width = len(grid), len(grid[0])
        directions = [(-1,-1), (-1,0), (-1,1),
                      (0,-1),          (0,1),
                      (1,-1),  (1,0), (1,1)]

        for dr, dc in directions:
            nr, nc = row + dr, col + dc
            if 0 <= nr < height and 0 <= nc < width:
                count += grid[nr][nc]

        return count

    @staticmethod
    def next_state(grid: List[List[int]]) -> List[List[int]]:
        """Apply Game of Life rules to get next state"""
        height, width = len(grid), len(grid[0])
        new_grid = [[0 for _ in range(width)] for _ in range(height)]

        for row in range(height):
            for col in range(width):
                neighbors = GameOfLifeEngine.count_neighbors(grid, row, col)
                current = grid[row][col]

                # Conway's Rules implementation
                if current:
                    new_grid[row][col] = 1 if neighbors in (2, 3) else 0
                else:
                    new_grid[row][col] = 1 if neighbors == 3 else 0

        return new_grid