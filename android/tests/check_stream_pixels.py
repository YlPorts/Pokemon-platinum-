#!/usr/bin/env python3
"""Compare original/append VBO uploads with the shipped g3 shader on GLES3."""
from pathlib import Path
exec((Path(__file__).parent/'check_gles.py').read_text())
F=C.c_float
proc('glUseProgram',None,U)(program)
loc=lambda name:proc('glGetUniformLocation',I,U,C.c_char_p)(program,name.encode())
ui=lambda name,value:proc('glUniform1i',None,I,I)(loc(name),value)
ui('myTexture',0);ui('polygonMode',0)
proc('glUniform4f',None,I,F,F,F,F)(loc('fogColor'),.2,.4,.6,.7)
for name,values in [('fogDepthBoundary',[-1+i/16 for i in range(32)]),('fogDensity',[i/64 for i in range(32)])]:
    proc('glUniform1fv',None,I,I,P)(loc(name),32,(F*32)(*values))
vao,buffer,texture=U(),U(),U()
proc('glGenVertexArrays',None,I,C.POINTER(U))(1,C.byref(vao))
proc('glBindVertexArray',None,U)(vao)
proc('glGenBuffers',None,I,C.POINTER(U))(1,C.byref(buffer))
proc('glBindBuffer',None,U,U)(0x8892,buffer)
for index,count,offset in [(0,3,0),(1,2,16),(2,4,24)]:
    proc('glEnableVertexAttribArray',None,U)(index)
    proc('glVertexAttribPointer',None,U,I,U,U,I,P)(index,count,0x1406,0,40,P(offset))
proc('glGenTextures',None,I,C.POINTER(U))(1,C.byref(texture))
proc('glActiveTexture',None,U)(0x84c0)
proc('glBindTexture',None,U,U)(0x0de1,texture)
for parameter,value in [(0x2800,0x2600),(0x2801,0x2600),(0x2802,0x812f),(0x2803,0x812f)]:
    proc('glTexParameteri',None,U,U,I)(0x0de1,parameter,value)
pixels=(C.c_ubyte*16)(255,200,100,255,40,255,160,255,100,40,255,0,255,255,255,128)
proc('glTexImage2D',None,U,I,I,I,I,I,U,U,P)(0x0de1,0,0x8058,2,2,0,0x1908,0x1401,pixels)
proc('glViewport',None,I,I,I,I)(0,0,8,8)
proc('glEnable',None,U)(0x0be2)
proc('glBlendFunc',None,U,U)(0x0302,0x0303)
vertices=[
 [-1,-1,.2,1,0,0,1,.2,.1,1],[-1,1,.2,1,0,1,.2,1,.1,1],[1,-1,.2,1,1,0,.1,.2,1,1],
 [-1,1,0,1,0,1,1,1,.1,.6],[1,1,0,1,1,1,.1,1,1,.6],[1,-1,0,1,1,0,1,.1,1,.6]]
def render(stream,textured):
    proc('glClearColor',None,F,F,F,F)(.01,.02,.03,1)
    proc('glClear',None,U)(0x4000)
    proc('glBufferData',None,U,C.c_ssize_t,P,U)(0x8892,240,None,0x88e0)
    ui('useTexture',textured)
    for batch in range(2):
        ui('useFog',batch)
        data=(F*30)(*(x for v in vertices[batch*3:batch*3+3] for x in v))
        offset=batch*120 if stream else 0
        proc('glBufferSubData',None,U,C.c_ssize_t,C.c_ssize_t,P)(0x8892,offset,120,data)
        proc('glDrawArrays',None,U,I,I)(0x0004,batch*3 if stream else 0,3)
    out=(C.c_ubyte*256)()
    proc('glReadPixels',None,I,I,I,I,U,U,P)(0,0,8,8,0x1908,0x1401,out)
    assert proc('glGetError',U)()==0
    return bytes(out)
for textured in (0,1):
    original=render(False,textured);optimized=render(True,textured)
    assert original==optimized, 'Changed pixels with streamed VBO'
    assert len(set(original[i:i+4] for i in range(0,256,4)))>3
print('PASS: GLES3 pixels identical with vertex colors, textures, alpha, discard and fog')
