import itertools
from typing import Optional, Generator, Iterable, Any
import re
import functools

from src.sudoku.cell import Cell
from src.sudoku import constants as c


def _table_settings(*groups : Iterable[Any]) -> Generator[tuple[Any, ...], None, None]:
    group_orderings = (tuple(itertools.permutations(group)) for group in groups)
    #Ex: ((('a', 'A'), ('A', 'a'), (('b', 'B'), ('B', 'b')))
    for ordered_groups in itertools.product(*group_orderings):
        # Ex: (('a', 'A'), ('B', 'b'))
        for group_order in itertools.permutations(ordered_groups):
            # Ex: (('B', 'b'), ('a', 'A'))
            # and yields flattened version
            yield tuple(itertools.chain.from_iterable(group_order))


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

    def _find_strong_links(self, candidate: int):
        if self._strong_links is None:
            self._strong_links = {}
        linked_cells = []
        for i in range(c.MAGIC_NUM):
            for div in (self.row, self.column, self.box):
                result = self.find_strong_link(div(i), candidate)
                if result is None:
                    continue
                _a, _b = result
                if (_a, _b) in linked_cells or (_b, _a) in linked_cells:
                    continue #TODO: make find_strong_link return in determined order
                linked_cells.append((_a, _b))
        self._strong_links[candidate] = linked_cells

    def find_strong_links(self, candidate: int, sets = False) -> list[tuple[Cell, Cell]] | set[frozenset]:
        if self._strong_links is None or self._strong_links.get(candidate) is None:
            self._find_strong_links(candidate)
        if sets:
            linked_cells = set()
            for link in self._strong_links[candidate]:
                linked_cells.add(frozenset(link))
            return linked_cells
        else:
            return self._strong_links[candidate].copy()


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

    @_transformation
    @_each_division
    def hidden_single_solve(self, _cells: Iterable[Cell] = None):
        _counts = [0, 0, 0, 0, 0, 0, 0, 0, 0] #TODO: Fix this
        for cell in _cells:
            if cell.solved:
                _counts[cell.value - 1] = None
            else:
                for candidate in cell:
                    try:
                        _counts[candidate - 1] += 1
                    except TypeError:
                        raise ValueError('Type error for Cell in hidden solve-- basic solve may be bugged.')
        if 1 in _counts:
            solved_val = _counts.index(1) + 1
            for cell in _cells:
                if solved_val in cell:
                    cell.equals(solved_val)
                    self.set_cell(cell)

    @_each_division
    @_transformation
    def pairs_solve(self, _cells: Iterable[Cell] = None):
        for matched_bi_values in self.find_bi_sets(_cells):
            if len(matched_bi_values) == 2:
                continue
            eligible_cells = []
            for cell in _cells:
                if cell.solved:
                    continue
                if cell in matched_bi_values:
                    continue
                if cell.intersection(matched_bi_values[0]):
                    eligible_cells.append(cell)
            if eligible_cells:
                for cell in eligible_cells:
                    cell.remove(matched_bi_values[0].candidates)
                    self.set_cell(cell)
                return None #TODO: true? Also, remove _each_division
        return None

    @_each_division
    @_transformation
    def hidden_pairs_solve(self, _cells: Iterable[Cell] = None):
        _cells_by_candidate = [set() for _ in range(c.MAGIC_NUM)]
        try:
            for cell in _cells:
                if cell.solved:
                    _cells_by_candidate[cell.value - 1] = None
                else:
                    for candidate in cell:
                        _cells_by_candidate[candidate - 1].add(cell)
        except Exception:
            print(f'Encountered error while processing {", ".join(repr(cell) for cell in _cells)}')
            raise
        interesting_values = []
        for i in range(c.MAGIC_NUM):
            _cells_w_candidate = _cells_by_candidate[i]
            if _cells_w_candidate is None:
                continue
            if len(_cells_w_candidate) != 2:
                continue
            interesting_values.append(i)

        for x, y in itertools.combinations(interesting_values, 2):
            if _cells_by_candidate[x] != _cells_by_candidate[y]:
                continue
            eligible_cells = []
            for cell in _cells_by_candidate[x]:
                if len(cell) == 2:
                    continue
                eligible_cells.append(cell)
            if not eligible_cells:
                continue
            for cell in eligible_cells:
                cell.candidates = [x + 1, y + 1]
                self.set_cell(cell)
            return None
        return None

    @_each_division
    @_transformation
    def triples_solve(self, _cells: Iterable[Cell] = None):
        #TODO: refactor this, so much
        # One thing might be making a subfunction that can be used for quads or triples.
        eligible_cells = []
        for cell in _cells:
            if len(cell) in {2, 3}:
                eligible_cells.append(cell) #TODO: fix naming and such
        if (length:=len(eligible_cells)) >= 3:
            final_candidates = None
            final_cells = None
            for i in reversed(range(length)):
                comparison_pairs = []
                primary_cell = eligible_cells[i]
                primary_candidates = primary_cell.candidates
                comp_cells = eligible_cells[:i]
                for secondary_cell in comp_cells:
                    secondary_candidates = secondary_cell.candidates
                    combo = secondary_candidates.union(primary_candidates)
                    if len(combo) == 3:
                        for comp_cell, comp_candidates in comparison_pairs:
                            if combo.issubset(comp_candidates):
                                final_candidates = comp_candidates #FOUND A TRIAD
                                final_cells = [primary_cell, secondary_cell, comp_cell] # Triad cells
                                break #$$$
                        else:
                            comparison_pairs.append((secondary_cell, combo))
                            continue
                        break # ONly reached if break reached at line with $$$
                else:
                    continue
                break # only reached if line with $$$ was reached # VE
            if final_candidates is not None:
                for cell in _cells:
                    for triple_cell in final_cells:
                        if cell == triple_cell:
                            break # Is one of the triple cells, leave alone
                    else:
                        # Only reached if was not one of the final triple cells
                        cell.remove(final_candidates)
                        self.set_cell(cell)

    @_transformation
    def intersection_removal(self):
        for div_name, other_divisions in {('row', ('box',)) # Box Line reduction
                                          , ('column', ('box',)) # Box Line reduction
                                          , ('box', ('row', 'column')) # Pointing pairs /triples
                                          }: # TODO: refactor so constant order, and have pointing pairs go first
            for i in range(c.MAGIC_NUM):
                _div_cells = self.division(div_name, i)
                _values = list([] for _ in c.VALID_CANDIDATES) #TODO
                for cell in _div_cells:
                    if cell.solved:
                        _values[cell.value - 1] = None
                    else:
                        for val in cell.candidates:
                            _values[val - 1].append(cell)
                            #TODO: Make a function that does this. Have WAY too many functions that do this.
                for j in range(c.MAGIC_NUM):
                    candidate = j + 1
                    cells = _values[j]
                    if cells is None:
                        continue
                    if len(cells) > 3:
                        continue
                    for other_div in other_divisions:
                        _which_spots = set(cell.position(other_div) for cell in cells)
                        if len(_which_spots) != 1: # THe linked cells from div_name aren't all in other_category as well.
                            continue #So keep moving.
                        _pos = _which_spots.pop() # All of them were in one other category, _pos.
                        for _other_cell in self.division(other_div, _pos):
                            for cell in cells: #TODO: FIX
                                if cell == _other_cell:
                                    break # Is one of the original cells, leave alone
                            else:
                                _other_cell.remove(candidate)
                                self.set_cell(_other_cell)

    @_transformation
    @_each_division #TODO: what?
    def hidden_sets(self, count, _cells : Iterable[Cell] = None):
        cells_by_candidate = [[] for _ in c.VALID_CANDIDATES]
        for cell in _cells:
            if cell.solved:
                cells_by_candidate[cell.value - 1] = None
            else:
                for candidate in cell:
                    cells_by_candidate[candidate - 1].append(cell)
        uninteresting_candidates = []
        for i in range(len(cells_by_candidate)):
            candidate = i + 1
            cells_with_candidates = cells_by_candidate[i]
            if cells_with_candidates is None or len(cells_with_candidates) > count:
                uninteresting_candidates.append(candidate)
        interesting_candidates = set(c.VALID_CANDIDATES) - set(uninteresting_candidates)
        for combination in itertools.combinations(interesting_candidates, count):
            _temp_cell_holding = None
            for candidate in combination:
                index = candidate - 1
                if _temp_cell_holding is None:
                    _temp_cell_holding = []
                for cell in cells_by_candidate[index]:
                    _temp_cell_holding.append(cell)
            if len(_temp_cell_holding) == count:
                extra_candidates = c.VALID_CANDIDATES - set(combination)
                for cell in _temp_cell_holding:
                    cell.remove(extra_candidates)
                    self.set_cell(cell)

    @_transformation
    def chute_remote_pairs(self):
        for i in range(3): #TODO: SWap
            for _div in {'chute', 'strip'}:
                if _div == 'chute':
                    _sub_div = 'column'
                else:
                    _sub_div = 'row'
                _cells = self.division(_div, i)
                for bi_valued_cells in self.find_bi_sets(_cells):
                    for cell_a, cell_b in itertools.combinations(bi_valued_cells, 2):
                        if cell_a.sees(cell_b):
                            continue
                        unseen_cells = []
                        double_elimination_cells = []
                        double_seen_cells = []
                        for cell in _cells:
                            if cell == cell_a or cell == cell_b:
                                continue
                            if cell_a.sees(cell) or cell_b.sees(cell):
                                if cell_a.box == cell.box and cell_a.aligned(cell, _sub_div):
                                    double_elimination_cells.append(cell)
                                elif cell_b.box == cell.box and cell_b.aligned(cell, _sub_div):
                                    double_elimination_cells.append(cell)
                                elif cell_a.sees(cell) and cell_b.sees(cell):
                                    double_seen_cells.append(cell)
                                    double_elimination_cells.append(cell)
                                continue
                            unseen_cells.append(cell) #TODO: refactor this logic

                        if len(unseen_cells) != 3:
                            raise ValueError('Unseen cells should always have exactly 3.')
                        candidate_1, candidate_2 = cell_a.candidates
                        removals = set()
                        for cell in unseen_cells:
                            if candidate_1 in cell.candidates:
                                removals.add(candidate_1)
                            if candidate_2 in cell.candidates:
                                removals.add(candidate_2)
                        count_seen = len(removals)
                        if count_seen == 2:
                            continue
                        elif count_seen == 1:
                            candidate = removals.pop()
                            eligible_cells = [_x for _x in double_seen_cells if candidate in _x and not _x.solved]
                            if not eligible_cells:
                                continue
                            for cell in eligible_cells:
                                cell.remove(candidate)
                                self.set_cell(cell)
                            return None #TODO: CLEAN up
                        elif count_seen == 0:
                            eligible_cells = [_x for _x in double_elimination_cells if not _x.solved and _x.intersection(cell_a)]
                            if not eligible_cells:
                                continue
                            for cell in eligible_cells:
                                cell.remove(cell_a.candidates)
                                self.set_cell(cell)
                            return None
                        else:
                            raise ValueError('Saw a weird number of candidates, what?')
        return None

    def _rectangle_elimination(self, candidate : int = None, _cells : Iterable[Cell] = None, other_div: str = None):
        temp = self.find_strong_link(_cells, candidate)
        if temp is None or temp[0].box == temp[1].box: #TODO: use aligned
            return None

        for ordering in [[temp[0], temp[1]], [temp[1], temp[0]]]:
            hinge, wing_1 = ordering
            _wing_range = self.division(other_div, hinge)
            for wing_2 in _wing_range:
                if wing_2.solved:
                    continue
                if wing_2.box == hinge.box or wing_2.box == wing_1.box:
                    continue
                if candidate in wing_2:
                    relevant_box = (wing_2.strip * 3) + wing_1.chute #TODO: make Cell static method for this sort of thing
                    if relevant_box == hinge.box:
                        relevant_box = (wing_1.strip * 3) + wing_2.chute
                    box_cells = self.box(relevant_box)
                    for box_cell in box_cells:
                        if candidate not in box_cell:
                            continue
                        if wing_1.sees(box_cell) or wing_2.sees(box_cell): #TODO: Seen_by
                            continue
                        break # Candidate existed in cell not seen by the two wings. Do nothing.
                    else:
                        # Candidate would go entirely missing from the relevant box if cell == candidate.
                        wing_2.remove(candidate)
                        self.set_cell(wing_2)
                        return True


    @_transformation
    def rectangle_elimination(self):
        for candidate in c.VALID_CANDIDATES:
            for division, other_div in {(self.row, 'column'), (self.column, 'row')}:
                for __i in range(c.MAGIC_NUM):
                    _cells = division(__i)
                    res = self._rectangle_elimination(candidate = candidate, _cells = _cells, other_div = other_div)
                    if res is True:
                        return True
        return None

    @_transformation
    def y_wing(self):
        def _single_intersection(*args: Cell):
            for _a, _b in itertools.combinations(args, 2):
                if len(_a.intersection(_b)) != 1:
                    return False
            return True

        for cell_a, cell_b, cell_c in itertools.combinations(self.bi_value_cells, 3):
            candidates = cell_a.union(cell_b.union(cell_c))
            if len(candidates) != 3:
                continue
            if not _single_intersection(cell_a, cell_b, cell_c):
                continue
            if not cell_a.sees(cell_b) and not cell_a.sees(cell_c): #TODO; fix
                continue
            for hinge, wing_1, wing_2 in itertools.permutations([cell_a, cell_b, cell_c]):
                if not (hinge.sees(wing_1) and hinge.sees(wing_2)):
                    continue
                common_candidate = wing_1.intersection(wing_2)
                if len(common_candidate) != 1:
                    raise ValueError('Should be impossible to get here')
                common_candidate = common_candidate.pop()
                affected_cells = []
                for cell in self.visible_from(wing_1):
                    if common_candidate not in cell.candidates:
                        continue
                    if cell in [hinge, wing_2]:
                        continue
                    if cell.sees(wing_2):
                        affected_cells.append(cell)
                if not affected_cells:
                    continue
                for cell in affected_cells:
                    cell.remove(common_candidate)
                    self.set_cell(cell)
                return None # Cells were modified, exit
        return None

    @_transformation
    def xyz_wing(self):
        for triad in self.tri_value_cells:
            triad_candidates = triad.candidates
            visible_cells = self.visible_from(triad)
            valid_bi_values = []
            for bi in self.bi_value_cells:
                if triad.sees(bi):
                    if bi.candidates.issubset(triad.candidates):
                        valid_bi_values.append(bi)
            if len(valid_bi_values) < 2:
                continue
            for combo in itertools.combinations(valid_bi_values, 2):
                cell_a, cell_b = combo
                if cell_a.row == cell_b.row == triad.row:
                    continue #TODO: fix this
                if cell_a.column == cell_b.column == triad.column:
                    continue
                if cell_a.box == cell_b.box == triad.box:
                    continue
                in_common = cell_a.intersection(cell_b)
                if len(in_common) != 1:
                    continue
                common_candidate = in_common.pop()
                affected_cells = []
                for cell in visible_cells:
                    if common_candidate not in cell:
                        continue
                    if cell.sees(cell_a) and cell.sees(cell_b):
                        affected_cells.append(cell)
                if not affected_cells:
                    continue
                for cell in affected_cells:
                    cell.remove(common_candidate)
                    self.set_cell(cell)
                return None
        return None

    @_transformation
    def bug_squasher(self):
        if len(self.tri_value_cells) != 1:
            return None #BUG not applicable
        for cell in self.cells():
            if len(cell) > 3:
                return None # NOt applicable
        triad = self.tri_value_cells[0]
        for candidate in triad:
            for division_name in {'row', 'column', 'box'}:
                division = self.division(division_name, triad)
                appearances = 0
                for cell in division:
                    if cell == triad:
                        continue
                    if candidate in cell:
                        appearances += 1
                if appearances != 2:
                    break
            else:
                # all divisions, if candidate removed, would have 2 appearances of candidate left. Squashing time
                triad.candidates = {candidate}
                self.set_cell(triad)
                return None
        return None

    @staticmethod
    def chaining(*chain_nodes : Cell, length = 1, final_cell : Cell = None, max_length = 10, cells = None):
        prior_cell = chain_nodes[-1]
        if prior_cell == final_cell:
            if length >= 3:
                yield chain_nodes
            else: #TODO: Combo
                return
        elif length >= max_length:
            return
        elif not cells:
            return
        else:
            temp = [x for x in cells if x.inclusive_sees(prior_cell) and x.intersection(prior_cell)]
            for cell in temp:
                #TODO: add in strong/weak loop logic?
                _cells = cells[:]
                _cells.remove(cell)
                yield from Grid.chaining(*chain_nodes, cell, length = length + 1, final_cell = final_cell, max_length = max_length, cells = _cells)

    def _closed_xy_chain(self, max_chain, valid_bookends):
        for fl_pair, eligible_remaining in valid_bookends.items():
            first_cell, final_cell = fl_pair
            eligible_cells, remaining_cells = eligible_remaining
            for chain in self.chaining(first_cell, final_cell = final_cell, max_length = max_chain, cells = remaining_cells):
                for candidate in first_cell.intersection(final_cell):
                    _eligible_cells = [x for x in eligible_cells if candidate in x and x not in chain]
                    if not _eligible_cells:
                        continue #TODO: remove and check elsewhere? idk
                    other_candidate = (first_cell.candidates - {candidate}).pop()
                    on_value, off_value = other_candidate, candidate
                    cell_b = first_cell
                    i = 1
                    candidate_removals = [(candidate, _eligible_cells)]
                    remaining = [x for x in self.cells() if x not in chain]
                    while i < len(chain):
                        cell_a, cell_b = cell_b, chain[i]
                        if on_value in cell_b:
                            # Weak link between cell_a and cell_b  via on_value
                            _cells = [x for x in remaining if on_value in x and x.inclusive_sees(cell_a) and x.inclusive_sees(cell_b)]
                            if _cells:
                                candidate_removals.append((on_value, _cells))
                            off_value = on_value
                            on_value = (cell_b.candidates - {off_value}).pop()
                        elif off_value in cell_b and self.are_strongly_linked(cell_a, cell_b, off_value):
                            #TODO: skip link here? should be unnecessary due to intersection removal
                            _cells = [x for x in remaining if off_value in x and x.inclusive_sees(cell_a) and x.inclusive_sees(cell_b)]
                            if _cells:
                                candidate_removals.append((off_value, _cells))
                            on_value = off_value
                            off_value = (cell_b.candidates - {on_value}).pop()
                        else:
                            on_value = None
                            break
                        i += 1
                    if on_value is None or on_value != candidate or cell_b != final_cell:
                        continue
                    for _candidate, _eligible_cells in candidate_removals:
                        for cell in eligible_cells:
                            cell.remove(_candidate)
                            self.set_cell(cell)
                    return True
        return None

    @_transformation
    def xy_chain(self, _max_chain: Optional[int] = None):
        bi_values = self.bi_value_cells
        many_bis = len(bi_values)
        if many_bis < 3:
            return None
        if _max_chain is None:
            _max_chain = many_bis
        else:
            _max_chain = min(_max_chain, many_bis)

        valid_bookends, valid_seen_bookends = {}, {}
        for pair in itertools.combinations(bi_values, 2):
            a, b = pair
            candidate_intersection = a.intersection(b)
            if not candidate_intersection:
                continue
            eligible_cells = self.visible_from(a)
            eligible_cells = [x for x in eligible_cells if x.intersection(candidate_intersection) and b.sees(x)]
            if not eligible_cells:
                continue
            remaining_cells = [x for x in bi_values if x != a]
            if a.inclusive_sees(b):
                valid_seen_bookends[(a, b)] = (eligible_cells, remaining_cells)
            else:
                valid_bookends[(a, b)] = (eligible_cells, remaining_cells)

        found = self._closed_xy_chain(max_chain = _max_chain, valid_bookends = valid_seen_bookends)
        if found:
            return True
        for fl_pair, eligible_remaining in valid_seen_bookends.items():
            first_cell, final_cell = fl_pair
            eligible_cells, remaining_cells = eligible_remaining
            for chain in self.chaining(first_cell, final_cell = final_cell, max_length = _max_chain, cells = remaining_cells):
                for candidate in first_cell.intersection(final_cell):
                    _eligible_cells = [x for x in eligible_cells if candidate in x and x not in chain]
                    if not _eligible_cells:
                        continue
                    other_candidate = (first_cell.candidates - {candidate}).pop()
                    on_value, off_value = other_candidate, candidate
                    cell_b = first_cell
                    i = 1
                    while i < len(chain):
                        cell_a, cell_b = cell_b, chain[i]
                        if on_value in cell_b:
                            off_value = on_value
                            on_value = (cell_b.candidates - {off_value}).pop()
                        elif off_value in cell_b and self.are_strongly_linked(cell_a, cell_b, off_value):
                            on_value = off_value
                            off_value = (cell_b.candidates - {on_value}).pop()
                        else:
                            on_value = None
                            break
                        i += 1
                    if on_value is None or on_value != candidate or cell_b != final_cell:
                        continue
                    for cell in _eligible_cells:
                        cell.remove(candidate)
                        self.set_cell(cell)
                    return None
        return None

    @_transformation
    def x_wing(self):
        for div, other_div_name in [(self.row, 'column'), (self.column, 'row')]:
            for candidate in c.VALID_CANDIDATES:
                links_found = []
                for i in range(c.MAGIC_NUM):
                    link = self.find_strong_link(div(i), candidate)
                    if link is None:
                        continue
                    #TODO: should skip if in same box? Is that possible?
                    cell_a, cell_b = link
                    link_pos = {cell_a.position(other_div_name), cell_b.position(other_div_name)}
                    link_info = (link_pos, (cell_a, cell_b))
                    for other_link in links_found:
                        other_link_pos, other_cells = other_link
                        if other_link_pos == link_pos:
                            cell_c, cell_d = other_cells
                            eligible_cells = []
                            for pos in link_pos:
                                for cell in self.division(other_div_name, pos):
                                    if cell.solved:
                                        continue
                                    if candidate not in cell:
                                        continue
                                    if cell in (cell_a, cell_b, cell_c, cell_d):
                                        continue
                                    eligible_cells.append(cell)
                            if not eligible_cells:
                                continue
                            if len({cell_a.box, cell_b.box, cell_c.box, cell_d}) != 4:  #TODO: thoroughly test, then take out if impossible
                                raise ValueError("BOXES CAN HAVE EFFECT ON X WING, CHECK X WING")
                            for cell in eligible_cells:
                                cell.remove(candidate)
                                self.set_cell(cell)
                            return None
                    links_found.append(link_info)

    @_transformation
    def unique_rectangles1(self):
        bi_values = []
        for x in range(c.MAGIC_NUM):
            bi_values.append([])
            for y in range(c.MAGIC_NUM):
                if y >= x:
                    break
                bi_values[x].append([])
        for cell in self.bi_value_cells:
            values = cell.candidates
            a, b = values
            if a > b:
                bi_values[a - 1][b - 1].append(cell)
            else:
                bi_values[b - 1][a - 1].append(cell)
        for first_candidate_list in bi_values:
            for second_candidate_list in first_candidate_list:
                for _cell_list in itertools.combinations(second_candidate_list, 3):
                    column_set = {cell.column for cell in _cell_list}
                    if len(column_set) != 2:
                        continue
                    row_set = {cell.row for cell in _cell_list}
                    if len(row_set) != 2:
                        continue
                    box_set = {cell.box for cell in _cell_list}
                    if len(box_set) != 2:
                        continue
                    cell = None
                    for row in row_set:
                        for column in column_set:
                            _cell = self[row][column]
                            if _cell in _cell_list:
                                continue
                            if cell is not None:
                                raise ValueError("Should be impossible, should not be two matching cells")
                            cell = _cell
                    if cell is None:
                        raise ValueError("Should be impossible, should be one matching cell")
                    if _cell_list[0].intersection(cell) == _cell_list[0].candidates:
                        cell.remove(_cell_list[0].candidates)
                        self.set_cell(cell)
                        return None
        return None

    @_transformation
    def hidden_unique_rectangles1(self): #TODO: This one needs some TLC
        for pair_cell in self.bi_value_cells: # ceil1_cell #TODO: refactor
            _poss_cells = self.box(pair_cell.box)
            _poss_cells.remove(pair_cell)
            _poss_cells = [x for x in _poss_cells if len(x.intersection(pair_cell)) == 2]
            for ceil2_cell in _poss_cells:
                if ceil2_cell.row == pair_cell.row:
                    ceil_dir = 'row'
                    wall_dir = 'column'
                else:
                    ceil_dir = 'column'
                    wall_dir = 'row'
                _poss_floor1_cells = self.division(wall_dir, pair_cell)
                _poss_floor1_cells.remove(pair_cell)
                _poss_floor1_cells = [x for x in _poss_floor1_cells if x.box != pair_cell.box]
                _poss_floor1_cells = [x for x in _poss_floor1_cells if len(x.intersection(pair_cell)) == 2] #TODO: check?
                for floor1_cell in _poss_floor1_cells:
                    #Time to find floor2_cell
                    # should be aligned in ceil_dir with floor1 and wall_dir with ceil2
                    floor2_cell = self.division(ceil_dir, floor1_cell)[ceil2_cell.position(wall_dir)]
                    if floor2_cell.box != floor1_cell.box:
                        raise ValueError("should be in same box-- logic error in hur1")
                    if len(floor2_cell.intersection(pair_cell)) != 2:
                        continue
                    for candidate in pair_cell.candidates:
                        # Floor2 strong link with floor1 and ceil2 for this candidate
                        if not self.are_strongly_linked(floor2_cell, floor1_cell, candidate):
                            continue
                        if not self.are_strongly_linked(floor2_cell, ceil2_cell, candidate):
                            continue
                        #Okay! Can remove other candidate from floor2_cell (catty-corner from pair_cell)
                        other_candidate = (pair_cell.candidates - {candidate}).pop()
                        floor2_cell.remove(other_candidate)
                        self.set_cell(floor2_cell)
                        return None # TODO: Check.. all of this.
        return None

    @_transformation
    def swordfish(self):
        for candidate in c.VALID_CANDIDATES:
            for div, other_div in (('row', 'column'), ('column', 'row')):
                trio_tracker = []
                for i in range(c.MAGIC_NUM):
                    cells = self.division(div, i)
                    cells = [x for x in cells if candidate in x]
                    if len(cells) <= 3:
                        trio_tracker.append(cells)
                if len(trio_tracker) < 3:
                    continue
                for div_trio in itertools.combinations(trio_tracker, 3):
                    other_div_pos = set()
                    sword_cells = set()
                    perfect = True
                    i = 0
                    for trio in div_trio:
                        for cell in trio:
                            i += 1
                            other_div_pos.add(cell.position(other_div))
                            sword_cells.add(cell)
                            if cell.solved:
                                perfect = False
                            #TODO: fix?
                    perfect = perfect and i == 9
                    if len(other_div_pos) != 3:
                        continue
                    eligible_cells = []
                    for i in other_div_pos:
                        for cell in self.division(other_div, i):
                            if cell in sword_cells:
                                continue
                            if candidate in cell:
                                eligible_cells.append(cell)
                    if not eligible_cells:
                        continue
                    for cell in eligible_cells:
                        cell.remove(candidate)
                        self.set_cell(cell)
                    if perfect:
                        print('Perfect swordfish?')
                    return None
        return None

    def x_cycle(self, min_length = 5, max_length = 40, _continuous = None):
        cells_by_candidate = [set() for _ in range(c.MAGIC_NUM)]
        for cell in self.cells:
            for candidate in cell:
                cells_by_candidate[candidate].add(cell)
        for candidate, cells in enumerate(cells_by_candidate):
            if not cells:
                continue
            strong_links = self.find_strong_links(candidate, sets = True)
            if not strong_links:
                continue
            linked_cells = set()
            linked_cells.update(*strong_links)
            _max_length = min(max_length, len(cells), len(linked_cells) + 1)
            if _max_length < min_length:
                continue
            # First, continuous nice loops. Only strong links and even.
            if _continuous is None or _continuous:
                for cycle_length in range(min_length, _max_length + 1):
                    if cycle_length % 2 == 1:
                        continue
                    for _cycle in itertools.combinations(strong_links, cycle_length // 2):
                        cycle_set = set()
                        cycle_set.update(*_cycle)
                        if len(cycle_set) != cycle_length:
                            continue
                        for cycle in _table_settings(*_cycle):
                            broken = False
                            for i in range(cycle_length): # First cell is OFF. [0] OFF [1] ON [2] OFF [3] ON
                                if i % 2:
                                    continue # {cycle[i], cycle[i-1]} in strong_links
                                if not cycle[i].inclusive_sees(cycle[i - 1]):
                                    broken = True
                                    break
                            if broken:
                                continue
                            groups = [[], []]
                            for i, ele in enumerate(cycle):
                                groups[i % 2].append(ele)
                            eligible_cells = cells - cycle_set
                            eligible_cells = [x for x in eligible_cells if x.seen_by(*groups[0]) and x.seen_by(*groups[1])]
                            if eligible_cells:
                                for cell in eligible_cells:
                                    cell.remove(candidate)
                                    self.set_cell(cell)
                                return None
            if not _continuous:
                for cycle_length in range(min_length, _max_length + 1):
                    if cycle_length % 2 == 0:
                        continue
                    for _cycle in itertools.combinations(strong_links, (cycle_length + 1) // 2):
                        cycle_set = set()
                        cycle_set.update(*_cycle)
                        if len(cycle_set) != cycle_length:
                            continue
                        for cycle in _table_settings(*_cycle):
                            if cycle[0] != cycle[1]: # Keep in mind, len(cycle) == cycle_length + 1 since these two ==
                                continue
                            broken = False
                            # Ex: ([0] OFF -> [1] ON) -> ([2] OFF -> [3] ON) -> ([4] OFF -> [5/-1/0] ON)
                            for i in range(cycle_length):
                                if i % 2:
                                    continue
                                if not cycle[i].inclusive_sees(cycle[i - 1]):
                                    broken = True
                                    break
                            if broken:
                                continue
                            # [0] OFF -> [-1] == [0] ON
                            first_cell = cycle[0]
                            first_cell.candidates = [1]
                            self.set_cell(first_cell)
                            return None
                for cycle_length in range(min_length, _max_length + 1):
                    if cycle_length % 2 == 0:
                        continue
                    for _cycle in itertools.combinations(strong_links, cycle_length // 2):
                        cycle_set = set()
                        cycle_set.update(*_cycle)
                        if len(cycle_set) != cycle_length - 1:
                            continue
                        for cycle in _table_settings(*_cycle):
                            broken = False
                            for i in range(cycle_length - 1):
                                if i % 2 or i == 0:
                                    continue
                                if not cycle[i].inclusive_sees(cycle[i - 1]):
                                    broken = True
                                    break
                            if broken:
                                continue
                            possible_first_cells = [x for x in cells if x not in cycle_set and x.sees(cycle[0]) and x.sees(cycle[-1])]
                            if possible_first_cells:
                                for first_cell in possible_first_cells:
                                    # First cell [*] is ON ANd sees both ends
                                    # So, in cycle of 5:
                                    # [*] ON -> ([0] OFF -> [1] ON) -> ([2] OFF -> [3] ON)
                                    # [3] sees [*] so implies [*] OFF.
                                    first_cell.remove(candidate)
                                    self.set_cell(first_cell)
                                return None
