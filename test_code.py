try:
    1 / 0
except ZeroDivisionError as e:
    print("Caught division by zero", e)