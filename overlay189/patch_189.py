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
s=s.replace(field,field+'    private TextView jarvisCommandLine,jarvisAnswerLine,jarvisOverlayCommandLine,jarvisOverlayAnswerLine,jarvisDrawerTab,jarvisReadyLine;\n    private LinearLayout jarvisDrawer;\n    private JarvisAtomCoreView jarvisAtomCore;\n    private ImageButton jarvisMicButton;\n    private boolean jarvisDrawerOpen=false;\n    private android.os.Handler jarvisHistoryHandler;\n    private Runnable jarvisHistoryRunnable;\n    private String jarvisPendingHistoryCommand="",jarvisPendingHistoryAnswer="",jarvisLastHistoryKey="";\n',1)

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
    private void jarvisToggleDrawer(){
        if(jarvisDrawer==null)return;
        jarvisDrawerOpen=!jarvisDrawerOpen;
        jarvisDrawer.animate().translationX(jarvisDrawerOpen?0f:jarvisDp(104)).setDuration(220).start();
        if(jarvisDrawerTab!=null)jarvisDrawerTab.setText(jarvisDrawerOpen?"›":"‹");
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

        TextView title=jarvisText("Sohbet Geçmişi",23,0xffeffaff);
        title.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        shell.addView(title,new LinearLayout.LayoutParams(-1,jarvisDp(42)));

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
        shell.addView(scroll,new LinearLayout.LayoutParams(-1,jarvisDp(470)));

        final AlertDialog dialog=new AlertDialog.Builder(this)
            .setView(shell)
            .setNegativeButton("Geçmişi Temizle",new android.content.DialogInterface.OnClickListener(){
                public void onClick(android.content.DialogInterface d,int which){
                    getSharedPreferences("jarvis_chat_history",MODE_PRIVATE).edit().remove("items").apply();
                    jarvisLastHistoryKey="";
                }
            })
            .setPositiveButton("Kapat",null)
            .create();
        dialog.setOnShowListener(new android.content.DialogInterface.OnShowListener(){
            public void onShow(android.content.DialogInterface d){
                if(dialog.getButton(AlertDialog.BUTTON_POSITIVE)!=null)dialog.getButton(AlertDialog.BUTTON_POSITIVE).setTextColor(0xff42b9ff);
                if(dialog.getButton(AlertDialog.BUTTON_NEGATIVE)!=null)dialog.getButton(AlertDialog.BUTTON_NEGATIVE).setTextColor(0xff7fa7c2);
            }
        });
        dialog.show();
    }

    private TextView jarvisDrawerItem(String icon,String label,final int action){
        TextView t=jarvisText(icon+"\n"+label,16,0xffdff5ff);
        t.setGravity(Gravity.CENTER);t.setPadding(jarvisDp(8),jarvisDp(14),jarvisDp(8),jarvisDp(14));
        t.setOnClickListener(new View.OnClickListener(){public void onClick(View v){
            if(jarvisDrawerOpen)jarvisToggleDrawer();
            if(action==1)jarvisShowChatHistory();
            else if(action==2)showInput();else if(action==3)showSettings();
        }});
        return t;
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

        View line=new View(this);line.setBackgroundColor(0xff168fff);
        LinearLayout.LayoutParams lineLp=new LinearLayout.LayoutParams(jarvisDp(70),jarvisDp(2));
        lineLp.topMargin=jarvisDp(4);lineLp.bottomMargin=jarvisDp(18);stack.addView(line,lineLp);

        android.widget.FrameLayout atomStage=new android.widget.FrameLayout(this);
        atomStage.setClipChildren(false);atomStage.setClipToPadding(false);
        try{
            java.io.InputStream in=getAssets().open("jarvis_core.webp");
            android.graphics.Bitmap bmp=android.graphics.BitmapFactory.decodeStream(in);in.close();
            if(bmp!=null){
                ImageView core=new ImageView(this);core.setImageBitmap(bmp);core.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
                atomStage.addView(core,new android.widget.FrameLayout.LayoutParams(-1,-1,Gravity.CENTER));
            }
        }catch(Exception ignored){}
        jarvisAtomCore=new JarvisAtomCoreView(this);
        atomStage.addView(jarvisAtomCore,new android.widget.FrameLayout.LayoutParams(-1,-1,Gravity.CENTER));
        LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(jarvisDp(310),jarvisDp(310));
        cp.bottomMargin=jarvisDp(6);stack.addView(atomStage,cp);

        TextView hello=jarvisText("Merhaba Hakan",26,0xfff2f7fb);
        if(android.os.Build.VERSION.SDK_INT>=21)hello.setLetterSpacing(0.08f);
        stack.addView(hello,new LinearLayout.LayoutParams(-1,jarvisDp(44)));

        jarvisReadyLine=jarvisText("Hazırım.",17,0xff7596b2);
        if(android.os.Build.VERSION.SDK_INT>=21)jarvisReadyLine.setLetterSpacing(0.08f);
        stack.addView(jarvisReadyLine,new LinearLayout.LayoutParams(-1,jarvisDp(34)));

        jarvisOverlayCommandLine=jarvisText("Komut: —",14,0xffdceef9);
        jarvisOverlayCommandLine.setSingleLine(true);jarvisOverlayCommandLine.setEllipsize(android.text.TextUtils.TruncateAt.END);
        stack.addView(jarvisOverlayCommandLine,new LinearLayout.LayoutParams(-1,jarvisDp(28)));

        jarvisOverlayAnswerLine=jarvisText("Cevap: —",14,0xff77bff0);
        jarvisOverlayAnswerLine.setSingleLine(true);jarvisOverlayAnswerLine.setEllipsize(android.text.TextUtils.TruncateAt.END);
        stack.addView(jarvisOverlayAnswerLine,new LinearLayout.LayoutParams(-1,jarvisDp(28)));

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
            v.performHapticFeedback(android.view.HapticFeedbackConstants.KEYBOARD_TAP);
            v.animate().scaleX(0.88f).scaleY(0.88f).setDuration(90).withEndAction(new Runnable(){public void run(){
                if(jarvisMicButton!=null)jarvisMicButton.animate().scaleX(1f).scaleY(1f).setDuration(140).start();
            }}).start();
            if(jarvisReadyLine!=null)jarvisReadyLine.setText("Dinliyorum...");
            if(jarvisAtomCore!=null)jarvisAtomCore.setMode(1);
            beginListening();
        }});
        android.widget.FrameLayout.LayoutParams micLp=new android.widget.FrameLayout.LayoutParams(jarvisDp(84),jarvisDp(84),Gravity.CENTER);
        micGlow.addView(jarvisMicButton,micLp);

        jarvisDrawer=new LinearLayout(this);jarvisDrawer.setOrientation(LinearLayout.VERTICAL);jarvisDrawer.setGravity(Gravity.CENTER);
        jarvisDrawer.setPadding(jarvisDp(8),jarvisDp(14),jarvisDp(8),jarvisDp(14));
        jarvisDrawer.setBackground(jarvisBg(0xee020a12,0xff147fd0,30));
        TextView chat=jarvisDrawerItem("◯","Sohbet",1);
        TextView write=jarvisDrawerItem("✎","Yaz",2);
        TextView settings=jarvisDrawerItem("⚙","Ayarlar",3);
        jarvisDrawer.addView(chat,new LinearLayout.LayoutParams(-1,0,1f));
        View d1=new View(this);d1.setBackgroundColor(0x553b6c8d);jarvisDrawer.addView(d1,new LinearLayout.LayoutParams(-1,jarvisDp(1)));
        jarvisDrawer.addView(write,new LinearLayout.LayoutParams(-1,0,1f));
        View d2=new View(this);d2.setBackgroundColor(0x553b6c8d);jarvisDrawer.addView(d2,new LinearLayout.LayoutParams(-1,jarvisDp(1)));
        jarvisDrawer.addView(settings,new LinearLayout.LayoutParams(-1,0,1f));
        android.widget.FrameLayout.LayoutParams drawerLp=new android.widget.FrameLayout.LayoutParams(jarvisDp(142),jarvisDp(350),Gravity.RIGHT|Gravity.CENTER_VERTICAL);
        drawerLp.rightMargin=jarvisDp(-4);home.addView(jarvisDrawer,drawerLp);
        jarvisDrawer.setTranslationX(jarvisDp(104));

        jarvisDrawerTab=jarvisText("‹",34,0xffeffaff);
        jarvisDrawerTab.setBackground(jarvisBg(0xee06131f,0xff1a91e8,18));
        jarvisDrawerTab.setOnClickListener(new View.OnClickListener(){public void onClick(View v){jarvisToggleDrawer();}});
        android.widget.FrameLayout.LayoutParams tabLp=new android.widget.FrameLayout.LayoutParams(jarvisDp(40),jarvisDp(82),Gravity.RIGHT|Gravity.CENTER_VERTICAL);
        home.addView(jarvisDrawerTab,tabLp);

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
    s=s.replace(dispatch_marker,dispatch_marker+'if(jarvisOverlayCommandLine!=null){String q=raw==null?"—":raw.replace("\\n"," ").trim();jarvisOverlayCommandLine.setText("Komut: "+(q.length()==0?"—":q));}',1)

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
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"','android:versionCode="111" android:versionName="1.8.9"',x,count=1)
if 'android:icon="@drawable/jarvis_icon"' not in x:
    x=x.replace('<application android:label="JARVIS"','<application android:label="JARVIS" android:icon="@drawable/jarvis_icon" android:roundIcon="@drawable/jarvis_icon"',1)
if 'com.hakan.jarvis.DesignActivity' in x:
    raise SystemExit('unsafe DesignActivity found')
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle';g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 111',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '1.8.9'",g,count=1)
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

print('JARVIS 1.8.9 UI PHASE 5B cloned home applied')


# build-trigger-187

# build-trigger-188
