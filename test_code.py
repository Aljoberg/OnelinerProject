try:
    assert False
except AssertionError:
    print("AssertionError raised")
else:
    print("AssertionError not raised")