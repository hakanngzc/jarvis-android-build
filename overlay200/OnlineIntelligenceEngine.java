package com.hakan.jarvis;

import org.json.*;
import java.io.*;
import java.net.*;
import java.text.Normalizer;
import java.util.*;

public final class OnlineIntelligenceEngine {
    public static final String PROFILE = "ONLINE_INTELLIGENCE_ENGINE_V1";
    public static final long TTL_MS = 7L * 24L * 60L * 60L * 1000L;

    public interface Transport {
        String get(String url) throws Exception;
    }

    public static final class Answer {
        public String title, text, source, url;
        public long fetchedAt;
        public boolean cached, stale;

        Answer(String title, String text, String source, String url, long fetchedAt) {
            this.title = title;
            this.text = text;
            this.source = source;
            this.url = url;
            this.fetchedAt = fetchedAt;
        }

        JSONObject json() throws Exception {
            return new JSONObject()
                    .put("title", title)
                    .put("text", text)
                    .put("source", source)
                    .put("url", url)
                    .put("time", fetchedAt);
        }

        static Answer read(JSONObject j) throws Exception {
            return new Answer(
                    j.getString("title"),
                    j.getString("text"),
                    j.getString("source"),
                    j.getString("url"),
                    j.getLong("time"));
        }
    }

    public static final class Unavailable extends Exception {
        public Unavailable(String message) {
            super(message);
        }
    }

    private final File cache;
    private final Transport transport;

    public OnlineIntelligenceEngine(File dir, Transport transport) {
        this.cache = new File(dir, "online-intelligence-cache-v1.json");
        this.transport = transport;
    }

    public synchronized void clearCache() {
        if (cache.exists()) cache.delete();
    }

    public synchronized Answer cached(String raw, long now) {
        try {
            JSONObject root = readCache();
            JSONObject entry = root.optJSONObject(key(raw));
            if (entry == null) return null;
            Answer a = Answer.read(entry);
            a.cached = true;
            a.stale = now < a.fetchedAt || now - a.fetchedAt > TTL_MS;
            return a;
        } catch (Exception e) {
            return null;
        }
    }

    public Answer fetch(String raw, boolean online, long now) throws Exception {
        String query = OnlineQueryRouter.query(raw);
        if (!OnlineQueryRouter.shouldHandle(raw))
            throw new Unavailable("Bu ifade çevrimiçi bilgi sorgusu olarak güvenle sınıflandırılamadı.");

        if (!online) {
            Answer a = cached(query, now);
            if (a != null) return a;
            throw new Unavailable("Çevrimdışısınız. Bu soru için kayıtlı bir çevrimiçi yanıt yok.");
        }

        Exception lastError = null;
        try {
            Answer a = duckDuckGo(query, now);
            if (a != null) {
                try { save(query, a); } catch (Exception ignored) {}
                return a;
            }
        } catch (Exception e) {
            lastError = e;
        }

        try {
            Answer a = wikipedia(query, now);
            if (a != null) {
                try { save(query, a); } catch (Exception ignored) {}
                return a;
            }
        } catch (Exception e) {
            lastError = e;
        }

        Answer cached = cached(query, now);
        if (cached != null) return cached;

        if (lastError instanceof InterruptedIOException || Thread.currentThread().isInterrupted())
            throw lastError;

        throw new Unavailable("Bu soru için güvenilir bir çevrimiçi özet bulunamadı.");
    }

    public static String speechText(Answer a) {
        if (a == null) return "";
        String body = a.text == null ? "" : a.text.replaceAll("\\s+", " ").trim();
        if (body.length() > 720) {
            int cut = body.lastIndexOf('.', 720);
            if (cut < 260) cut = 720;
            body = body.substring(0, cut + (cut < body.length() && body.charAt(cut) == '.' ? 1 : 0)).trim();
        }
        String title = a.title == null ? "" : a.title.trim();
        if (title.length() == 0 || body.toLowerCase(new Locale("tr","TR")).startsWith(title.toLowerCase(new Locale("tr","TR"))))
            return body;
        return title + ". " + body;
    }

    private Answer duckDuckGo(String query, long now) throws Exception {
        String url = "https://api.duckduckgo.com/?q=" + enc(query)
                + "&format=json&no_html=1&no_redirect=1&skip_disambig=1&kl=tr-tr";
        JSONObject j = new JSONObject(transport.get(url));

        String direct = clean(j.optString("Answer"));
        String abstractText = clean(j.optString("AbstractText"));
        String definition = clean(j.optString("Definition"));

        String body = "";
        if (direct.length() > 0) body = direct;
        else if (abstractText.length() >= 40) body = abstractText;
        else if (definition.length() >= 40) body = definition;
        if (body.length() == 0) return null;

        String title = clean(j.optString("Heading"));
        if (title.length() == 0) title = "Çevrimiçi bilgi";

        String sourceName = clean(j.optString("AbstractSource"));
        if (sourceName.length() == 0) sourceName = "DuckDuckGo Instant Answer";

        String sourceUrl = clean(j.optString("AbstractURL"));
        if (sourceUrl.length() == 0) sourceUrl = clean(j.optString("DefinitionURL"));
        if (sourceUrl.length() == 0) sourceUrl = "https://duckduckgo.com/?q=" + enc(query);

        return new Answer(title, body, "DuckDuckGo · " + sourceName, sourceUrl, now);
    }

    private Answer wikipedia(String query, long now) throws Exception {
        String url = "https://tr.wikipedia.org/w/api.php?action=query&format=json&formatversion=2"
                + "&generator=search&gsrnamespace=0&gsrlimit=1&gsrsearch=" + enc(query)
                + "&prop=extracts%7Cinfo&exintro=1&explaintext=1&exchars=2000&inprop=url";

        JSONObject j = new JSONObject(transport.get(url));
        JSONObject q = j.optJSONObject("query");
        JSONArray pages = q == null ? null : q.optJSONArray("pages");
        if (pages == null || pages.length() == 0) return null;

        JSONObject p = pages.getJSONObject(0);
        String body = clean(p.optString("extract"));
        if (body.length() < 40) return null;

        String title = clean(p.optString("title"));
        String sourceUrl = clean(p.optString("fullurl"));
        if (sourceUrl.length() == 0)
            sourceUrl = "https://tr.wikipedia.org/wiki/" + enc(title.replace(' ', '_'));

        return new Answer(title, body, "Türkçe Wikipedia · en ilgili eşleşme", sourceUrl, now);
    }

    private synchronized JSONObject readCache() throws Exception {
        if (!cache.isFile() || cache.length() > 800000) return new JSONObject();
        FileInputStream in = new FileInputStream(cache);
        try {
            return new JSONObject(readBounded(in, 800000));
        } finally {
            in.close();
        }
    }

    private synchronized void save(String raw, Answer answer) throws Exception {
        JSONObject root;
        try { root = readCache(); } catch (Exception e) { root = new JSONObject(); }

        root.put(key(raw), answer.json());

        while (root.length() > 40) {
            String oldest = null;
            long time = Long.MAX_VALUE;
            Iterator<String> it = root.keys();
            while (it.hasNext()) {
                String k = it.next();
                long t = root.getJSONObject(k).optLong("time", 0L);
                if (oldest == null || t < time) {
                    oldest = k;
                    time = t;
                }
            }
            if (oldest == null) break;
            root.remove(oldest);
        }

        cache.getParentFile().mkdirs();
        File tmp = new File(cache.getPath() + ".tmp");
        FileOutputStream out = new FileOutputStream(tmp);
        try {
            out.write(root.toString().getBytes("UTF-8"));
            out.getFD().sync();
        } finally {
            out.close();
        }
        if (!tmp.renameTo(cache)) throw new IOException("Cache write failed");
    }

    private static String key(String raw) {
        return normalize(OnlineQueryRouter.query(raw));
    }

    private static String normalize(String raw) {
        if (raw == null) return "";
        String s = raw.trim().toLowerCase(new Locale("tr","TR"));
        s = s.replace('ı','i').replace('ğ','g').replace('ü','u').replace('ş','s').replace('ö','o').replace('ç','c');
        s = Normalizer.normalize(s, Normalizer.Form.NFD).replaceAll("\\p{M}+", "");
        return s.replaceAll("[^a-z0-9 ]+", " ").replaceAll("\\s+", " ").trim();
    }

    private static String clean(String s) {
        if (s == null) return "";
        return s.replaceAll("<[^>]+>", " ").replaceAll("\\s+", " ").trim();
    }

    private static String enc(String q) throws Exception {
        return URLEncoder.encode(q, "UTF-8");
    }

    private static String readBounded(InputStream in, int max) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buf = new byte[4096];
        int n, total = 0;
        while ((n = in.read(buf)) != -1) {
            if (Thread.currentThread().isInterrupted()) throw new InterruptedIOException();
            total += n;
            if (total > max) throw new IOException("Response too large");
            out.write(buf, 0, n);
        }
        return out.toString("UTF-8");
    }

    public static final class HttpsTransport implements Transport {
        private volatile HttpURLConnection active;

        public void cancel() {
            HttpURLConnection c = active;
            if (c != null) c.disconnect();
        }

        public String get(String address) throws Exception {
            URL url = new URL(address);
            String host = url.getHost();

            if (!"https".equals(url.getProtocol())
                    || !Arrays.asList("api.duckduckgo.com", "tr.wikipedia.org").contains(host))
                throw new IOException("Untrusted endpoint");

            HttpURLConnection c = (HttpURLConnection) url.openConnection();
            active = c;
            c.setConnectTimeout(4500);
            c.setReadTimeout(6500);
            c.setInstanceFollowRedirects(false);
            c.setRequestProperty("Accept", "application/json");
            c.setRequestProperty("User-Agent", "JarvisAndroid/2.0.0 (personal assistant)");

            try {
                if (c.getResponseCode() != 200) throw new IOException("HTTP " + c.getResponseCode());
                InputStream in = c.getInputStream();
                try {
                    return readBounded(in, 327680);
                } finally {
                    in.close();
                }
            } finally {
                c.disconnect();
                if (active == c) active = null;
            }
        }
    }
}
