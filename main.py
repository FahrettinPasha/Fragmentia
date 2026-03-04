# main.py
from entities import BlankBackground, ParallaxBackground, Platform, Star, CursedEnemy, NPC, DroneEnemy, TankEnemy, HealthOrb
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
from settings import (COST_DASH, COST_SLAM, COST_HEAVY, COST_LIGHT,
                      PLAYER_MAX_STAMINA, STAMINA_REGEN_RATE, STAMINA_REGEN_DELAY,
                      REVOLVER_MAX_BULLETS, REVOLVER_DAMAGE, REVOLVER_COOLDOWN,
                      REVOLVER_RELOAD_TIME, PLAYER_BULLET_SPEED)
from auxiliary_systems import RestAreaManager, NexusHub, PhilosophicalCore, RealityShiftSystem, TimeLayerSystem
from auxiliary_systems import CombatPhilosophySystem, LivingSoundtrack, EndlessFragmentia, ReactiveFragmentia, LivingNPC
from auxiliary_systems import FragmentiaDistrict, PhilosophicalTitan, WarpLine
from drawing_utils import rotate_point, draw_legendary_revolver, draw_smg_placeholder, draw_cinematic_overlay, draw_background_hero, get_weapon_muzzle_point
from drawing_utils import draw_background_boss_silhouette, draw_npc_chat
from local_bosses import NexusBoss, AresBoss, VasilBoss, EnemyBullet, draw_vasil_arena_bg

# --- GÜNCEL UTILS IMPORT (audio_manager eklendi) ---
from utils import generate_sound_effect, generate_ambient_fallback, generate_calm_ambient, load_sound_asset, draw_text, draw_animated_player, wrap_text, draw_text_with_shadow, get_silent_sound, audio_manager
from vfx import LightningBolt, FlameSpark, GhostTrail, SpeedLine, Shockwave, EnergyOrb, ParticleExplosion, ScreenFlash, SavedSoul
from bullet_visuals import draw_player_bullet
# YENİ: ParallaxBackground eklendi (BlankBackground yerine)
from entities import BlankBackground, ParallaxBackground, Platform, Star, CursedEnemy, NPC, DroneEnemy, TankEnemy, HealthOrb, PlayerProjectile, WeaponChest, AmmoPickup
from ui_system import render_ui
from animations import CharacterAnimator, TrailEffect
from save_system import SaveManager
from story_system import StoryManager
from cutscene import AICutscene, IntroCutscene, VasilDefeatScene

# --- BEAT 'EM UP / DÖVÜŞ SİSTEMİ ---
from combat_system import (
    ComboSystem, BeatArenaManager, PlayerHealth, CombatHUD
)

# --- SİLAH SİSTEMİ ---
from weapon_system import Revolver, SMG, Shotgun, create_weapon
from inventory_manager import inventory_manager  # Merkezi envanter sistemi

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
_traj_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)  # Trajectory ızgara

# --- 2. SES AYARLARI ---
# Ses kanalları artık audio_manager üzerinden yönetiliyor.

# Ses dosyaları
DASH_SOUND = load_sound_asset("assets/sfx/dash.wav")
SLAM_SOUND = load_sound_asset("assets/sfx/slam.wav")
EXPLOSION_SOUND = get_silent_sound()
GUN_SHOT_SOUND = load_sound_asset("assets/sfx/gun_shot.wav")
RELOAD_SOUND   = load_sound_asset("assets/sfx/reload.wav")

current_level_music = None
# --- OPTİMİZASYON 3: VFX Limiti Azaltıldı ---
MAX_VFX_COUNT = 100 # 200'den 100'e çekildi (CPU rahatlatma)
MAX_DASH_VFX_PER_FRAME = 5
METEOR_CORE = (255, 255, 200)
METEOR_FIRE = (255, 80, 0)

# --- 3. DURUM DEĞİŞKENLERİ ---
GAME_STATE = 'MENU'
vasil_companion = None
vasil_intro_kill_pending = False  # VasilBoss.kill_player sinyali
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
jumps_left = MAX_JUMPS
dash_timer = 0
screen_shake = 0
dash_particles_timer = 0
dash_angle = 0.0
dash_frame_counter = 0.0
character_state = 'idle'
slam_collision_check_frames = 0
active_damage_waves = []

active_player_speed = PLAYER_SPEED
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
all_health_orbs = pygame.sprite.Group()  # Can küreleri
all_player_projectiles = pygame.sprite.Group()  # Oyuncu mermileri (altıpatar)
all_weapon_chests = pygame.sprite.Group()  # Silah sandıkları
all_ammo_pickups  = pygame.sprite.Group()  # Cephane pickup'ları

# --- AKTİF SİLAH SİSTEMİ ---
# active_weapon_obj : Weapon alt sınıfı nesnesi (Revolver / SMG) veya None
# inventory_weapons : Kuşanılmış silahların türlerini tutan liste (switch için)
active_weapon_obj  = None      # Başlangıçta silahsız
inventory_weapons  = []        # Açılmış silahlar listesi
# Ölüm anında envanterin anlık görüntüsü — respawn'da geri yüklenir
_death_inventory_snapshot: list = []   # [(weapon_type, bullets, spare_mags), ...]
_death_active_type: str | None  = None
weapon_shoot_timer = 0.0       # Çizim için atış zamanı sayacı (sn)
aim_angle          = 0.0       # Fare nişangah açısı (radyan) — her frame güncellenir
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
    elif width >= CHEST_MIN_PLATFORM_W and random.random() < CHEST_SPAWN_CHANCE:
        # Düşmansız yeterince geniş platformlarda sandık çıkar
        chest = WeaponChest(new_plat.rect)
        all_weapon_chests.add(chest)

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

def init_vasil_intro_fight():
    """Level 0: Vasil intro boss fight. Oyuncu silahsız, Vasil yenilemez."""
    global player_x, player_y, y_velocity, camera_speed, CURRENT_THEME
    global all_platforms, all_enemies, all_vfx, npcs, current_level_idx
    global active_background, boss_manager_system
    global active_weapon_obj, inventory_weapons, player_bullets
    global gun_cooldown, is_reloading, vasil_intro_kill_pending

    boss_manager_system.reset()
    current_level_idx = 0
    camera_speed = 0
    y_velocity   = 0

    all_platforms.empty()
    all_enemies.empty()
    all_vfx.empty()
    npcs.clear()

    CURRENT_THEME = THEMES[1]

    # ═══════════════════════════════════════════════════════════════════
    # VASİL INTRO ARENA — Sonsuz düz zemin
    # camera_speed = 0 ama oyuncu X ekseninde serbestçe hareket eder.
    # Dünya genişliği: LOGICAL_WIDTH * 6  →  Pratik olarak sonsuz.
    # Boss player'ı lerp ile takip eder (aşağıda game loop'ta).
    # ═══════════════════════════════════════════════════════════════════

    LW = LOGICAL_WIDTH
    LH = LOGICAL_HEIGHT
    TH = 1

    # ── Tek düz sonsuz zemin platformu ───────────────────────────────
    all_platforms.add(Platform(-LW * 3, LH - 80, LW * 6, 80, theme_index=TH))

    active_background = ParallaxBackground(f"{BG_DIR}/gutter_far.png", speed_mult=0.0)

    player_x, player_y = 180.0, float(LOGICAL_HEIGHT - 80 - 42)  # Düz zemin üstü
    # ── VASIL INTRO: Tüm silahları 5'er yedek şarjörle ver ──────────────────
    # Oyuncu elinden geleni yapacak ama boss yine de yenilemez.
    inventory_manager.reset()
    inventory_weapons = []           # Legacy referans — korunuyor
    gun_cooldown      = 0.0
    is_reloading      = False
    for _intro_wtype in ['revolver', 'smg', 'shotgun']:
        _intro_wpn = create_weapon(_intro_wtype, spare_mags=5)
        if _intro_wpn:
            inventory_manager.unlock(_intro_wtype, _intro_wpn)
    inventory_manager.switch_to('revolver')
    active_weapon_obj = inventory_manager.active_weapon
    player_bullets    = active_weapon_obj.bullets if active_weapon_obj else 0

    vasil = VasilBoss(LOGICAL_WIDTH // 2, LOGICAL_HEIGHT - 80 - 130)  # Düz zemin üstünde hover
    vasil.ignore_camera_speed = True
    all_enemies.add(vasil)
    vasil_intro_kill_pending = False

    music = load_sound_asset("assets/music/final_boss.mp3", generate_ambient_fallback, 0.8)
    audio_manager.play_music(music)


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
    global is_jumping, is_dashing, is_slamming, dash_timer, slam_stall_timer
    global CURRENT_THEME, CURRENT_SHAPE, screen_shake, dash_particles_timer, dash_angle, dash_frame_counter
    global character_state, trail_effects, last_trail_time, slam_collision_check_frames, active_damage_waves
    global CURRENT_THEME, current_level_music, npcs, current_npc, npc_conversation_active
    global player_karma, enemies_killed_current_level, karma_notification_timer, karma_notification_text
    global active_player_speed
    global has_revived_this_run, has_talisman
    global boss_manager_system, vasil_companion
    global level_15_timer, finisher_active, finisher_state_timer, finisher_type, level_15_cutscene_played
    global active_background # Global active_background
    global cached_ui_surface, last_score # UI Cache
    global combo_system, beat_arena, player_hp
    global all_health_orbs
    global all_player_projectiles, all_weapon_chests, all_ammo_pickups
    global player_bullets, gun_cooldown, is_reloading
    global active_weapon_obj, inventory_weapons, weapon_shoot_timer

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
    boss_manager_system.reset()
    # --- DÖVÜŞ SİSTEMİ SIFIRLA ---
    combo_system.reset()
    beat_arena.reset()
    player_hp = PlayerHealth(ARENA_PLAYER_HP,
                             max_stamina=PLAYER_MAX_STAMINA,
                             stamina_regen=STAMINA_REGEN_RATE)
    all_health_orbs.empty()
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
        # Güvenli başlangıç: zemin kat (Y_G=1000) üstü, player_h=30 → y=970
        player_x, player_y = 120.0, float(LOGICAL_HEIGHT - 110)
        y_velocity = 0
        music_file = lvl_config.get('music_file', 'dark_ambient.mp3')
        current_level_music = load_sound_asset(
            f"assets/music/{music_file}", generate_ambient_fallback, 0.5
        )
        audio_manager.play_music(current_level_music)

        # ══════════════════════════════════════════════════════════════════
        # MALİKANE BİNA PLANI — Tüm Y koordinatları ekran içinde
        # ──────────────────────────────────────────────────────────────────
        #  Ölüm eşiği: player_y > LOGICAL_HEIGHT + 100 = 1180
        #  → Tüm Y değerleri < 1050 tutulur (güvenli marj)
        #
        #  KAT Y TABANLARI (platform.rect.top):
        #   Zemin  Y_G  = LH - 80   = 1000
        #   1. Kat Y_F1 = LH - 290  =  790
        #   2. Kat Y_F2 = LH - 510  =  570
        #   Çatı   Y_RF = LH - 730  =  350
        #
        #  Oyuncu başlangıcı: x=120, y=Y_G-30=970  ← platform üstüne oturur
        #  Gizli Kasa:        x≈2910, y=Y_RF-120=230 (kasa platformu üstü)
        #  Harita: 3200px geniş; dikey span 730px → kamera Y ofseti = 0
        # ══════════════════════════════════════════════════════════════════
        all_platforms.empty()
        _ti = theme_idx
        _LH = LOGICAL_HEIGHT   # 1080

        Y_G  = _LH - 80    # 1000 — Zemin kat
        Y_F1 = _LH - 290   #  790 — 1. Kat
        Y_F2 = _LH - 510   #  570 — 2. Kat
        Y_RF = _LH - 730   #  350 — Çatı / Kasa katı
        T = 20              # Platform kalınlığı
        W = 18              # Duvar kalınlığı

        # ─── DIŞ YAPI ─────────────────────────────────────────────────────
        all_platforms.add(Platform(40,   Y_RF, W, _LH - Y_RF + 80, theme_index=_ti))  # Sol dış duvar
        all_platforms.add(Platform(3160, Y_RF, W, _LH - Y_RF + 80, theme_index=_ti))  # Sağ dış duvar

        # ─── ZEMİN KAT (Y_G = 1000) ──────────────────────────────────────
        all_platforms.add(Platform(60,   Y_G, 860, T, theme_index=_ti))   # Giriş holü
        all_platforms.add(Platform(920,  Y_F1 + T, W, Y_G - Y_F1, theme_index=_ti))  # Duvar 1
        all_platforms.add(Platform(940,  Y_G, 960, T, theme_index=_ti))   # Güvenlik odası
        all_platforms.add(Platform(1900, Y_F1 + T, W, Y_G - Y_F1, theme_index=_ti))  # Duvar 2
        all_platforms.add(Platform(1920, Y_G, 1240, T, theme_index=_ti))  # Depo/koridor

        # ─── ZEMİN → 1. KAT MERDİVENLERİ ────────────────────────────────
        # Sol merdiven: 4 basamak × 52px yükselir (giriş holünden)
        for _s in range(4):
            all_platforms.add(Platform(130 + _s * 95, Y_G - (_s + 1) * 52, 100, T, theme_index=_ti))
        # Sağ merdiven: 4 basamak (depodan)
        for _s in range(4):
            all_platforms.add(Platform(2600 + _s * 95, Y_G - (_s + 1) * 52, 100, T, theme_index=_ti))

        # ─── 1. KAT (Y_F1 = 790) ─────────────────────────────────────────
        all_platforms.add(Platform(60,   Y_F1, 1240, T, theme_index=_ti))   # Kütüphane
        all_platforms.add(Platform(1300, Y_F2 + T, W, Y_F1 - Y_F2, theme_index=_ti))  # Duvar 1a
        all_platforms.add(Platform(1320, Y_F1, 1840, T, theme_index=_ti))   # Ofis/güvenlik

        # ─── 1. KAT → 2. KAT MERDİVENLERİ ───────────────────────────────
        # Orta merdiven: 4 basamak × 55px
        for _s in range(4):
            all_platforms.add(Platform(1090 + _s * 95, Y_F1 - (_s + 1) * 55, 105, T, theme_index=_ti))
        # Sağ merdiven: 4 basamak
        for _s in range(4):
            all_platforms.add(Platform(2780 + _s * 90, Y_F1 - (_s + 1) * 55, 100, T, theme_index=_ti))

        # ─── 2. KAT (Y_F2 = 570) ─────────────────────────────────────────
        all_platforms.add(Platform(60,   Y_F2, 3100, T, theme_index=_ti))   # Tam kat zemini
        # Havalandırma rafları (gizlenme/atlama)
        all_platforms.add(Platform(350,  Y_F2 - 130, 160, T, theme_index=_ti))
        all_platforms.add(Platform(620,  Y_F2 - 240, 160, T, theme_index=_ti))
        all_platforms.add(Platform(900,  Y_F2 - 130, 160, T, theme_index=_ti))
        all_platforms.add(Platform(1700, Y_F2 - 130, 160, T, theme_index=_ti))
        all_platforms.add(Platform(2000, Y_F2 - 240, 160, T, theme_index=_ti))
        all_platforms.add(Platform(2400, Y_F2 - 130, 160, T, theme_index=_ti))
        all_platforms.add(Platform(2200, Y_RF + T, W, Y_F2 - Y_RF, theme_index=_ti))  # Sunucu odası duvarı

        # ─── 2. KAT → ÇATI MERDİVENLERİ ─────────────────────────────────
        # Sağ köşe: 5 basamak × 72px
        for _s in range(5):
            all_platforms.add(Platform(2480 + _s * 80, Y_F2 - (_s + 1) * 72, 90, T, theme_index=_ti))

        # ─── ÇATI / KASA KATI (Y_RF = 350) ───────────────────────────────
        all_platforms.add(Platform(60,   Y_RF, 1740, T, theme_index=_ti))   # Sol çatı terası
        # x=1800–2000 arası açık (havalandırma boşluğu)
        all_platforms.add(Platform(2000, Y_RF, 1160, T, theme_index=_ti))   # Kasa odası zemini
        # KASA PLATFORMU — hedef: x=2700, y=Y_RF-120=230
        all_platforms.add(Platform(2700, Y_RF - 120, 420, T + 8, theme_index=_ti))

    elif lvl_config.get('type') == 'debug_arena':
        # ─────────────────────────────────────────────────────────────────
        # DEBUG ARENA BAŞLATMA
        # Kamera: 0 (sabit), Düşman: yok, Skor hedefi: yok
        # Tek devasa zemin platformu — oyuncu tam ortaya doğar.
        # ─────────────────────────────────────────────────────────────────
        camera_speed = 0
        CURRENT_THEME = THEMES[theme_idx]
        all_platforms.empty()
        all_enemies.empty()
        all_vfx.empty()
        # Tam ekran genişliğinde zemin platformu
        _debug_floor = Platform(0, LOGICAL_HEIGHT - 80, LOGICAL_WIDTH, 80, theme_index=theme_idx)
        all_platforms.add(_debug_floor)
        # Orta yükseklikte iki test platformu (zıplama testi için)
        all_platforms.add(Platform(LOGICAL_WIDTH // 2 - 200, LOGICAL_HEIGHT - 280, 400, 30, theme_index=theme_idx))
        all_platforms.add(Platform(LOGICAL_WIDTH // 2 - 100, LOGICAL_HEIGHT - 480, 200, 30, theme_index=theme_idx))
        # Oyuncu platform ortasına spawn — platform_top - PLAYER_H
        player_x = float(LOGICAL_WIDTH // 2 - 14)
        player_y = float(LOGICAL_HEIGHT - 80 - 42)
        y_velocity = 0
        # ── DEBUG ARENA: Her iki silahı ver, sınırsız cephane ─────────────
        _DEBUG_MAG = 9999
        for _dbg_wtype in ('revolver', 'smg', 'shotgun'):
            _dbg_wpn = create_weapon(_dbg_wtype, spare_mags=_DEBUG_MAG)
            if _dbg_wpn:
                _dbg_wpn.bullets    = _dbg_wpn.mag_size
                _dbg_wpn.spare_mags = _DEBUG_MAG
                inventory_manager.unlock(_dbg_wtype, _dbg_wpn)
                if _dbg_wtype not in inventory_weapons:
                    inventory_weapons.append(_dbg_wtype)
        # Revolver'ı aktif kuşan (1: Revolver, 2: SMG, 3: Pompalı)
        inventory_manager.switch_to('revolver')
        active_weapon_obj = inventory_manager.active_weapon
        if active_weapon_obj:
            active_weapon_obj.spare_mags = _DEBUG_MAG
            player_bullets = active_weapon_obj.bullets
        gun_cooldown = 0.0
        is_reloading = False
        karma_notification_text  = "DEBUG ARENA | 1:Revolver 2:SMG 3:Pompalı | T:Terminal | Num1-3:Spawn"
        karma_notification_timer = 180
        music_file = lvl_config.get('music_file', 'calm_ambient.mp3')
        current_level_music = load_sound_asset(
            f"assets/music/{music_file}", generate_calm_ambient, 0.5
        )
        audio_manager.play_music(current_level_music)

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

    y_velocity = score = dash_timer = screen_shake = slam_stall_timer = 0
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

    # ── Silah sistemi sıfırla ─────────────────────────────────────────────────
    # Başlangıçta silahsız — sandıktan alınacak.
    # Önceki bölümdeki silah ve cephane gruplarını temizle.
    all_weapon_chests.empty()
    all_ammo_pickups.empty()
    active_weapon_obj  = None    # Bölüm başında silahsız
    weapon_shoot_timer = 0.0
    # inventory_weapons listesi bölümler arası korunur — silmiyoruz.
    # (Bir kez kazanılan silah bir sonraki bölüme taşınır.)
    #
    # InventoryManager'dan aktif silahı geri yükle (tipe göre doğru nesne)
    if inventory_manager.unlocked_weapons:
        _restore_type = inventory_manager.active_type or inventory_manager.unlocked_weapons[0]
        inventory_manager.switch_to(_restore_type)   # per-type dict'ten doğru nesneyi alır
        active_weapon_obj = inventory_manager.active_weapon
        if active_weapon_obj is not None:
            _b, _s = inventory_manager.ammo_state()
            active_weapon_obj.bullets    = _b
            active_weapon_obj.spare_mags = _s
            player_bullets = _b

    # ── Altıpatar (eski sistem) uyumluluk sıfırlaması ─────────────────────────
    if active_weapon_obj is None:
        player_bullets = 0   # Silahsız → ateş yok (inventory'den alınmadan çalışmamalı)
    gun_cooldown    = 0.0
    is_reloading    = False
    all_player_projectiles.empty()

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
    global slam_stall_timer, jumps_left, dash_timer
    global screen_shake, character_state, current_level_idx, high_score
    global dash_vx, dash_vy, dash_particles_timer, dash_angle, dash_frame_counter
    global slam_collision_check_frames, active_damage_waves, trail_effects, last_trail_time
    global CURRENT_THEME, CURRENT_SHAPE, loading_progress, frame_count
    global current_npc, npc_conversation_active, npc_chat_input, npc_chat_history
    global npc_show_cursor, npc_cursor_timer, npc_typing_timer, npcs
    global active_ui_elements
    global player_karma, enemies_killed_current_level, karma_notification_timer, karma_notification_text
    global active_player_speed
    global has_revived_this_run, has_talisman
    global level_select_page, vasil_companion
    global boss_manager_system
    global level_15_timer, finisher_active, finisher_state_timer, finisher_type, level_15_cutscene_played
    global game_settings
    global active_background
    global cached_ui_surface, last_score, last_active_ui_elements
    global combo_system, beat_arena, player_hp, combat_hud
    global vasil_intro_kill_pending
    global player_bullets, gun_cooldown, is_reloading, all_player_projectiles
    global active_weapon_obj, inventory_weapons, weapon_shoot_timer
    global all_weapon_chests, all_ammo_pickups
    global aim_angle

    is_super_mode  = False
    is_god_hp      = False   # "god hp on"   → her kare canı tam doldur
    is_god_stamina = False   # "god stam on" → her kare staminayı tam doldur
    # Malikane bölümü için kamera X ve Y ofseti (oyuncuyu ekranın ortasında tutar)
    manor_camera_offset_x = 0
    manor_camera_offset_y = 0
    terminal_input = ""
    terminal_status = "KOMUT BEKLENİYOR..."
    terminal_prev_state = 'MENU'  # Terminal kapanınca dönülecek state
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

    # ── Altıpatar başlangıç değerleri ─────────────────────────────────────
    player_bullets = 0    # Silahsız başla — sandıktan alınmadan ateş yok
    gun_cooldown   = 0.0
    is_reloading   = False

    # ── Silah sistemi: her zaman silahsız başla ──────────────────────────
    # Silahlar sandıktan kazanılır — kayıt/save'den yüklenmez.
    active_weapon_obj  = None
    inventory_weapons  = []
    weapon_shoot_timer = 0.0
    inventory_manager.reset()   # Singleton tamamen temizlendi
    CURRENT_THEME = THEMES[0]
    CURRENT_SHAPE = 'circle'
    score = 0.0
    high_score = 0
    camera_speed = INITIAL_CAMERA_SPEED
    player_x, player_y = 150.0, float(LOGICAL_HEIGHT - 300)
    y_velocity = 0.0
    is_jumping = is_dashing = is_slamming = False
    jumps_left = MAX_JUMPS
    dash_timer = 0
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

        # ── AİM ANGLE — her frame, event'lerden ÖNCE hesapla ──────────────
        # player_x/y bu oyunda dünya koordinatı = ekran koordinatı
        # (kamera platformları kaydırır, oyuncuyu değil)
        _aim_px = player_x + 14   # hitbox merkezi X
        _aim_py = player_y + 21   # omuz hizası Y
        _aim_dx = mouse_pos[0] - _aim_px
        _aim_dy = mouse_pos[1] - _aim_py
        aim_angle = math.atan2(_aim_dy, _aim_dx)
        # Yön: silah varken fareye bak (dash/slam sırasında değiştirme)
        if active_weapon_obj is not None and not is_dashing and not is_slamming:
            player_direction = -1 if _aim_dx < 0 else 1
        
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
                    # TERMINAL, INVENTORY, NPC_CHAT kendi ESC mantıklarını
                    # aşağıdaki spesifik handler'da yönetir — burada müdahale etme.
                    if GAME_STATE not in ('TERMINAL', 'INVENTORY', 'NPC_CHAT', 'PAUSED'):
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

            # ── F12: Debug Arena'ya Anında Geçiş (Her state'den çalışır) ───
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F12:
                current_level_idx = 999
                start_loading_sequence('PLAYING')
                print("[DEBUG] F12 → Debug Arena (ID:999) yükleniyor...")

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
                        # Direkt Vasil intro fight — cutscene yok, savaşın içinde konuşma balonları
                        init_vasil_intro_fight()
                        GAME_STATE = 'PLAYING'
                    elif 'level_select' in active_ui_elements and active_ui_elements['level_select'].collidepoint(mouse_pos):
                        GAME_STATE = 'LEVEL_SELECT'
                        level_select_page = 0
                    elif 'settings' in active_ui_elements and active_ui_elements['settings'].collidepoint(mouse_pos):
                        GAME_STATE = 'SETTINGS'
                    elif 'cheat_terminal' in active_ui_elements and active_ui_elements['cheat_terminal'].collidepoint(mouse_pos):
                        GAME_STATE = 'TERMINAL'
                        terminal_prev_state = 'MENU'
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

                elif GAME_STATE in ('PLAYING', 'ENDLESS_PLAY'):
                    # ── SOL TIK: ATEŞ ET ─────────────────────────────────────
                    _manor_click = EASY_MODE_LEVELS.get(current_level_idx, {})
                    if _manor_click.get('type') != 'manor_stealth':
                        if active_weapon_obj is not None:
                            _fire_result = active_weapon_obj.fire()
                            if _fire_result:
                                player_bullets      = active_weapon_obj.bullets
                                gun_cooldown        = active_weapon_obj.cooldown
                                is_reloading        = active_weapon_obj.is_reloading
                                weapon_shoot_timer  = active_weapon_obj._get_fire_cooldown()
                                _inv_sl = inventory_manager.slot_for(active_weapon_obj.WEAPON_TYPE)
                                if _inv_sl is not None:
                                    _inv_sl.current_mag = player_bullets
                                _spread      = getattr(active_weapon_obj, 'current_spread', 0.0)
                                _shoot_angle = aim_angle + random.uniform(-_spread, _spread)
                                _muzzle = get_weapon_muzzle_point(
                                    active_weapon_obj.WEAPON_TYPE,
                                    player_x + 15, player_y + 18,
                                    _shoot_angle, weapon_shoot_timer
                                )
                                _px_proj = _muzzle[0] if _muzzle else player_x + 15 + math.cos(aim_angle) * 14
                                _py_proj = _muzzle[1] if _muzzle else player_y + 18 + math.sin(aim_angle) * 14
                                # ── Pompalı: tek mermi yerine saçma demeti ───────────
                                if active_weapon_obj.WEAPON_TYPE == "shotgun":
                                    _pellet_n    = active_weapon_obj.PELLET_COUNT
                                    _half_spread = active_weapon_obj.SPREAD_ANGLE / 2.0
                                    for _pi in range(_pellet_n):
                                        # Saçmaları koniye eşit aralıklı dağıt
                                        _t = _pi / max(_pellet_n - 1, 1)   # 0..1
                                        _pa = (aim_angle - _half_spread) + _t * active_weapon_obj.SPREAD_ANGLE
                                        _pp = PlayerProjectile(_px_proj, _py_proj, _pa)
                                        all_player_projectiles.add(_pp)
                                    screen_shake = max(screen_shake, 6)   # Güçlü sarsma
                                else:
                                    proj = PlayerProjectile(_px_proj, _py_proj, _shoot_angle)
                                    all_player_projectiles.add(proj)
                                    screen_shake = max(screen_shake, 2)
                                if GUN_SHOT_SOUND:
                                    audio_manager.play_sfx(GUN_SHOT_SOUND)
                                all_vfx.add(ParticleExplosion(
                                    int(_px_proj), int(_py_proj), (255, 220, 80), 5
                                ))
                        elif gun_cooldown <= 0 and player_bullets > 0 and not is_reloading:
                            # Eski uyumluluk kodu — silahsız iken çalışmasın
                            # (player_bullets = REVOLVER_MAX_BULLETS init değeri bug'a yol açıyordu)
                            pass  # Silah yoksa ateş yok

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
                    if GAME_STATE == 'INVENTORY':
                        GAME_STATE = 'PLAYING'
                        audio_manager.unpause_all()
                    elif GAME_STATE == 'PLAYING':
                        GAME_STATE = 'MENU'
                        audio_manager.stop_music()
                    elif GAME_STATE == 'NPC_CHAT':
                        GAME_STATE = 'PLAYING'
                        if current_npc:
                            current_npc.end_conversation()
                            current_npc = None
                    elif GAME_STATE == 'TERMINAL':
                        GAME_STATE = terminal_prev_state  # Nereden geldiyse oraya dön
                    elif GAME_STATE in ['MENU', 'SETTINGS', 'LEVEL_SELECT', 'ENDLESS_SELECT']:
                        running = False

                if event.key == pygame.K_p:
                    if GAME_STATE == 'PLAYING':
                        GAME_STATE = 'PAUSED'
                        audio_manager.pause_all()
                    elif GAME_STATE == 'PAUSED':
                        GAME_STATE = 'PLAYING'
                        audio_manager.unpause_all()

                # ── I TUŞU: ENVANTER ─────────────────────────────────────
                if event.key == pygame.K_i:
                    if GAME_STATE == 'PLAYING':
                        GAME_STATE = 'INVENTORY'
                        audio_manager.pause_all()
                    elif GAME_STATE == 'INVENTORY':
                        GAME_STATE = 'PLAYING'
                        audio_manager.unpause_all()

                if GAME_STATE == 'GAME_OVER' and event.key == pygame.K_r:
                    # Ölmeden önceki envanter snapshot'ını kaydet (reset öncesi)
                    _death_inventory_snapshot = []
                    for _wt in inventory_manager.unlocked_weapons:
                        _wslot = inventory_manager.slot_for(_wt)
                        _wobj  = inventory_manager._weapon_objects.get(_wt)
                        if _wslot and _wobj:
                            _death_inventory_snapshot.append((
                                _wt,
                                _wobj.__class__,          # sınıf referansı
                                max(_wobj.bullets, 0),    # mevcut şarjör
                                max(_wobj.spare_mags, 0), # yedek şarjörler
                            ))
                    _death_active_type = inventory_manager.active_type

                    # Oyunu sıfırla (init_game içinde inventory_manager.reset çağrılır)
                    init_game()
                    GAME_STATE = 'PLAYING'

                    # Silahları geri yükle — sandıktan sıfırdan almak gerekmez
                    for (_wt, _wcls, _wbullets, _wspare) in _death_inventory_snapshot:
                        _restored = _wcls(spare_mags=_wspare)
                        _restored.bullets = _wbullets
                        inventory_manager.unlock(_wt, _restored)
                        if _wt not in inventory_weapons:
                            inventory_weapons.append(_wt)
                    # Önceki aktif silahı tekrar kuşan
                    if _death_active_type and _death_active_type in inventory_weapons:
                        inventory_manager.switch_to(_death_active_type)
                        active_weapon_obj = inventory_manager.active_weapon
                        if active_weapon_obj:
                            _rb, _rs = inventory_manager.ammo_state()
                            active_weapon_obj.bullets    = _rb
                            active_weapon_obj.spare_mags = _rs
                            player_bullets = _rb
                            is_reloading   = False
                            gun_cooldown   = 0.0
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
                    else:
                        # ── Silah sandığı etkileşimi ──────────────────────────────
                        for _chest in list(all_weapon_chests):
                            _cx_d = math.sqrt((player_x + 14 - _chest.rect.centerx)**2 +
                                              (player_y + 21 - _chest.rect.centery)**2)
                            if _cx_d < WeaponChest.INTERACT_RADIUS:
                                _wtype = _chest.interact()
                                if _wtype:
                                    # Yeni silah nesnesini oluştur
                                    _new_weapon = create_weapon(_wtype)
                                    if _new_weapon:
                                        _is_new = inventory_manager.unlock(_wtype, _new_weapon)
                                        if _wtype not in inventory_weapons:
                                            inventory_weapons.append(_wtype)
                                        if active_weapon_obj is None or _is_new:
                                            # Yeni silah → kuşan
                                            inventory_manager.switch_to(_wtype)
                                            active_weapon_obj = inventory_manager.active_weapon
                                            _b, _s = inventory_manager.ammo_state()
                                            if active_weapon_obj:
                                                active_weapon_obj.bullets    = _b
                                                active_weapon_obj.spare_mags = _s
                                            player_bullets  = _b
                                            is_reloading    = False
                                            gun_cooldown    = 0.0
                                            karma_notification_text  = f"{_wtype.upper()} ALINDI!"
                                        else:
                                            # Aynı silah zaten var → chest_add_ammo
                                            # Slot + weapon_obj atomik güncellenir,
                                            # mermi bitmişse otomatik doldurulur.
                                            _ammo_r = inventory_manager.chest_add_ammo(_wtype)
                                            if active_weapon_obj and active_weapon_obj.WEAPON_TYPE == _wtype:
                                                player_bullets = _ammo_r['bullets']
                                                is_reloading   = False
                                                gun_cooldown   = 0.0
                                            if _ammo_r['was_empty']:
                                                karma_notification_text = f"ŞARJÖR + MERMİ! ({_wtype.upper()})"
                                            else:
                                                karma_notification_text = f"+1 ŞARJÖR ({_wtype.upper()})"
                                        karma_notification_timer = 60
                                        save_manager.unlock_weapon(_wtype)
                                        all_vfx.add(ParticleExplosion(
                                            _chest.rect.centerx, _chest.rect.centery,
                                            (255, 215, 0), 12
                                        ))
                                break

                # --- DÖVÜŞ TUŞLARI (tüm bölümlerde aktif) ---
                if GAME_STATE == 'PLAYING':
                    px_c = int(player_x + 15)
                    py_c = int(player_y + 15)
                    if event.key == pygame.K_j:   # Hafif vuruş
                        if player_hp.consume_stamina(COST_LIGHT):
                            combo_system.input_light(player_x, player_y, player_direction)
                            all_vfx.add(ParticleExplosion(
                                px_c + player_direction * 40, py_c,
                                (255, 150, 50), 8
                            ))
                    elif event.key == pygame.K_k:  # Ağır vuruş
                        if player_hp.consume_stamina(COST_HEAVY):
                            combo_system.input_heavy(player_x, player_y, player_direction)
                            all_vfx.add(Shockwave(
                                px_c + player_direction * 50, py_c,
                                CURSED_RED, max_radius=60, speed=12
                            ))
                            screen_shake = 6

                elif GAME_STATE == 'TERMINAL':
                    if event.key == pygame.K_RETURN:
                        _cmd = terminal_input.strip().lower()
                        terminal_input = ""

                        # ── Cheat kodları (her yerden) ─────────────────────
                        if _cmd == "super_mode_on":
                            is_super_mode = not is_super_mode
                            terminal_status = "SÜPER MOD: " + ("AKTİF!" if is_super_mode else "PASİF!")

                        elif _cmd in ("god on", "god_on"):
                            is_super_mode = True
                            terminal_status = "OK — GOD MODE AKTİF"

                        elif _cmd in ("god off", "god_off"):
                            is_super_mode = False
                            terminal_status = "OK — GOD MODE PASİF"

                        elif _cmd in ("god hp on", "god_hp_on"):
                            is_god_hp = True
                            player_hp.current_hp = player_hp.max_hp
                            terminal_status = "OK — SINIRSIZ CAN AKTİF"

                        elif _cmd in ("god hp off", "god_hp_off"):
                            is_god_hp = False
                            terminal_status = "OK — SINIRSIZ CAN PASİF"

                        elif _cmd in ("god stam on", "god_stam_on"):
                            is_god_stamina = True
                            player_hp.current_stamina = float(player_hp.max_stamina)
                            terminal_status = "OK — SINIRSIZ STAMINA AKTİF"

                        elif _cmd in ("god stam off", "god_stam_off"):
                            is_god_stamina = False
                            terminal_status = "OK — SINIRSIZ STAMINA PASİF"

                        elif _cmd == "debug_arena":
                            current_level_idx = 999
                            start_loading_sequence('PLAYING')
                            terminal_status = "DEBUG ARENA YÜKLENİYOR..."

                        # ── Debug Arena spawn komutları ────────────────────
                        elif current_level_idx == 999:
                            _dbg_floor_top = LOGICAL_HEIGHT - 80
                            _sx = min(int(player_x) + 400, LOGICAL_WIDTH - 60)

                            if _cmd in ("help", "yardim"):
                                terminal_status = "KOMUTLAR: spawn cursed/tank/drone/vasil/ares/nexus/chest/ammo/health | clear enemies/all | god on/off | god hp on/off | god stam on/off"

                            elif _cmd == "spawn cursed":
                                # Gerçek zemin platformunu bul (debug arena'nın tam genişlikte zemini)
                                _floor_plat = next((p for p in all_platforms if p.rect.width > LOGICAL_WIDTH - 10), None)
                                if _floor_plat is None:
                                    _floor_plat = Platform(0, _dbg_floor_top, LOGICAL_WIDTH, 80, theme_index=0)
                                _e = CursedEnemy(_floor_plat)
                                _e.rect.midbottom = (_sx, _dbg_floor_top)
                                all_enemies.add(_e)
                                terminal_status = f"OK — CursedEnemy spawn edildi ({_sx})"

                            elif _cmd == "spawn tank":
                                _floor_plat = next((p for p in all_platforms if p.rect.width > LOGICAL_WIDTH - 10), None)
                                if _floor_plat is None:
                                    _floor_plat = Platform(0, _dbg_floor_top, LOGICAL_WIDTH, 80, theme_index=0)
                                _e = TankEnemy(_floor_plat)
                                _e.rect.midbottom = (_sx, _dbg_floor_top)
                                all_enemies.add(_e)
                                terminal_status = f"OK — TankEnemy spawn edildi ({_sx})"

                            elif _cmd == "spawn drone":
                                # DroneEnemy doğrudan x, y alır
                                _e = DroneEnemy(_sx, _dbg_floor_top - 210)
                                all_enemies.add(_e)
                                terminal_status = f"OK — DroneEnemy spawn edildi ({_sx})"

                            elif _cmd == "spawn vasil":
                                _bsx = min(int(player_x) + 350, LOGICAL_WIDTH - 80)
                                _b = VasilBoss(_bsx, _dbg_floor_top - 180)
                                all_enemies.add(_b)
                                terminal_status = f"OK — VasilBoss spawn edildi"

                            elif _cmd == "spawn ares":
                                _bsx = min(int(player_x) + 350, LOGICAL_WIDTH - 80)
                                _b = AresBoss(_bsx, _dbg_floor_top - 180)
                                all_enemies.add(_b)
                                terminal_status = f"OK — AresBoss spawn edildi"

                            elif _cmd == "spawn nexus":
                                _bsx = min(int(player_x) + 350, LOGICAL_WIDTH - 80)
                                _b = NexusBoss(_bsx, _dbg_floor_top - 300)
                                all_enemies.add(_b)
                                terminal_status = f"OK — NexusBoss spawn edildi"

                            elif _cmd == "spawn chest":
                                _cr = pygame.Rect(_sx, _dbg_floor_top - 50, 40, 40)
                                _c = WeaponChest(_cr)
                                all_weapon_chests.add(_c)
                                terminal_status = f"OK — WeaponChest spawn edildi ({_sx})"

                            elif _cmd == "spawn shotgun":
                                _sg = create_weapon("shotgun", spare_mags=9999)
                                if _sg:
                                    inventory_manager.unlock("shotgun", _sg)
                                    if "shotgun" not in inventory_weapons:
                                        inventory_weapons.append("shotgun")
                                    terminal_status = "OK — Shotgun envanterine eklendi (3 ile kuşan)"

                            elif _cmd == "spawn ammo":
                                _ap = AmmoPickup(_sx, _dbg_floor_top - 30)
                                all_ammo_pickups.add(_ap)
                                terminal_status = f"OK — AmmoPickup spawn edildi ({_sx})"

                            elif _cmd == "spawn health":
                                _ho = HealthOrb(_sx, _dbg_floor_top - 30)
                                all_health_orbs.add(_ho)
                                terminal_status = f"OK — HealthOrb spawn edildi ({_sx})"

                            elif _cmd == "clear enemies":
                                _count = len(all_enemies)
                                all_enemies.empty()
                                terminal_status = f"TEMİZLENDİ — {_count} düşman silindi"

                            elif _cmd == "clear all":
                                _ec = len(all_enemies)
                                all_enemies.empty()
                                all_weapon_chests.empty()
                                all_ammo_pickups.empty()
                                all_health_orbs.empty()
                                terminal_status = f"TEMİZLENDİ — {_ec} düşman + tüm objeler silindi"

                            else:
                                terminal_status = f"HATA: '{_cmd}' tanımlı değil. 'help' yaz."

                        else:
                            terminal_status = f"HATA: GEÇERSİZ KOD"

                    elif event.key == pygame.K_BACKSPACE:
                        terminal_input = terminal_input[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        GAME_STATE = 'PLAYING'
                    else:
                        if len(terminal_input) < 30:
                            terminal_input += event.unicode

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
                    if current_level_idx == 999:
                        # Debug Arena: T → Terminal aç
                        GAME_STATE = 'TERMINAL'
                        terminal_prev_state = 'PLAYING'
                        terminal_input  = ""
                        terminal_status = "KOMUT BEKLENİYOR... (help yaz)"
                    elif lvl_config.get('type') == 'rest_area':
                        # Dinlenme alanından ayrılırken canı tam doldur (Bonfire)
                        player_hp.heal(player_hp.max_hp)
                        karma_notification_text  = "DİNLENDİN! CAN DOLDU"
                        karma_notification_timer = 60
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

                    if event.key == pygame.K_s and is_jumping and not is_dashing and not is_slamming and player_hp.consume_stamina(COST_SLAM):
                        is_slamming = True
                        slam_stall_timer = 15
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

                    # ── F TUŞU: SADECE SESSİZ SUİKAST (manor_stealth) ───────────
                    # Ateş etmek → Sol Tık (MOUSEBUTTONDOWN aşağıda)
                    if event.key == pygame.K_f:
                        _manor_lvl = EASY_MODE_LEVELS.get(current_level_idx, {})
                        if _manor_lvl.get('type') == 'manor_stealth':
                            _sk_result = stealth_system.try_stealth_kill(
                                player_x + 15, player_y + 15,
                                reach=STEALTH_KILL_REACH_PX
                            )
                            if _sk_result["success"]:
                                _gx = int(_sk_result["x"])
                                _gy = int(_sk_result["y"])
                                score += 3000
                                save_manager.update_karma(STEALTH_KILL_KARMA)
                                player_karma = save_manager.get_karma()
                                enemies_killed_current_level += 1
                                karma_notification_text  = f"SESSİZ SUİKAST! KARMA +{STEALTH_KILL_KARMA}"
                                karma_notification_timer = 80
                                all_vfx.add(ParticleExplosion(_gx, _gy, (0, 200, 100), 14))
                                all_vfx.add(Shockwave(_gx, _gy, (0, 180, 80),
                                                      max_radius=60, rings=1, speed=10))
                                screen_shake = max(screen_shake, 3)
                                if stealth_system.active_guard_count() == 0:
                                    from mission_system import mission_manager
                                    mission_manager.complete_objective("eliminate_guards")
                            else:
                                _reason = _sk_result.get("reason", "BAŞARISIZ")
                                karma_notification_text  = f"SUİKAST BAŞARISIZ: {_reason}"
                                karma_notification_timer = 60

                    # ── R TUŞU: ŞARJÖR DOLDUR ─────────────────────────────────────
                    if event.key == pygame.K_r and GAME_STATE == 'PLAYING':
                        _manor_r = EASY_MODE_LEVELS.get(current_level_idx, {})
                        if _manor_r.get('type') != 'manor_stealth':
                            if active_weapon_obj is not None:
                                # inventory_manager slot'undan reload kontrolü
                                _inv_slot = inventory_manager.slot_for(active_weapon_obj.WEAPON_TYPE)
                                _can_reload = (_inv_slot is not None and _inv_slot.can_reload)
                                if _can_reload and active_weapon_obj.start_reload():
                                    # inventory slot'unu da güncelle
                                    if _inv_slot:
                                        _inv_slot.spare_mags  -= 0  # weapon_system.update() düşürecek
                                    gun_cooldown = active_weapon_obj.cooldown
                                    is_reloading = True
                                    player_bullets = active_weapon_obj.bullets
                                    if RELOAD_SOUND:
                                        audio_manager.play_sfx(RELOAD_SOUND)
                                    karma_notification_text  = "ŞARJÖR DOLUYOR..."
                                    karma_notification_timer = 40
                            elif not is_reloading and player_bullets < REVOLVER_MAX_BULLETS:
                                # Eski uyumluluk — sadece gerçekten silahsız legacy mod için
                                # active_weapon_obj varsa buraya düşmemeli (yukarıda yakalanır)
                                # Silahsız iken R'ya basılırsa hiçbir şey yapma
                                pass

                    # ── 1/2 TUŞLARI: SİLAH DEĞİŞTİR ─────────────────────────────
                    if event.key in (pygame.K_1, pygame.K_2, pygame.K_3) and GAME_STATE == 'PLAYING':
                        _slot = 0 if event.key == pygame.K_1 else (1 if event.key == pygame.K_2 else 2)
                        if _slot < len(inventory_weapons):
                            _switch_type = inventory_weapons[_slot]
                            # Zaten aktif silahsa değiştirme
                            if active_weapon_obj is None or active_weapon_obj.WEAPON_TYPE != _switch_type:
                                # switch_by_slot_index: per-type dict'ten doğru nesneyi alır
                                _switched = inventory_manager.switch_by_slot_index(_slot)
                                if _switched:
                                    # Tipe özel nesne yoksa yeni oluştur ve kaydet
                                    if inventory_manager.active_weapon is None:
                                        _new_wobj = create_weapon(_switch_type)
                                        if _new_wobj:
                                            inventory_manager.active_weapon = _new_wobj
                                    # active_weapon artık doğru tipe ait nesneyi döner
                                    active_weapon_obj = inventory_manager.active_weapon
                                    _b, _s = inventory_manager.ammo_state()
                                    if active_weapon_obj:
                                        active_weapon_obj.bullets    = _b
                                        active_weapon_obj.spare_mags = _s
                                    player_bullets     = _b
                                    is_reloading       = False
                                    gun_cooldown       = 0.0
                                    weapon_shoot_timer = 0.0
                                    karma_notification_text  = f"SİLAH: {_switch_type.upper()}"
                                    karma_notification_timer = 40

                    if event.key == pygame.K_SPACE and player_hp.consume_stamina(COST_DASH) and not is_dashing:
                        is_dashing = True
                        # Malikane bölümünde dash mesafesi kısaltılır (kaçış adımı)
                        _manor_dash_cfg = EASY_MODE_LEVELS.get(current_level_idx, {})
                        dash_timer = (DASH_DURATION // 3) if _manor_dash_cfg.get('type') == 'manor_stealth' else DASH_DURATION
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

                    # ── DEBUG ARENA: Manuel Düşman Spawner (Numpad 1 / 2 / 3) ─
                    # Güvenlik kapısı: Sadece PLAYING state + Debug Arena (ID:999)
                    if GAME_STATE == 'PLAYING' and current_level_idx == 999:
                        # Zemin platformunun üst kenarı (debug_arena: LOGICAL_HEIGHT - 80)
                        _dbg_floor_top = LOGICAL_HEIGHT - 80
                        # Oyuncunun sağına +400 px ofset, ekran dışına çıkmasın
                        _dbg_spawn_x = min(int(player_x) + 400, LOGICAL_WIDTH - 50)

                        if event.key == pygame.K_KP1:
                            # CursedEnemy — standart yakın dövüş düşmanı (boy ~60px)
                            _dbg_y = _dbg_floor_top - 60
                            _dbg_enemy = CursedEnemy(_dbg_spawn_x, _dbg_y)
                            all_enemies.add(_dbg_enemy)
                            print(f"[DBG SPAWN] CursedEnemy → ({_dbg_spawn_x}, {_dbg_y})")

                        elif event.key == pygame.K_KP2:
                            # TankEnemy — ağır düşman (boy ~70px)
                            _dbg_y = _dbg_floor_top - 70
                            _dbg_enemy = TankEnemy(_dbg_spawn_x, _dbg_y)
                            all_enemies.add(_dbg_enemy)
                            print(f"[DBG SPAWN] TankEnemy  → ({_dbg_spawn_x}, {_dbg_y})")

                        elif event.key == pygame.K_KP3:
                            # DroneEnemy — uçan düşman, zeminden 150px yukarıda
                            _dbg_y = _dbg_floor_top - 60 - 150
                            _dbg_enemy = DroneEnemy(_dbg_spawn_x, _dbg_y)
                            all_enemies.add(_dbg_enemy)
                            print(f"[DBG SPAWN] DroneEnemy → ({_dbg_spawn_x}, {_dbg_y})")

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
            buff_stacks = max(0, (current_level_idx - 1) // 3)
            if buff_stacks > 2:
                buff_stacks = 2
            base_speed_mult = 1.0 + (0.25 * buff_stacks)
            active_player_speed = PLAYER_SPEED * base_speed_mult

            # ── Karma Stamina Buff'ı ──────────────────────────────────────
            # Karma ±100'ü geçince stamina dolum hızı ve maksimum stamina artar.
            # Böylece iyi/kötü yolda kararlı oyuncular daha seri kombolar yapar.
            _karma_abs = abs(current_karma)
            if _karma_abs >= 100:
                player_hp.stamina_regen = STAMINA_REGEN_RATE * 1.5   # %50 daha hızlı regen
                player_hp.max_stamina   = int(PLAYER_MAX_STAMINA * 1.25)  # %25 daha fazla stamina
            elif _karma_abs >= 50:
                player_hp.stamina_regen = STAMINA_REGEN_RATE * 1.25
                player_hp.max_stamina   = PLAYER_MAX_STAMINA
            else:
                player_hp.stamina_regen = STAMINA_REGEN_RATE
                player_hp.max_stamina   = PLAYER_MAX_STAMINA
            # Mevcut stamina'yı yeni maksimumla sınırla
            player_hp.current_stamina = min(player_hp.current_stamina, float(player_hp.max_stamina))

            if vasil_companion:
                active_player_speed = PLAYER_SPEED * 1.5
                # Vasi varken stamina anında dolar (tam güç)
                player_hp.stamina_regen = STAMINA_REGEN_RATE * 4.0

            # ── MALİKANE STEALTHFİZİĞİ OVERRİDE ────────────────────────────
            # Normal bölüm hız hesaplamaları stealth için çok hızlı.
            # manor_stealth bölümünde tüm karma/level buff'ları bastırılır.
            _lvl_cfg_physics = EASY_MODE_LEVELS.get(current_level_idx, {})
            if _lvl_cfg_physics.get('type') == 'manor_stealth':
                active_player_speed   = PLAYER_SPEED * 0.80   # Normal'in %80'i

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

            # ── Hile flagları: sınırsız can / stamina ────────────────────
            if is_god_hp:
                player_hp.current_hp = player_hp.max_hp
            if is_god_stamina:
                player_hp.current_stamina = float(player_hp.max_stamina)

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
                    if _killed and not hasattr(_enemy, 'arena_id'):
                        # Normal düşman (CursedEnemy / DroneEnemy / TankEnemy) öldü → sprite sil
                        _enemy.kill()
                        # %18 ihtimalle can küresi düşür
                        if random.random() < 0.18:
                            _orb = HealthOrb(_enemy.rect.centerx, _enemy.rect.top)
                            all_health_orbs.add(_orb)
                        # Cephane düşürme (aktif silah varsa)
                        if active_weapon_obj is not None and random.random() < AMMO_DROP_CHANCE:
                            _ammo_drop = AmmoPickup(
                                _enemy.rect.centerx,
                                _enemy.rect.top,
                                active_weapon_obj.WEAPON_TYPE
                            )
                            all_ammo_pickups.add(_ammo_drop)
                else:
                    # Fallback — take_damage metodu yoksa anında öldür
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
                        _slam_killed = False
                        if hasattr(_ne, 'take_damage'):
                            _slam_killed = _ne.take_damage(_SLAM_DMG)
                        else:
                            _slam_killed = True
                        if _slam_killed:
                            _ne.kill()
                            if random.random() < 0.18:
                                all_health_orbs.add(HealthOrb(_ne.rect.centerx, _ne.rect.top))
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
                            if current_level_idx == 0:
                                all_enemies.empty()
                                all_vfx.empty()
                                VasilDefeatScene(screen, clock).run()
                                init_limbo()
                                GAME_STATE = 'PLAYING'
                                if npcs:
                                    start_npc_conversation(npcs[0])
                            else:
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
                if current_level_idx != 99 and current_level_idx != 0:
                    if lvl_config.get('type') not in ('beat_arena', 'debug_arena'):
                        camera_speed = min(MAX_CAMERA_SPEED, camera_speed + SPEED_INCREMENT_RATE * frame_mul)
                    score_gain = 0.1 * max(camera_speed, 1.0) * frame_mul
                    if is_super_mode:
                        score_gain *= 40
                    score += score_gain

            # ═════════════════════════════════════════════════════════════
            # MALİKANE KAMERA TAKİBİ — aşağıda platform collision sonrasına taşındı
            # ═════════════════════════════════════════════════════════════
            if lvl_config.get('type') != 'manor_stealth':
                manor_camera_offset_x = 0
                manor_camera_offset_y = 0

            # Silah yoksa klavye yönü geçerlidir

            old_x, old_y = player_x, player_y
            keys = pygame.key.get_pressed()
            horizontal_move = keys[pygame.K_d] - keys[pygame.K_a]
            if horizontal_move != 0 and not is_dashing and not is_slamming:
                character_state = 'running'
                player_direction = 1 if horizontal_move > 0 else -1  # Yön güncelle
            elif not is_jumping and not is_dashing and not is_slamming:
                character_state = 'idle'
                # player_direction değişmez → durduğunda son yönü korur

            # Silah yoksa klavye yönü geçerlidir
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
                for enemy in list(all_enemies):
                    dist = math.sqrt((enemy.rect.centerx - wave['x'])**2 + (enemy.rect.centery - wave['y'])**2)
                    if dist < wave['r'] + 20 and dist > wave['r'] - 40:
                        _wave_killed = False
                        if hasattr(enemy, 'take_damage'):
                            _wave_killed = enemy.take_damage(80)
                        else:
                            _wave_killed = True
                        if _wave_killed:
                            enemy.kill()
                            if random.random() < 0.18:
                                all_health_orbs.add(HealthOrb(enemy.rect.centerx, enemy.rect.top))
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
                    if isinstance(enemy, EnemyBullet):
                        continue
                    _dash_killed = False
                    if hasattr(enemy, 'take_damage'):
                        _dash_killed = enemy.take_damage(_DASH_DMG)
                    else:
                        _dash_killed = True
                    if _dash_killed:
                        enemy.kill()
                        # %18 ihtimalle can küresi düşür
                        if random.random() < 0.18:
                            all_health_orbs.add(HealthOrb(enemy.rect.centerx, enemy.rect.top))
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
                if lvl_config.get('type') not in ('rest_area', 'manor_stealth', 'debug_arena'):
                    player_x -= camera_speed * frame_mul
                if keys[pygame.K_a]:
                    player_x -= active_player_speed * frame_mul
                if keys[pygame.K_d]:
                    player_x += active_player_speed * frame_mul
                # Debug Arena: oyuncu ekran dışına çıkmasın
                if lvl_config.get('type') == 'debug_arena':
                    player_x = max(0.0, min(player_x, float(LOGICAL_WIDTH - 28)))

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

            if screen_shake > 0:
                screen_shake -= 1
            if karma_notification_timer > 0:
                karma_notification_timer -= 1

            # ── Silah nesnesi güncelle (cooldown, reload, SMG sekme) ───────────
            if active_weapon_obj is not None:
                active_weapon_obj.update(dt)
                gun_cooldown   = active_weapon_obj.cooldown
                is_reloading   = active_weapon_obj.is_reloading
                player_bullets = active_weapon_obj.bullets

                # ── DEBUG ARENA: Sınırsız cephane — şarjör bitince anında doldur
                if lvl_config.get('type') == 'debug_arena':
                    if active_weapon_obj.bullets <= 0 and not active_weapon_obj.is_reloading:
                        active_weapon_obj.bullets    = active_weapon_obj.mag_size
                        active_weapon_obj.spare_mags = 9999
                        player_bullets = active_weapon_obj.bullets
                        active_weapon_obj.cooldown = 0.0

                # Dolum tamamlandıysa bildirim
                if is_reloading and active_weapon_obj.cooldown <= 0:
                    karma_notification_text  = "ŞARJÖR TAMAM!"
                    karma_notification_timer = 30

                # ── SMG OTOMATİK ATEŞ — sol tıka basılı tutunca sürekli ateş ──
                # get_pressed() değil mouse.get_pressed() kullanılır
                if active_weapon_obj.is_automatic and GAME_STATE == 'PLAYING':
                    _manor_smg = EASY_MODE_LEVELS.get(current_level_idx, {})
                    if _manor_smg.get('type') != 'manor_stealth':
                        _mouse_held = pygame.mouse.get_pressed()
                        if _mouse_held[0]:   # Sol tık basılı mı?
                            if active_weapon_obj.can_auto_fire(dt):
                                _fire_res = active_weapon_obj.fire()
                                if _fire_res:
                                    player_bullets     = active_weapon_obj.bullets
                                    gun_cooldown       = active_weapon_obj.cooldown
                                    weapon_shoot_timer = active_weapon_obj.fire_interval
                                    _smg_spread = getattr(active_weapon_obj, 'current_spread', 0.0)
                                    _smg_angle  = aim_angle + random.uniform(-_smg_spread, _smg_spread)
                                    _smg_muzzle = active_weapon_obj.get_muzzle_point(
                                        player_x + 15, player_y + 18, _smg_angle, active_weapon_obj.fire_interval
                                    )
                                    _px_proj = _smg_muzzle[0] if _smg_muzzle else player_x + 15 + math.cos(_smg_angle) * 14
                                    _py_proj = _smg_muzzle[1] if _smg_muzzle else player_y + 18 + math.sin(_smg_angle) * 14
                                    proj = PlayerProjectile(_px_proj, _py_proj, _smg_angle)
                                    all_player_projectiles.add(proj)
                                    if GUN_SHOT_SOUND:
                                        audio_manager.play_sfx(GUN_SHOT_SOUND)
                                    all_vfx.add(ParticleExplosion(
                                        int(_px_proj + player_direction * 10), int(_py_proj),
                                        (0, 220, 255), 4
                                    ))
                                    screen_shake = max(screen_shake, 1)
            else:
                # Silah yok — eski altıpatar sayaç sistemi
                if gun_cooldown > 0:
                    gun_cooldown = max(0.0, gun_cooldown - dt)
                    if is_reloading and gun_cooldown <= 0:
                        is_reloading   = False
                        player_bullets = REVOLVER_MAX_BULLETS
                        karma_notification_text  = "ŞARJÖR TAMAM!"
                        karma_notification_timer = 30

            # Atış görsel sayacı azalt
            if weapon_shoot_timer > 0:
                weapon_shoot_timer = max(0.0, weapon_shoot_timer - dt)

            # ── Altıpatar sayaçları güncelle (eski uyumluluk — silah yoksa) ───
            if gun_cooldown > 0:
                gun_cooldown = max(0.0, gun_cooldown - dt)
                # Dolum tamamlandıysa şarjörü doldur
                if is_reloading and gun_cooldown <= 0:
                    is_reloading   = False
                    player_bullets = REVOLVER_MAX_BULLETS
                    karma_notification_text  = "ŞARJÖR TAMAM!"
                    karma_notification_timer = 30

            # ── Oyuncu mermilerini güncelle (CCD: eski pos kaydet) ───────────
            for _proj in list(all_player_projectiles):
                _proj._ccd_ox = _proj.rect.centerx
                _proj._ccd_oy = _proj.rect.centery
                _proj.update(camera_speed, dt)

            # ── Mermi → düşman çarpışması (CCD + Fat Hitbox) ─────────────────
            # groupcollide() sadece final rect'i test eder.
            # Yüksek hızlı / yakın mesafe mermileri düşmandan atlayabilir.
            # CCD: eski→yeni konum arası 4px adımlarla taranır.
            # Fat hitbox: BULLET_RADIUS kadar genişletilir.
            # Shotgun yakın mesafe: ilk frame'de zaten hedef içinde olabilir,
            # bu yüzden substep 0'dan başlatılır (muzzle noktası da test edilir).
            _lvl_cfg_revolver = EASY_MODE_LEVELS.get(current_level_idx, {})
            if _lvl_cfg_revolver.get('type') != 'manor_stealth':

                _wpn_dmg  = active_weapon_obj.damage if active_weapon_obj else REVOLVER_DAMAGE
                _bullet_r = getattr(active_weapon_obj, 'BULLET_RADIUS', 6) if active_weapon_obj else 6

                for _proj in list(all_player_projectiles):
                    if not _proj.alive():
                        continue
                    _ox       = getattr(_proj, '_ccd_ox', _proj.rect.centerx)
                    _oy       = getattr(_proj, '_ccd_oy', _proj.rect.centery)
                    _nx       = _proj.rect.centerx
                    _ny       = _proj.rect.centery
                    _substeps = min(8, max(1, int(math.hypot(_nx-_ox, _ny-_oy) / 4)))
                    _hit_enemy = None
                    _hit_cx, _hit_cy = _nx, _ny

                    # range(0, ...) — substep 0 = muzzle noktası da test edilir
                    # shotgun yakın mesafe için kritik
                    for _si in range(0, _substeps + 1):
                        _t  = _si / max(_substeps, 1)
                        _ix = int(_ox + (_nx - _ox) * _t)
                        _iy = int(_oy + (_ny - _oy) * _t)
                        _tr = pygame.Rect(
                            _ix - _bullet_r, _iy - _bullet_r,
                            _bullet_r * 2,   _bullet_r * 2
                        )
                        for _en in all_enemies:
                            if isinstance(_en, EnemyBullet):
                                continue
                            if _tr.colliderect(_en.rect):
                                _hit_enemy = _en
                                _hit_cx, _hit_cy = _ix, _iy
                                break
                        if _hit_enemy:
                            break

                    if _hit_enemy:
                        if hasattr(_hit_enemy, 'take_damage'):
                            _hit_enemy.take_damage(_wpn_dmg)
                        score += 300
                        enemies_killed_current_level += 1
                        save_manager.update_karma(-5)
                        player_karma = save_manager.get_karma()
                        karma_notification_text  = f"İSABET! -{_wpn_dmg} HP"
                        karma_notification_timer = 30
                        all_vfx.add(ParticleExplosion(_hit_cx, _hit_cy, (255, 100, 30), 10))
                        all_vfx.add(Shockwave(
                            _hit_cx, _hit_cy, (255, 150, 50), max_radius=50, rings=1, speed=10
                        ))
                        screen_shake = max(screen_shake, 3)
                        if hasattr(_hit_enemy, 'is_active') and not _hit_enemy.is_active:
                            _hit_enemy.kill()
                            all_vfx.add(ParticleExplosion(_hit_cx, _hit_cy, CURSED_PURPLE, 20))
                        _proj.kill()

                # Arena düşmanlarına da mermi isabet (CCD)
                if lvl_config.get('type') == 'beat_arena':
                    for _ap in list(all_player_projectiles):
                        if not _ap.alive():
                            continue
                        _ox2 = getattr(_ap, '_ccd_ox', _ap.rect.centerx)
                        _oy2 = getattr(_ap, '_ccd_oy', _ap.rect.centery)
                        _nx2 = _ap.rect.centerx
                        _ny2 = _ap.rect.centery
                        _ss2 = min(8, max(1, int(math.hypot(_nx2-_ox2, _ny2-_oy2) / 4)))
                        _ae_hit = None
                        _ae_cx, _ae_cy = _nx2, _ny2

                        for _si2 in range(0, _ss2 + 1):
                            _t2  = _si2 / max(_ss2, 1)
                            _ix2 = int(_ox2 + (_nx2-_ox2) * _t2)
                            _iy2 = int(_oy2 + (_ny2-_oy2) * _t2)
                            _r2  = pygame.Rect(
                                _ix2-_bullet_r, _iy2-_bullet_r,
                                _bullet_r*2,    _bullet_r*2
                            )
                            for _ae in beat_arena.arena_enemies:
                                if _r2.colliderect(_ae.rect):
                                    _ae_hit = _ae
                                    _ae_cx, _ae_cy = _ix2, _iy2
                                    break
                            if _ae_hit:
                                break

                        if _ae_hit:
                            if hasattr(_ae_hit, 'take_damage'):
                                _ae_hit.take_damage(_wpn_dmg)
                            score += 300
                            all_vfx.add(ParticleExplosion(_ae_cx, _ae_cy, (255, 100, 30), 10))
                            _ap.kill()

            PLAYER_W, PLAYER_H = 28, 42   # sprite boyutuyla eşleşir
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
                    _bullet_died = player_hp.take_damage(30)
                    screen_shake = max(screen_shake, 10)
                    all_vfx.add(ScreenFlash((255, 0, 0), 80, 5))
                    enemy.kill()
                    if _bullet_died:
                        GAME_STATE = 'GAME_OVER'
                        high_score = max(high_score, int(score))
                        save_manager.update_high_score('easy_mode', current_level_idx, score)
                        audio_manager.stop_music()
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
                        # --- CAN SİSTEMİ: Anlık ölüm yok, hasar al ---
                        _touch_died = player_hp.take_damage(20)
                        screen_shake = max(screen_shake, 12)
                        all_vfx.add(ScreenFlash((255, 0, 0), 80, 5))
                        all_vfx.add(ParticleExplosion(int(player_x + 15), int(player_y + 15), CURSED_RED, 10))
                        if _touch_died:
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

            # ── MALİKANE: Yatay duvar + kapı çarpışması ──────────────────────
            if lvl_config.get('type') == 'manor_stealth':
                # Dikey platform (duvar) çarpışması
                _wall_rect = pygame.Rect(int(player_x), int(player_y) + 4, PLAYER_W, PLAYER_H - 8)
                for _wp in all_platforms:
                    if _wp.rect.height > _wp.rect.width:   # Dikey (duvar) platform
                        if _wall_rect.colliderect(_wp.rect):
                            if old_x + PLAYER_W <= _wp.rect.left + 6:
                                player_x = float(_wp.rect.left - PLAYER_W)
                            elif old_x >= _wp.rect.right - 6:
                                player_x = float(_wp.rect.right)

                # Kilitli kapı çarpışması — "CART CURT" sesi + geri it
                try:
                    _door_rect_p = pygame.Rect(int(player_x) + 3, int(player_y) + 2,
                                               PLAYER_W - 6, PLAYER_H - 4)
                    for _door in manor_doors:
                        if not _door.active:
                            continue
                        if _door_rect_p.colliderect(_door.rect):
                            # Sese bas (sadece ilk çarpışmada, spam olmasın)
                            if not getattr(_door, '_bump_cooldown', 0):
                                try:
                                    import pygame as _pg
                                    # Kısa metalik tıkırtı sesi — basit beep ile simüle
                                    _bump_snd = _pg.sndarray.make_sound(
                                        __import__('numpy').array(
                                            [int(3000 * __import__('math').sin(
                                                i * 0.8 + __import__('math').sin(i * 0.3) * 2
                                            )) for i in range(4000)],
                                            dtype=__import__('numpy').int16
                                        ).reshape(-1, 1).repeat(2, axis=1)
                                    )
                                    _bump_snd.set_volume(0.4)
                                    _bump_snd.play()
                                except Exception:
                                    pass   # numpy yoksa sessiz geç
                                _door._bump_cooldown = 20   # 20 kare bekleme
                            else:
                                _door._bump_cooldown -= 1

                            # Kapıdan geri it
                            if old_x + PLAYER_W <= _door.rect.left + 10:
                                player_x = float(_door.rect.left - PLAYER_W - 1)
                            elif old_x >= _door.rect.right - 10:
                                player_x = float(_door.rect.right + 1)
                            else:
                                player_x = old_x
                            break
                        elif getattr(_door, '_bump_cooldown', 0):
                            _door._bump_cooldown = max(0, _door._bump_cooldown - 1)
                except NameError:
                    pass   # manor_doors henüz tanımlanmamışsa sessizce geç

                # ── KAMERA TAKİBİ — tüm fizik & çarpışma sonrası ─────────────
                # Burada hesaplama yapılır ki kamera oyuncunun SON konumunu görsün.
                MANOR_MAP_WIDTH  = lvl_config.get('map_width',  3300)
                MANOR_MAP_HEIGHT = lvl_config.get('map_height', LOGICAL_HEIGHT)

                # Oyuncu merkezini hesapla
                _pcx = player_x + PLAYER_W / 2
                _pcy = player_y + PLAYER_H / 2

                # Kamera hedefi: oyuncu tam ortada olsun
                _target_cam_x = _pcx - LOGICAL_WIDTH  / 2
                _target_cam_y = _pcy - LOGICAL_HEIGHT / 2

                # Harita sınırları
                _cam_max_x = max(0, MANOR_MAP_WIDTH  - LOGICAL_WIDTH)
                _cam_max_y = max(0, MANOR_MAP_HEIGHT - LOGICAL_HEIGHT)
                _target_cam_x = max(0.0, min(float(_target_cam_x), float(_cam_max_x)))
                _target_cam_y = max(0.0, min(float(_target_cam_y), float(_cam_max_y)))

                # Hafif lerp (0.18) — kayışlı ama gecikmesiz hissini verir
                # Tam anlık istersen 1.0 yap
                _CAM_LERP = 0.22
                manor_camera_offset_x += (_target_cam_x - manor_camera_offset_x) * _CAM_LERP
                manor_camera_offset_y += (_target_cam_y - manor_camera_offset_y) * _CAM_LERP

                # ── Kasa alanı kontrolü ───────────────────────────────────────
                _safe_x = lvl_config.get("secret_safe_x", 2910)
                _safe_y = lvl_config.get("secret_safe_y", 230)
                _safe_r = lvl_config.get("secret_safe_radius", 100)
                _dx_safe = player_x - _safe_x
                _dy_safe = player_y - _safe_y
                if math.sqrt(_dx_safe * _dx_safe + _dy_safe * _dy_safe) < _safe_r:
                    from mission_system import mission_manager
                    mission_manager.set_flag("area_secret_safe", True)
                    mission_manager.complete_objective("find_secret_safe")
                    if stealth_system.active_guard_count() == 0:
                        mission_manager.complete_objective("eliminate_guards")
                    if stealth_system.global_alert == 0:
                        mission_manager.complete_objective("stealth_optional_no_alert")
                        save_manager.update_karma(15)
                        player_karma = save_manager.get_karma()
                        karma_notification_text  = "MÜKEMMEL GİZLİLİK! KARMA +15"
                        karma_notification_timer = 120
                    score += 20000
                    GAME_STATE = 'LEVEL_COMPLETE'
                    save_manager.unlock_next_level('easy_mode', current_level_idx)
                    save_manager.update_high_score('easy_mode', current_level_idx, score)

            # ── Can Küreleri (HealthOrb) güncelle + topla ─────────────────
            _player_rect_orb = pygame.Rect(int(player_x), int(player_y), PLAYER_W, PLAYER_H)
            for _orb in list(all_health_orbs):
                _orb.update(camera_speed, dt)
                if _player_rect_orb.colliderect(_orb.rect):
                    player_hp.heal(HealthOrb.HEAL_AMOUNT)
                    _orb.kill()
                    karma_notification_text  = f"CAN +{HealthOrb.HEAL_AMOUNT}"
                    karma_notification_timer = 45
                    all_vfx.add(EnergyOrb(int(player_x + 15), int(player_y - 20), (0, 255, 80), 8, 20))

            # ── Silah Sandıkları güncelle ─────────────────────────────────
            for _wc in list(all_weapon_chests):
                _wc.update(camera_speed, dt)
                if _wc.rect.right < -50:   # Ekran dışı → sil
                    _wc.kill()

            # ── Cephane Pickup'ları güncelle + topla ─────────────────────
            for _ap in list(all_ammo_pickups):
                _ap.update(camera_speed, dt)
                if _player_rect_orb.colliderect(_ap.rect):
                    _added = 0
                    if active_weapon_obj is not None and _ap.weapon_type == active_weapon_obj.WEAPON_TYPE:
                        # inventory_manager slot'unu güncelle
                        _added = inventory_manager.pickup_spare_mag(_ap.weapon_type, 1)
                        if _added == 0:
                            # Inventory slot yoksa doğrudan weapon_obj'ye ekle
                            active_weapon_obj.add_spare_mag(1)
                        else:
                            # weapon_obj'yi inventory slot ile senkronize et
                            _b, _s = inventory_manager.ammo_state()
                            active_weapon_obj.spare_mags = _s
                        player_bullets = active_weapon_obj.bullets
                    _ap.kill()
                    karma_notification_text  = "CEPHANELENDİN! +1 ŞARJÖR"
                    karma_notification_timer = 40
                    all_vfx.add(EnergyOrb(int(player_x + 15), int(player_y - 25),
                                          (255, 165, 0), 6, 15))

            for npc in npcs:
                npc.update(player_x, player_y, dt)
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

            if current_level_idx in [0, 10, 30]:
                _bm_idx = current_level_idx if current_level_idx != 0 else 10  # Level 0 → level 10 saldırı seti
                boss_manager_system.update_logic(_bm_idx, all_platforms, player_x, player_karma, camera_speed, frame_mul, is_weakened=False)

                # ── LEVEL 0 / INTRO: Boss player'ı smooth lerp ile takip eder ──
                if current_level_idx == 0:
                    _intro_boss = next((e for e in all_enemies if isinstance(e, VasilBoss)), None)
                    if _intro_boss:
                        _ib_target_x = player_x + 380
                        _ib_speed    = 3.0 * frame_mul
                        if _intro_boss.x < _ib_target_x:
                            _intro_boss.x = min(_intro_boss.x + _ib_speed, _ib_target_x)
                        elif _intro_boss.x > _ib_target_x:
                            _intro_boss.x = max(_intro_boss.x - _ib_speed, _ib_target_x)
                        _intro_boss.rect.x = int(_intro_boss.x)
                player_hitbox = pygame.Rect(player_x + 5, player_y + 5, 20, 20)
                player_obj_data = {'x': player_x, 'y': player_y}
                is_hit = boss_manager_system.check_collisions(player_hitbox, player_obj_data, all_vfx, save_manager)
                if is_hit:
                    screen_shake = 20
                    all_vfx.add(ScreenFlash((255, 0, 0), 150, 5))
                    all_vfx.add(ParticleExplosion(player_x + 15, player_y + 15, (200, 0, 0), 25))
                    player_x -= 40
                    y_velocity = -10

                    if current_level_idx == 0:
                        # ── Level 0: Hasar doğrudan cana gider ──────────
                        _died = player_hp.take_damage(35)
                        karma_notification_text  = f"HASAR ALDIN! ({player_hp.current_hp}/{player_hp.max_hp})"
                        karma_notification_timer = 40
                        if _died:
                            # Vasil yenilemez → ölünce defeat sahnesine geç
                            all_enemies.empty()
                            all_vfx.empty()
                            VasilDefeatScene(screen, clock).run()
                            init_limbo()
                            GAME_STATE = 'PLAYING'
                            if npcs:
                                start_npc_conversation(npcs[0])
                    else:
                        # ── Level 10/30: Eski karma hasar sistemi ───────
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
                            karma_notification_text  = "İRADE HASAR ALDI!"
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

            if GAME_STATE == 'PLAYING' and lvl_config.get('type') not in ('rest_area', 'beat_arena', 'manor_stealth', 'debug_arena'):
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

            # ── INTRO BOSS (Level 0) — Vasil yenilemez, kill_player sinyalini yakala ─
            if current_level_idx == 0:
                for _ib_e in list(all_enemies):
                    if isinstance(_ib_e, VasilBoss) and getattr(_ib_e, 'kill_player', False):
                        vasil_intro_kill_pending = True
                        break
                if vasil_intro_kill_pending:
                    vasil_intro_kill_pending = False
                    all_enemies.empty()
                    all_vfx.empty()
                    VasilDefeatScene(screen, clock).run()
                    init_limbo()
                    GAME_STATE = 'PLAYING'
                    if npcs:
                        start_npc_conversation(npcs[0])

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

            if lvl_config.get('type') not in ('rest_area', 'beat_arena', 'debug_arena') and current_level_idx not in (0, 99):
                if current_level_idx <= 30:
                    if len(all_platforms) > 0 and max(p.rect.right for p in all_platforms) < LOGICAL_WIDTH + 100:
                        add_new_platform()

            if player_y > LOGICAL_HEIGHT + 100:
                if current_level_idx == 0:
                    all_enemies.empty()
                    all_vfx.empty()
                    VasilDefeatScene(screen, clock).run()
                    init_limbo()
                    GAME_STATE = 'PLAYING'
                    if npcs:
                        start_npc_conversation(npcs[0])
                elif current_level_idx == 10:
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
                elif lvl_config.get('type') == 'manor_stealth':
                    # Malikane'de düşme → ölüm yok, başlangıç noktasına respawn
                    player_x, player_y = 120.0, float(LOGICAL_HEIGHT - 110)
                    y_velocity = 0
                    is_jumping = is_dashing = is_slamming = False
                    jumps_left = MAX_JUMPS
                elif lvl_config.get('type') == 'debug_arena':
                    # Debug Arena: zemin ortasına ışınlan, oyun kesilmez
                    player_x = float(LOGICAL_WIDTH // 2 - 14)
                    player_y = float(LOGICAL_HEIGHT - 80 - 42)
                    y_velocity = 0
                    is_jumping = is_dashing = is_slamming = False
                    jumps_left = MAX_JUMPS
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
            'term_input': terminal_input,
            'term_status': terminal_status,
            'is_debug_arena': (current_level_idx == 999),
            'level_select_page': level_select_page,
            'has_talisman': has_talisman,
            # --- DÖVÜŞ SİSTEMİ ---
            'beat_arena_active': beat_arena.active,
            'arena_wave':  beat_arena.current_wave,
            'arena_total': beat_arena.total_waves,
            'combo_info':  combo_system.get_hud_info(),
            'player_hp':   player_hp.current_hp,
            'player_hp_max': player_hp.max_hp,
            # --- STAMINA ---
            'stamina':     player_hp.current_stamina,
            'stamina_max': player_hp.max_stamina,
            # --- ALTIPATAR ---
            'player_bullets': player_bullets,
            'gun_cooldown':   gun_cooldown,
            'is_reloading':   is_reloading,
            # --- YENİ SİLAH SİSTEMİ ---
            'active_weapon':  active_weapon_obj.WEAPON_TYPE if active_weapon_obj else None,
            'mag_size':       active_weapon_obj.mag_size if active_weapon_obj else 0,
            'spare_mags':     active_weapon_obj.spare_mags if active_weapon_obj else 0,
            'inventory_weapons': list(inventory_weapons),
            'chest_prompt':   any(
                math.sqrt((player_x + 14 - _c.rect.centerx)**2 + (player_y + 21 - _c.rect.centery)**2)
                < WeaponChest.INTERACT_RADIUS
                for _c in all_weapon_chests
            ),
        }

        if GAME_STATE in ['MENU', 'SETTINGS', 'LOADING', 'LEVEL_SELECT', 'ENDLESS_SELECT']:
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

            # ── 4b. Vasil intro arena arka plan (Level 0) ────────────────
            if current_level_idx == 0:
                _vasil_boss_ref = next(
                    (e for e in all_enemies if isinstance(e, VasilBoss)), None
                )
                _arena_timer = getattr(_vasil_boss_ref, '_fight_timer', 0.0) if _vasil_boss_ref else 0.0
                draw_vasil_arena_bg(game_canvas, _arena_timer, LOGICAL_WIDTH, LOGICAL_HEIGHT)

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

            # ── Can Kürelerini çiz ────────────────────────────────────────
            for _orb in all_health_orbs:
                _orb.draw(game_canvas, render_offset, CURRENT_THEME)

            # ── Silah Sandıkları çiz ──────────────────────────────────────
            for _wc in all_weapon_chests:
                _wc.draw(game_canvas)
                _wc.draw_prompt(game_canvas, player_x + 14, player_y + 21)

            # ── Cephane Pickup'larını çiz ─────────────────────────────────
            for _ap in all_ammo_pickups:
                _ap.draw(game_canvas)

            # ── Kombo sistemi hitbox (her bölümde) ───────────────────────
            combo_system.draw(vfx_surface)

            # ── Combat HUD (her bölümde) — kombo zinciri ────────────────
            # HP + Stamina barları ui_system.py içinde render edilir (Step 12).
            # Kombo zinciri her bölümde görünür
            hud_info = combo_system.get_hud_info()
            if hud_info.get('chain') or hud_info.get('last_combo'):
                combat_hud.draw(game_canvas, hud_info)

            # VFX partikülleri ve trail'leri ayrı yüzeye çiz
            for v in all_vfx:
                v.draw(vfx_surface)
            for trail in trail_effects:
                trail.draw(vfx_surface)

            # ── Oyuncu mermilerini çiz (VFX yüzeyi üstünde) ──────────────
            _bullet_wtype = 'default'
            if active_weapon_obj is not None:
                _bullet_wtype = getattr(active_weapon_obj, 'WEAPON_TYPE', 'default')
            for _p in all_player_projectiles:
                draw_player_bullet(game_canvas, _p, _bullet_wtype)

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

                _px = int(player_x) + render_offset[0] + int(-manor_camera_offset_x)
                _py = int(player_y) + render_offset[1] + int(-manor_camera_offset_y)

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

            # ── 8b. SİLAH ÇİZİMİ — oyuncunun üstünde, partiküllerin altında ──
            if (GAME_STATE in ('PLAYING', 'PAUSED', 'ENDLESS_PLAY', 'CHAT')
                    and active_weapon_obj is not None
                    and active_weapon_obj.visual is not None):
                _wep_base_x = int(player_x) + render_offset[0] + int(-manor_camera_offset_x)
                _wep_base_y = int(player_y) + render_offset[1] + int(-manor_camera_offset_y)
                _wep_pivot_x = _wep_base_x + 14   # hitbox merkezi X
                _wep_pivot_y = _wep_base_y + 22   # omuz hizası Y
                active_weapon_obj.draw(
                    game_canvas,
                    _wep_pivot_x, _wep_pivot_y,
                    aim_angle, weapon_shoot_timer
                )

                # ── DEBUG: Spread (dağılım) konisi ───────────────────────────
                if DEBUG_SPRITE and active_weapon_obj is not None:
                    _sp_cur  = getattr(active_weapon_obj, 'current_spread', 0.0)
                    _sp_max  = getattr(active_weapon_obj, '_spread_max', 0.2)
                    _sp_rec  = getattr(active_weapon_obj, '_spread_recovery', 2.5)
                    _sp_inc  = getattr(active_weapon_obj, '_spread_inc', 0.05)
                    _sp_pct  = min(1.0, _sp_cur / max(_sp_max, 0.001))   # 0..1 (clamp: spread > _spread_max olursa renk taşmaz)
                    _cone_r  = 160   # Koni yarıçapı (piksel)
                    _px0     = _wep_pivot_x
                    _py0     = _wep_pivot_y

                    # ── 1. DOLU MAKSİMUM KONİ (sabit gri, arka plan) ─────────
                    _steps = 24
                    _max_pts = [(_px0, _py0)]
                    for _i in range(_steps + 1):
                        _a = aim_angle - _sp_max + (2 * _sp_max * _i / _steps)
                        _max_pts.append((
                            int(_px0 + math.cos(_a) * _cone_r),
                            int(_py0 + math.sin(_a) * _cone_r)
                        ))
                    _max_surf = pygame.Surface(
                        (game_canvas.get_width(), game_canvas.get_height()), pygame.SRCALPHA
                    )
                    if len(_max_pts) >= 3:
                        pygame.draw.polygon(_max_surf, (180, 180, 180, 18), _max_pts)
                        pygame.draw.lines(_max_surf, (180, 180, 180, 60), False,
                                          [_max_pts[1], _max_pts[0], _max_pts[-1]], 1)
                    game_canvas.blit(_max_surf, (0, 0))

                    # ── 2. DOLU MEVCUT KONİ (yeşil→turuncu→kırmızı renk geçişi) ─
                    if _sp_cur > 0.001:
                        _r_col = int(50  + 205 * _sp_pct)
                        _g_col = int(230 - 180 * _sp_pct)
                        _cur_pts = [(_px0, _py0)]
                        for _i in range(_steps + 1):
                            _a = aim_angle - _sp_cur + (2 * _sp_cur * _i / _steps)
                            _cur_pts.append((
                                int(_px0 + math.cos(_a) * _cone_r),
                                int(_py0 + math.sin(_a) * _cone_r)
                            ))
                        _cur_surf = pygame.Surface(
                            (game_canvas.get_width(), game_canvas.get_height()), pygame.SRCALPHA
                        )
                        _fill_alpha = int(30 + 60 * _sp_pct)
                        if len(_cur_pts) >= 3:
                            pygame.draw.polygon(_cur_surf, (_r_col, _g_col, 20, _fill_alpha), _cur_pts)
                            # Kenar çizgileri (pivot → iki uç nokta)
                            pygame.draw.line(_cur_surf, (_r_col, _g_col, 20, 200),
                                             (_px0, _py0), _cur_pts[1], 2)
                            pygame.draw.line(_cur_surf, (_r_col, _g_col, 20, 200),
                                             (_px0, _py0), _cur_pts[-1], 2)
                        game_canvas.blit(_cur_surf, (0, 0))

                    # ── 3. MERKEZ NİŞAN ÇİZGİSİ ─────────────────────────────
                    _aim_ex = int(_px0 + math.cos(aim_angle) * _cone_r)
                    _aim_ey = int(_py0 + math.sin(aim_angle) * _cone_r)
                    pygame.draw.line(game_canvas, (0, 255, 120), (_px0, _py0), (_aim_ex, _aim_ey), 1)
                    # Nokta ucu
                    pygame.draw.circle(game_canvas, (0, 255, 120), (_aim_ex, _aim_ey), 3)

                    # ── 4. BİLGİ PANELİ ─────────────────────────────────────
                    _pf = pygame.font.Font(None, 18)
                    _bar_x  = _px0 + 14
                    _bar_y  = _py0 - 58
                    _bar_w  = 90
                    _bar_h  = 7
                    # Panel arka plan
                    _panel = pygame.Surface((110, 72), pygame.SRCALPHA)
                    _panel.fill((0, 0, 0, 160))
                    game_canvas.blit(_panel, (_bar_x - 4, _bar_y - 4))
                    # Spread bar
                    pygame.draw.rect(game_canvas, (60, 60, 60),    (_bar_x, _bar_y,            _bar_w, _bar_h))
                    pygame.draw.rect(game_canvas, (_r_col if _sp_cur > 0.001 else 50,
                                                   _g_col if _sp_cur > 0.001 else 230, 20),
                                                  (_bar_x, _bar_y, int(_bar_w * _sp_pct), _bar_h))
                    pygame.draw.rect(game_canvas, (120, 120, 120), (_bar_x, _bar_y, _bar_w, _bar_h), 1)
                    # Metinler
                    _wname = active_weapon_obj.WEAPON_TYPE.upper()
                    game_canvas.blit(_pf.render(f"[{_wname}] SPREAD", True, (200, 200, 200)),
                                     (_bar_x, _bar_y - 14))
                    game_canvas.blit(_pf.render(f"cur  {_sp_cur:.3f} rad", True, (255, 220, 60)),
                                     (_bar_x, _bar_y + 10))
                    game_canvas.blit(_pf.render(f"max  {_sp_max:.3f} rad", True, (160, 160, 160)),
                                     (_bar_x, _bar_y + 24))
                    game_canvas.blit(_pf.render(f"+inc {_sp_inc:.3f}  rec {_sp_rec:.1f}/s", True, (120, 200, 255)),
                                     (_bar_x, _bar_y + 38))
                    game_canvas.blit(_pf.render(f"{int(_sp_pct * 100):3d}%", True,
                                                (int(50+205*_sp_pct), int(230-180*_sp_pct), 20)),
                                     (_bar_x + 68, _bar_y + 10))

            # ── 8c. TRAJECTORY IZGARA — Mermi yolu göstergesi ───────────────
            # DEBUG_SPRITE'dan bağımsız, her zaman gösterilir.
            # Rule 3: _traj_surface pre-allocated, her frame sadece fill+draw.
            if (GAME_STATE in ('PLAYING', 'ENDLESS_PLAY')
                    and active_weapon_obj is not None
                    and not active_weapon_obj.is_reloading
                    and active_weapon_obj.bullets > 0):

                _traj_surface.fill((0, 0, 0, 0))

                _tr_px = int(player_x) + render_offset[0] + int(-manor_camera_offset_x) + 14
                _tr_py = int(player_y) + render_offset[1] + int(-manor_camera_offset_y) + 22

                _tr_wtype = getattr(active_weapon_obj, 'WEAPON_TYPE', 'revolver')
                if _tr_wtype == 'revolver':
                    _tr_rgb = (255, 200, 50)
                elif _tr_wtype == 'smg':
                    _tr_rgb = (80, 210, 255)
                elif _tr_wtype == 'shotgun':
                    _tr_rgb = (255, 130, 40)
                else:
                    _tr_rgb = (200, 200, 200)

                _tgp      = active_weapon_obj.get_trajectory_grid_points(
                    _tr_px, _tr_py, aim_angle, step_px=45, total_px=315
                )
                _tg_steps  = len(_tgp['center'])
                _tg_spread = _tgp['spread']

                if _tg_steps >= 2:
                    pygame.draw.line(_traj_surface, (*_tr_rgb, 30),
                                     _tgp['center'][0], _tgp['center'][-1], 1)

                for _tgi in range(1, _tg_steps):
                    _tg_alpha = int(160 * (1.0 - (_tgi / _tg_steps)))
                    pygame.draw.circle(_traj_surface, (*_tr_rgb, _tg_alpha),
                                       _tgp['center'][_tgi], 2)
                    if _tg_spread > 0.001:
                        _tu = _tgp['upper'][_tgi]
                        _tl = _tgp['lower'][_tgi]
                        _ra = max(25, _tg_alpha // 3)
                        pygame.draw.circle(_traj_surface,
                                           (*_tr_rgb, max(40, _tg_alpha-30)), _tu, 2)
                        pygame.draw.circle(_traj_surface,
                                           (*_tr_rgb, max(40, _tg_alpha-30)), _tl, 2)
                        if _tgi - 1 < len(_tgp['rungs']):
                            pygame.draw.line(_traj_surface, (*_tr_rgb, _ra),
                                             _tgp['rungs'][_tgi-1][0],
                                             _tgp['rungs'][_tgi-1][1], 1)

                if _tg_spread > 0.001 and len(_tgp['upper']) >= 2:
                    for _tgi2 in range(1, _tg_steps, 2):
                        _ta2 = max(20, int(80 * (1.0 - (_tgi2 / _tg_steps))))
                        if _tgi2 < len(_tgp['upper']):
                            pygame.draw.line(_traj_surface, (*_tr_rgb, _ta2),
                                             _tgp['upper'][_tgi2-1], _tgp['upper'][_tgi2], 1)
                            pygame.draw.line(_traj_surface, (*_tr_rgb, _ta2),
                                             _tgp['lower'][_tgi2-1], _tgp['lower'][_tgi2], 1)

                game_canvas.blit(_traj_surface, (0, 0))

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
                elif lvl_config.get('type') == 'debug_arena':
                    # Debug Arena HUD: geliştirici ipuçları
                    _db_font = pygame.font.Font(None, 24)
                    _db_hints = [
                        "[ DEBUG ARENA - GELISTIRICI MODU ]",
                        "WASD: Hareket   W: Zipla   SPACE: Dash",
                        "J: Hafif  K: Agir  S(havada): Slam",
                        "ESC: Menuye Don   F12: Debug Arena'ya Don",
                    ]
                    _db_y = LOGICAL_HEIGHT - 105
                    for _dh in _db_hints:
                        _dh_surf = _db_font.render(_dh, True, (80, 220, 80))
                        game_canvas.blit(_dh_surf, (40, _db_y))
                        _db_y += 24
                    # Sağ üst köşeye kırmızı "DEBUG" etiketi
                    _db_tag = pygame.font.Font(None, 26).render("[ DEBUG ARENA ]", True, (255, 50, 50))
                    game_canvas.blit(_db_tag, (LOGICAL_WIDTH - _db_tag.get_width() - 12, 8))
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
                    frame_count % 10 == 0 or
                    GAME_STATE == 'INVENTORY' or  # Envanter her frame güncellenir
                    GAME_STATE == 'TERMINAL'    # Terminal her frame güncellenir (cursor blink)
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