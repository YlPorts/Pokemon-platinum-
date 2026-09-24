#include <stdlib.h>
#include <assert.h>
#include <stdio.h>
#include "android_layout.h"
static void bounds(ADRect r,float w,float h) {
 assert(r.w>=0 && r.h>=0 && r.x>=-.01 && r.y>=-.01);
 assert(r.x+r.w<=w+.01 && r.y+r.h<=h+.01);
}
static int overlap(ADRect a,ADRect b) {
 return a.x<b.x+b.w-.1 && a.x+a.w>b.x+.1 && a.y<b.y+b.h-.1 && a.y+a.h>b.y+.1;
}
int main(void) {
 const int sizes[][2]={{540,960},{960,540},{1080,2340},{2340,1080},{800,1280},{1280,800},{600,600}};
 int count=0;
 for(int d=0;d<7;d++) for(int mode=0;mode<5;mode++) for(int swap=0;swap<2;swap++)
 for(int field=0;field<2;field++) for(int show=0;show<2;show++) for(int aspect=0;aspect<3;aspect++)
 for(int size=85;size<=115;size+=15) {
  int w=sizes[d][0],h=sizes[d][1];
  ADLayout a=ad_layout(w,h,mode,swap,field,show,aspect,size);
  bounds(a.top,w,h); bounds(a.touch,w,h);
  for(int i=0;i<15;i++) bounds(a.keys[i],w,h);
  if(a.single) {
   assert((a.top.w>0) != (a.touch.w>0));
   ADRect shown=a.top.w>0?a.top:a.touch;
   assert(fabsf(shown.x+shown.w/2-w/2.0f)<.01f);
   if(w>h) {
    assert(fabsf(shown.y+shown.h/2-h/2.0f)<.01f);
    assert(fabsf(shown.w-w)<.01f || fabsf(shown.h-h)<.01f);
    if(field && !swap && aspect==0) assert(fabsf(shown.y)<.01f);
   }
  } else assert(a.top.w>0 && a.top.h>0);
  if(a.touch.w>0) {
   assert(fabsf(a.touch.w/a.touch.h-4.0f/3.0f)<.001f);
   int x,y;
   assert(ad_stylus(&a,a.touch.x+a.touch.w*.5f,a.touch.y+a.touch.h*.5f,&x,&y));
   assert(abs(x-128)<=1 && abs(y-96)<=1);
   assert(ad_stylus(&a,a.touch.x,a.touch.y,&x,&y) && x==0 && y==0);
   assert(!ad_stylus(&a,a.touch.x+a.touch.w,a.touch.y,&x,&y));
  }
  if(!a.expanded) assert(fabsf(a.aspect-4.0f/3.0f)<.001f);
  else if(aspect==1) assert(fabsf(a.aspect-16.0f/9.0f)<.001f);
  else if(aspect==2) assert(fabsf(a.aspect-21.0f/9.0f)<.001f);
  if(!a.single || swap) assert(a.touch.w>0);
  for(int k=0;k<8;k++) { ADRect r=a.keys[k]; assert(ad_pad_hit(&a,r.x+r.w/2,r.y+r.h/2)==(1<<k)); }
  ADRect u=a.keys[AD_UP];float c=u.w,cx=u.x+c/2,cy=u.y+c*1.5f;
  assert(ad_pad_hit(&a,cx+c*.8f,cy-c*.8f)==((1<<AD_UP)|(1<<AD_RIGHT)));
  count++;
 }
 printf("PASS: %d layouts, aspect preservation, stylus bounds, DS buttons and diagonals\n",count);
}
