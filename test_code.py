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

# hi = 1

# class Test:
#     global hi
#     # you can do that?
#     a: int = 5

#     hi = 2

#     for i in range(3):
#         print("Hi")
#         d: str = "world"

#     print(i)
    

#     def test(self):
#         b: str = "hello"
#         c: float = 3.14
#         return self.a, b, c
    
# t = Test()

# print(__annotations__)
# print(t.__annotations__)
# t.test()
# print(t.test.__annotations__)
# print(t.__annotations__)
# print(__annotations__)
# print(hi)
# print(t.i, "t.i")
# # print(Test.hi)


# match {"a": 1, "b": 2, "c": 3, "d": 4}:
#     case {"a": a, "b": 2, **d}:
#         print(a, d)

# a = {}
# for a["b"] in [1, 2, 3]:
#     print(a["b"])

# print(t.a, "ta ")
# list((print("hi") for t.a in [1, 2, 3]))

# print(t.a)
# print(a)

# import time


# def napolni(n):
#     return [x for x in range(1, n + 1)]


# sez = list(napolni(100_000_000))
# ter = tuple(sez)


# def lin_isk(sez, iskano: int):
#     for i in range(len(sez)):
#         if sez[i] == iskano:
#             return i
#     else:
#         return -1


# def bin_isk(sez, iskano: int):
#     zg = len(sez) - 1
#     sp = 0
#     while sp <= zg:
#         sr = (zg + sp) // 2
#         if sez[sr] == iskano:
#             return sr
#         elif sez[sr] < iskano:
#             sp = sr + 1
#         else:
#             zg = sr - 1
#     return -1


# start = time.perf_counter()

# print("Linearno iskanje:")
# print(lin_isk(ter, 67_520_384))

# end = time.perf_counter()
# print(end - start)


# print()


# start = time.perf_counter()

# print("Binarno iskanje:")
# print(bin_isk(ter, 67_520_384))

# end = time.perf_counter()
# print(end - start)

# import numpy as np
# from collections import Counter

# class KNN:
#     def __init__(self, k=3):
#         self.k = k

#     def fit(self, X, y):
#         self.X_train = X
#         self.y_train = y

#     def predict(self, X):
#         y_pred = [self._predict(x) for x in X]
#         return np.array(y_pred)

#     def _predict(self, x):
#         # Compute distances between x and all examples in the training set
#         distances = [np.sqrt(np.sum((x_train - x) ** 2)) for x_train in self.X_train]
#         # Sort by distance and return indices of the first k neighbors
#         k_indices = np.argsort(distances)[:self.k]
#         # Extract the labels of the k nearest neighbor training samples
#         k_nearest_labels = [self.y_train[i] for i in k_indices]  
#         # Return the most common class label
#         most_common = Counter(k_nearest_labels).most_common(1)
#         return most_common[0][0]

# # Example of usage:
# if __name__ == "__main__":
#     from sklearn.datasets import load_iris
#     from sklearn.model_selection import train_test_split

#     iris = load_iris()
#     X, y = iris.data, iris.target
#     X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=123)

#     clf = KNN(k=3)
#     clf.fit(X_train, y_train)
#     predictions = clf.predict(X_test)

#     # Calculate accuracy
#     accuracy = np.mean(predictions == y_test)
#     print(f"KNN classification accuracy: {accuracy}")

with open("hello_there.txt", "w") as f:
    f.write("hi")