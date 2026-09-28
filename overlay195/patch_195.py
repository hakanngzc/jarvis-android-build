from pathlib import Path
import sys,re
base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'
h=java/'HybridActivity.java'
s=h.read_text(encoding='utf-8')

# PHASE 1: theme only. Keep original Activity, original onCreate flow and original setContentView structure.
needle='        LinearLayout root=(LinearLayout)content.getChildAt(0);content.removeView(root);\n'
if needle not in s:
    raise SystemExit('root marker missing')
s=s.replace(needle, needle+
'''        getWindow().setStatusBarColor(0xff020913);
        getWindow().setNavigationBarColor(0xff020913);
        getWindow().getDecorView().setBackgroundColor(0xff020913);
        root.setBackgroundColor(0xff020913);
''',1)

old='        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.addView(root);setContentView(scroll);'
new='        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.setBackgroundColor(0xff020913);scroll.addView(root);setContentView(scroll);'
if old not in s:
    raise SystemExit('scroll marker missing')
s=s.replace(old,new,1)

old='if(s.contains("v1.5.7"))t.setText("JARVIS 1.7.0 · ONE BREATH COMMAND");'
new='if(s.contains("v1.5.7")){t.setText("J A R V I S");t.setTextSize(30);t.setTextColor(0xffe7f7ff);t.setGravity(Gravity.CENTER);if(android.os.Build.VERSION.SDK_INT>=21)t.setLetterSpacing(0.16f);}'
if old not in s:
    raise SystemExit('title marker missing')
s=s.replace(old,new,1)

# PHASE 3: add only the central JARVIS core. No Activity swap and no new DEX layer.
core_code=r'''        int jarvisTitleIndex=0;
        for(int i=0;i<root.getChildCount();i++){
            View v=root.getChildAt(i);
            if(v instanceof TextView && "J A R V I S".equals(((TextView)v).getText().toString())){jarvisTitleIndex=i;break;}
        }
        try{
            java.io.InputStream jarvisCoreStream=getAssets().open("jarvis_core.webp");
            android.graphics.Bitmap jarvisCoreBitmap=android.graphics.BitmapFactory.decodeStream(jarvisCoreStream);
            jarvisCoreStream.close();
            if(jarvisCoreBitmap!=null){
                ImageView jarvisCoreView=new ImageView(this);
                jarvisCoreView.setImageBitmap(jarvisCoreBitmap);
                jarvisCoreView.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
                jarvisCoreView.setAdjustViewBounds(true);
                int jarvisCoreSize=(int)(260*getResources().getDisplayMetrics().density+0.5f);
                LinearLayout.LayoutParams jarvisCoreLp=new LinearLayout.LayoutParams(jarvisCoreSize,jarvisCoreSize);
                jarvisCoreLp.gravity=Gravity.CENTER_HORIZONTAL;
                jarvisCoreLp.topMargin=(int)(10*getResources().getDisplayMetrics().density+0.5f);
                jarvisCoreLp.bottomMargin=(int)(14*getResources().getDisplayMetrics().density+0.5f);
                root.addView(jarvisCoreView,Math.min(jarvisTitleIndex+1,root.getChildCount()),jarvisCoreLp);
            }
        }catch(Exception ignored){}
'''
anchor='        LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);'
if anchor not in s:
    raise SystemExit('phase2 anchor missing')
s=s.replace(anchor,core_code+anchor,1)

# PHASE 3: greeting, ready state, and live command/answer lines.
field='    private TextView voiceStatus,recognitionStatus,heard;\n'
if field not in s:
    raise SystemExit('phase3 field marker missing')
s=s.replace(field,field+'    private TextView jarvisCommandLine,jarvisAnswerLine,jarvisOverlayCommandLine,jarvisOverlayAnswerLine,jarvisDrawerTab,jarvisReadyLine;\n    private LinearLayout jarvisDrawer;\n    private JarvisAtomCoreView jarvisAtomCore;\n    private ImageButton jarvisMicButton;\n    private EditText jarvisWriteInput;\n    private TextView jarvisWriteCommandLine,jarvisWriteAnswerLine,jarvisWriteStatusLine;\n    private AlertDialog jarvisWriteDialog,jarvisSettingsDialog;\n    private android.widget.FrameLayout jarvisEliteLayer,jarvisElitePage,jarvisEliteBody;\n    private TextView jarvisEliteTitle,jarvisEliteSubtitle;\n    private boolean jarvisEliteOpen=false;\n    private boolean jarvisDrawerOpen=false;\n    private View jarvisMenuScrim;\n    private android.os.Handler jarvisHistoryHandler;\n    private Runnable jarvisHistoryRunnable;\n    private String jarvisPendingHistoryCommand="",jarvisPendingHistoryAnswer="",jarvisLastHistoryKey="";\n',1)

phase3_code=r'''        TextView jarvisHello=new TextView(this);
        jarvisHello.setText("Merhaba Hakan");
        jarvisHello.setTextColor(0xfff2f7fb);
        jarvisHello.setTextSize(27);
        jarvisHello.setGravity(Gravity.CENTER);
        if(android.os.Build.VERSION.SDK_INT>=21)jarvisHello.setLetterSpacing(0.08f);
        root.addView(jarvisHello,new LinearLayout.LayoutParams(-1,-2));

        TextView jarvisReady=new TextView(this);
        jarvisReady.setText("Hazırım.");
        jarvisReady.setTextColor(0xff8ebbd7);
        jarvisReady.setTextSize(18);
        jarvisReady.setGravity(Gravity.CENTER);
        if(android.os.Build.VERSION.SDK_INT>=21)jarvisReady.setLetterSpacing(0.08f);
        jarvisReady.setPadding(0,8,0,10);
        root.addView(jarvisReady,new LinearLayout.LayoutParams(-1,-2));

        jarvisCommandLine=new TextView(this);
        jarvisCommandLine.setText("Komut: —");
        jarvisCommandLine.setTextColor(0xffe7f7ff);
        jarvisCommandLine.setTextSize(16);
        jarvisCommandLine.setGravity(Gravity.CENTER);
        jarvisCommandLine.setSingleLine(true);
        jarvisCommandLine.setEllipsize(android.text.TextUtils.TruncateAt.END);
        jarvisCommandLine.setPadding(18,10,18,8);
        root.addView(jarvisCommandLine,new LinearLayout.LayoutParams(-1,-2));

        jarvisAnswerLine=new TextView(this);
        jarvisAnswerLine.setText("Cevap: —");
        jarvisAnswerLine.setTextColor(0xff9bd8ff);
        jarvisAnswerLine.setTextSize(16);
        jarvisAnswerLine.setGravity(Gravity.CENTER);
        jarvisAnswerLine.setSingleLine(true);
        jarvisAnswerLine.setEllipsize(android.text.TextUtils.TruncateAt.END);
        jarvisAnswerLine.setPadding(18,8,18,14);
        root.addView(jarvisAnswerLine,new LinearLayout.LayoutParams(-1,-2));
'''
if anchor not in s:
    raise SystemExit('phase3 row marker missing')
s=s.replace(anchor,phase3_code+anchor,1)


reference_home=r'''    private int jarvisDp(int v){return (int)(v*getResources().getDisplayMetrics().density+0.5f);}
    private android.graphics.drawable.GradientDrawable jarvisBg(int fill,int stroke,int radius){
        android.graphics.drawable.GradientDrawable g=new android.graphics.drawable.GradientDrawable();
        g.setColor(fill);g.setCornerRadius(jarvisDp(radius));
        if(stroke!=0)g.setStroke(jarvisDp(1),stroke);
        return g;
    }
    private TextView jarvisText(String value,float size,int color){
        TextView t=new TextView(this);t.setText(value);t.setTextSize(size);t.setTextColor(color);
        t.setGravity(Gravity.CENTER);t.setIncludeFontPadding(false);return t;
    }
    private TextView jarvisEliteIconButton(String value){
        TextView b=jarvisText(value,26,0xffeaf8ff);
        b.setGravity(Gravity.CENTER);
        b.setBackground(jarvisBg(0xff071521,0xff185f8a,18));
        b.setElevation(jarvisDp(8));
        return b;
    }
    private void jarvisBuildEliteLayer(android.widget.FrameLayout home){
        jarvisEliteLayer=new android.widget.FrameLayout(this);
        jarvisEliteLayer.setVisibility(View.GONE);
        jarvisEliteLayer.setAlpha(0f);
        jarvisEliteLayer.setClickable(true);

        JarvisEliteBackdropView bg=new JarvisEliteBackdropView(this);
        jarvisEliteLayer.addView(bg,new android.widget.FrameLayout.LayoutParams(-1,-1));

        View shade=new View(this);
        shade.setBackgroundColor(0x33000000);
        jarvisEliteLayer.addView(shade,new android.widget.FrameLayout.LayoutParams(-1,-1));

        jarvisElitePage=new android.widget.FrameLayout(this);
        jarvisElitePage.setPadding(jarvisDp(14),jarvisDp(16),jarvisDp(14),jarvisDp(16));
        jarvisElitePage.setBackground(jarvisBg(0xd9030a12,0xff175982,30));
        jarvisElitePage.setElevation(jarvisDp(18));

        android.widget.FrameLayout.LayoutParams pageLp=new android.widget.FrameLayout.LayoutParams(-1,-1);
        pageLp.leftMargin=jarvisDp(10);pageLp.rightMargin=jarvisDp(10);
        pageLp.topMargin=jarvisDp(14);pageLp.bottomMargin=jarvisDp(14);
        jarvisEliteLayer.addView(jarvisElitePage,pageLp);

        LinearLayout column=new LinearLayout(this);
        column.setOrientation(LinearLayout.VERTICAL);
        column.setPadding(jarvisDp(4),jarvisDp(4),jarvisDp(4),jarvisDp(4));
        jarvisElitePage.addView(column,new android.widget.FrameLayout.LayoutParams(-1,-1));

        LinearLayout top=new LinearLayout(this);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);

        TextView back=jarvisEliteIconButton("‹");
        back.setOnClickListener(new View.OnClickListener(){public void onClick(View v){
            jarvisHaptic(v);jarvisCloseElitePage();
        }});
        top.addView(back,new LinearLayout.LayoutParams(jarvisDp(46),jarvisDp(46)));

        LinearLayout titleBox=new LinearLayout(this);
        titleBox.setOrientation(LinearLayout.VERTICAL);
        titleBox.setPadding(jarvisDp(12),0,0,0);
        jarvisEliteTitle=jarvisText("JARVIS",20,0xfff0faff);
        jarvisEliteTitle.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        if(android.os.Build.VERSION.SDK_INT>=21)jarvisEliteTitle.setLetterSpacing(0.05f);
        jarvisEliteSubtitle=jarvisText("",12,0xff6f99b4);
        jarvisEliteSubtitle.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        titleBox.addView(jarvisEliteTitle,new LinearLayout.LayoutParams(-1,jarvisDp(27)));
        titleBox.addView(jarvisEliteSubtitle,new LinearLayout.LayoutParams(-1,jarvisDp(20)));
        top.addView(titleBox,new LinearLayout.LayoutParams(0,jarvisDp(50),1f));

        TextView mark=jarvisText("●",18,0xff4ac7ff);
        mark.setGravity(Gravity.CENTER);
        top.addView(mark,new LinearLayout.LayoutParams(jarvisDp(36),jarvisDp(46)));

        column.addView(top,new LinearLayout.LayoutParams(-1,jarvisDp(54)));

        View topLine=new View(this);topLine.setBackgroundColor(0x553876a1);
        LinearLayout.LayoutParams topLineLp=new LinearLayout.LayoutParams(-1,jarvisDp(1));
        topLineLp.topMargin=jarvisDp(4);topLineLp.bottomMargin=jarvisDp(10);
        column.addView(topLine,topLineLp);

        jarvisEliteBody=new android.widget.FrameLayout(this);
        column.addView(jarvisEliteBody,new LinearLayout.LayoutParams(-1,0,1f));

        TextView footer=jarvisText("JARVIS  •  ELITE INTERFACE  •  1.9.5",10,0xff355c76);
        footer.setGravity(Gravity.CENTER);
        column.addView(footer,new LinearLayout.LayoutParams(-1,jarvisDp(24)));

        home.addView(jarvisEliteLayer,new android.widget.FrameLayout.LayoutParams(-1,-1));
    }
    private void jarvisOpenElitePage(String title,String subtitle,View content){
        if(jarvisEliteLayer==null||jarvisEliteBody==null)return;
        jarvisEliteBody.removeAllViews();
        if(content.getParent()!=null&&content.getParent() instanceof android.view.ViewGroup)
            ((android.view.ViewGroup)content.getParent()).removeView(content);
        jarvisEliteBody.addView(content,new android.widget.FrameLayout.LayoutParams(-1,-1));
        if(jarvisEliteTitle!=null)jarvisEliteTitle.setText(title==null?"JARVIS":title);
        if(jarvisEliteSubtitle!=null)jarvisEliteSubtitle.setText(subtitle==null?"":subtitle);
        jarvisEliteOpen=true;
        jarvisEliteLayer.setVisibility(View.VISIBLE);
        jarvisEliteLayer.setAlpha(0f);
        jarvisElitePage.setTranslationX(jarvisDp(54));
        jarvisElitePage.setScaleX(.985f);jarvisElitePage.setScaleY(.985f);
        jarvisEliteLayer.animate().alpha(1f).setDuration(180).start();
        jarvisElitePage.animate()
            .translationX(0f).scaleX(1f).scaleY(1f)
            .setDuration(300)
            .setInterpolator(new android.view.animation.DecelerateInterpolator())
            .start();
    }
    private void jarvisCloseElitePage(){
        if(!jarvisEliteOpen||jarvisEliteLayer==null)return;
        jarvisEliteOpen=false;
        android.view.inputmethod.InputMethodManager im=(android.view.inputmethod.InputMethodManager)getSystemService(INPUT_METHOD_SERVICE);
        View focus=getCurrentFocus();if(im!=null&&focus!=null)im.hideSoftInputFromWindow(focus.getWindowToken(),0);
        if(jarvisElitePage!=null)jarvisElitePage.animate().translationX(jarvisDp(42)).alpha(.96f).setDuration(180).start();
        jarvisEliteLayer.animate().alpha(0f).setDuration(190).withEndAction(new Runnable(){public void run(){
            if(jarvisEliteLayer!=null){jarvisEliteLayer.setVisibility(View.GONE);jarvisEliteLayer.setAlpha(1f);}
            if(jarvisElitePage!=null){jarvisElitePage.setTranslationX(0f);jarvisElitePage.setAlpha(1f);}
            if(jarvisEliteBody!=null)jarvisEliteBody.removeAllViews();
            jarvisWriteInput=null;jarvisWriteCommandLine=null;jarvisWriteAnswerLine=null;jarvisWriteStatusLine=null;
        }}).start();
    }
    private LinearLayout jarvisEliteSection(String kicker,String title,String description){
        LinearLayout box=new LinearLayout(this);box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(jarvisDp(15),jarvisDp(13),jarvisDp(15),jarvisDp(13));
        box.setBackground(jarvisBg(0xb8061520,0xff164f73,20));
        TextView k=jarvisText(kicker,10,0xff4f9cc9);k.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        if(android.os.Build.VERSION.SDK_INT>=21)k.setLetterSpacing(.09f);
        TextView t=jarvisText(title,17,0xfff1f8fc);t.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        TextView d=jarvisText(description,12,0xff6f94aa);d.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);d.setMaxLines(2);
        box.addView(k,new LinearLayout.LayoutParams(-1,jarvisDp(20)));
        box.addView(t,new LinearLayout.LayoutParams(-1,jarvisDp(28)));
        box.addView(d,new LinearLayout.LayoutParams(-1,-2));
        return box;
    }

    private void jarvisToggleDrawer(){
        if(jarvisDrawer==null)return;
        jarvisDrawerOpen=!jarvisDrawerOpen;
        jarvisDrawer.animate()
            .translationX(jarvisDrawerOpen?0f:jarvisDp(246))
            .alpha(jarvisDrawerOpen?1f:0.96f)
            .setDuration(280)
            .setInterpolator(new android.view.animation.DecelerateInterpolator())
            .start();
        if(jarvisMenuScrim!=null){
            if(jarvisDrawerOpen){
                jarvisMenuScrim.setVisibility(View.VISIBLE);
                jarvisMenuScrim.setAlpha(0f);
                jarvisMenuScrim.animate().alpha(1f).setDuration(220).start();
            }else{
                jarvisMenuScrim.animate().alpha(0f).setDuration(180).withEndAction(new Runnable(){
                    public void run(){if(jarvisMenuScrim!=null)jarvisMenuScrim.setVisibility(View.GONE);}
                }).start();
            }
        }
        if(jarvisDrawerTab!=null){
            jarvisDrawerTab.setText(jarvisDrawerOpen?"›":"‹");
            jarvisDrawerTab.setRotation(0f);
            jarvisDrawerTab.animate().scaleX(.90f).scaleY(.90f).setDuration(90).withEndAction(new Runnable(){public void run(){
                if(jarvisDrawerTab!=null)jarvisDrawerTab.animate().scaleX(1f).scaleY(1f).setDuration(120).start();
            }}).start();
        }
    }
    private String jarvisCleanHistoryText(String value,String prefix){
        if(value==null)return "";
        String v=value.replace("\n"," ").replaceAll("\\s+"," ").trim();
        if(prefix!=null&&v.startsWith(prefix))v=v.substring(prefix.length()).trim();
        return "—".equals(v)?"":v;
    }
    private String jarvisHistoryEncode(String value){
        try{return android.util.Base64.encodeToString(value.getBytes("UTF-8"),android.util.Base64.NO_WRAP);}
        catch(Exception e){return "";}
    }
    private String jarvisHistoryDecode(String value){
        try{return new String(android.util.Base64.decode(value,android.util.Base64.NO_WRAP),"UTF-8");}
        catch(Exception e){return "";}
    }
    private void jarvisCommitHistory(String command,String response){
        String cmd=jarvisCleanHistoryText(command,"Komut:");
        String ans=jarvisCleanHistoryText(response,"Cevap:");
        if(cmd.length()==0||ans.length()==0)return;
        String key=cmd+"\n"+ans;
        if(key.equals(jarvisLastHistoryKey))return;
        android.content.SharedPreferences prefs=getSharedPreferences("jarvis_chat_history",MODE_PRIVATE);
        String old=prefs.getString("items","");
        String record=System.currentTimeMillis()+"|"+jarvisHistoryEncode(cmd)+"|"+jarvisHistoryEncode(ans);
        StringBuilder out=new StringBuilder(record);
        if(old!=null&&old.length()>0){
            String[] rows=old.split("\n");
            int kept=0;
            for(int i=0;i<rows.length&&kept<49;i++){
                String row=rows[i]==null?"":rows[i].trim();
                if(row.length()==0)continue;
                out.append("\n").append(row);kept++;
            }
        }
        prefs.edit().putString("items",out.toString()).apply();
        jarvisLastHistoryKey=key;
    }
    private void jarvisQueueHistory(String command,String response){
        if(!jarvisUiBool("save_chat_history",true))return;
        final String cmd=jarvisCleanHistoryText(command,"Komut:");
        final String ans=jarvisCleanHistoryText(response,"Cevap:");
        if(cmd.length()==0||ans.length()==0)return;
        jarvisPendingHistoryCommand=cmd;jarvisPendingHistoryAnswer=ans;
        if(jarvisHistoryHandler==null)jarvisHistoryHandler=new android.os.Handler(android.os.Looper.getMainLooper());
        if(jarvisHistoryRunnable!=null)jarvisHistoryHandler.removeCallbacks(jarvisHistoryRunnable);
        jarvisHistoryRunnable=new Runnable(){public void run(){
            jarvisCommitHistory(jarvisPendingHistoryCommand,jarvisPendingHistoryAnswer);
        }};
        jarvisHistoryHandler.postDelayed(jarvisHistoryRunnable,850L);
    }
    private void jarvisShowChatHistory(){
        android.content.SharedPreferences prefs=getSharedPreferences("jarvis_chat_history",MODE_PRIVATE);
        String data=prefs.getString("items","");
        LinearLayout shell=new LinearLayout(this);
        shell.setOrientation(LinearLayout.VERTICAL);
        shell.setPadding(jarvisDp(18),jarvisDp(18),jarvisDp(18),jarvisDp(10));
        shell.setBackground(jarvisBg(0xff020a12,0xff16486d,24));

        LinearLayout intro=jarvisEliteSection("HAFIZA","Konuşmalar","Son komutların ve JARVIS yanıtların cihazda saklanır.");
        LinearLayout.LayoutParams introLp=new LinearLayout.LayoutParams(-1,-2);introLp.bottomMargin=jarvisDp(10);shell.addView(intro,introLp);

        String[] records=(data==null||data.trim().length()==0)?new String[0]:data.split("\n");
        TextView count=jarvisText(records.length==0?"Henüz kayıt yok":records.length+" konuşma",13,0xff6f9bbb);
        count.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        shell.addView(count,new LinearLayout.LayoutParams(-1,jarvisDp(28)));

        android.widget.ScrollView scroll=new android.widget.ScrollView(this);
        scroll.setFillViewport(true);
        LinearLayout list=new LinearLayout(this);
        list.setOrientation(LinearLayout.VERTICAL);
        list.setPadding(0,jarvisDp(8),0,jarvisDp(8));
        scroll.addView(list,new android.widget.ScrollView.LayoutParams(-1,-2));

        if(records.length==0){
            TextView empty=jarvisText("JARVIS ile yaptığın konuşmalar burada görünecek.",15,0xff86a8c0);
            empty.setPadding(jarvisDp(12),jarvisDp(40),jarvisDp(12),jarvisDp(40));
            list.addView(empty,new LinearLayout.LayoutParams(-1,-2));
        }else{
            java.text.SimpleDateFormat df=new java.text.SimpleDateFormat("dd.MM.yyyy  •  HH:mm",new java.util.Locale("tr","TR"));
            for(int i=0;i<records.length;i++){
                String row=records[i];
                String[] parts=row.split("\\|",3);
                if(parts.length!=3)continue;
                long when=0L;try{when=Long.parseLong(parts[0]);}catch(Exception ignored){}
                String cmd=jarvisHistoryDecode(parts[1]);
                String ans=jarvisHistoryDecode(parts[2]);
                if(cmd.length()==0&&ans.length()==0)continue;

                LinearLayout card=new LinearLayout(this);
                card.setOrientation(LinearLayout.VERTICAL);
                card.setPadding(jarvisDp(14),jarvisDp(12),jarvisDp(14),jarvisDp(12));
                card.setBackground(jarvisBg(0xff06131f,0xff173f5b,17));

                String whenText=when>0?df.format(new java.util.Date(when)):"";
                TextView you=jarvisText("SEN  •  "+whenText,11,0xff6ea9d0);
                you.setGravity(Gravity.LEFT);card.addView(you,new LinearLayout.LayoutParams(-1,jarvisDp(22)));
                TextView command=jarvisText(cmd,15,0xfff1f8fc);
                command.setGravity(Gravity.LEFT);command.setPadding(0,0,0,jarvisDp(10));
                card.addView(command,new LinearLayout.LayoutParams(-1,-2));

                TextView jlabel=jarvisText("JARVIS",11,0xff37b8ff);
                jlabel.setGravity(Gravity.LEFT);card.addView(jlabel,new LinearLayout.LayoutParams(-1,jarvisDp(22)));
                TextView reply=jarvisText(ans,15,0xffa9d9f5);
                reply.setGravity(Gravity.LEFT);reply.setPadding(0,0,0,jarvisDp(2));
                card.addView(reply,new LinearLayout.LayoutParams(-1,-2));

                LinearLayout.LayoutParams cardLp=new LinearLayout.LayoutParams(-1,-2);
                cardLp.bottomMargin=jarvisDp(10);list.addView(card,cardLp);
            }
        }
        shell.addView(scroll,new LinearLayout.LayoutParams(-1,0,1f));

        TextView clear=jarvisText("GEÇMİŞİ TEMİZLE",12,0xff93bdd5);
        clear.setGravity(Gravity.CENTER);
        clear.setBackground(jarvisBg(0xff071520,0xff1b5e83,15));
        clear.setOnClickListener(new View.OnClickListener(){public void onClick(View v){
            jarvisHaptic(v);
            getSharedPreferences("jarvis_chat_history",MODE_PRIVATE).edit().remove("items").apply();
            jarvisLastHistoryKey="";
            android.widget.Toast.makeText(HybridActivity.this,"Sohbet geçmişi temizlendi",android.widget.Toast.LENGTH_SHORT).show();
            jarvisCloseElitePage();
        }});
        LinearLayout.LayoutParams clearLp=new LinearLayout.LayoutParams(-1,jarvisDp(44));
        clearLp.topMargin=jarvisDp(8);shell.addView(clear,clearLp);
        jarvisOpenElitePage("SOHBET","Kalıcı JARVIS konuşma geçmişi",shell);
    }

    private android.content.SharedPreferences jarvisUiPrefs(){
        return getSharedPreferences("jarvis_ui_settings",MODE_PRIVATE);
    }
    private boolean jarvisUiBool(String key,boolean def){
        return jarvisUiPrefs().getBoolean(key,def);
    }
    private void jarvisHaptic(View v){
        if(v!=null&&jarvisUiBool("haptic",true))
            v.performHapticFeedback(android.view.HapticFeedbackConstants.KEYBOARD_TAP);
    }
    private void jarvisApplyUiPrefs(){
        if(jarvisAtomCore!=null)jarvisAtomCore.setVisibility(jarvisUiBool("atom_animation",true)?View.VISIBLE:View.GONE);
    }
    private LinearLayout jarvisSettingsSwitch(String title,String description,String key,boolean def){
        LinearLayout card=new LinearLayout(this);
        card.setOrientation(LinearLayout.HORIZONTAL);
        card.setGravity(Gravity.CENTER_VERTICAL);
        card.setPadding(jarvisDp(14),jarvisDp(10),jarvisDp(10),jarvisDp(10));
        card.setBackground(jarvisBg(0xff06131f,0xff173f5b,17));

        LinearLayout copy=new LinearLayout(this);
        copy.setOrientation(LinearLayout.VERTICAL);
        TextView t=jarvisText(title,15,0xffeff8fd);t.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        TextView d=jarvisText(description,11,0xff6f96af);d.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);d.setMaxLines(2);
        copy.addView(t,new LinearLayout.LayoutParams(-1,jarvisDp(25)));
        copy.addView(d,new LinearLayout.LayoutParams(-1,-2));
        card.addView(copy,new LinearLayout.LayoutParams(0,-1,1f));

        android.widget.Switch sw=new android.widget.Switch(this);
        sw.setChecked(jarvisUiBool(key,def));
        sw.setOnCheckedChangeListener(new android.widget.CompoundButton.OnCheckedChangeListener(){
            public void onCheckedChanged(android.widget.CompoundButton button,boolean checked){
                jarvisUiPrefs().edit().putBoolean(key,checked).apply();
                jarvisHaptic(button);
                if("atom_animation".equals(key))jarvisApplyUiPrefs();
                if("save_chat_history".equals(key)&&!checked)jarvisLastHistoryKey="";
            }
        });
        card.addView(sw,new LinearLayout.LayoutParams(jarvisDp(58),-1));
        return card;
    }
    private LinearLayout jarvisSettingsInfo(String title,String value,String icon){
        LinearLayout card=new LinearLayout(this);
        card.setOrientation(LinearLayout.HORIZONTAL);
        card.setGravity(Gravity.CENTER_VERTICAL);
        card.setPadding(jarvisDp(12),jarvisDp(9),jarvisDp(12),jarvisDp(9));
        card.setBackground(jarvisBg(0xff06131f,0xff173f5b,17));
        TextView badge=jarvisText(icon,20,0xffbfeeff);
        badge.setBackground(jarvisBg(0xff092437,0xff185f8b,14));
        card.addView(badge,new LinearLayout.LayoutParams(jarvisDp(42),jarvisDp(42)));
        LinearLayout copy=new LinearLayout(this);copy.setOrientation(LinearLayout.VERTICAL);copy.setPadding(jarvisDp(11),0,0,0);
        TextView t=jarvisText(title,14,0xffedf8fd);t.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        TextView v=jarvisText(value,11,0xff6f9ab6);v.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);v.setMaxLines(2);
        copy.addView(t,new LinearLayout.LayoutParams(-1,jarvisDp(23)));
        copy.addView(v,new LinearLayout.LayoutParams(-1,-2));
        card.addView(copy,new LinearLayout.LayoutParams(0,-1,1f));
        return card;
    }
    private TextView jarvisSettingsButton(String label,final int action){
        TextView b=jarvisText(label,13,0xffdff6ff);
        b.setGravity(Gravity.CENTER);
        b.setBackground(jarvisBg(0xff071b29,0xff1a638f,15));
        b.setOnClickListener(new View.OnClickListener(){public void onClick(View v){
            jarvisHaptic(v);
            if(action==1){
                getSharedPreferences("jarvis_chat_history",MODE_PRIVATE).edit().remove("items").apply();
                jarvisLastHistoryKey="";
                android.widget.Toast.makeText(HybridActivity.this,"Sohbet geçmişi temizlendi",android.widget.Toast.LENGTH_SHORT).show();
            }else if(action==2){
                getSharedPreferences("jarvis_write_panel",MODE_PRIVATE).edit().remove("draft").apply();
                android.widget.Toast.makeText(HybridActivity.this,"Yazı taslağı temizlendi",android.widget.Toast.LENGTH_SHORT).show();
            }else if(action==3){
                if(android.os.Build.VERSION.SDK_INT>=23&&checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)!=android.content.pm.PackageManager.PERMISSION_GRANTED){
                    requestPermissions(new String[]{android.Manifest.permission.RECORD_AUDIO},7103);
                }else{
                    android.widget.Toast.makeText(HybridActivity.this,"Mikrofon izni aktif",android.widget.Toast.LENGTH_SHORT).show();
                }
            }
        }});
        return b;
    }
    private void jarvisAddSettingsSection(LinearLayout root,String name){
        TextView s=jarvisText(name,11,0xff5c8ba9);
        s.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        if(android.os.Build.VERSION.SDK_INT>=21)s.setLetterSpacing(0.08f);
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,jarvisDp(30));
        lp.topMargin=jarvisDp(5);root.addView(s,lp);
    }
    private void jarvisAddSettingsCard(LinearLayout root,View card){
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);
        lp.bottomMargin=jarvisDp(8);root.addView(card,lp);
    }
    private void jarvisShowSettingsPanel(){
        LinearLayout content=new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(jarvisDp(18),jarvisDp(18),jarvisDp(18),jarvisDp(16));
        content.setBackground(jarvisBg(0xff020a12,0xff155d8a,26));

        LinearLayout settingsIntro=jarvisEliteSection("CONTROL CENTER","JARVIS Ayarları","Davranış, hafıza, ses ve görünüm tercihlerini yönet.");
        LinearLayout.LayoutParams siLp=new LinearLayout.LayoutParams(-1,-2);siLp.bottomMargin=jarvisDp(10);content.addView(settingsIntro,siLp);

        jarvisAddSettingsSection(content,"ARAYÜZ");
        jarvisAddSettingsCard(content,jarvisSettingsSwitch("Ultra Atom Animasyonu","Elektron, parçacık ve enerji halkalarını göster","atom_animation",true));
        jarvisAddSettingsCard(content,jarvisSettingsSwitch("Dokunsal Geri Bildirim","Menü ve komut butonlarında titreşim","haptic",true));

        jarvisAddSettingsSection(content,"HAFIZA");
        jarvisAddSettingsCard(content,jarvisSettingsSwitch("Sohbet Geçmişini Kaydet","Komut ve JARVIS cevaplarını cihazda sakla","save_chat_history",true));
        jarvisAddSettingsCard(content,jarvisSettingsSwitch("Yazı Taslağını Koru","Yarım kalan yazılı komutu tekrar açınca getir","keep_write_draft",true));

        jarvisAddSettingsSection(content,"SES & WAKE");
        jarvisAddSettingsCard(content,jarvisSettingsInfo("JARVIS Sesi","Türkçe doğal erkek ses sistemi","♪"));
        jarvisAddSettingsCard(content,jarvisSettingsInfo("Wake Word","Hey Jarvis  •  media-safe pasif dinleme","◉"));
        boolean micOk=android.os.Build.VERSION.SDK_INT<23||checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)==android.content.pm.PackageManager.PERMISSION_GRANTED;
        jarvisAddSettingsCard(content,jarvisSettingsInfo("Mikrofon",micOk?"İzin aktif":"İzin gerekli","●"));
        TextView micButton=jarvisSettingsButton(micOk?"MİKROFON İZNİ AKTİF":"MİKROFON İZNİNİ AÇ",3);
        LinearLayout.LayoutParams mbLp=new LinearLayout.LayoutParams(-1,jarvisDp(42));mbLp.bottomMargin=jarvisDp(8);content.addView(micButton,mbLp);

        jarvisAddSettingsSection(content,"VERİ");
        LinearLayout dataRow=new LinearLayout(this);dataRow.setOrientation(LinearLayout.HORIZONTAL);
        TextView clearHistory=jarvisSettingsButton("SOHBETİ TEMİZLE",1);
        TextView clearDraft=jarvisSettingsButton("TASLAĞI TEMİZLE",2);
        LinearLayout.LayoutParams db1=new LinearLayout.LayoutParams(0,jarvisDp(44),1f);db1.rightMargin=jarvisDp(6);
        LinearLayout.LayoutParams db2=new LinearLayout.LayoutParams(0,jarvisDp(44),1f);db2.leftMargin=jarvisDp(6);
        dataRow.addView(clearHistory,db1);dataRow.addView(clearDraft,db2);
        LinearLayout.LayoutParams drLp=new LinearLayout.LayoutParams(-1,jarvisDp(44));drLp.bottomMargin=jarvisDp(8);content.addView(dataRow,drLp);

        jarvisAddSettingsSection(content,"SİSTEM");
        jarvisAddSettingsCard(content,jarvisSettingsInfo("Çalışma Modu","Hibrit  •  çevrimiçi + çevrimdışı","↔"));
        jarvisAddSettingsCard(content,jarvisSettingsInfo("Sürüm","JARVIS 1.9.5  •  build 117","i"));
        jarvisAddSettingsCard(content,jarvisSettingsInfo("Paket","com.hakan.jarvis","□"));

        android.widget.ScrollView scroll=new android.widget.ScrollView(this);
        scroll.setFillViewport(true);
        scroll.addView(content,new android.widget.ScrollView.LayoutParams(-1,-2));

        jarvisOpenElitePage("AYARLAR","JARVIS Control Center",scroll);
    }

    private TextView jarvisQuickCommand(final String command){
        TextView chip=jarvisText(command,12,0xffbfeaff);
        chip.setSingleLine(true);
        chip.setPadding(jarvisDp(10),0,jarvisDp(10),0);
        chip.setBackground(jarvisBg(0xff071b29,0xff185b82,15));
        chip.setOnClickListener(new View.OnClickListener(){public void onClick(View v){
            if(jarvisWriteInput!=null){
                jarvisWriteInput.setText(command);
                jarvisWriteInput.setSelection(command.length());
                jarvisWriteInput.requestFocus();
            }
        }});
        return chip;
    }
    private void jarvisSendTypedCommand(){
        if(jarvisWriteInput==null)return;
        String cmd=jarvisWriteInput.getText()==null?"":jarvisWriteInput.getText().toString().trim();
        if(cmd.length()==0){
            if(jarvisWriteStatusLine!=null)jarvisWriteStatusLine.setText("Bir komut yaz.");
            return;
        }
        if(jarvisWriteCommandLine!=null)jarvisWriteCommandLine.setText("SEN  •  "+cmd);
        if(jarvisWriteAnswerLine!=null)jarvisWriteAnswerLine.setText("JARVIS  •  İşliyorum...");
        if(jarvisWriteStatusLine!=null)jarvisWriteStatusLine.setText("Komut işleniyor");
        if(jarvisReadyLine!=null)jarvisReadyLine.setText("İşliyorum...");
        if(jarvisAtomCore!=null)jarvisAtomCore.setMode(2);
        getSharedPreferences("jarvis_write_panel",MODE_PRIVATE).edit().remove("draft").apply();
        jarvisWriteInput.setText("");
        dispatch(cmd);
    }
    private void jarvisShowWritePanel(){
        LinearLayout shell=new LinearLayout(this);
        shell.setOrientation(LinearLayout.VERTICAL);
        shell.setPadding(jarvisDp(18),jarvisDp(18),jarvisDp(18),jarvisDp(12));
        shell.setBackground(jarvisBg(0xff020a12,0xff155d8a,26));

        jarvisWriteStatusLine=jarvisText("Hazır  •  Mesajını yaz ve gönder",12,0xff70a7c6);
        jarvisWriteStatusLine.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        LinearLayout.LayoutParams statusLp=new LinearLayout.LayoutParams(-1,jarvisDp(28));
        statusLp.bottomMargin=jarvisDp(10);shell.addView(jarvisWriteStatusLine,statusLp);

        LinearLayout writeIntro=jarvisEliteSection("YAZILI KANAL","Komut Konsolu","Sesli komutlarla aynı motoru klavyeden kullan.");
        LinearLayout.LayoutParams wiLp=new LinearLayout.LayoutParams(-1,-2);wiLp.bottomMargin=jarvisDp(12);shell.addView(writeIntro,wiLp);

        LinearLayout liveCard=new LinearLayout(this);
        liveCard.setOrientation(LinearLayout.VERTICAL);
        liveCard.setPadding(jarvisDp(14),jarvisDp(12),jarvisDp(14),jarvisDp(12));
        liveCard.setBackground(jarvisBg(0xff06131f,0xff173f5b,18));

        String currentCmd=jarvisOverlayCommandLine==null?"":jarvisCleanHistoryText(jarvisOverlayCommandLine.getText().toString(),"Komut:");
        String currentAns=jarvisOverlayAnswerLine==null?"":jarvisCleanHistoryText(jarvisOverlayAnswerLine.getText().toString(),"Cevap:");

        jarvisWriteCommandLine=jarvisText(currentCmd.length()==0?"SEN  •  Henüz komut yok":"SEN  •  "+currentCmd,14,0xffeef8fd);
        jarvisWriteCommandLine.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        jarvisWriteCommandLine.setMaxLines(2);
        liveCard.addView(jarvisWriteCommandLine,new LinearLayout.LayoutParams(-1,-2));

        View mini=new View(this);mini.setBackgroundColor(0x333579a2);
        LinearLayout.LayoutParams miniLp=new LinearLayout.LayoutParams(-1,jarvisDp(1));
        miniLp.topMargin=jarvisDp(10);miniLp.bottomMargin=jarvisDp(10);
        liveCard.addView(mini,miniLp);

        jarvisWriteAnswerLine=jarvisText(currentAns.length()==0?"JARVIS  •  Hazırım.":"JARVIS  •  "+currentAns,14,0xff8fd8ff);
        jarvisWriteAnswerLine.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        jarvisWriteAnswerLine.setMaxLines(4);
        liveCard.addView(jarvisWriteAnswerLine,new LinearLayout.LayoutParams(-1,-2));

        LinearLayout.LayoutParams liveLp=new LinearLayout.LayoutParams(-1,-2);
        liveLp.bottomMargin=jarvisDp(14);shell.addView(liveCard,liveLp);

        TextView quickTitle=jarvisText("HIZLI KOMUTLAR",11,0xff608baa);
        quickTitle.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        shell.addView(quickTitle,new LinearLayout.LayoutParams(-1,jarvisDp(24)));

        android.widget.HorizontalScrollView quickScroll=new android.widget.HorizontalScrollView(this);
        quickScroll.setHorizontalScrollBarEnabled(false);
        LinearLayout quickRow=new LinearLayout(this);quickRow.setOrientation(LinearLayout.HORIZONTAL);
        TextView q1=jarvisQuickCommand("Feneri aç");
        TextView q2=jarvisQuickCommand("Spotify'ı aç");
        TextView q3=jarvisQuickCommand("Müziği durdur");
        LinearLayout.LayoutParams qlp=new LinearLayout.LayoutParams(-2,jarvisDp(38));qlp.rightMargin=jarvisDp(8);
        quickRow.addView(q1,qlp);
        LinearLayout.LayoutParams qlp2=new LinearLayout.LayoutParams(-2,jarvisDp(38));qlp2.rightMargin=jarvisDp(8);
        quickRow.addView(q2,qlp2);
        quickRow.addView(q3,new LinearLayout.LayoutParams(-2,jarvisDp(38)));
        quickScroll.addView(quickRow,new android.widget.HorizontalScrollView.LayoutParams(-2,-1));
        LinearLayout.LayoutParams qsLp=new LinearLayout.LayoutParams(-1,jarvisDp(48));qsLp.bottomMargin=jarvisDp(10);
        shell.addView(quickScroll,qsLp);

        jarvisWriteInput=new EditText(this);
        jarvisWriteInput.setTextColor(0xffeffaff);
        jarvisWriteInput.setHintTextColor(0xff56758a);
        jarvisWriteInput.setHint("JARVIS'e bir komut yaz...");
        jarvisWriteInput.setTextSize(16);
        jarvisWriteInput.setSingleLine(false);
        jarvisWriteInput.setMinLines(2);jarvisWriteInput.setMaxLines(4);
        jarvisWriteInput.setGravity(Gravity.TOP|Gravity.LEFT);
        jarvisWriteInput.setPadding(jarvisDp(14),jarvisDp(12),jarvisDp(14),jarvisDp(12));
        jarvisWriteInput.setBackground(jarvisBg(0xff07131d,0xff216891,18));
        String draft=jarvisUiBool("keep_write_draft",true)?getSharedPreferences("jarvis_write_panel",MODE_PRIVATE).getString("draft",""):"";
        if(draft!=null&&draft.length()>0){jarvisWriteInput.setText(draft);jarvisWriteInput.setSelection(draft.length());}
        jarvisWriteInput.addTextChangedListener(new android.text.TextWatcher(){
            public void beforeTextChanged(CharSequence s,int st,int c,int a){}
            public void onTextChanged(CharSequence s,int st,int before,int count){
                String d=s==null?"":s.toString();
                if(jarvisUiBool("keep_write_draft",true))getSharedPreferences("jarvis_write_panel",MODE_PRIVATE).edit().putString("draft",d).apply();
                if(jarvisWriteStatusLine!=null)jarvisWriteStatusLine.setText(d.trim().length()==0?"Hazır  •  Mesajını yaz ve gönder":"Yazılıyor  •  "+d.trim().length()+" karakter");
            }
            public void afterTextChanged(android.text.Editable e){}
        });
        LinearLayout.LayoutParams inputLp=new LinearLayout.LayoutParams(-1,-2);
        inputLp.bottomMargin=jarvisDp(12);shell.addView(jarvisWriteInput,inputLp);

        TextView send=jarvisText("GÖNDER  ➜",15,0xffffffff);
        send.setGravity(Gravity.CENTER);
        send.setBackground(jarvisBg(0xff0a6da8,0xff36bfff,18));
        send.setOnClickListener(new View.OnClickListener(){public void onClick(View v){
            jarvisHaptic(v);
            v.animate().scaleX(.97f).scaleY(.97f).setDuration(70).withEndAction(new Runnable(){public void run(){
                v.animate().scaleX(1f).scaleY(1f).setDuration(100).start();
            }}).start();
            jarvisSendTypedCommand();
        }});
        shell.addView(send,new LinearLayout.LayoutParams(-1,jarvisDp(52)));

        TextView hint=jarvisText("Yazılı komutlar sesli komutlarla aynı JARVIS motorunu kullanır.",11,0xff557a93);
        hint.setGravity(Gravity.CENTER);
        hint.setPadding(0,jarvisDp(10),0,0);
        shell.addView(hint,new LinearLayout.LayoutParams(-1,jarvisDp(34)));

        jarvisOpenElitePage("YAZ","JARVIS yazılı komut konsolu",shell);
        if(jarvisWriteInput!=null){
            jarvisWriteInput.requestFocus();
            jarvisWriteInput.postDelayed(new Runnable(){public void run(){
                android.view.inputmethod.InputMethodManager im=(android.view.inputmethod.InputMethodManager)getSystemService(INPUT_METHOD_SERVICE);
                if(im!=null&&jarvisWriteInput!=null)im.showSoftInput(jarvisWriteInput,android.view.inputmethod.InputMethodManager.SHOW_IMPLICIT);
            }},260L);
        }
    }

    private View jarvisDrawerItem(String icon,String label,String description,final int action){
        LinearLayout card=new LinearLayout(this);
        card.setOrientation(LinearLayout.HORIZONTAL);
        card.setGravity(Gravity.CENTER_VERTICAL);
        card.setPadding(jarvisDp(11),jarvisDp(8),jarvisDp(9),jarvisDp(8));
        card.setBackground(jarvisBg(0xff071521,0xff173f5b,18));

        TextView badge=jarvisText(icon,21,0xffdff7ff);
        badge.setBackground(jarvisBg(0xff0a2639,0xff1b81bd,16));
        card.addView(badge,new LinearLayout.LayoutParams(jarvisDp(42),jarvisDp(42)));

        LinearLayout copy=new LinearLayout(this);
        copy.setOrientation(LinearLayout.VERTICAL);
        copy.setGravity(Gravity.CENTER_VERTICAL);
        copy.setPadding(jarvisDp(10),0,0,0);

        TextView title=jarvisText(label,15,0xfff0f8fd);
        title.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        if(android.os.Build.VERSION.SDK_INT>=21)title.setLetterSpacing(0.03f);
        copy.addView(title,new LinearLayout.LayoutParams(-1,jarvisDp(25)));

        TextView desc=jarvisText(description,11,0xff7299b4);
        desc.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        desc.setMaxLines(2);
        copy.addView(desc,new LinearLayout.LayoutParams(-1,-2));
        card.addView(copy,new LinearLayout.LayoutParams(0,-1,1f));

        TextView arrow=jarvisText("›",23,0xff39aef2);
        card.addView(arrow,new LinearLayout.LayoutParams(jarvisDp(20),-1));

        card.setOnClickListener(new View.OnClickListener(){public void onClick(View v){
            jarvisHaptic(v);
            v.animate().scaleX(0.97f).scaleY(0.97f).setDuration(70).withEndAction(new Runnable(){
                public void run(){v.animate().scaleX(1f).scaleY(1f).setDuration(100).start();}
            }).start();
            if(jarvisDrawerOpen)jarvisToggleDrawer();
            if(action==1)jarvisShowChatHistory();
            else if(action==2)jarvisShowWritePanel();
            else if(action==3)jarvisShowSettingsPanel();
        }});
        return card;
    }

    private void buildJarvisReferenceHome(){
        final android.widget.FrameLayout home=new android.widget.FrameLayout(this);
        home.setBackgroundColor(0xff01070d);

        LinearLayout stack=new LinearLayout(this);
        stack.setOrientation(LinearLayout.VERTICAL);stack.setGravity(Gravity.CENTER_HORIZONTAL);
        stack.setPadding(jarvisDp(24),jarvisDp(24),jarvisDp(24),jarvisDp(20));
        android.widget.FrameLayout.LayoutParams stackLp=new android.widget.FrameLayout.LayoutParams(-1,-1);
        home.addView(stack,stackLp);

        TextView top=jarvisText("J A R V I S",29,0xffeaf8ff);
        if(android.os.Build.VERSION.SDK_INT>=21)top.setLetterSpacing(0.20f);
        LinearLayout.LayoutParams topLp=new LinearLayout.LayoutParams(-1,jarvisDp(44));
        topLp.topMargin=jarvisDp(10);stack.addView(top,topLp);

        TextView sub=jarvisText("Kişisel Yapay Zeka Asistanın",14,0xff7fa4c3);
        if(android.os.Build.VERSION.SDK_INT>=21)sub.setLetterSpacing(0.08f);
        stack.addView(sub,new LinearLayout.LayoutParams(-1,jarvisDp(30)));

        TextView systemChip=jarvisText("●  CORE ONLINE  •  HYBRID READY",10,0xff74cfff);
        systemChip.setPadding(jarvisDp(10),0,jarvisDp(10),0);
        systemChip.setBackground(jarvisBg(0x6610293b,0xff165a82,14));
        LinearLayout.LayoutParams sysLp=new LinearLayout.LayoutParams(-2,jarvisDp(28));
        sysLp.topMargin=jarvisDp(2);sysLp.bottomMargin=jarvisDp(6);stack.addView(systemChip,sysLp);

        View line=new View(this);line.setBackgroundColor(0xff168fff);
        LinearLayout.LayoutParams lineLp=new LinearLayout.LayoutParams(jarvisDp(70),jarvisDp(2));
        lineLp.topMargin=jarvisDp(4);lineLp.bottomMargin=jarvisDp(18);stack.addView(line,lineLp);

        android.widget.FrameLayout atomStage=new android.widget.FrameLayout(this);
        atomStage.setClipChildren(false);atomStage.setClipToPadding(false);
        jarvisAtomCore=new JarvisAtomCoreView(this);
        atomStage.addView(jarvisAtomCore,new android.widget.FrameLayout.LayoutParams(-1,-1,Gravity.CENTER));
        jarvisApplyUiPrefs();
        LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(jarvisDp(292),jarvisDp(292));
        cp.bottomMargin=jarvisDp(6);stack.addView(atomStage,cp);

        TextView hello=jarvisText("Merhaba Hakan",26,0xfff2f7fb);
        if(android.os.Build.VERSION.SDK_INT>=21)hello.setLetterSpacing(0.08f);
        stack.addView(hello,new LinearLayout.LayoutParams(-1,jarvisDp(44)));

        jarvisReadyLine=jarvisText("Hazırım.",17,0xff7596b2);
        if(android.os.Build.VERSION.SDK_INT>=21)jarvisReadyLine.setLetterSpacing(0.08f);
        stack.addView(jarvisReadyLine,new LinearLayout.LayoutParams(-1,jarvisDp(34)));

        LinearLayout liveStrip=new LinearLayout(this);
        liveStrip.setOrientation(LinearLayout.VERTICAL);
        liveStrip.setPadding(jarvisDp(14),jarvisDp(9),jarvisDp(14),jarvisDp(9));
        liveStrip.setBackground(jarvisBg(0x8f06131f,0xff164f73,18));
        jarvisOverlayCommandLine=jarvisText("Komut: —",13,0xffdceef9);
        jarvisOverlayCommandLine.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        jarvisOverlayCommandLine.setSingleLine(true);jarvisOverlayCommandLine.setEllipsize(android.text.TextUtils.TruncateAt.END);
        liveStrip.addView(jarvisOverlayCommandLine,new LinearLayout.LayoutParams(-1,jarvisDp(24)));
        jarvisOverlayAnswerLine=jarvisText("Cevap: —",13,0xff7fcfff);
        jarvisOverlayAnswerLine.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        jarvisOverlayAnswerLine.setSingleLine(true);jarvisOverlayAnswerLine.setEllipsize(android.text.TextUtils.TruncateAt.END);
        liveStrip.addView(jarvisOverlayAnswerLine,new LinearLayout.LayoutParams(-1,jarvisDp(24)));
        LinearLayout.LayoutParams liveStripLp=new LinearLayout.LayoutParams(-1,jarvisDp(70));
        liveStripLp.leftMargin=jarvisDp(10);liveStripLp.rightMargin=jarvisDp(10);liveStripLp.topMargin=jarvisDp(6);
        stack.addView(liveStrip,liveStripLp);

        View spacer=new View(this);stack.addView(spacer,new LinearLayout.LayoutParams(1,0,1f));

        android.widget.FrameLayout micGlow=new android.widget.FrameLayout(this);
        micGlow.setBackground(jarvisBg(0x221a9fff,0xff177fd0,70));
        LinearLayout.LayoutParams glowLp=new LinearLayout.LayoutParams(jarvisDp(108),jarvisDp(108));
        glowLp.bottomMargin=jarvisDp(22);stack.addView(micGlow,glowLp);

        jarvisMicButton=new ImageButton(this);jarvisMicButton.setImageResource(android.R.drawable.ic_btn_speak_now);
        jarvisMicButton.setColorFilter(0xffeefaff);jarvisMicButton.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
        jarvisMicButton.setPadding(jarvisDp(21),jarvisDp(21),jarvisDp(21),jarvisDp(21));
        jarvisMicButton.setBackground(jarvisBg(0xff06131f,0xff35a9ff,60));
        jarvisMicButton.setContentDescription("JARVIS mikrofon");
        jarvisMicButton.setOnClickListener(new View.OnClickListener(){public void onClick(View v){
            jarvisHaptic(v);
            v.animate().scaleX(0.88f).scaleY(0.88f).setDuration(90).withEndAction(new Runnable(){public void run(){
                if(jarvisMicButton!=null)jarvisMicButton.animate().scaleX(1f).scaleY(1f).setDuration(140).start();
            }}).start();
            if(jarvisReadyLine!=null)jarvisReadyLine.setText("Dinliyorum...");
            if(jarvisAtomCore!=null)jarvisAtomCore.setMode(1);
            beginListening();
        }});
        android.widget.FrameLayout.LayoutParams micLp=new android.widget.FrameLayout.LayoutParams(jarvisDp(84),jarvisDp(84),Gravity.CENTER);
        micGlow.addView(jarvisMicButton,micLp);

        jarvisMenuScrim=new View(this);
        jarvisMenuScrim.setBackgroundColor(0x88000000);
        jarvisMenuScrim.setVisibility(View.GONE);
        jarvisMenuScrim.setOnClickListener(new View.OnClickListener(){public void onClick(View v){
            if(jarvisDrawerOpen)jarvisToggleDrawer();
        }});
        home.addView(jarvisMenuScrim,new android.widget.FrameLayout.LayoutParams(-1,-1));

        jarvisDrawer=new LinearLayout(this);
        jarvisDrawer.setOrientation(LinearLayout.VERTICAL);
        jarvisDrawer.setPadding(jarvisDp(14),jarvisDp(16),jarvisDp(14),jarvisDp(12));
        jarvisDrawer.setBackground(jarvisBg(0xfa020a12,0xff1b73a8,30));
        jarvisDrawer.setElevation(jarvisDp(18));

        LinearLayout header=new LinearLayout(this);
        header.setOrientation(LinearLayout.VERTICAL);
        header.setPadding(jarvisDp(2),0,jarvisDp(2),jarvisDp(10));

        TextView panelTitle=jarvisText("J A R V I S  P A N E L",16,0xffecf9ff);
        panelTitle.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        if(android.os.Build.VERSION.SDK_INT>=21)panelTitle.setLetterSpacing(0.08f);
        header.addView(panelTitle,new LinearLayout.LayoutParams(-1,jarvisDp(32)));

        TextView panelSub=jarvisText("Kişisel komut merkezi",11,0xff6e9ab8);
        panelSub.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        header.addView(panelSub,new LinearLayout.LayoutParams(-1,jarvisDp(22)));

        TextView statusChip=jarvisText("●  JARVIS hazır",11,0xff8ad9ff);
        statusChip.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        statusChip.setPadding(jarvisDp(10),0,jarvisDp(10),0);
        statusChip.setBackground(jarvisBg(0xff062133,0xff155a84,14));
        LinearLayout.LayoutParams chipLp=new LinearLayout.LayoutParams(-2,jarvisDp(30));
        chipLp.topMargin=jarvisDp(7);chipLp.bottomMargin=jarvisDp(10);
        header.addView(statusChip,chipLp);
        jarvisDrawer.addView(header,new LinearLayout.LayoutParams(-1,-2));

        View headerLine=new View(this);headerLine.setBackgroundColor(0x553579a2);
        LinearLayout.LayoutParams hlp=new LinearLayout.LayoutParams(-1,jarvisDp(1));
        hlp.bottomMargin=jarvisDp(14);jarvisDrawer.addView(headerLine,hlp);

        View chat=jarvisDrawerItem("◌","Sohbet Geçmişi","Önceki komut ve cevaplarını görüntüle",1);
        View write=jarvisDrawerItem("✎","Yaz","JARVIS'e klavyeden komut gönder",2);
        View settings=jarvisDrawerItem("⚙","Ayarlar","Ses, wake word ve uygulama tercihleri",3);

        LinearLayout.LayoutParams menuCardLp=new LinearLayout.LayoutParams(-1,jarvisDp(70));
        menuCardLp.bottomMargin=jarvisDp(10);
        jarvisDrawer.addView(chat,menuCardLp);
        LinearLayout.LayoutParams menuCardLp2=new LinearLayout.LayoutParams(-1,jarvisDp(70));
        menuCardLp2.bottomMargin=jarvisDp(10);
        jarvisDrawer.addView(write,menuCardLp2);
        jarvisDrawer.addView(settings,new LinearLayout.LayoutParams(-1,jarvisDp(70)));

        View menuSpacer=new View(this);
        jarvisDrawer.addView(menuSpacer,new LinearLayout.LayoutParams(1,0,1f));

        TextView footer=jarvisText("JARVIS 1.9.5  •  UI PHASE 8B",11,0xff496f89);
        footer.setGravity(Gravity.CENTER);
        jarvisDrawer.addView(footer,new LinearLayout.LayoutParams(-1,jarvisDp(30)));

        android.widget.FrameLayout.LayoutParams drawerLp=new android.widget.FrameLayout.LayoutParams(jarvisDp(238),jarvisDp(430),Gravity.RIGHT|Gravity.CENTER_VERTICAL);
        drawerLp.rightMargin=jarvisDp(4);
        home.addView(jarvisDrawer,drawerLp);
        jarvisDrawer.setTranslationX(jarvisDp(246));
        jarvisDrawer.setAlpha(0.96f);

        jarvisDrawerTab=jarvisText("‹",24,0xffeffaff);
        jarvisDrawerTab.setBackground(jarvisBg(0xf206131f,0xff1a91e8,14));
        jarvisDrawerTab.setElevation(jarvisDp(12));
        jarvisDrawerTab.setOnClickListener(new View.OnClickListener(){public void onClick(View v){jarvisToggleDrawer();}});
        android.widget.FrameLayout.LayoutParams tabLp=new android.widget.FrameLayout.LayoutParams(jarvisDp(28),jarvisDp(66),Gravity.RIGHT|Gravity.CENTER_VERTICAL);
        tabLp.rightMargin=0;
        home.addView(jarvisDrawerTab,tabLp);
        jarvisBuildEliteLayer(home);

        String a=answer==null?"":answer.getText().toString().replace("\n"," ").replaceAll("\\s+"," ").trim();
        if(a.length()>0)jarvisOverlayAnswerLine.setText("Cevap: "+a);
        addContentView(home,new android.view.ViewGroup.LayoutParams(-1,-1));
    }

'''
set_old='    private void setText(int id,String text){View v=findViewById(id);if(v instanceof TextView)((TextView)v).setText(text);}'
if set_old not in s:
    raise SystemExit('reference home insertion marker missing')
s=s.replace(set_old,reference_home+set_old,1)


set_new='    private void setText(int id,String text){View v=findViewById(id);if(v instanceof TextView)((TextView)v).setText(text);if(id==2001){String q=(text==null||text.trim().length()==0?"—":text.replace("\\n"," ").trim());if(jarvisCommandLine!=null)jarvisCommandLine.setText("Komut: "+q);if(jarvisOverlayCommandLine!=null)jarvisOverlayCommandLine.setText("Komut: "+q);if(jarvisReadyLine!=null)jarvisReadyLine.setText("İşliyorum...");if(jarvisAtomCore!=null)jarvisAtomCore.setMode(2);}}'
if set_old not in s:
    raise SystemExit('phase3 setText marker missing')
s=s.replace(set_old,set_new,1)

state_marker='        if(state!=null){answer.setText(state.getString("hybrid_answer",answer.getText().toString()));meta.setText(state.getString("hybrid_meta",""));String k=state.getString("last_kind");if(k!=null){last=new HybridEngine.Request(k,state.getString("last_query",""));retry.setVisibility(View.VISIBLE);}}'
watcher=r'''        if(answer!=null&&jarvisAnswerLine!=null){
            answer.addTextChangedListener(new android.text.TextWatcher(){
                public void beforeTextChanged(CharSequence s,int st,int c,int a){}
                public void onTextChanged(CharSequence s,int st,int before,int count){
                    if(jarvisAnswerLine==null)return;
                    String v=s==null?"":s.toString().replace("\n"," ").replaceAll("\\s+"," ").trim();
                    jarvisAnswerLine.setText("Cevap: "+(v.length()==0?"—":v));
                    if(jarvisOverlayAnswerLine!=null)jarvisOverlayAnswerLine.setText("Cevap: "+(v.length()==0?"—":v));
                    if(jarvisWriteAnswerLine!=null)jarvisWriteAnswerLine.setText("JARVIS  •  "+(v.length()==0?"—":v));
                    if(jarvisWriteStatusLine!=null)jarvisWriteStatusLine.setText(v.length()==0?"Hazır":"Yanıt alındı");
                    jarvisQueueHistory(jarvisOverlayCommandLine==null?"":jarvisOverlayCommandLine.getText().toString(),v);
                    if(jarvisReadyLine!=null)jarvisReadyLine.setText("Yanıtlıyorum...");
                    if(jarvisAtomCore!=null){
                        jarvisAtomCore.setMode(2);
                        jarvisAtomCore.postDelayed(new Runnable(){public void run(){
                            if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
                            if(jarvisReadyLine!=null)jarvisReadyLine.setText("Hazırım.");
                        }},1800L);
                    }
                }
                public void afterTextChanged(android.text.Editable e){}
            });
        }
'''
if state_marker not in s:
    raise SystemExit('phase3 state marker missing')
s=s.replace(state_marker,watcher+state_marker+'\n        buildJarvisReferenceHome();',1)

dispatch_marker='    private void dispatch(String raw){'
if dispatch_marker in s:
    s=s.replace(dispatch_marker,dispatch_marker+'if(jarvisOverlayCommandLine!=null){String q=raw==null?"—":raw.replace("\\n"," ").trim();jarvisOverlayCommandLine.setText("Komut: "+(q.length()==0?"—":q));if(jarvisWriteCommandLine!=null)jarvisWriteCommandLine.setText("SEN  •  "+(q.length()==0?"—":q));if(jarvisWriteStatusLine!=null)jarvisWriteStatusLine.setText("Komut işleniyor");}',1)

# Persist the themed HybridActivity source before compiling/cloning it.
h.write_text(s,encoding='utf-8')

# Preserve the phone-confirmed 1.7.6 media-safe wake behavior exactly at source level.
o=java/'OpenWakeWordDetector.java';x=o.read_text(encoding='utf-8')
old='try{if(melSession==null)initModels();initBuffers();if(!initAudioRecord())throw new IllegalStateException("Mikrofon açılamadı");audioLoop();}'
new='try{if(!initAudioRecord())throw new IllegalStateException("Mikrofon açılamadı");if(melSession==null)initModels();initBuffers();audioLoop();}'
if old not in x: raise SystemExit('wake start marker missing')
x=x.replace(old,new,1)
old='registerRecordingDiagnostics(candidate);return true;'
new='candidate.startRecording();return true;'
if old not in x: raise SystemExit('audio start marker missing')
x=x.replace(old,new,1)
old='private void audioLoop(){AudioRecord r=audioRecord;if(r==null)return;r.startRecording();JarvisForensics.event(context,"A","startRecording state="+r.getRecordingState()+" source="+activeSource);'
new='private void audioLoop(){AudioRecord r=audioRecord;if(r==null)return;JarvisForensics.event(context,"A","startRecording state="+r.getRecordingState()+" source="+activeSource);'
if old not in x: raise SystemExit('audioLoop marker missing')
x=x.replace(old,new,1)
x=x.replace('if(score>=0.48f){','if(score>=0.42f){',1)
o.write_text(x,encoding='utf-8')

w=java/'WakeWordService.java';x=w.read_text(encoding='utf-8')
old='new OpenWakeWordDetector(this,0.30f,0.48f,3800L)'
new='new OpenWakeWordDetector(this,0.15f,0.42f,3800L)'
if old not in x: raise SystemExit('wake threshold marker missing')
x=x.replace(old,new,1)
w.write_text(x,encoding='utf-8')

# Version and launcher icon only. Launcher Activity remains HybridActivity.
m=base/'app/src/main/AndroidManifest.xml';x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"','android:versionCode="117" android:versionName="1.9.5"',x,count=1)
if 'android:icon="@drawable/jarvis_icon"' not in x:
    x=x.replace('<application android:label="JARVIS"','<application android:label="JARVIS" android:icon="@drawable/jarvis_icon" android:roundIcon="@drawable/jarvis_icon"',1)
if 'com.hakan.jarvis.DesignActivity' in x:
    raise SystemExit('unsafe DesignActivity found')
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle';g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 117',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '1.9.5'",g,count=1)
b.write_text(g,encoding='utf-8')


# Safe visible UI clone. The legacy HybridActivity remains in the baseline DEX, while this unique class carries the same engine plus the new UI.
home=java/'JarvisHomeActivity.java'
home_src=h.read_text(encoding='utf-8')
home_src=home_src.replace('HybridActivity','JarvisHomeActivity')
home.write_text(home_src,encoding='utf-8')

# Route every wake/direct handoff to the visible cloned home activity.
ws=java/'WakeWordService.java'
wx=ws.read_text(encoding='utf-8').replace('new Intent(this,HybridActivity.class)','new Intent(this,JarvisHomeActivity.class)')
ws.write_text(wx,encoding='utf-8')

# Launcher points at JarvisHomeActivity. The old HybridActivity bytecode remains untouched as a fallback engine class.
m=base/'app/src/main/AndroidManifest.xml'
mx=m.read_text(encoding='utf-8')
mx=mx.replace('android:name="com.hakan.jarvis.HybridActivity"','android:name="com.hakan.jarvis.JarvisHomeActivity"',1)
m.write_text(mx,encoding='utf-8')

print('JARVIS 1.9.5 UI PHASE 8B cloned home applied')


# build-trigger-187

# build-trigger-188

# build-trigger-190

# build-trigger-191

# build-trigger-192

# build-trigger-193
