# A key that does not exist reports what is at the deepest part of the path that does
data modify storage ward:missing path.to.test set value {value:false}
assert data storage ward:missing path.to.nothing.here
