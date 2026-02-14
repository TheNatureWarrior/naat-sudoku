from typing import Optional, Generator
import re

from src.sudoku.cell import Cell
from src.sudoku import constants as c


class Grid:
    def __init__(self, *cells: Cell):
        blank_unit: list[Optional[Cell]] = [None for _ in range(c.MAGIC_NUM)]
        self._rows = [blank_unit for _ in range(c.MAGIC_NUM)]
        self._columns = [blank_unit for _ in range(c.MAGIC_NUM)]
        self._boxes = [blank_unit for _ in range(c.MAGIC_NUM)]
        #TODO: tuples of lists instead of list of lists?
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


    @staticmethod
    def text_to_grid(text: str) -> "Grid":
        text = text.replace(',', '')
        text = re.sub(r'\D+', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        text_list = text.split(' ')
        cell_list = []
        for i in range(len(text_list)):
            cell_candidates = []
            for candidate in text_list[i]:
                cell_candidates.append(int(candidate))  # Dependent on MAGIC_NUM < 10
            cell_row = i // c.MAGIC_NUM
            cell_col = i % c.MAGIC_NUM
            cell = Cell(*cell_candidates, row=cell_row, column=cell_col)
            cell_list.append(cell)
        return Grid(*cell_list)


    def __str__(self) -> str:
        row_divisor = '+------------------------------+------------------------------+------------------------------+'
        _temp_list = [row_divisor]
        counter = 0
        for row in self._rows:
            counter += 1
            row_str = '|'
            cell_counter = 0
            for cell in row:
                cell_counter += 1
                candidates = [str(x) for x in cell.candidates]
                candidates.sort()
                cell_str = f" {''.join(candidates):<9}"
                row_str += cell_str
                if cell_counter == 3:
                    cell_counter = 0
                    row_str += '|'
            _temp_list.append(row_str)
            if counter == 3:
                counter = 0
                _temp_list.append(row_divisor)
        return '\n'.join(_temp_list)

    def __eq__(self, other) -> bool:
        if isinstance(other, Grid):
            return str(self) == str(other)
        elif isinstance(other, str):
            if str(self) == other:
                return True
            else:
                try:
                    new_other = self.text_to_grid(other)
                    return self.__eq__(new_other)
                except Exception:
                    return NotImplemented
        else:
            if str(self) == str(other):
                return True
            return NotImplemented


    #TODO: look at converting a lot of these lists to tuples.
    def __getitem__(self, i: int, /) -> list[Cell]:
        return self.row(i)

    def _cells(self) -> Generator[Cell, None, None]:
        for row in self._rows:
            for cell in row:
                yield cell

    def cells(self, include_solved : bool = False) -> Generator[Cell, None, None]:
        if include_solved:
            yield from self._cells()
        else:
            for cell in self._cells():
                if not cell.solved:
                    yield cell


    def row(self, i: int, /) -> list[Cell]:
        return self._rows[i].copy()
    def column(self, i: int, /) -> list[Cell]:
        return self._columns[i].copy()
    def box(self, i: int, /) -> list[Cell]:
        return self._boxes[i].copy()

    def strip(self, i: int, /) -> list[Cell]:
        cells = []
        start = i * 3
        cells.extend(self.row(start))
        cells.extend(self.row(start + 1))
        cells.extend(self.row(start + 2))
        return cells

    def chute(self, i: int, /) -> list[Cell]:
        cells = []
        start = i * 3
        cells.extend(self.column(start))
        cells.extend(self.column(start + 1))
        cells.extend(self.column(start + 2))
        return cells


    def visible_from(self, cell: Cell, include_solved = False) -> list[Cell]:
        seen_cells = []
        row = cell.row
        column = cell.column
        for _cell in self.row(row):
            if _cell.column == column:
                continue
            seen_cells.append(_cell)
        for _cell in self.column(column):
            if _cell.row == row:
                continue
            seen_cells.append(_cell)
        for _cell in self.box(cell.box):
            if _cell.row == row or _cell.column == column:
                continue
            seen_cells.append(_cell)
        if not include_solved:
            seen_cells = [x for x in seen_cells if not x.solved]
        return seen_cells


    def division(self, division : str, position : int | Cell):
        if isinstance(position, Cell):
            position = position.position(division)
        if division == 'row':
            return self.row(position)
        elif division == 'column':
            return self.column(position)
        elif division == 'box':
            return self.box(position)
        elif division == 'chute':
            return self.chute(position)
        elif division == 'strip':
            return self.strip(position)
        else:
            raise TypeError(f'Unknown division {division}')


    def _set_cell(self, cell: Cell) -> None:
        # I know for now this is mostly unnecessary since Cells are mutable, but I may change that eventually.
        self._rows[cell.row][cell.column] = cell
        self._columns[cell.column][cell.row] = cell
        self._boxes[cell.box][cell.box_cell] = cell
