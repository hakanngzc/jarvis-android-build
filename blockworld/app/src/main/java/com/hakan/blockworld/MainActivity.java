package com.hakan.blockworld;

import android.app.Activity;
import android.os.Bundle;
import android.opengl.GLES20;
import android.opengl.GLSurfaceView;
import android.opengl.Matrix;
import android.graphics.*;
import android.graphics.drawable.ColorDrawable;
import android.view.*;
import android.content.Context;
import android.content.pm.ActivityInfo;
import java.nio.*;
import java.util.*;

public class MainActivity extends Activity {
    GameView game;
    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION |
            View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
        FrameLayout root = new FrameLayout(this);
        game = new GameView(this);
        HudView hud = new HudView(this, game);
        root.addView(game, new FrameLayout.LayoutParams(-1,-1));
        root.addView(hud, new FrameLayout.LayoutParams(-1,-1));
        setContentView(root);
    }
    @Override protected void onPause(){ super.onPause(); game.onPause(); }
    @Override protected void onResume(){ super.onResume(); game.onResume(); }
}

class GameView extends GLSurfaceView {
    final Renderer3D renderer;
    volatile float moveX=0, moveY=0;
    GameView(Context c){ super(c); setEGLContextClientVersion(2); renderer=new Renderer3D(); setRenderer(renderer); setRenderMode(RENDERMODE_CONTINUOUSLY); }
    void setMove(float x,float y){ moveX=x; moveY=y; renderer.moveX=x; renderer.moveY=y; }
    void look(float dx,float dy){ renderer.yaw += dx*0.20f; renderer.pitch -= dy*0.17f; renderer.pitch=Math.max(-82,Math.min(82,renderer.pitch)); }
    void jump(){ renderer.jumpRequest=true; }
    void breakBlock(){ queueEvent(renderer::breakTarget); }
    void placeBlock(){ queueEvent(renderer::placeTarget); }
    void selectBlock(int i){ renderer.selected=Math.max(1,Math.min(5,i)); }
}

class HudView extends View {
    final Paint p=new Paint(Paint.ANTI_ALIAS_FLAG); final GameView game;
    int leftPointer=-1,rightPointer=-1; float leftStartX,leftStartY,leftX,leftY,rightLastX,rightLastY;
    float density; final String[] names={"","Çim","Toprak","Taş","Odun","Yaprak"};
    HudView(Context c,GameView g){ super(c); game=g; density=getResources().getDisplayMetrics().density; setBackground(new ColorDrawable(Color.TRANSPARENT)); }
    float d(float v){return v*density;}
    @Override protected void onDraw(Canvas c){ super.onDraw(c); int w=getWidth(),h=getHeight();
        p.setStyle(Paint.Style.STROKE); p.setStrokeWidth(d(2)); p.setColor(0xDFFFFFFF);
        c.drawLine(w/2f-d(10),h/2f,w/2f+d(10),h/2f,p); c.drawLine(w/2f,h/2f-d(10),w/2f,h/2f+d(10),p);
        float joyR=d(62), knobR=d(26), jx=d(95), jy=h-d(92);
        p.setStyle(Paint.Style.FILL); p.setColor(0x33000000); c.drawCircle(jx,jy,joyR,p); p.setColor(0x66FFFFFF);
        float kx=leftPointer>=0?leftX:jx, ky=leftPointer>=0?leftY:jy; float vx=kx-jx,vy=ky-jy,mag=(float)Math.hypot(vx,vy); if(mag>joyR){kx=jx+vx/mag*joyR;ky=jy+vy/mag*joyR;} c.drawCircle(kx,ky,knobR,p);
        drawButton(c,w-d(86),h-d(142),d(58),"KIR"); drawButton(c,w-d(155),h-d(78),d(52),"KOY"); drawButton(c,w-d(72),h-d(62),d(42),"ZIPLA");
        float slot=d(48), gap=d(6), total=5*slot+4*gap, sx=(w-total)/2f, sy=h-d(66);
        for(int i=1;i<=5;i++){ p.setStyle(Paint.Style.FILL); p.setColor(i==game.renderer.selected?0xCCFFFFFF:0x77000000); c.drawRoundRect(sx+(i-1)*(slot+gap),sy,sx+(i-1)*(slot+gap)+slot,sy+slot,d(7),d(7),p); p.setTextAlign(Paint.Align.CENTER); p.setTextSize(d(11)); p.setColor(i==game.renderer.selected?Color.BLACK:Color.WHITE); c.drawText(names[i],sx+(i-1)*(slot+gap)+slot/2,sy+slot/2+d(4),p); }
        p.setTextAlign(Paint.Align.LEFT); p.setTextSize(d(13)); p.setColor(0xDDFFFFFF); c.drawText("BlockWorld v0.1",d(14),d(22),p); c.drawText("Dünya: 24×24  •  Survival prototipi",d(14),d(40),p);
        invalidate();
    }
    void drawButton(Canvas c,float x,float y,float r,String t){p.setStyle(Paint.Style.FILL);p.setColor(0x66000000);c.drawCircle(x,y,r,p);p.setColor(Color.WHITE);p.setTextAlign(Paint.Align.CENTER);p.setTextSize(d(12));c.drawText(t,x,y+d(4),p);}
    @Override public boolean onTouchEvent(android.view.MotionEvent e){ int a=e.getActionMasked(), idx=e.getActionIndex(), id=e.getPointerId(idx),w=getWidth(),h=getHeight();
        if(a==MotionEvent.ACTION_DOWN||a==MotionEvent.ACTION_POINTER_DOWN){ float x=e.getX(idx),y=e.getY(idx);
            float slot=d(48),gap=d(6),total=5*slot+4*gap,sx=(w-total)/2f,sy=h-d(66); if(y>=sy && y<=sy+slot){int s=(int)((x-sx)/(slot+gap))+1;if(s>=1&&s<=5)game.selectBlock(s);return true;}
            if(dist(x,y,w-d(86),h-d(142))<d(60)){game.breakBlock();return true;} if(dist(x,y,w-d(155),h-d(78))<d(55)){game.placeBlock();return true;} if(dist(x,y,w-d(72),h-d(62))<d(48)){game.jump();return true;}
            if(x<w*0.42f && y>h*0.38f && leftPointer<0){leftPointer=id;leftStartX=d(95);leftStartY=h-d(92);leftX=x;leftY=y;updateMove();} else if(rightPointer<0){rightPointer=id;rightLastX=x;rightLastY=y;}
        } else if(a==MotionEvent.ACTION_MOVE){ for(int i=0;i<e.getPointerCount();i++){int pid=e.getPointerId(i),xid=i;float x=e.getX(xid),y=e.getY(xid);if(pid==leftPointer){leftX=x;leftY=y;updateMove();}if(pid==rightPointer){game.look(x-rightLastX,y-rightLastY);rightLastX=x;rightLastY=y;}} }
        else if(a==MotionEvent.ACTION_UP||a==MotionEvent.ACTION_POINTER_UP||a==MotionEvent.ACTION_CANCEL){ if(id==leftPointer){leftPointer=-1;game.setMove(0,0);} if(id==rightPointer)rightPointer=-1; }
        return true;
    }
    void updateMove(){float dx=leftX-leftStartX,dy=leftY-leftStartY,r=d(62),m=(float)Math.hypot(dx,dy);if(m>r){dx=dx/m*r;dy=dy/m*r;}game.setMove(dx/r,-dy/r);}
    float dist(float a,float b,float c,float d){return(float)Math.hypot(a-c,b-d);}
}

class Renderer3D implements GLSurfaceView.Renderer {
    static final int W=24,H=12,D=24; byte[][][] world=new byte[W][H][D];
    FloatBuffer mesh; int vertexCount=0, program, aPos,aCol,uMvp; float[] proj=new float[16],view=new float[16],mvp=new float[16];
    volatile float moveX,moveY,yaw=-35,pitch=-10; volatile boolean jumpRequest=false; volatile int selected=2;
    float px=12.5f,py=6.0f,pz=12.5f,vy=0; long last=System.nanoTime();
    final float[][] colors={{0,0,0,1},{0.30f,0.72f,0.24f,1},{0.48f,0.30f,0.15f,1},{0.45f,0.47f,0.50f,1},{0.52f,0.32f,0.16f,1},{0.24f,0.58f,0.22f,1}};
    Renderer3D(){generate();}
    void generate(){ Random r=new Random(1337); for(int x=0;x<W;x++)for(int z=0;z<D;z++){int top=2+(int)(1.2*Math.sin(x*.45)+1.1*Math.cos(z*.37));top=Math.max(2,Math.min(5,top));for(int y=0;y<=top;y++)world[x][y][z]=(byte)(y==top?1:(y>top-3?2:3));}
        for(int t=0;t<12;t++){int x=2+r.nextInt(W-4),z=2+r.nextInt(D-4),g=top(x,z);for(int y=g+1;y<=g+3&&y<H;y++)world[x][y][z]=4;for(int dx=-2;dx<=2;dx++)for(int dz=-2;dz<=2;dz++)for(int dy=2;dy<=4;dy++){if(Math.abs(dx)+Math.abs(dz)<4 && in(x+dx,g+dy,z+dz)&&world[x+dx][g+dy][z+dz]==0)world[x+dx][g+dy][z+dz]=5;}}
    }
    int top(int x,int z){for(int y=H-1;y>=0;y--)if(world[x][y][z]!=0)return y;return 0;}
    boolean in(int x,int y,int z){return x>=0&&x<W&&y>=0&&y<H&&z>=0&&z<D;}
    @Override public void onSurfaceCreated(javax.microedition.khronos.opengles.GL10 gl,javax.microedition.khronos.egl.EGLConfig cfg){GLES20.glClearColor(0.47f,0.72f,0.95f,1);GLES20.glEnable(GLES20.GL_DEPTH_TEST);GLES20.glEnable(GLES20.GL_CULL_FACE);program=shader();aPos=GLES20.glGetAttribLocation(program,"aPos");aCol=GLES20.glGetAttribLocation(program,"aCol");uMvp=GLES20.glGetUniformLocation(program,"uMvp");buildMesh();}
    @Override public void onSurfaceChanged(javax.microedition.khronos.opengles.GL10 gl,int w,int h){GLES20.glViewport(0,0,w,h);Matrix.perspectiveM(proj,0,70f,(float)w/h,0.08f,70f);}
    @Override public void onDrawFrame(javax.microedition.khronos.opengles.GL10 gl){long n=System.nanoTime();float dt=Math.min(.04f,(n-last)/1_000_000_000f);last=n;update(dt);GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT|GLES20.GL_DEPTH_BUFFER_BIT);float ry=(float)Math.toRadians(yaw),rp=(float)Math.toRadians(pitch);float dx=(float)(Math.cos(rp)*Math.sin(ry)),dy=(float)Math.sin(rp),dz=(float)(-Math.cos(rp)*Math.cos(ry));Matrix.setLookAtM(view,0,px,py,pz,px+dx,py+dy,pz+dz,0,1,0);Matrix.multiplyMM(mvp,0,proj,0,view,0);GLES20.glUseProgram(program);GLES20.glUniformMatrix4fv(uMvp,1,false,mvp,0);mesh.position(0);GLES20.glEnableVertexAttribArray(aPos);GLES20.glVertexAttribPointer(aPos,3,GLES20.GL_FLOAT,false,7*4,mesh);mesh.position(3);GLES20.glEnableVertexAttribArray(aCol);GLES20.glVertexAttribPointer(aCol,4,GLES20.GL_FLOAT,false,7*4,mesh);GLES20.glDrawArrays(GLES20.GL_TRIANGLES,0,vertexCount);}
    void update(float dt){float ry=(float)Math.toRadians(yaw);float fx=(float)Math.sin(ry),fz=(float)-Math.cos(ry),rx=(float)Math.cos(ry),rz=(float)Math.sin(ry);float speed=4.3f;float mx=(fx*moveY+rx*moveX)*speed*dt,mz=(fz*moveY+rz*moveX)*speed*dt;moveAxis(mx,0);moveAxis(mz,2);boolean grounded=collides(px,py-1.72f-.06f,pz);if(jumpRequest&&grounded)vy=5.3f;jumpRequest=false;vy-=12.5f*dt;float ny=py+vy*dt;if(!collides(px,ny-1.62f,pz)&&!collides(px,ny-.12f,pz))py=ny;else {if(vy<0)py=(float)Math.floor(py-1.62f)+2.63f;vy=0;} if(py<1){px=12.5f;py=8;pz=12.5f;vy=0;}}
    void moveAxis(float d,int axis){float nx=px,nz=pz;if(axis==0)nx+=d;else nz+=d;if(!playerHit(nx,py,nz)){px=nx;pz=nz;}}
    boolean playerHit(float x,float y,float z){float hw=.28f;return collides(x-hw,y-1.6f,z-hw)||collides(x+hw,y-1.6f,z-hw)||collides(x-hw,y-1.6f,z+hw)||collides(x+hw,y-1.6f,z+hw)||collides(x-hw,y-.1f,z-hw)||collides(x+hw,y-.1f,z+hw);}
    boolean collides(float x,float y,float z){int bx=(int)Math.floor(x),by=(int)Math.floor(y),bz=(int)Math.floor(z);return in(bx,by,bz)&&world[bx][by][bz]!=0;}
    int[] ray(boolean place){float ry=(float)Math.toRadians(yaw),rp=(float)Math.toRadians(pitch);float dx=(float)(Math.cos(rp)*Math.sin(ry)),dy=(float)Math.sin(rp),dz=(float)(-Math.cos(rp)*Math.cos(ry));int lx=-1,ly=-1,lz=-1;for(float t=.1f;t<=6f;t+=.07f){int x=(int)Math.floor(px+dx*t),y=(int)Math.floor(py+dy*t),z=(int)Math.floor(pz+dz*t);if(!in(x,y,z))continue;if(world[x][y][z]!=0)return place?new int[]{lx,ly,lz}:new int[]{x,y,z};lx=x;ly=y;lz=z;}return null;}
    void breakTarget(){int[] a=ray(false);if(a!=null&&a[1]>0){world[a[0]][a[1]][a[2]]=0;buildMesh();}}
    void placeTarget(){int[] a=ray(true);if(a!=null&&in(a[0],a[1],a[2])&&world[a[0]][a[1]][a[2]]==0){float cx=a[0]+.5f,cy=a[1]+.5f,cz=a[2]+.5f;if(Math.abs(cx-px)>.7f||Math.abs(cz-pz)>.7f||Math.abs(cy-(py-.8f))>1.2f){world[a[0]][a[1]][a[2]]=(byte)selected;buildMesh();}}}
    void buildMesh(){ArrayList<Float> v=new ArrayList<>();int[][] dirs={{0,0,-1},{0,0,1},{-1,0,0},{1,0,0},{0,-1,0},{0,1,0}};for(int x=0;x<W;x++)for(int y=0;y<H;y++)for(int z=0;z<D;z++){int t=world[x][y][z];if(t==0)continue;for(int f=0;f<6;f++){int nx=x+dirs[f][0],ny=y+dirs[f][1],nz=z+dirs[f][2];if(in(nx,ny,nz)&&world[nx][ny][nz]!=0)continue;face(v,x,y,z,f,t);}}float[] arr=new float[v.size()];for(int i=0;i<arr.length;i++)arr[i]=v.get(i);ByteBuffer bb=ByteBuffer.allocateDirect(arr.length*4).order(ByteOrder.nativeOrder());mesh=bb.asFloatBuffer();mesh.put(arr).position(0);vertexCount=arr.length/7;}
    void face(ArrayList<Float> o,float x,float y,float z,int f,int type){float[][][] q={{{0,0,0},{1,1,0},{1,0,0},{0,0,0},{0,1,0},{1,1,0}},{{0,0,1},{1,0,1},{1,1,1},{0,0,1},{1,1,1},{0,1,1}},{{0,0,0},{0,0,1},{0,1,1},{0,0,0},{0,1,1},{0,1,0}},{{1,0,0},{1,1,0},{1,1,1},{1,0,0},{1,1,1},{1,0,1}},{{0,0,0},{1,0,0},{1,0,1},{0,0,0},{1,0,1},{0,0,1}},{{0,1,0},{0,1,1},{1,1,1},{0,1,0},{1,1,1},{1,1,0}}};float shade=(f==5?1f:(f==4?.58f:(f<2?.78f:.88f)));float[] c=colors[type];for(int i=0;i<6;i++){add(o,x+q[f][i][0],y+q[f][i][1],z+q[f][i][2],c[0]*shade,c[1]*shade,c[2]*shade,1);}}
    void add(ArrayList<Float>o,float x,float y,float z,float r,float g,float b,float a){o.add(x);o.add(y);o.add(z);o.add(r);o.add(g);o.add(b);o.add(a);}
    int shader(){String vs="uniform mat4 uMvp; attribute vec3 aPos; attribute vec4 aCol; varying vec4 vCol; void main(){vCol=aCol; gl_Position=uMvp*vec4(aPos,1.0);}";String fs="precision mediump float; varying vec4 vCol; void main(){gl_FragColor=vCol;}";int v=compile(GLES20.GL_VERTEX_SHADER,vs),f=compile(GLES20.GL_FRAGMENT_SHADER,fs),p=GLES20.glCreateProgram();GLES20.glAttachShader(p,v);GLES20.glAttachShader(p,f);GLES20.glLinkProgram(p);return p;}
    int compile(int t,String s){int sh=GLES20.glCreateShader(t);GLES20.glShaderSource(sh,s);GLES20.glCompileShader(sh);return sh;}
}
