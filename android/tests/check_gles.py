#!/usr/bin/env python3
"""Compile and link the shipped shaders in a real Mesa OpenGL ES 3 context."""
import ctypes as C
import os
from pathlib import Path
import sys

os.environ.setdefault('EGL_PLATFORM', 'surfaceless')
egl = C.CDLL('libEGL.so.1')
egl.eglGetProcAddress.argtypes = [C.c_char_p]
egl.eglGetProcAddress.restype = C.c_void_p

def proc(name, result, *args):
    ptr = egl.eglGetProcAddress(name.encode())
    if not ptr:
        raise RuntimeError(f'Missing EGL/GLES function: {name}')
    return C.CFUNCTYPE(result, *args)(ptr)

I, U, P = C.c_int, C.c_uint, C.c_void_p
arr = lambda *v: (I * len(v))(*v)
get_display = proc('eglGetPlatformDisplayEXT', P, U, P, C.POINTER(I))
display = get_display(0x31DD, None, None)
assert proc('eglInitialize', U, P, C.POINTER(I), C.POINTER(I))(display, None, None)
assert proc('eglBindAPI', U, U)(0x30A0)
config, count = P(), I()
attrs = arr(0x3040, 0x0040, 0x3033, 1, 0x3024, 8, 0x3023, 8, 0x3022, 8, 0x3038)
assert proc('eglChooseConfig', U, P, C.POINTER(I), C.POINTER(P), I, C.POINTER(I))(
    display, attrs, C.byref(config), 1, C.byref(count)) and count.value
context = proc('eglCreateContext', P, P, P, P, C.POINTER(I))(display, config, None, arr(0x3098, 3, 0x3038))
surface = proc('eglCreatePbufferSurface', P, P, P, C.POINTER(I))(display, config, arr(0x3057, 8, 0x3056, 8, 0x3038))
assert context and surface
assert proc('eglMakeCurrent', U, P, P, P, P)(display, surface, surface, context)

root = Path(sys.argv[1]) / 'subprojects/libntr/libraries/sim/src/shaders'
def shader(name, kind):
    raw = (root / name).read_text()
    raw = raw[raw.index('(') + 1:raw.rindex(')')]
    raw = raw[raw.index('\n', raw.index('#version')) + 1:]
    source = C.c_char_p(('#version 300 es\nprecision highp float;\nprecision highp int;\n' + raw).encode())
    ident = proc('glCreateShader', U, U)(kind)
    proc('glShaderSource', None, U, I, C.POINTER(C.c_char_p), P)(ident, 1, C.byref(source), None)
    proc('glCompileShader', None, U)(ident)
    ok = I()
    proc('glGetShaderiv', None, U, U, C.POINTER(I))(ident, 0x8B81, C.byref(ok))
    log = C.create_string_buffer(16384)
    proc('glGetShaderInfoLog', None, U, I, P, P)(ident, len(log), None, log)
    assert ok.value, f'{name}: {log.value.decode()}'
    return ident

for engine in ('g2', 'g3'):
    vertex = shader(f'{engine}_vertex.glsl', 0x8B31)
    fragment = shader(f'{engine}_fragment.glsl', 0x8B30)
    program = proc('glCreateProgram', U)()
    for ident in (vertex, fragment):
        proc('glAttachShader', None, U, U)(program, ident)
    proc('glLinkProgram', None, U)(program)
    ok = I()
    proc('glGetProgramiv', None, U, U, C.POINTER(I))(program, 0x8B82, C.byref(ok))
    log = C.create_string_buffer(16384)
    proc('glGetProgramInfoLog', None, U, I, P, P)(program, len(log), None, log)
    assert ok.value, f'{engine}: {log.value.decode()}'
    print(f'PASS: {engine} shaders compile and link on OpenGL ES 3')
