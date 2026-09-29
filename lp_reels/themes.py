"""5本それぞれのテーマ設定（色・フォント・曲・テロップ）。

時刻はすべて「素材動画の秒数」基準。0〜HOOK秒はBEFOREのみ、HOOK秒でAFTERが登場（曲のドロップ）。
captions: (開始, 終了, 英字ラベル, 日本語) … 分割表示中に下段へ出す見どころ解説
"""

HOOK = 2.0        # AFTER登場（=曲のドロップ）
END_LEN = 3.2     # エンドカードの長さ

COMMON_END = dict(
    main="あなたのLPも、\\N動かしませんか。",
    cta="LP制作のご相談はプロフィールのリンクから",
    save="SAVE ─ 保存して、あとで見返す",
)

THEMES = {
    "car": dict(
        src="dff55191", idx=0, music="770", hero=19.6,
        # 色（RGB）
        base=(8, 8, 10), accent=(214, 190, 140), text=(245, 241, 234), sub=(170, 160, 145),
        light=False, amb_bright=-0.30, amb_sat=0.9,
        f_en="Cinzel", f_jp="Shippori Mincho", f_lbl="Montserrat",
        brand="VELARIN", brand_font="Cinzel", brand_size=78, brand_sp=26,
        category="LUXURY CAR BRAND",
        hook=("そのLP、", "エンジン、かかってますか。"),
        captions=[
            (2.2, 4.4, "01  OPENING", "一瞬で世界観に引き込む"),
            (4.6, 10.0, "02  ASSEMBLY", "スクロールで、車体が組み上がる"),
            (10.2, 15.2, "03  LIFESTYLE", "写真がカードのように重なる"),
            (15.4, 19.4, "04  PERFORMANCE", "メーターと数値が走り出す"),
        ],
        hero_copy=("“見る”から、", "“体感する”へ。"),
        sfx_reveal="1143", sfx_hero="1492",
    ),
    "kebab": dict(
        src="717474a4", idx=1, music="872", hero=19.4,
        base=(14, 9, 6), accent=(255, 164, 82), text=(255, 246, 232), sub=(205, 170, 135),
        light=False, amb_bright=-0.22, amb_sat=1.25,
        f_en="Playfair Display", f_jp="Zen Kaku Gothic New", f_lbl="Montserrat",
        brand="Kebab", brand_font="Playfair Display", brand_size=104, brand_sp=2, brand_italic=True,
        category="KEBAB RESTAURANT",
        hook=("“美味しそう”が、", "伝わっていない。"),
        captions=[
            (2.2, 4.4, "01  SPICE", "秘伝のスパイスが、舞い上がる"),
            (4.6, 10.2, "02  SIZZLE", "肉と具材が、弾けて重なる"),
            (10.4, 15.2, "03  JUICY", "流れる文字で、食欲を刺激"),
            (15.4, 19.2, "04  MENU", "メニューが次々と現れる"),
        ],
        hero_copy=("“美味しそう”は、", "動きでつくる。"),
        sfx_reveal="1143", sfx_hero="1492",
    ),
    "salon": dict(
        src="f0664387", idx=2, music="132", hero=19.3,
        base=(246, 240, 232), accent=(176, 132, 102), text=(43, 33, 28), sub=(120, 100, 88),
        light=True, amb_bright=0.10, amb_sat=0.8,
        f_en="Cormorant Garamond", f_jp="Shippori Mincho", f_lbl="Montserrat",
        brand="Shizuku", brand_font="Cormorant Garamond", brand_size=112, brand_sp=4, brand_italic=True,
        category="HAIR ATELIER",
        hook=("その美しさ、", "伝わっていますか。"),
        captions=[
            (2.2, 4.4, "01  FIRST VIEW", "雫がはじける、ファーストビュー"),
            (4.6, 9.0, "02  GLOSS", "髪の艶を、映像のように見せる"),
            (9.2, 13.4, "03  MENU", "メニューがカードで流れる"),
            (13.6, 19.1, "04  ATMOSPHERE", "光と刃の、シネマティック演出"),
        ],
        hero_copy=("世界観ごと、", "美しく伝える。"),
        sfx_reveal="2350", sfx_hero="1489",
    ),
    "ryokan": dict(
        src="b4302077", idx=3, music="658", hero=18.6,
        base=(10, 12, 11), accent=(201, 164, 92), text=(240, 234, 222), sub=(160, 150, 130),
        light=False, amb_bright=-0.32, amb_sat=0.9,
        f_en="Cormorant Garamond", f_jp="Shippori Mincho", f_lbl="Montserrat",
        brand="朧", brand_font="Zen Old Mincho", brand_size=110, brand_sp=0,
        category="RYOKAN  ─  OBORO",
        hook=("写真を並べるだけの", "旅館サイトから。"),
        captions=[
            (2.2, 4.4, "01  PROLOGUE", "灯りが、ゆっくりと灯る"),
            (4.6, 9.0, "02  GARDEN", "庭・膳・湯が、順に現れる"),
            (9.2, 13.2, "03  LIGHT", "光と影で、奥行きを描く"),
            (13.4, 18.4, "04  SILENCE", "文字が流れ、花びらが舞う"),
        ],
        hero_copy=("予約の前から、", "旅は始まっている。"),
        sfx_reveal="788", sfx_hero="1489", koto=True,
    ),
    "gym": dict(
        src="24585873", idx=4, music="126", hero=19.3,
        base=(9, 9, 9), accent=(245, 196, 0), text=(255, 255, 255), sub=(180, 180, 180),
        light=False, amb_bright=-0.28, amb_sat=1.0,
        f_en="Bebas Neue", f_jp="Zen Kaku Gothic New", f_lbl="Oswald",
        brand="BEYOND", brand_font="Bebas Neue", brand_size=120, brand_sp=14,
        category="PERSONAL GYM",
        hook=("読まれないLPから、", "“動かす”LPへ。"),
        captions=[
            (2.2, 4.4, "01  KINETIC COPY", "言葉が、次々と切り替わる"),
            (4.6, 9.0, "02  STORY", "写真とコピーが連動する"),
            (9.2, 14.0, "03  PROOF", "数字とこだわりを、テンポよく"),
            (14.2, 19.1, "04  FLOW", "流れもFAQも、飽きさせない"),
        ],
        hero_copy=("“やってみたい”を、", "動かすLP。"),
        sfx_reveal="1143", sfx_hero="1492",
    ),
}

# ---- 画面録画版（AFTER/BEFORE を別々に録画した素材） ----
# rec: after/before=ファイル名の一部, offset=AFTERを遅らせる秒数（=HOOK。AFTER冒頭から見せる）,
#      hero_v/dend_v=ヒーロー開始/エンドカード開始（完成動画の秒数）
THEMES["car_rec"] = dict(
    THEMES["car"],
    rec=dict(after="3b20a6ff", before="d3312809", offset=HOOK, hero_v=21.5, dend_v=25.0),
    captions=[
        (2.2, 5.4, "01  OPENING", "一瞬で世界観に引き込む"),
        (5.6, 12.4, "02  ASSEMBLY", "スクロールで、車体が組み上がる"),
        (12.6, 17.4, "03  LIFESTYLE", "写真がカードのように重なる"),
        (17.6, 21.3, "04  PERFORMANCE", "数値とボディカラーが動き出す"),
    ],
)
THEMES["kebab_rec"] = dict(
    THEMES["kebab"],
    rec=dict(after="316a4e2b", before="50b8f99f", offset=HOOK, hero_v=20.3, dend_v=23.6),
    captions=[
        (2.2, 6.2, "01  SPICE", "秘伝のスパイスが、舞い上がる"),
        (6.4, 12.3, "02  SIZZLE", "肉と具材が、弾けて重なる"),
        (12.5, 16.3, "03  JUICY", "流れる文字で、食欲を刺激"),
        (16.5, 20.1, "04  MENU", "メニューが次々と現れる"),
    ],
)
