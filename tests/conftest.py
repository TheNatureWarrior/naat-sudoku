import pytest
from src.sudoku import Cell, Grid

@pytest.fixture(scope = 'function')
def blank_grid():
    yield Grid()
