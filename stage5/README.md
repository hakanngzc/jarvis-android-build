# NSS Stage5 public-stock save compatibility gate

This branch tests one narrow compatibility claim against verified public NSS 4.31 / versionCode 137 on Android 10 API29:

1. create a fresh stock Career and let stock save/load code persist it;
2. capture the exact private `MonkeyGame.xml` bytes;
3. build a same-signed update where only the v2025 club/nation/competition presentation-name fields change;
4. prove numeric IDs, row ordering, club reference columns, APK entry set and every DEX entry are unchanged;
5. install the update without clearing app data;
6. prove `MonkeyGame.xml` is byte-identical immediately after update;
7. load slot 0 through stock `LoadCareer` and reach the Career hub.

The startup/cloud/trial helpers are TEST-ONLY navigation shortcuts already used by the public Stage3 harness. They do not replace the stock save/load implementation or football identity readers.
