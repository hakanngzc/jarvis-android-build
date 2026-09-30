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
    private final int[] inventory={0,0,0,0,0};
    private volatile int health=20;
    private volatile int hunger=20;

    public VoxelGameView(Context context){
        super(context);
        prefs=context.getSharedPreferences("voxelcraft_world_v2", Context.MODE_PRIVATE);
        setEGLContextClientVersion(2);
        renderer=new VoxelRenderer();
        setRenderer(renderer);
        setRenderMode(RENDERMODE_CONTINUOUSLY);
        setPreserveEGLContextOnPause(true);
    }

    public void setMove(float x,float y){ renderer.moveX=x; renderer.moveForward=y; }
    public void look(float dx,float dy){ renderer.yawDelta+=dx; renderer.pitchDelta+=dy; }
    public void jump(){ renderer.wantJump=true; }
    public void breakBlock(){ queueEvent(renderer::breakBlock); }
    public void placeBlock(){ queueEvent(renderer::placeBlock); }
    public void selectBlock(int i){
        renderer.selected=Math.max(0,Math.min(4,i));
        showStatus(new String[]{"Çim","Toprak","Taş","Odun","Yaprak"}[renderer.selected]+" seçildi");
    }
    public String getStatusText(){ return statusText; }
    public long getStatusUntil(){ return statusUntil; }
    public int getInventoryCount(int i){ return (i>=0&&i<inventory.length)?inventory[i]:0; }
    public int getHealth(){ return health; }
    public int getHunger(){ return hunger; }
    private void showStatus(String s){ statusText=s; statusUntil=System.currentTimeMillis()+1300; }
    public void requestSave(){ queueEvent(this::saveWorld); }

    private void saveWorld(){
        byte[] data=new byte[VoxelRenderer.SX*VoxelRenderer.SY*VoxelRenderer.SZ];
        int k=0;
        for(int x=0;x<VoxelRenderer.SX;x++)for(int y=0;y<VoxelRenderer.SY;y++)for(int z=0;z<VoxelRenderer.SZ;z++)
            data[k++]=(byte)renderer.world[x][y][z];

        prefs.edit()
                .putString("blocks",Base64.encodeToString(data,Base64.NO_WRAP))
                .putFloat("px",renderer.px).putFloat("py",renderer.py).putFloat("pz",renderer.pz)
                .putFloat("yaw",renderer.yaw).putFloat("pitch",renderer.pitch)
                .putInt("inv0",inventory[0]).putInt("inv1",inventory[1]).putInt("inv2",inventory[2])
                .putInt("inv3",inventory[3]).putInt("inv4",inventory[4])
                .putInt("health",health).putInt("hunger",hunger)
                .apply();
    }

    private boolean loadWorld(){
        String s=prefs.getString("blocks",null);
        if(s==null)return false;
        try{
            byte[] data=Base64.decode(s,Base64.DEFAULT);
            if(data.length!=VoxelRenderer.SX*VoxelRenderer.SY*VoxelRenderer.SZ)return false;
            int k=0;
            for(int x=0;x<VoxelRenderer.SX;x++)for(int y=0;y<VoxelRenderer.SY;y++)for(int z=0;z<VoxelRenderer.SZ;z++)
                renderer.world[x][y][z]=data[k++]&0xff;

            renderer.px=prefs.getFloat("px",VoxelRenderer.SX/2f+.5f);
            renderer.py=prefs.getFloat("py",7f);
            renderer.pz=prefs.getFloat("pz",VoxelRenderer.SZ/2f+.5f);
            renderer.yaw=prefs.getFloat("yaw",0f);
            renderer.pitch=prefs.getFloat("pitch",-8f);
            for(int i=0;i<inventory.length;i++) inventory[i]=prefs.getInt("inv"+i,0);
            health=Math.max(1,Math.min(20,prefs.getInt("health",20)));
            hunger=Math.max(0,Math.min(20,prefs.getInt("hunger",20)));
            return true;
        }catch(Exception e){
            return false;
        }
    }

    class VoxelRenderer implements Renderer {
        static final int SX=32,SY=16,SZ=32;
        final int[][][] world=new int[SX][SY][SZ];
        final float[] proj=new float[16],view=new float[16],vp=new float[16];
        final FloatBuffer outlineBuffer;

        FloatBuffer mesh;
        int vertexCount=0;
        boolean meshDirty=true;
        int program,aPos,aColor,uMvp;

        volatile float moveX=0,moveForward=0,yawDelta=0,pitchDelta=0;
        volatile boolean wantJump=false;
        volatile int selected=0;

        float px=16.5f,py=7,pz=16.5f,yaw=0,pitch=-8,vy=0;
        float spawnX,spawnY,spawnZ;
        boolean grounded=false;
        float fallDistance=0f;
        float exhaustion=0f;
        float regenTimer=0f;
        float starveTimer=0f;
        long lastNanos=0;
        final int[] palette={1,2,3,4,5};

        VoxelRenderer(){
            outlineBuffer=ByteBuffer.allocateDirect(24*6*4).order(ByteOrder.nativeOrder()).asFloatBuffer();
        }

        @Override public void onSurfaceCreated(javax.microedition.khronos.opengles.GL10 gl, javax.microedition.khronos.egl.EGLConfig config){
            GLES20.glClearColor(0.39f,0.70f,0.94f,1f);
            GLES20.glEnable(GLES20.GL_DEPTH_TEST);
            GLES20.glEnable(GLES20.GL_CULL_FACE);
            GLES20.glCullFace(GLES20.GL_BACK);

            program=createProgram(VS,FS);
            aPos=GLES20.glGetAttribLocation(program,"aPos");
            aColor=GLES20.glGetAttribLocation(program,"aColor");
            uMvp=GLES20.glGetUniformLocation(program,"uMvp");

            if(!loadWorld()){
                generateWorld();
                saveWorld();
                showStatus("Yeni dünya oluşturuldu");
            }else{
                spawnX=SX/2f+.5f;
                spawnZ=SZ/2f+.5f;
                spawnY=Math.max(2,topY(SX/2,SZ/2)+1.02f);
                if(px<1||pz<1||px>SX-2||pz>SZ-2||py<0||py>SY+4||collides(px,py,pz)){
                    px=spawnX;py=spawnY;pz=spawnZ;yaw=0;pitch=-8;
                }
                showStatus("Dünya yüklendi");
            }
            rebuildMesh();
        }

        @Override public void onSurfaceChanged(javax.microedition.khronos.opengles.GL10 gl,int width,int height){
            GLES20.glViewport(0,0,width,height);
            Matrix.perspectiveM(proj,0,67f,width/(float)Math.max(1,height),0.08f,90f);
        }

        @Override public void onDrawFrame(javax.microedition.khronos.opengles.GL10 gl){
            long now=System.nanoTime();
            float dt=lastNanos==0?0.016f:(now-lastNanos)/1_000_000_000f;
            lastNanos=now;
            if(dt>0.05f)dt=0.05f;

            update(dt);
            if(meshDirty)rebuildMesh();

            GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT|GLES20.GL_DEPTH_BUFFER_BIT);

            float eyeY=py+1.62f;
            float cy=(float)Math.cos(Math.toRadians(pitch));
            float sy=(float)Math.sin(Math.toRadians(pitch));
            float sx=(float)Math.sin(Math.toRadians(yaw));
            float cz=(float)Math.cos(Math.toRadians(yaw));
            float dx=sx*cy, dy=-sy, dz=-cz*cy;

            Matrix.setLookAtM(view,0,px,eyeY,pz,px+dx,eyeY+dy,pz+dz,0,1,0);
            Matrix.multiplyMM(vp,0,proj,0,view,0);

            GLES20.glUseProgram(program);
            GLES20.glUniformMatrix4fv(uMvp,1,false,vp,0);

            mesh.position(0);
            GLES20.glEnableVertexAttribArray(aPos);
            GLES20.glVertexAttribPointer(aPos,3,GLES20.GL_FLOAT,false,24,mesh);
            mesh.position(3);
            GLES20.glEnableVertexAttribArray(aColor);
            GLES20.glVertexAttribPointer(aColor,3,GLES20.GL_FLOAT,false,24,mesh);
            GLES20.glDrawArrays(GLES20.GL_TRIANGLES,0,vertexCount);

            drawTargetOutline();

            GLES20.glDisableVertexAttribArray(aPos);
            GLES20.glDisableVertexAttribArray(aColor);
        }

        void generateWorld(){
            Random rnd=new Random(3042026L);
            int spawnGround=0;

            for(int x=0;x<SX;x++) for(int z=0;z<SZ;z++){
                int h=4+(int)Math.round(
                        1.45*Math.sin(x*0.31)+
                        1.10*Math.cos(z*0.27)+
                        0.75*Math.sin((x+z)*0.19)+
                        0.35*Math.cos((x-z)*0.41));
                h=Math.max(2,Math.min(8,h));

                for(int y=0;y<=h;y++){
                    if(y==h)world[x][y][z]=1;
                    else if(y>=h-2)world[x][y][z]=2;
                    else world[x][y][z]=3;
                }
                if(x==SX/2&&z==SZ/2)spawnGround=h;
            }

            for(int i=0;i<22;i++){
                int x=2+rnd.nextInt(SX-4);
                int z=2+rnd.nextInt(SZ-4);
                if(Math.abs(x-SX/2)<3&&Math.abs(z-SZ/2)<3)continue;
                int y=topY(x,z)+1;
                if(y<2||y+4>=SY)continue;

                for(int t=0;t<3;t++)world[x][y+t][z]=4;

                for(int ox=-2;ox<=2;ox++)for(int oz=-2;oz<=2;oz++)for(int oy=2;oy<=4;oy++){
                    if(Math.abs(ox)+Math.abs(oz)+(oy==4?1:0)<=3){
                        int xx=x+ox,zz=z+oz,yy=y+oy;
                        if(in(xx,yy,zz)&&world[xx][yy][zz]==0)world[xx][yy][zz]=5;
                    }
                }
            }

            spawnX=SX/2+0.5f;
            spawnZ=SZ/2+0.5f;
            spawnY=spawnGround+1.02f;
            px=spawnX;py=spawnY;pz=spawnZ;
        }

        int topY(int x,int z){
            for(int y=SY-1;y>=0;y--)if(world[x][y][z]!=0)return y;
            return 0;
        }

        void update(float dt){
            float yd=yawDelta,pd=pitchDelta;
            yawDelta=0;pitchDelta=0;
            yaw=(yaw+yd)%360f;
            pitch=Math.max(-82f,Math.min(82f,pitch+pd));

            float mx=moveX,mf=moveForward;
            float len=(float)Math.sqrt(mx*mx+mf*mf);
            if(len>1){mx/=len;mf/=len;}

            float rad=(float)Math.toRadians(yaw);
            float fx=(float)Math.sin(rad),fz=-(float)Math.cos(rad);
            float rx=(float)Math.cos(rad),rz=(float)Math.sin(rad);
            float speed=4.15f;

            float dx=(fx*mf+rx*mx)*speed*dt;
            float dz=(fz*mf+rz*mx)*speed*dt;
            moveHorizontal(dx,0);
            moveHorizontal(0,dz);

            if(wantJump){
                wantJump=false;
                if(grounded){
                    vy=6.25f; grounded=false; exhaustion+=0.42f;
                }
            }

            if(len>0.08f && grounded) exhaustion+=len*dt*0.18f;
            while(exhaustion>=4f){
                exhaustion-=4f;
                if(hunger>0) hunger--;
            }

            vy-=18.5f*dt;
            float ny=py+vy*dt;
            if(!collides(px,ny,pz)){
                py=ny;
                if(vy<0) fallDistance+=(-vy)*dt;
                grounded=false;
            }else{
                if(vy<0){
                    if(fallDistance>3.35f){
                        int dmg=(int)Math.ceil(fallDistance-3.35f);
                        damage(dmg,"Düşme hasarı");
                    }
                    fallDistance=0f;
                    grounded=true;
                }else{
                    fallDistance=0f;
                }
                vy=0;
            }

            if(hunger>=18 && health<20){
                regenTimer+=dt;
                if(regenTimer>=4f){
                    regenTimer=0f;
                    health=Math.min(20,health+1);
                    exhaustion+=0.55f;
                }
            }else regenTimer=0f;

            if(hunger==0){
                starveTimer+=dt;
                if(starveTimer>=7f){
                    starveTimer=0f;
                    damage(1,"Açlık");
                }
            }else starveTimer=0f;

            if(py<-3){
                damage(20,"Boşluğa düştün");
            }
        }

        void moveHorizontal(float dx,float dz){
            if(Math.abs(dx)+Math.abs(dz)<0.0001f)return;
            float nx=px+dx,nz=pz+dz;
            if(!collides(nx,py,nz)){px=nx;pz=nz;}
        }
        void damage(int amount,String reason){
            if(amount<=0)return;
            health=Math.max(0,health-amount);
            showStatus(reason+" • Can "+health+"/20");
            if(health<=0){
                health=20; hunger=20; exhaustion=0f; fallDistance=0f;
                px=spawnX; py=spawnY; pz=spawnZ; vy=0f; yaw=0f; pitch=-8f;
                showStatus("Öldün • başlangıç noktasında yeniden doğdun");
            }
            saveWorld();
        }


        boolean collides(float x,float y,float z){
            float r=0.29f,h=1.78f;
            int minX=(int)Math.floor(x-r),maxX=(int)Math.floor(x+r);
            int minY=(int)Math.floor(y),maxY=(int)Math.floor(y+h);
            int minZ=(int)Math.floor(z-r),maxZ=(int)Math.floor(z+r);

            for(int xx=minX;xx<=maxX;xx++)
                for(int yy=minY;yy<=maxY;yy++)
                    for(int zz=minZ;zz<=maxZ;zz++)
                        if(solid(xx,yy,zz))return true;
            return false;
        }

        boolean solid(int x,int y,int z){
            if(x<0||z<0||x>=SX||z>=SZ)return true;
            if(y<0)return true;
            if(y>=SY)return false;
            return world[x][y][z]!=0;
        }

        int[] raycast(){
            float eyeY=py+1.62f;
            float cy=(float)Math.cos(Math.toRadians(pitch));
            float sy=(float)Math.sin(Math.toRadians(pitch));
            float sx=(float)Math.sin(Math.toRadians(yaw));
            float cz=(float)Math.cos(Math.toRadians(yaw));
            float dx=sx*cy,dy=-sy,dz=-cz*cy;

            int pxv=(int)Math.floor(px),pyv=(int)Math.floor(eyeY),pzv=(int)Math.floor(pz);
            for(float t=0.05f;t<=5.4f;t+=0.045f){
                int x=(int)Math.floor(px+dx*t);
                int y=(int)Math.floor(eyeY+dy*t);
                int z=(int)Math.floor(pz+dz*t);
                if(in(x,y,z)&&world[x][y][z]!=0)return new int[]{x,y,z,pxv,pyv,pzv};
                pxv=x;pyv=y;pzv=z;
            }
            return null;
        }

        void breakBlock(){
            int[] r=raycast();
            if(r==null){showStatus("Blok menzil dışında");return;}
            if(r[1]==0){showStatus("En alt katman kırılamaz");return;}
            int broken=world[r[0]][r[1]][r[2]];
            world[r[0]][r[1]][r[2]]=0;
            if(broken>=1&&broken<=5) inventory[broken-1]++;
            meshDirty=true;
            saveWorld();
            showStatus("Blok toplandı • "+inventory[Math.max(0,Math.min(4,broken-1))]+" adet");
        }

        void placeBlock(){
            int[] r=raycast();
            if(r==null){showStatus("Yerleştirilecek yüzey yok");return;}
            int x=r[3],y=r[4],z=r[5];
            if(!in(x,y,z)||world[x][y][z]!=0)return;

            if(inventory[selected]<=0){ showStatus("Bu bloktan envanterde yok"); return; }
            int old=world[x][y][z];
            world[x][y][z]=palette[selected];
            inventory[selected]--;
            if(collides(px,py,pz)){
                world[x][y][z]=old;
                inventory[selected]++;
                showStatus("Buraya blok koyamazsın");
                return;
            }

            meshDirty=true;
            saveWorld();
            showStatus("Blok yerleştirildi • "+inventory[selected]+" kaldı");
        }

        boolean in(int x,int y,int z){
            return x>=0&&y>=0&&z>=0&&x<SX&&y<SY&&z<SZ;
        }

        void rebuildMesh(){
            MeshBuilder b=new MeshBuilder(60000);
            for(int x=0;x<SX;x++)for(int y=0;y<SY;y++)for(int z=0;z<SZ;z++){
                int id=world[x][y][z];
                if(id==0)continue;

                if(!solidInside(x,y+1,z))face(b,x,y,z,0,id,1.08f);
                if(!solidInside(x,y-1,z))face(b,x,y,z,1,id,0.58f);
                if(!solidInside(x,y,z+1))face(b,x,y,z,2,id,0.86f);
                if(!solidInside(x,y,z-1))face(b,x,y,z,3,id,0.73f);
                if(!solidInside(x+1,y,z))face(b,x,y,z,4,id,0.82f);
                if(!solidInside(x-1,y,z))face(b,x,y,z,5,id,0.67f);
            }

            float[] arr=b.toArray();
            ByteBuffer bb=ByteBuffer.allocateDirect(arr.length*4).order(ByteOrder.nativeOrder());
            mesh=bb.asFloatBuffer();
            mesh.put(arr).position(0);
            vertexCount=arr.length/6;
            meshDirty=false;
        }

        void drawTargetOutline(){
            int[] r=raycast();
            if(r==null)return;

            float e=0.004f;
            float x0=r[0]-e,y0=r[1]-e,z0=r[2]-e;
            float x1=r[0]+1+e,y1=r[1]+1+e,z1=r[2]+1+e;

            outlineBuffer.clear();
            line(x0,y0,z0,x1,y0,z0); line(x1,y0,z0,x1,y0,z1);
            line(x1,y0,z1,x0,y0,z1); line(x0,y0,z1,x0,y0,z0);

            line(x0,y1,z0,x1,y1,z0); line(x1,y1,z0,x1,y1,z1);
            line(x1,y1,z1,x0,y1,z1); line(x0,y1,z1,x0,y1,z0);

            line(x0,y0,z0,x0,y1,z0); line(x1,y0,z0,x1,y1,z0);
            line(x1,y0,z1,x1,y1,z1); line(x0,y0,z1,x0,y1,z1);
            outlineBuffer.flip();

            GLES20.glDisable(GLES20.GL_CULL_FACE);
            GLES20.glLineWidth(3f);

            outlineBuffer.position(0);
            GLES20.glVertexAttribPointer(aPos,3,GLES20.GL_FLOAT,false,24,outlineBuffer);
            outlineBuffer.position(3);
            GLES20.glVertexAttribPointer(aColor,3,GLES20.GL_FLOAT,false,24,outlineBuffer);
            GLES20.glDrawArrays(GLES20.GL_LINES,0,24);

            GLES20.glEnable(GLES20.GL_CULL_FACE);
        }

        void line(float ax,float ay,float az,float bx,float by,float bz){
            outlineBuffer.put(ax).put(ay).put(az).put(1f).put(1f).put(1f);
            outlineBuffer.put(bx).put(by).put(bz).put(1f).put(1f).put(1f);
        }

        boolean solidInside(int x,int y,int z){
            return in(x,y,z)&&world[x][y][z]!=0;
        }

        float[] color(int id,int face,int x,int y,int z){
            float[] c;
            switch(id){
                case 1:
                    if(face==0)c=new float[]{0.34f,0.69f,0.24f};
                    else if(face==1)c=new float[]{0.48f,0.31f,0.19f};
                    else c=new float[]{0.43f,0.54f,0.23f};
                    break;
                case 2:c=new float[]{0.49f,0.32f,0.20f};break;
                case 3:c=new float[]{0.49f,0.51f,0.52f};break;
                case 4:
                    if(face==0||face==1)c=new float[]{0.62f,0.46f,0.29f};
                    else c=new float[]{0.49f,0.32f,0.18f};
                    break;
                case 5:c=new float[]{0.18f,0.47f,0.19f};break;
                default:c=new float[]{1,1,1};
            }

            int hash=(x*734287+z*912931+y*193)&7;
            float tint=0.945f+hash*0.010f;
            c[0]=Math.min(1,c[0]*tint);
            c[1]=Math.min(1,c[1]*tint);
            c[2]=Math.min(1,c[2]*tint);
            return c;
        }

        void face(MeshBuilder b,int x,int y,int z,int f,int id,float shade){
            final float[][][] F={
                    {{0,1,0},{0,1,1},{1,1,1},{0,1,0},{1,1,1},{1,1,0}},
                    {{0,0,0},{1,0,1},{0,0,1},{0,0,0},{1,0,0},{1,0,1}},
                    {{0,0,1},{1,0,1},{1,1,1},{0,0,1},{1,1,1},{0,1,1}},
                    {{1,0,0},{0,0,0},{0,1,0},{1,0,0},{0,1,0},{1,1,0}},
                    {{1,0,1},{1,0,0},{1,1,0},{1,0,1},{1,1,0},{1,1,1}},
                    {{0,0,0},{0,0,1},{0,1,1},{0,0,0},{0,1,1},{0,1,0}}
            };

            float[] c=color(id,f,x,y,z);
            float rr=Math.min(1,c[0]*shade);
            float gg=Math.min(1,c[1]*shade);
            float bb=Math.min(1,c[2]*shade);
            for(float[] v:F[f])b.add(x+v[0],y+v[1],z+v[2],rr,gg,bb);
        }

        int createProgram(String vs,String fs){
            int v=shader(GLES20.GL_VERTEX_SHADER,vs);
            int f=shader(GLES20.GL_FRAGMENT_SHADER,fs);
            int p=GLES20.glCreateProgram();
            GLES20.glAttachShader(p,v);
            GLES20.glAttachShader(p,f);
            GLES20.glLinkProgram(p);
            return p;
        }

        int shader(int type,String src){
            int s=GLES20.glCreateShader(type);
            GLES20.glShaderSource(s,src);
            GLES20.glCompileShader(s);
            return s;
        }

        static final String VS="uniform mat4 uMvp; attribute vec3 aPos; attribute vec3 aColor; varying vec3 vColor; void main(){vColor=aColor; gl_Position=uMvp*vec4(aPos,1.0);}";
        static final String FS="precision mediump float; varying vec3 vColor; void main(){gl_FragColor=vec4(vColor,1.0);}";
    }

    static class MeshBuilder {
        float[] a;
        int n=0;

        MeshBuilder(int initial){a=new float[initial];}

        void add(float x,float y,float z,float r,float g,float b){
            if(n+6>a.length){
                float[] q=new float[a.length*2];
                System.arraycopy(a,0,q,0,n);
                a=q;
            }
            a[n++]=x;a[n++]=y;a[n++]=z;
            a[n++]=r;a[n++]=g;a[n++]=b;
        }

        float[] toArray(){
            float[] q=new float[n];
            System.arraycopy(a,0,q,0,n);
            return q;
        }
    }
}
