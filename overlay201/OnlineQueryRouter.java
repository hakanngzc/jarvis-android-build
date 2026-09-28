package com.hakan.jarvis;

import java.text.Normalizer;
import java.util.Locale;

public final class OnlineQueryRouter {
    public static final String PROFILE = "ONLINE_INTELLIGENCE_ROUTER_V2";

    private OnlineQueryRouter() {}

    public static boolean shouldHandle(String raw) {
        String q = query(raw);
        String n = normalize(q);
        if (n.length() < 3 || n.length() > 220) return false;

        if (looksLikeDeviceAction(n)) return false;
        if (looksRealtimeUnsupported(n)) return false;
        if (looksAlreadyLocal(n)) return false;
        if (looksOnlineFollowup(n)) return false;

        if (n.endsWith("?")) return true;

        if (startsAny(n,
                "kim ", "kimdir ", "ne ", "nedir ", "neden ", "nasil ",
                "nerede ", "ne zaman ", "hangi ", "kac ", "acikla ", "anlat ")) return true;

        if (containsAny(n,
                " nedir", " kimdir", " nasil calisir", " nasil calisiyor", " nasil olur",
                " ne demek", " ne ise yarar", " neden onemli",
                " hakkinda anlat", " hakkinda bilgi ver", " aciklar misin",
                " anlatir misin", " bilgi verir misin", " arasindaki fark",
                " farki ne", " bana anlat", " bana acikla")) return true;

        if (endsAny(n, " anlat", " acikla", " anlatabilir misin", " aciklayabilir misin"))
            return true;

        return false;
    }

    public static String query(String raw) {
        if (raw == null) return "";
        String s = raw.trim();
        s = s.replaceFirst("(?iu)^(hey )?([jc]arvi[sz]|[cj]ervis)[,:]?\\s+", "");
        s = s.replaceFirst("(?iu)^lütfen\\s+", "");
        s = s.replaceFirst("(?iu)^(bana|benim için)\\s+", "");
        return s.trim();
    }

    static boolean looksOnlineFollowup(String n) {
        return eqAny(n,
                "biraz daha anlat", "daha fazla anlat", "devam et", "devamini anlat",
                "bunun hakkinda biraz daha anlat", "kisaca anlat", "kisaca soyle",
                "ozetle", "tekrar soyle", "bir daha soyle", "tekrar anlat",
                "kaynagin ne", "kaynak ne", "bunun kaynagi ne", "nereden biliyorsun",
                "kaynagi ac", "kaynak ac");
    }

    static boolean looksAlreadyLocal(String n) {
        return n.matches("(?:su an )?saat(?: kac( oldu)?)?")
                || n.matches("(?:tarih|bugun hangi gun|bugun ayin kaci)")
                || n.startsWith("hesapla ")
                || n.startsWith("not al ")
                || n.startsWith("notlar")
                || n.matches("baglanti(?: durumu)?|internet var mi")
                || n.contains("hava durumu")
                || n.matches("(?:dolar|euro|sterlin|usd|eur|gbp)(?: kuru| kac| ne kadar| kac tl)?");
    }

    static boolean looksLikeDeviceAction(String n) {
        String[] nouns = {
                "fener", "alarm", "spotify", "youtube", "uygulama", "mesaj",
                "sesi", "wifi", "bluetooth", "muzik", "sarki", "telefonu",
                "ekran", "not al"
        };
        for (String t : nouns) if (n.contains(t)) return true;

        return n.matches(".*\\b(?:ac|kapat|baslat|calistir|ara|gonder|yukselt|kis|azalt|oynat|duraklat|durdur)\\b.*");
    }

    static boolean looksRealtimeUnsupported(String n) {
        String[] tokens = {
                "son dakika", "haber", "canli", "skor", " mac ", "maci", "mac sonucu",
                "borsa", "hisse", "kripto", "bitcoin", "fiyat", "kac para",
                "trafik", "deprem", "secim sonucu", "anket", "su an ne oluyor",
                "bugun ne oldu", "bugunku gundem", "yarin hava", "hava nasil"
        };
        for (String t : tokens) if (n.contains(t)) return true;
        return false;
    }

    static boolean startsAny(String s, String... values) {
        for (String v : values) if (s.startsWith(v)) return true;
        return false;
    }

    static boolean containsAny(String s, String... values) {
        for (String v : values) if (s.contains(v)) return true;
        return false;
    }

    static boolean endsAny(String s, String... values) {
        for (String v : values) if (s.endsWith(v)) return true;
        return false;
    }

    static boolean eqAny(String s, String... values) {
        for (String v : values) if (s.equals(v)) return true;
        return false;
    }

    static String normalize(String raw) {
        if (raw == null) return "";
        String s = raw.trim().toLowerCase(new Locale("tr", "TR"));
        s = s.replace('ı','i').replace('ğ','g').replace('ü','u').replace('ş','s').replace('ö','o').replace('ç','c');
        s = Normalizer.normalize(s, Normalizer.Form.NFD).replaceAll("\\p{M}+", "");
        s = s.replace('’',' ').replace('\'',' ');
        s = s.replaceAll("[^a-z0-9? ]+", " ");
        return s.replaceAll("\\s+", " ").trim();
    }
}
