#include <assert.h>
#include <stdio.h>
#include "android_visibility.h"
int main(void) {
 for(int top=0;top<2;top++) for(int bottom=0;bottom<2;bottom++) {
  int main=ad_engine_visible(1,bottom,top,0),sub=ad_engine_visible(1,bottom,top,1);
  assert(main+sub==1);
  if(top && !bottom) assert(main);
  if(top && bottom) assert(sub);
  if(!top && !bottom) assert(sub);
  if(!top && bottom) assert(main);
  assert(ad_engine_visible(0,bottom,top,0) && ad_engine_visible(0,bottom,top,1));
 }
 puts("PASS: only invisible presentation skipped; both engines retained in dual layouts");
}
