package com.hakan.jarvis;

import java.text.Normalizer;
import java.util.Locale;

public final class ConversationRouter {
    public static final String PROFILE = "CONTEXT_TALK_V2";
    public static final long CONTEXT_WINDOW_MS = 120000L;

    public static final class Reply {
        public final String intent;
        public final String text;
        public final String voiceKey;
        public final boolean contextual;

        Reply(String intent, String text, String voiceKey, boolean contextual) {
            this.intent = intent;
            this.text = text;
            this.voiceKey = voiceKey == null ? "" : voiceKey;
            this.contextual = contextual;
        }
    }

    private ConversationRouter() {}

    public static Reply match(String raw) {
        return matchContext(raw, "", "", "", Long.MAX_VALUE);
    }

    public static Reply matchContext(
            String raw,
            String previousIntent,
            String previousUser,
            String previousAssistant,
            long ageMs) {

        String n = normalize(raw);
        if (n.length() == 0) return null;

        if (isWakeOnly(n)) {
            return reply("wake_exact", "Buradayım efendim.", "wake", false);
        }

        String q = stripLeadingWake(n);
        if (q.length() == 0) return null;

        // Hard refusal for action-like phrases. These always belong to the legacy command engine.
        if (looksLikeAction(q)) return null;

        if (eqAny(q, "merhaba", "selam", "selamlar", "gunaydin", "iyi aksamlar", "iyi geceler")) {
            String answer = q.equals("gunaydin") ? "Günaydın efendim. Hazırım."
                    : q.equals("iyi geceler") ? "İyi geceler efendim. Buradayım."
                    : q.equals("iyi aksamlar") ? "İyi akşamlar efendim. Hazırım."
                    : "Merhaba efendim. Buradayım.";
            return reply("greeting", answer, "", false);
        }

        if (containsAny(q, "nasilsin", "iyi misin", "keyfin nasil", "durumun nasil")) {
            return reply("wellbeing", "Gayet iyiyim efendim. Sistemlerim hazır. Siz nasılsınız?", "", false);
        }

        if (containsAny(q, "ne yapiyorsun", "napiyorsun", "neyle ugrasiyorsun")) {
            return reply("activity", "Sizi dinliyorum efendim. Hazırım.", "", false);
        }

        if (eqAny(q, "sen kimsin", "kimsin", "kendini tanit", "kendini tanitsana", "sen nesin", "adin ne", "ismin ne")) {
            return reply("identity", "Ben JARVIS. Size yardımcı olmak için buradayım.", "", false);
        }

        if (containsAny(q, "beni duyuyor musun", "sesimi duyuyor musun", "duyuyor musun")) {
            return reply("hearing", "Evet efendim. Sizi duyuyorum.", "", false);
        }

        if (eqAny(q, "ne yapabilirsin", "neler yapabilirsin", "neler biliyorsun")) {
            return reply("capabilities", "Komutlarınızı çalıştırabilir, bilgi verebilir ve sizinle konuşabilirim efendim.", "", false);
        }

        if (containsAny(q, "tesekkur ederim", "tesekkurler", "sag ol", "sagol", "eyvallah")) {
            return reply("thanks", "Her zaman efendim.", "", false);
        }

        if (eqAny(q, "hazir misin", "hazirmisin", "orada misin", "burada misin")) {
            return reply("ready", "Buradayım efendim. Hazırım.", "", false);
        }

        if (eqAny(q, "gorusuruz", "sonra gorusuruz", "hosca kal", "bay bay")) {
            return reply("farewell", "Görüşmek üzere efendim.", "", false);
        }

        boolean recent = ageMs >= 0 && ageMs <= CONTEXT_WINDOW_MS;
        if (!recent) return null;

        String prev = previousIntent == null ? "" : previousIntent;

        if ("wellbeing".equals(prev)) {
            if (containsAny(q, "iyiyim", "ben de iyiyim", "gayet iyiyim", "fena degilim", "idare eder")) {
                return reply("wellbeing_positive_followup", "Bunu duymak güzel efendim.", "", true);
            }
            if (containsAny(q, "kotu", "iyi degilim", "pek iyi degilim", "moralim bozuk", "canim sikkın", "canim sikkin")) {
                return reply("wellbeing_negative_followup", "Anladım efendim. İsterseniz burada kalıp sizi dinleyebilirim.", "", true);
            }
        }

        if (eqAny(q, "sen", "peki sen", "ya sen", "sen nasilsin", "peki ya sen")) {
            return reply("context_you", "Ben iyiyim efendim. Sistemlerim hazır.", "", true);
        }

        if (eqAny(q, "tamam", "peki", "anladim", "olur", "guzel", "iyi")) {
            return reply("acknowledge", "Hazırım efendim.", "", true);
        }

        if ("thanks".equals(prev) && eqAny(q, "rica ederim", "ne demek")) {
            return reply("courtesy_followup", "Memnuniyetle efendim.", "", true);
        }

        if ("identity".equals(prev) && eqAny(q, "neden", "ne icin", "amacın ne", "amacin ne")) {
            return reply("identity_followup", "Amacım size hızlı ve güvenilir biçimde yardımcı olmak efendim.", "", true);
        }

        if ("capabilities".equals(prev) && eqAny(q, "mesela", "ornek ver", "ornegin")) {
            return reply("capabilities_followup", "Örneğin alarm kurabilir, uygulama açabilir, feneri yönetebilir ve sorularınıza yanıt verebilirim.", "", true);
        }

        return null;
    }

    private static Reply reply(String intent, String text, String voiceKey, boolean contextual) {
        return new Reply(intent, text, voiceKey, contextual);
    }

    static boolean looksLikeAction(String q) {
        // Conservative command shield: do not steal action phrases from the mature command parser.
        String[] tokens = {
            "alarm ", " alarm", "fener", "spotify", "youtube", "uygulama", "ac ", " ac",
            "kapat", "baslat", "calistir", "ara ", "mesaj", "not al", "notlar",
            "sesi ", "ses ", "yukselt", "kis", "hava durumu", "dolar", "euro",
            "saat kac", "tarih", "hesapla", "muzik", "sarki", "wifi", "bluetooth"
        };
        for (String t : tokens) if (q.contains(t)) return true;
        return false;
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
