package com.hakan.jarvis;

import java.text.Normalizer;
import java.util.Locale;

public final class ConversationRouter {
    public static final String PROFILE = "CONVERSATION_CORE_V1";

    public static final class Reply {
        public final String intent;
        public final String text;
        public final String voiceKey;
        Reply(String intent, String text, String voiceKey) {
            this.intent = intent;
            this.text = text;
            this.voiceKey = voiceKey == null ? "" : voiceKey;
        }
    }

    private ConversationRouter() {}

    public static Reply match(String raw) {
        String n = normalize(raw);
        if (n.length() == 0) return null;

        boolean wakeOnly = isWakeOnly(n);
        if (wakeOnly) {
            return new Reply("wake_exact", "Buradayım efendim.", "wake");
        }

        String q = stripLeadingWake(n);
        if (q.length() == 0) return null;

        if (eqAny(q, "merhaba", "selam", "selamlar", "gunaydin", "iyi aksamlar", "iyi geceler")) {
            String answer = q.equals("gunaydin") ? "Günaydın efendim. Hazırım."
                    : q.equals("iyi geceler") ? "İyi geceler efendim. Buradayım."
                    : q.equals("iyi aksamlar") ? "İyi akşamlar efendim. Hazırım."
                    : "Merhaba efendim. Buradayım.";
            return new Reply("greeting", answer, "");
        }

        if (containsAny(q, "nasilsin", "iyi misin", "keyfin nasil", "durumun nasil")) {
            return new Reply("wellbeing", "Gayet iyiyim efendim. Sistemlerim hazır.", "");
        }

        if (containsAny(q, "ne yapiyorsun", "napıyorsun", "napiyorsun", "neyle ugrasiyorsun")) {
            return new Reply("activity", "Sizi dinliyorum efendim. Hazırım.", "");
        }

        if (eqAny(q, "sen kimsin", "kimsin", "kendini tanit", "kendini tanitsana", "sen nesin")) {
            return new Reply("identity", "Ben JARVIS. Size yardımcı olmak için buradayım.", "");
        }

        if (containsAny(q, "tesekkur ederim", "tesekkurler", "sag ol", "sagol", "eyvallah")) {
            return new Reply("thanks", "Her zaman efendim.", "");
        }

        if (eqAny(q, "hazir misin", "hazirmisin", "orada misin", "burada misin")) {
            return new Reply("ready", "Buradayım efendim. Hazırım.", "");
        }

        return null;
    }

    static boolean isWakeOnly(String n) {
        return eqAny(n, "jarvis", "hey jarvis", "heyjarvis", "jarviz", "hey jarviz", "carvis", "hey carvis", "jervis", "hey jervis");
    }

    static String stripLeadingWake(String n) {
        String[] prefixes = {
            "hey jarvis ", "hey jarviz ", "hey carvis ", "hey jervis ",
            "jarvis ", "jarviz ", "carvis ", "jervis "
        };
        for (String p : prefixes) if (n.startsWith(p)) return n.substring(p.length()).trim();
        return n;
    }

    static boolean eqAny(String s, String... values) {
        for (String v : values) if (s.equals(v)) return true;
        return false;
    }

    static boolean containsAny(String s, String... values) {
        for (String v : values) if (s.contains(v)) return true;
        return false;
    }

    static String normalize(String raw) {
        if (raw == null) return "";
        String s = raw.trim().toLowerCase(new Locale("tr", "TR"));
        s = s.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c');
        s = Normalizer.normalize(s, Normalizer.Form.NFD).replaceAll("\\p{M}+", "");
        s = s.replace('’', ' ').replace('\'', ' ');
        s = s.replaceAll("[^a-z0-9 ]+", " ");
        return s.replaceAll("\\s+", " ").trim();
    }
}
