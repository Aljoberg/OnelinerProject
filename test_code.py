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

# (a, b), (c, d) = (1, 2), [3, 4]
# e, f = g = 1, 2
# h = i = j = 50
# lis = [67, 68]
# m, n = lis
# o = [1]
# o[0] = 2
# import threading
# p = threading.Thread(target=lambda: print("hi"))
# p.daemon = True
# p.start()

# for i in range(2, 100):
#     delitli = 0
#     for j in range(2, i // 2 + 1):
#         if i % j == 0:
#             delitli += 1
#     if delitli == 0:
#         print(i)

hi = 1

class Test:
    global hi
    # you can do that?
    a: int = 5

    hi = 2

    for i in range(3):
        print("Hi")
        d: str = "world"

    print(i)
    

    def test(self):
        b: str = "hello"
        c: float = 3.14
        return self.a, b, c
    
t = Test()

print(__annotations__)
print(t.__annotations__)
t.test()
print(t.test.__annotations__)
print(t.__annotations__)
print(__annotations__)
print(hi)
print(t.i, "t.i")
# print(Test.hi)


match {"a": 1, "b": 2, "c": 3, "d": 4}:
    case {"a": a, "b": 2, **d}:
        print(a, d)

a = {}
for a["b"] in [1, 2, 3]:
    print(a["b"])

print(t.a, "ta ")
list((print("hi") for t.a in [1, 2, 3]))

print(t.a)
print(a)