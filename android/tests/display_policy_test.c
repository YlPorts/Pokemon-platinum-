#include <assert.h>
#include <stdio.h>
#include "android_screen_policy.h"
int main(void) {
 ADScreenPolicy p={0xffffffffu,-1};
 assert(ad_selected_screen(&p,0,0)==0);
 p.manual=1; for(int i=0;i<120;i++) assert(ad_selected_screen(&p,0,0)==1);
 /* A scene change releases the manual override even when main is still top. */
 assert(ad_selected_screen(&p,0,1)==0);
 assert(ad_selected_screen(&p,1,1)==1); /* ball / battle command */
 assert(ad_selected_screen(&p,0,1)==0); /* dialogue / battle animation */
 p.manual=1; p.manual=-1; assert(ad_selected_screen(&p,0,1)==0);
 ADScreenTransition t={-1,-1,0,0};
 assert(ad_automatic_screen(&t,0,0,0)==0);
 assert(ad_automatic_screen(&t,1,0,10)==0);
 assert(ad_automatic_screen(&t,1,0,90)==1);
 assert(ad_automatic_screen(&t,0,0,100)==1);
 assert(ad_automatic_screen(&t,1,0,120)==1); // no flash between battle menus
 assert(ad_automatic_screen(&t,0,0,200)==1);
 assert(ad_automatic_screen(&t,0,0,280)==0);
 assert(ad_automatic_screen(&t,1,1,290)==1); // new application changes immediately
 puts("PASS: automatic top/touch transitions, persistent manual override, app exit reset");
}
