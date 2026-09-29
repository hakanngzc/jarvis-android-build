package com.hakan.jarvis;

import android.Manifest;
import android.app.Activity;
import android.content.*;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.provider.ContactsContract;
import android.provider.Settings;

import java.net.URLEncoder;
import java.text.Normalizer;
import java.util.*;

public final class ContactActions {
    public static final String PROFILE="CONTACT_ACTIONS_V1";
    public static final int REQ_CONTACTS=7205;

    public static final class ResolvedContact {
        public final String displayName,number;
        public final long contactId;
        ResolvedContact(String displayName,String number,long contactId){
            this.displayName=displayName==null?"":displayName;
            this.number=number==null?"":number;
            this.contactId=contactId;
        }
    }

    public static final class ResolveResult {
        public final String status;
        public final ResolvedContact contact;
        public final String candidates;
        ResolveResult(String status,ResolvedContact contact,String candidates){
            this.status=status;this.contact=contact;this.candidates=candidates==null?"":candidates;
        }
    }

    public static final class ActionResult {
        public final boolean success;
        public final boolean fallback;
        public final String note;
        ActionResult(boolean success,boolean fallback,String note){
            this.success=success;this.fallback=fallback;this.note=note==null?"":note;
        }
    }

    static final class Row {
        long id;
        String name,number;
        int phoneType;
        boolean primary;
        final ArrayList<String> nicknames=new ArrayList<String>();
    }

    private ContactActions(){}

    public static boolean hasContactsPermission(Activity a){
        return Build.VERSION.SDK_INT<23||a.checkSelfPermission(Manifest.permission.READ_CONTACTS)==PackageManager.PERMISSION_GRANTED;
    }

    public static void requestContactsPermission(Activity a){
        if(Build.VERSION.SDK_INT>=23)
            a.requestPermissions(new String[]{Manifest.permission.READ_CONTACTS},REQ_CONTACTS);
    }

    public static ResolveResult resolve(Activity a,String target){
        if(!hasContactsPermission(a))return new ResolveResult("PERMISSION",null,"");

        ArrayList<Row> rows=loadRows(a);
        if(rows.isEmpty())return new ResolveResult("NOT_FOUND",null,"");

        Map<Long,ArrayList<String>> nick=loadNicknames(a);
        for(Row r:rows){
            ArrayList<String> n=nick.get(Long.valueOf(r.id));
            if(n!=null)r.nicknames.addAll(n);
        }

        ArrayList<String> vars=targetVariants(target);
        ArrayList<Scored> scored=new ArrayList<Scored>();
        for(Row r:rows){
            int score=bestScore(vars,r);
            if(score>0)scored.add(new Scored(r,score));
        }
        Collections.sort(scored,new Comparator<Scored>(){
            public int compare(Scored a,Scored b){return b.score-a.score;}
        });

        if(scored.isEmpty()||scored.get(0).score<58)return new ResolveResult("NOT_FOUND",null,"");

        Scored top=scored.get(0);
        ArrayList<String> ambiguous=new ArrayList<String>();
        ambiguous.add(top.row.name);
        for(int i=1;i<scored.size()&&i<5;i++){
            Scored other=scored.get(i);
            if(other.score>=top.score-4&&!normalize(other.row.name).equals(normalize(top.row.name)))
                ambiguous.add(other.row.name);
        }
        if(ambiguous.size()>1)
            return new ResolveResult("AMBIGUOUS",null,joinUnique(ambiguous));

        return new ResolveResult("FOUND",new ResolvedContact(top.row.name,top.row.number,top.row.id),"");
    }

    static final class Scored{
        final Row row;final int score;
        Scored(Row row,int score){this.row=row;this.score=score;}
    }

    static int bestScore(List<String> variants,Row r){
        int best=0;
        for(String v:variants){
            best=Math.max(best,scoreName(v,r.name));
            for(String nick:r.nicknames)best=Math.max(best,scoreName(v,nick)+5);
        }
        if(r.primary)best+=2;
        return best;
    }

    static int scoreName(String query,String candidate){
        String q=normalize(query),c=normalize(candidate);
        if(q.length()==0||c.length()==0)return 0;
        if(q.equals(c))return 120;
        if(c.startsWith(q)||q.startsWith(c))return 98;
        if(c.contains(q)||q.contains(c))return 88;

        Set<String> qt=tokens(q),ct=tokens(c);
        if(qt.isEmpty()||ct.isEmpty())return 0;
        int hit=0;for(String x:qt)if(ct.contains(x))hit++;
        return (int)Math.round(75.0*hit/qt.size());
    }

    static ArrayList<String> targetVariants(String target){
        String n=normalize(target);
        LinkedHashSet<String> out=new LinkedHashSet<String>();
        if(n.length()>0)out.add(n);

        String[] endings={"imi","imi","umu","umu","mi","mu","yi","yu","i","u"};
        for(String e:endings){
            if(n.endsWith(e)&&n.length()>e.length()+1){
                String v=n.substring(0,n.length()-e.length()).trim();
                if(v.length()>=2)out.add(v);
            }
        }
        if(n.endsWith("m")&&n.length()>3)out.add(n.substring(0,n.length()-1));
        return new ArrayList<String>(out);
    }

    static ArrayList<Row> loadRows(Activity a){
        LinkedHashMap<Long,ArrayList<Row>> byId=new LinkedHashMap<Long,ArrayList<Row>>();
        Cursor c=null;
        try{
            String[] p={
                ContactsContract.CommonDataKinds.Phone.CONTACT_ID,
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                ContactsContract.CommonDataKinds.Phone.NUMBER,
                ContactsContract.CommonDataKinds.Phone.TYPE,
                ContactsContract.CommonDataKinds.Phone.IS_PRIMARY
            };
            c=a.getContentResolver().query(ContactsContract.CommonDataKinds.Phone.CONTENT_URI,p,null,null,null);
            if(c!=null){
                while(c.moveToNext()){
                    Row r=new Row();
                    r.id=c.getLong(0);
                    r.name=c.getString(1)==null?"":c.getString(1).trim();
                    r.number=c.getString(2)==null?"":c.getString(2).trim();
                    r.phoneType=c.getInt(3);
                    r.primary=c.getInt(4)==1;
                    if(r.name.length()==0||r.number.length()==0)continue;
                    ArrayList<Row> list=byId.get(Long.valueOf(r.id));
                    if(list==null){list=new ArrayList<Row>();byId.put(Long.valueOf(r.id),list);}
                    list.add(r);
                }
            }
        }catch(Exception ignored){}
        finally{if(c!=null)c.close();}

        ArrayList<Row> rows=new ArrayList<Row>();
        for(ArrayList<Row> list:byId.values()){
            Row best=null;
            for(Row r:list){
                if(best==null)best=r;
                else if(r.primary&&!best.primary)best=r;
                else if(r.phoneType==ContactsContract.CommonDataKinds.Phone.TYPE_MOBILE
                        &&best.phoneType!=ContactsContract.CommonDataKinds.Phone.TYPE_MOBILE&&!best.primary)best=r;
            }
            if(best!=null)rows.add(best);
        }
        return rows;
    }

    static Map<Long,ArrayList<String>> loadNicknames(Activity a){
        HashMap<Long,ArrayList<String>> out=new HashMap<Long,ArrayList<String>>();
        Cursor c=null;
        try{
            String[] p={ContactsContract.Data.CONTACT_ID,ContactsContract.CommonDataKinds.Nickname.NAME};
            String sel=ContactsContract.Data.MIMETYPE+"=?";
            String[] args={ContactsContract.CommonDataKinds.Nickname.CONTENT_ITEM_TYPE};
            c=a.getContentResolver().query(ContactsContract.Data.CONTENT_URI,p,sel,args,null);
            if(c!=null){
                while(c.moveToNext()){
                    long id=c.getLong(0);
                    String name=c.getString(1);
                    if(name==null||name.trim().length()<2)continue;
                    ArrayList<String> list=out.get(Long.valueOf(id));
                    if(list==null){list=new ArrayList<String>();out.put(Long.valueOf(id),list);}
                    list.add(name.trim());
                }
            }
        }catch(Exception ignored){}
        finally{if(c!=null)c.close();}
        return out;
    }

    public static ActionResult call(Activity a,ResolvedContact c){
        if(c==null||c.number.length()==0)return new ActionResult(false,false,"Numara yok.");
        Uri tel=Uri.fromParts("tel",c.number,null);
        try{
            boolean direct=Build.VERSION.SDK_INT<23
                ||a.checkSelfPermission(Manifest.permission.CALL_PHONE)==PackageManager.PERMISSION_GRANTED;
            Intent i=new Intent(direct?Intent.ACTION_CALL:Intent.ACTION_DIAL,tel);
            if(i.resolveActivity(a.getPackageManager())==null)return new ActionResult(false,false,"Telefon uygulaması bulunamadı.");
            a.startActivity(i);
            return new ActionResult(true,!direct,direct?"Arama başlatıldı.":"Arama izni olmadığı için numara çevirici açıldı.");
        }catch(Exception e){
            try{
                Intent d=new Intent(Intent.ACTION_DIAL,tel);
                a.startActivity(d);
                return new ActionResult(true,true,"Doğrudan arama kullanılamadı; numara çevirici açıldı.");
            }catch(Exception ignored){return new ActionResult(false,false,e.getClass().getSimpleName());}
        }
    }

    public static ActionResult composeSms(Activity a,ResolvedContact c,String message){
        if(c==null||c.number.length()==0)return new ActionResult(false,false,"Numara yok.");
        try{
            Intent i=new Intent(Intent.ACTION_SENDTO);
            i.setData(Uri.parse("smsto:"+Uri.encode(c.number)));
            i.putExtra("sms_body",message==null?"":message);
            if(i.resolveActivity(a.getPackageManager())==null)return new ActionResult(false,false,"Mesaj uygulaması bulunamadı.");
            a.startActivity(i);
            return new ActionResult(true,false,"SMS taslağı açıldı.");
        }catch(Exception e){return new ActionResult(false,false,e.getClass().getSimpleName());}
    }

    public static ActionResult composeWhatsApp(Activity a,ResolvedContact c,String message){
        if(c==null||c.number.length()==0)return new ActionResult(false,false,"Numara yok.");
        try{
            String intl=whatsAppNumber(c.number);
            if(intl.length()<8)return new ActionResult(false,false,"WhatsApp numarası hazırlanamadı.");
            String url="https://wa.me/"+intl+"?text="+URLEncoder.encode(message==null?"":message,"UTF-8");
            Intent i=new Intent(Intent.ACTION_VIEW,Uri.parse(url));
            try{
                a.getPackageManager().getPackageInfo("com.whatsapp",0);
                i.setPackage("com.whatsapp");
            }catch(Exception ignored){}
            if(i.resolveActivity(a.getPackageManager())==null){
                i.setPackage(null);
                if(i.resolveActivity(a.getPackageManager())==null)return new ActionResult(false,false,"WhatsApp bağlantısı açılamadı.");
            }
            a.startActivity(i);
            return new ActionResult(true,false,"WhatsApp mesaj taslağı açıldı.");
        }catch(Exception e){return new ActionResult(false,false,e.getClass().getSimpleName());}
    }

    static String whatsAppNumber(String raw){
        if(raw==null)return "";
        String d=raw.replaceAll("[^0-9]","");
        if(d.startsWith("00"))d=d.substring(2);
        if(d.startsWith("0")&&d.length()==11)d="90"+d.substring(1);
        else if(d.startsWith("5")&&d.length()==10)d="90"+d;
        return d;
    }

    static Set<String> tokens(String s){
        LinkedHashSet<String> out=new LinkedHashSet<String>();
        for(String x:normalize(s).split(" "))if(x.length()>1)out.add(x);
        return out;
    }

    static String joinUnique(List<String> xs){
        LinkedHashSet<String> u=new LinkedHashSet<String>(xs);
        StringBuilder b=new StringBuilder();
        for(String x:u){if(b.length()>0)b.append(", ");b.append(x);}
        return b.toString();
    }

    static String normalize(String raw){
        if(raw==null)return "";
        String s=raw.trim().toLowerCase(new Locale("tr","TR"));
        s=s.replace('ı','i').replace('ğ','g').replace('ü','u').replace('ş','s').replace('ö','o').replace('ç','c');
        s=Normalizer.normalize(s,Normalizer.Form.NFD).replaceAll("\\p{M}+","");
        s=s.replace('’',' ').replace('\'',' ');
        s=s.replaceAll("[^a-z0-9 ]+"," ");
        return s.replaceAll("\\s+"," ").trim();
    }
}
