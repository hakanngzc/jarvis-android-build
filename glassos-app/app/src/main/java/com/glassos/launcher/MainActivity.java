package com.glassos.launcher;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.role.RoleManager;
import android.content.ComponentName;
import android.content.ClipData;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.graphics.Color;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.text.Editable;
import android.text.TextUtils;
import android.text.TextWatcher;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.DragEvent;
import android.view.WindowInsets;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.EditText;
import android.widget.GridView;
import android.widget.FrameLayout;
import android.widget.SeekBar;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.PopupMenu;
import android.widget.ScrollView;
import android.widget.TextClock;
import android.widget.TextView;
import android.widget.Toast;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public final class MainActivity extends Activity {
    private static final Locale TR = new Locale("tr","TR");
    private static final int NAVY=0xff091224,WHITE=0xffeff7ff,MUTED=0xffa7bad3,BLUE=0xff80c6ff;
    private static final String HOME_KEY="home", DOCK_KEY="dock";
    private final ArrayList<App> apps=new ArrayList<>();
    private final ArrayList<App> visible=new ArrayList<>();
    private SharedPreferences prefs;
    private LinearLayout root;
    private FrameLayout canvasRoot;
    private LiquidArt.Wallpaper wall;
    private int statusInset,navigationInset;
    private boolean drawer=false, settings=false;
    private float downX,downY;
    private static final class App {
        final String name;
        final ComponentName component;
        final Drawable icon;
        App(String n, ComponentName c, Drawable d) {name=n;component=c;icon=d;}
        String key(){return component.flattenToString();}
    }

    private int dp(float v){return (int)(v*getResources().getDisplayMetrics().density+0.5f);}
    private TextView text(String s,float sp,int color,boolean bold){
        TextView t=new TextView(this);
        t.setText(s);
        t.setTextColor(color);
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP,sp);
        t.setGravity(Gravity.CENTER_VERTICAL);
        if(bold)t.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));
        return t;
    }
    private LinearLayout vertical(){ LinearLayout l=new LinearLayout(this);l.setOrientation(1);return l;}
    private LinearLayout horizontal(){ LinearLayout l=new LinearLayout(this);l.setOrientation(0);l.setGravity(Gravity.CENTER_VERTICAL);return l;}
    private GradientDrawable gradient(int radius,boolean accent){
        GradientDrawable d=new GradientDrawable(GradientDrawable.Orientation.TL_BR,
           accent?new int[]{0xffa5d9ff,0xff5e9deb}:new int[]{0xe82b4568,0xe815253e});
        d.setCornerRadius(dp(radius));
        if(!accent)d.setStroke(dp(1),0x6688b9e2);
        return d;
    }
    private void panel(View v,int r){v.setBackground(gradient(r,false));}
    private LinearLayout.LayoutParams margins(int top){
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.topMargin=dp(top);return lp;
    }
    @Override public void onCreate(Bundle s){
        super.onCreate(s);
        prefs=getSharedPreferences("glassos_prefs",MODE_PRIVATE);
        getWindow().setStatusBarColor(Color.TRANSPARENT);
        getWindow().setNavigationBarColor(Color.TRANSPARENT);
        if(Build.VERSION.SDK_INT>=29)getWindow().setNavigationBarContrastEnforced(false);
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE|View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN|
            View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
        refreshApps();
        showHome();
    }
    @Override protected void onResume(){
        super.onResume();
        if(root!=null){refreshApps(); if(drawer)showDrawer();else if(!settings)showHome();}
    }
    private void refreshApps(){
        PackageManager pm=getPackageManager();
        Intent query=new Intent(Intent.ACTION_MAIN);
        query.addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> ris;
        try{ris=pm.queryIntentActivities(query,0);}catch(Exception ex){ris=Collections.emptyList();}
        apps.clear();
        for(ResolveInfo ri:ris){
            if(ri.activityInfo==null || !ri.activityInfo.enabled)continue;
            if(getPackageName().equals(ri.activityInfo.packageName))continue;
            try{
                String name=String.valueOf(ri.loadLabel(pm));
                Drawable icon=ri.loadIcon(pm);
                apps.add(new App(name,new ComponentName(ri.activityInfo.packageName,ri.activityInfo.name),
                   icon==null?pm.getDefaultActivityIcon():icon));
            }catch(Exception ignored){}
        }
        Collections.sort(apps,new Comparator<App>() {
            @Override public int compare(App a,App b){return a.name.toLowerCase(TR).compareTo(b.name.toLowerCase(TR));}
        });
        if(!prefs.getBoolean("seeded",false)&&!apps.isEmpty()){
            ArrayList<String> home=new ArrayList<>(),dock=new ArrayList<>();
            String[] favorites={"dialer|phone|telefon","messag|sms|mesaj","chrome|browser|internet","camera|kamera"};
            for(String group:favorites){
                for(App app:apps){
                    String val=(app.name+" "+app.component.getPackageName()).toLowerCase(TR);
                    boolean found=false;
                    for(String match:group.split("\\|"))if(val.contains(match))found=true;
                    if(found&&!dock.contains(app.key())){dock.add(app.key());break;}
                }
            }
            for(App app:apps)if(dock.size()<4&&!dock.contains(app.key()))dock.add(app.key());
            for(App app:apps)if(home.size()<16&&!dock.contains(app.key()))home.add(app.key());
            prefs.edit().putString(HOME_KEY,TextUtils.join("\n",home))
                .putString(DOCK_KEY,TextUtils.join("\n",dock)).putBoolean("seeded",true).apply();
        }
    }
    private ArrayList<String> keys(String key){
        String value=prefs.getString(key,"");
        if(value==null||value.length()==0)return new ArrayList<>();
        return new ArrayList<>(Arrays.asList(value.split("\n")));
    }
    private List<App> pinned(String key){
        ArrayList<App> result=new ArrayList<>();
        for(String id:keys(key))for(App a:apps)if(a.key().equals(id)){result.add(a);break;}
        return result;
    }
    private void updatePinned(String key,String id,boolean add,int max){
        ArrayList<String> set=keys(key);
        if(add){
            if(set.contains(id)){toast("Bu uygulama zaten ekli");return;}
            if(set.size()>=max){toast("Yer dolu. Önce bir simge kaldır.");return;}
            set.add(id);
        }else set.remove(id);
        prefs.edit().putString(key,TextUtils.join("\n",set)).apply();
        if(drawer)showDrawer();else showHome();
    }
    private void shell(){
        canvasRoot=new FrameLayout(this);
        wall=new LiquidArt.Wallpaper(this);
        canvasRoot.addView(wall,new FrameLayout.LayoutParams(-1,-1));
        root=vertical();
        canvasRoot.addView(root,new FrameLayout.LayoutParams(-1,-1));
        root.setPadding(dp(18),dp(39),dp(18),dp(26));
        root.setOnApplyWindowInsetsListener((v,insets)->{
            if(Build.VERSION.SDK_INT>=30){
                statusInset=insets.getInsets(WindowInsets.Type.statusBars()|WindowInsets.Type.displayCutout()).top;
                navigationInset=insets.getInsets(WindowInsets.Type.navigationBars()).bottom;
            }else{
                statusInset=insets.getSystemWindowInsetTop();
                navigationInset=insets.getSystemWindowInsetBottom();
            }
            int t=Math.max(dp(24),statusInset)+dp(7);
            int b=Math.max(dp(14),navigationInset)+dp(7);
            if(root.getPaddingTop()!=t||root.getPaddingBottom()!=b)
                root.setPadding(dp(18),t,dp(18),b);
            return insets;
        });
        setContentView(canvasRoot);
        canvasRoot.requestApplyInsets();
    }
    private LiquidArt.Glass glass(int radius,boolean strong){return new LiquidArt.Glass(this,radius,strong);}
    private ImageView systemIcon(int drawable){
        ImageView image=new ImageView(this);
        image.setImageResource(drawable);
        image.setColorFilter(LiquidArt.WHITE);
        image.setPadding(dp(12),dp(12),dp(12),dp(12));
        image.setScaleType(ImageView.ScaleType.FIT_CENTER);
        return image;
    }
    private LinearLayout.LayoutParams params(int w,int h){
        return new LinearLayout.LayoutParams(w<0?w:dp(w),h<0?h:dp(h));
    }
    private TextView smallCaps(String v){
        TextView t=text(v,11,LiquidArt.MUTED,true);t.setLetterSpacing(.14f);return t;
    }
    private TextView button(String value,boolean primary){
        TextView t=text(value,14,primary?0xff0a2035:WHITE,true);
        t.setGravity(Gravity.CENTER);t.setMinHeight(dp(50));
        t.setBackground(LiquidArt.capsule(this,primary));
        return t;
    }
    private static final class BatteryCircle extends View{
        private final Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);
        private final int percent;
        BatteryCircle(Context c,int pct){super(c);percent=pct;}
        @Override protected void onDraw(Canvas c){
            float w=getWidth(),h=getHeight();
            float size=Math.min(w,h)-getResources().getDisplayMetrics().density*8;
            float cx=w/2,cy=h/2;
            p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(Math.max(4,size*.095f));
            p.setStrokeCap(Paint.Cap.ROUND);p.setColor(0x367cbcff);
            RectF arc=new RectF(cx-size/2,cy-size/2,cx+size/2,cy+size/2);
            c.drawArc(arc,0,360,false,p);
            p.setColor(0xff9ed9ff);
            c.drawArc(arc,-90,Math.max(0,Math.min(100,percent))*3.6f,false,p);
            p.setStyle(Paint.Style.FILL);p.setColor(Color.WHITE);
            p.setTypeface(Typeface.create("sans-serif-medium",Typeface.BOLD));
            p.setTextSize(size*.27f);
            String val=percent>=0?percent+"%":"—";
            c.drawText(val,cx-p.measureText(val)/2,cy-(p.ascent()+p.descent())/2,p);
        }
    }
    private void showHome(){
        drawer=false;settings=false;shell();
        LinearLayout header=horizontal();
        String day=new SimpleDateFormat("EEEE, d MMMM",TR).format(new Date());
        TextView date=smallCaps(day.toUpperCase(TR));
        header.addView(date,new LinearLayout.LayoutParams(0,dp(38),1));
        ImageView gear=systemIcon(R.drawable.ic_glass_settings);
        gear.setContentDescription("GlassOS ayarları");
        gear.setOnClickListener(v->showSettings());
        header.addView(gear,params(42,42));
        root.addView(header);
        LinearLayout widgets=horizontal();
        LiquidArt.Glass left=glass(28,true);left.setPadding(dp(17),dp(13),dp(12),dp(11));
        LinearLayout clockCol=vertical();
        clockCol.addView(smallCaps("SAAT"));
        TextClock clock=new TextClock(this);
        clock.setFormat12Hour("HH:mm");clock.setFormat24Hour("HH:mm");
        clock.setTextSize(TypedValue.COMPLEX_UNIT_SP,44);
        clock.setTextColor(Color.WHITE);clock.setIncludeFontPadding(false);
        clock.setTypeface(Typeface.create("sans-serif-light",Typeface.NORMAL));
        clockCol.addView(clock,params(-1,63));
        clockCol.addView(text(new SimpleDateFormat("d MMMM",TR).format(new Date()),13,0xffe3eefe,true));
        left.addView(clockCol,new FrameLayout.LayoutParams(-1,-1));
        widgets.addView(left,new LinearLayout.LayoutParams(0,dp(140),1));
        LiquidArt.Glass right=glass(28,true);right.setPadding(dp(12),dp(13),dp(12),dp(10));
        LinearLayout batCol=vertical();batCol.addView(smallCaps("BATARYA"));
        BatteryCircle circle=new BatteryCircle(this,readBatteryPercent());
        LinearLayout.LayoutParams ring=new LinearLayout.LayoutParams(-1,0,1);
        ring.topMargin=dp(1);batCol.addView(circle,ring);
        TextView model=text("vivo Y22s",11,0xffe2eeff,true);
        model.setGravity(Gravity.CENTER);batCol.addView(model);
        right.addView(batCol,new FrameLayout.LayoutParams(-1,-1));
        LinearLayout.LayoutParams rp=new LinearLayout.LayoutParams(0,dp(140),1);
        rp.leftMargin=dp(12);widgets.addView(right,rp);
        root.addView(widgets,margins(13));
        GridView homeGrid=new GridView(this);
        configureGrid(homeGrid);
        homeGrid.setVerticalSpacing(dp(2));
        homeGrid.setAdapter(new AppAdapter(new ArrayList<>(pinned(HOME_KEY)),
            "home",!prefs.getBoolean("hide_labels",false)));
        LinearLayout.LayoutParams gp=new LinearLayout.LayoutParams(-1,0,1);
        gp.topMargin=dp(16);gp.bottomMargin=dp(3);
        root.addView(homeGrid,gp);
        LiquidArt.Glass search=glass(20,false);
        LinearLayout searchContent=horizontal();
        searchContent.setGravity(Gravity.CENTER);
        ImageView lens=new ImageView(this);
        lens.setImageResource(R.drawable.ic_glass_search);
        lens.setColorFilter(LiquidArt.WHITE);
        searchContent.addView(lens,params(15,15));
        TextView st=text("  Ara",12,LiquidArt.WHITE,true);
        searchContent.addView(st);
        search.addView(searchContent,new FrameLayout.LayoutParams(-1,-1));
        search.setContentDescription("Uygulamalarda ara");
        search.setOnClickListener(v->showDrawer());
        LinearLayout.LayoutParams sp=params(102,31);
        sp.gravity=Gravity.CENTER_HORIZONTAL;sp.bottomMargin=dp(10);
        root.addView(search,sp);
        LiquidArt.Glass dock=glass(29,true);dock.setPadding(dp(8),dp(8),dp(8),dp(8));
        LinearLayout icons=horizontal();
        List<App> favorites=pinned(DOCK_KEY);
        for(int i=0;i<4;i++){
            if(i<favorites.size())icons.addView(tile(favorites.get(i),"dock",false),
                new LinearLayout.LayoutParams(0,dp(65),1));
            else{
                TextView add=text("+",29,WHITE,false);
                add.setGravity(Gravity.CENTER);add.setOnClickListener(v->showDrawer());
                icons.addView(add,new LinearLayout.LayoutParams(0,dp(65),1));
            }
        }
        dock.addView(icons,new FrameLayout.LayoutParams(-1,-1));
        root.addView(dock,params(-1,81));
    }
    private int readBatteryPercent(){
        Intent in=registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if(in==null)return -1;
        int level=in.getIntExtra(BatteryManager.EXTRA_LEVEL,-1);
        int scale=in.getIntExtra(BatteryManager.EXTRA_SCALE,100);
        return level<0||scale<=0?-1:level*100/scale;
    }
    private String battery(){
        Intent intent=registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if(intent==null)return "Pil";
        int n=intent.getIntExtra(BatteryManager.EXTRA_LEVEL,-1);
        int d=intent.getIntExtra(BatteryManager.EXTRA_SCALE,100);
        return n<0||d<=0?"Pil":((n*100/d)+"%");
    }
    private void configureGrid(GridView g){
        g.setNumColumns(4);g.setVerticalSpacing(dp(10));
        g.setHorizontalSpacing(dp(4));g.setVerticalScrollBarEnabled(false);
        g.setStretchMode(GridView.STRETCH_COLUMN_WIDTH);
        g.setClipToPadding(false);
    }
    private View tile(App app,String where,boolean labelled){
        LinearLayout box=vertical();
        box.setGravity(Gravity.TOP|Gravity.CENTER_HORIZONTAL);
        box.setPadding(dp(1),dp(3),dp(1),0);
        FrameLayout plate=new FrameLayout(this);
        int size=where.equals("dock")?59:58;
        ImageView pic=new ImageView(this);
        Drawable icon=app.icon;
        if(icon.getConstantState()!=null)icon=icon.getConstantState().newDrawable(getResources()).mutate();
        pic.setImageDrawable(icon);
        pic.setScaleType(ImageView.ScaleType.FIT_CENTER);
        plate.addView(pic,new FrameLayout.LayoutParams(dp(size),dp(size),Gravity.CENTER));
        box.addView(plate,params(size,size));
        if(labelled){
            TextView title=text(app.name,10.5f,LiquidArt.WHITE,false);
            title.setSingleLine(true);title.setEllipsize(TextUtils.TruncateAt.END);
            title.setGravity(Gravity.CENTER);
            title.setShadowLayer(dp(3),0,dp(1),0xd0000000);
            LinearLayout.LayoutParams lp=params(-1,24);lp.topMargin=dp(3);
            box.addView(title,lp);
        }
        box.setContentDescription(app.name+", uygulamayı aç");
        box.setOnClickListener(v->launch(app));
        box.setOnLongClickListener(v->{
            if(where.equals("drawer"))popup(v,app,where);
            else {
                ClipData data=ClipData.newPlainText("GlassOS icon",app.key());
                if(!v.startDragAndDrop(data,new View.DragShadowBuilder(v),null,0))popup(v,app,where);
            }
            return true;
        });
        if(!where.equals("drawer")){
            box.setOnDragListener((v,event)->{
                int a=event.getAction();
                if(a==DragEvent.ACTION_DRAG_STARTED)return true;
                if(a==DragEvent.ACTION_DRAG_ENTERED){
                    v.animate().scaleX(1.08f).scaleY(1.08f).setDuration(90).start();return true;
                }
                if(a==DragEvent.ACTION_DRAG_EXITED||a==DragEvent.ACTION_DRAG_ENDED){
                    v.animate().scaleX(1f).scaleY(1f).setDuration(90).start();return true;
                }
                if(a==DragEvent.ACTION_DROP && event.getClipData()!=null){
                    String key=String.valueOf(event.getClipData().getItemAt(0).coerceToText(this));
                    if(!key.equals(app.key()))moveIcon(key,where,app.key());
                    return true;
                }
                return true;
            });
        }
        return box;
    }
    private void moveIcon(String moving,String dest,String target){
        ArrayList<String> home=keys(HOME_KEY),dock=keys(DOCK_KEY);
        if(!home.contains(moving)&&!dock.contains(moving))return;
        if(dest.equals("home")){
            home.remove(moving);dock.remove(moving);
            int pos=home.indexOf(target);
            home.add(pos<0?home.size():pos,moving);
        }else{
            if(!dock.contains(moving)&&dock.size()>=4){
                int pos=dock.indexOf(target);
                if(pos>=0){
                    String displaced=dock.remove(pos);
                    home.remove(displaced);home.add(displaced);
                }
            }
            home.remove(moving);dock.remove(moving);
            int pos=dock.indexOf(target);
            dock.add(pos<0?dock.size():pos,moving);
        }
        prefs.edit().putString(HOME_KEY,TextUtils.join("\n",home))
            .putString(DOCK_KEY,TextUtils.join("\n",dock)).apply();
        showHome();
    }
    private void launch(App app){
        try{
            Intent intent=new Intent(Intent.ACTION_MAIN);
            intent.addCategory(Intent.CATEGORY_LAUNCHER);
            intent.setComponent(app.component);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
            startActivity(intent);
        }catch(Exception ex){toast("Uygulama açılamadı: "+app.name);refreshApps();}
    }
    private void popup(View v,App a,String where){
        PopupMenu menu=new PopupMenu(this,v);
        menu.getMenu().add(0,1,0,"Ana ekrana ekle");
        menu.getMenu().add(0,2,1,"Ana ekrandan kaldır");
        menu.getMenu().add(0,3,2,"Dock'a ekle");
        menu.getMenu().add(0,4,3,"Dock'tan kaldır");
        menu.getMenu().add(0,5,4,"Uygulama bilgisi");
        menu.setOnMenuItemClickListener(item->{
            switch(item.getItemId()){
                case 1:updatePinned(HOME_KEY,a.key(),true,24);return true;
                case 2:updatePinned(HOME_KEY,a.key(),false,24);return true;
                case 3:updatePinned(DOCK_KEY,a.key(),true,4);return true;
                case 4:updatePinned(DOCK_KEY,a.key(),false,4);return true;
                case 5:
                    try{startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                        Uri.parse("package:"+a.component.getPackageName())));}
                    catch(Exception ex){toast("Uygulama bilgisi açılamadı");}
                    return true;
                default:return false;
            }
        });
        menu.show();
    }
    private void showDrawer(){
        drawer=true;settings=false;shell();
        LinearLayout top=horizontal();
        ImageView back=systemIcon(R.drawable.ic_glass_back);
        back.setContentDescription("Ana ekrana dön");
        back.setOnClickListener(v->showHome());
        top.addView(back,params(42,48));
        TextView heading=text("  Uygulama Kitaplığı",23,WHITE,true);
        top.addView(heading,new LinearLayout.LayoutParams(0,dp(48),1));
        root.addView(top);
        LiquidArt.Glass field=glass(22,true);
        field.setPadding(dp(12),0,dp(12),0);
        EditText search=new EditText(this);
        search.setSingleLine(true);search.setTextColor(WHITE);
        search.setHintTextColor(0xffc5d4ea);
        search.setTextSize(16);search.setHint("Uygulamalarda ara");
        Drawable lensDrawable=getDrawable(R.drawable.ic_glass_search);
        if(lensDrawable!=null){
            lensDrawable=lensDrawable.mutate();
            lensDrawable.setTint(0xffd4e7fc);
            lensDrawable.setBounds(0,0,dp(19),dp(19));
            search.setCompoundDrawables(lensDrawable,null,null,null);
            search.setCompoundDrawablePadding(dp(12));
        }
        search.setBackgroundColor(Color.TRANSPARENT);
        search.setPadding(dp(9),0,dp(8),0);
        field.addView(search,new FrameLayout.LayoutParams(-1,-1));
        LinearLayout.LayoutParams fp=margins(19);
        fp.height=dp(56);fp.bottomMargin=dp(18);
        root.addView(field,fp);
        TextView all=smallCaps("TÜM UYGULAMALAR");
        root.addView(all,params(-1,30));
        GridView grid=new GridView(this);configureGrid(grid);
        grid.setVerticalSpacing(dp(8));
        visible.clear();visible.addAll(apps);
        AppAdapter adapter=new AppAdapter(visible,"drawer",true);
        grid.setAdapter(adapter);
        root.addView(grid,new LinearLayout.LayoutParams(-1,0,1));
        LiquidArt.Glass close=glass(22,false);
        TextView done=text("Ana ekrana dön",14,WHITE,true);
        done.setGravity(Gravity.CENTER);
        close.addView(done,new FrameLayout.LayoutParams(-1,-1));
        close.setOnClickListener(v->showHome());
        root.addView(close,params(-1,49));
        search.addTextChangedListener(new TextWatcher(){
            @Override public void beforeTextChanged(CharSequence s,int start,int count,int after){}
            @Override public void onTextChanged(CharSequence s,int start,int before,int count){
                String q=s.toString().trim().toLowerCase(TR);
                visible.clear();
                for(App app:apps)if(q.isEmpty()||app.name.toLowerCase(TR).contains(q)||
                    app.component.getPackageName().toLowerCase(TR).contains(q))visible.add(app);
                adapter.notifyDataSetChanged();
            }
            @Override public void afterTextChanged(Editable e){}
        });
        root.setFocusableInTouchMode(true);root.requestFocus();
    }
    private final class AppAdapter extends BaseAdapter{
        private final List<App> entries;
        private final String where;
        private final boolean labels;
        AppAdapter(List<App> a,String w,boolean l){entries=a;where=w;labels=l;}
        @Override public int getCount(){return entries.size();}
        @Override public Object getItem(int i){return entries.get(i);}
        @Override public long getItemId(int i){return i;}
        @Override public View getView(int i,View recycled,ViewGroup parent){
            View v=tile(entries.get(i),where,labels);
            v.setLayoutParams(new android.widget.AbsListView.LayoutParams(-1,dp(labels?95:69)));
            return v;
        }
    }
    private void showSettings(){
        settings=true;drawer=false;shell();
        LinearLayout top=horizontal();
        ImageView back=systemIcon(R.drawable.ic_glass_back);
        back.setContentDescription("Geri");back.setOnClickListener(v->showHome());
        top.addView(back,params(42,48));
        top.addView(text("  Görünüm",24,WHITE,true));
        root.addView(top);
        ScrollView scroll=new ScrollView(this);
        scroll.setVerticalScrollBarEnabled(false);
        LinearLayout body=vertical();body.setPadding(0,dp(24),0,dp(15));
        scroll.addView(body);
        body.addView(smallCaps("GLASSOS   •   KOYU CAM"));
        TextView intro=text("vivo Y22s için tasarlandı. Android 14.\nCam saydamlığını ve ana ekranı kendine göre ayarla.",14,LiquidArt.MUTED,false);
        intro.setPadding(0,dp(10),0,0);
        body.addView(intro);
        LiquidArt.Glass transparency=glass(28,true);
        transparency.setPadding(dp(18),dp(16),dp(18),dp(12));
        LinearLayout row=vertical();
        row.addView(text("Cam yoğunluğu",17,WHITE,true));
        row.addView(text("Saydam  —  Buzlu",12,LiquidArt.MUTED,false));
        SeekBar slider=new SeekBar(this);
        slider.setMax(100);slider.setProgress(prefs.getInt("glass",52));
        slider.setProgressTintList(android.content.res.ColorStateList.valueOf(0xff98d5ff));
        slider.setThumbTintList(android.content.res.ColorStateList.valueOf(0xffcbeaff));
        slider.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){
            @Override public void onProgressChanged(SeekBar sb,int progress,boolean user){
                if(user){prefs.edit().putInt("glass",progress).apply();transparency.invalidate();}
            }
            @Override public void onStartTrackingTouch(SeekBar sb){}
            @Override public void onStopTrackingTouch(SeekBar sb){}
        });
        row.addView(slider,params(-1,52));
        transparency.addView(row,new FrameLayout.LayoutParams(-1,-2));
        body.addView(transparency,margins(24));
        LiquidArt.Glass wallpaperPanel=glass(28,true);
        wallpaperPanel.setPadding(dp(16),dp(15),dp(16),dp(17));
        LinearLayout wb=vertical();
        wb.addView(text("Duvar kâğıdı",17,WHITE,true));
        wb.addView(text("Koyu Cam paletleri",12,LiquidArt.MUTED,false));
        LinearLayout options=horizontal();
        String[] names={"Okyanus","Safir","Grafit"};
        for(int i=0;i<3;i++){
            final int which=i;
            TextView choose=text(names[i],11,i==prefs.getInt("wallpaper",0)?0xffb7eaff:WHITE,true);
            choose.setGravity(Gravity.CENTER);
            choose.setBackground(LiquidArt.capsule(this,false));
            LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,dp(46),1);
            if(i>0)lp.leftMargin=dp(6);
            options.addView(choose,lp);
            choose.setOnClickListener(v->{
                prefs.edit().putInt("wallpaper",which).apply();
                LiquidArt.invalidate();
                showSettings();
            });
        }
        wb.addView(options,margins(13));
        wallpaperPanel.addView(wb,new FrameLayout.LayoutParams(-1,-2));
        body.addView(wallpaperPanel,margins(13));
        LiquidArt.Glass labels=glass(24,false);
        labels.setPadding(dp(16),dp(6),dp(16),dp(6));
        TextView l=text(prefs.getBoolean("hide_labels",false)?
          "Simge adları: Gizli   ›":"Simge adları: Görünür   ›",15,WHITE,true);
        labels.addView(l,new FrameLayout.LayoutParams(-1,dp(48)));
        labels.setOnClickListener(v->{
            prefs.edit().putBoolean("hide_labels",!prefs.getBoolean("hide_labels",false)).apply();
            showSettings();
        });
        body.addView(labels,margins(13));
        TextView homeButton=button("Varsayılan başlatıcı yap",true);
        homeButton.setOnClickListener(v->chooseHome());
        body.addView(homeButton,margins(26));
        TextView sys=button("Android başlatıcı ayarları",false);
        sys.setOnClickListener(v->openHomeSettings());
        body.addView(sys,margins(10));
        TextView reset=button("Ana ekran düzenini sıfırla",false);
        reset.setOnClickListener(v->new AlertDialog.Builder(this)
            .setTitle("Ana ekran sıfırlansın mı?")
            .setMessage("Simge sıralaman ve Dock düzenin sıfırlanacak.")
            .setNegativeButton("Vazgeç",null)
            .setPositiveButton("Sıfırla",(d,w)->{
                prefs.edit().remove("seeded").remove(HOME_KEY).remove(DOCK_KEY).apply();
                refreshApps();showHome();
            }).show());
        body.addView(reset,margins(20));
        TextView privacy=text("Reklam, internet izni ve takip yok.\nFuntouch OS ve kilit ekranı değişmez.\n\nGlassOS v0.2 Beta",12,LiquidArt.MUTED,false);
        body.addView(privacy,margins(28));
        root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
    }
    private void chooseHome(){
        if(Build.VERSION.SDK_INT>=29){
            RoleManager rm=(RoleManager)getSystemService(Context.ROLE_SERVICE);
            if(rm!=null&&rm.isRoleAvailable(RoleManager.ROLE_HOME)){
                if(rm.isRoleHeld(RoleManager.ROLE_HOME)){toast("GlassOS zaten varsayılan");return;}
                try{startActivityForResult(rm.createRequestRoleIntent(RoleManager.ROLE_HOME),25);return;}
                catch(Exception ignored){}
            }
        }
        openHomeSettings();
    }
    private void openHomeSettings(){
        try{startActivity(new Intent(Settings.ACTION_HOME_SETTINGS));}
        catch(Exception ex){
            try{startActivity(new Intent(Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS));}
            catch(Exception e){toast("Android ayarları açılamadı");}
        }
    }
    private void toast(String s){Toast.makeText(this,s,Toast.LENGTH_SHORT).show();}
    @Override public void onBackPressed(){
        if(drawer||settings)showHome();
    }
    @Override public boolean dispatchTouchEvent(MotionEvent e){
        if(e.getActionMasked()==MotionEvent.ACTION_DOWN){
            downY=e.getRawY();downX=e.getRawX();
        }else if(e.getActionMasked()==MotionEvent.ACTION_UP){
            float dy=e.getRawY()-downY,dx=e.getRawX()-downX;
            if(!settings&&Math.abs(dy)>dp(115)&&Math.abs(dy)>Math.abs(dx)*1.5f){
                if(dy<0&&!drawer){showDrawer();return true;}
                if(dy>0&&drawer&&downY<dp(270)){showHome();return true;}
            }
        }
        return super.dispatchTouchEvent(e);
    }
}