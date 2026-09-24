/* Append draws into separate buffer ranges. Orphan only when the store fills:
   earlier GL draws retain their original store and cannot be overwritten. */
static const unsigned AD_STREAM_CAPACITY = G3_DRAW_MAX_VERTS * 8;
static unsigned s_androidVertexCursor = AD_STREAM_CAPACITY;
static void AndroidDrawVertices(const G3SIM_Vertex_t *vertices, unsigned count) {
    if(!count) return;
    glBindVertexArray(s_G3DrawVertexArray);
    glBindBuffer(GL_ARRAY_BUFFER, s_G3DrawVertexBuffer);
    if(count > AD_STREAM_CAPACITY) {
        /* Preserve geometry even if a future caller submits larger batches. */
        glBufferData(GL_ARRAY_BUFFER, sizeof(*vertices)*count, vertices, GL_STREAM_DRAW);
        glDrawArrays(GL_TRIANGLES,0,count);
        s_androidVertexCursor=AD_STREAM_CAPACITY;
        return;
    }
    if(s_androidVertexCursor > AD_STREAM_CAPACITY-count) {
        glBufferData(GL_ARRAY_BUFFER,sizeof(*vertices)*AD_STREAM_CAPACITY,NULL,GL_STREAM_DRAW);
        s_androidVertexCursor=0;
    }
    glBufferSubData(GL_ARRAY_BUFFER,sizeof(*vertices)*s_androidVertexCursor,sizeof(*vertices)*count,vertices);
    glDrawArrays(GL_TRIANGLES,s_androidVertexCursor,count);
    s_androidVertexCursor+=count;
}
