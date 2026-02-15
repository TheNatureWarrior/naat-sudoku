from typing import Optional, Generator, Iterable
import re
import functools

from src.sudoku.cell import Cell
from src.sudoku import constants as c


def _each_division(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        for x in range(c.MAGIC_NUM):
            for _func in {self.row, self.column, self.box}: #TODO: if don't just remove this, make that a tuple or list
                #TODO: also, switch this. Should go by units, then numbers. Weird to do it like this tbh.
                cells = _func(x)
                result = func(self, *args, **kwargs, _cells = cells)
                if result is True:
                    return True
        return None
    return wrapper

def _transformation(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        return self._reset_grid_state(had_changes = result)
    return wrapper


class Grid:
    def __init__(self, *cells: Cell):
        self._rows = []
        self._columns = []
        self._boxes = []
        for x in range(c.MAGIC_NUM):
            for _list in [self._rows, self._columns, self._boxes]:
                _list.append([None for _ in range(c.MAGIC_NUM)])
        for row_num in range(c.MAGIC_NUM):
            for col_num in range(c.MAGIC_NUM):
                self._set_cell(Cell(row = row_num, column = col_num))
        #TODO: tuples of lists instead of list of lists?
        for cell in cells:
            if not isinstance(cell, Cell):
                #TODO: make more flexible, check for specific implementations
                # Bare minimum, it needs row, column, and candidates.
                # Then convert to Cell.
                raise TypeError(f'cell must be Cell, not {type(cell)}')
            self._set_cell(cell)
        #TODO: put basic solve after these.
        self._basic_solve()
        self._selected_cell = None
        self._bi_value_cells = []
        self._tri_value_cells = []
        self._strong_links = None
        self._clear_cell_collections = True
        self._reset_cell_collections = True
        self._reset_grid_state(had_changes = True)


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

    def set_cell(self, cell: Cell) -> None:
        self._set_cell(cell)
        if cell.solved and not cell.previously_solved:
            self._basic_solve()

    @_each_division
    def _basic_solve(self, _cells: Iterable[Cell] = None):
        #TODO: fix this whole system.
        values = set()
        for cell in _cells:
            if cell.solved:
                values.add(cell.value)
        for cell in _cells:
            for value in values:
                cell.remove(value)
                self.set_cell(cell)


    def _reset_grid_state(self, had_changes : Optional[bool] = False) -> bool:
        #TODO: change default to none (again, trying to keep everything pretty close to how it was before)
        if had_changes is not False:
            for cell in self.cells():
                if not had_changes and cell.changed:
                    had_changes = True
                cell.reset_changed()
                self.set_cell(cell)
            if had_changes:
                self._clear_cell_collections = True
                return True
        return False

    def _prep_cell_collections(self) -> None:
        if self._clear_cell_collections:
            self._bi_value_cells.clear()
            self._tri_value_cells.clear()
            self._strong_links = None
            for cell in self.cells(include_solved = False):
                cell_length = len(cell)
                if cell_length > 3:
                    continue
                elif cell_length == 3:
                    self._tri_value_cells.append(cell)
                elif cell_length == 2:
                    self._bi_value_cells.append(cell)
            self._clear_cell_collections = False

    @property
    def bi_value_cells(self) -> list[Cell]:
        self._prep_cell_collections()
        return self._bi_value_cells.copy()

    @property
    def tri_value_cells(self) -> list[Cell]:
        self._prep_cell_collections()
        return self._tri_value_cells.copy()

    @staticmethod
    def find_strong_link(cells : Iterable[Cell], num : int, includes : Optional[Cell] = None) -> tuple[Cell, Cell] | None:
        cell_list = []
        for cell in cells:
            if num in cell:
                if cell.solved:
                    return None
                else:
                    cell_list.append(cell)
        if len(cell_list) == 2:
            if includes is None:
                return cell_list[0], cell_list[1]
            else:
                if cell_list[0] == includes:
                    return cell_list[0], cell_list[1]
                elif cell_list[1] == includes:
                    return cell_list[1], cell_list[0]
                else:
                    return None

    def are_strongly_linked(self, a : Cell, b : Cell, value : int) -> bool:
        if a.solved or b.solved or value not in a or value not in b:
            return False
        pair = {a, b}
        for div_name in {"row", "column", "box"}:
            if a.aligned(b, div_name):
                for cell in self.division(div_name, a):
                    if cell.solved:
                        continue
                    if value in cell:
                        if cell in pair:
                            continue
                        break
                else:
                    return True
        return False

    @staticmethod # TODO: turn into *cells
    def find_bi_sets(cells : Iterable[Cell]) -> Generator[list[Cell], None, None]:
        bi_value_cells = []
        for cell in cells:
            if len(cell) == 2:
                bi_value_cells.append(cell) # TODO: Would it be faster to just.. check against bi_value_cells?
        bi_values = []
        for cell in bi_value_cells:
            for already_matching in bi_values:
                if cell.candidates == already_matching[0].candidates:
                    already_matching.append(cell)
                    break
            else:
                bi_values.append(cell)
        for matched_cell in bi_values:
            yield matched_cell

    