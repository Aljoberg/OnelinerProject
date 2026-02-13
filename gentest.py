# import inspect


# def get_current_generator():
# """Get the generator from the current frame."""
# frame = inspect.currentframe().f_back

# yield 1

# # Search through locals for a generator whose frame matches
# for var in frame.f_locals.values():
# print(var)
# if inspect.isgenerator(var) and var.gi_frame is frame:
# return var
# return None


# def get():
# print((yield from get_current_generator()))


# list(get())

import ctypes
import sys


class PyObject(ctypes.Structure):
    pass


PyObject._fields_ = [
    ("ob_refcnt", ctypes.c_ssize_t),
    ("ob_type", ctypes.POINTER(PyObject)),
]


class _PyErr_StackItem(ctypes.Structure):
    _fields_ = [
        ("exc_value", ctypes.py_object),
        ("previous_item", ctypes.c_void_p),  # pointer to _PyErr_StackItem
    ]


# class _PyInterpreterFrame(ctypes.Structure):
# _fields_ = [
# ("f_executable", ctypes.py_object),  # PyCodeObject or None
# ("f_funcobj", ctypes.py_object),
# ("f_builtins", ctypes.py_object),
# ("f_globals", ctypes.py_object),
# ("f_locals", ctypes.py_object),
# ("frame_obj", ctypes.c_void_p),  # PyFrameObject*
# ("previous", ctypes.c_void_p),  # _PyInterpreterFrame*
# ("prev_instr", ctypes.c_void_p),  # _Py_CODEUNIT*
# ("stacktop", ctypes.c_int),
# ("return_offset", ctypes.c_uint16),
# ("owner", ctypes.c_char),
# ("localsplus", ctypes.py_object * 1),  # flexible array
# ]


class _PyStackRef(ctypes.Structure):
    _fields_ = [
        ("bits", ctypes.c_size_t),
    ]


class _Py_CODEUNIT(ctypes.Structure):
    _fields_ = [
        ("cache", ctypes.c_uint8),
        ("opcode", ctypes.c_uint8),
    ]



class _PyInterpreterFrame(ctypes.Structure):
    pass


class PyFrameObject(ctypes.Structure):
    _fields_ = [
        # PyObject_HEAD
        ("ob_refcnt", ctypes.c_ssize_t),
        ("ob_type", ctypes.c_void_p),
        # _PyGenObject_HEAD(gi)
        ("f_back", ctypes.c_void_p),
        ("f_frame", ctypes.c_void_p),
        ("f_trace", ctypes.py_object),
        ("f_lineno", ctypes.c_int),
        ("f_trace_lines", ctypes.c_char),
        ("f_trace_opcodes", ctypes.c_char),
        ("f_fast_as_locals", ctypes.c_char),
        ("_f_frame_data", (ctypes.py_object * 1))
    ]

# Define fields based on whether Py_GIL_DISABLED and Py_DEBUG are set
# Standard build (no GIL_DISABLED, no DEBUG)
_PyInterpreterFrame._fields_ = [
    ("f_code", ctypes.c_void_p),
    ("previous", ctypes.c_void_p),
    ("f_funcobj", ctypes.py_object),
    ("f_globals", ctypes.py_object),
    ("f_builtins", ctypes.py_object),
    ("f_locals", ctypes.py_object),
    ("frame_obj", ctypes.POINTER(PyFrameObject)),
    # ("instr_ptr", ctypes.POINTER(_Py_CODEUNIT)),
    ("prev_instr", ctypes.POINTER(_Py_CODEUNIT)),
    # ('stackpointer', ctypes.POINTER(_PyStackRef)), TODO this is for 3.14 i guess, 3.12 uses localsplus
    ("stacktop", ctypes.c_int),  # 3.12 only
    ("return_offset", ctypes.c_uint16),
    ("owner", ctypes.c_char),
    # ("visited", ctypes.c_uint8),
    (
        "localsplus",
        (ctypes.py_object) * 1,
    ),  # Flexible array member TODO uses pystackref isntead of py object
]


class PyGenObject(ctypes.Structure):
    _fields_ = [
        # PyObject_HEAD
        ("ob_refcnt", ctypes.c_ssize_t),
        ("ob_type", ctypes.POINTER(PyObject)),
        # _PyGenObject_HEAD(gi)
        ("gi_weakreflist", ctypes.py_object),
        ("gi_name", ctypes.py_object),
        ("gi_qualname", ctypes.py_object),
        ("gi_exc_state", _PyErr_StackItem),
        ("gi_origin_or_finalizer", ctypes.py_object),
        ("gi_hooks_inited", ctypes.c_char),
        ("gi_closed", ctypes.c_char),
        ("gi_running_async", ctypes.c_char),
        ("gi_frame_state", ctypes.c_int8),
        ("gi_iframe", (_PyInterpreterFrame)),
    ]


print(PyGenObject.gi_iframe.offset)

import inspect, sys


# Usage
def my_gen():
    yield 1
    value = ctypes.py_object(123)

    print(inspect.stack())

    curr_frame = inspect.currentframe()  # inspect.stack()[0].frame

    print(curr_frame.f_lasti)

    print(curr_frame.f_locals)

    print(gen_ptr)
    input()


    backframe = curr_frame.f_back

    frame = ctypes.cast(
        id(curr_frame), ctypes.POINTER(PyFrameObject)
    )  # or inspect.currentframe

    print(frame.contents.f_lineno)
    print(frame.contents.f_trace_lines)
    frame_f_frame = ctypes.cast(frame.contents.f_frame, ctypes.POINTER(_PyInterpreterFrame))
    print(frame_f_frame.contents.f_builtins)
    print(frame_f_frame.contents.localsplus[0])
    print(frame_f_frame.contents.stacktop, "stack top")

    gen_object = ctypes.cast(
        ctypes.addressof(frame_f_frame.contents) - PyGenObject.gi_iframe.offset,
        ctypes.POINTER(PyGenObject),
    )

    print(gen_object.contents.gi_qualname)

    print(gen_object.contents.gi_iframe.f_builtins)
    print(gen_object.contents.gi_iframe.stacktop, "first stacktop")

    # gen_frame = ctypes.cast(gen_object.contents.gi_iframe, ctypes.POINTER(_PyInterpreterFrame))
    # gen_frame = frame.contents
    # print(f"{gen_frame = }")

    # gen_object.contents.gi_frame_state = -2 # PyFrameState.FRAME_SUSPENDED
    # frame.contents.stackpointer[0] = frame.contents.stackpointer[-1]
    # print(gen_object.contents.gi_frame_state)
    # print(frame.contents.stackpointer.contents)
    # print(frame.contents.stackpointer._type_)
    # print(ctypes.addressof(ctypes.cast(frame.contents.stackpointer, ctypes.POINTER(_PyStackRef))) - ctypes.sizeof(_PyStackRef))
    # print("a")
    # print(gen_object.contents)
    # print(gen_object.contents.gi_iframe.stackpointer)
    # print(ctypes.cast(
    # ctypes.addressof(gen_object.contents.gi_iframe.stackpointer.contents) - ctypes.sizeof(_PyStackRef),
    # ctypes.POINTER(_PyStackRef)
    # )
    # )

    # print(frame.contents.stackpointer)
    # gen_object.contents.gi_iframe.stackpointer = ctypes.cast(
    # ctypes.addressof(frame.contents.stackpointer.contents) - ctypes.sizeof(_PyStackRef),
    # ctypes.POINTER(_PyStackRef)
    # ) XXX 3.14 again

    gen_object.contents.gi_frame_state = -1 # PyFrameState.FRAME_SUSPENDED
    sp_addr = (ctypes.addressof(gen_object.contents.gi_iframe.localsplus) + gen_object.contents.gi_iframe.stacktop * ctypes.sizeof(ctypes.POINTER(ctypes.py_object)))

# Decrement by 1 element
    sp_addr -= ctypes.sizeof(ctypes.POINTER(ctypes.py_object))

# Calculate new stacktop
    new_stacktop = ((sp_addr - ctypes.addressof(gen_object.contents.gi_iframe.localsplus)) // ctypes.sizeof(ctypes.POINTER(ctypes.py_object)))
    print(new_stacktop, "new stacktop")

    gen_object.contents.gi_iframe.stacktop = new_stacktop


    """
    sp = ctypes.cast(
        ctypes.addressof(gen_object.contents.gi_iframe.localsplus)
        + (gen_object.contents.gi_iframe.stacktop * ctypes.sizeof(ctypes.c_int)),
        ctypes.POINTER(ctypes.POINTER(ctypes.py_object)),
    )
    # stackpointer =

    print(gen_object.contents.gi_iframe.stacktop)

    new_stacktop = ctypes.cast(sp, ctypes.c_void_p).value - (
        ctypes.addressof(gen_object.contents.gi_iframe.localsplus)
        * ctypes.sizeof(ctypes.c_int)
    )

    gen_object.contents.gi_iframe.stacktop = new_stacktop
    # ctypes.c_int,
    """

    print("hihihi")
    print(gen_object.contents.gi_iframe.stacktop)
    print(gen_object.contents.gi_iframe.f_globals)
    print(gen_object.contents.gi_iframe.f_locals)
    print(gen_object.contents.gi_iframe.localsplus)

    # TODO some exceptions stuff
    print("here")
    # gen_object.contents.gi_iframe = gen_object.contents.gi_iframe.previous
    print(gen_object.contents.gi_iframe.previous)

    # prev_frame = ctypes.cast(frame.contents.f_frame.contents.previous, ctypes.POINTER(_PyInterpreterFrame))
    gen_frame = frame

# Get the previous frame pointer VALUE (not contents)
    # previous_frame_addr = ctypes.cast(gen_frame.contents.f_frame.contents.previous, ctypes.c_void_p).value
    previous_frame_addr = ctypes.cast(gen_object.contents.gi_iframe.previous, ctypes.c_void_p).value
    print(previous_frame_addr, 'addr')

# Update current frame to point to previous frame
# (This would update cframe.current_frame in the C code)
    # prev_frame = ctypes.cast(previous_frame_addr, ctypes.POINTER(_PyInterpreterFrame))
    prev_frame = ctypes.cast(ctypes.cast(id(backframe), ctypes.POINTER(PyFrameObject)).contents.f_frame, ctypes.POINTER(_PyInterpreterFrame))

    print("hulleh", prev_frame)
    print(ctypes.cast(id(backframe), ctypes.POINTER(PyFrameObject)).contents.f_trace_lines)
    print(ctypes.cast(ctypes.cast(id(backframe), ctypes.POINTER(PyFrameObject)).contents.f_frame, ctypes.POINTER(_PyInterpreterFrame)).contents.f_globals)
    print(id(backframe), backframe, ctypes.addressof(prev_frame))
    print(prev_frame.contents.stacktop)
    print(prev_frame.contents.f_builtins)

# Set gen_frame->previous = NULL
    # gen_frame.contents.f_frame.contents.previous = ctypes.c_void_p(0)  # or ctypes.c_void_p(0)
    gen_frame.previous = ctypes.c_void_p(0)  # or ctypes.c_void_p(0)
    # gen_object.contents.gi_iframe.previous = ctypes.c_void_p(0)  # or ctypes.c_void_p(0)
    # print(prev_frame.contents.f_locals)
    print(prev_frame.contents.stacktop)
    print(prev_frame.contents.f_locals)
    print(gen_object.contents.gi_iframe.f_locals)
##    print(prev_frame.contents.frame_obj.contents.f_trace)
    input()
    print("here 2")

    # frame.contents.previous = None  # ctypes.c_void_p
    # gen_object.contents.gi_iframe.previous = None  # ctypes.c_void_p TODO add back
    print("here 3")
    # print(gen_object.contents.gi_iframe.localsplus.contents)
    print(gen_object.contents.gi_iframe.stacktop)
    print("sans")
    # print(gen_object.contents.gi_iframe.localsplus)
    # print(
    #    frame.contents.localsplus.contents
    # )  # removing this makes it not work??????????
    # print(gen_object.contents.gi_iframe.stacktop, dir(gen_object.contents.gi_iframe.localsplus))
    print("after print")
    print(
        gen_object.contents.gi_iframe.localsplus, gen_object.contents.gi_iframe.stacktop
    )
    print(gen_object.contents.gi_iframe.stacktop)
    print(new_stacktop)
    # print(gen_object.contents.gi_iframe.localsplus[gen_object.contents.gi_iframe.stacktop] is not None)
    # gen_object.contents.gi_iframe.localsplus[gen_object.contents.gi_iframe.stacktop] = (
    # print("shit works", prev_frame.contents.f_builtins)
    print("shit 2orks", prev_frame.contents.stacktop, prev_frame.contents.prev_instr.contents.cache)
    print(prev_frame.contents.stacktop)
    topstack = prev_frame.contents.stacktop
    prev_frame.contents.localsplus[topstack] = value
    # frame.contents.localsplus[frame.contents.stacktop] = value
    print("here 5")
    prev_frame.contents.stacktop = topstack + 1

    tstate = ctypes.pythonapi.PyGILState_GetThisThreadState()

    # tstate.contents.frame.contents.current_frame = prev_frame


    # frame.contents.stackpointer[0] = value
    print("here 4")
    print(prev_frame.contents.stacktop)
    print(gen_object.contents.gi_frame_state)
    # frame.contents.stackpointer = ctypes.cast(
    #     ctypes.addressof(frame.contents.stackpointer.contents) + ctypes.sizeof(value),
    #     type(frame.contents.stackpointer),
    # )

    time.sleep(3)

    # yield 3

    print("maybe")

    return 4


import dis, time
from inspect import CO_OPTIMIZED

#my_gen.__code__ = my_gen.__code__.replace(
#    co_flags=my_gen.__code__.co_flags & ~CO_OPTIMIZED
#)


dis.dis(my_gen)
gen = my_gen()
gen_ptr = ctypes.cast(id(gen), ctypes.POINTER(PyGenObject))
print(f"Name: {gen_ptr.contents.gi_name}")
print(f"Qualified name: {gen_ptr.contents.gi_qualname}")
print(f"Closed: {gen_ptr.contents.gi_closed}")
print(f"Frame state: {gen_ptr.contents.gi_frame_state}")
print(gen_ptr.contents.gi_iframe.f_builtins)
print(next(gen), "nex")
print(next(gen), "nex 2")
# print(next(gen))
