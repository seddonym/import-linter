SOME_VAR = 1


def some_func():
    from cyclicpackage.foo.blue.delta import four
    from ..charlie import SOMETHING

    four.another_func(a=SOMETHING)
