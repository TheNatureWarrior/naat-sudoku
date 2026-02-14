from src.sudoku.cell import Cell
from src.sudoku import constants as c


class Grid:
    def __init__(self, *cells: Cell):
        blank_unit = [None for _ in range(c.MAGIC_NUM)]
        self._rows = [blank_unit for _ in range(c.MAGIC_NUM)]
        self._columns = [blank_unit for _ in range(c.MAGIC_NUM)]
        self._boxes = [blank_unit for _ in range(c.MAGIC_NUM)]
        for cell in cells:
            if not isinstance(cell, Cell):
                #TODO: make more flexible, check for specific implementations
                # Bare minimum, it needs row, column, and candidates.
                # Then convert to Cell.
                raise TypeError(f'cell must be Cell, not {type(cell)}')
            self._set_cell(cell)
        for row_num, row in enumerate(self._rows):
            for col_num in range(len(row)):
                if row[col_num] is None:
                    self._set_cell(Cell(row = row_num, column = col_num))


    def _set_cell(self, cell: Cell) -> None:
        # I know for now this is mostly unnecessary since Cells are mutable, but I may change that eventually.
        self._rows[cell.row][cell.column] = cell
        self._columns[cell.column][cell.row] = cell
        self._boxes[cell.box][cell.box_cell] = cell
