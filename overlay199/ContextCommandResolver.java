package com.hakan.jarvis;

import java.text.Normalizer;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class ContextCommandResolver {
    public static final String PROFILE = "CONTEXTUAL_COMMANDS_V1";
    public static final long WINDOW_MS = 90000L;

    public static final class Resolution {
        public final String resolvedCommand;
        public final String contextType;
        public final int confidence;

        Resolution(String resolvedCommand, String contextType, int confidence) {
            this.resolvedCommand = resolvedCommand;
            this.contextType = contextType;
            this.confidence = confidence;
        }
    }

    private static final Pattern RELATIVE_ALARM =
            Pattern.compile("^(\\d{1,4})\\s*dakika\\s*sonra\\s*alarm\\s*kur$");

    private ContextCommandResolver() {}

    public static boolean isTrackable(String raw) {
        return classify(raw) != null;
    }

    public static Resolution resolve(String raw, String previousCommand, long ageMs) {
        if (raw == null || previousCommand == null) return null;
        if (ageMs < 0 || ageMs > WINDOW_MS) return null;

        String q = stripWake(normalize(raw));
        if (q.length() == 0) return null;

        Context previous = classify(previousCommand);
        if (previous == null) return null;

        if ("VOLUME_UP".equals(previous.type)) {
            if (eqAny(q, "biraz daha", "daha", "bir tik daha", "biraz daha yukselt", "daha yukselt"))
                return resolution("sesi yükselt", previous.type, 96);
            if (eqAny(q, "tersi", "tersini yap", "geri al"))
                return resolution("sesi kıs", previous.type, 88);
            if (eqAny(q, "tekrar", "tekrar yap", "aynisini yap"))
                return resolution("sesi yükselt", previous.type, 94);
        }

        if ("VOLUME_DOWN".equals(previous.type)) {
            if (eqAny(q, "biraz daha", "daha", "bir tik daha", "biraz daha kis", "daha kis"))
                return resolution("sesi kıs", previous.type, 96);
            if (eqAny(q, "tersi", "tersini yap", "geri al"))
                return resolution("sesi yükselt", previous.type, 88);
            if (eqAny(q, "tekrar", "tekrar yap", "aynisini yap"))
                return resolution("sesi kıs", previous.type, 94);
        }

        if ("FLASH_ON".equals(previous.type)) {
            if (eqAny(q, "kapat", "simdi kapat", "onu kapat", "feneri kapat"))
                return resolution("feneri kapat", previous.type, 99);
            if (eqAny(q, "tekrar", "tekrar yap", "aynisini yap", "tekrar ac"))
                return resolution("feneri aç", previous.type, 96);
        }

        if ("FLASH_OFF".equals(previous.type)) {
            if (eqAny(q, "ac", "geri ac", "tekrar ac", "onu ac", "feneri ac"))
                return resolution("feneri aç", previous.type, 99);
            if (eqAny(q, "tekrar", "tekrar yap", "aynisini yap"))
                return resolution("feneri kapat", previous.type, 94);
        }

        if ("APP_OPEN_SPOTIFY".equals(previous.type)) {
            if (eqAny(q, "tekrar ac", "geri ac", "yeniden ac", "tekrar yap"))
                return resolution("Spotify aç", previous.type, 95);
        }

        if ("APP_OPEN_YOUTUBE".equals(previous.type)) {
            if (eqAny(q, "tekrar ac", "geri ac", "yeniden ac", "tekrar yap"))
                return resolution("YouTube aç", previous.type, 95);
        }

        if ("ALARM_RELATIVE".equals(previous.type)) {
            int base = previous.minutes;
            Integer delta = parseDeltaMinutes(q);
            if (delta != null) {
                int total = base + delta.intValue();
                if (total >= 1 && total <= 1440)
                    return resolution(total + " dakika sonra alarm kur", previous.type, 97);
            }
            if (eqAny(q, "tekrar kur", "ayni alarmi kur", "tekrar yap"))
                return resolution(base + " dakika sonra alarm kur", previous.type, 93);
        }

        return null;
    }

    private static Integer parseDeltaMinutes(String q) {
        Matcher add = Pattern.compile("^(\\d{1,3})\\s*dakika\\s*(daha\\s*)?(ekle|uzat)$").matcher(q);
        if (add.matches()) return Integer.valueOf(Integer.parseInt(add.group(1)));

        Matcher sub = Pattern.compile("^(\\d{1,3})\\s*dakika\\s*(azalt|kisalt)$").matcher(q);
        if (sub.matches()) return Integer.valueOf(-Integer.parseInt(sub.group(1)));

        return null;
    }

    private static Resolution resolution(String cmd, String type, int confidence) {
        return new Resolution(cmd, type, confidence);
    }

    private static final class Context {
        final String type;
        final int minutes;
        Context(String type, int minutes) {
            this.type = type;
            this.minutes = minutes;
        }
    }

    private static Context classify(String raw) {
        String q = stripWake(normalize(raw));
        if (q.length() == 0) return null;

        if (containsAny(q, "sesi yukselt", "ses yukselt", "sesi arttir", "ses arttir"))
            return new Context("VOLUME_UP", 0);
        if (containsAny(q, "sesi kis", "ses kis", "sesi azalt", "ses azalt"))
            return new Context("VOLUME_DOWN", 0);

        if (containsAny(q, "feneri ac", "fener ac"))
            return new Context("FLASH_ON", 0);
        if (containsAny(q, "feneri kapat", "fener kapat"))
            return new Context("FLASH_OFF", 0);

        if (containsAny(q, "spotify ac", "spotify yi ac", "spotify i ac", "spotifyyi ac"))
            return new Context("APP_OPEN_SPOTIFY", 0);
        if (containsAny(q, "youtube ac", "youtube u ac", "youtube yi ac", "youtubeu ac"))
            return new Context("APP_OPEN_YOUTUBE", 0);

        Matcher alarm = RELATIVE_ALARM.matcher(q);
        if (alarm.matches()) {
            int minutes = Integer.parseInt(alarm.group(1));
            if (minutes >= 1 && minutes <= 1440)
                return new Context("ALARM_RELATIVE", minutes);
        }

        return null;
    }

    static String normalize(String raw) {
        if (raw == null) return "";
        String s = raw.trim().toLowerCase(new Locale("tr", "TR"));
        s = s.replace('ı','i').replace('ğ','g').replace('ü','u').replace('ş','s').replace('ö','o').replace('ç','c');
        s = Normalizer.normalize(s, Normalizer.Form.NFD).replaceAll("\\p{M}+", "");
        s = s.replace('’',' ').replace('\'',' ');
        s = s.replaceAll("[^a-z0-9 ]+", " ");
        return s.replaceAll("\\s+", " ").trim();
    }

    static String stripWake(String q) {
        String[] prefixes = {
            "hey jarvis ", "hey jarviz ", "hey carvis ", "hey jervis ",
            "jarvis ", "jarviz ", "carvis ", "jervis "
        };
        for (String p : prefixes) if (q.startsWith(p)) return q.substring(p.length()).trim();
        return q;
    }

    static boolean eqAny(String s, String... values) {
        for (String v : values) if (s.equals(v)) return true;
        return false;
    }

    static boolean containsAny(String s, String... values) {
        for (String v : values) if (s.contains(v)) return true;
        return false;
    }
}
