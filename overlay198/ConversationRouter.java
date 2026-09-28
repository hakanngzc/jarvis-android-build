package com.hakan.jarvis;

import java.text.Normalizer;
import java.util.Locale;

public final class ConversationRouter {
    public static final String PROFILE = "CONTEXT_MEMORY_V3";
    public static final long CONTEXT_WINDOW_MS = 120000L;

    public static final class Reply {
        public final String intent;
        public final String text;
        public final String voiceKey;
        public final boolean contextual;
        // null = keep current value, empty = clear, non-empty = remember
        public final String memoryName;
        public final String memoryTopic;

        Reply(String intent, String text, String voiceKey, boolean contextual) {
            this(intent, text, voiceKey, contextual, null, null);
        }

        Reply(String intent, String text, String voiceKey, boolean contextual, String memoryName, String memoryTopic) {
            this.intent = intent;
            this.text = text;
            this.voiceKey = voiceKey == null ? "" : voiceKey;
            this.contextual = contextual;
            this.memoryName = memoryName;
            this.memoryTopic = memoryTopic;
        }
    }

    private ConversationRouter() {}

    public static Reply match(String raw) {
        return matchContext(raw, "", "", "", Long.MAX_VALUE, "", "");
    }

    // Compatibility path used by the 1.9.7 regression suite.
    public static Reply matchContext(String raw, String previousIntent, String previousUser, String previousAssistant, long ageMs) {
        return matchContext(raw, previousIntent, previousUser, previousAssistant, ageMs, "", "");
    }

    public static Reply matchContext(
            String raw,
            String previousIntent,
            String previousUser,
            String previousAssistant,
            long ageMs,
            String rememberedName,
            String rememberedTopic) {

        String n = normalize(raw);
        if (n.length() == 0) return null;

        if (isWakeOnly(n)) {
            return reply("wake_exact", "Buradayım efendim.", "wake", false);
        }

        String q = stripLeadingWake(n);
        if (q.length() == 0) return null;

        // Mature action commands always stay with the legacy command engine.
        if (looksLikeAction(q)) return null;

        String name = safe(rememberedName);
        String topic = safe(rememberedTopic);

        // Session memory questions come before memory writes.
        if (eqAny(q, "adim ne", "benim adim ne", "ismim ne", "beni taniyor musun", "ben kimim")) {
            if (name.length() > 0) {
                return reply("memory_name_recall", "Bu oturumda sizi " + name + " olarak hatırlıyorum efendim.", "", true);
            }
            return reply("memory_name_empty", "Bu oturumda adınızı henüz söylemediniz efendim.", "", true);
        }

        if (eqAny(q, "ne hakkinda konusuyorduk", "konumuz neydi", "hangi konudaydik", "konu neydi")) {
            if (topic.length() > 0) {
                return reply("memory_topic_recall", "Son konuşma konumuz " + topic + " idi efendim.", "", true);
            }
            return reply("memory_topic_empty", "Henüz belirgin bir konuşma konusu kaydetmedim efendim.", "", true);
        }

        if (eqAny(q, "ismimi unut", "adimi unut")) {
            return reply("memory_name_clear", "Peki efendim. Bu oturumdaki isim bilgisini bıraktım.", "", true, "", null);
        }

        if (eqAny(q, "konuyu unut", "konuyu kapat", "bu konuyu kapat")) {
            return reply("memory_topic_clear", "Peki efendim. Konuyu kapattım.", "", true, null, "");
        }

        String learnedName = extractName(q);
        if (learnedName.length() > 0) {
            return reply("memory_name_store", "Memnun oldum " + learnedName + ". Bu oturumda isminizi hatırlayacağım.", "", true, learnedName, null);
        }

        String learnedTopic = extractTopic(q);
        if (learnedTopic.length() > 0) {
            return reply("memory_topic_store", "Tamam efendim. " + learnedTopic + " hakkında devam edebiliriz.", "", true, null, learnedTopic);
        }

        if (eqAny(q, "merhaba", "selam", "selamlar", "gunaydin", "iyi aksamlar", "iyi geceler")) {
            String who = name.length() > 0 ? " " + name : " efendim";
            String answer = q.equals("gunaydin") ? "Günaydın" + who + ". Hazırım."
                    : q.equals("iyi geceler") ? "İyi geceler" + who + ". Buradayım."
                    : q.equals("iyi aksamlar") ? "İyi akşamlar" + who + ". Hazırım."
                    : "Merhaba" + who + ". Buradayım.";
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

        String prev = safe(previousIntent);

        if ("wellbeing".equals(prev)) {
            if (containsAny(q, "iyiyim", "ben de iyiyim", "gayet iyiyim", "fena degilim", "idare eder")) {
                return reply("wellbeing_positive_followup", "Bunu duymak güzel efendim.", "", true);
            }
            if (containsAny(q, "kotu", "iyi degilim", "pek iyi degilim", "moralim bozuk", "canim sikkin")) {
                return reply("wellbeing_negative_followup", "Anladım efendim. İsterseniz burada kalıp sizi dinleyebilirim.", "", true);
            }
        }

        if (eqAny(q, "sen", "peki sen", "ya sen", "sen nasilsin", "peki ya sen")) {
            return reply("context_you", "Ben iyiyim efendim. Sistemlerim hazır.", "", true);
        }

        if (eqAny(q, "gercekten mi", "ciddi misin", "emin misin")) {
            return reply("context_confirm", "Evet efendim.", "", true);
        }

        if (eqAny(q, "tamam", "peki", "anladim", "olur", "guzel", "iyi", "harika")) {
            return reply("acknowledge", "Hazırım efendim.", "", true);
        }

        if ("thanks".equals(prev) && eqAny(q, "rica ederim", "ne demek")) {
            return reply("courtesy_followup", "Memnuniyetle efendim.", "", true);
        }

        if ("identity".equals(prev) && eqAny(q, "neden", "ne icin", "amacin ne")) {
            return reply("identity_followup", "Amacım size hızlı ve güvenilir biçimde yardımcı olmak efendim.", "", true);
        }

        if ("capabilities".equals(prev) && eqAny(q, "mesela", "ornek ver", "ornegin")) {
            return reply("capabilities_followup", "Örneğin alarm kurabilir, uygulama açabilir, feneri yönetebilir ve sorularınıza yanıt verebilirim.", "", true);
        }

        if (topic.length() > 0 && eqAny(q, "devam et", "devam edelim", "konuya devam et", "ordan devam et")) {
            return reply("topic_continue", topic + " konusuna devam ediyoruz efendim. Sizi dinliyorum.", "", true);
        }

        return null;
    }

    private static Reply reply(String intent, String text, String voiceKey, boolean contextual) {
        return new Reply(intent, text, voiceKey, contextual, null, null);
    }

    private static Reply reply(String intent, String text, String voiceKey, boolean contextual, String memoryName, String memoryTopic) {
        return new Reply(intent, text, voiceKey, contextual, memoryName, memoryTopic);
    }

    static String extractName(String q) {
        String v = "";
        if (q.startsWith("benim adim ")) v = q.substring("benim adim ".length()).trim();
        else if (q.startsWith("adim ")) v = q.substring("adim ".length()).trim();
        else if (q.startsWith("ismim ")) v = q.substring("ismim ".length()).trim();
        if (v.length() < 2 || v.length() > 24 || v.indexOf(' ') >= 0 || !v.matches("[a-z]+")) return "";
        return capitalize(v);
    }

    static String extractTopic(String q) {
        String[] suffixes = {" hakkinda konusalim", " hakkinda konusabiliriz", " konusunu konusalim"};
        for (String suffix : suffixes) {
            if (q.endsWith(suffix)) {
                String v = q.substring(0, q.length() - suffix.length()).trim();
                if (v.length() >= 2 && v.length() <= 48) return capitalizeWords(v);
            }
        }
        return "";
    }

    static String capitalize(String v) {
        if (v == null || v.length() == 0) return "";
        return v.substring(0,1).toUpperCase(new Locale("tr","TR")) + v.substring(1);
    }

    static String capitalizeWords(String v) {
        String[] p=v.split(" ");
        StringBuilder b=new StringBuilder();
        for(String x:p){
            if(x.length()==0)continue;
            if(b.length()>0)b.append(' ');
            b.append(capitalize(x));
        }
        return b.toString();
    }

    static String safe(String v) { return v == null ? "" : v.trim(); }

    static boolean looksLikeAction(String q) {
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
