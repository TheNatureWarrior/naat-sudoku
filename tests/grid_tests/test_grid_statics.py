from src.sudoku import grid as gr
import pytest

TS_IO = ({'input': (('a', 'A'), ('b', 'B')),
             'output': {('a', 'A', 'b', 'B'), ('a', 'A', 'B', 'b'), ('A', 'a', 'b', 'B'), ('A', 'a', 'B', 'b'),
                 ('b', 'B', 'a', 'A'), ('b', 'B', 'A', 'a'), ('B', 'b', 'a', 'A'), ('B', 'b', 'A', 'a')}},
         {'input': (('a', 'A'), ('b', 'B'), ('c',)),
          'output': {('a', 'A', 'b', 'B', 'c'), ('a', 'A', 'B', 'b', 'c'), ('A', 'a', 'b', 'B', 'c'),
              ('A', 'a', 'B', 'b', 'c'), ('b', 'B', 'a', 'A', 'c'), ('b', 'B', 'A', 'a', 'c'),
              ('B', 'b', 'a', 'A', 'c'), ('B', 'b', 'A', 'a', 'c'), ('c', 'a', 'A', 'b', 'B'),
              ('c', 'a', 'A', 'B', 'b'), ('c', 'A', 'a', 'b', 'B'), ('c', 'A', 'a', 'B', 'b'),
              ('c', 'b', 'B', 'a', 'A'), ('c', 'b', 'B', 'A', 'a'), ('c', 'B', 'b', 'a', 'A'),
              ('c', 'B', 'b', 'A', 'a'), ('a', 'A', 'c', 'b', 'B'), ('a', 'A', 'c', 'B', 'b'),
              ('A', 'a', 'c', 'b', 'B'), ('A', 'a', 'c', 'B', 'b'), ('b', 'B', 'c', 'a', 'A'),
              ('b', 'B', 'c', 'A', 'a'), ('B', 'b', 'c', 'a', 'A'), ('B', 'b', 'c', 'A', 'a')}})

@pytest.mark.parametrize('io_dict', TS_IO)
def test_table_settings(io_dict):
    expected = io_dict['output']
    results = []
    for result in gr._table_settings(*io_dict['input']):
        assert result in expected
        results.append(result)
    assert len(results) == len(expected)
