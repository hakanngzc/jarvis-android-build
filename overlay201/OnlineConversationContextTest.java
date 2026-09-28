package com.hakan.jarvis;

public final class OnlineConversationContextTest{
 static int pass=0,fail=0;
 static void e(String raw,String topic,long age,String expected){
  String got=OnlineConversationContext.resolve(raw,topic,age);
  if(expected==null?got==null:expected.equals(got))pass++;
  else{fail++;System.out.println("FAIL raw="+raw+" topic="+topic+" expected="+expected+" got="+got);}
 }
 public static void main(String[]a){
  e("ne zaman doğdu","Albert Einstein",5000,"Albert Einstein ne zaman doğdu");
  e("peki nereliydi","Albert Einstein",5000,"Albert Einstein nerede doğdu");
  e("biraz daha anlat","Kara delik",5000,"Kara delik hakkında biraz daha anlat");
  e("devam et","Kuantum mekaniği",5000,"Kuantum mekaniği hakkında biraz daha anlat");
  e("neden peki","Gökyüzü",5000,"Gökyüzü neden");
  e("peki nasıl oluşur","Kara delik",5000,"Kara delik nasil olusur");
  e("ne zaman kuruldu","Roma İmparatorluğu",5000,"Roma İmparatorluğu ne zaman kuruldu");
  e("bu ne demek","Fotosentez",5000,"Fotosentez ne demek");

  e("feneri aç","Albert Einstein",5000,null);
  e("Spotify aç","Albert Einstein",5000,null);
  e("peki bugünkü haberler","Albert Einstein",5000,null);
  e("devam et","",5000,null);
  e("devam et","Albert Einstein",181000,null);

  String t=OnlineConversationContext.topicFromAnswer("einstein kimdir","Albert Einstein");
  if("Albert Einstein".equals(t))pass++;else{fail++;System.out.println("FAIL topic "+t);}

  System.out.println("OnlineConversationContext: PASS "+pass+" / FAIL "+fail);
  if(fail!=0)System.exit(1);
 }
}
