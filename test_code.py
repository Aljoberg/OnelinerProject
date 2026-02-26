# class Test:
#     __match_args__ = ("a",)
#     def __init__(self):
#         self.a = 5

# test = Test()
# print(test.a)

# match test:
#     case Test(a):
#         print(100, a)

def outer():
    a = 5
    def inner():
        nonlocal a
        a += 1
        return a
    
    print(a)
    print(inner())
    print(a)

outer()