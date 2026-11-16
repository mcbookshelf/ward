# A failed chat assertion shows the last messages, the useful ones in a long test
say chat sample 1
say chat sample 2
say chat sample 3
say chat sample 4
say chat sample 5
say chat sample 6
say chat sample 7
assert chat "never said"
