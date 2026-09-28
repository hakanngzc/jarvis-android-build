package com.hakan.jarvis;

import java.text.Normalizer;
import java.util.Locale;

public final class OnlineFollowupRouter {
    public static final String PROFILE = "ONLINE_FOLLOWUP_CONTEXT_V1";
    public static final long WINDOW_MS = 180000L;

    public static final class Followup {
        public final String kind;
        public final String text;
        public final boolean openSource;

        Followup(String kind, String text, boolean openSource) {
            this.kind = kind;
            this.text = text == null ? "" : text;
            this.openSource = openSource;
        }
    }

    private OnlineFollowupRouter() {}

    public static Followup match(String raw, String title, String body, String source, String url, long ageMs) {
        if (ageMs < 0 || ageMs > WINDOW_MS) return null;
        if (clean(body).length() == 0) return null;
        String q = normalize(OnlineQueryRouter.query(raw));
        if (q.length() == 0) return null;

        if (eqAny(q, "kaynagin ne", "kaynak ne", "bunun kaynagi ne", "nereden biliyorsun")) {
            String sourceName = clean(source);
            if (sourceName.length() == 0) sourceName = "çevrimiçi kaynak";
            String cleanTitle = clean(title);
            String text = cleanTitle.length() == 0
                    ? "Kaynağım " + sourceName + " efendim."
                    : "Kaynağım " + sourceName + ". Başlık " + cleanTitle + " efendim.";
            return new Followup("source", text, false);
        }

        if (eqAny(q, "kaynagi ac", "kaynak ac")) {
            if (clean(url).length() == 0) return null;
            return new Followup("open_source", "Kaynağı açıyorum efendim.", true);
        }

        if (eqAny(q, "tekrar soyle", "bir daha soyle", "tekrar anlat")) {
            return new Followup("repeat", repeatText(title, body), false);
        }

        if (eqAny(q, "kisaca anlat", "kisaca soyle", "ozetle")) {
            return new Followup("short", shortText(body), false);
        }

        if (eqAny(q, "biraz daha anlat", "daha fazla anlat", "devam et", "devamini anlat",
                "bunun hakkinda biraz daha anlat")) {
            return new Followup("more", moreText(body), false);
        }

        return null;
    }

    static String repeatText(String rawTitle, String rawBody) {
        String body = clean(rawBody);
        String title = clean(rawTitle);
        if (body.length() > 720) {
            int cut = body.lastIndexOf('.', 720);
            if (cut < 260) cut = 720;
            body = body.substring(0, Math.min(body.length(), cut + (cut < body.length() && body.charAt(cut) == '.' ? 1 : 0))).trim();
        }
        if (title.length() == 0 || body.toLowerCase(new Locale("tr","TR")).startsWith(title.toLowerCase(new Locale("tr","TR"))))
            return body;
        return title + ". " + body;
    }

    static String shortText(String rawBody) {
        String body = clean(rawBody);
        if (body.length() == 0) return "Kısa bir özet çıkaramadım efendim.";
        int end = sentenceEnd(body, 320);
        String out = body.substring(0, end).trim();
        return out.length() == 0 ? body.substring(0, Math.min(260, body.length())).trim() : out;
    }

    static String moreText(String rawBody) {
        String body = clean(rawBody);
        if (body.length() == 0) return "Devam edecek kayıtlı bir özet yok efendim.";

        int start = sentenceEnd(body, 680);
        while (start < body.length() && Character.isWhitespace(body.charAt(start))) start++;
        if (start >= body.length() - 24)
            return "Elimdeki çevrimiçi özet bu kadar efendim.";

        int maxEnd = Math.min(body.length(), start + 680);
        int end = sentenceEndFrom(body, start, maxEnd);
        if (end <= start) end = maxEnd;
        return body.substring(start, end).trim();
    }

    private static int sentenceEnd(String body, int target) {
        int limit = Math.min(body.length(), target);
        int dot = Math.max(body.lastIndexOf('.', limit), Math.max(body.lastIndexOf('!', limit), body.lastIndexOf('?', limit)));
        if (dot >= 180) return dot + 1;
        return limit;
    }

    private static int sentenceEndFrom(String body, int start, int target) {
        int limit = Math.min(body.length(), target);
        int dot = Math.max(body.lastIndexOf('.', limit), Math.max(body.lastIndexOf('!', limit), body.lastIndexOf('?', limit)));
        if (dot >= start + 160) return dot + 1;
        return limit;
    }

    static String clean(String s) {
        return s == null ? "" : s.replaceAll("\\s+", " ").trim();
    }

    static boolean eqAny(String s, String... values) {
        for (String v : values) if (s.equals(v)) return true;
        return false;
    }

    static String normalize(String raw) {
        if (raw == null) return "";
        String s = raw.trim().toLowerCase(new Locale("tr","TR"));
        s = s.replace('ı','i').replace('ğ','g').replace('ü','u').replace('ş','s').replace('ö','o').replace('ç','c');
        s = Normalizer.normalize(s, Normalizer.Form.NFD).replaceAll("\\p{M}+", "");
        s = s.replace('’',' ').replace('\'',' ');
        return s.replaceAll("[^a-z0-9 ]+"," ").replaceAll("\\s+"," ").trim();
    }
}
