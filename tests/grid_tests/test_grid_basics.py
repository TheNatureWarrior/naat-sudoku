import pytest
from src.sudoku import Cell, Grid

def assertCellsIdentical(actual, expected):
    assert actual.solved == expected.solved
    assert actual.value == expected.value
    assert actual.row == expected.row
    assert actual.column == expected.column
    assert actual.box == expected.box
    assert actual.box_cell == expected.box_cell
    assert actual.candidates == expected.candidates
    assert actual == expected

def assertGridIntegrity(grid : Grid) -> None:
    all_cells = list(grid.cells(include_solved = True))
    assert len(all_cells) == 81
    for row in range(9):
        for col in range(9):
            cell = grid[row][col]
            assert cell.row == row
            assert cell.column == col
            box = cell.box
            box_cell = cell.box_cell
            assertCellsIdentical(grid.row(row)[col], cell)
            assertCellsIdentical(grid.column(col)[row], cell)
            assertCellsIdentical(grid.box(box)[box_cell], cell)
            assertCellsIdentical(grid.division('row', row)[col], cell)
            assertCellsIdentical(grid.division('column', col)[row], cell)
            assertCellsIdentical(grid.division('box', box)[box_cell], cell)
            strip_found = False
            for _cell in grid.strip(cell.strip):
                if _cell == cell:
                    assertCellsIdentical(_cell, cell)
                    strip_found = True
                    break
            assert strip_found
            chute_found = False
            for _cell in grid.chute(cell.chute):
                if _cell == cell:
                    assertCellsIdentical(_cell, cell)
                    chute_found = True
                    break
            assert chute_found
            assert cell in all_cells

class TestGridFundamentals:
    def test_grid_init(self):
        assertGridIntegrity(Grid())


class TestGridSolver:
    def test_solve_specific(self):
        base = """
        +------------------+-------------------+--------------------+
        | 5    267  2378   | 9    14678  147   | 12346 1246 1346    |
        | 4    67   79     | 2    1567   3     | 8     16   156     |
        | 1236 26   238    | 168  14568  145   | 7     9    13456   |
        +------------------+-------------------+--------------------+
        | 269  3    2459   | 16   12569  8     | 12469 7    146     |
        | 2679 1    24579  | 67   25679  257   | 2469  3    468     |
        | 2679 8    279    | 4    123679 127   | 1269  5    16      |
        +------------------+-------------------+--------------------+
        | 237  9    6      | 1378 123478 1247  | 1345  148  134578  |
        | 37   47   1      | 5    3478   9     | 346   468  2       |
        | 8    2457 23457  | 137  12347  6     | 1345  14   9       |
        +------------------+-------------------+--------------------+
        """
        expected = """
        +--------------+--------------+--------------+
        | 5   6   8    | 9   4   7    | 1   2   3    |
        | 4   7   9    | 2   1   3    | 8   6   5    |
        | 1   2   3    | 8   6   5    | 7   9   4    |
        +--------------+--------------+--------------+
        | 9   3   4    | 6   5   8    | 2   7   1    |
        | 6   1   5    | 7   9   2    | 4   3   8    |
        | 7   8   2    | 4   3   1    | 9   5   6    |
        +--------------+--------------+--------------+
        | 2   9   6    | 3   8   4    | 5   1   7    |
        | 3   4   1    | 5   7   9    | 6   8   2    |
        | 8   5   7    | 1   2   6    | 3   4   9    |
        +--------------+--------------+--------------+
        """
        grid = Grid.text_to_grid(base)
        assertGridIntegrity(grid)
        message = ""
        for _ in range(42):
            message = grid.run_round()
            assertGridIntegrity(grid)
            if message in {'Solved.', 'No changes.'}:
                break
        assert grid == expected
        assert message == 'Solved.'
