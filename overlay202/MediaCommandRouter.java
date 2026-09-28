package com.hakan.jarvis;

import java.text.Normalizer;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class MediaCommandRouter {
    public static final String PROFILE="MEDIA_ENTITY_V4";
    public static final long CONTEXT_WINDOW_MS=30L*60L*1000L;

    public static final class Command {
        public final String action;
        public final String provider;
        public final String query;
        public final String artist;
        public final String title;
        public final String reply;

        Command(String action,String provider,String query,String artist,String title,String reply){
            this.action=action;this.provider=provider;this.query=query;
            this.artist=artist;this.title=title;this.reply=reply;
        }
    }

    private MediaCommandRouter(){}

    public static Command parse(String raw,String lastProvider,long ageMs){
        String original=stripWakeRaw(raw);
        String n=normalize(original);
        if(n.length()==0)return null;

        String explicitProvider=provider(n);
        String provider=explicitProvider;
        boolean recent=lastProvider!=null&&lastProvider.length()>0&&ageMs>=0&&ageMs<=CONTEXT_WINDOW_MS;
        if(provider.length()==0&&recent)provider=lastProvider;

        if(isPause(n,provider.length()>0)){
            if(provider.length()==0)return null;
            return new Command("PAUSE",provider,"","","",providerName(provider)+" oynatmasını durduruyorum efendim.");
        }
        if(isResume(n)&&recent){
            return new Command("RESUME",lastProvider,"","","",providerName(lastProvider)+" oynatmasına devam ediyorum efendim.");
        }
        if(isNext(n)&&recent){
            return new Command("NEXT",lastProvider,"","","","Sonraki parçaya geçiyorum efendim.");
        }
        if(isPrevious(n)&&recent){
            return new Command("PREVIOUS",lastProvider,"","","","Önceki parçaya dönüyorum efendim.");
        }

        if(explicitProvider.length()==0 && !looksMusicVerb(n))return null;
        if(provider.length()==0)provider=recent?lastProvider:"spotify";

        if(isProviderOpenOnly(n,provider)){
            return new Command("OPEN",provider,"","","",providerName(provider)+" uygulamasını açıyorum efendim.");
        }

        boolean searchOnly=n.contains(" ara")||n.endsWith(" ara")||n.startsWith("ara ");
        String q=extractQuery(original,provider);
        if(q.length()<2)return null;

        Entity e=extractEntity(q);
        String query=e.query.length()>0?e.query:q;
        String reply;
        if(searchOnly){
            reply=providerName(provider)+" üzerinde "+query+" arıyorum efendim.";
            return new Command("SEARCH",provider,query,e.artist,e.title,reply);
        }
        if(e.artist.length()>0&&e.title.length()>0)
            reply=e.artist+" adlı sanatçıdan "+e.title+" parçasını "+providerName(provider)+" üzerinde açıyorum efendim.";
        else if(e.artist.length()>0)
            reply=e.artist+" için "+providerName(provider)+" üzerinde müzik açıyorum efendim.";
        else
            reply=query+" için "+providerName(provider)+" üzerinde açıyorum efendim.";
        return new Command("PLAY",provider,query,e.artist,e.title,reply);
    }

    static final class Entity{
        String query="",artist="",title="";
    }

    static Entity extractEntity(String raw){
        Entity e=new Entity();
        String q=cleanQuery(raw);
        e.query=q;

        Matcher titleFromArtist=Pattern.compile("(?iu)^(.+?)(?:['’]?[ıiuü])?\\s+(.+?)(?:['’]?(?:den|dan|ten|tan))$").matcher(q);
        if(titleFromArtist.matches()){
            String title=cleanQuery(titleFromArtist.group(1));
            String artist=cleanQuery(titleFromArtist.group(2));
            if(valid(title)&&valid(artist)){
                e.title=title;e.artist=artist;e.query=artist+" "+title;return e;
            }
        }

        Matcher artistThing=Pattern.compile("(?iu)^(.+?)(?:['’]?(?:den|dan|ten|tan))\\s+(?:bir sey|bir şey|bir parca|bir parça|muzik|müzik)$").matcher(q);
        if(artistThing.matches()){
            String artist=cleanQuery(artistThing.group(1));
            if(valid(artist)){e.artist=artist;e.query=artist;return e;}
        }

        Matcher artistTitle=Pattern.compile("(?iu)^(.+?)(?:['’]?(?:den|dan|ten|tan))\\s+(.+)$").matcher(q);
        if(artistTitle.matches()){
            String artist=cleanQuery(artistTitle.group(1));
            String title=cleanQuery(artistTitle.group(2));
            if(valid(artist)&&valid(title)){
                e.artist=artist;e.title=title;e.query=artist+" "+title;return e;
            }
        }
        return e;
    }

    static String extractQuery(String raw,String provider){
        String s=stripWakeRaw(raw).trim();
        s=s.replaceFirst("(?iu)^lütfen\\s+","");
        s=s.replaceAll("(?iu)\\bspotify(?:['’]?(?:da|de|dan|den|tan|ten|yi|i))?\\b"," ");
        s=s.replaceAll("(?iu)\\byoutube\\s*music(?:['’]?(?:da|de|dan|den|tan|ten|yi|i))?\\b"," ");
        s=s.replaceAll("(?iu)\\byoutube(?:['’]?(?:da|de|dan|den|tan|ten|yi|u|i))?\\b"," ");
        s=s.replaceAll("(?iu)\\b(?:ac|aç|cal|çal|oynat|ara|bul)\\b"," ");
        s=s.replaceAll("(?iu)\\b(?:sarkiyi|şarkıyı|sarkisini|şarkısını|sarki|şarkı|muzigi|müziği)\\b"," ");
        s=s.replaceAll("(?iu)\\b(?:bana|benim icin|benim için|lutfen|lütfen)\\b"," ");
        s=s.replaceAll("\\s+"," ").trim();
        return cleanQuery(s);
    }

    static String cleanQuery(String s){
        if(s==null)return "";
        return s.replaceAll("^[,.:;!? ]+|[,.:;!? ]+$","").replaceAll("\\s+"," ").trim();
    }

    static boolean valid(String s){return s!=null&&s.trim().length()>=2&&s.trim().length()<=90;}

    static String provider(String n){
        if(n.contains("youtube music")||n.contains("youtube muzik"))return "youtube_music";
        if(n.contains("youtube")||n.contains("yutub"))return "youtube";
        if(n.contains("spotify")||n.contains("spotif"))return "spotify";
        return "";
    }

    static boolean isProviderOpenOnly(String n,String provider){
        String p=provider.equals("spotify")?"(?:spotify|spotif.)":
                 provider.equals("youtube_music")?"youtube (?:music|muzik)":"(?:youtube|yutub.?)";
        return n.matches("^(?:ac )?"+p+"(?: yi| i| u)?(?: ac)?$")
            || n.matches("^"+p+"(?: uygulamasini)? ac$");
    }

    static boolean isPause(String n,boolean hasProvider){
        if(n.matches("^(?:sarkiyi |muzigi |muzik |sarki )?(?:durdur|duraklat)$"))return true;
        if(hasProvider && n.matches("^.*\\b(?:kapat|durdur|duraklat)\\b.*$"))return true;
        return false;
    }
    static boolean isResume(String n){return n.matches("^(?:muzige |sarkiya )?(?:devam et|devam ettir|oynat|surdu?r)$");}
    static boolean isNext(String n){return n.matches("^(?:sonraki|sonraki sarki|siradaki|siradaki sarki|diger sarki|gec)$");}
    static boolean isPrevious(String n){return n.matches("^(?:onceki|onceki sarki|geri don|bir onceki)$");}
    static boolean looksMusicVerb(String n){
        return n.matches(".*\\b(?:cal|oynat|sarki|muzik)\\b.*");
    }

    static String providerName(String p){
        if("youtube_music".equals(p))return "YouTube Music";
        if("youtube".equals(p))return "YouTube";
        return "Spotify";
    }

    static String stripWakeRaw(String raw){
        if(raw==null)return "";
        return raw.trim().replaceFirst("(?iu)^(hey )?([jc]arvi[sz]|[cj]ervis)[,:]?\\s+","");
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
