# class Test:
#     __match_args__ = ("a",)
#     def __init__(self):
#         self.a = 5

# test = Test()
# print(test.a)

# match test:
#     case Test(a):
#         print(100, a)

# def outer():
#     a = 5
#     def inner():
#         nonlocal a
#         a += 1
#         return a
    
#     print(a)
#     print(inner())
#     print(a)

# outer()

# def process_coordinates(coord):
#     match coord:
#         case (x, y):
#             return f"Coordinates are X: {x}, Y: {y}"
#         case [x, y, z]:
#             return f"Coordinates are X: {x}, Y: {y}, Z: {z}"
#         case _:
#             return "Invalid coordinate format"

# print(process_coordinates((10, 20)))        # Output: Coordinates are X: 10, Y: 20
# print(process_coordinates([10, 20, 30]))     # Output: Coordinates are X: 10, Y: 20, Z: 30

(a, b), (c, d) = (1, 2), [3, 4]
e, f = g = 1, 2
h = i = j = 50
lis = [67, 68]
m, n = lis
o = [1]
o[0] = 2
import threading
p = threading.Thread(target=lambda: print("hi"))
p.daemon = True
p.start()