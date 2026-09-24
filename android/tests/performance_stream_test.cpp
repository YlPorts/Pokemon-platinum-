#include <cassert>
#include <cstring>
#include <vector>
#include <cstdio>
#include <simulator/g3_draw.h>
static GLuint s_G3DrawVertexArray=1,s_G3DrawVertexBuffer=2;
static std::vector<unsigned char> storage;
static size_t endWritten=0,stores=0,draws=0;
static const G3SIM_Vertex_t *expected;
static unsigned expectedCount;
void glBindVertexArray(GLuint n) { assert(n==1); }
void glBindBuffer(GLenum kind,GLuint n) { assert(kind==GL_ARRAY_BUFFER && n==2); }
void glBufferData(GLenum kind,GLsizeiptr size,const void *data,GLenum usage) {
 assert(kind==GL_ARRAY_BUFFER && usage==GL_STREAM_DRAW);
 storage.resize(size);endWritten=0;stores++;
 if(data) { memcpy(storage.data(),data,size);endWritten=size; }
}
void glBufferSubData(GLenum kind,GLintptr offset,GLsizeiptr size,const void *data) {
 assert(kind==GL_ARRAY_BUFFER && offset>=(GLintptr)endWritten);
 assert(offset+size<=(GLsizeiptr)storage.size());
 memcpy(storage.data()+offset,data,size);endWritten=offset+size;
}
void glDrawArrays(GLenum mode,GLint first,GLsizei count) {
 assert(mode==GL_TRIANGLES && count==(int)expectedCount);
 assert(memcmp(storage.data()+sizeof(*expected)*first,expected,sizeof(*expected)*count)==0);draws++;
}
#include "android_vertex_stream.inc"
int main() {
 std::vector<G3SIM_Vertex_t> vertices(AD_STREAM_CAPACITY+3);
 for(size_t i=0;i<vertices.size();i++) {
  G3SIM_Vertex_t &v=vertices[i];v.x=i;v.y=-int(i);v.z=0.25f;v.w=1;v.s=i%256;v.t=i%128;v.r=.1f;v.g=.3f;v.b=.7f;v.a=.5f;
 }
 const unsigned sizes[]={3,6,150,12000,30,999,12000};
 for(int i=0;i<1400;i++) { expected=vertices.data();expectedCount=sizes[i%7];AndroidDrawVertices(expected,expectedCount); }
 assert(draws==1400 && stores<100); // no per-draw reallocations or overwritten ranges
 expectedCount=AD_STREAM_CAPACITY+3;AndroidDrawVertices(vertices.data(),expectedCount);
 expectedCount=3;AndroidDrawVertices(vertices.data(),3);
 AndroidDrawVertices(vertices.data(),0);assert(draws==1402);
 puts("PASS: 1402 ordered draws, exact positions/UV/colors/alpha, wrap and oversized fallback");
}
