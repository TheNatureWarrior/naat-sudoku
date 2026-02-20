from typing import Iterable
from src.sudoku import constants as c

class Cell:
    def __init__(self, *candidates : int, row : int = None, column : int = None):
        self._length = None
        self.solved = False
        self.previously_solved = False
            # TODO: Change how this works? IDK If I like current implementation.
        self.value = None

        self.row = row
        if self.row not in c.VALID_ROWS:
            raise ValueError("Invalid row")
        self.column = column
        if self.column not in c.VALID_COLUMNS:
            raise ValueError("Invalid column")
        self._hash = hash((self.row, self.column))
        self.chute = self.column // 3
        self.strip = self.row // 3
        self.box = (self.strip * 3) + self.chute
        self.box_cell = (self.column % 3) + ((self.row % 3) * 3)

        if not candidates: # Default is everything
            temp_list = list(c.VALID_CANDIDATES)
        else:
            temp_list = []
            for candidate in candidates:
                if not isinstance(candidate, int):
                    raise TypeError("Candidates must be integers")
                if candidate not in c.VALID_CANDIDATES:
                    raise ValueError(f"Candidate {candidate} not in {c.VALID_CANDIDATES}")
                if candidate in temp_list:
                    raise ValueError(f"Candidate {candidate} already exists")
                temp_list.append(candidate)
        temp_list.sort()
        self._candidates = tuple(temp_list)
        if len(self) == 1:
            self.solved = True
            self.value = self._candidates[0]
        self._internal_changed = False

    def __hash__(self) -> int:
        return self._hash

    def __repr__(self) -> str:
        candidates = list(self.candidates)
        candidates.sort()
        candidates = [str(x) for x in candidates]
        return f"R{self.row}C{self.column}Cell({', '.join(candidates)})"


    def __iter__(self):
        return iter(self._candidates)

    def __contains__(self, item) -> bool:
        return item in self._candidates

    def __len__(self):
        if self._length is None:
            self._length = len(self._candidates)
        return self._length

    def __eq__(self, other) -> bool:
        if not isinstance(other, Cell):
            return NotImplemented
        return self.row == other.row and self.column == other.column

    @property
    def candidates(self) -> set[int]:
        return {*self._candidates}

    @candidates.setter
    def candidates(self, candidates : Iterable[int]) -> None:
        if not self.solved and set(candidates) != set(self.candidates):
            self._internal_changed = True
        self.previously_solved = self.solved
        if not self.previously_solved:
            self._candidates = tuple(candidates)
            self._length = None
            if len(self) == 1:
                self.solved = True
                self.value = self._candidates[0]
            else:
                self.solved = False
                self.value = None

    def remove(self, value: int | Iterable[int]) -> None: #TODO fix
        x = self.candidates
        if isinstance(value, int):
            value = [value]
        for val in value:
            x.discard(val)
        self.candidates = x

    def equals(self, value: int) -> None: #TODO: fix
        self.candidates = [value]

    def sees(self, cell: "Cell") -> bool:
        #TODO: timeit
        return self.inclusive_sees(cell) and self != cell

    def inclusive_sees(self, cell: "Cell") -> bool:
        return self.row == cell.row or self.column == cell.column or self.box == cell.box

    def seen_by(self, *cells: "Cell") -> bool:
        for cell in cells:
            if self.inclusive_sees(cell):
                return True
        return False

    def position(self, division : str) -> int:
        if division == 'row':
            return self.row
        elif division == 'column':
            return self.column
        elif division == 'box':
            return self.box
        elif division == 'chute':
            return self.chute
        elif division == 'strip':
            return self.strip
        else:
            raise ValueError("Invalid division")

    def aligned(self, cell: "Cell", *divisions: str) -> bool:
        for div in divisions:
            if self.position(div) != cell.position(div):
                return False
        return True

    def intersection(self, x : Iterable[int], /):
        if not isinstance(x, Cell) and not isinstance(x, set):
            raise TypeError("Input must be cell or set")
        if isinstance(x, Cell):
            x = x.candidates
        return self.candidates.intersection(x)

    def union(self, x, /):
        if not isinstance(x, Cell) and not isinstance(x, set):
            raise TypeError("Input must be cell or set")
        if isinstance(x, Cell):
            x = x.candidates
        return self.candidates.union(x)

    @property
    def changed(self) -> bool:
        return self._internal_changed

    def reset_changed(self): #TODO: get rid of this.
        self._internal_changed = False
