from settings import EASY_MODE_LEVELS

# --- BOSS SABİTLERİ ---
BULLET_SPEED = 8
BOSS_HEALTH = 1000
BOSS_DAMAGE = 10
BOSS_FIRE_RATE = 60
BOSS_INVULNERABILITY_TIME = 30

# --- LIMBO VE RENK TANIMLARI ---
LIMBO_VASIL_PROMPT = "Sen... buradasın. İraden kırıldı, ama sistem seni tamamen silmedi. Neden? Belki de hâlâ bir şansın var. Ya da belki bu, daha büyük bir planın parçası. Bu siyah boşluk, senin için bir ceza mı yoksa bir fırsat mı?"
LIMBO_ARES_PROMPT = "Ölümün bile seni kurtaramadı. Ama buradayız. Bu limbo, gerçekliğin çatlaklarından biri. Belki de burada, gerçek gücün ne olduğunu anlayacaksın. Hazır mısın?"

CURSED_PURPLE = (128, 0, 128)
GLITCH_BLACK = (20, 20, 30)
CURSED_RED = (200, 0, 0)

# --- BÖLÜM AYARLARI (LEVEL UPDATES) ---
# Gizli bölümleri ekle (11-15)
EASY_MODE_LEVELS.update({
    11: {'name': 'Karanlık Diriliş Yolu', 'goal_score': 60000, 'speed_mult': 1.6, 'theme_index': 0, 'type': 'normal', 'music_file': 'cyber_chase.mp3'},
    12: {'name': 'Vasi\'nin İzinde', 'goal_score': 75000, 'speed_mult': 1.7, 'theme_index': 1, 'type': 'normal', 'music_file': 'final_ascension.mp3'},
    13: {'name': 'Felsefi Geçit', 'goal_score': 90000, 'speed_mult': 1.8, 'theme_index': 2, 'type': 'normal', 'music_file': 'dark_ambient.mp3'},
    14: {'name': 'Gerçeklik Çatlağı', 'goal_score': 110000, 'speed_mult': 1.9, 'theme_index': 3, 'type': 'normal', 'music_file': 'synthwave.mp3'},
    15: { 
        'name': 'NİHAİ HAKİKAT',
        'goal_score': 100000,
        'theme_index': 2,
        'speed_mult': 1.4,
        'desc': 'Zaman dolana kadar dayan.',
        'music_file': 'boss2.mp3',
        'type': 'scrolling_boss',
        'no_enemies': True
    }
})

# --- BÖLÜM 10 AYARI ---
EASY_MODE_LEVELS[10] = {
    'name': 'YARGI GÜNÜ (Bölüm 10)',
    'goal_score': 100000, 
    'speed_mult': 0.0,    # Kamera durur (Boss fight)
    'theme_index': 1,     # Kırmızı Kule teması
    'type': 'boss_fight',
    'music_file': 'final_boss.mp3'
}