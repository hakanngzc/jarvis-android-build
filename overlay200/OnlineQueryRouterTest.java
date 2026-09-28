package com.hakan.jarvis;

public final class OnlineQueryRouterTest {
    private static int pass=0, fail=0;

    private static void expect(String input, boolean expected) {
        boolean got = OnlineQueryRouter.shouldHandle(input);
        if (got == expected) pass++;
        else {
            fail++;
            System.out.println("FAIL input="+input+" expected="+expected+" got="+got);
        }
    }

    private static void query(String input, String expected) {
        String got = OnlineQueryRouter.query(input);
        if (expected.equals(got)) pass++;
        else {
            fail++;
            System.out.println("FAIL query input="+input+" expected="+expected+" got="+got);
        }
    }

    public static void main(String[] args) {
        expect("Kara delik nasıl oluşur?", true);
        expect("Türkiye'nin başkenti neresi?", true);
        expect("Yer çekimi nasıl çalışır", true);
        expect("Kuantum fiziği hakkında anlat", true);
        expect("Fotosentez ne demek?", true);
        expect("Albert Einstein kimdir", true);
        expect("Neden gökyüzü mavi?", true);
        expect("DNA nedir?", true);
        expect("Bir atomu açıklar mısın", true);

        expect("feneri aç", false);
        expect("Spotify aç", false);
        expect("YouTube'u aç", false);
        expect("sesi yükselt", false);
        expect("20 dakika sonra alarm kur", false);
        expect("annemi ara", false);
        expect("mesaj gönder", false);
        expect("not al markete git", false);

        expect("bugün Beşiktaş maçı kaç kaç", false);
        expect("son dakika haberleri ne", false);
        expect("borsa şu an nasıl", false);
        expect("Bitcoin fiyatı kaç para", false);
        expect("yarın hava nasıl", false);

        expect("saat kaç", false);
        expect("dolar kuru", false);
        expect("Ankara hava durumu", false);
        expect("hesapla 12+4", false);

        query("Jarvis, kara delik nedir?", "kara delik nedir?");
        query("Hey Jarvis neden gökyüzü mavi?", "neden gökyüzü mavi?");
        query("Lütfen DNA nedir?", "DNA nedir?");

        System.out.println("OnlineQueryRouter: PASS "+pass+" / FAIL "+fail);
        if (fail != 0) System.exit(1);
    }
}
