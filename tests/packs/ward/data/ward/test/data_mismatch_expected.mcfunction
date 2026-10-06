# A filter that does not match reports the tag it was applied to, not its parent or the whole storage
data modify storage ward:mismatch filler set value [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
data modify storage ward:mismatch path.to.other set value {noise:true}
data modify storage ward:mismatch path.to.test set value {value:false}
assert data storage ward:mismatch path.to.test{value:true}
