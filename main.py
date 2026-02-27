# main.py
from entities import BlankBackground, ParallaxBackground, Platform, Star, CursedEnemy, NPC, DroneEnemy, TankEnemy
from boss_entities import VasilCompanion, BossSpike, BossLightning
from boss_manager import BossManager
import pygame
import sys
import random
import math
import os
import json
import warnings
import numpy as np
import gc  # --- OPTİMİZASYON 2: Garbage Collector Kontrolü ---

# Gereksiz uyarıları gizle
warnings.filterwarnings("ignore", category=UserWarning, module='pygame.pkgdata')

from settings import *
from settings import STEALTH_KILL_REACH_PX, STEALTH_KILL_KARMA

# --- MODÜLER YAPI IMPORTLARI ---
from game_config import EASY_MODE_LEVELS, BULLET_SPEED, BOSS_HEALTH, BOSS_DAMAGE, BOSS_FIRE_RATE, BOSS_INVULNERABILITY_TIME
from game_config import LIMBO_VASIL_PROMPT, LIMBO_ARES_PROMPT, CURSED_PURPLE, GLITCH_BLACK, CURSED_RED
from auxiliary_systems import RestAreaManager, NexusHub, PhilosophicalCore, RealityShiftSystem, TimeLayerSystem
from auxiliary_systems import CombatPhilosophySystem, LivingSoundtrack, EndlessFragmentia, ReactiveFragmentia, LivingNPC
from auxiliary_systems import FragmentiaDistrict, PhilosophicalTitan, WarpLine
from drawing_utils import rotate_point, draw_legendary_revolver, draw_cinematic_overlay, draw_background_hero
from drawing_utils import draw_background_boss_silhouette, draw_npc_chat
from local_bosses import NexusBoss, AresBoss, VasilBoss, EnemyBullet

# --- GÜNCEL UTILS IMPORT (audio_manager eklendi) ---
from utils import generate_sound_effect, generate_ambient_fallback, generate_calm_ambient, load_sound_asset, draw_text, draw_animated_player, wrap_text, draw_text_with_shadow, get_silent_sound, audio_manager
from vfx import LightningBolt, FlameSpark, GhostTrail, SpeedLine, Shockwave, EnergyOrb, ParticleExplosion, ScreenFlash, SavedSoul
# YENİ: ParallaxBackground eklendi (BlankBackground yerine)
from entities import BlankBackground, ParallaxBackground, Platform, Star, CursedEnemy, NPC, DroneEnemy, TankEnemy
from ui_system import render_ui
from animations import CharacterAnimator, TrailEffect
from save_system import SaveManager
from story_system import StoryManager
from cutscene import AICutscene, IntroCutscene  # ← DEĞİŞİKLİK 1: IntroCutscene eklendi

# --- BEAT 'EM UP / DÖVÜŞ SİSTEMİ ---
from combat_system import (
    ComboSystem, BeatArenaManager, PlayerHealth, CombatHUD
)

# --- GİZLİLİK SİSTEMİ ---
from stealth_system import stealth_system

# --- Asset Paths Tanımı ---
asset_paths = {
    'font': 'assets/fonts/VCR_OSD_MONO.ttf',
    'sfx_bip': 'assets/sounds/bip.mp3',
    'sfx_glitch': 'assets/sounds/glitch.mp3',
    'sfx_awake': 'assets/sounds/awake.mp3',
    'npc_image': 'assets/images/npc_silhouette.png'}

# --- YENİ: BOSS MANAGER SİSTEMİ ---
boss_manager_system = BossManager()

# --- BEAT 'EM UP SİSTEMLERİ ---
combo_system  = ComboSystem()
beat_arena    = BeatArenaManager()
player_hp     = PlayerHealth(ARENA_PLAYER_HP)
combat_hud    = CombatHUD()

# --- OPTİMİZASYON 1: UI CACHE DEĞİŞKENLERİ ---
cached_ui_surface = None
last_score = -1
last_active_ui_elements = {}

def trigger_guardian_interruption():
    """Karma sıfırlandığında Vasi'nin araya girip savaşı durdurması."""
    global GAME_STATE, story_manager, all_enemies
    boss_manager_system.clear_all_attacks()
    all_enemies.empty()
    GAME_STATE = 'CHAT'
    story_manager.set_dialogue("VASI", "SİSTEM UYARISI: İrade bütünlüğü kritik seviyenin altında... Müdahale ediliyor.", is_cutscene=True)

# --- 1. SİSTEM VE EKRAN AYARLARI ---
pygame.init()
# Mikser başlatma işlemi artık audio_manager içinde yapılıyor.

current_display_w, current_display_h = LOGICAL_WIDTH, LOGICAL_HEIGHT
# --- OPTİMİZASYON 4: V-Sync Açık ---
screen = pygame.display.set_mode((current_display_w, current_display_h),
                                pygame.SCALED | pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE, vsync=1)
pygame.display.set_caption("FRAGMENTIA: Hakikat ve İhanet")
clock = pygame.time.Clock()

game_canvas = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
vfx_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)

# --- 2. SES AYARLARI ---
# Ses kanalları artık audio_manager üzerinden yönetiliyor.

# Ses dosyaları
DASH_SOUND = load_sound_asset("assets/sfx/dash.wav")
SLAM_SOUND = load_sound_asset("assets/sfx/slam.wav")
EXPLOSION_SOUND = get_silent_sound()

current_level_music = None
# --- OPTİMİZASYON 3: VFX Limiti Azaltıldı ---
MAX_VFX_COUNT = 100 # 200'den 100'e çekildi (CPU rahatlatma)
MAX_DASH_VFX_PER_FRAME = 5
METEOR_CORE = (255, 255, 200)
METEOR_FIRE = (255, 80, 0)

# --- 3. DURUM DEĞİŞKENLERİ ---
GAME_STATE = 'MENU'
vasil_companion = None
active_background = None # YENİ: Global Arka Plan Değişkeni (Eski city_bg)

# Varsayılan ayarlar (sadece ilk çalıştırma için)
game_settings = {
    'fullscreen': True,
    'res_index': 1,
    'fps_limit': 60,
    'fps_index': 1,
    'sound_volume': 0.7,
    'music_volume': 0.5,
    'effects_volume': 0.8
}
current_fps = 60

# --- SAVE VE AYAR YÜKLEME ---
save_manager = SaveManager()
game_settings = save_manager.get_settings()
# SES SİSTEMİNİ BAŞLAT VE AYARLARI UYGULA
audio_manager.update_settings(game_settings) 
# ---------------------------------------------------

story_manager = StoryManager()
philosophical_core = PhilosophicalCore()
reality_shifter = RealityShiftSystem()
time_layer = TimeLayerSystem()
combat_philosophy = CombatPhilosophySystem()
soundtrack = LivingSoundtrack()
endless_modes = EndlessFragmentia()
world_reactor = ReactiveFragmentia()

current_level_idx = 15
level_select_page = 0

loading_progress = 0.0
loading_logs = []
loading_timer = 0
loading_stage = 0
target_state_after_load = 'PLAYING'
fake_log_messages = [
    "Yapay Zeka Çekirdeği Başlatılıyor...",
    "NEXUS Protokolü Aktif...",
    "VRAM Tahsisi Yapılıyor...",
    "Bölüm Varlıkları Yükleniyor...",
    "Felsefi Matris Yükleniyor...",
    "Gerçeklik Stabilizasyonu...",
    "Zaman Katmanları Senkronize Ediliyor...",
    "NPC Bellek Bankası Hazırlanıyor...",
    "Dünya Tepki Sistemi Aktif...",
    "Sistem Hazır."
]

CURRENT_THEME = THEMES[0]
CURRENT_SHAPE = 'circle'
score = 0.0
high_score = 0
camera_speed = INITIAL_CAMERA_SPEED
player_x, player_y = 150.0, float(LOGICAL_HEIGHT - 300)
y_velocity = 0.0
is_jumping = is_dashing = is_slamming = False
slam_stall_timer = 0
slam_cooldown = 0
jumps_left = MAX_JUMPS
dash_timer = 0
dash_cooldown_timer = 0
screen_shake = 0
dash_particles_timer = 0
dash_angle = 0.0
dash_frame_counter = 0.0
character_state = 'idle'
slam_collision_check_frames = 0
active_damage_waves = []

active_player_speed = PLAYER_SPEED
active_dash_cd = DASH_COOLDOWN
active_slam_cd = SLAM_COOLDOWN_BASE
has_revived_this_run = False
has_talisman = False

level_15_timer = 0.0
finisher_active = False
finisher_state_timer = 0.0
finisher_type = None
level_15_cutscene_played = False

character_animator = CharacterAnimator()
trail_effects = []
last_trail_time = 0.0
TRAIL_INTERVAL = 3

all_platforms = pygame.sprite.Group()
all_enemies = pygame.sprite.Group()
all_vfx = pygame.sprite.Group()
stars = [Star(LOGICAL_WIDTH, LOGICAL_HEIGHT) for _ in range(120)]

npcs = []
current_npc = None
npc_conversation_active = False
npc_chat_input = ""
npc_chat_history = []
npc_show_cursor = True
npc_cursor_timer = 0
npc_typing_timer = 0

player_karma = 0
enemies_killed_current_level = 0
karma_notification_timer = 0
karma_notification_text = ""

rest_area_manager = RestAreaManager()

# NPC ekosistemi
npc_ecosystem = []
for i in range(50):
    npc = LivingNPC(i, random.randint(1, 5))
    npc_ecosystem.append(npc)

districts = []
for i in range(12):
    district = FragmentiaDistrict(i, random.choice(['small', 'medium', 'large']))
    districts.append(district)

boss_arenas = [
    PhilosophicalTitan('Plato Reborn', 'platonist', 8),
    PhilosophicalTitan('Nietzsche Incarnate', 'nietzschean', 9),
    PhilosophicalTitan('Camus Manifest', 'existentialist', 7),
    PhilosophicalTitan('Buddha Digital', 'buddhist', 10)
]

# --- YARDIMCI FONKSİYONLAR ---
def apply_display_settings():
    global screen, current_display_w, current_display_h
    target_res = AVAILABLE_RESOLUTIONS[game_settings['res_index']]

    if game_settings['fullscreen']:
        current_display_w, current_display_h = LOGICAL_WIDTH, LOGICAL_HEIGHT
        flags = pygame.SCALED | pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE
    else:
        current_display_w, current_display_h = target_res
        flags = pygame.DOUBLEBUF | pygame.HWSURFACE
    # Vsync=1 her zaman aktif
    screen = pygame.display.set_mode((current_display_w, current_display_h), flags, vsync=1)

def add_new_platform(start_x=None):
    if start_x is None:
        if len(all_platforms) > 0:
            rightmost = max(all_platforms, key=lambda p: p.rect.right)
            gap = random.randint(GAP_MIN, GAP_MAX)
            start_x = rightmost.rect.right + gap
        else:
            start_x = LOGICAL_WIDTH

    width = random.randint(PLATFORM_MIN_WIDTH, PLATFORM_MAX_WIDTH)
    y = random.choice(PLATFORM_HEIGHTS)
    new_plat = Platform(start_x, y, width, 50)
    all_platforms.add(new_plat)

    if current_level_idx in [10, 30]:
        return

    has_enemy = False
    lvl_props = EASY_MODE_LEVELS.get(current_level_idx, {})

    if not lvl_props.get("no_enemies") and width > 120 and random.random() < 0.4:
        enemy_roll = random.random()
        if current_level_idx >= 7 and enemy_roll < 0.15:
            enemy = TankEnemy(new_plat)
        elif current_level_idx >= 4 and enemy_roll < 0.35:
            drone_y = y - random.randint(50, 150)
            enemy = DroneEnemy(new_plat.rect.centerx, drone_y)
        else:
            enemy = CursedEnemy(new_plat)
        all_enemies.add(enemy)
        has_enemy = True

    if has_enemy:
        safe_gap = random.randint(150, 250)
        safe_start_x = new_plat.rect.right + safe_gap
        safe_width = random.randint(PLATFORM_MIN_WIDTH, PLATFORM_MAX_WIDTH)
        possible_heights = [h for h in PLATFORM_HEIGHTS if abs(h - y) <= VERTICAL_GAP]
        if not possible_heights:
            possible_heights = PLATFORM_HEIGHTS
        safe_y = random.choice(possible_heights)
        safe_plat = Platform(safe_start_x, safe_y, safe_width, 50)
        safe_plat.theme_index = CURRENT_THEME
        all_platforms.add(safe_plat)

def start_loading_sequence(next_state_override=None):
    global GAME_STATE, loading_progress, loading_logs, loading_timer, loading_stage, target_state_after_load
    GAME_STATE = 'LOADING'
    loading_progress = 0.0
    loading_logs = []
    loading_timer = 0
    loading_stage = 0
    target_state_after_load = next_state_override if next_state_override else 'PLAYING'
    global MAX_VFX_COUNT, MAX_DASH_VFX_PER_FRAME
    # --- OPTİMİZASYON: Yükleme ekranında çöp topla ---
    gc.collect() 
    MAX_VFX_COUNT = 100
    MAX_DASH_VFX_PER_FRAME = 5

def start_story_chapter(chapter_id):
    global GAME_STATE, current_level_idx, player_x, player_y, camera_speed, CURRENT_THEME, y_velocity
    global active_background
    
    story_manager.load_chapter(chapter_id)
    GAME_STATE = 'CHAT'

    if chapter_id == 0:
        all_platforms.empty()
        all_enemies.empty()
        all_vfx.empty()
        base_plat = Platform(0, LOGICAL_HEIGHT - 100, LOGICAL_WIDTH, 100, theme_index=2)
        all_platforms.add(base_plat)
        bed1 = Platform(400, LOGICAL_HEIGHT - 180, 200, 30, theme_index=2)
        bed2 = Platform(800, LOGICAL_HEIGHT - 180, 200, 30, theme_index=2)
        all_platforms.add(bed1)
        all_platforms.add(bed2)
        player_x, player_y = 200.0, float(LOGICAL_HEIGHT - 250)
        y_velocity = 0
        camera_speed = 0
        CURRENT_THEME = THEMES[2]
        active_background = ParallaxBackground(
            f"{BG_DIR}/gutter_far.png", speed_mult=0.0)


def init_rest_area():
    global npcs, camera_speed, CURRENT_THEME, player_karma
    camera_speed = 0
    CURRENT_THEME = THEMES[4]
    all_platforms.empty()
    platform_width = 400
    gap = 200
    npc_spawn_index = 0

    for i in range(len(NPC_PERSONALITIES)):
        personality = NPC_PERSONALITIES[i]
        name = NPC_NAMES[i]
        color = NPC_COLORS[i]
        if personality == "merchant": continue
        if personality == "warrior" and player_karma <= 0: continue

        x = npc_spawn_index * (platform_width + gap) + 200
        y = LOGICAL_HEIGHT - 100
        platform = Platform(x, y, platform_width, 50, theme_index=4)
        all_platforms.add(platform)
        npc_x = x + platform_width // 2
        npc_y = y - 80
        prompt = NPC_PROMPTS.get(personality, "...")
        npc = NPC(npc_x, npc_y, name, color, personality, prompt)
        if personality == "philosopher":
            npc.talk_radius = 250
        npcs.append(npc)
        npc_spawn_index += 1

    center_x = (npc_spawn_index * (platform_width + gap)) + 200
    center_platform = Platform(center_x, LOGICAL_HEIGHT - 150, 600, 60, theme_index=4)
    all_platforms.add(center_platform)

def init_limbo():
    global player_x, player_y, y_velocity, camera_speed, CURRENT_THEME
    global all_platforms, all_enemies, all_vfx, npcs, game_canvas
    global current_level_idx, boss_manager_system
    global active_background

    boss_manager_system.reset()
    current_level_idx = 99
    all_platforms.empty()
    all_enemies.empty()
    all_vfx.empty()
    npcs.clear()
    camera_speed = 0
    y_velocity = 0
    CURRENT_THEME = THEMES[2]
    
    # Limbo için Arka Plan (karanlık gutter teması)
    active_background = ParallaxBackground(
        f"{BG_DIR}/gutter_far.png", speed_mult=0.0)  # speed=0 → sabit arka plan

    center_plat = Platform(LOGICAL_WIDTH//2 - 400, LOGICAL_HEIGHT - 150, 800, 50, theme_index=4)
    all_platforms.add(center_plat)
    player_x = LOGICAL_WIDTH // 2 - 100
    player_y = LOGICAL_HEIGHT - 250

    karma = save_manager.get_karma()
    npc_name = ""
    npc_prompt = ""
    npc_color = (255, 255, 255)
    personality = "guide"

    if karma >= 0:
        npc_name = "SAVAŞÇI ARES"
        npc_prompt = LIMBO_ARES_PROMPT
        npc_color = (255, 50, 50)
        personality = "warrior"
    else:
        npc_name = "VASİ"
        npc_prompt = LIMBO_VASIL_PROMPT
        npc_color = (0, 255, 100)
        personality = "philosopher"

    limbo_npc = NPC(
        x=LOGICAL_WIDTH // 2 + 100,
        y=LOGICAL_HEIGHT - 230,
        name=npc_name,
        color=npc_color,
        personality_type=personality,
        prompt=npc_prompt
    )
    limbo_npc.ai_active = True
    npcs.append(limbo_npc)
    audio_manager.stop_music()

def init_redemption_mode():
    global player_x, player_y, y_velocity, camera_speed, CURRENT_THEME
    global all_platforms, all_enemies, all_vfx, npcs, current_level_idx
    global has_talisman, boss_manager_system

    current_level_idx = 11
    has_talisman = True
    all_platforms.empty()
    all_enemies.empty()
    all_vfx.empty()
    npcs.clear()
    boss_manager_system.reset()
    CURRENT_THEME = THEMES[0]
    start_plat = Platform(0, LOGICAL_HEIGHT - 100, 600, 50)
    all_platforms.add(start_plat)
    player_x = 100
    player_y = LOGICAL_HEIGHT - 250
    camera_speed = INITIAL_CAMERA_SPEED * 1.5
    y_velocity = 0
    
    sound = load_sound_asset("assets/music/cyber_chase.mp3", generate_ambient_fallback, 0.8)
    audio_manager.play_music(sound)

def init_genocide_mode():
    global player_x, player_y, y_velocity, camera_speed, CURRENT_THEME
    global all_platforms, all_enemies, all_vfx, npcs, current_level_idx
    global vasil_companion, boss_manager_system

    current_level_idx = 11
    all_platforms.empty()
    all_enemies.empty()
    all_vfx.empty()
    npcs.clear()
    boss_manager_system.reset()
    CURRENT_THEME = THEMES[1]
    start_plat = Platform(0, LOGICAL_HEIGHT - 100, 600, 50)
    all_platforms.add(start_plat)
    player_x = 100
    player_y = LOGICAL_HEIGHT - 250
    camera_speed = INITIAL_CAMERA_SPEED * 1.6
    y_velocity = 0
    vasil_companion = None
    
    sound = load_sound_asset("assets/music/final_ascension.mp3", generate_ambient_fallback, 0.8)
    audio_manager.play_music(sound)


def start_npc_conversation(npc):
    global current_npc, npc_conversation_active, npc_chat_history, GAME_STATE
    current_npc = npc
    npc_conversation_active = True
    npc_chat_input = ""
    npc_chat_history = []
    greeting = npc.start_conversation()
    npc_chat_history.append({"speaker": npc.name, "text": greeting})
    GAME_STATE = 'NPC_CHAT'

def init_game():
    global player_x, player_y, y_velocity, score, camera_speed, jumps_left
    global is_jumping, is_dashing, is_slamming, dash_timer, dash_cooldown_timer, slam_stall_timer, slam_cooldown
    global CURRENT_THEME, CURRENT_SHAPE, screen_shake, dash_particles_timer, dash_angle, dash_frame_counter
    global character_state, trail_effects, last_trail_time, slam_collision_check_frames, active_damage_waves
    global CURRENT_THEME, current_level_music, npcs, current_npc, npc_conversation_active
    global player_karma, enemies_killed_current_level, karma_notification_timer, karma_notification_text
    global active_player_speed, active_dash_cd, active_slam_cd
    global has_revived_this_run, has_talisman
    global boss_manager_system, vasil_companion
    global level_15_timer, finisher_active, finisher_state_timer, finisher_type, level_15_cutscene_played
    global active_background # Global active_background
    global cached_ui_surface, last_score # UI Cache
    global combo_system, beat_arena, player_hp

    # --- OPTİMİZASYON: Oyun sırasında GC'yi kapat ---
    gc.disable()
    
    cached_ui_surface = None
    last_score = -1

    lvl_config = EASY_MODE_LEVELS.get(current_level_idx, EASY_MODE_LEVELS[1])

    # --- ARKA PLAN SEÇİMİ ---
    # Tema indeksine göre parallax katman dosyası belirlenir.
    # Dosya yoksa ParallaxBackground sessizce boş çizer (fallback).
    theme_idx  = lvl_config.get('theme_index', 0)
    theme_name = THEMES[theme_idx % len(THEMES)].get('name', 'unknown').lower()

    # Tema → arka plan dosya adı eşlemesi
    # Pixel artist klasöre dosya eklediğinde otomatik devreye girer.
    _BG_MAP = {
        2: "gutter",       # MİDE (The Gutter)
        3: "industrial",   # Dökümhane
        0: "neon_city",    # Neon Pazarı
        1: "nexus",        # Nexus Çekirdeği
        4: "safe_zone",    # Güvenli Bölge
    }
    bg_key = _BG_MAP.get(theme_idx, "neon_city")

    # Katmanları oluştur — dosya yoksa BlankBackground gibi davranır
    active_background = ParallaxBackground(
        f"{BG_DIR}/{bg_key}_far.png",
        speed_mult=BG_LAYER_FAR_SPEED
    )
    # Orta ve yakın katman için de aynı nesneyi oluşturmak istiyorsan:
    # active_bg_mid  = ParallaxBackground(f"{BG_DIR}/{bg_key}_mid.png",  BG_LAYER_MID_SPEED)
    # active_bg_near = ParallaxBackground(f"{BG_DIR}/{bg_key}_near.png", BG_LAYER_NEAR_SPEED)
    # Şimdilik tek katman; pixel art eklenince yukarıdaki satırlar açılacak.


    if current_level_idx < 11:
        has_talisman = False
        vasil_companion = None
        has_revived_this_run = False

    active_player_speed = PLAYER_SPEED
    active_dash_cd = DASH_COOLDOWN
    active_slam_cd = SLAM_COOLDOWN_BASE
    boss_manager_system.reset()
    # --- DÖVÜŞ SİSTEMİ SIFIRLA ---
    combo_system.reset()
    beat_arena.reset()
    player_hp = PlayerHealth(ARENA_PLAYER_HP)
    npcs.clear()
    current_npc = None
    npc_conversation_active = False
    npc_chat_input = ""
    npc_chat_history = []

    if lvl_config.get('type') == 'rest_area':
        camera_speed = 0
        CURRENT_THEME = THEMES[4]
        init_rest_area()
        player_x, player_y = 200.0, float(LOGICAL_HEIGHT - 180)
        y_velocity = 0
        music_file = random.choice(REST_AREA_MUSIC) if REST_AREA_MUSIC else "calm_ambient.mp3"
        
        current_level_music = load_sound_asset(f"assets/music/{music_file}", generate_calm_ambient, 0.6)
        audio_manager.play_music(current_level_music)

    elif lvl_config.get('type') == 'beat_arena':
        # --- BEAT 'EM UP ARENA BAŞLATMA ---
        camera_speed = 0   # Kamera durur — platform kaymaz
        CURRENT_THEME = THEMES[theme_idx]
        player_x, player_y = 200.0, float(LOGICAL_HEIGHT - 180)
        y_velocity = 0
        music_file = lvl_config.get('music_file', 'dark_ambient.mp3')
        current_level_music = load_sound_asset(f"assets/music/{music_file}", generate_ambient_fallback, 1.0)
        audio_manager.play_music(current_level_music)
        # Düz zemin + yan duvar platformları
        all_platforms.empty()
        floor_plat = Platform(0, LOGICAL_HEIGHT - 80, LOGICAL_WIDTH, 80, theme_index=theme_idx)
        all_platforms.add(floor_plat)
        # Arena henüz başlatılmadı — PLAYING loop içinde start() çağrılacak
        beat_arena.reset()

    elif lvl_config.get('type') == 'boss_fight':
        pass
    elif lvl_config.get('type') == 'manor_stealth':
        # ─────────────────────────────────────────────────────────────────
        # MALİKANE SIZDIRMA — camera_speed=0, 2D kameraya kilitli
        # ─────────────────────────────────────────────────────────────────
        camera_speed = 0
        CURRENT_THEME = THEMES[theme_idx]
        player_x, player_y = 120.0, float(LOGICAL_HEIGHT + 870)   # zemin kat (Y_GROUND - player_height)
        y_velocity = 0
        music_file = lvl_config.get('music_file', 'dark_ambient.mp3')
        current_level_music = load_sound_asset(
            f"assets/music/{music_file}", generate_ambient_fallback, 0.5
        )
        audio_manager.play_music(current_level_music)

        # ══════════════════════════════════════════════════════════════════
        # MALİKANE BİNA PLANI
        # ──────────────────────────────────────────────────────────────────
        #  Harita: 3200px geniş × ~2200px yüksek  (yukarı doğru büyür)
        #
        #  Koordinat sistemi:  Y = LOGICAL_HEIGHT + offset (büyük Y → aşağı)
        #  Oyuncu başlangıcı:  x=120,  y=LOGICAL_HEIGHT+900  (zemin kat)
        #  Gizli Kasa hedefi:  x≈2900, y=LOGICAL_HEIGHT-200  (çatı katta)
        #
        #  KAT DÜZENİ (yukarıdan aşağıya):
        #   Çatı Terası  : Y_BASE - 200  (kat 4)
        #   2. Kat        : Y_BASE + 200  (kat 3)
        #   1. Kat        : Y_BASE + 600  (kat 2)
        #   Zemin Kat     : Y_BASE + 900  (kat 1 / başlangıç)
        #
        #  MERDIVEN YERLERİ:
        #   Sol merdiven  : x≈200  — zemin → 1.kat → 2.kat
        #   Orta merdiven : x≈1400 — 1.kat → 2.kat
        #   Sağ merdiven  : x≈2400 — 2.kat → çatı
        #   Havalandırma  : x≈1800 — 2.kat içindeki kısa bağlantı
        # ══════════════════════════════════════════════════════════════════
        all_platforms.empty()
        _ti  = theme_idx
        _LH  = LOGICAL_HEIGHT       # 1080

        # Kat Y koordinatları (platform üst yüzeyi)
        Y_GROUND = _LH + 900     # Zemin kat zemini
        Y_F1     = _LH + 600     # 1. Kat
        Y_F2     = _LH + 200     # 2. Kat
        Y_ROOF   = _LH - 200     # Çatı terası / Gizli Kasa katı

        T = 22     # Platform kalınlığı
        W = 20     # Duvar kalınlığı

        # ─── DIŞ YAPI — sol ve sağ duvar ─────────────────────────────────
        # Sol dış duvar  (x=40,  y=Y_ROOF → Y_GROUND)
        all_platforms.add(Platform(40, Y_ROOF, W, Y_GROUND - Y_ROOF + T, theme_index=_ti))
        # Sağ dış duvar  (x=3180, y=Y_ROOF → Y_GROUND)
        all_platforms.add(Platform(3180, Y_ROOF, W, Y_GROUND - Y_ROOF + T, theme_index=_ti))

        # ─── ZEMİN KAT (Y=Y_GROUND) ─────────────────────────────────────
        # Giriş holü  : x=60 → 900  (oyuncu buradan başlar)
        all_platforms.add(Platform(60,   Y_GROUND, 840, T, theme_index=_ti))
        # İç duvar 1  : x=900, zemin kattan 1.kata uzanır (kapı yok → merdiven gerekli)
        all_platforms.add(Platform(900,  Y_F1 + T, W, Y_GROUND - Y_F1, theme_index=_ti))
        # Güvenlik Odası : x=920 → 1900
        all_platforms.add(Platform(920,  Y_GROUND, 980, T, theme_index=_ti))
        # İç duvar 2  : x=1900
        all_platforms.add(Platform(1900, Y_F1 + T, W, Y_GROUND - Y_F1, theme_index=_ti))
        # Depo         : x=1920 → 3160
        all_platforms.add(Platform(1920, Y_GROUND, 1260, T, theme_index=_ti))

        # ─── ZEMİN KAT MERDİVENLERİ (zemin → 1. kat) ────────────────────
        # Sol merdiven: x=100–200 bölgesinde 4 basamak, 75px aralıklı
        _step_y = Y_GROUND
        for _s in range(5):
            all_platforms.add(Platform(120 + _s * 90, _step_y - (_s + 1) * 60, 110, T, theme_index=_ti))
        # Sağ merdiven (depo → 1. kata): x≈2700–2900
        _step_y = Y_GROUND
        for _s in range(5):
            all_platforms.add(Platform(2620 + _s * 90, _step_y - (_s + 1) * 60, 110, T, theme_index=_ti))

        # ─── 1. KAT (Y=Y_F1) ─────────────────────────────────────────────
        # Sol bölüm   : x=60 → 1300  (kütüphane)
        all_platforms.add(Platform(60,   Y_F1, 1240, T, theme_index=_ti))
        # İç duvar 1a : x=1300 (1. kattaki kapı bölücü)
        all_platforms.add(Platform(1300, Y_F2 + T, W, Y_F1 - Y_F2, theme_index=_ti))
        # Sağ bölüm   : x=1320 → 3160  (ofis/güvenlik merkezi)
        all_platforms.add(Platform(1320, Y_F1, 1860, T, theme_index=_ti))

        # ─── 1. KAT → 2. KAT MERDİVENLERİ ───────────────────────────────
        # Orta merdiven (x≈1380–1580)
        _step_y = Y_F1
        for _s in range(4):
            all_platforms.add(Platform(1370 + _s * 100, _step_y - (_s + 1) * 65, 120, T, theme_index=_ti))
        # Sağ merdiven (x≈2800–3000)
        _step_y = Y_F1
        for _s in range(4):
            all_platforms.add(Platform(2810 + _s * 90, _step_y - (_s + 1) * 65, 110, T, theme_index=_ti))

        # ─── 2. KAT (Y=Y_F2) ─────────────────────────────────────────────
        # Tüm 2. kat zemini: x=60 → 3160 (geniş açık alan + havalandırma kanalları)
        all_platforms.add(Platform(60,   Y_F2, 3120, T, theme_index=_ti))
        # Havalandırma rafları (atlama taşları)
        all_platforms.add(Platform(400,  Y_F2 - 160, 200, T, theme_index=_ti))
        all_platforms.add(Platform(700,  Y_F2 - 280, 200, T, theme_index=_ti))
        all_platforms.add(Platform(1000, Y_F2 - 160, 200, T, theme_index=_ti))
        all_platforms.add(Platform(1800, Y_F2 - 160, 200, T, theme_index=_ti))
        all_platforms.add(Platform(2100, Y_F2 - 280, 200, T, theme_index=_ti))
        all_platforms.add(Platform(2500, Y_F2 - 160, 200, T, theme_index=_ti))
        # İç bölücü duvar (sunucu odası girişi)
        all_platforms.add(Platform(2200, Y_ROOF + T, W, Y_F2 - Y_ROOF, theme_index=_ti))

        # ─── 2. KAT → ÇATI MERDİVENLERİ ─────────────────────────────────
        # Sağ taraf yüksek merdiven (x≈2500–2800)
        _step_y = Y_F2
        for _s in range(5):
            all_platforms.add(Platform(2480 + _s * 80, _step_y - (_s + 1) * 80, 100, T, theme_index=_ti))

        # ─── ÇATI TERASI / GİZLİ KASA KATI (Y=Y_ROOF) ───────────────────
        # Sol çatı terası: x=60 → 1800
        all_platforms.add(Platform(60,   Y_ROOF, 1740, T, theme_index=_ti))
        # Ara boşluk (havalandırma kaçış penceresi): x=1800–2000 arası açık
        # Sağ çatı (kasa odası): x=2000 → 3160
        all_platforms.add(Platform(2000, Y_ROOF, 1180, T, theme_index=_ti))
        # Kasa platformu (hedef): oyuncu buraya ulaşınca bölüm biter
        # secret_safe_x=2900, secret_safe_y≈Y_ROOF-60 ile eşleşir
        all_platforms.add(Platform(2720, Y_ROOF - 140, 380, T + 8, theme_index=_ti))  # KASA YÜKSELTİSİ

    elif lvl_config.get('type') == 'scrolling_boss':
        mult = lvl_config.get('speed_mult', 1.0)
        camera_speed = (INITIAL_CAMERA_SPEED * 1.25) * mult
        CURRENT_THEME = THEMES[theme_idx]
        player_x, player_y = 150.0, float(LOGICAL_HEIGHT - 300)
        music_file = lvl_config.get('music_file', 'dark_ambient.mp3')
        
        current_level_music = load_sound_asset(f"assets/music/{music_file}", generate_ambient_fallback, 1.0)
        audio_manager.play_music(current_level_music)
        
        all_platforms.empty()
        start_plat = Platform(0, LOGICAL_HEIGHT - 50, 400, 50)
        all_platforms.add(start_plat)

        karma = save_manager.get_karma()
        boss = None
        boss_spawn_x = LOGICAL_WIDTH - 300
        if karma <= -20:
            boss = AresBoss(boss_spawn_x, LOGICAL_HEIGHT - 200)
        elif karma >= 20:
            boss = VasilBoss(boss_spawn_x, 100)
        else:
            boss = NexusBoss(boss_spawn_x, LOGICAL_HEIGHT - 400)

        if boss:
            boss.ignore_camera_speed = True
            all_enemies.add(boss)
    else:
        mult = lvl_config.get('speed_mult', 1.0)
        if current_level_idx == 10 and mult <= 0.1:
            mult = 1.4
        camera_speed = (INITIAL_CAMERA_SPEED * 1.25) * mult
        CURRENT_THEME = THEMES[theme_idx]
        player_x, player_y = 150.0, float(LOGICAL_HEIGHT - 300)
        music_file = lvl_config.get('music_file', 'dark_ambient.mp3')
        
        current_level_music = load_sound_asset(f"assets/music/{music_file}", generate_ambient_fallback, 1.0)
        audio_manager.play_music(current_level_music)

        all_platforms.empty()
        start_plat = Platform(0, LOGICAL_HEIGHT - 50, 400, 50)
        all_platforms.add(start_plat)
        current_right = 400
        while current_right < LOGICAL_WIDTH + 200:
            add_new_platform()
            if len(all_platforms) > 0:
                current_right = max(p.rect.right for p in all_platforms)
            else:
                current_right += 200

        if current_level_idx == 30:
            karma = save_manager.get_karma()
            boss = None
            if karma <= -20:
                boss = AresBoss(LOGICAL_WIDTH - 300, LOGICAL_HEIGHT - 200)
            elif karma >= 20:
                boss = VasilBoss(LOGICAL_WIDTH // 2, 100)
            else:
                boss = NexusBoss(LOGICAL_WIDTH - 300, LOGICAL_HEIGHT - 400)
            if boss:
                boss.ignore_camera_speed = True
                all_enemies.add(boss)

    if current_level_idx == 30:
        for e in all_enemies:
            if hasattr(e, 'health'):
                e.max_health = 50000
                e.health = 50000

    y_velocity = score = dash_timer = dash_cooldown_timer = screen_shake = slam_stall_timer = slam_cooldown = 0
    is_jumping = is_dashing = is_slamming = False
    jumps_left = MAX_JUMPS
    dash_particles_timer = 0
    dash_angle = 0.0
    dash_frame_counter = 0.0
    character_state = 'idle'
    slam_collision_check_frames = 0
    active_damage_waves.clear()
    trail_effects.clear()
    last_trail_time = 0.0
    player_karma = save_manager.get_karma()
    enemies_killed_current_level = 0
    karma_notification_timer = 0
    CURRENT_SHAPE = random.choice(PLAYER_SHAPES)
    all_enemies.empty()
    all_vfx.empty()
    character_animator.__init__()

    # --- GİZLİLİK SİSTEMİ: Bölüm düzenini yükle ---
    stealth_system.setup_level(current_level_idx)

    # --- MALİKANE: Önbelleğe alınmış bayrakları temizle ---
    # goal_score=0 olan manor_stealth bölümlerinde önceki çalışmadan kalan
    # "area_secret_safe" bayrağı anlık kazanmayı tetikleyebilir.
    if lvl_config.get('type') == 'manor_stealth':
        from mission_system import mission_manager
        mission_manager.set_flag("area_secret_safe", False)

def main():
    global GAME_STATE
    GAME_STATE = 'MENU'
    run_game_loop()

def run_game_loop():
    dragging_slider = None
    global GAME_STATE, loading_timer, loading_logs, loading_stage, target_state_after_load
    global score, camera_speed, player_x, player_y, y_velocity, is_jumping, is_dashing, is_slamming
    global slam_stall_timer, slam_cooldown, jumps_left, dash_timer, dash_cooldown_timer
    global screen_shake, character_state, current_level_idx, high_score
    global dash_vx, dash_vy, dash_particles_timer, dash_angle, dash_frame_counter
    global slam_collision_check_frames, active_damage_waves, trail_effects, last_trail_time
    global CURRENT_THEME, CURRENT_SHAPE, loading_progress, frame_count
    global current_npc, npc_conversation_active, npc_chat_input, npc_chat_history
    global npc_show_cursor, npc_cursor_timer, npc_typing_timer, npcs
    global active_ui_elements
    global player_karma, enemies_killed_current_level, karma_notification_timer, karma_notification_text
    global active_player_speed, active_dash_cd, active_slam_cd
    global has_revived_this_run, has_talisman
    global level_select_page, vasil_companion
    global boss_manager_system
    global level_15_timer, finisher_active, finisher_state_timer, finisher_type, level_15_cutscene_played
    global game_settings
    global active_background
    global cached_ui_surface, last_score, last_active_ui_elements
    global combo_system, beat_arena, player_hp, combat_hud

    is_super_mode = False
    # Malikane bölümü için kamera X ve Y ofseti (oyuncuyu ekranın ortasında tutar)
    manor_camera_offset_x = 0
    manor_camera_offset_y = 0
    terminal_input = ""
    terminal_status = "KOMUT BEKLENİYOR..."
    active_ui_elements = {}

    # Oyuncunun baktığı yön (+1 sağ, -1 sol).
    # Durduğunda son hareket yönünü korur — sprite doğru tarafa bakar.
    player_direction = 1

    # ── SPRITE DEBUG MODU ────────────────────────────────────────────────────
    # True  → Her karede konsolda koordinat/sprite bilgisi yazdırır +
    #          karakterin üstüne kırmızı hitbox kare çizer +
    #          sol üst köşede tüm sprite sheet'i gösterir.
    # False → Üretim modu, hiçbir debug çıktısı olmaz.
    # Sprite görünmüyorsa True yap, sorunu bul, sonra False yap.
    DEBUG_SPRITE = True
    _debug_print_counter = 0   # Her karede değil, 60 karede bir yazdır

    # Sprite sheet önbelleği — her karede diskten yüklemekten kaçınmak için.
    # pygame.image.load() döngü içinde çağrılırsa FPS 1-2'ye düşer!
    # None → ilk karede bir kez yüklenir, sonra aynı nesne kullanılır.
    _test_sheet = None
    _test_sheet_path = "assets/sprites/player/player_sheet.png"

    # ── DIRECT SPRITE TEST ───────────────────────────────────────────────────
    # Animasyon sistemi tamamen devre dışı — sheet'in ilk karesini (64×64)
    # doğrudan player_x / player_y konumuna blit eder.
    # Sprite görünüyorsa sistem çalışıyor, sorun animasyon katmanındadır.
    # Sprite hâlâ görünmüyorsa sorun dosya yolu veya çizim sırasındadır.
    #
    # Aktif etmek → DIRECT_SPRITE_TEST = True
    # Kapatmak   → DIRECT_SPRITE_TEST = False
    DIRECT_SPRITE_TEST = True
    _direct_sprite     = None          # Önbellek — döngü içinde yeniden yüklenmez
    _direct_sprite_path = "assets/sprites/player/player_sheet.png"
    _direct_sprite_size = (64, 64)     # Oyuncuya blit edilecek boyut

    # ── DEBUG TOGGLE BUTONU ──────────────────────────────────────────────────
    # Oyun esnasında sol alt köşede küçük buton.
    # Tıklanınca DEBUG_SPRITE ve DIRECT_SPRITE_TEST birlikte toggle edilir.
    _DEBUG_BTN_RECT  = pygame.Rect(10, LOGICAL_HEIGHT - 36, 120, 26)
    _debug_btn_font  = pygame.font.Font(None, 20)
    _debug_btn_hover = False
    # ────────────────────────────────────────────────────────────────────────

    running = True
    last_time = pygame.time.get_ticks()
    frame_count = 0
    current_level_idx = 15

    CURRENT_THEME = THEMES[0]
    CURRENT_SHAPE = 'circle'
    score = 0.0
    high_score = 0
    camera_speed = INITIAL_CAMERA_SPEED
    player_x, player_y = 150.0, float(LOGICAL_HEIGHT - 300)
    y_velocity = 0.0
    is_jumping = is_dashing = is_slamming = False
    jumps_left = MAX_JUMPS
    dash_timer = dash_cooldown_timer = 0
    screen_shake = 0
    dash_particles_timer = 0
    dash_angle = 0.0
    dash_frame_counter = 0.0
    character_state = 'idle'
    slam_collision_check_frames = 0
    active_damage_waves.clear()
    trail_effects.clear()
    last_trail_time = 0.0
    level_15_timer = 0.0
    finisher_active = False
    finisher_state_timer = 0.0
    finisher_type = None
    level_15_cutscene_played = False
    boss_manager_system.reset()
    vasil_companion = None
    active_background = None

    while running:
        current_time = pygame.time.get_ticks()
        dt = (current_time - last_time) / 1000.0
        dt = min(dt, 1.0 / 30.0)
        last_time = current_time
        time_ms = current_time
        frame_count += 1
        frame_mul = max(0.001, dt) * 60.0

        raw_mouse_pos = pygame.mouse.get_pos()
        scale_x = LOGICAL_WIDTH / screen.get_width()
        scale_y = LOGICAL_HEIGHT / screen.get_height()
        mouse_pos = (raw_mouse_pos[0] * scale_x, raw_mouse_pos[1] * scale_y)
        _debug_btn_hover = _DEBUG_BTN_RECT.collidepoint(mouse_pos)
        
        if active_background:
            active_background.update(camera_speed)

        if frame_count % 30 == 0:
            if len(all_vfx) > MAX_VFX_COUNT:
                 sprites = list(all_vfx.sprites())
                 for sprite in sprites[:20]:
                     sprite.kill()

        events = pygame.event.get()

        if GAME_STATE == 'SETTINGS':
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    save_manager.update_settings(game_settings)
                    GAME_STATE = 'MENU'
                
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    is_slider_clicked = False
                    for key, rect in active_ui_elements.items():
                        if key.startswith('slider_') and rect.collidepoint(mouse_pos):
                            dragging_slider = key
                            is_slider_clicked = True
                            slider_key_name = dragging_slider.replace('slider_', '')
                            relative_x = mouse_pos[0] - rect.x
                            value = max(0.0, min(1.0, relative_x / rect.width))
                            game_settings[slider_key_name] = value
                            audio_manager.update_settings(game_settings)
                            break

                    if not is_slider_clicked:
                        if 'toggle_fullscreen' in active_ui_elements and active_ui_elements['toggle_fullscreen'].collidepoint(mouse_pos):
                            game_settings['fullscreen'] = not game_settings['fullscreen']
                        elif 'change_resolution' in active_ui_elements and active_ui_elements['change_resolution'].collidepoint(mouse_pos):
                            game_settings['res_index'] = (game_settings['res_index'] + 1) % len(AVAILABLE_RESOLUTIONS)
                        elif 'apply_changes' in active_ui_elements and active_ui_elements['apply_changes'].collidepoint(mouse_pos):
                            save_manager.update_settings(game_settings)
                            audio_manager.update_settings(game_settings)
                            apply_display_settings()
                        elif 'back' in active_ui_elements and active_ui_elements['back'].collidepoint(mouse_pos):
                            save_manager.update_settings(game_settings)
                            GAME_STATE = 'MENU'
                        elif 'reset_progress' in active_ui_elements and active_ui_elements['reset_progress'].collidepoint(mouse_pos):
                            save_manager.reset_progress()
                            game_settings = save_manager.get_settings()
                            audio_manager.update_settings(game_settings)

                elif event.type == pygame.MOUSEMOTION:
                    if dragging_slider:
                        slider_key_name = dragging_slider.replace('slider_', '')
                        slider_rect = active_ui_elements[dragging_slider]
                        relative_x = mouse_pos[0] - slider_rect.x
                        value = max(0.0, min(1.0, relative_x / slider_rect.width))
                        game_settings[slider_key_name] = value
                        audio_manager.update_settings(game_settings)

                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if dragging_slider:
                        save_manager.update_settings(game_settings)
                        dragging_slider = None
            
            events = []

        for event in events:
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # ── DEBUG BUTONU — her game state'de çalışır ────────────
                if _DEBUG_BTN_RECT.collidepoint(mouse_pos):
                    DEBUG_SPRITE = not DEBUG_SPRITE
                    # DIRECT_SPRITE_TEST her zaman True — karakter hep çizilir
                    _state_str = "AÇIK" if DEBUG_SPRITE else "KAPALI"
                    print(f"[DEBUG] Toggle → {_state_str}")
                    pass
                elif GAME_STATE == 'MENU':
                    if 'story_mode' in active_ui_elements and active_ui_elements['story_mode'].collidepoint(mouse_pos):
                        audio_manager.stop_music()
                        IntroCutscene(screen, clock).run()  # ← DEĞİŞİKLİK 2: Giriş sahnesi
                        ai_awakening_scene = AICutscene(screen, clock, asset_paths)
                        cutscene_finished = ai_awakening_scene.run()
                        if cutscene_finished:
                            current_level_idx = 1
                            start_loading_sequence('PLAYING')
                        else:
                            running = False
                    elif 'level_select' in active_ui_elements and active_ui_elements['level_select'].collidepoint(mouse_pos):
                        GAME_STATE = 'LEVEL_SELECT'
                        level_select_page = 0
                    elif 'settings' in active_ui_elements and active_ui_elements['settings'].collidepoint(mouse_pos):
                        GAME_STATE = 'SETTINGS'
                    elif 'cheat_terminal' in active_ui_elements and active_ui_elements['cheat_terminal'].collidepoint(mouse_pos):
                        GAME_STATE = 'TERMINAL'
                        terminal_input = ""
                        terminal_status = "KOMUT BEKLENİYOR..."
                    elif 'endless' in active_ui_elements and active_ui_elements['endless'].collidepoint(mouse_pos):
                        GAME_STATE = 'ENDLESS_SELECT'
                    elif 'exit' in active_ui_elements and active_ui_elements['exit'].collidepoint(mouse_pos):
                        running = False

                elif GAME_STATE == 'LEVEL_SELECT':
                    if 'back' in active_ui_elements and active_ui_elements['back'].collidepoint(mouse_pos):
                        GAME_STATE = 'MENU'
                    elif 'next_page' in active_ui_elements and active_ui_elements['next_page'].collidepoint(mouse_pos):
                        level_select_page += 1
                    elif 'prev_page' in active_ui_elements and active_ui_elements['prev_page'].collidepoint(mouse_pos):
                        level_select_page = max(0, level_select_page - 1)
                    else:
                        for key, rect in active_ui_elements.items():
                            if key.startswith('level_') and rect.collidepoint(mouse_pos):
                                level_num = int(key.split('_')[1])
                                current_level_idx = level_num
                                start_loading_sequence('PLAYING')
                                break

                elif GAME_STATE == 'ENDLESS_SELECT':
                    if 'back' in active_ui_elements and active_ui_elements['back'].collidepoint(mouse_pos):
                        GAME_STATE = 'MENU'
                    else:
                        for key, rect in active_ui_elements.items():
                            if key.startswith('mode_') and rect.collidepoint(mouse_pos):
                                mode_name = key.split('_')[1]
                                endless_modes.current_mode = mode_name
                                start_loading_sequence('ENDLESS_PLAY')
                                break

                elif GAME_STATE == 'LEVEL_COMPLETE':
                    if 'continue' in active_ui_elements and active_ui_elements['continue'].collidepoint(mouse_pos):
                        next_level = current_level_idx + 1
                        if next_level == 10:
                            karma = save_manager.get_karma()
                            scenario = "BETRAYAL" if karma >= 0 else "JUDGMENT"
                            cinematic_assets = asset_paths.copy()
                            cinematic_assets['scenario'] = scenario
                            audio_manager.stop_music()
                            scene = AICutscene(screen, clock, cinematic_assets)
                            scene.run()
                            current_level_idx = 10
                            start_loading_sequence('PLAYING')
                            continue
                        if 11 <= current_level_idx <= 14:
                            current_level_idx = next_level
                            init_game()
                            GAME_STATE = 'PLAYING'
                            continue
                        elif current_level_idx == 30:
                            GAME_STATE = 'GAME_COMPLETE'
                        elif next_level in EASY_MODE_LEVELS:
                            current_level_idx = next_level
                            init_game()
                            GAME_STATE = 'PLAYING'
                        else:
                            GAME_STATE = 'GAME_COMPLETE'
                    elif 'return_menu' in active_ui_elements and active_ui_elements['return_menu'].collidepoint(mouse_pos):
                        GAME_STATE = 'MENU'

                elif GAME_STATE in ['CHAT', 'CUTSCENE']:
                    if story_manager.state == "WAITING_CHOICE":
                        for key, rect in active_ui_elements.items():
                            if key.startswith('choice_') and rect.collidepoint(mouse_pos):
                                choice_idx = int(key.split('_')[1])
                                story_manager.select_choice(choice_idx)
                                break
                    elif story_manager.waiting_for_click:
                        story_manager.next_line()
                        if story_manager.state == "FINISHED":
                            if story_manager.current_chapter == 0:
                                current_level_idx = 1
                                start_loading_sequence('PLAYING')
                            else:
                                start_loading_sequence('PLAYING')

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if GAME_STATE == 'PLAYING':
                        GAME_STATE = 'MENU'
                        audio_manager.stop_music()
                    elif GAME_STATE == 'NPC_CHAT':
                        GAME_STATE = 'PLAYING'
                        if current_npc:
                            current_npc.end_conversation()
                            current_npc = None
                    elif GAME_STATE == 'TERMINAL':
                        GAME_STATE = 'MENU'
                    elif GAME_STATE in ['MENU', 'SETTINGS', 'LEVEL_SELECT', 'ENDLESS_SELECT']:
                        running = False

                if event.key == pygame.K_p:
                    if GAME_STATE == 'PLAYING':
                        GAME_STATE = 'PAUSED'
                        audio_manager.pause_all()
                    elif GAME_STATE == 'PAUSED':
                        GAME_STATE = 'PLAYING'
                        audio_manager.unpause_all()

                if GAME_STATE == 'GAME_OVER' and event.key == pygame.K_r:
                    init_game()
                    GAME_STATE = 'PLAYING'
                if current_level_idx == 99 and event.key == pygame.K_r:
                    init_redemption_mode()
                if current_level_idx == 99 and event.key == pygame.K_g:
                    save_manager.update_karma(-80)
                    init_genocide_mode()

                if GAME_STATE == 'PLAYING' and event.key == pygame.K_e:
                    closest_npc = None
                    min_dist = float('inf')
                    for npc in npcs:
                        dist = math.sqrt((player_x - npc.x)**2 + (player_y - npc.y)**2)
                        if dist < npc.talk_radius and dist < min_dist:
                            min_dist = dist
                            closest_npc = npc
                    if closest_npc:
                        start_npc_conversation(closest_npc)

                # --- DÖVÜŞ TUŞLARI (tüm bölümlerde aktif) ---
                if GAME_STATE == 'PLAYING':
                    px_c = int(player_x + 15)
                    py_c = int(player_y + 15)
                    if event.key == pygame.K_j:   # Hafif vuruş
                        combo_system.input_light(player_x, player_y, player_direction)
                        all_vfx.add(ParticleExplosion(
                            px_c + player_direction * 40, py_c,
                            (255, 150, 50), 8
                        ))
                    elif event.key == pygame.K_k:  # Ağır vuruş
                        combo_system.input_heavy(player_x, player_y, player_direction)
                        all_vfx.add(Shockwave(
                            px_c + player_direction * 50, py_c,
                            CURSED_RED, max_radius=60, speed=12
                        ))
                        screen_shake = 6

                elif GAME_STATE == 'TERMINAL':
                    if event.key == pygame.K_RETURN:
                        if terminal_input.upper() == "SUPER_MODE_ON":
                            is_super_mode = not is_super_mode
                            status = "AKTİF" if is_super_mode else "PASİF"
                            terminal_status = f"SÜPER MOD: {status}!"
                            terminal_input = ""
                        else:
                            terminal_status = "HATA: GEÇERSİZ KOD"
                            terminal_input = ""
                    elif event.key == pygame.K_BACKSPACE:
                        terminal_input = terminal_input[:-1]
                    else:
                        if len(terminal_input) < 20:
                            terminal_input += event.unicode.upper()

                elif GAME_STATE == 'NPC_CHAT':
                    if event.key == pygame.K_RETURN:
                        if npc_chat_input.strip():
                            npc_chat_history.append({"speaker": "Oyuncu", "text": npc_chat_input})
                            npc_response = "..."
                            if current_npc:
                                if current_npc.ai_active:
                                    npc_response = story_manager.generate_npc_response(current_npc, npc_chat_input, npc_chat_history[:-1])
                                else:
                                    game_context = f"Skor: {int(score)}, Bölüm: {current_level_idx}"
                                    npc_response = current_npc.send_message(npc_chat_input, game_context)
                                npc_chat_history.append({"speaker": current_npc.name, "text": npc_response})
                            npc_chat_input = ""
                    elif event.key == pygame.K_BACKSPACE:
                        npc_chat_input = npc_chat_input[:-1]
                    elif event.key == pygame.K_TAB:
                        if current_npc:
                            current_npc.ai_active = not current_npc.ai_active
                    elif event.key == pygame.K_ESCAPE:
                        GAME_STATE = 'PLAYING'
                        if current_npc:
                            current_npc.end_conversation()
                            current_npc = None
                    else:
                        if len(npc_chat_input) < 100:
                            npc_chat_input += event.unicode

                if GAME_STATE == 'PLAYING' and event.key == pygame.K_t:
                    lvl_config = EASY_MODE_LEVELS.get(current_level_idx, EASY_MODE_LEVELS[1])
                    if lvl_config.get('type') == 'rest_area':
                        next_level = current_level_idx + 1
                        if next_level in EASY_MODE_LEVELS:
                            current_level_idx = next_level
                            init_game()
                        else:
                            GAME_STATE = 'GAME_COMPLETE'

                if GAME_STATE == 'PLAYING':
                    px, py = int(player_x + 15), int(player_y + 15)
                    if event.key == pygame.K_w and jumps_left > 0 and not is_dashing:
                        jumps_left -= 1
                        is_jumping = True
                        is_slamming = False
                        y_velocity = -JUMP_POWER
                        character_state = 'jumping'
                        all_vfx.add(ParticleExplosion(px, py, CURRENT_THEME["player_color"], 6))
                        for _ in range(2):
                            all_vfx.add(EnergyOrb(px + random.randint(-10, 10),
                                                    py + random.randint(-10, 10),
                                                    CURRENT_THEME["border_color"], 4, 15))

                    if event.key == pygame.K_s and is_jumping and not is_dashing and not is_slamming and slam_cooldown <= 0:
                        is_slamming = True
                        slam_stall_timer = 15
                        slam_cooldown = active_slam_cd
                        y_velocity = 0
                        character_state = 'slamming'
                        slam_collision_check_frames = 0
                        if SLAM_SOUND:
                            audio_manager.play_sfx(SLAM_SOUND)
                        all_vfx.add(ScreenFlash(PLAYER_SLAM, 80, 8))
                        all_vfx.add(Shockwave(px, py, PLAYER_SLAM, max_radius=200, rings=3, speed=25))
                        for _ in range(3):
                            all_vfx.add(LightningBolt(px, py,
                                                        px + random.randint(-60, 60),
                                                        py + random.randint(-60, 60),
                                                        PLAYER_SLAM, 12))

                    # ── F TUŞU: SESSİZ SUİKAST ────────────────────────────────────
                    # Sadece manor_stealth bölümlerinde aktif.
                    # stealth_system.try_stealth_kill() iki şartı kontrol eder:
                    #   1) Muhafızın suspicion < 0.5 (seni fark etmemiş)
                    #   2) Oyuncu muhafızın ARKASINDA (facing yönüne ters taraf)
                    # Başarılıysa: muhafız anında deaktive, karma +1, yeşil VFX
                    # Başarısızsa: ekrana kısa hata bildirimi (kırmızı metin)
                    if event.key == pygame.K_f:
                        _manor_lvl = EASY_MODE_LEVELS.get(current_level_idx, {})
                        if _manor_lvl.get('type') == 'manor_stealth':
                            _sk_result = stealth_system.try_stealth_kill(
                                player_x + 15, player_y + 15,
                                reach=STEALTH_KILL_REACH_PX
                            )
                            if _sk_result["success"]:
                                # Başarılı sessiz öldürme
                                _gx = int(_sk_result["x"])
                                _gy = int(_sk_result["y"])
                                score += 3000
                                save_manager.update_karma(STEALTH_KILL_KARMA)
                                player_karma = save_manager.get_karma()
                                enemies_killed_current_level += 1
                                karma_notification_text  = f"SESSİZ SUİKAST! KARMA +{STEALTH_KILL_KARMA}"
                                karma_notification_timer = 80
                                # Gizli yeşil parçacık patlaması — ışıklı değil, sütunlu değil
                                all_vfx.add(ParticleExplosion(_gx, _gy, (0, 200, 100), 14))
                                all_vfx.add(Shockwave(_gx, _gy, (0, 180, 80),
                                                      max_radius=60, rings=1, speed=10))
                                screen_shake = max(screen_shake, 3)
                                # Tüm muhafızlar elenince opsiyonel hedefi işaretle
                                if stealth_system.active_guard_count() == 0:
                                    from mission_system import mission_manager
                                    mission_manager.complete_objective("eliminate_guards")
                            else:
                                # Başarısız — neden başarısız olduğunu bildir
                                _reason = _sk_result.get("reason", "BAŞARISIZ")
                                karma_notification_text  = f"SUİKAST BAŞARISIZ: {_reason}"
                                karma_notification_timer = 60

                    if event.key == pygame.K_SPACE and dash_cooldown_timer <= 0 and not is_dashing:
                        is_dashing = True
                        # Malikane bölümünde dash mesafesi kısaltılır (kaçış adımı)
                        _manor_dash_cfg = EASY_MODE_LEVELS.get(current_level_idx, {})
                        dash_timer = (DASH_DURATION // 3) if _manor_dash_cfg.get('type') == 'manor_stealth' else DASH_DURATION
                        dash_cooldown_timer = active_dash_cd
                        screen_shake = 8
                        dash_particles_timer = 0
                        dash_frame_counter = 0.0
                        character_state = 'dashing'
                        if DASH_SOUND:
                            audio_manager.play_sfx(DASH_SOUND)
                        all_vfx.add(ScreenFlash(METEOR_CORE, 80, 6))
                        all_vfx.add(Shockwave(px, py, METEOR_FIRE, max_radius=120, rings=2, speed=15))
                        keys = pygame.key.get_pressed()
                        dx = (keys[pygame.K_d] - keys[pygame.K_a])
                        dy = (keys[pygame.K_s] - keys[pygame.K_w])
                        if dx == 0 and dy == 0:
                            dx = 1
                        mag = math.sqrt(dx*dx + dy*dy)
                        dash_vx, dash_vy = (dx/mag)*DASH_SPEED, (dy/mag)*DASH_SPEED
                        is_jumping = True
                        y_velocity = 0
                        dash_angle = math.atan2(dash_vy, dash_vx)

        if GAME_STATE == 'LOADING':
            loading_timer += 1
            if loading_timer % 10 == 0 and loading_stage < len(fake_log_messages):
                loading_logs.append(fake_log_messages[loading_stage])
                loading_stage += 1
                loading_progress = min(0.95, loading_stage / len(fake_log_messages))
            if loading_stage >= len(fake_log_messages):
                loading_progress += 0.02
                if loading_progress >= 1.0:
                    init_game()
                    GAME_STATE = target_state_after_load

        elif GAME_STATE == 'CHAT' or GAME_STATE == 'CUTSCENE':
            story_manager.update(dt)
            if story_manager.is_cutscene:
                GAME_STATE = 'CUTSCENE'
            else:
                GAME_STATE = 'CHAT'

        elif GAME_STATE == 'NPC_CHAT':
            npc_cursor_timer += 1
            if npc_cursor_timer >= 30:
                npc_show_cursor = not npc_show_cursor
                npc_cursor_timer = 0

        elif GAME_STATE in ['PLAYING', 'ENDLESS_PLAY']:
            current_karma = player_karma
            buff_stacks = (current_level_idx - 1) // 3
            if buff_stacks > 2:
                buff_stacks = 2
            base_speed_mult = 1.0 + (0.25 * buff_stacks)
            base_cd_mult = 0.5 ** buff_stacks
            karma_bonus = 0.0
            if abs(current_karma) >= 100:
                karma_speed_bonus = 0.25
                karma_cd_reduction = 0.25
                base_speed_mult += karma_speed_bonus
                base_cd_mult -= karma_cd_reduction
            active_player_speed = PLAYER_SPEED * base_speed_mult
            active_dash_cd = DASH_COOLDOWN * max(0.2, base_cd_mult)
            active_slam_cd = SLAM_COOLDOWN_BASE * max(0.2, base_cd_mult)
            if vasil_companion:
                active_player_speed = PLAYER_SPEED * 1.5
                active_dash_cd = 0
                active_slam_cd = 0

            # ── MALİKANE STEALTHFİZİĞİ OVERRİDE ────────────────────────────
            # Normal bölüm hız/cooldown hesaplamaları stealth için çok hızlı.
            # manor_stealth bölümünde tüm karma/level buff'ları bastırılır ve
            # hız %45'e düşürülür; dash kısa kaçış adımına (1/3 süre) indirgenir.
            _lvl_cfg_physics = EASY_MODE_LEVELS.get(current_level_idx, {})
            if _lvl_cfg_physics.get('type') == 'manor_stealth':
                active_player_speed = PLAYER_SPEED * 0.80          # Normal'in %80'i — kontrollü ama kullanılabilir
                active_dash_cd      = DASH_COOLDOWN * 1.2          # Dash hafif seyrek
                active_slam_cd      = SLAM_COOLDOWN_BASE            # Slam değişmez

            lvl_config = EASY_MODE_LEVELS.get(current_level_idx, EASY_MODE_LEVELS[1])
            if lvl_config.get('type') == 'rest_area':
                if player_x > LOGICAL_WIDTH + 100:
                    next_level = current_level_idx + 1
                    if next_level in EASY_MODE_LEVELS:
                        current_level_idx = next_level
                        init_game()
                    else:
                        GAME_STATE = 'GAME_COMPLETE'

            # ═════════════════════════════════════════════════════════════
            # GİZLİLİK SİSTEMİ — Her karede çalışır
            # ═════════════════════════════════════════════════════════════
            stealth_system.update(dt, player_x, player_y)

            # Stealth olaylarını oku (tespitler, karma bonusları, uyarılar)
            for stealth_event in stealth_system.poll_events():
                ev_type = stealth_event.get('type')
                if ev_type == 'detected':
                    # Tespit edilince ekran sarsıntısı + karma cezası
                    screen_shake = max(screen_shake, 10)
                    save_manager.update_karma(-5)
                    player_karma = save_manager.get_karma()
                    karma_notification_text  = "TESPİT EDİLDİN! KARMA -5"
                    karma_notification_timer = 90
                    all_vfx.add(ScreenFlash((255, 50, 50), 80, 5))
                elif ev_type == 'stealth_bonus':
                    # Başarılı gizlilik → karma bonusu
                    bonus = stealth_event.get('value', 5)
                    save_manager.update_karma(bonus)
                    player_karma = save_manager.get_karma()
                    karma_notification_text  = f"STEALTH BONUS! KARMA +{bonus}"
                    karma_notification_timer = 70
                elif ev_type == 'alert':
                    # Genel uyarı mesajı
                    karma_notification_text  = stealth_event.get('message', 'UYARI!')
                    karma_notification_timer = 60

            # ═════════════════════════════════════════════════════════════
            # GLOBAL DÖVÜŞ SİSTEMİ — Her bölümde çalışır
            # ═════════════════════════════════════════════════════════════

            # Kombo zamanlayıcısı + can yenileme her frame güncellenir
            combo_system.update(dt)
            player_hp.update(dt)

            # ── J/K Melee vuruş tespiti ───────────────────────────────────
            # Hedef havuzu: normal düşmanlar + arena düşmanları (eğer aktifse)
            _arena_targets = list(beat_arena.arena_enemies) if beat_arena.active else []
            _all_targets   = list(all_enemies) + _arena_targets
            melee_hits = combo_system.check_hits(_all_targets)
            for hit in melee_hits:
                _enemy  = hit["enemy"]
                _damage = hit["damage"]
                _vfx    = hit["vfx_type"]
                _hx, _hy = hit["hit_pos"]

                # Hasar uygula — ArenaEnemy veya normal düşman
                if hasattr(_enemy, 'take_damage'):
                    _killed = _enemy.take_damage(_damage)
                    score  += _damage * 10
                else:
                    # CursedEnemy / DroneEnemy / TankEnemy → tek vuruşta ölür
                    _killed = True
                    _enemy.kill()
                    score  += 500

                # Kombo tetiklenince bildirim + skor bonusu
                if hit["combo"]:
                    _combo_info = hit["combo"]
                    score += _combo_info.get("score_bonus", 0)
                    save_manager.update_karma(-_combo_info.get("karma", 2))
                    player_karma = save_manager.get_karma()
                    karma_notification_text  = f"KOMBO: {_combo_info['name']}!"
                    karma_notification_timer = 70
                else:
                    save_manager.update_karma(-2)
                    player_karma = save_manager.get_karma()

                # VFX
                if _vfx == "explosion":
                    all_vfx.add(ParticleExplosion(_hx, _hy, CURSED_PURPLE, 18))
                elif _vfx == "shockwave":
                    all_vfx.add(Shockwave(_hx, _hy, CURSED_RED, max_radius=80, speed=12))
                elif _vfx == "lightning":
                    all_vfx.add(LightningBolt(int(player_x + 15), int(player_y + 15),
                                              _hx, _hy, (100, 200, 255), life=8))
                else:
                    all_vfx.add(FlameSpark(_hx, _hy, random.uniform(0, math.pi * 2),
                                           random.uniform(4, 10), (255, 150, 50), life=15))

                if _killed:
                    enemies_killed_current_level += 1
                    screen_shake = max(screen_shake, 8)
                    all_vfx.add(ScreenFlash(CURSED_PURPLE, 40, 4))

            # VFX kuyruğunu boşalt
            for _ in combo_system.pop_vfx():
                pass

            # ── DASH → Tüm düşmanlara AOE hasar ─────────────────────────
            if is_dashing:
                _px_d = int(player_x + 15)
                _py_d = int(player_y + 15)
                _DASH_DMG    = 45
                _DASH_RADIUS = 110
                # Normal düşmanlar (all_enemies) — mevcut kod ile çakışmayı önlemek için
                # sadece ArenaEnemy türünü burada ele alıyoruz; CursedEnemy vb. zaten
                # mevcut sprite collision koduyla öldürülüyor (aşağıda).
                for _ae in _arena_targets:
                    if not _ae.is_active:
                        continue
                    _d = math.sqrt((_ae.rect.centerx - _px_d)**2 + (_ae.rect.centery - _py_d)**2)
                    if _d < _DASH_RADIUS:
                        _dk = _ae.take_damage(_DASH_DMG, bypass_block=True)
                        score += _DASH_DMG * 8
                        save_manager.update_karma(-8)
                        player_karma = save_manager.get_karma()
                        all_vfx.add(ParticleExplosion(_ae.rect.centerx, _ae.rect.centery, METEOR_FIRE, 15))
                        all_vfx.add(Shockwave(_ae.rect.centerx, _ae.rect.centery,
                                              (255, 120, 0), max_radius=70, speed=14))
                        if _dk:
                            enemies_killed_current_level += 1
                            screen_shake = max(screen_shake, 10)
                            karma_notification_text  = "DASH STRIKE!"
                            karma_notification_timer = 40
                            all_vfx.add(ScreenFlash(METEOR_FIRE, 50, 4))

            # ── SLAM → Yere değdiğinde tüm düşmanlara AOE hasar ─────────
            if is_slamming and slam_stall_timer <= 0:
                _px_s = int(player_x + 15)
                _py_s = int(player_y + 30)
                _SLAM_DMG    = 60
                _SLAM_RADIUS = 140
                # Normal düşmanlar
                for _ne in list(all_enemies):
                    if isinstance(_ne, EnemyBullet):
                        continue
                    _ds = math.sqrt((_ne.rect.centerx - _px_s)**2 + (_ne.rect.centery - _py_s)**2)
                    if _ds < _SLAM_RADIUS:
                        _ne.kill()
                        score += 500
                        save_manager.update_karma(-10)
                        player_karma = save_manager.get_karma()
                        enemies_killed_current_level += 1
                        all_vfx.add(ParticleExplosion(_ne.rect.centerx, _ne.rect.centery, PLAYER_SLAM, 18))
                # Arena düşmanları
                for _ae2 in _arena_targets:
                    if not _ae2.is_active:
                        continue
                    _ds2 = math.sqrt((_ae2.rect.centerx - _px_s)**2 + (_ae2.rect.centery - _py_s)**2)
                    if _ds2 < _SLAM_RADIUS:
                        _sk = _ae2.take_damage(_SLAM_DMG, bypass_block=True)
                        score += _SLAM_DMG * 8
                        save_manager.update_karma(-10)
                        player_karma = save_manager.get_karma()
                        all_vfx.add(ParticleExplosion(_ae2.rect.centerx, _ae2.rect.centery, PLAYER_SLAM, 20))
                        all_vfx.add(Shockwave(_px_s, _py_s, PLAYER_SLAM, max_radius=_SLAM_RADIUS, speed=18))
                        if _sk:
                            enemies_killed_current_level += 1
                            screen_shake = max(screen_shake, 20)
                            karma_notification_text  = "SLAM KO!"
                            karma_notification_timer = 50
                            all_vfx.add(ScreenFlash(PLAYER_SLAM, 80, 6))

            # ═════════════════════════════════════════════════════════════
            # BEAT 'EM UP ARENA — Sadece arena bölümlerine özgü mantık
            # ═════════════════════════════════════════════════════════════
            if lvl_config.get('type') == 'beat_arena':
                camera_speed = 0   # Kamera sabit

                # Arena henüz başlamadıysa başlat
                if not beat_arena.active and not beat_arena.is_complete:
                    beat_arena.start(lvl_config.get('arena_level_id', current_level_idx))

                # Arena düşmanlarını güncelle
                beat_arena.update(dt, frame_mul,
                                  player_x + 15,
                                  player_y + 15,
                                  0.0)

                # Arena düşmanlarının oyuncuya saldırısı
                for atk in beat_arena.get_enemy_attacks():
                    _pcx = atk.get("player_cx", player_x + 15)
                    _pcy = atk.get("player_cy", player_y + 15)
                    _dist_atk = math.sqrt((_pcx - atk["x"])**2 + (_pcy - atk["y"])**2)
                    if _dist_atk < 120:
                        _died = player_hp.take_damage(atk["damage"])
                        screen_shake = max(screen_shake, 12)
                        all_vfx.add(ScreenFlash((255, 0, 0), 100, 6))
                        all_vfx.add(ParticleExplosion(int(player_x + 15), int(player_y + 15),
                                                      (220, 0, 0), 12))
                        if _died:
                            GAME_STATE = 'GAME_OVER'
                            high_score = max(high_score, int(score))
                            save_manager.update_high_score('easy_mode', current_level_idx, score)
                            audio_manager.stop_music()

                # Ödül toplama
                _player_rect_d = pygame.Rect(int(player_x), int(player_y), 30, 30)
                for drop in beat_arena.collect_drops(_player_rect_d):
                    if drop["type"] == "score":
                        score += drop["value"]
                        karma_notification_text  = f"+{drop['value']} PUAN!"
                        karma_notification_timer = 45
                    elif drop["type"] == "karma":
                        save_manager.update_karma(drop["value"])
                        player_karma = save_manager.get_karma()
                        karma_notification_text  = f"KARMA +{drop['value']}"
                        karma_notification_timer = 45
                    elif drop["type"] == "health":
                        player_hp.heal(25)
                        karma_notification_text  = "CAN +25"
                        karma_notification_timer = 45
                    all_vfx.add(EnergyOrb(int(player_x + 15), int(player_y - 30),
                                          (255, 215, 0), 8, 20))

                # Tüm dalgalar temizlendi → bölüm geçişi
                if beat_arena.is_complete:
                    score += beat_arena.total_bonus
                    save_manager.update_karma(15)
                    player_karma = save_manager.get_karma()
                    beat_arena.reset()
                    GAME_STATE = 'LEVEL_COMPLETE'
                    save_manager.unlock_next_level('easy_mode', current_level_idx)
                    save_manager.update_high_score('easy_mode', current_level_idx, score)
            # ─────────────────────────────────────────────────────────────
            else:
                if current_level_idx != 99:
                    if lvl_config.get('type') != 'beat_arena':
                        camera_speed = min(MAX_CAMERA_SPEED, camera_speed + SPEED_INCREMENT_RATE * frame_mul)
                    score_gain = 0.1 * max(camera_speed, 1.0) * frame_mul
                    if is_super_mode:
                        score_gain *= 40
                    score += score_gain

            # ═════════════════════════════════════════════════════════════
            # MALİKANE KAMERA TAKİBİ — ÇOK KRİTİK
            # manor_stealth tipinde kamera kendi kendine kaymaz;
            # bunun yerine kamera X ofseti oyuncuyu her zaman ekran
            # ortasında tutacak şekilde hesaplanır.
            # Tüm draw çağrıları bu ofseti dikkate alır.
            # ═════════════════════════════════════════════════════════════
            if lvl_config.get('type') == 'manor_stealth':
                # ── 2D KAMERA TAKİBİ — Anlık ve kesin merkezleme ──────────────
                # Harita boyutları — platform düzenine göre sabit
                MANOR_MAP_WIDTH  = lvl_config.get('map_width',  3300)
                MANOR_MAP_HEIGHT = lvl_config.get('map_height', 2200)
                PLAYER_W_HALF = 15
                PLAYER_H_HALF = 15

                # Oyuncunun gerçek merkezi → hedef kamera ofseti
                _target_cam_x = (player_x + PLAYER_W_HALF) - LOGICAL_WIDTH  // 2
                _target_cam_y = (player_y + PLAYER_H_HALF) - LOGICAL_HEIGHT // 2

                # Sınır: harita dışına çıkılmasın
                _cam_max_x = max(0, MANOR_MAP_WIDTH  - LOGICAL_WIDTH)
                _cam_max_y = max(0, MANOR_MAP_HEIGHT - LOGICAL_HEIGHT)
                _target_cam_x = max(0, min(_target_cam_x, _cam_max_x))
                _target_cam_y = max(0, min(_target_cam_y, _cam_max_y))

                # Anlık takip — gecikme yok, kamera her zaman oyuncuyu ortalar
                manor_camera_offset_x = int(_target_cam_x)
                manor_camera_offset_y = int(_target_cam_y)

                # Malikane bölümünde area_reached kontrolü:
                # Oyuncu gizli kasanın etrafındaki alana girince görev tamamlanır.
                # Kasa platformu: x=2720, y=Y_ROOF-140=(1080-200)-140=740
                _safe_x = lvl_config.get("secret_safe_x", 2910)
                _safe_y = lvl_config.get("secret_safe_y", 720)
                _safe_r = lvl_config.get("secret_safe_radius", 100)
                _dx_safe = player_x - _safe_x
                _dy_safe = player_y - _safe_y
                if math.sqrt(_dx_safe * _dx_safe + _dy_safe * _dy_safe) < _safe_r:
                    # İlk kez tetiklendiyse hedefleri tamamla ve bölümü bitir
                    from mission_system import mission_manager
                    mission_manager.set_flag("area_secret_safe", True)
                    mission_manager.complete_objective("find_secret_safe")
                    # Tüm muhafızlar elendiyse "eliminate_guards" hedefini de tamamla
                    if stealth_system.active_guard_count() == 0:
                        mission_manager.complete_objective("eliminate_guards")
                    # Hiç alarm verilmediyse opsiyonel bonus
                    if stealth_system.global_alert == 0:   # ALERT_UNDETECTED
                        mission_manager.complete_objective("stealth_optional_no_alert")
                        save_manager.update_karma(15)
                        player_karma = save_manager.get_karma()
                        karma_notification_text  = "MÜKEMMEL GİZLİLİK! KARMA +15"
                        karma_notification_timer = 120
                    # Bölüm tamamlandı
                    score += 20000
                    GAME_STATE = 'LEVEL_COMPLETE'
                    save_manager.unlock_next_level('easy_mode', current_level_idx)
                    save_manager.update_high_score('easy_mode', current_level_idx, score)
            else:
                manor_camera_offset_x = 0
                manor_camera_offset_y = 0

            old_x, old_y = player_x, player_y
            keys = pygame.key.get_pressed()
            horizontal_move = keys[pygame.K_d] - keys[pygame.K_a]
            if horizontal_move != 0 and not is_dashing and not is_slamming:
                character_state = 'running'
                player_direction = 1 if horizontal_move > 0 else -1  # Yön güncelle
            elif not is_jumping and not is_dashing and not is_slamming:
                character_state = 'idle'
                # player_direction değişmez → durduğunda son yönü korur
            is_grounded = not is_jumping and not is_slamming and not is_dashing
            character_animator.update(dt, character_state, is_grounded, y_velocity, is_dashing, is_slamming)

            last_trail_time += frame_mul
            if last_trail_time >= TRAIL_INTERVAL and (is_dashing or is_slamming):
                last_trail_time = 0.0
                trail_color = CURRENT_THEME["player_color"]
                if is_dashing:
                    trail_color = METEOR_FIRE
                    trail_size = random.randint(8, 14)
                elif is_slamming:
                    trail_color = PLAYER_SLAM
                    trail_size = random.randint(8, 12)
                trail_effects.append(TrailEffect(player_x + 15, player_y + 15, trail_color, trail_size, life=12))

            for wave in active_damage_waves[:]:
                wave['r'] += wave['speed'] * frame_mul
                wave['x'] -= camera_speed * frame_mul
                for enemy in all_enemies:
                    dist = math.sqrt((enemy.rect.centerx - wave['x'])**2 + (enemy.rect.centery - wave['y'])**2)
                    if dist < wave['r'] + 20 and dist > wave['r'] - 40:
                        enemy.kill()
                        score += 500
                        save_manager.update_karma(-10)
                        player_karma = save_manager.get_karma()
                        enemies_killed_current_level += 1
                        karma_notification_text = "KARMA DÜŞTÜ!"
                        karma_notification_timer = 60
                        all_vfx.add(ParticleExplosion(enemy.rect.centerx, enemy.rect.centery, CURSED_PURPLE, 20))
                        all_vfx.add(ScreenFlash(CURSED_PURPLE, 30, 2))
                if wave['r'] > wave['max_r']:
                    active_damage_waves.remove(wave)

            if is_dashing:
                px, py = int(player_x + 15), int(player_y + 15)
                dash_frame_counter += frame_mul
                for _ in range(4):
                    inv_angle = dash_angle + math.pi + random.uniform(-0.5, 0.5)
                    spark_speed = random.uniform(5, 15)
                    color = random.choice([(255, 50, 0), (255, 150, 0), (255, 255, 100)])
                    all_vfx.add(FlameSpark(px, py, inv_angle, spark_speed, color, life=20, size=random.randint(4, 8)))

                if int(dash_frame_counter) % 5 == 0:
                    all_vfx.add(Shockwave(px, py, (255, 200, 100), max_radius=70, width=2, speed=10))

                meteor_hit_radius = 120
                enemy_hits_aoe = [e for e in all_enemies if math.sqrt((e.rect.centerx - px)**2 + (e.rect.centery - py)**2) < meteor_hit_radius]
                for enemy in enemy_hits_aoe:
                    enemy.kill()
                    score += 500
                    save_manager.update_karma(-10)
                    player_karma = save_manager.get_karma()
                    enemies_killed_current_level += 1
                    karma_notification_text = "KARMA DÜŞTÜ!"
                    karma_notification_timer = 60
                    screen_shake = 10
                    if EXPLOSION_SOUND:
                        audio_manager.play_sfx(EXPLOSION_SOUND)
                    all_vfx.add(ParticleExplosion(enemy.rect.centerx, enemy.rect.centery, METEOR_FIRE, 25))
                    all_vfx.add(Shockwave(enemy.rect.centerx, enemy.rect.centery, (255, 100, 0), max_radius=90, width=4))

                if dash_particles_timer > 0:
                    dash_particles_timer -= frame_mul
                else:
                    dash_particles_timer = 4
                    offset_x = random.randint(-5, 5)
                    offset_y = random.randint(-5, 5)
                    all_vfx.add(WarpLine(px + offset_x, py + offset_y, dash_angle + random.uniform(-0.15, 0.15), METEOR_CORE, METEOR_FIRE))

                player_x += dash_vx * frame_mul
                player_y += dash_vy * frame_mul
                player_x -= camera_speed * frame_mul
                
                dash_timer -= frame_mul
                if not vasil_companion:
                    dash_timer -= frame_mul

                if dash_timer <= 0:
                    is_dashing = False
            elif is_slamming and slam_stall_timer > 0:
                slam_stall_timer -= frame_mul
                slam_collision_check_frames += 1
                if int(slam_stall_timer) % 3 == 0:
                    for _ in range(2):
                        angle = random.uniform(0, math.pi * 2)
                        dist = random.randint(20, 40)
                        ex = player_x + 15 + math.cos(angle) * dist
                        ey = player_y + 15 + math.sin(angle) * dist
                        all_vfx.add(FlameSpark(ex, ey, angle + math.pi, dist/10, PLAYER_SLAM, life=15))

                vibration = random.randint(-1, 1) if slam_stall_timer > 7 else 0
                player_x += vibration
                if slam_stall_timer <= 0:
                    y_velocity = 30
                    screen_shake = 12
                    all_vfx.add(ParticleExplosion(player_x+15, player_y+15, PLAYER_SLAM, 12))
            else:
                if lvl_config.get('type') != 'rest_area':
                    player_x -= camera_speed * frame_mul
                if keys[pygame.K_a]:
                    player_x -= active_player_speed * frame_mul
                if keys[pygame.K_d]:
                    player_x += active_player_speed * frame_mul

                if is_super_mode:
                    y_velocity = 0
                    fly_speed = 15
                    if keys[pygame.K_w]:
                        player_y -= fly_speed * frame_mul
                    if keys[pygame.K_s]:
                        player_y += fly_speed * frame_mul
                else:
                    player_y += y_velocity * frame_mul
                    if is_slamming:
                        y_velocity += SLAM_GRAVITY * 1.8 * frame_mul
                    else:
                        y_velocity += GRAVITY * frame_mul

            attack_sequence = []
            if attack_sequence:
                philosophical_combo = combat_philosophy.create_philosophical_combo(attack_sequence)
                if philosophical_combo:
                    score *= philosophical_combo['power_multiplier']

            if reality_shifter.current_reality != 0:
                reality_effects = reality_shifter.get_current_effects()
                if 'physics' in reality_effects:
                    physics = reality_effects['physics']
                    if 'gravity' in physics:
                        y_velocity += (GRAVITY * physics['gravity'] - GRAVITY) * frame_mul
                    if 'player_speed' in physics:
                        player_x += (PLAYER_SPEED * physics['player_speed'] - PLAYER_SPEED) * frame_mul

            if dash_cooldown_timer > 0:
                dash_cooldown_timer -= frame_mul
            if slam_cooldown > 0:
                slam_cooldown -= frame_mul
            if screen_shake > 0:
                screen_shake -= 1
            if karma_notification_timer > 0:
                karma_notification_timer -= 1

            PLAYER_W, PLAYER_H = 30, 30
            player_rect = pygame.Rect(int(player_x), int(player_y), PLAYER_W, PLAYER_H)
            dummy_player = type('',(object,),{'rect':player_rect})()
            enemy_hits = pygame.sprite.spritecollide(dummy_player, all_enemies, False)

            for enemy in enemy_hits:
                if has_talisman:
                    enemy.kill()
                    saved_soul = SavedSoul(enemy.rect.centerx, enemy.rect.centery)
                    all_vfx.add(saved_soul)
                    all_vfx.add(ParticleExplosion(enemy.rect.centerx, enemy.rect.centery, (255, 215, 0), 20))
                    all_vfx.add(Shockwave(enemy.rect.centerx, enemy.rect.centery, (255, 255, 200), max_radius=120, width=5))
                    save_manager.update_karma(25)
                    save_manager.add_saved_soul(1)
                    score += 1000
                    enemies_killed_current_level += 1
                    karma_notification_text = "RUH KURTARILDI! (+25)"
                    karma_notification_timer = 40
                    continue

                if isinstance(enemy, EnemyBullet):
                    GAME_STATE = 'GAME_OVER'
                    enemy.kill()
                    continue

                if is_dashing or is_slamming or is_super_mode:
                    enemy.kill()
                    score += 500
                    if not is_super_mode:
                        save_manager.update_karma(-10)
                        enemies_killed_current_level += 1
                        karma_notification_text = "KARMA DÜŞTÜ!"
                        karma_notification_timer = 60
                    screen_shake = 15
                    if EXPLOSION_SOUND:
                        audio_manager.play_sfx(EXPLOSION_SOUND)
                    all_vfx.add(ParticleExplosion(enemy.rect.centerx, enemy.rect.centery, CURSED_PURPLE, 20))
                    all_vfx.add(Shockwave(enemy.rect.centerx, enemy.rect.centery, GLITCH_BLACK, max_radius=80, width=5))
                    pygame.time.delay(30)
                else:
                    if player_karma <= -90 and not has_revived_this_run:
                        has_revived_this_run = True
                        karma_notification_text = "KARANLIK DİRİLİŞ AKTİF!"
                        karma_notification_timer = 120
                        screen_shake = 30
                        all_vfx.add(ScreenFlash((0, 0, 0), 150, 20))
                        for e in all_enemies:
                            e.kill()
                            all_vfx.add(ParticleExplosion(e.rect.centerx, e.rect.centery, CURSED_RED, 20))
                        active_damage_waves.append({'x': player_x + 15, 'y': player_y + 15, 'r': 10, 'max_r': 500, 'speed': 40})
                        y_velocity = -15
                        is_jumping = True
                    else:
                        if current_level_idx == 10:
                            init_limbo()
                            GAME_STATE = 'PLAYING'
                            if npcs:
                                start_npc_conversation(npcs[0])
                        else:
                            GAME_STATE = 'GAME_OVER'
                            high_score = max(high_score, int(score))
                            save_manager.update_high_score('easy_mode', current_level_idx, score)
                            audio_manager.stop_music()
                            all_vfx.add(ParticleExplosion(player_x, player_y, CURSED_RED, 30))

            move_rect = pygame.Rect(int(player_x), int(min(old_y, player_y)), PLAYER_W, int(abs(player_y - old_y)) + PLAYER_H)
            collided_platforms = pygame.sprite.spritecollide(type('',(object,),{'rect':move_rect})(), all_platforms, False)

            for p in collided_platforms:
                platform_top = p.rect.top
                if (old_y + PLAYER_H <= platform_top + 15) and (player_y + PLAYER_H >= platform_top):
                    player_y = platform_top - PLAYER_H
                    if is_slamming:
                        y_velocity = -15
                        screen_shake = 30
                        active_damage_waves.append({'x': player_x + 15, 'y': platform_top, 'r': 10, 'max_r': 250, 'speed': 25})
                        for i in range(2):
                            wave = Shockwave(player_x+15, p.rect.top, (255, 180, 80), speed=25)
                            wave.radius = 30 + i*30
                            wave.max_radius = 200 + i*60
                            all_vfx.add(wave)
                        all_vfx.add(ParticleExplosion(player_x+15, p.rect.top, PLAYER_SLAM, 25))
                        is_slamming = False
                        is_jumping = True
                        jumps_left = MAX_JUMPS - 1
                        character_state = 'jumping'
                    else:
                        y_velocity = 0
                        is_jumping = is_slamming = False
                        jumps_left = MAX_JUMPS
                        character_state = 'idle'
                        all_vfx.add(ParticleExplosion(player_x+15, player_y+30, CURRENT_THEME["player_color"], 8))
                    break

            # ── MALİKANE: Yatay duvar çarpışması ─────────────────────────────
            # Duvar platformları (yüksekliği > genişliğinden büyük olanlar)
            # oyuncunun soldan veya sağdan geçişini engeller.
            if lvl_config.get('type') == 'manor_stealth':
                _wall_rect = pygame.Rect(int(player_x), int(player_y) + 4, PLAYER_W, PLAYER_H - 8)
                for _wp in all_platforms:
                    if _wp.rect.height > _wp.rect.width:   # Dikey (duvar) platform
                        if _wall_rect.colliderect(_wp.rect):
                            if old_x + PLAYER_W <= _wp.rect.left + 6:
                                player_x = float(_wp.rect.left - PLAYER_W)
                            elif old_x >= _wp.rect.right - 6:
                                player_x = float(_wp.rect.right)

            for npc in npcs:
                npc.update(player_x, player_y, dt)

            if vasil_companion:
                action = vasil_companion.update(player_x, player_y, all_enemies, boss_manager_system, camera_speed)
                if action:
                    act_type, target = action
                    if act_type == "LASER":
                        pygame.draw.line(game_canvas, (0, 255, 100), (vasil_companion.x, vasil_companion.y), target.rect.center, 3)
                        target.kill()
                        all_vfx.add(ParticleExplosion(target.rect.centerx, target.rect.centery, (0, 255, 100), 15))
                        save_manager.update_karma(-5)
                        score += 1000

                if save_manager.get_karma() <= -250:
                    vasil_companion.spike_timer += 1
                    if vasil_companion.spike_timer > 120:
                        vasil_companion.spike_timer = 0
                        vis_plats = [p for p in all_platforms if 0 < p.rect.centerx < LOGICAL_WIDTH]
                        if vis_plats:
                            p = random.choice(vis_plats)
                            all_vfx.add(Shockwave(p.rect.centerx, p.rect.top, (0, 255, 100), max_radius=100, speed=15, rings=2))
                            for e in all_enemies:
                                if e.rect.colliderect(p.rect.inflate(0, -50)):
                                    e.kill()
                                    all_vfx.add(ParticleExplosion(e.rect.centerx, e.rect.centery, (0, 255, 100), 20))

            if current_level_idx in [11, 12, 13, 14, 15, 30] and save_manager.get_karma() <= -100 and vasil_companion is None:
                vasil_companion = VasilCompanion(player_x, player_y - 100)
                karma_notification_text = "VASİ KATILDI! (-100 KARMA)"
                karma_notification_timer = 120
                all_vfx.add(ScreenFlash((0, 255, 100), 100, 10))

            if current_level_idx in [11, 12, 13, 14, 15, 30] and save_manager.get_karma() == -250 and karma_notification_timer == 0:
                 karma_notification_text = "VASİ TAM GÜÇ! (-250 KARMA)"
                 karma_notification_timer = 120

            if current_level_idx == 30:
                if not level_15_cutscene_played:
                    level_15_cutscene_played = True
                    audio_manager.stop_music()
                    cinematic_assets = asset_paths.copy()
                    cinematic_assets['scenario'] = 'FINAL_MEMORY'
                    AICutscene(screen, clock, cinematic_assets).run()
                    last_time = pygame.time.get_ticks()
                    level_15_timer = 0
                    
                    sound = load_sound_asset("assets/music/final_boss.mp3", generate_ambient_fallback, 1.0)
                    audio_manager.play_music(sound)

                if not finisher_active:
                    level_15_timer += dt
                    for enemy in all_enemies:
                        if isinstance(enemy, (NexusBoss, AresBoss, VasilBoss)):
                            enemy.health = max(enemy.health, 1000)
                    if level_15_timer >= 120.0:
                        finisher_active = True
                        finisher_state_timer = 0.0
                        finisher_type = 'GOOD' if player_karma >= 0 else 'BAD'
                        audio_manager.stop_music()
                        screen_shake = 50

                if finisher_active:
                    finisher_state_timer += dt
                    boss_target = None
                    for e in all_enemies:
                        if isinstance(e, (NexusBoss, AresBoss, VasilBoss)):
                            boss_target = e
                            break
                    if boss_target:
                        if finisher_type == 'GOOD':
                            if finisher_state_timer < 6.0:
                                if frame_count % 2 == 0:
                                    start_x = random.choice([-100, LOGICAL_WIDTH + 100, random.randint(0, LOGICAL_WIDTH)])
                                    start_y = -100 if start_x > 0 and start_x < LOGICAL_WIDTH else random.randint(0, LOGICAL_HEIGHT)
                                    soul = SavedSoul(start_x, start_y)
                                    dx = boss_target.x - start_x
                                    dy = boss_target.y - start_y
                                    dist = math.sqrt(dx*dx + dy*dy)
                                    soul.vy = (dy / dist) * 25
                                    soul.x += (dx / dist) * 25
                                    all_vfx.add(soul)
                                    bx = boss_target.x + random.randint(-50, 50)
                                    by = boss_target.y + random.randint(-50, 50)
                                    all_vfx.add(ParticleExplosion(bx, by, (0, 255, 255), 15))
                                    all_vfx.add(Shockwave(bx, by, (255, 255, 100), max_radius=50, speed=10))
                                karma_notification_text = "TÜM DOSTLAR SALDIRIYOR!"
                                karma_notification_timer = 2
                            elif finisher_state_timer > 6.0:
                                boss_target.health = 0
                        elif finisher_type == 'BAD':
                            center_x = player_x
                            center_y = player_y
                            if vasil_companion:
                                center_x = vasil_companion.x
                                center_y = vasil_companion.y
                            if finisher_state_timer < 3.0:
                                if frame_count % 2 == 0:
                                    angle = random.uniform(0, math.pi*2)
                                    dist = 300 - (finisher_state_timer * 100)
                                    px = center_x + math.cos(angle) * dist
                                    py = center_y + math.sin(angle) * dist
                                    pygame.draw.line(vfx_surface, (255, 0, 0), (px, py), (center_x, center_y), 2)
                                    all_vfx.add(EnergyOrb(px, py, (255, 50, 50), 4, 10))
                                karma_notification_text = "VASİ: KIYAMET PROTOKOLÜ..."
                                karma_notification_timer = 2
                            elif 3.0 <= finisher_state_timer < 5.0:
                                if int(finisher_state_timer * 10) % 5 == 0:
                                    screen_shake = 100
                                    all_vfx.add(ScreenFlash((255, 255, 255), 255, 60))
                                    all_vfx.add(Shockwave(center_x, center_y, (255, 0, 0), max_radius=2000, width=50, speed=100))
                                    for _ in range(20):
                                        rx = random.randint(0, LOGICAL_WIDTH)
                                        ry = random.randint(0, LOGICAL_HEIGHT)
                                        all_vfx.add(ParticleExplosion(rx, ry, (255, 0, 0), 40))
                            elif finisher_state_timer > 5.0:
                                boss_target.health = 0

            if current_level_idx in [10, 30]:
                boss_manager_system.update_logic(current_level_idx, all_platforms, player_x, player_karma, camera_speed, frame_mul, is_weakened=False)
                player_hitbox = pygame.Rect(player_x + 5, player_y + 5, 20, 20)
                player_obj_data = {'x': player_x, 'y': player_y}
                is_hit = boss_manager_system.check_collisions(player_hitbox, player_obj_data, all_vfx, save_manager)
                if is_hit:
                    screen_shake = 20
                    all_vfx.add(ScreenFlash((255, 0, 0), 150, 5))
                    all_vfx.add(ParticleExplosion(player_x + 15, player_y + 15, (200, 0, 0), 25))
                    player_x -= 40
                    y_velocity = -10
                    current_k = save_manager.get_karma()
                    damage = 75
                    if current_k > 0:
                        save_manager.update_karma(-damage)
                    elif current_k < 0:
                        save_manager.update_karma(damage)
                    new_k = save_manager.get_karma()
                    if abs(new_k) < 50:
                        save_manager.data["karma"] = 0
                        save_manager.save_data()
                        if current_level_idx == 10:
                            init_limbo()
                            GAME_STATE = 'PLAYING'
                            if npcs:
                                start_npc_conversation(npcs[0])
                        else:
                            GAME_STATE = 'GAME_OVER'
                            save_manager.update_high_score('easy_mode', current_level_idx, score)
                            audio_manager.stop_music()
                    else:
                        karma_notification_text = "İRADE HASAR ALDI!"
                        karma_notification_timer = 40

            lvl_config = EASY_MODE_LEVELS.get(current_level_idx, {})
            if lvl_config.get('type') == 'scrolling_boss' or current_level_idx == 30:
                boss_obj = None
                for e in all_enemies:
                    if isinstance(e, (NexusBoss, AresBoss, VasilBoss)):
                        boss_obj = e
                        break
                if boss_obj:
                    target_x = player_x + 550
                    boss_obj.x = target_x
                    boss_obj.rect.x = int(boss_obj.x)

            if GAME_STATE == 'PLAYING' and lvl_config.get('type') not in ('rest_area', 'beat_arena', 'manor_stealth'):
                base_goal = EASY_MODE_LEVELS.get(current_level_idx, EASY_MODE_LEVELS[1])['goal_score']
                lvl_goal = base_goal * 0.75
                # goal_score=0 olan bölümleri de standart kontrolden dışla
                # (Skor=0 → eşik=0 → ilk karede True → anlık kazanma hatası)
                if current_level_idx < 30 and lvl_goal > 0 and score >= lvl_goal:
                    if enemies_killed_current_level == 0:
                        save_manager.update_karma(50)
                        karma_notification_text = "PASİFİST BONUSU! (+50 KARMA)"
                    else:
                        save_manager.update_karma(5)
                    GAME_STATE = 'LEVEL_COMPLETE'
                    save_manager.unlock_next_level('easy_mode', current_level_idx)
                    save_manager.update_high_score('easy_mode', current_level_idx, score)

                all_platforms.update(camera_speed * frame_mul)

            all_enemies.update(camera_speed * frame_mul, dt, (player_x, player_y))
            for enemy in all_enemies:
                if hasattr(enemy, 'spawn_queue') and enemy.spawn_queue:
                    for projectile in enemy.spawn_queue:
                        all_enemies.add(projectile)
                enemy.spawn_queue = []

            if lvl_config.get('type') == 'boss_fight' or current_level_idx == 30:
                boss_alive = False
                boss_obj = None
                for e in all_enemies:
                    if isinstance(e, (NexusBoss, AresBoss, VasilBoss)):
                        boss_alive = True
                        boss_obj = e
                        break
                if not boss_alive and current_level_idx == 30:
                    score += 150000
                    audio_manager.stop_music()
                    final_karma = save_manager.get_karma()
                    ending_scenario = "GOOD_ENDING" if final_karma >= 0 else "BAD_ENDING"
                    ending_assets = asset_paths.copy()
                    ending_assets['scenario'] = ending_scenario
                    final_cutscene = AICutscene(screen, clock, ending_assets)
                    final_cutscene.run()
                    GAME_STATE = 'GAME_COMPLETE'
                    save_manager.update_high_score('easy_mode', current_level_idx, score)

            for s in stars:
                s.update(camera_speed * frame_mul)
            all_vfx.update(camera_speed * frame_mul)

            for trail in trail_effects[:]:
                try:
                    trail.update(camera_speed * frame_mul)
                except:
                    trail.update(camera_speed * frame_mul, dt)
                if trail.life <= 0:
                    trail_effects.remove(trail)

            if lvl_config.get('type') not in ('rest_area', 'beat_arena') and current_level_idx != 99:
                if current_level_idx <= 30:
                    if len(all_platforms) > 0 and max(p.rect.right for p in all_platforms) < LOGICAL_WIDTH + 100:
                        add_new_platform()

            if player_y > LOGICAL_HEIGHT + 100:
                if current_level_idx == 10:
                    init_limbo()
                    GAME_STATE = 'PLAYING'
                    if npcs:
                        start_npc_conversation(npcs[0])
                elif current_level_idx == 99:
                    player_y = LOGICAL_HEIGHT - 300
                    player_x = 100
                    y_velocity = 0
                elif lvl_config.get('type') == 'beat_arena':
                    # Arena zemininde yere gömme — sadece pozisyonu düzelt
                    player_y = LOGICAL_HEIGHT - 150
                    y_velocity = 0
                else:
                    GAME_STATE = 'GAME_OVER'
                    high_score = max(high_score, int(score))
                    save_manager.update_high_score('easy_mode', current_level_idx, score)
                    audio_manager.stop_music()
                    all_vfx.add(ParticleExplosion(player_x, player_y, (255, 0, 0), 30))

            if player_x < -50:
                if current_level_idx == 10:
                    init_limbo()
                    GAME_STATE = 'PLAYING'
                    if npcs:
                        start_npc_conversation(npcs[0])
                elif current_level_idx == 99:
                    player_x = 50
                elif lvl_config.get('type') == 'beat_arena':
                    player_x = 50   # Arena sınırı — soldan çıkış yok
                else:
                    GAME_STATE = 'GAME_OVER'
                    high_score = max(high_score, int(score))
                    save_manager.update_high_score('easy_mode', current_level_idx, score)
                    audio_manager.stop_music()
                    all_vfx.add(ParticleExplosion(player_x, player_y, (255, 0, 0), 30))
            
            # Arena sağ sınırı
            if lvl_config.get('type') == 'beat_arena' and player_x > LOGICAL_WIDTH - 50:
                player_x = LOGICAL_WIDTH - 50

            rest_area_manager.update((player_x, player_y))

        ui_data = {
            'theme': CURRENT_THEME,
            'score': score,
            'high_score': high_score,
            'dash_cd': dash_cooldown_timer,
            'slam_cd': slam_cooldown,
            'time_ms': time_ms,
            'settings': game_settings,
            'progress': loading_progress,
            'logs': loading_logs,
            'save_data': save_manager.data,
            'level_idx': current_level_idx,
            'level_data': EASY_MODE_LEVELS.get(current_level_idx, EASY_MODE_LEVELS[1]),
            'story_manager': story_manager,
            'philosophical_core': philosophical_core,
            'reality_shifter': reality_shifter,
            'time_layer': time_layer,
            'combat_philosophy': combat_philosophy,
            'endless_modes': endless_modes,
            'current_mode': endless_modes.current_mode if GAME_STATE == 'ENDLESS_PLAY' else None,
            'world_reactor': world_reactor,
            'npcs': npcs,
            'current_npc': current_npc,
            'npc_conversation_active': npc_conversation_active,
            'npc_chat_input': npc_chat_input,
            'npc_chat_history': npc_chat_history,
            'karma': player_karma,
            'kills': enemies_killed_current_level,
            'active_dash_max': active_dash_cd,
            'active_slam_max': active_slam_cd,
            'term_input': terminal_input,
            'term_status': terminal_status,
            'level_select_page': level_select_page,
            'has_talisman': has_talisman,
            # --- DÖVÜŞ SİSTEMİ ---
            'beat_arena_active': beat_arena.active,
            'arena_wave':  beat_arena.current_wave,
            'arena_total': beat_arena.total_waves,
            'combo_info':  combo_system.get_hud_info(),
            'player_hp':   player_hp.current_hp,
            'player_hp_max': player_hp.max_hp,
        }

        if GAME_STATE in ['MENU', 'SETTINGS', 'LOADING', 'LEVEL_SELECT', 'ENDLESS_SELECT', 'TERMINAL']:
            game_canvas.fill(DARK_BLUE)
            for s in stars:
                s.draw(game_canvas)
                s.update(0.5)
            active_ui_elements = render_ui(game_canvas, GAME_STATE, ui_data, mouse_pos)
        else:
            # ════════════════════════════════════════════════════════════════
            # ÇİZİM SIRASI — Bu sıra kesinlikle değiştirilmemeli.
            # Bir katman bir öncekinin üstüne biter; en son çizilen en üstte
            # görünür.
            #
            #  1. game_canvas.fill()          → Ekranı temizle
            #  2. active_background.draw()    → Uzak parallax arkaplan
            #  3. stars                       → Yıldızlar
            #  4. boss silhouette             → Arkaplan boss gölgesi
            #  5. platforms                   → Platformlar
            #  6. enemies / boss              → Düşmanlar
            #  7. npcs                        → NPC figürleri
            #  8. OYUNCU                      → Karakter (sprite/fallback)
            #  9. vasil_companion             → Yardımcı figür
            # 10. vfx_surface blit            → Partiküller / trail (oyuncunun
            #                                   üstünde değil — ÖNÜNDE)
            # 11. UI / HUD                    → Skor, karma, timer
            # 12. NPC chat / cinematic        → Diyalog kutuları
            # ════════════════════════════════════════════════════════════════

            # ── Kamera sarsma ofseti ─────────────────────────────────────
            try:
                anim_params = character_animator.get_draw_params()
            except:
                anim_params = {}
            anim_offset = anim_params.get('screen_shake_offset', (0, 0))
            global_offset = (
                random.randint(-screen_shake, screen_shake),
                random.randint(-screen_shake, screen_shake)
            ) if screen_shake > 0 else (0, 0)
            render_offset = (
                global_offset[0] + int(anim_offset[0]),
                global_offset[1] + int(anim_offset[1])
            )

            # ── Malikane kamera ofseti — platformları ve düşmanları kaydır ──
            # manor_stealth bölümünde tüm dünya nesneleri manor_camera_offset_x/y
            # kadar kaydırılarak çizilir; oyuncu ise ekran ortasında sabit görünür.
            _manor_draw_ox = -manor_camera_offset_x  # platform blit ofseti (negatif = sola kaydır)
            _manor_draw_oy = -manor_camera_offset_y  # dikey ofset (negatif = yukarı kaydır)
            _manor_render_offset = (
                render_offset[0] + _manor_draw_ox,
                render_offset[1] + _manor_draw_oy
            )

            # Render pipeline boyunca güvenli erişim için lvl_config garantisi
            lvl_config = EASY_MODE_LEVELS.get(current_level_idx, EASY_MODE_LEVELS[1])

            # ── 1. Ekranı temizle ────────────────────────────────────────
            if reality_shifter.current_reality != 0:
                reality_effect = reality_shifter.get_visual_effect()
                game_canvas.fill(reality_effect.get('bg_color', CURRENT_THEME["bg_color"]))
            elif time_layer.current_era != 'present':
                era_data = time_layer.eras[time_layer.current_era]
                game_canvas.fill(era_data.get('bg_color', CURRENT_THEME["bg_color"]))
            else:
                game_canvas.fill(CURRENT_THEME["bg_color"])

            # ── 2. Uzak parallax arkaplan ────────────────────────────────
            if active_background:
                active_background.draw(game_canvas)

            # ── 3. Yıldızlar ─────────────────────────────────────────────
            for s in stars:
                s.draw(game_canvas)

            # ── 4. Boss arkaplan gölgesi ─────────────────────────────────
            if current_level_idx in [10, 30]:
                current_k = save_manager.get_karma()
                draw_background_boss_silhouette(game_canvas, current_k, LOGICAL_WIDTH, LOGICAL_HEIGHT)

            # ── VFX yüzeyini sıfırla (henüz game_canvas'a bitmeyecek) ───
            vfx_surface.fill((0, 0, 0, 0))

            # ── 5. Platformlar ───────────────────────────────────────────
            for p in all_platforms:
                # Malikane bölümünde kamera oyuncuyu 2D takip eder;
                # platformlar X ve Y ofseti uygulanarak çizilir.
                _p_draw_rect = p.rect.move(_manor_draw_ox, _manor_draw_oy)
                _old_rect = p.rect
                p.rect = _p_draw_rect
                p.draw(game_canvas, CURRENT_THEME)
                p.rect = _old_rect

            # ── 6. Düşmanlar / Boss ──────────────────────────────────────
            boss_manager_system.draw(game_canvas)
            for e in all_enemies:
                # Malikane kamera ofseti (X ve Y) uygulanır
                if (_manor_draw_ox != 0 or _manor_draw_oy != 0) and hasattr(e, 'rect'):
                    _e_ox, _e_oy = e.rect.x, e.rect.y
                    e.rect.x += _manor_draw_ox
                    e.rect.y += _manor_draw_oy
                    e.draw(game_canvas, theme=CURRENT_THEME)
                    e.rect.x = _e_ox
                    e.rect.y = _e_oy
                else:
                    e.draw(game_canvas, theme=CURRENT_THEME)

            # ── 6b. Beat Arena Düşmanları + HUD ──────────────────────────
            if lvl_config.get('type') == 'beat_arena':
                beat_arena.draw(game_canvas)

            # ── Kombo sistemi hitbox (her bölümde) ───────────────────────
            combo_system.draw(vfx_surface)

            # ── Combat HUD (her bölümde) — can çubuğu + kombo zinciri ───
            # Can çubuğu: sadece arena bölümlerinde (normal bölümlerde anlık ölüm var)
            if lvl_config.get('type') == 'beat_arena':
                player_hp.draw_hud(game_canvas, 20, 20)
            # Kombo zinciri her bölümde görünür
            hud_info = combo_system.get_hud_info()
            if hud_info.get('chain') or hud_info.get('last_combo'):
                combat_hud.draw(game_canvas, hud_info)

            # VFX partikülleri ve trail'leri ayrı yüzeye çiz
            for v in all_vfx:
                v.draw(vfx_surface)
            for trail in trail_effects:
                trail.draw(vfx_surface)

            # ── 7. NPC'ler ───────────────────────────────────────────────
            for npc in npcs:
                npc.draw(game_canvas, render_offset)

            # ── 7b. Gizlilik katmanı (kameralar, vizyon konileri, şüphe HUD) ──
            stealth_system.draw(game_canvas, camera_offset=(_manor_draw_ox, _manor_draw_oy))

            # ── 8. OYUNCU ────────────────────────────────────────────────
            if GAME_STATE in ('PLAYING', 'PAUSED', 'GAME_OVER', 'LEVEL_COMPLETE',
                              'ENDLESS_PLAY', 'CHAT', 'CUTSCENE') and GAME_STATE != 'GAME_OVER':

                # Duruma göre renk belirle (fallback için kullanılır)
                p_color = CURRENT_THEME["player_color"]
                if is_dashing:
                    p_color = METEOR_CORE
                elif is_slamming:
                    p_color = PLAYER_SLAM
                elif is_super_mode:
                    p_color = (255, 215, 0)
                try:
                    modified_color = character_animator.get_modified_color(p_color)
                except:
                    modified_color = p_color

                # Talisman halkası — oyuncunun etrafında altın çember
                if has_talisman:
                    t = pygame.time.get_ticks() * 0.005
                    px, py = int(player_x + 15) + render_offset[0], int(player_y + 15) + render_offset[1]
                    radius = 35 + math.sin(t) * 5
                    pygame.draw.circle(game_canvas, (255, 215, 0), (px, py), int(radius), 2)
                    for i in range(3):
                        angle = t + (i * 2.09)
                        ox = math.cos(angle) * radius
                        oy = math.sin(angle) * radius
                        pygame.draw.circle(game_canvas, (255, 255, 200), (int(px + ox), int(py + oy)), 4)

                # ── Sprite karesini al ───────────────────────────────────
                current_sprite = character_animator.get_current_frame(
                    dt, character_state, player_direction
                )

                _px = int(player_x) + render_offset[0] + _manor_draw_ox
                _py = int(player_y) + render_offset[1] + _manor_draw_oy

                # ── DEBUG: print + sheet görselleştirme ──────────────────
                if DEBUG_SPRITE:
                    # ── 1. Sprite sheet'i bir kez yükle (lazy init) ──────
                    if _test_sheet is None:
                        try:
                            import os as _os
                            if _os.path.exists(_test_sheet_path):
                                _test_sheet = pygame.image.load(
                                    _test_sheet_path
                                ).convert_alpha()
                                print(
                                    f"[DEBUG] Sheet yüklendi: {_test_sheet_path} "
                                    f"→ boyut={_test_sheet.get_size()}"
                                )
                            else:
                                # Dosya yoksa hata vermemek için dummy surface
                                _test_sheet = pygame.Surface((1, 1), pygame.SRCALPHA)
                                print(
                                    f"[DEBUG] HATA: Sheet bulunamadı → {_test_sheet_path}\n"
                                    f"        Dosya yolunu ve klasör yapısını kontrol et."
                                )
                        except Exception as _e:
                            _test_sheet = pygame.Surface((1, 1), pygame.SRCALPHA)
                            print(f"[DEBUG] Sheet yüklenirken istisna: {_e}")

                    # ── 2. Sheet'i sol üst köşede göster ─────────────────
                    # Sadece gerçek bir surface ise (1×1 dummy değilse) blit et
                    if _test_sheet and _test_sheet.get_width() > 1:
                        # Sheet çok büyükse yarıya küçült, 400px'i geçmesin
                        _ts_w, _ts_h = _test_sheet.get_size()
                        _max_preview = 400
                        if _ts_w > _max_preview or _ts_h > _max_preview:
                            _scale_f = _max_preview / max(_ts_w, _ts_h)
                            _preview = pygame.transform.scale(
                                _test_sheet,
                                (int(_ts_w * _scale_f), int(_ts_h * _scale_f))
                            )
                        else:
                            _preview = _test_sheet

                        # Koyu yarı saydam arka plan — sheet görünürlüğü için
                        _bg = pygame.Surface(
                            (_preview.get_width() + 6, _preview.get_height() + 20),
                            pygame.SRCALPHA
                        )
                        _bg.fill((0, 0, 0, 180))
                        game_canvas.blit(_bg, (97, 97))
                        game_canvas.blit(_preview, (100, 100))

                        # Etiket: dosya adı + boyut bilgisi
                        _lbl_font = pygame.font.Font(None, 20)
                        _lbl = _lbl_font.render(
                            f"SHEET TEST: {_ts_w}x{_ts_h}px  |  DEBUG_SPRITE=True kapat",
                            True, (255, 255, 0)
                        )
                        game_canvas.blit(_lbl, (100, 100 + _preview.get_height() + 3))

                        # Sheet'in üstüne grid çiz: her 64px'de bir çizgi
                        _grid_color = (255, 0, 255)  # Magenta — kolayca görülür
                        _frame_size = 64             # Sprite frame boyutu (64×64)
                        _gx0, _gy0 = 100, 100
                        # Dikey çizgiler
                        for _gx in range(0, _preview.get_width() + 1, int(_frame_size * (_preview.get_width() / _ts_w))):
                            pygame.draw.line(
                                game_canvas, _grid_color,
                                (_gx0 + _gx, _gy0),
                                (_gx0 + _gx, _gy0 + _preview.get_height()), 1
                            )
                        # Yatay çizgiler
                        for _gy in range(0, _preview.get_height() + 1, int(_frame_size * (_preview.get_height() / _ts_h))):
                            pygame.draw.line(
                                game_canvas, _grid_color,
                                (_gx0, _gy0 + _gy),
                                (_gx0 + _preview.get_width(), _gy0 + _gy), 1
                            )

                    # ── 3. Konsolda koordinat yazdır (60 karede bir) ──────
                    _debug_print_counter += 1
                    if _debug_print_counter >= 60:
                        _debug_print_counter = 0
                        _sprite_info = (
                            f"{current_sprite.get_size()}" if current_sprite
                            else "None (sprite yüklenemedi — fallback aktif)"
                        )
                        print(
                            f"[DEBUG] player_x={player_x:.1f}  player_y={player_y:.1f} | "
                            f"render_offset={render_offset} | "
                            f"ekran_pos=({_px},{_py}) | "
                            f"state={character_state} | dir={player_direction} | "
                            f"Sprite={_sprite_info}"
                        )

                if DIRECT_SPRITE_TEST:
                    # ════════════════════════════════════════════════════
                    # YÜRÜME ANİMASYONU — 4 frame, 4×2 grid (üst satır)
                    # Sheet: 1024×1024 px
                    # Grid : 4 kolon × 2 satır → her frame 256×512 px
                    # Satır 0 (üst): sağa koşu → 4 frame yüklenir
                    # Satır 1 (alt): sola koşu → flip ile üretilir
                    # PNG: convert_alpha() — kendi şeffaflığını kullanır
                    # ════════════════════════════════════════════════════

                    if _direct_sprite is None:
                        import os as _os2

                        _COLS          = 4      # Yatay frame sayısı  (4×2 grid)
                        _ROWS          = 2      # Her iki satırı da yükle → 8 frame
                        _SHEET_FRAMES  = _COLS * _ROWS   # = 8
                        _SHEET_FRAME_W = 256    # Her frame genişliği (1024/4)
                        _SHEET_FRAME_H = 512    # Her frame yüksekliği (1024/2)
                        _DISPLAY_W     = 120    # Ekranda gösterilecek genişlik
                        _DISPLAY_H     = 180    # Ekranda gösterilecek yükseklik

                        _candidates = [
                            "assets/sprites/player_walk.png",
                            "assets/sprites/player/player_walk.png",
                            "assets/player_walk.png",
                            "player_walk.png",
                            _direct_sprite_path,
                        ]

                        _walk_frames = []
                        for _candidate in _candidates:
                            if _os2.path.exists(_candidate):
                                try:
                                    _sheet_raw = pygame.image.load(_candidate).convert_alpha()
                                    # PNG'nin kendi alpha kanalını kullan — colorkey gerekmez

                                    # Grid'i soldan sağa, yukarıdan aşağıya tara
                                    for _row in range(_ROWS):
                                        for _col in range(_COLS):
                                            _sx = _col * _SHEET_FRAME_W
                                            _sy = _row * _SHEET_FRAME_H

                                            _frame_surf = pygame.Surface(
                                                (_SHEET_FRAME_W, _SHEET_FRAME_H),
                                                pygame.SRCALPHA
                                            )
                                            _frame_surf.blit(
                                                _sheet_raw, (0, 0),
                                                (_sx, _sy, _SHEET_FRAME_W, _SHEET_FRAME_H)
                                            )
                                            _frame_scaled = pygame.transform.scale(
                                                _frame_surf, (_DISPLAY_W, _DISPLAY_H)
                                            )
                                            _walk_frames.append(_frame_scaled)

                                    print(
                                        f"[WALK] ✓ {_SHEET_FRAMES} frame yüklendi: {_candidate}\n"
                                        f"[WALK]   Grid: {_COLS}×{_ROWS}  "
                                        f"Ham: {_SHEET_FRAME_W}×{_SHEET_FRAME_H}  "
                                        f"→ Ekran: {_DISPLAY_W}×{_DISPLAY_H}"
                                    )
                                    break
                                except Exception as _le:
                                    print(f"[WALK] Yükleme hatası: {_le}")

                        if _walk_frames:
                            _direct_sprite = _walk_frames
                        else:
                            _fb = pygame.Surface((60, 90))
                            _fb.fill((255, 0, 100))
                            _fb.blit(pygame.font.Font(None, 40).render("?", True, (255,255,255)), (18, 30))
                            _direct_sprite = [_fb]
                            print("[WALK] ✗ Dosya bulunamadı! → assets/sprites/player_walk.png")

                    # ── Frame seç ────────────────────────────────────────
                    _frames_list = _direct_sprite if isinstance(_direct_sprite, list) else [_direct_sprite]
                    _ANIM_FPS    = 5.0
                    _anim_t      = (pygame.time.get_ticks() / 1000.0) % (len(_frames_list) / _ANIM_FPS)
                    _frame_idx   = int(_anim_t * _ANIM_FPS) % len(_frames_list)

                    # Idle'da dondur — yürürken animasyon oynar
                    if character_state == 'idle':
                        _frame_idx = 0

                    _cur_frame = _frames_list[_frame_idx]

                    # Sola gidince ters çevir
                    if player_direction == -1:
                        _cur_frame = pygame.transform.flip(_cur_frame, True, False)

                    # ── Hitbox hizalama ───────────────────────────────────
                    _hitbox_w, _hitbox_h = 28, 42
                    _sprite_w  = _cur_frame.get_width()
                    _sprite_h  = _cur_frame.get_height()
                    _off_x = (_hitbox_w - _sprite_w) // 2   # Yatay ortala
                    _off_y = _hitbox_h - _sprite_h           # Alt kenar hizala

                    _draw_x = int(player_x) + render_offset[0] + _off_x
                    _draw_y = int(player_y) + render_offset[1] + _off_y

                    # ── KARAKTERİ HER ZAMAN ÇİZ ──────────────────────────
                    game_canvas.blit(_cur_frame, (_draw_x, _draw_y))

                    # ── DEBUG KATMANI — sadece DEBUG_SPRITE açıksa ───────
                    if DEBUG_SPRITE:
                        game_canvas.blit(_cur_frame, (200, 200))
                        _lf = pygame.font.Font(None, 20)
                        game_canvas.blit(
                            _lf.render(f"FRAME {_frame_idx+1}/{len(_frames_list)}  |  {character_state}", True, (255,255,0)),
                            (200, 185)
                        )
                        pygame.draw.rect(game_canvas, (255, 255, 0),
                            (_draw_x, _draw_y, _sprite_w, _sprite_h), 2)
                        pygame.draw.rect(game_canvas, (0, 255, 255),
                            (int(player_x) + render_offset[0],
                             int(player_y) + render_offset[1],
                             _hitbox_w, _hitbox_h), 1)

                elif current_sprite is not None:
                    # ── NORMAL SPRITE MODU ───────────────────────────────
                    _sw, _sh = current_sprite.get_size()
                    _target_w, _target_h = 28, 42

                    if _sw != _target_w or _sh != _target_h:
                        current_sprite = pygame.transform.scale(
                            current_sprite, (_target_w, _target_h)
                        )

                    try:
                        _params  = character_animator.get_draw_params()
                        _sx      = _params.get('squash',   1.0)
                        _sy      = _params.get('stretch',  1.0)
                        _sc      = _params.get('scale',    1.0)
                        _rot_deg = math.degrees(_params.get('rotation', 0.0))
                        _new_w   = max(1, int(_target_w * _sx * _sc))
                        _new_h   = max(1, int(_target_h * _sy * _sc))
                        if _new_w != _target_w or _new_h != _target_h:
                            current_sprite = pygame.transform.scale(
                                current_sprite, (_new_w, _new_h)
                            )
                        if abs(_rot_deg) > 0.5:
                            current_sprite = pygame.transform.rotate(
                                current_sprite, -_rot_deg
                            )
                        _blit_x = _px - (current_sprite.get_width()  - _target_w) // 2
                        _blit_y = _py - (current_sprite.get_height() - _target_h) // 2
                    except Exception:
                        _blit_x, _blit_y = _px, _py

                    game_canvas.blit(current_sprite, (_blit_x, _blit_y))

                    if DEBUG_SPRITE:
                        pygame.draw.rect(
                            game_canvas, (255, 0, 0),
                            (_px, _py, 28, 42), 2
                        )

                else:
                    # ── FALLBACK: Placeholder dikdörtgen ─────────────────
                    _pw, _ph = 28, 42
                    _ps = pygame.Surface((_pw, _ph), pygame.SRCALPHA)
                    _ps.fill((*modified_color[:3], 100))
                    game_canvas.blit(_ps, (_px, _py))
                    pygame.draw.rect(game_canvas, modified_color, (_px, _py, _pw, _ph), 2)

                    if DEBUG_SPRITE:
                        pygame.draw.rect(
                            game_canvas, (255, 0, 0),
                            (_px, _py, _pw, _ph), 2
                        )
            # ── 8. OYUNCU SONU ───────────────────────────────────────────

            # ── 9. Yardımcı figür ────────────────────────────────────────
            if vasil_companion:
                vasil_companion.draw(game_canvas)

            # ── 10. VFX partikülleri game_canvas üstüne blit ────────────
            # NOT: vfx_surface oyuncunun üstüne değil, render_offset ile
            # kamera sarsmasını yansıtarak blit edilir. Trail/partiküller
            # oyuncunun üstünde görünür — bu kasıtlı (ön plan efekti).
            game_canvas.blit(vfx_surface, render_offset)

            # ── DEBUG TOGGLE BUTONU (her zaman en üstte) ────────────────
            # Renk: açıkken yeşil, kapalıyken gri; hover'da parlıyor.
            if DEBUG_SPRITE:
                _btn_bg    = (0, 160, 0)   if _debug_btn_hover else (0, 110, 0)
                _btn_bdr   = (0, 255, 50)
                _btn_label = "■ DEBUG KAPAT"
            else:
                _btn_bg    = (60, 60, 60)  if _debug_btn_hover else (35, 35, 35)
                _btn_bdr   = (120, 120, 120)
                _btn_label = "□ DEBUG AÇ"
            # Yarı saydam arka plan
            _btn_surf = pygame.Surface(
                (_DEBUG_BTN_RECT.width, _DEBUG_BTN_RECT.height), pygame.SRCALPHA
            )
            _btn_surf.fill((*_btn_bg, 210))
            game_canvas.blit(_btn_surf, _DEBUG_BTN_RECT.topleft)
            # Çerçeve
            pygame.draw.rect(game_canvas, _btn_bdr, _DEBUG_BTN_RECT, 1)
            # Metin
            _btn_txt = _debug_btn_font.render(_btn_label, True, (220, 220, 220))
            _btn_txt_x = _DEBUG_BTN_RECT.x + (_DEBUG_BTN_RECT.width  - _btn_txt.get_width())  // 2
            _btn_txt_y = _DEBUG_BTN_RECT.y + (_DEBUG_BTN_RECT.height - _btn_txt.get_height()) // 2
            game_canvas.blit(_btn_txt, (_btn_txt_x, _btn_txt_y))
            # ─────────────────────────────────────────────────────────────

            # Karma bildirimi
            if karma_notification_timer > 0:
                font = pygame.font.Font(None, 40)
                color = (255, 50, 50) if "DÜŞTÜ" in karma_notification_text else (0, 255, 100)
                if "DİRİLİŞ" in karma_notification_text:
                    color = (200, 50, 200)
                draw_text_with_shadow(game_canvas, karma_notification_text, font,
                                     (LOGICAL_WIDTH//2, LOGICAL_HEIGHT//2 - 100), color, align="center")

            # Bölüm 30 hayatta kalma sayacı
            if current_level_idx == 30 and not finisher_active:
                remaining = max(0, 120 - level_15_timer)
                mins = int(remaining // 60)
                secs = int(remaining % 60)
                time_str = f"HAYATTA KAL: {mins:02}:{secs:02}"
                text_color = (255, 50, 50) if frame_count % 60 < 30 else (255, 255, 255)
                font_timer = pygame.font.Font(None, 60)
                draw_text_with_shadow(game_canvas, time_str, font_timer,
                                     (LOGICAL_WIDTH//2, 80), text_color, align="center")

            # ── 11. NPC sohbet / sinematik katman ───────────────────────
            if GAME_STATE == 'NPC_CHAT':
                draw_npc_chat(game_canvas, current_npc, npc_chat_history,
                              npc_chat_input, npc_show_cursor, LOGICAL_WIDTH, LOGICAL_HEIGHT)

            if GAME_STATE in ['CHAT', 'CUTSCENE']:
                active_ui_elements = draw_cinematic_overlay(
                    game_canvas, story_manager, time_ms, mouse_pos
                )

            # Dinlenme alanı tuş ipuçları
            if GAME_STATE == 'PLAYING':
                lvl_config = EASY_MODE_LEVELS.get(current_level_idx, EASY_MODE_LEVELS[1])
                if lvl_config.get('type') == 'rest_area':
                    font = pygame.font.Font(None, 24)
                    instructions = [
                        "E: NPC ile konuş", "T: Sonraki bölüme geç",
                        "WASD: Hareket et", "Sağa git → Otomatik geçiş"
                    ]
                    y_offset = LOGICAL_HEIGHT - 120
                    for instruction in instructions:
                        text_surf = font.render(instruction, True, (200, 255, 200))
                        game_canvas.blit(text_surf, (40, y_offset))
                        y_offset += 25
                elif lvl_config.get('type') == 'beat_arena':
                    font = pygame.font.Font(None, 24)
                    instructions = [
                        "J: Hafif Vuruş    K: Ağır Vuruş",
                        "WASD: Hareket / Zıplama",
                        "Kombo: J+J+J / J+J+K / H+H ...",
                        "Tüm dalgaları temizle → Bölüm geçer"
                    ]
                    y_offset = LOGICAL_HEIGHT - 105
                    for instruction in instructions:
                        text_surf = font.render(instruction, True, (255, 200, 100))
                        game_canvas.blit(text_surf, (40, y_offset))
                        y_offset += 25
                elif lvl_config.get('type') == 'manor_stealth':
                    # Malikane özel HUD: suikast ipucu + aktif muhafız sayacı
                    _mfont = pygame.font.Font(None, 24)
                    _guard_count = stealth_system.active_guard_count()
                    _manor_hints = [
                        "F: Sessiz Suikast (Arkadan, Şüphe < %50)",
                        "WASD: Hareket   SPACE: Dash",
                        f"Aktif Muhafız: {_guard_count}",
                        "Hedef: Gizli Kasaya Ulaş →",
                    ]
                    _mhud_y = LOGICAL_HEIGHT - 100
                    for _mh in _manor_hints:
                        _mh_surf = _mfont.render(_mh, True, (200, 150, 80))
                        game_canvas.blit(_mh_surf, (40, _mhud_y))
                        _mhud_y += 24
                else:
                    # Normal bölümlerde köşede kısa ipucu
                    _hint_font = pygame.font.Font(None, 22)
                    _hint = _hint_font.render("J: Hafif  K: Ağır  SPACE: Dash  S↓: Slam", True, (180, 180, 180))
                    game_canvas.blit(_hint, (LOGICAL_WIDTH - _hint.get_width() - 12, LOGICAL_HEIGHT - 30))

            # Yakındaki NPC ekosistemi figürleri
            for npc in npc_ecosystem:
                if abs(npc.x - player_x) < 500 and abs(npc.y - player_y) < 400:
                    npc.draw(game_canvas, render_offset)

            # ── 12. UI / HUD (en üstte) ─────────────────────────────────
            if GAME_STATE not in ['CHAT', 'CUTSCENE']:
                current_score_int = int(score)
                should_update_ui = (
                    cached_ui_surface is None or
                    current_score_int != last_score or
                    frame_count % 10 == 0
                )
                if should_update_ui:
                    last_score = current_score_int
                    cached_ui_surface = pygame.Surface(
                        (LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA
                    )
                    last_active_ui_elements = render_ui(
                        cached_ui_surface, GAME_STATE, ui_data, mouse_pos
                    )
                game_canvas.blit(cached_ui_surface, (0, 0))
                active_ui_elements = last_active_ui_elements

        target_res = AVAILABLE_RESOLUTIONS[game_settings['res_index']]
        if game_settings['fullscreen']:
            if target_res != (LOGICAL_WIDTH, LOGICAL_HEIGHT):
                scaled_small = pygame.transform.scale(game_canvas, target_res)
                final_game_image = pygame.transform.scale(scaled_small, screen.get_size())
            else:
                final_game_image = pygame.transform.scale(game_canvas, screen.get_size())
        else:
            final_game_image = pygame.transform.scale(game_canvas, screen.get_size())

        master_vol = game_settings.get("sound_volume", 0.7)
        music_vol = game_settings.get("music_volume", 0.5)
        effects_vol = game_settings.get("effects_volume", 0.8)

        if 'AMBIENT_CHANNEL' in locals() and AMBIENT_CHANNEL:
            try:
                AMBIENT_CHANNEL.set_volume(master_vol * music_vol)
            except Exception:
                pass

        if 'FX_CHANNEL' in locals() and FX_CHANNEL:
            try:
                FX_CHANNEL.set_volume(master_vol * effects_vol)
            except Exception:
                pass

        screen.blit(final_game_image, (0, 0))
        pygame.display.flip()
        clock.tick(current_fps)

if __name__ == '__main__':
    main()