package com.hakan.voxelcraft;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.MotionEvent;
import android.view.View;

public class ControlOverlay extends View {
    private final VoxelGameView game;
    private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint stroke = new Paint(Paint.ANTI_ALIAS_FLAG);
    private int movePointer = -1, lookPointer = -1;
    private float moveCx, moveCy, knobX, knobY;
    private float lastLookX, lastLookY;
    private boolean moving;
    private final RectF jumpRect = new RectF();
    private final RectF breakRect = new RectF();
    private final RectF placeRect = new RectF();
    private final RectF[] slots = { new RectF(), new RectF(), new RectF(), new RectF(), new RectF() };
    private int selected = 0;
    private final long started = System.currentTimeMillis();

    public ControlOverlay(Context c, VoxelGameView g) {
        super(c);
        game = g;
        setBackgroundColor(Color.TRANSPARENT);
        stroke.setStyle(Paint.Style.STROKE);
        stroke.setStrokeWidth(dp(2));
        setFocusable(true);
    }

    private float dp(float v) { return v * getResources().getDisplayMetrics().density; }

    @Override protected void onDraw(Canvas c) {
        super.onDraw(c);
        float w=getWidth(), h=getHeight();
        float r=Math.min(w,h)*0.105f;
        if (!moving) { moveCx=w*0.14f; moveCy=h*0.73f; knobX=moveCx; knobY=moveCy; }

        fill.setColor(Color.argb(52,255,255,255)); c.drawCircle(moveCx,moveCy,r,fill);
        stroke.setStrokeWidth(dp(2)); stroke.setColor(Color.argb(145,255,255,255)); c.drawCircle(moveCx,moveCy,r,stroke);
        fill.setColor(Color.argb(110,255,255,255)); c.drawCircle(knobX,knobY,r*0.38f,fill);

        float bw=Math.min(w,h)*0.15f, bh=Math.min(w,h)*0.09f;
        jumpRect.set(w-bw-dp(18), h-bh-dp(18), w-dp(18), h-dp(18));
        breakRect.set(w-bw-dp(18), h-bh*2.25f-dp(26), w-dp(18), h-bh*1.25f-dp(26));
        placeRect.set(w-bw*2.1f-dp(26), h-bh-dp(18), w-bw*1.1f-dp(26), h-dp(18));
        drawButton(c,jumpRect,"ZIPLA"); drawButton(c,breakRect,"KIR"); drawButton(c,placeRect,"KOY");

        float slot=Math.min(w,h)*0.078f, gap=dp(7), total=slot*5+gap*4;
        float sx=(w-total)/2f, sy=h-slot-dp(15);
        String[] names={"ÇİM","TOP","TAŞ","ODN","YAP"};
        int[] cols={Color.rgb(92,155,67),Color.rgb(121,85,58),Color.rgb(125,125,125),Color.rgb(133,94,66),Color.rgb(55,126,58)};
        for(int i=0;i<5;i++){
            slots[i].set(sx+i*(slot+gap),sy,sx+i*(slot+gap)+slot,sy+slot);
            fill.setColor(Color.argb(i==selected?220:135,18,18,18)); c.drawRoundRect(slots[i],dp(8),dp(8),fill);
            stroke.setStrokeWidth(dp(i==selected?3:1.4f));
            stroke.setColor(i==selected?Color.WHITE:Color.argb(135,255,255,255));
            c.drawRoundRect(slots[i],dp(8),dp(8),stroke);
            fill.setColor(cols[i]);
            c.drawRoundRect(new RectF(slots[i].left+dp(8),slots[i].top+dp(7),slots[i].right-dp(8),slots[i].top+slot*0.49f),dp(3),dp(3),fill);
            fill.setColor(Color.WHITE); fill.setTextAlign(Paint.Align.CENTER); fill.setTextSize(Math.max(dp(8),slot*0.17f));
            c.drawText(names[i],slots[i].centerX(),slots[i].bottom-dp(7),fill);
            fill.setTextAlign(Paint.Align.RIGHT); fill.setTextSize(dp(9)); fill.setColor(Color.argb(210,255,255,255));
            c.drawText("∞",slots[i].right-dp(5),slots[i].top+dp(12),fill);
        }

        stroke.setStrokeWidth(dp(2)); stroke.setColor(Color.WHITE);
        float cx=w/2f, cy=h/2f, cr=dp(8);
        c.drawLine(cx-cr,cy,cx-dp(2),cy,stroke); c.drawLine(cx+dp(2),cy,cx+cr,cy,stroke);
        c.drawLine(cx,cy-cr,cx,cy-dp(2),stroke); c.drawLine(cx,cy+dp(2),cx,cy+cr,stroke);

        fill.setTextAlign(Paint.Align.LEFT); fill.setTextSize(dp(12)); fill.setColor(Color.argb(190,255,255,255));
        c.drawText("VoxelCraft v0.3",dp(12),dp(22),fill);
        fill.setTextSize(dp(9)); fill.setColor(Color.argb(150,255,255,255));
        c.drawText("Dünya otomatik kaydedilir",dp(12),dp(36),fill);

        long now=System.currentTimeMillis();
        if(now-started<7500){
            fill.setTextAlign(Paint.Align.CENTER); fill.setTextSize(dp(12)); fill.setColor(Color.argb(215,255,255,255));
            c.drawText("Sol: yürü  •  Sağ: bak  •  Beyaz çerçeve: hedef blok",w/2f,dp(28),fill);
            postInvalidateDelayed(250);
        }

        postInvalidateDelayed(100); // HUD_LOOP\n\n        if(now < game.getStatusUntil()){
            String status=game.getStatusText();
            if(status!=null && !status.isEmpty()){
                fill.setTextAlign(Paint.Align.CENTER); fill.setTextSize(dp(12)); fill.setColor(Color.WHITE);
                float tw=fill.measureText(status)+dp(24);
                RectF badge=new RectF(w/2f-tw/2f,sy-dp(38),w/2f+tw/2f,sy-dp(10));
                Paint.FontMetrics fm=fill.getFontMetrics();
                Paint bg=new Paint(Paint.ANTI_ALIAS_FLAG); bg.setColor(Color.argb(150,10,10,10));
                c.drawRoundRect(badge,dp(12),dp(12),bg);
                c.drawText(status,w/2f,badge.centerY()-(fm.ascent+fm.descent)/2f,fill);
                postInvalidateDelayed(100);
            }
        }
    }

    private void drawButton(Canvas c, RectF r, String text){
        fill.setColor(Color.argb(115,18,18,18)); c.drawRoundRect(r,dp(13),dp(13),fill);
        stroke.setStrokeWidth(dp(1.5f)); stroke.setColor(Color.argb(170,255,255,255)); c.drawRoundRect(r,dp(13),dp(13),stroke);
        fill.setColor(Color.WHITE); fill.setTextAlign(Paint.Align.CENTER); fill.setTextSize(Math.max(dp(11),r.height()*0.24f));
        Paint.FontMetrics fm=fill.getFontMetrics(); float y=r.centerY()-(fm.ascent+fm.descent)/2f; c.drawText(text,r.centerX(),y,fill);
    }

    @Override public boolean onTouchEvent(MotionEvent e){
        int action=e.getActionMasked(), idx=e.getActionIndex(), id=e.getPointerId(idx);
        if(action==MotionEvent.ACTION_DOWN || action==MotionEvent.ACTION_POINTER_DOWN){
            float x=e.getX(idx), y=e.getY(idx);
            if(jumpRect.contains(x,y)){ game.jump(); return true; }
            if(breakRect.contains(x,y)){ game.breakBlock(); return true; }
            if(placeRect.contains(x,y)){ game.placeBlock(); return true; }
            for(int i=0;i<slots.length;i++) if(slots[i].contains(x,y)){ selected=i; game.selectBlock(i); invalidate(); return true; }
            if(x<getWidth()*0.43f && y>getHeight()*0.25f && movePointer<0){
                movePointer=id; moving=true; moveCx=x; moveCy=y; knobX=x; knobY=y; game.setMove(0,0); invalidate(); return true;
            }
            if(lookPointer<0){ lookPointer=id; lastLookX=x; lastLookY=y; return true; }
        }
        if(action==MotionEvent.ACTION_MOVE){
            for(int i=0;i<e.getPointerCount();i++){
                int pid=e.getPointerId(i); float x=e.getX(i),y=e.getY(i);
                if(pid==movePointer){
                    float r=Math.min(getWidth(),getHeight())*0.105f; float dx=x-moveCx,dy=y-moveCy; float len=(float)Math.sqrt(dx*dx+dy*dy);
                    if(len>r){ dx*=r/len; dy*=r/len; }
                    knobX=moveCx+dx; knobY=moveCy+dy; game.setMove(dx/r,-dy/r); invalidate();
                } else if(pid==lookPointer){
                    float dx=x-lastLookX,dy=y-lastLookY; lastLookX=x; lastLookY=y; game.look(dx*0.18f,dy*0.15f);
                }
            }
            return true;
        }
        if(action==MotionEvent.ACTION_UP || action==MotionEvent.ACTION_POINTER_UP || action==MotionEvent.ACTION_CANCEL){
            if(id==movePointer || action==MotionEvent.ACTION_CANCEL){ movePointer=-1; moving=false; game.setMove(0,0); invalidate(); }
            if(id==lookPointer || action==MotionEvent.ACTION_CANCEL) lookPointer=-1;
            return true;
        }
        return true;
    }
}
