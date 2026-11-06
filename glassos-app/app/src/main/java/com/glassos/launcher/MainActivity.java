package com.glassos.launcher;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.role.RoleManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.graphics.Color;
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
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.EditText;
import android.widget.GridView;
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
        getWindow().setStatusBarColor(NAVY);
        getWindow().setNavigationBarColor(NAVY);
        if(Build.VERSION.SDK_INT>=29)getWindow().setNavigationBarContrastEnforced(false);
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
            for(App app:apps)if(home.size()<12&&!dock.contains(app.key()))home.add(app.key());
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
        root=vertical();
        root.setPadding(dp(18),dp(12),dp(18),dp(12));
        GradientDrawable bg=new GradientDrawable(GradientDrawable.Orientation.TL_BR,
            new int[]{0xff061020,0xff0a1930,0xff1b2d46,0xff091525});
        root.setBackground(bg);
        setContentView(root);
    }
    private TextView button(String name,boolean bright){
        TextView t=text(name,14,bright?NAVY:WHITE,true);
        t.setGravity(Gravity.CENTER);
        t.setMinHeight(dp(48));
        t.setBackground(gradient(18,bright));
        return t;
    }
    private void showHome(){
        drawer=false; settings=false; shell();
        LinearLayout header=horizontal();
        LinearLayout names=vertical();
        names.addView(text("GlassOS",25,WHITE,true));
        TextView sub=text("VIVO Y22S  •  KOYU CAM",10,MUTED,true);
        sub.setLetterSpacing(.12f);
        names.addView(sub);
        header.addView(names,new LinearLayout.LayoutParams(0,dp(58),1));
        TextView gear=button("⚙",false);
        gear.setTextSize(25);
        gear.setOnClickListener(v->showSettings());
        header.addView(gear,new LinearLayout.LayoutParams(dp(52),dp(52)));
        root.addView(header);
        LinearLayout clockCard=horizontal();
        clockCard.setPadding(dp(18),dp(14),dp(16),dp(12)); panel(clockCard,27);
        LinearLayout left=vertical();
        String date=new SimpleDateFormat("EEEE, d MMMM",TR).format(new Date()).toUpperCase(TR);
        left.addView(text(date,11,0xffcce3fc,true));
        TextClock time=new TextClock(this);
        time.setFormat24Hour("HH:mm");time.setFormat12Hour("HH:mm");
        time.setTextColor(Color.WHITE);
        time.setTextSize(TypedValue.COMPLEX_UNIT_SP,57);
        time.setTypeface(Typeface.create("sans-serif-light",Typeface.NORMAL));
        left.addView(time,new LinearLayout.LayoutParams(-1,dp(76)));
        left.addView(text("Sadece sana özel.",12,MUTED,false));
        clockCard.addView(left,new LinearLayout.LayoutParams(0,-2,1));
        LinearLayout right=vertical();
        right.setGravity(Gravity.TOP|Gravity.RIGHT);
        TextView bat=text("⚡ "+battery(),12,WHITE,true);
        bat.setPadding(dp(9),dp(5),dp(9),dp(5));
        panel(bat,14);right.addView(bat);
        TextView os=text("Android 14",10,MUTED,false);
        os.setPadding(0,dp(13),0,0);right.addView(os);
        clockCard.addView(right);
        root.addView(clockCard,margins(18));
        LinearLayout title=horizontal();
        TextView label=text("ANA EKRAN",12,MUTED,true);
        label.setLetterSpacing(.13f);
        title.addView(label,new LinearLayout.LayoutParams(0,dp(52),1));
        TextView see=text("Tüm uygulamalar  ›",12,WHITE,true);
        see.setOnClickListener(v->showDrawer());
        title.addView(see);root.addView(title,margins(4));
        GridView homeGrid=new GridView(this);
        configureGrid(homeGrid);
        homeGrid.setAdapter(new AppAdapter(new ArrayList<>(pinned(HOME_KEY)),"home",true));
        root.addView(homeGrid,new LinearLayout.LayoutParams(-1,0,1));
        LinearLayout dock=horizontal();
        dock.setPadding(dp(7),dp(5),dp(7),dp(4));panel(dock,24);
        List<App> favorites=pinned(DOCK_KEY);
        for(int i=0;i<4;i++){
            if(i<favorites.size()){
                App a=favorites.get(i);
                View tile=tile(a,"dock",false);
                dock.addView(tile,new LinearLayout.LayoutParams(0,dp(65),1));
            }else{
                TextView add=text("+",25,MUTED,true);add.setGravity(Gravity.CENTER);
                add.setOnClickListener(v->showDrawer());
                dock.addView(add,new LinearLayout.LayoutParams(0,dp(65),1));
            }
        }
        root.addView(dock,new LinearLayout.LayoutParams(-1,dp(76)));
        TextView swipe=text("↑  Yukarı kaydır · Uygulamalar",11,MUTED,false);
        swipe.setGravity(Gravity.CENTER);
        swipe.setOnClickListener(v->showDrawer());
        root.addView(swipe,new LinearLayout.LayoutParams(-1,dp(34)));
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
        LinearLayout box=vertical();box.setGravity(Gravity.TOP|Gravity.CENTER_HORIZONTAL);
        box.setPadding(dp(1),dp(5),dp(1),dp(3));
        LinearLayout backdrop=vertical();
        backdrop.setGravity(Gravity.CENTER);
        panel(backdrop,19);
        ImageView pic=new ImageView(this);
        Drawable icon=app.icon;
        if(icon.getConstantState()!=null)icon=icon.getConstantState().newDrawable(getResources()).mutate();
        pic.setImageDrawable(icon);
        pic.setScaleType(ImageView.ScaleType.FIT_CENTER);
        backdrop.addView(pic,new LinearLayout.LayoutParams(dp(49),dp(49)));
        box.addView(backdrop,new LinearLayout.LayoutParams(dp(61),dp(61)));
        if(labelled){
            TextView t=text(app.name,10.5f,WHITE,true);
            t.setSingleLine(true);t.setEllipsize(TextUtils.TruncateAt.END);
            t.setGravity(Gravity.CENTER);
            box.addView(t,new LinearLayout.LayoutParams(-1,dp(23)));
        }
        box.setContentDescription(app.name);
        box.setOnClickListener(v->launch(app));
        box.setOnLongClickListener(v->{popup(v,app,where);return true;});
        return box;
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
        TextView back=button("‹",false);back.setTextSize(29);
        back.setOnClickListener(v->showHome());
        top.addView(back,new LinearLayout.LayoutParams(dp(48),dp(48)));
        TextView title=text("  Uygulama Kitaplığı",22,WHITE,true);
        top.addView(title,new LinearLayout.LayoutParams(0,dp(56),1));
        root.addView(top);
        EditText search=new EditText(this);
        search.setSingleLine(true);search.setTextColor(WHITE);
        search.setHintTextColor(MUTED);
        search.setTextSize(16);search.setHint("⌕  Uygulama ara");
        search.setPadding(dp(18),0,dp(18),0);panel(search,18);
        LinearLayout.LayoutParams searchParams=new LinearLayout.LayoutParams(-1,dp(54));
        searchParams.topMargin=dp(20);searchParams.bottomMargin=dp(17);
        root.addView(search,searchParams);
        GridView grid=new GridView(this);configureGrid(grid);
        visible.clear();visible.addAll(apps);
        AppAdapter adapter=new AppAdapter(visible,"drawer",true);
        grid.setAdapter(adapter);
        root.addView(grid,new LinearLayout.LayoutParams(-1,0,1));
        TextView foot=button("Ana ekrana dön",false);
        foot.setOnClickListener(v->showHome());
        root.addView(foot,margins(12));
        search.addTextChangedListener(new TextWatcher(){
            @Override public void beforeTextChanged(CharSequence s,int st,int c,int a){}
            @Override public void onTextChanged(CharSequence s,int st,int before,int count){
                String q=s.toString().trim().toLowerCase(TR);
                visible.clear();
                for(App a:apps)if(q.length()==0||a.name.toLowerCase(TR).contains(q)
                   ||a.component.getPackageName().toLowerCase(TR).contains(q))visible.add(a);
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
            v.setLayoutParams(new android.widget.AbsListView.LayoutParams(-1,dp(labels?97:69)));
            return v;
        }
    }
    private void showSettings(){
        settings=true;drawer=false;shell();
        LinearLayout top=horizontal();
        TextView back=button("‹",false);back.setTextSize(28);back.setOnClickListener(v->showHome());
        top.addView(back,new LinearLayout.LayoutParams(dp(48),dp(48)));
        TextView title=text("  GlassOS Ayarları",22,WHITE,true);
        top.addView(title);
        root.addView(top);
        ScrollView scroll=new ScrollView(this);
        LinearLayout content=vertical();content.setPadding(dp(2),dp(28),dp(2),dp(15));
        scroll.addView(content);
        TextView model=text("Koyu Cam · vivo Y22s · Android 14\nAlpha sürüm 0.1.1",14,MUTED,false);
        content.addView(model);
        TextView choose=button("Varsayılan başlatıcı olarak ayarla",true);
        choose.setOnClickListener(v->chooseHome());
        content.addView(choose,margins(28));
        TextView android=button("Android ana ekran ayarları",false);
        android.setOnClickListener(v->openHomeSettings());
        content.addView(android,margins(12));
        TextView reset=button("Ana ekran düzenini sıfırla",false);
        reset.setOnClickListener(v->new AlertDialog.Builder(this)
            .setTitle("Ana ekran sıfırlansın mı?")
            .setNegativeButton("Vazgeç",null)
            .setPositiveButton("Sıfırla",(d,w)->{
                prefs.edit().clear().apply();refreshApps();showHome();
            }).show());
        content.addView(reset,margins(25));
        TextView note=text("Gizlilik: İnternet izni, reklam, takip ve erişilebilirlik servisi yoktur.\n\n" +
            "Bu sürüm canlı bulanıklık veya iOS sistem kontrol merkezi sunmaz. " +
            "Orijinal Funtouch OS yerinde kalır.",13,MUTED,false);
        content.addView(note,margins(30));
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
            if(!settings&&Math.abs(dy)>dp(100)&&Math.abs(dy)>Math.abs(dx)*1.5f){
                if(dy<0&&!drawer){showDrawer();return true;}
                if(dy>0&&drawer){showHome();return true;}
            }
        }
        return super.dispatchTouchEvent(e);
    }
}