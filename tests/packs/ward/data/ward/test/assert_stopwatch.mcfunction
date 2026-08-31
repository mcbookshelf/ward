stopwatch create ward:elapsed
assert stopwatch ward:elapsed 0..
assert not stopwatch ward:elapsed 100000..
stopwatch remove ward:elapsed
