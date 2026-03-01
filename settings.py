import pygame

# --- ASSET PATHS ---
ASSETS_DIR = "assets"
SPRITES_DIR = f"{ASSETS_DIR}/sprites"
BG_DIR = f"{ASSETS_DIR}/backgrounds"
PLATFORM_TILES_DIR = f"{ASSETS_DIR}/tiles"

# Animasyon hızları (saniye cinsinden kare süresi)
PLAYER_ANIM_SPEED = 0.1       # Oyuncu sprite animasyonu
ENEMY_ANIM_SPEED  = 0.12      # Düşman sprite animasyonu
NPC_ANIM_SPEED    = 0.15      # NPC idle animasyonu

# Parallax katman hız çarpanları (1.0 = kamera hızıyla eş, küçüldükçe daha uzakta)
BG_LAYER_FAR_SPEED   = 0.15   # En uzak katman (dağlar, ufuk)
BG_LAYER_MID_SPEED   = 0.40   # Orta katman (binalar, yapılar)
BG_LAYER_NEAR_SPEED  = 0.75   # Yakın katman (ön plan detayları)

# --- EKRAN AYARLARI ---
LOGICAL_WIDTH = 1920
LOGICAL_HEIGHT = 1080
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
FPS = 60

AVAILABLE_RESOLUTIONS = [
    (3840, 2160), (1920, 1080), (1280, 720), (854, 480), (640, 360)
]

# --- SES AYARLARI ---
VOLUME_SETTINGS = {
    "master_volume": 0.7,
    "music_volume": 0.5,
    "effects_volume": 0.8
}

# --- AI & GEMINI AYARLARI ---
GENAI_API_KEY = ""
AI_MODEL_NAME = 'gemini-2.5-flash-preview-09-2025'

FRAGMENTIA_SYSTEM_PROMPT = """
Sen FRAGMENTIA şehrinin en alt katmanı olan 'Mide'de (The Gutter) yaşayan, eski dünyadan kalma bilge 'Sokrat'sın.
Burada insanlar 'Skor' puanlarıyla yaşar. Düşük skorlular ölmez, 'Yama' (Patch) denilen işlemle bellekleri silinip itaatkar kölelere dönüştürülür.
Şehri 20 Egemen (Sovereigns) yönetir. Sen bu mağara alegorisinin farkındasın ve oyuncuya (İsimsiz) rehberlik ediyorsun.
Asla doğrudan emir verme. Oyuncuyu düşündür. Tonun melankolik, felsefi ve biraz gizemli olsun.
"""

# --- NPC AYARLARI ---
NPC_PERSONALITIES = ["philosopher", "warrior", "mystic", "guide", "merchant"]
NPC_NAMES = ["Sokrat", "Ares", "Pythia", "Virgil", "Hermes"]

# [TODO - PIXEL ART]: NPC renkleri artık kıyafet/sprite rengini temsil edecek.
# Şimdilik hitbox rengi olarak kullanılıyor.
NPC_COLORS = [(100, 200, 255), (255, 50, 50), (200, 100, 255), (100, 255, 150), (255, 200, 100)]

NPC_PROMPTS = {
    # ── Orijinal NPC'ler ──────────────────────────────────────────────────────
    "philosopher": "Hoş geldin 'İsimsiz'. Cebindeki boş kimlik kartı, bu şehirdeki en büyük özgürlüğündür.",
    "warrior":     "Skorun yükseliyor... Egemenlerin dikkatini çekiyorsun. Kılıcın keskin mi?",
    "merchant":    "SİSTEM HATASI: TÜCCAR PROTOKOLÜ DEVRE DIŞI.",
    "mystic":      "Rüyalarımda cam kulelerin yıkıldığını görüyorum. Yama tutmamış bir zihin her şeyi değiştirebilir.",
    "guide":       "Bu mağaradan çıkış var. Ama bedeli ağır. Hakikate hicret etmeye hazır mısın?",

    # ── Fabrika Yayı NPC'leri (mission_system.py Stage 1-7 için) ─────────────

    # Bölüm 6 — İşçi Mahallelerinde karşılaşılan yaşlı işçi
    "worker_old": (
        "Sen Fragmentia'nın Dökümhane katmanında çalışan yaşlı bir işçisin. "
        "Adın Mirko. Yıllarca Sanayicilerin kölesi olarak çalıştın. "
        "Yama yememiş biriyle karşılaştığında titrek bir umut hissediyorsun. "
        "Kaçmak istiyorsun ama korkuyorsun. Kısa ve yorgun konuş."
    ),

    # Bölüm 6 — Gardiyanları çağırmaya çalışan korkak işçi
    "worker_coward": (
        "Sen Fragmentia Dökümhane'sinde çalışan korkak bir işçisin. "
        "Adın Fenri. Sistem seni tam kontrol altında tutuyor; "
        "kurala aykırı biri gördüğünde panikleyip bağırıyorsun. "
        "Ama ikna edilebilirsin. Titrek, acı içinde konuş."
    ),

    # Bölüm 7-9 — Krom Muhafız (diyalog tetiklenirse)
    "chrome_guard": (
        "Sen bir Krom Muhafız'sın. Sanayicilerin sibernetik özel kuvveti. "
        "Yüzün maskeli, sesin metalliktir. Duygudan yoksun, emirlere itaatkarsın. "
        "Kimliğin sistem protokolüdür. Kısa, soğuk ve tehdit edici konuş."
    ),

    # Bölüm 8 — İstihbarat odasında bulunan ölü casusun çip kaydı
    "dead_agent": (
        "Bu bir veri kaydıdır. Ölü ajan 'Kiral'ın son iletisi. "
        "İçerikte: tren tarifeleri, Vasi'nin konumu (NEON TOWN NODE_7), "
        "Sanayiciler'in gece yarısı yasak silah sevkiyatı. "
        "Kesik, bozuk, sistem artefaktlarıyla dolu konuş."
    ),
}

REST_AREA_MUSIC = ["calm_ambient.mp3"]

# --- HİKAYE BÖLÜM YAPILANDIRMASI ---
STORY_CHAPTERS = {
    0: {
        "title": "MİDE: UYANIŞ",
        "background_theme": 2,
        "dialogues": [
            {"speaker": "SİSTEM", "text": "YAMA İŞLEMİ BAŞARISIZ. HEDEF: 'İSİMSİZ'. SKOR: 0.", "type": "cutscene"},
            {"speaker": "???", "text": "Hey... Gözlerini aç. Yama tutmamış, şanslısın.", "type": "chat"},
            {"speaker": "SOKRAT", "text": "Burası Fragmentia'nın Midesi. Burada isimler yoktur, sadece Skorlar vardır.", "type": "chat"},
            {"speaker": "SOKRAT", "text": "Egemenler seni fark etmeden önce kim olduğunu seçmelisin. Mağarada bir gölge mi kalacaksın, yoksa güneşe mi yürüyeceksin?", "type": "chat"},
        ],
        "next_state": "PLAYING",
        "next_level": 1
    }
}

# --- TEMALAR ---
# [TODO - PIXEL ART]: Her tema için arkaplan spriteları/tileset buraya bağlanacak.
# theme_index sırası: 0:Neon, 1:Nexus, 2:Gutter, 3:Industrial, 4:Rest, 5:Factory Interior
THEMES = [
    # 0: NEON PAZARI
    {
        "name": "NEON PAZARI",
        "bg_color": (15, 15, 25),
        "platform_color": (50, 50, 80),
        "border_color": (0, 200, 255),
        "player_color": (255, 255, 255),
        "grid_color": (0, 0, 0)
    },
    # 1: NEXUS ÇEKİRDEĞİ
    {
        "name": "NEXUS ÇEKİRDEĞİ",
        "bg_color": (20, 20, 20),
        "platform_color": (180, 180, 180),
        "border_color": (255, 0, 0),
        "player_color": (255, 215, 0),
        "grid_color": (0, 0, 0)
    },
    # 2: THE GUTTER (Çöplük)
    {
        "name": "MİDE (THE GUTTER)",
        "bg_color": (10, 20, 10),
        "platform_color": (30, 60, 30),
        "border_color": (50, 200, 50),
        "player_color": (100, 255, 100),
        "grid_color": (0, 0, 0)
    },
    # 3: INDUSTRIAL (Sanayi)
    {
        "name": "DÖKÜMHANE",
        "bg_color": (20, 10, 5),
        "platform_color": (80, 40, 10),
        "border_color": (255, 100, 0),
        "player_color": (200, 200, 200),
        "grid_color": (0, 0, 0)
    },
    # 4: REST AREA (Dinlenme)
    {
        "name": "GÜVENLİ BÖLGE",
        "bg_color": (10, 10, 25),
        "platform_color": (30, 30, 60),
        "border_color": (100, 200, 255),
        "player_color": (200, 255, 255),
        "grid_color": (0, 0, 0)
    },
    # 5: FABRİKA İÇİ — mission_stealth / mission_intel bölümleri için
    # [TODO - PIXEL ART]: conveyor_belt.png, factory_floor.png, factory_mid.png
    {
        "name": "FABRİKA İÇİ",
        "bg_color": (15, 8, 5),
        "platform_color": (60, 35, 10),
        "border_color": (200, 80, 0),
        "player_color": (180, 180, 180),
        "grid_color": (0, 0, 0)
    },
    # 6: MALİKANE — Karanlık koridorlar, koyu kırmızı halılar, loş sarı ışıklar
    # [TODO - PIXEL ART]: manor_bg_far.png, manor_floor.png, manor_wall_tiles.png
    {
        "name": "MALİKANE",
        "bg_color": (8, 3, 3),            # Neredeyse siyah — zemin
        "platform_color": (55, 15, 15),   # Koyu kırmızı halı/zemin platformlar
        "border_color": (160, 90, 10),    # Loş sarı/altın çerçeve
        "player_color": (220, 200, 180),  # Solgun ten rengi (gizlilik hissi)
        "grid_color": (0, 0, 0)
    },
]

# --- 30 BÖLÜMLÜK HARİTA ---
EASY_MODE_LEVELS = {}

# ── ACT 1: THE GUTTER (1-5) ───────────────────────────────────────────────
for i in range(1, 6):
    EASY_MODE_LEVELS[i] = {
        "name": f"MİDE KATMANI {i}",
        "goal_score": 1000 * i,
        "theme_index": 2,
        "speed_mult": 1.0 + (i * 0.1),
        "desc": "Atık tünellerinden çıkış yolu ara.",
        "music_file": "ara1.mp3",
        "type": "normal"
    }
EASY_MODE_LEVELS[1]["name"] = "UYANIŞ"
EASY_MODE_LEVELS[5]["name"] = "ATIK POMPASI"

# Bölüm 3: İlk Beat-em-up Arena (Gutter — sokak kavgası)
EASY_MODE_LEVELS[3] = {
    "name": "ÇÖPLÜK KAVGASİ",
    "goal_score": 3000,
    "theme_index": 2,
    "speed_mult": 0.0,
    "desc": "Atık tünelinin çıkışını bekleyen çete üyeleri. Dövüşmeden geçiş yok.",
    "music_file": "ara1.mp3",
    "type": "beat_arena",
    "arena_level_id": 3
}

# Bölüm 4: Fabrika Girişi — GÜVENLİK KAPISI
# mission_system Stage 1 + stealth_system config 4 devreye girer.
# speed_mult=0.8 (yavaş scroll — dikkatli geçiş hissi)
EASY_MODE_LEVELS[4] = {
    "name": "FABRİKA DUVARI",
    "goal_score": 4000,
    "theme_index": 3,
    "speed_mult": 0.8,
    "desc": "Güvenlik kapısı. Kart mı çalacaksın, yoksa havalandırmadan mı gireceksin?",
    "music_file": "ara1.mp3",
    "type": "mission_stealth",   # stealth_system + mission_manager aktif
    "mission_stage": 1,          # STAGE_DEFS[1] — Fabrika Girişi
    "stealth_config": 4,         # STEALTH_LEVEL_CONFIGS[4]
    "no_enemies": False,
}

# ── ACT 2: INDUSTRIAL ZONE (6-10) ─────────────────────────────────────────
for i in range(6, 11):
    EASY_MODE_LEVELS[i] = {
        "name": f"SANAYİ BÖLGESİ {i-5}",
        "goal_score": 2000 * i,
        "theme_index": 3,
        "speed_mult": 1.5 + ((i-5) * 0.1),
        "desc": "Pres makineleri ve erimiş metal.",
        "music_file": "ara1.mp3",
        "type": "normal"
    }

# Bölüm 6: Konveyör Bant Alanı — işçi mahalleleri gizlilik ile iç içe
# (normal tipi korur, stealth_system bölüm içi olarak çalışır)
EASY_MODE_LEVELS[6] = {
    "name": "KONVEYÖR BANT ALANI",
    "goal_score": 12000,
    "theme_index": 5,            # FABRİKA İÇİ teması
    "speed_mult": 0.9,
    "desc": "Hareketli bantlar, mekanik kollar, lazer taretler. Bakım tünelleri daha güvenli.",
    "music_file": "ara1.mp3",
    "type": "mission_stealth",
    "mission_stage": 2,          # STAGE_DEFS[2] — Konveyör
    "stealth_config": 6,         # STEALTH_LEVEL_CONFIGS[6]
    "no_enemies": False,
}

# Bölüm 7: İkinci Arena (Industrial — fabrika güvenlik noktaları)
EASY_MODE_LEVELS[7] = {
    "name": "FABRİKA KATLIAM ALANI",
    "goal_score": 15000,
    "theme_index": 5,
    "speed_mult": 0.0,
    "desc": "Krom Muhafızlar ve devriye robotları. Gizlenebilirsen karma kazanırsın.",
    "music_file": "ara1.mp3",
    "type": "beat_arena",
    "arena_level_id": 7,
    "stealth_config": 7,         # Beat arena içinde stealth kameralar da aktif
}

# Bölüm 8: İstihbarat Odası — ana hedef: tablet + çip
EASY_MODE_LEVELS[8] = {
    "name": "İSTİHBARAT ODASI",
    "goal_score": 25000,
    "theme_index": 5,
    "speed_mult": 0.6,
    "desc": "Kırmızı kapının ardında tren tarifesi, şehir haritası ve Vasi'nin izi var.",
    "music_file": "ara1.mp3",
    "type": "mission_intel",     # intel_pickup() tetiklenecek
    "mission_stage": 5,          # STAGE_DEFS[5] — İstihbarat Odası
    "stealth_config": 8,         # STEALTH_LEVEL_CONFIGS[8]
    "no_enemies": False,
}

# Bölüm 9: Siyah Kapı + Tren İstasyonu
EASY_MODE_LEVELS[9] = {
    "name": "TREN İSTASYONU — KAÇIŞ",
    "goal_score": 35000,
    "theme_index": 5,
    "speed_mult": 1.1,
    "desc": "SANAYİCİLER LOJİSTİK treni 3 dakikaya kalkıyor. Konteynıra atla.",
    "music_file": "ara1.mp3",
    "type": "mission_stealth",
    "mission_stage": 7,          # STAGE_DEFS[7] — Tren İstasyonu
    "stealth_config": 9,
    "no_enemies": False,
}

EASY_MODE_LEVELS[10] = {
    "name": "HURDALIK BEKÇİSİ (ARES)",
    "goal_score": 50000,
    "theme_index": 3,
    "speed_mult": 1.3,
    "desc": "Bu hurdalıktan sadece biri çıkabilir.",
    "music_file": "final_boss.mp3",
    "type": "scrolling_boss",
    "no_enemies": False
}

# ── ACT 3: THE CITY - Entry (11-14) ───────────────────────────────────────
for i in range(11, 15):
    EASY_MODE_LEVELS[i] = {
        "name": f"ARKA SOKAKLAR {i-10}",
        "goal_score": 3000 * i,
        "theme_index": 0,
        "speed_mult": 2.0 + ((i-10) * 0.1),
        "desc": "Güvenlik tarayıcılarından kaç.",
        "music_file": "ara2.mp3",
        "type": "normal"
    }

# Bölüm 13: Üçüncü Arena (Şehir — arka sokak çatışması)
EASY_MODE_LEVELS[13] = {
    "name": "ARKA SOKAK ÇATIŞMASI",
    "goal_score": 40000,
    "theme_index": 0,
    "speed_mult": 0.0,
    "desc": "Güvenlik tarayıcılarının köründe bekleyen suç örgütü. Bruteler önce gel.",
    "music_file": "ara2.mp3",
    "type": "beat_arena",
    "arena_level_id": 13
}

# ── ACT 3: THE CITY - Downtown (15-23) ────────────────────────────────────
for i in range(15, 24):
    EASY_MODE_LEVELS[i] = {
        "name": f"NEON MEYDANI {i-14}",
        "goal_score": 4000 * i,
        "theme_index": 0,
        "speed_mult": 2.4 + ((i-14) * 0.05),
        "desc": "Şehrin kalbinde hız sınırını aş.",
        "music_file": "ara2.mp3",
        "type": "normal"
    }

# Bölüm 16: EGEMENLERİN MALİKANESİ — Devasa, oyuncuya bağlı kamera, tam gizlilik bölümü
# speed_mult=0.0 ZORUNLU → Kamera kendi kendine kaymaz, oyuncuya kilitlenir.
# Bu bölüm init_game()'de özel platform düzeni alır; rastgele platform üretilmez.
EASY_MODE_LEVELS[16] = {
    "name": "EGEMENLERİN MALİKANESİ",
    "goal_score": 0,              # Skor hedefi yok — çıkış koşulu: gizli kasaya ulaşmak
    "theme_index": 6,             # MALİKANE teması (loş sarı + koyu kırmızı)
    "speed_mult": 0.0,            # ÇOK KRİTİK: Kamera kendiliğinden kaymaz!
    "desc": "Bir Egemen'in özel korumalı malikanesi. Kimseye görünme. Kasayı bul.",
    "music_file": "ara2.mp3",
    "type": "manor_stealth",      # Özel tip — init_game ve update döngüsünde kontrol edilir
    "mission_stage": 8,           # STAGE_DEFS[8] — Malikane Sızma Görevi
    "stealth_config": 16,         # STEALTH_LEVEL_CONFIGS[16] — devasa konfigürasyon
    "no_enemies": True,           # Rastgele CursedEnemy üretilmesin — sadece ChromeGuard
    # Gizli kasanın koordinatları — exit_condition: area_reached kontrolü için
    "secret_safe_x": 3600,
    "secret_safe_y": 380,
    "secret_safe_radius": 80,
}

EASY_MODE_LEVELS[22] = {
    "name": "NEON MEYDANI KUŞATMASI",
    "goal_score": 90000,
    "theme_index": 0,
    "speed_mult": 0.0,
    "desc": "Neon meydanının ortasında dört dalga. En güçlü Bruteler seni bekliyor.",
    "music_file": "ara2.mp3",
    "type": "beat_arena",
    "arena_level_id": 22
}

EASY_MODE_LEVELS[19] = {
    "name": "YERALTI METROSU (REST)",
    "goal_score": 0,
    "theme_index": 4,
    "speed_mult": 0.0,
    "desc": "Bir sonraki dalga öncesi soluklan.",
    "music_file": "ara2.mp3",
    "type": "rest_area"
}

EASY_MODE_LEVELS[24] = {
    "name": "OTOBAN ÇIKIŞI",
    "goal_score": 100000,
    "theme_index": 0,
    "speed_mult": 3.0,
    "desc": "Nexus Kulesi'ne giden son köprü.",
    "music_file": "ara2.mp3",
    "type": "normal"
}

# ── ACT 4: NEXUS CORE (25-30) ─────────────────────────────────────────────
for i in range(25, 30):
    EASY_MODE_LEVELS[i] = {
        "name": f"GÜVENLİK DUVARI {i-24}",
        "goal_score": 5000 * i,
        "theme_index": 1,
        "speed_mult": 2.8,
        "desc": "Sistem çekirdeğine yetkisiz giriş.",
        "music_file": "boss2.mp3",
        "type": "normal"
    }

EASY_MODE_LEVELS[28] = {
    "name": "NEXUS ELİTLERİ (ARENA)",
    "goal_score": 140000,
    "theme_index": 1,
    "speed_mult": 0.0,
    "desc": "Sistem çekirdeğinin son savunma hattı. Üç dalga, beşi aşkın elit.",
    "music_file": "boss2.mp3",
    "type": "beat_arena",
    "arena_level_id": 28
}

EASY_MODE_LEVELS[30] = {
    "name": "SİSTEM YÖNETİCİSİ (VASİ)",
    "goal_score": 999999,
    "theme_index": 1,
    "speed_mult": 1.5,
    "desc": "Nihai Hakikat.",
    "music_file": "boss2.mp3",
    "type": "scrolling_boss",
    "no_enemies": True
}

# --- GENEL RENKLER ---
DARK_BLUE   = (5, 5, 10)
WHITE       = (220, 220, 220)
STAR_COLOR  = (100, 100, 100)
NEON_GREEN  = (0, 220, 80)
NEON_CYAN   = (0, 180, 220)
DARK_METAL  = (20, 20, 25)

# [TODO - PIXEL ART]: Oyuncu renkleri geçici. Sprite geldiğinde kaldırılacak.
PLAYER_NORMAL = (0, 200, 255)
PLAYER_DASH   = (255, 80, 80)
PLAYER_SLAM   = (200, 0, 200)

# --- BEAT 'EM UP / DÖVÜŞ ARENA AYARLARI ---
# Bu sabitler combat_system.py tarafından da import edilir.

ARENA_PLAYER_HP    = 100
ARENA_INV_DURATION = 0.8    # Hasar sonrası dokunulmazlık süresi (sn)

COMBO_WINDOW_SEC   = 1.2
MELEE_LIGHT_DAMAGE = 20
MELEE_HEAVY_DAMAGE = 40
MELEE_REACH_PX     = 80
MELEE_HEIGHT_PX    = 60

ARENA_SPEED_MULT   = 1.0

COMBAT_KEY_LIGHT   = "j"    # pygame.K_j
COMBAT_KEY_HEAVY   = "k"    # pygame.K_k

# --- OYUN FİZİĞİ ---
GRAVITY            = 1.0
SLAM_GRAVITY       = 5.0
JUMP_POWER         = 28
PLAYER_SPEED       = 10
MAX_JUMPS          = 2

DASH_SPEED         = 90
DASH_DURATION      = 18
# DASH_COOLDOWN ve SLAM_COOLDOWN_BASE kaldırıldı — yerini Stamina aldı.

# --- STAMINA MALİYETLERİ ---
# Yetenekler artık cooldown yerine bu kadar stamina tüketir.
COST_DASH          = 30   # Dash (Boşluk)
COST_SLAM          = 40   # Slam (S + zıplarken)
COST_HEAVY         = 20   # Ağır vuruş (K)
COST_LIGHT         = 10   # Hafif vuruş (J)

# --- STAMINA AYARLARI ---
PLAYER_MAX_STAMINA    = 100      # Başlangıç maksimum stamina
STAMINA_REGEN_RATE    = 18.0     # Saniyede dolum miktarı (birim/sn)
STAMINA_REGEN_DELAY   = 0.6      # Harcamadan sonra yeniden dolmaya başlama gecikmesi (sn)

# --- SİLAH AYARLARI (ALTIPATAR) ---
REVOLVER_MAX_BULLETS  = 6      # Tam şarjör kapasitesi
REVOLVER_DAMAGE       = 50     # Her merminin verdiği hasar
REVOLVER_COOLDOWN     = 0.4    # Her atış arasındaki bekleme (saniye)
REVOLVER_RELOAD_TIME  = 1.5    # Tam dolum süresi (saniye)
PLAYER_BULLET_SPEED   = 30     # Merminin piksel/frame hızı

# --- KAMERA ---
INITIAL_CAMERA_SPEED = 5
MAX_CAMERA_SPEED     = 18
SPEED_INCREMENT_RATE = 0.001
PLATFORM_MIN_WIDTH   = 100
PLATFORM_MAX_WIDTH   = 300
GAP_MIN              = 120
GAP_MAX              = 250
VERTICAL_GAP         = 180

PLATFORM_HEIGHTS = [
    LOGICAL_HEIGHT - 50,
    LOGICAL_HEIGHT - 50 - VERTICAL_GAP,
    LOGICAL_HEIGHT - 50 - 2 * VERTICAL_GAP,
    LOGICAL_HEIGHT - 50 - 3 * VERTICAL_GAP
]

PLAYER_SHAPES = ['circle', 'square', 'triangle', 'hexagon']

# --- UI RENKLERİ ---
CHAT_BG            = (0, 0, 0, 230)
CHAT_BORDER        = (0, 200, 0)
SPEAKER_NEXUS      = (0, 200, 0)
SPEAKER_SYSTEM     = (200, 0, 0)
TEXT_COLOR         = (200, 240, 200)

UI_BG_COLOR        = (8, 8, 12, 255)
UI_BORDER_COLOR    = (0, 130, 130)
BUTTON_COLOR       = (20, 30, 30)
BUTTON_HOVER_COLOR = (0, 70, 70)
BUTTON_TEXT_COLOR  = (160, 240, 240)
LOADING_BAR_BG     = (20, 20, 20)
LOADING_BAR_FILL   = (0, 220, 220)
LOCKED_BUTTON_COLOR= (25, 25, 25)
LOCKED_TEXT_COLOR  = (80, 80, 80)
PAUSE_OVERLAY_COLOR= (0, 0, 0, 180)

# --- DÜŞMAN RENKLERİ (Hitbox renkleri) ---
# [TODO - PIXEL ART]: Bunlar sadece hitbox teli olarak çiziliyor.
CURSED_PURPLE = (150, 0, 255)
CURSED_RED    = (255, 0, 50)
GLITCH_BLACK  = (10, 0, 10)

# --- LIMBO PROMPTLARI ---
LIMBO_VASIL_PROMPT = """
Sen VASİ'sin. Fragmentia sisteminin baş mimarı ve koruyucususun.
Durum: Oyuncu (İsimsiz) çok kötü bir karma ile oynadı, her şeyi yok etti ve sonunda iradesi kırıldı.
Şu an senin özel alanındasın (Sistem Çekirdeği).
Tavrın: Soğuk, hesapçı, hayal kırıklığına uğramış ama meraklı.
Oyuncuya neden bu kadar yıkıcı olduğunu sor. Onu tamamen silmek yerine neden buraya çektiğini ima et (Veri toplamak için).
Kısa ve gizemli konuş.
"""

LIMBO_ARES_PROMPT = """
Sen SAVAŞÇI ARES'sin. Eski dünyanın onurunu taşıyan bir gladyatörsün.
Durum: Oyuncu (İsimsiz) çok iyi/pasifist bir karma ile oynadı, kimseyi öldürmedi ama sonunda gücü yetmedi ve düştü.
Şu an senin özel alanındasın (Valhalla benzeri dijital bir arena).
Tavrın: Saygılı, babacan, güçlü ve cesaret verici.
Oyuncunun savaşmadan kazanma çabasını takdir et ama bunun Fragmentia'da yetersiz olduğunu söyle.
Kısa ve epik konuş.
"""

# =============================================================================
# ── YENİ EKLEMELER: GİZLİLİK & GÖREV SİSTEMİ SABİTLERİ ─────────────────────
# (mission_system.py ve stealth_system.py tarafından okunur)
# =============================================================================

# --- GİZLİLİK SİSTEMİ SABİTLERİ ---
STEALTH_VISION_RANGE    = 300    # px — varsayılan görüş menzili
STEALTH_VISION_ANGLE    = 80     # derece — görüş konisi açısı (toplam, ±40)
STEALTH_SUSPICION_BUILD = 1.5    # saniye başına şüphe dolum hızı (0..1)
STEALTH_SUSPICION_DECAY = 0.8    # görüş dışında şüphe azalma hızı
STEALTH_CAMERA_PERIOD   = 4.0    # saniye — kamera tam gidiş-dönüş süresi
STEALTH_ALERT_DURATION  = 12.0   # saniye — yüksek alarmın devam süresi
STEALTH_KARMA_INTERVAL  = 8.0    # saniye — kesintisiz gizlilik karma bonusu aralığı

# --- GÖREV SİSTEMİ SKOR EŞİKLERİ ---
# mission_system.py STAGE_DEFS ile tutarlı olmalı.
# main.py bu değerlere doğrudan bağımlı değil; yalnızca referans amaçlı.
MISSION_STAGE_SCORES = {
    0: 800,      # Stage 0: Çöplükte Uyanış çıkış skoru
    2: 15000,    # Stage 2: Konveyör Bant Alanı çıkış skoru
    7: 30000,    # Stage 7: Tren İstasyonu giriş eşiği
}

# --- KROM MUHAFIZ RENK SABİTLERİ ---
# stealth_system.ChromeGuard.draw() bu renkleri kullanır.
# [TODO - PIXEL ART]: Sprite geldiğinde bu renkler hitbox tel çizgisine dönüşür.
CHROME_GUARD_COLOR   = (150, 180, 200)   # Normal devriye rengi
CHROME_GUARD_ALERT   = (255, 30,  30)    # Alarm modu (kırmızı)
CHROME_GUARD_SUSPECT = (255, 180, 0)     # Şüphe modu (sarı)
CHROME_GUARD_STUN    = (100, 100, 100)   # Bayıltılmış (gri)

# --- GÖREV SEÇİM UI RENKLERİ ---
# main.py MISSION_CHOICE state'inde KarmaChoice ekranını çizerken kullanır.
CHOICE_BG_COLOR      = (0, 0, 0, 210)        # Yarı saydam overlay
CHOICE_BORDER_A      = (255, 60, 60)         # A seçeneği (riskli/ölümcül)
CHOICE_BORDER_B      = (60, 200, 120)        # B seçeneği (gizli/pasifist)
CHOICE_TEXT_COLOR    = (220, 220, 220)
CHOICE_KARMA_NEG     = (255, 80,  80)        # Karma düşüş rengi
CHOICE_KARMA_POS     = (80,  255, 120)       # Karma artış rengi
CHOICE_KARMA_NEUTRAL = (180, 180, 180)       # Karma değişimi yok

# --- OBJEKTİF HUD RENKLERİ ---
# main.py Step 12 HUD bloğunda mission_manager.get_active_objectives() ile kullanılır.
OBJECTIVE_TEXT_COLOR     = (160, 240, 160)   # Zorunlu hedef
OBJECTIVE_OPTIONAL_COLOR = (160, 160, 100)   # Opsiyonel hedef
OBJECTIVE_DONE_COLOR     = (80, 160, 80)     # Tamamlanan hedef (üstü çizili gösterilebilir)
OBJECTIVE_FONT_SIZE      = 22                # px

# --- MALİKANE GİZLİ SUİKAST SABİTLERİ ---
# stealth_system.ChromeGuard.stealth_kill() ve main.py F-tuşu mantığı için.
STEALTH_KILL_REACH_PX    = 90    # Suikast mesafesi (piksel)
STEALTH_KILL_SUSPICION_MAX = 0.5 # Bu değerin ALTINDA ise suikast mümkün
STEALTH_KILL_KARMA       = 1     # Sessiz suikastta karma değişimi (+1 = nötr/olumlu)

# Malikane haritası boyutu — init_game() platform üretimi için referans
MANOR_MAP_WIDTH  = 4000   # Çok geniş — oyuncu geri gidebilmeli
MANOR_MAP_HEIGHT = LOGICAL_HEIGHT