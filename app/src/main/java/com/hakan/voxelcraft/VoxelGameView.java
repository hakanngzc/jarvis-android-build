package com.hakan.voxelcraft;

import android.content.Context;
import android.opengl.GLES20;
import android.opengl.GLSurfaceView;
import android.opengl.Matrix;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.util.Random;
import android.content.SharedPreferences;
import android.util.Base64;

public class VoxelGameView extends GLSurfaceView {
    private final VoxelRenderer renderer;
    private final SharedPreferences prefs;
    private volatile String statusText="";
    private volatile long statusUntil=0;
    public VoxelGameView(Context context){
        super(context); prefs=context.getSharedPreferences("voxelcraft_world_v2", Context.MODE_PRIVATE); setEGLContextClientVersion(2); renderer=new VoxelRenderer(); setRenderer(renderer); setRenderMode(RENDERMODE_CONTINUOUSLY); setPreserveEGLContextOnPause(true);
    }
    public void setMove(float x,float y){ renderer.moveX=x; renderer.moveForward=y; }
    public void look(float dx,float dy){ renderer.yawDelta+=dx; renderer.pitchDelta+=dy; }
    public void jump(){ renderer.wantJump=true; }
    public void breakBlock(){ queueEvent(renderer::breakBlock); }
    public void placeBlock(){ queueEvent(renderer::placeBlock); }
    public void selectBlock(int i){ renderer.selected=Math.max(0,Math.min(3,i)); showStatus(new String[]{"Çim","Toprak","Taş","Odun"}[renderer.selected]); }
    public String getStatusText(){ return statusText; }
    public long getStatusUntil(){ return statusUntil; }
    private void showStatus(String s){ statusText=s; statusUntil=System.currentTimeMillis()+1200; }
    public void requestSave(){ queueEvent(this::saveWorld); }
    private void saveWorld(){
        byte[] data=new byte[VoxelRenderer.SX*VoxelRenderer.SY*VoxelRenderer.SZ]; int k=0;
        for(int x=0;x<VoxelRenderer.SX;x++)for(int y=0;y<VoxelRenderer.SY;y++)for(int z=0;z<VoxelRenderer.SZ;z++) data[k++]=(byte)renderer.world[x][y][z];
        prefs.edit().putString("blocks",Base64.encodeToString(data,Base64.NO_WRAP))
                .putFloat("px",renderer.px).putFloat("py",renderer.py).putFloat("pz",renderer.pz)
                .putFloat("yaw",renderer.yaw).putFloat("pitch",renderer.pitch).apply();
        showStatus("Dünya kaydedildi");
    }
    private boolean loadWorld(){
        String s=prefs.getString("blocks",null); if(s==null)return false;
        try{
            byte[] data=Base64.decode(s,Base64.DEFAULT);
            if(data.length!=VoxelRenderer.SX*VoxelRenderer.SY*VoxelRenderer.SZ)return false;
            int k=0; for(int x=0;x<VoxelRenderer.SX;x++)for(int y=0;y<VoxelRenderer.SY;y++)for(int z=0;z<VoxelRenderer.SZ;z++) renderer.world[x][y][z]=data[k++]&0xff;
            renderer.px=prefs.getFloat("px",VoxelRenderer.SX/2f+.5f); renderer.py=prefs.getFloat("py",7f); renderer.pz=prefs.getFloat("pz",VoxelRenderer.SZ/2f+.5f);
            renderer.yaw=prefs.getFloat("yaw",0f); renderer.pitch=prefs.getFloat("pitch",-8f); return true;
        }catch(Exception e){ return false; }
    }

    static class VoxelRenderer implements Renderer {
        static final int SX=32,SY=16,SZ=32;
        final int[][][] world=new int[SX][SY][SZ];
        final float[] proj=new float[16],view=new float[16],vp=new float[16];
        FloatBuffer mesh; int vertexCount=0; boolean meshDirty=true;
        int program,aPos,aColor,uMvp;
        volatile float moveX=0,moveForward=0,yawDelta=0,pitchDelta=0;
        volatile boolean wantJump=false; volatile int selected=0;
        float px=16.5f,py=7,pz=16.5f,yaw=0,pitch=-8,vy=0;
        float spawnX,spawnY,spawnZ; boolean grounded=false;
        long lastNanos=0;
        final int[] palette={1,2,3,4};

        @Override public void onSurfaceCreated(javax.microedition.khronos.opengles.GL10 gl, javax.microedition.khronos.egl.EGLConfig config){
            GLES20.glClearColor(0.38f,0.68f,0.92f,1f); GLES20.glEnable(GLES20.GL_DEPTH_TEST); GLES20.glEnable(GLES20.GL_CULL_FACE); GLES20.glCullFace(GLES20.GL_BACK);
            program=createProgram(VS,FS); aPos=GLES20.glGetAttribLocation(program,"aPos"); aColor=GLES20.glGetAttribLocation(program,"aColor"); uMvp=GLES20.glGetUniformLocation(program,"uMvp");
            if(!loadWorld()) generateWorld(); else { spawnX=SX/2f+.5f; spawnZ=SZ/2f+.5f; spawnY=Math.max(2,topY(SX/2,SZ/2)+1.02f); } rebuildMesh();
        }
        @Override public void onSurfaceChanged(javax.microedition.khronos.opengles.GL10 gl,int width,int height){ GLES20.glViewport(0,0,width,height); Matrix.perspectiveM(proj,0,67f,width/(float)Math.max(1,height),0.08f,90f); }
        @Override public void onDrawFrame(javax.microedition.khronos.opengles.GL10 gl){
            long now=System.nanoTime(); float dt=lastNanos==0?0.016f:(now-lastNanos)/1_000_000_000f; lastNanos=now; if(dt>0.05f)dt=0.05f;
            update(dt); if(meshDirty)rebuildMesh();
            GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT|GLES20.GL_DEPTH_BUFFER_BIT);
            float eyeY=py+1.62f; float cy=(float)Math.cos(Math.toRadians(pitch)), sy=(float)Math.sin(Math.toRadians(pitch)); float sx=(float)Math.sin(Math.toRadians(yaw)), cz=(float)Math.cos(Math.toRadians(yaw));
            float dx=sx*cy, dy=-sy, dz=-cz*cy;
            Matrix.setLookAtM(view,0,px,eyeY,pz,px+dx,eyeY+dy,pz+dz,0,1,0); Matrix.multiplyMM(vp,0,proj,0,view,0);
            GLES20.glUseProgram(program); GLES20.glUniformMatrix4fv(uMvp,1,false,vp,0);
            mesh.position(0); GLES20.glEnableVertexAttribArray(aPos); GLES20.glVertexAttribPointer(aPos,3,GLES20.GL_FLOAT,false,24,mesh);
            mesh.position(3); GLES20.glEnableVertexAttribArray(aColor); GLES20.glVertexAttribPointer(aColor,3,GLES20.GL_FLOAT,false,24,mesh);
            GLES20.glDrawArrays(GLES20.GL_TRIANGLES,0,vertexCount);
            GLES20.glDisableVertexAttribArray(aPos); GLES20.glDisableVertexAttribArray(aColor);
        }

        void generateWorld(){
            Random rnd=new Random(3042026L); int spawnGround=0;
            for(int x=0;x<SX;x++) for(int z=0;z<SZ;z++){
                int h=4+(int)Math.round(1.45*Math.sin(x*0.31)+1.10*Math.cos(z*0.27)+0.75*Math.sin((x+z)*0.19)+0.35*Math.cos((x-z)*0.41)); h=Math.max(2,Math.min(8,h));
                for(int y=0;y<=h;y++){ if(y==h)world[x][y][z]=1; else if(y>=h-2)world[x][y][z]=2; else world[x][y][z]=3; }
                if(x==SX/2&&z==SZ/2)spawnGround=h;
            }
            for(int i=0;i<22;i++){
                int x=2+rnd.nextInt(SX-4), z=2+rnd.nextInt(SZ-4); if(Math.abs(x-SX/2)<3&&Math.abs(z-SZ/2)<3)continue; int y=topY(x,z)+1; if(y<2||y+4>=SY)continue;
                for(int t=0;t<3;t++) world[x][y+t][z]=4;
                for(int ox=-2;ox<=2;ox++)for(int oz=-2;oz<=2;oz++)for(int oy=2;oy<=4;oy++) if(Math.abs(ox)+Math.abs(oz)+(oy==4?1:0)<=3){ int xx=x+ox,zz=z+oz,yy=y+oy; if(in(xx,yy,zz)&&world[xx][yy][zz]==0)world[xx][yy][zz]=5; }
            }
            spawnX=SX/2+0.5f; spawnZ=SZ/2+0.5f; spawnY=spawnGround+1.02f; px=spawnX;py=spawnY;pz=spawnZ;
        }
        int topY(int x,int z){ for(int y=SY-1;y>=0;y--)if(world[x][y][z]!=0)return y;return 0; }

        void update(float dt){
            float yd=yawDelta,pd=pitchDelta; yawDelta=0; pitchDelta=0; yaw=(yaw+yd)%360f; pitch=Math.max(-82f,Math.min(82f,pitch+pd));
            float mx=moveX,mf=moveForward; float len=(float)Math.sqrt(mx*mx+mf*mf); if(len>1){mx/=len;mf/=len;}
            float rad=(float)Math.toRadians(yaw); float fx=(float)Math.sin(rad),fz=-(float)Math.cos(rad),rx=(float)Math.cos(rad),rz=(float)Math.sin(rad); float speed=4.15f;
            float dx=(fx*mf+rx*mx)*speed*dt, dz=(fz*mf+rz*mx)*speed*dt;
            moveHorizontal(dx,0); moveHorizontal(0,dz);
            if(wantJump){ wantJump=false; if(grounded){vy=6.25f;grounded=false;} }
            vy-=18.5f*dt; float ny=py+vy*dt;
            if(!collides(px,ny,pz)){py=ny; grounded=false;} else { if(vy<0)grounded=true; vy=0; }
            if(py<-3){px=spawnX;py=spawnY;pz=spawnZ;vy=0;}
        }
        void moveHorizontal(float dx,float dz){ if(Math.abs(dx)+Math.abs(dz)<0.0001f)return; float nx=px+dx,nz=pz+dz; if(!collides(nx,py,nz)){px=nx;pz=nz;} }
        boolean collides(float x,float y,float z){
            float r=0.29f,h=1.78f; int minX=(int)Math.floor(x-r),maxX=(int)Math.floor(x+r),minY=(int)Math.floor(y),maxY=(int)Math.floor(y+h),minZ=(int)Math.floor(z-r),maxZ=(int)Math.floor(z+r);
            for(int xx=minX;xx<=maxX;xx++)for(int yy=minY;yy<=maxY;yy++)for(int zz=minZ;zz<=maxZ;zz++) if(solid(xx,yy,zz))return true; return false;
        }
        boolean solid(int x,int y,int z){ if(x<0||z<0||x>=SX||z>=SZ)return true; if(y<0)return true; if(y>=SY)return false; return world[x][y][z]!=0; }

        int[] raycast(){
            float eyeY=py+1.62f; float cy=(float)Math.cos(Math.toRadians(pitch)), sy=(float)Math.sin(Math.toRadians(pitch)); float sx=(float)Math.sin(Math.toRadians(yaw)), cz=(float)Math.cos(Math.toRadians(yaw)); float dx=sx*cy,dy=-sy,dz=-cz*cy;
            int pxv=(int)Math.floor(px),pyv=(int)Math.floor(eyeY),pzv=(int)Math.floor(pz);
            for(float t=0.05f;t<=5.2f;t+=0.045f){ int x=(int)Math.floor(px+dx*t),y=(int)Math.floor(eyeY+dy*t),z=(int)Math.floor(pz+dz*t); if(in(x,y,z)&&world[x][y][z]!=0)return new int[]{x,y,z,pxv,pyv,pzv}; pxv=x;pyv=y;pzv=z; }
            return null;
        }
        void breakBlock(){ int[] r=raycast(); if(r==null){showStatus("Blok menzil dışında");return;} if(r[1]==0)return; world[r[0]][r[1]][r[2]]=0; meshDirty=true; showStatus("Blok kırıldı"); }
        void placeBlock(){ int[] r=raycast(); if(r==null){showStatus("Yerleştirilecek yüzey yok");return;} int x=r[3],y=r[4],z=r[5]; if(!in(x,y,z)||world[x][y][z]!=0)return; int old=world[x][y][z]; world[x][y][z]=palette[selected]; if(collides(px,py,pz)){world[x][y][z]=old;showStatus("Buraya blok koyamazsın");return;} meshDirty=true; showStatus("Blok yerleştirildi"); }
        boolean in(int x,int y,int z){ return x>=0&&y>=0&&z>=0&&x<SX&&y<SY&&z<SZ; }

        void rebuildMesh(){
            MeshBuilder b=new MeshBuilder(24000);
            for(int x=0;x<SX;x++)for(int y=0;y<SY;y++)for(int z=0;z<SZ;z++){ int id=world[x][y][z]; if(id==0)continue; float[] base=color(id);
                if(!solidInside(x,y+1,z))face(b,x,y,z,0,base,1.08f); if(!solidInside(x,y-1,z))face(b,x,y,z,1,base,0.58f);
                if(!solidInside(x,y,z+1))face(b,x,y,z,2,base,0.86f); if(!solidInside(x,y,z-1))face(b,x,y,z,3,base,0.73f);
                if(!solidInside(x+1,y,z))face(b,x,y,z,4,base,0.82f); if(!solidInside(x-1,y,z))face(b,x,y,z,5,base,0.67f);
            }
            float[] arr=b.toArray(); ByteBuffer bb=ByteBuffer.allocateDirect(arr.length*4).order(ByteOrder.nativeOrder()); mesh=bb.asFloatBuffer(); mesh.put(arr).position(0); vertexCount=arr.length/6; meshDirty=false;
        }
        boolean solidInside(int x,int y,int z){ return in(x,y,z)&&world[x][y][z]!=0; }
        float[] color(int id){
            switch(id){case 1:return new float[]{0.36f,0.66f,0.25f};case 2:return new float[]{0.48f,0.31f,0.19f};case 3:return new float[]{0.48f,0.50f,0.51f};case 4:return new float[]{0.50f,0.34f,0.20f};case 5:return new float[]{0.18f,0.46f,0.18f};default:return new float[]{1,1,1};}
        }
        void face(MeshBuilder b,int x,int y,int z,int f,float[] c,float shade){
            final float[][][] F={
                    {{0,1,0},{0,1,1},{1,1,1},{0,1,0},{1,1,1},{1,1,0}},
                    {{0,0,0},{1,0,1},{0,0,1},{0,0,0},{1,0,0},{1,0,1}},
                    {{0,0,1},{1,0,1},{1,1,1},{0,0,1},{1,1,1},{0,1,1}},
                    {{1,0,0},{0,0,0},{0,1,0},{1,0,0},{0,1,0},{1,1,0}},
                    {{1,0,1},{1,0,0},{1,1,0},{1,0,1},{1,1,0},{1,1,1}},
                    {{0,0,0},{0,0,1},{0,1,1},{0,0,0},{0,1,1},{0,1,0}}
            };
            float r=Math.min(1,c[0]*shade),g=Math.min(1,c[1]*shade),bl=Math.min(1,c[2]*shade);
            for(float[] v:F[f])b.add(x+v[0],y+v[1],z+v[2],r,g,bl);
        }
        int createProgram(String vs,String fs){ int v=shader(GLES20.GL_VERTEX_SHADER,vs),f=shader(GLES20.GL_FRAGMENT_SHADER,fs); int p=GLES20.glCreateProgram(); GLES20.glAttachShader(p,v); GLES20.glAttachShader(p,f); GLES20.glLinkProgram(p); return p; }
        int shader(int type,String src){ int s=GLES20.glCreateShader(type); GLES20.glShaderSource(s,src); GLES20.glCompileShader(s); return s; }
        static final String VS="uniform mat4 uMvp; attribute vec3 aPos; attribute vec3 aColor; varying vec3 vColor; void main(){vColor=aColor; gl_Position=uMvp*vec4(aPos,1.0);}";
        static final String FS="precision mediump float; varying vec3 vColor; void main(){gl_FragColor=vec4(vColor,1.0);}";
    }

    static class MeshBuilder {
        float[] a; int n=0; MeshBuilder(int initial){a=new float[initial];}
        void add(float x,float y,float z,float r,float g,float b){ if(n+6>a.length){float[] q=new float[a.length*2];System.arraycopy(a,0,q,0,n);a=q;} a[n++]=x;a[n++]=y;a[n++]=z;a[n++]=r;a[n++]=g;a[n++]=b; }
        float[] toArray(){float[] q=new float[n];System.arraycopy(a,0,q,0,n);return q;}
    }
}
