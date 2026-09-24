#include <cassert>
#include <cstdio>
#include <cstring>
#include <map>
#include <vector>
using GLint=int;using GLfloat=float;using GLsizei=int;
static unsigned calls;
static std::map<int,std::vector<unsigned char>> actual;
static void record(int loc,const void *data,unsigned size) { ++calls;if(loc>=0) actual[loc]=std::vector<unsigned char>((const unsigned char*)data,(const unsigned char*)data+size); }
static void glUniform1i(int loc,int value) {record(loc,&value,sizeof(value));}
static void glUniform4f(int loc,float x,float y,float z,float w) { float data[]={x,y,z,w};record(loc,data,sizeof(data));}
static void glUniform1fv(int loc,int count,const float *data) {record(loc,data,count*sizeof(float));}
#include "android_uniforms.inc"
int main() {
    float fog[32];for(int i=0;i<32;i++) fog[i]=i/31.f;
    for(int draw=0;draw<5000;draw++) {
        AndroidUniform1i(0,1);AndroidUniform4f(1,.2f,.3f,.4f,.5f);AndroidUniform1fv(2,32,fog);
    }
    assert(calls==3);
    assert(!memcmp(actual[2].data(),fog,sizeof(fog)));
    fog[17]=.123f;AndroidUniform1fv(2,32,fog);assert(calls==4);
    assert(!memcmp(actual[2].data(),fog,sizeof(fog)));
    AndroidUniform1i(0,0);assert(calls==5);
    AndroidUniformReset();AndroidUniform1fv(2,32,fog);assert(calls==6);
    // Overflow/reused locations can cost an upload, never leave stale GPU data.
    for(int i=0;i<1000;i++) {
        int loc=i%23,value=i;AndroidUniform1i(loc,value);
        assert(!memcmp(actual[loc].data(),&value,sizeof(value)));
    }
    puts("PASS: 15000 redundant uniform requests -> 3 uploads; animated fog, resets and cache overflow remain exact");
}
