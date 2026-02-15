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
