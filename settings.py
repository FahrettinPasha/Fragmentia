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
    "philosopher": "Hoş geldin 'İsimsiz'. Cebindeki boş kimlik kartı, bu şehirdeki en büyük özgürlüğündür.",
    "warrior": "Skorun yükseliyor... Egemenlerin dikkatini çekiyorsun. Kılıcın keskin mi?",
    "merchant": "SİSTEM HATASI: TÜCCAR PROTOKOLÜ DEVRE DIŞI.",
    "mystic": "Rüyalarımda cam kulelerin yıkıldığını görüyorum. Yama tutmamış bir zihin her şeyi değiştirebilir.",
    "guide": "Bu mağaradan çıkış var. Ama bedeli ağır. Hakikate hicret etmeye hazır mısın?"
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

# --- TEMALAR (PLACEHOLDER) ---
# [TODO - PIXEL ART]: Her tema için arkaplan spriteları/tileset buraya bağlanacak.
# Şimdilik sadece düz arka plan rengi kullanılıyor.
# theme_index sırası: 0:Neon, 1:Nexus, 2:Gutter, 3:Industrial, 4:Rest
THEMES = [
    # 0: NEON PAZARI
    {
        "name": "NEON PAZARI",
        "bg_color": (15, 15, 25),        # Düz arka plan
        "platform_color": (50, 50, 80),  # Düz platform rengi
        "border_color": (0, 200, 255),   # UI / çerçeve rengi
        "player_color": (255, 255, 255),
        "grid_color": (0, 0, 0)          # Kullanılmıyor (grid kaldırıldı)
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
    }
]

# --- 30 BÖLÜMLÜK HARİTA ---
EASY_MODE_LEVELS = {}

# ACT 1: THE GUTTER (1-5)
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

# ACT 2: INDUSTRIAL ZONE (6-10)
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

# ACT 3: THE CITY - Entry (11-14)
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

# ACT 3: THE CITY - Downtown (15-23)
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

# ACT 4: NEXUS CORE (25-30)
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
DARK_BLUE = (5, 5, 10)
WHITE = (220, 220, 220)
STAR_COLOR = (100, 100, 100)
NEON_GREEN = (0, 220, 80)
NEON_CYAN = (0, 180, 220)
DARK_METAL = (20, 20, 25)

# [TODO - PIXEL ART]: Oyuncu renkleri geçici. Sprite geldiğinde kaldırılacak.
PLAYER_NORMAL = (0, 200, 255)
PLAYER_DASH = (255, 80, 80)
PLAYER_SLAM = (200, 0, 200)

# --- OYUN FİZİĞİ (DEĞİŞMEDİ) ---
GRAVITY = 1.0
SLAM_GRAVITY = 5.0
JUMP_POWER = 28
PLAYER_SPEED = 10
MAX_JUMPS = 2

DASH_SPEED = 90
DASH_DURATION = 18
DASH_COOLDOWN = 60
SLAM_COOLDOWN_BASE = 100

# --- KAMERA ---
INITIAL_CAMERA_SPEED = 5
MAX_CAMERA_SPEED = 18
SPEED_INCREMENT_RATE = 0.001
PLATFORM_MIN_WIDTH = 100
PLATFORM_MAX_WIDTH = 300
GAP_MIN = 120
GAP_MAX = 250
VERTICAL_GAP = 180

PLATFORM_HEIGHTS = [
    LOGICAL_HEIGHT - 50,
    LOGICAL_HEIGHT - 50 - VERTICAL_GAP,
    LOGICAL_HEIGHT - 50 - 2 * VERTICAL_GAP,
    LOGICAL_HEIGHT - 50 - 3 * VERTICAL_GAP
]

PLAYER_SHAPES = ['circle', 'square', 'triangle', 'hexagon']

# --- UI RENKLERİ ---
CHAT_BG = (0, 0, 0, 230)
CHAT_BORDER = (0, 200, 0)
SPEAKER_NEXUS = (0, 200, 0)
SPEAKER_SYSTEM = (200, 0, 0)
TEXT_COLOR = (200, 240, 200)

UI_BG_COLOR = (8, 8, 12, 255)
UI_BORDER_COLOR = (0, 130, 130)
BUTTON_COLOR = (20, 30, 30)
BUTTON_HOVER_COLOR = (0, 70, 70)
BUTTON_TEXT_COLOR = (160, 240, 240)
LOADING_BAR_BG = (20, 20, 20)
LOADING_BAR_FILL = (0, 220, 220)
LOCKED_BUTTON_COLOR = (25, 25, 25)
LOCKED_TEXT_COLOR = (80, 80, 80)
PAUSE_OVERLAY_COLOR = (0, 0, 0, 180)

# --- DÜŞMAN RENKLERİ (Hitbox renkleri) ---
# [TODO - PIXEL ART]: Bunlar sadece hitbox teli olarak çiziliyor.
CURSED_PURPLE = (150, 0, 255)
CURSED_RED = (255, 0, 50)
GLITCH_BLACK = (10, 0, 10)

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