(
    (
        (
            fib := lambda n: (a := [None])
            and (b := False)
            or [
                (
                    b
                    or (
                        ((b or (a.__setitem__(0, 1) or (b := True))))
                        if ((n < 3))
                        else (None)
                    )
                ),
                (
                    b
                    or (
                        a.__setitem__(0, ((b or fib((n - 1))) + (b or fib((n - 2)))))
                        or (b := True)
                    )
                ),
                a[0],
            ][-1]
        )
    ),
    (print(fib(10))),
)[0]
