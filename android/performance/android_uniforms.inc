/* g3 owns these uniforms. Reset with its GL objects; preserve exact bytes. */
struct ADUniformEntry { bool valid; GLint location; unsigned kind,bytes; unsigned char data[128]; };
static ADUniformEntry s_androidUniforms[16];
static unsigned s_androidUniformCursor;
static void AndroidUniformReset() {
    memset(s_androidUniforms,0,sizeof(s_androidUniforms));s_androidUniformCursor=0;
}
static bool AndroidUniformChanged(GLint location,unsigned kind,const void *data,unsigned bytes) {
    if(location<0) return false;
    if(bytes>128) return true;
    ADUniformEntry *entry=nullptr;
    for(auto &e:s_androidUniforms) if(e.valid && e.location==location) { entry=&e;break; }
    if(entry && entry->kind==kind && entry->bytes==bytes && !memcmp(entry->data,data,bytes)) return false;
    if(!entry) entry=&s_androidUniforms[(s_androidUniformCursor++)%16];
    entry->valid=true;entry->location=location;entry->kind=kind;entry->bytes=bytes;
    memcpy(entry->data,data,bytes);return true;
}
static void AndroidUniform1i(GLint location,GLint value) {
    if(AndroidUniformChanged(location,1,&value,sizeof(value))) glUniform1i(location,value);
}
static void AndroidUniform4f(GLint location,GLfloat x,GLfloat y,GLfloat z,GLfloat w) {
    GLfloat data[4]={x,y,z,w};
    if(AndroidUniformChanged(location,2,data,sizeof(data))) glUniform4f(location,x,y,z,w);
}
static void AndroidUniform1fv(GLint location,GLsizei count,const GLfloat *data) {
    if(count<0 || AndroidUniformChanged(location,3,data,sizeof(*data)*count)) glUniform1fv(location,count,data);
}
