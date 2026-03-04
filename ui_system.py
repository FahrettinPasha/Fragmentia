import pygame
import math
from settings import *
from settings import REVOLVER_MAX_BULLETS, REVOLVER_COOLDOWN
from utils import draw_text_with_shadow, wrap_text
from story_system import ai_chat_effect

# ============================================================
#  UI PLACEHOLDER MODÜLÜ
#
#  Tüm süslü cyberpunk dekorasyonlar (glitch efekti, ızgara,
#  hareketli scanline, köşe aksanları vb.) kaldırıldı.
#
#  Kalan şeyler: düz renkli paneller, düz çerçeveler, butonlar,
#  font bazlı metinler.
#
#  [TODO - PIXEL ART / UI ART]:
#    - Arkaplan → sprite/tileset
#    - Paneller → 9-slice veya custom frame sprite
#    - Butonlar → hover/pressed/locked state spriteları
#    - İkonlar → pixel art ikonlar
# ============================================================


# --- YARDIMCI FONKSİYONLAR ---

def draw_glitch_text(surface, text, size, x, y, color, intensity=2):
    """
    PLACEHOLDER: Glitch efekti kaldırıldı — düz metin.
    [TODO - UI ART]: Özel title font veya animasyonlu başlık ile değiştir.
    """
    font = pygame.font.Font(None, size)
    draw_text_with_shadow(surface, text, font, (x, y), color, align='center')


def draw_cyber_panel(surface, rect, color, title=""):
    """
    PLACEHOLDER: Cyberpunk köşe aksanları kaldırıldı.
    Sadece düz dikdörtgen çerçeve çiziliyor.
    [TODO - UI ART]: 9-slice panel sprite ile değiştir.
    """
    # Yarı saydam iç dolgu
    try:
        panel_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 200))
        surface.blit(panel_surf, rect.topleft)
    except:
        pygame.draw.rect(surface, (0, 0, 0), rect)

    # Düz çerçeve
    pygame.draw.rect(surface, color, rect, 2)

    # Başlık (varsa)
    if title:
        title_font = pygame.font.Font(None, 24)
        title_surf = title_font.render(f" {title} ", True, (0, 0, 0))
        title_w = title_surf.get_width()
        title_bg = pygame.Rect(rect.centerx - title_w // 2, rect.y - 12, title_w, 20)
        pygame.draw.rect(surface, color, title_bg)
        surface.blit(title_surf, title_bg.topleft)


def draw_button(surface, rect, text, is_hovered, color_theme=BUTTON_COLOR, locked=False):
    """Düz buton — hover'da hafif parlama."""
    if locked:
        color = LOCKED_BUTTON_COLOR
        border = (60, 60, 60)
        text_col = LOCKED_TEXT_COLOR
        text = f"[KİLİTLİ] {text}"
    else:
        color = BUTTON_HOVER_COLOR if is_hovered else color_theme
        border = WHITE if is_hovered else (80, 80, 80)
        text_col = WHITE if is_hovered else BUTTON_TEXT_COLOR

    draw_rect = rect.inflate(4, 4) if is_hovered and not locked else rect.copy()

    pygame.draw.rect(surface, color, draw_rect)
    pygame.draw.rect(surface, border, draw_rect, 2)

    font = pygame.font.Font(None, 30)
    draw_text_with_shadow(surface, text, font, draw_rect.center, text_col)


def draw_cyber_rect(surface, rect, color, filled=False, alpha=255):
    """
    PLACEHOLDER: Köşe kesiği kaldırıldı — düz dikdörtgen.
    [TODO - UI ART]: Pixel art çerçeve ile değiştir.
    """
    if filled:
        try:
            s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            s.fill((*color, alpha))
            surface.blit(s, rect.topleft)
        except:
            pygame.draw.rect(surface, color, rect)
    else:
        pygame.draw.rect(surface, color, rect, 2)


def draw_level_card(surface, rect, level_num, level_info, status, high_score, is_hovered):
    """Bölüm kartı — düz, okunabilir."""
    if status == "LOCKED":
        bg_color = (30, 30, 30)
        border_color = (60, 60, 60)
        text_color = (100, 100, 100)
    elif status == "COMPLETED":
        bg_color = (0, 40, 20)
        border_color = NEON_GREEN
        text_color = WHITE
    elif status == "BOSS":
        bg_color = (40, 10, 10)
        border_color = (220, 50, 50)
        text_color = (255, 180, 180)
    else:  # UNLOCKED
        bg_color = (0, 30, 40)
        border_color = NEON_CYAN
        text_color = WHITE

    draw_rect = rect.inflate(6, 6) if is_hovered and status != "LOCKED" else rect.copy()
    if is_hovered and status != "LOCKED":
        border_color = WHITE

    pygame.draw.rect(surface, bg_color, draw_rect)
    pygame.draw.rect(surface, border_color, draw_rect, 2)

    center_x = draw_rect.centerx

    # Bölüm numarası
    num_font = pygame.font.Font(None, 36)
    num_text = f"#{level_num}"
    draw_text_with_shadow(surface, num_text, num_font,
                          (center_x, draw_rect.y + 22), border_color, align='center')

    # Bölüm adı
    name_font = pygame.font.Font(None, 22)
    display_name = level_info['name']
    if status == "LOCKED":
        display_name = "ERİŞİM YOK"
    if len(display_name) > 18:
        display_name = display_name[:16] + ".."
    draw_text_with_shadow(surface, display_name, name_font,
                          (center_x, draw_rect.y + 50), text_color, align='center')

    # High score
    if status != "LOCKED" and high_score > 0:
        score_font = pygame.font.Font(None, 19)
        draw_text_with_shadow(surface, f"* {high_score}", score_font,
                              (center_x, draw_rect.bottom - 18), (220, 200, 50), align='center')

    return draw_rect


# --- SAHNE FONKSİYONLARI ---

def render_cutscene(surface, story_manager):
    w, h = surface.get_width(), surface.get_height()
    surface.fill((0, 0, 0))

    text_box = pygame.Rect(w // 2 - 400, h // 2 - 100, 800, 200)
    draw_cyber_panel(surface, text_box, (120, 120, 120))

    font = pygame.font.Font(None, 38)
    lines = wrap_text(story_manager.display_text, font, 760)
    start_y = text_box.y + 30
    for i, line in enumerate(lines):
        draw_text_with_shadow(surface, line, font,
                              (text_box.centerx, start_y + i * 44), WHITE, align='center')

    if story_manager.waiting_for_click:
        blink = (pygame.time.get_ticks() // 500) % 2 == 0
        if blink:
            blink_font = pygame.font.Font(None, 24)
            draw_text_with_shadow(surface, "DEVAM ETMEK İÇİN TIKLA >", blink_font,
                                  (w - 220, h - 45), (160, 240, 240), align='center')
    return {}


def render_chat_interface(surface, story_manager):
    w, h = surface.get_width(), surface.get_height()

    # Yarı saydam arka plan
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill(CHAT_BG)
    surface.blit(overlay, (0, 0))

    chat_rect = pygame.Rect(w // 2 - 400, h // 2 - 150, 800, 300)
    draw_cyber_panel(surface, chat_rect, CHAT_BORDER, "SECURE_CONNECTION: NEXUS_AI")

    speaker = story_manager.speaker
    color = SPEAKER_NEXUS if speaker == "NEXUS" else SPEAKER_SYSTEM

    # Avatar (placeholder daire)
    avatar_x, avatar_y = chat_rect.x + 70, chat_rect.centery
    thinking = story_manager.state == "THINKING"
    ai_chat_effect.draw_ai_avatar(surface, avatar_x, avatar_y, 40, thinking)

    # Konuşan isim
    speaker_font = pygame.font.Font(None, 36)
    draw_text_with_shadow(surface, speaker, speaker_font,
                          (avatar_x, avatar_y + 60), color, align='center')

    # Metin
    text_x = chat_rect.x + 140
    text_y = chat_rect.y + 40
    font = pygame.font.Font(None, 33)
    lines = wrap_text(story_manager.display_text, font, 620)
    for i, line in enumerate(lines):
        draw_text_with_shadow(surface, line, font,
                              (text_x, text_y + i * 38), TEXT_COLOR, align='topleft')

    # Devam oku
    if story_manager.waiting_for_click:
        blink = (pygame.time.get_ticks() // 500) % 2 == 0
        if blink:
            blink_font = pygame.font.Font(None, 28)
            draw_text_with_shadow(surface, "v", blink_font,
                                  (chat_rect.right - 35, chat_rect.bottom - 35), color, align='center')
    return {}


def render_loading_screen(surface, progress):
    w, h = surface.get_width(), surface.get_height()
    surface.fill((8, 8, 12))

    bar_w, bar_h = 500, 28
    bar_x = w // 2 - bar_w // 2
    bar_y = h // 2

    title_font = pygame.font.Font(None, 48)
    draw_text_with_shadow(surface, "YÜKLENİYOR...", title_font,
                          (w // 2, bar_y - 55), UI_BORDER_COLOR, align='center')

    pygame.draw.rect(surface, LOADING_BAR_BG, (bar_x, bar_y, bar_w, bar_h))
    pygame.draw.rect(surface, LOADING_BAR_FILL, (bar_x, bar_y, int(bar_w * progress), bar_h))
    pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_w, bar_h), 2)

    pct_font = pygame.font.Font(None, 32)
    draw_text_with_shadow(surface, f"%{int(progress * 100)}", pct_font,
                          (w // 2, bar_y + 50), WHITE, align='center')
    return {}


def render_cheat_terminal(surface, input_text, status_msg, debug_mode=False):
    """
    Cheat Terminal UI.
    debug_mode=True → Debug Arena komut listesini gösterir (daha büyük panel).
    """
    w, h = surface.get_width(), surface.get_height()

    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 15, 5, 220))
    surface.blit(overlay, (0, 0))

    if debug_mode:
        term_w, term_h = 860, 560
    else:
        term_w, term_h = 800, 360
    term_rect = pygame.Rect(w // 2 - term_w // 2, h // 2 - term_h // 2, term_w, term_h)

    title = "DEBUG_ARENA_TERMINAL v2.0" if debug_mode else "ROOT_ACCESS_TERMINAL v1.0"
    draw_cyber_panel(surface, term_rect, (0, 220, 0), title)

    font     = pygame.font.Font(None, 30)
    sm_font  = pygame.font.Font(None, 22)
    hint_font= pygame.font.Font(None, 21)

    header_y = term_rect.y + 50
    if debug_mode:
        draw_text_with_shadow(surface, "FRAGMENTIA DEBUG SPAWNER — Komut gir, ENTER'a bas:",
                              font, (term_rect.x + 24, header_y), (0, 220, 0), align='topleft')

        # Komut tablosu
        commands = [
            ("spawn cursed",   "CursedEnemy — standart yakın dövüş düşmanı"),
            ("spawn tank",     "TankEnemy   — zırhlı ağır düşman"),
            ("spawn drone",    "DroneEnemy  — uçan drone"),
            ("spawn vasil",    "VasilBoss   — Vasil boss"),
            ("spawn ares",     "AresBoss    — Ares boss"),
            ("spawn nexus",    "NexusBoss   — Nexus boss"),
            ("spawn chest",    "WeaponChest — silah sandığı"),
            ("spawn shotgun",  "Pompalı tüfeği envantere ekle  (3 ile kuşan)"),
            ("spawn ammo",     "AmmoPickup  — cephane kutusu"),
            ("spawn health",   "HealthOrb   — can küresi"),
            ("clear enemies",  "Tüm düşmanları temizle"),
            ("clear all",      "Tüm spawn edilen nesneleri temizle"),
            ("god on/off",     "Oyuncuya süper mod aç/kapat"),
            ("--- KISA YOL ---", "1:Revolver  2:SMG  3:Pompalı  Num1-3:Düşman Spawn"),
            ("help",           "Bu yardım menüsünü göster"),
        ]
        col1_x  = term_rect.x + 24
        col2_x  = term_rect.x + 250
        row_h   = 22
        tbl_y   = header_y + 30
        for i, (cmd, desc) in enumerate(commands):
            cy = tbl_y + i * row_h
            pygame.draw.rect(surface, (0, 30, 0) if i % 2 == 0 else (0, 20, 0),
                             (col1_x - 4, cy - 2, term_w - 36, row_h - 1))
            draw_text_with_shadow(surface, cmd,  sm_font, (col1_x, cy), (0, 255, 120), align='topleft')
            draw_text_with_shadow(surface, desc, sm_font, (col2_x, cy), (160, 200, 160), align='topleft')

        input_y = tbl_y + len(commands) * row_h + 14
    else:
        draw_text_with_shadow(surface, "C:\\NEXUS\\SYSTEM> HİLE KODU GİRİN:", font,
                              (term_rect.x + 30, header_y + 5), (0, 220, 0), align='topleft')
        input_y = term_rect.y + 100

    # ── Giriş kutusu ────────────────────────────────────────────────────────
    input_box = pygame.Rect(term_rect.x + 24, input_y, term_w - 48, 40)
    pygame.draw.rect(surface, (0, 40, 0), input_box)
    pygame.draw.rect(surface, (0, 220, 0), input_box, 2)
    cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
    draw_text_with_shadow(surface, f"> {input_text}{cursor}", font,
                          (input_box.x + 10, input_box.centery), (180, 255, 180), align='midleft')

    # ── Durum mesajı ─────────────────────────────────────────────────────────
    status_color = (255, 200, 0) if "BEKLENİYOR" in status_msg else (
        (0, 220, 80) if any(k in status_msg for k in ("OK", "AKTİF", "SPAWN", "TEMİZLENDİ")) else (220, 50, 50))
    draw_text_with_shadow(surface, f">> {status_msg}", font,
                          (term_rect.x + 24, input_box.bottom + 10), status_color, align='topleft')

    draw_text_with_shadow(surface, "[ENTER] ONAYLA   [ESC] ÇIKIŞ   [T] TEKRAR AÇ", hint_font,
                          (term_rect.centerx, term_rect.bottom - 18), (100, 100, 100), align='center')
    return {}


def render_main_menu(surface, mouse_pos, buttons):
    w, h = surface.get_width(), surface.get_height()
    surface.fill(UI_BG_COLOR)

    # [TODO - PIXEL ART]: Arkaplan sprite burada çizilecek.

    # Başlık
    draw_glitch_text(surface, "NEON RUNNER", 130, w // 2, 140, UI_BORDER_COLOR)

    subtitle_font = pygame.font.Font(None, 28)
    draw_text_with_shadow(surface, "NEXUS CHRONICLES (AI EDITION)", subtitle_font,
                          (w // 2, 220), (0, 200, 200), align='center')

    menu_rect = pygame.Rect(w // 2 - 200, 290, 400, 440)
    draw_cyber_panel(surface, menu_rect, UI_BORDER_COLOR, "MAIN_ACCESS")

    active_buttons = {}
    btn_configs = [
        ('story_mode',     "HİKAYE MODU",      340, (0, 50, 80)),
        ('level_select',   "BÖLÜM SEÇ",         398, (0, 60, 60)),
        ('settings',       "AYARLAR",            456, BUTTON_COLOR),
        ('cheat_terminal', "HİLE TERMİNALİ",    514, (50, 0, 50)),
        ('exit',           "ÇIKIŞ",              572, (60, 0, 0)),
    ]

    for key, label, y, col in btn_configs:
        btn = pygame.Rect(w // 2 - 150, y, 300, 48)
        draw_button(surface, btn, label, btn.collidepoint(mouse_pos), col)
        active_buttons[key] = btn

    return active_buttons


def render_level_select(surface, mouse_pos, save_data, page_index=0):
    w, h = surface.get_width(), surface.get_height()
    surface.fill(UI_BG_COLOR)

    # [TODO - PIXEL ART]: Arkaplan sprite burada çizilecek.

    if not save_data or 'easy_mode' not in save_data:
        easy_data = {'unlocked_levels': 1, 'completed_levels': [], 'high_scores': {}}
    else:
        easy_data = save_data['easy_mode']

    unlocked_lvl = easy_data['unlocked_levels']

    ACTS = [
        {
            "title": "ACT I: YERALTI KÖKLERİ",
            "color": (50, 220, 100),
            "groups": [
                {"name": "THE GUTTER (ÇÖPLÜK)", "levels": range(1, 6),  "theme_col": (50, 180, 50)},
                {"name": "INDUSTRIAL ZONE",      "levels": range(6, 11), "theme_col": (220, 100, 0)}
            ]
        },
        {
            "title": "ACT II: NEON METROPOL",
            "color": (0, 180, 240),
            "groups": [
                {"name": "THE SLUMS (VAROŞLAR)",  "levels": range(11, 15), "theme_col": (0, 100, 200)},
                {"name": "NEON DOWNTOWN (MERKEZ)", "levels": range(15, 24), "theme_col": (180, 0, 220)},
                {"name": "HIGHWAY (ÇIKIŞ)",        "levels": range(24, 25), "theme_col": (220, 220, 220)}
            ]
        },
        {
            "title": "ACT III: SİSTEMİN KALBİ",
            "color": (220, 50, 50),
            "groups": [
                {"name": "FIREWALL (GÜVENLİK)", "levels": range(25, 30), "theme_col": (180, 50, 50)},
                {"name": "THE CORE (ÇEKİRDEK)", "levels": range(30, 31), "theme_col": (220, 180, 0)}
            ]
        }
    ]

    page_index = max(0, min(page_index, len(ACTS) - 1))
    current_act = ACTS[page_index]
    active_buttons = {}

    # --- Sekme Başlıkları ---
    tab_w = 300
    start_tab_x = (w - len(ACTS) * tab_w) // 2
    for i, act in enumerate(ACTS):
        tab_rect = pygame.Rect(start_tab_x + i * tab_w, 40, tab_w - 8, 48)
        is_active = (i == page_index)
        bg = act['color'] if is_active else (40, 40, 40)
        draw_cyber_rect(surface, tab_rect, bg, filled=True, alpha=200 if is_active else 80)
        pygame.draw.rect(surface, bg if is_active else (80, 80, 80), tab_rect, 2)
        tab_font = pygame.font.Font(None, 26)
        draw_text_with_shadow(surface, act['title'], tab_font, tab_rect.center,
                              WHITE if is_active else (140, 140, 140), align='center')

    # --- Bölüm Kartları ---
    card_w, card_h = 195, 105
    gap_x, gap_y = 25, 18
    current_y = 120

    for group in current_act['groups']:
        # Grup başlığı
        line_y = current_y + 18
        pygame.draw.line(surface, group['theme_col'], (50, line_y), (w - 50, line_y), 1)
        hdr_font = pygame.font.Font(None, 32)
        hdr_surf = hdr_font.render(f"  {group['name']}  ", True, group['theme_col'])
        hdr_rect = hdr_surf.get_rect(center=(w // 2, line_y))
        pygame.draw.rect(surface, UI_BG_COLOR, hdr_rect)
        surface.blit(hdr_surf, hdr_rect)
        current_y += 48

        levels = list(group['levels'])
        cols = 6
        actual_cols = min(len(levels), cols)
        actual_w = actual_cols * card_w + (actual_cols - 1) * gap_x
        start_x = (w - actual_w) // 2
        rows = math.ceil(len(levels) / cols)

        for i, lvl_num in enumerate(levels):
            col = i % cols
            row = i // cols
            x = start_x + col * (card_w + gap_x)
            y = current_y + row * (card_h + gap_y)
            card_rect = pygame.Rect(x, y, card_w, card_h)

            lvl_info = EASY_MODE_LEVELS.get(lvl_num, {'name': 'BİLİNMEYEN', 'type': 'normal'})

            status = "LOCKED"
            if lvl_num <= unlocked_lvl:
                status = "UNLOCKED"
                if lvl_num in easy_data['completed_levels']:
                    status = "COMPLETED"
                if lvl_info.get('type') in ['scrolling_boss', 'boss_fight']:
                    status = "BOSS"
                    if lvl_num > unlocked_lvl:
                        status = "LOCKED"

            h_score = easy_data['high_scores'].get(str(lvl_num), 0)
            is_hover = card_rect.collidepoint(mouse_pos)
            final_rect = draw_level_card(surface, card_rect, lvl_num, lvl_info, status, h_score, is_hover)
            if status != "LOCKED":
                active_buttons[f'level_{lvl_num}'] = final_rect

        current_y += rows * (card_h + gap_y) + 35

    # --- Navigasyon ---
    if page_index > 0:
        btn_prev = pygame.Rect(40, h // 2 - 50, 55, 100)
        is_h = btn_prev.collidepoint(mouse_pos)
        pygame.draw.rect(surface, BUTTON_HOVER_COLOR if is_h else (30, 30, 30), btn_prev)
        pygame.draw.rect(surface, UI_BORDER_COLOR, btn_prev, 2)
        arr_font = pygame.font.Font(None, 55)
        draw_text_with_shadow(surface, "<", arr_font, btn_prev.center, WHITE, align='center')
        active_buttons['prev_page'] = btn_prev

    if page_index < len(ACTS) - 1:
        btn_next = pygame.Rect(w - 95, h // 2 - 50, 55, 100)
        is_h = btn_next.collidepoint(mouse_pos)
        pygame.draw.rect(surface, BUTTON_HOVER_COLOR if is_h else (30, 30, 30), btn_next)
        pygame.draw.rect(surface, UI_BORDER_COLOR, btn_next, 2)
        arr_font = pygame.font.Font(None, 55)
        draw_text_with_shadow(surface, ">", arr_font, btn_next.center, WHITE, align='center')
        active_buttons['next_page'] = btn_next

    btn_back = pygame.Rect(40, 40, 90, 38)
    pygame.draw.rect(surface, (60, 20, 20), btn_back)
    pygame.draw.rect(surface, (180, 50, 50), btn_back, 2)
    back_font = pygame.font.Font(None, 24)
    draw_text_with_shadow(surface, "GERİ", back_font, btn_back.center, WHITE, align='center')
    active_buttons['back'] = btn_back

    return active_buttons


def render_level_complete(surface, mouse_pos, level_data, score):
    w, h = surface.get_width(), surface.get_height()

    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 15, 5, 200))
    surface.blit(overlay, (0, 0))

    panel_rect = pygame.Rect(w // 2 - 280, h // 2 - 190, 560, 380)
    draw_cyber_panel(surface, panel_rect, NEON_GREEN, "GÖREV TAMAMLANDI")

    title_font = pygame.font.Font(None, 72)
    draw_text_with_shadow(surface, "BÖLÜM GEÇİLDİ!", title_font,
                          (w // 2, h // 2 - 110), WHITE, align='center')

    score_font = pygame.font.Font(None, 48)
    draw_text_with_shadow(surface, f"SKOR: {int(score)}", score_font,
                          (w // 2, h // 2 - 30), (240, 220, 0), align='center')

    msg_font = pygame.font.Font(None, 28)
    draw_text_with_shadow(surface, "Sonraki veri paketi yükleniyor...", msg_font,
                          (w // 2, h // 2 + 30), WHITE, align='center')

    active_buttons = {}
    btn_cont = pygame.Rect(w // 2 - 140, h // 2 + 80, 280, 48)
    draw_button(surface, btn_cont, "DEVAM ET", btn_cont.collidepoint(mouse_pos), (0, 90, 0))
    active_buttons['continue'] = btn_cont

    btn_menu = pygame.Rect(w // 2 - 140, h // 2 + 140, 280, 48)
    draw_button(surface, btn_menu, "MENÜYE DÖN", btn_menu.collidepoint(mouse_pos), (40, 40, 70))
    active_buttons['return_menu'] = btn_menu

    return active_buttons


def render_settings_menu(surface, mouse_pos, settings_data):
    w, h = surface.get_width(), surface.get_height()
    surface.fill(UI_BG_COLOR)

    draw_glitch_text(surface, "SİSTEM AYARLARI", 75, w // 2, 75, UI_BORDER_COLOR)

    panel_rect = pygame.Rect(w // 2 - 370, 130, 740, 700)
    draw_cyber_panel(surface, panel_rect, UI_BORDER_COLOR, "TERCİHLER & SES")

    active_buttons = {}
    current_y = 180
    spacing = 62
    btn_w = 640
    btn_x = w // 2 - btn_w // 2

    # --- Ses Slider'ları ---
    volume_settings = [
        ("GENEL SES",  "sound_volume",   (0, 220, 220)),
        ("MÜZİK",      "music_volume",   (220, 0, 220)),
        ("EFEKTLER",   "effects_volume", (0, 220, 80))
    ]

    label_font = pygame.font.Font(None, 27)
    for label, key, slider_color in volume_settings:
        draw_text_with_shadow(surface, label, label_font,
                              (btn_x, current_y), WHITE, align='midleft')

        slider_rect = pygame.Rect(btn_x + 155, current_y - 5, 440, 12)
        pygame.draw.rect(surface, (30, 30, 30), slider_rect)
        pygame.draw.rect(surface, (100, 100, 100), slider_rect, 1)

        volume = settings_data.get(key, 0.5)
        fill_w = int(slider_rect.width * volume)
        pygame.draw.rect(surface, slider_color, (slider_rect.x, slider_rect.y, fill_w, slider_rect.height))

        handle_x = slider_rect.x + fill_w
        handle_rect = pygame.Rect(handle_x - 5, slider_rect.y - 8, 10, 28)
        pygame.draw.rect(surface, WHITE, handle_rect)
        pygame.draw.rect(surface, slider_color, handle_rect, 2)

        active_buttons[f'slider_{key}'] = slider_rect
        current_y += spacing

    current_y += 18

    # --- Görüntü Ayarları ---
    mode_text = "MOD: [TAM EKRAN]" if settings_data.get('fullscreen', True) else "MOD: [PENCERE]"
    btn_mode = pygame.Rect(btn_x, current_y, btn_w, 48)
    draw_button(surface, btn_mode, mode_text, btn_mode.collidepoint(mouse_pos))
    active_buttons['toggle_fullscreen'] = btn_mode
    current_y += spacing - 8

    current_res = AVAILABLE_RESOLUTIONS[settings_data.get('res_index', 1)]
    res_text = f"ÇÖZÜNÜRLÜK: [{current_res[0]}x{current_res[1]}]"
    btn_res = pygame.Rect(btn_x, current_y, btn_w, 48)
    draw_button(surface, btn_res, res_text, btn_res.collidepoint(mouse_pos))
    active_buttons['change_resolution'] = btn_res
    current_y += spacing - 8

    btn_apply = pygame.Rect(btn_x, current_y, btn_w, 48)
    draw_button(surface, btn_apply, "AYARLARI UYGULA", btn_apply.collidepoint(mouse_pos), (0, 75, 0))
    active_buttons['apply_changes'] = btn_apply
    current_y += spacing

    btn_reset = pygame.Rect(btn_x, current_y, btn_w, 48)
    draw_button(surface, btn_reset, "!!! İLERLEMEYİ SIFIRLA !!!",
                btn_reset.collidepoint(mouse_pos), (75, 0, 0))
    active_buttons['reset_progress'] = btn_reset
    current_y += spacing + 8

    btn_back = pygame.Rect(w // 2 - 140, current_y, 280, 48)
    draw_button(surface, btn_back, "< GERİ", btn_back.collidepoint(mouse_pos))
    active_buttons['back'] = btn_back

    return active_buttons


def draw_weapon_hud(surface, active_weapon: str, bullets: int, mag_size: int,
                    spare_mags: int, gun_cooldown: float, is_reloading: bool,
                    inventory: list):
    """
    Aktif silahın mermi durumunu ve envanter silah ikonlarını çizer.

    Düzen (sağ alt köşe):
      [Silah İkon 1] [Silah İkon 2]   ← Weapon Switch UI
      ┌───────────────────────────┐
      │ AKTİF SİLAH  MERMİ/MAG   │   ← Ammo Counter
      │ ████░░░░  DOLDURULUYOR... │   ← Cooldown / Reload Bar
      └───────────────────────────┘

    Aktif silah türüne göre revolver haznesi veya SMG şerit göstergesi seçilir.
    """
    if active_weapon == "revolver":
        draw_revolver_hud(surface, bullets, gun_cooldown, is_reloading, spare_mags)
    elif active_weapon == "shotgun":
        draw_shotgun_hud(surface, bullets, mag_size, spare_mags, gun_cooldown, is_reloading)
    else:
        draw_smg_hud(surface, bullets, mag_size, spare_mags, gun_cooldown, is_reloading)

    # ── Silah Değiştirme UI (envanterdeki silahlar) ───────────────────────
    if len(inventory) > 1:
        draw_weapon_switch_ui(surface, active_weapon, inventory)


def draw_smg_hud(surface, bullets: int, mag_size: int, spare_mags: int,
                 gun_cooldown: float, is_reloading: bool):
    """
    [PLACEHOLDER] SMG mermi şerit göstergesi.
    Şarjördeki mermileri yatay bölmeli çubuk olarak gösterir.
    """
    w = surface.get_width()
    h = surface.get_height()
    PANEL_W, PANEL_H = 240, 110
    PANEL_X = w - PANEL_W - 24
    PANEL_Y = h - PANEL_H - 24
    panel_rect = pygame.Rect(PANEL_X, PANEL_Y, PANEL_W, PANEL_H)

    # Arka panel
    panel_surf = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
    panel_surf.fill((0, 0, 0, 200))
    surface.blit(panel_surf, panel_rect.topleft)

    accent   = (0, 200, 255)
    reload_c = (60, 200, 60)
    border_c = reload_c if is_reloading else accent
    pygame.draw.rect(surface, border_c, panel_rect, 2)

    # Başlık
    title_font = pygame.font.Font(None, 20)
    title_txt  = "HAFİF MAKİNALI"
    if is_reloading:
        title_txt = "DOLDURULUYOR..."
    surface.blit(title_font.render(title_txt, True, border_c),
                 (PANEL_X + 8, PANEL_Y + 6))

    # Mermi şeridi — her mermi için küçük dikey bölme
    STRIP_X   = PANEL_X + 8
    STRIP_Y   = PANEL_Y + 28
    STRIP_W   = PANEL_W - 16
    STRIP_H   = 30
    slot_w    = max(2, STRIP_W // max(mag_size, 1))
    gap       = 1

    for i in range(mag_size):
        sx = STRIP_X + i * (slot_w + gap)
        if i < bullets:
            color = accent
        else:
            color = (40, 40, 50)
        pygame.draw.rect(surface, color, pygame.Rect(sx, STRIP_Y, slot_w, STRIP_H))

    pygame.draw.rect(surface, border_c,
                     pygame.Rect(STRIP_X, STRIP_Y, STRIP_W, STRIP_H), 1)

    # Sayı ve yedek şarjör
    cnt_font = pygame.font.Font(None, 28)
    cnt_surf = cnt_font.render(f"{bullets}/{spare_mags} MAG", True, (220, 220, 220))
    surface.blit(cnt_surf, (PANEL_X + 8, PANEL_Y + PANEL_H - 28))

    # Dolum / bekleme çubuğu
    from settings import SMG_FIRE_RATE
    BAR_X, BAR_Y, BAR_W, BAR_H = PANEL_X + 8, PANEL_Y + PANEL_H - 42, PANEL_W - 16, 8
    fire_interval = 1.0 / max(SMG_FIRE_RATE, 0.01)
    if is_reloading:
        fill_pct = 1.0 - (gun_cooldown / max(1.5, 0.01))
        bar_c    = reload_c
    elif gun_cooldown > 0:
        fill_pct = 1.0 - (gun_cooldown / max(fire_interval, 0.001))
        bar_c    = accent
    else:
        fill_pct = 1.0
        bar_c    = accent
    fill_pct = max(0.0, min(1.0, fill_pct))
    pygame.draw.rect(surface, (20, 20, 30), (BAR_X, BAR_Y, BAR_W, BAR_H))
    pygame.draw.rect(surface, bar_c,        (BAR_X, BAR_Y, int(BAR_W * fill_pct), BAR_H))
    pygame.draw.rect(surface, border_c,     (BAR_X, BAR_Y, BAR_W, BAR_H), 1)



def draw_shotgun_hud(surface, bullets: int, mag_size: int, spare_mags: int,
                     gun_cooldown: float, is_reloading: bool):
    """
    Pompalı HUD — 6 dairesel kabuk göstergesi + pump bekleme çubuğu.
    Dolu kabuklar turuncu, boş kabuklar koyu gri gösterilir.
    """
    w = surface.get_width()
    h = surface.get_height()
    PANEL_W, PANEL_H = 220, 110
    PANEL_X = w - PANEL_W - 24
    PANEL_Y = h - PANEL_H - 24
    panel_rect = pygame.Rect(PANEL_X, PANEL_Y, PANEL_W, PANEL_H)

    # Arka panel
    panel_surf = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
    panel_surf.fill((0, 0, 0, 200))
    surface.blit(panel_surf, panel_rect.topleft)

    accent   = (220, 120, 30)   # turuncu-kahve
    reload_c = (60,  200, 60)
    border_c = reload_c if is_reloading else accent
    pygame.draw.rect(surface, border_c, panel_rect, 2)

    # Başlık
    title_font = pygame.font.Font(None, 20)
    title_txt  = "POMPALI TÜFEK"
    if is_reloading:
        title_txt = "DOLDURULUYOR..."
    elif gun_cooldown > 0:
        title_txt = "PUMP..."
    surface.blit(title_font.render(title_txt, True, border_c),
                 (PANEL_X + 8, PANEL_Y + 6))

    # ── Kabuk daireleri ────────────────────────────────────────────────────
    shell_r    = 10
    shell_gap  = 6
    total_w    = mag_size * (shell_r * 2 + shell_gap) - shell_gap
    start_x    = PANEL_X + (PANEL_W - total_w) // 2 + shell_r
    shell_y    = PANEL_Y + 38

    for idx in range(mag_size):
        cx = start_x + idx * (shell_r * 2 + shell_gap)
        filled = idx < bullets
        color  = (220, 130, 30) if filled else (50, 50, 50)
        pygame.draw.circle(surface, color, (cx, shell_y), shell_r)
        pygame.draw.circle(surface, border_c, (cx, shell_y), shell_r, 1)
        # Doluysa parlak merkez nokta
        if filled:
            pygame.draw.circle(surface, (255, 200, 100), (cx, shell_y), shell_r // 3)

    # ── Pump bekleme çubuğu ────────────────────────────────────────────────
    BAR_X = PANEL_X + 14
    BAR_Y = PANEL_Y + 66
    BAR_W = PANEL_W - 28
    BAR_H = 8
    pygame.draw.rect(surface, (40, 40, 40), (BAR_X, BAR_Y, BAR_W, BAR_H))
    # gun_cooldown azaldıkça çubuk doluyor
    from settings import REVOLVER_COOLDOWN  # fallback; gerçekte SHOTGUN_COOLDOWN kullan
    _pump_full = 0.75  # SHOTGUN_COOLDOWN default
    _ratio = 1.0 - min(1.0, gun_cooldown / _pump_full) if gun_cooldown > 0 else 1.0
    _fill = int(BAR_W * _ratio)
    if _fill > 0:
        pygame.draw.rect(surface, accent, (BAR_X, BAR_Y, _fill, BAR_H))
    pygame.draw.rect(surface, border_c, (BAR_X, BAR_Y, BAR_W, BAR_H), 1)

    # ── Yedek şarjör ──────────────────────────────────────────────────────
    spare_font = pygame.font.Font(None, 20)
    spare_txt  = f"YEDEK: {spare_mags}" if spare_mags < 9990 else "∞"
    surface.blit(spare_font.render(spare_txt, True, (180, 180, 180)),
                 (PANEL_X + 8, PANEL_Y + 86))

def draw_weapon_switch_ui(surface, active_weapon: str, inventory: list):
    """
    [PLACEHOLDER] Envanterdeki silahların ikonlarını gösterir.
    Aktif silah parlak, diğerleri soluk görünür.
    1/2 tuş ipuçları her ikonun altında yer alır.
    """
    w = surface.get_width()
    h = surface.get_height()
    ICON_SIZE    = 36
    ICON_GAP     = 8
    PANEL_H      = ICON_SIZE + 30
    PANEL_W      = len(inventory) * (ICON_SIZE + ICON_GAP) + ICON_GAP
    PANEL_X      = w - PANEL_W - 24
    PANEL_Y      = h - 24 - 120 - PANEL_H   # HUD'un hemen üstüne

    weapon_colors = {
        "revolver": (200, 160, 60),
        "smg":      (0,   200, 255),
        "shotgun":  (220, 120,  30),
    }
    key_labels = {0: "1", 1: "2", 2: "3"}
    font       = pygame.font.Font(None, 22)

    for idx, wtype in enumerate(inventory):
        ix = PANEL_X + ICON_GAP + idx * (ICON_SIZE + ICON_GAP)
        iy = PANEL_Y + 8
        color  = weapon_colors.get(wtype, (200, 200, 200))
        active = (wtype == active_weapon)

        # İkon arka planı
        icon_surf = pygame.Surface((ICON_SIZE, ICON_SIZE), pygame.SRCALPHA)
        alpha = 220 if active else 100
        icon_surf.fill((*color, alpha // 4))
        surface.blit(icon_surf, (ix, iy))

        # Çerçeve
        border_w = 3 if active else 1
        pygame.draw.rect(surface, color, pygame.Rect(ix, iy, ICON_SIZE, ICON_SIZE), border_w)

        # Kısa isim etiketi
        lbl = font.render(wtype[:3].upper(), True, color if active else (120, 120, 120))
        surface.blit(lbl, (ix + ICON_SIZE // 2 - lbl.get_width() // 2,
                           iy  + ICON_SIZE // 2 - lbl.get_height() // 2))

        # Tuş ipucu
        if idx in key_labels:
            key_lbl = font.render(key_labels[idx], True, (180, 180, 180))
            surface.blit(key_lbl, (ix + ICON_SIZE // 2 - key_lbl.get_width() // 2,
                                   iy + ICON_SIZE + 2))


def draw_revolver_hud(surface, bullets: int, gun_cooldown: float, is_reloading: bool,
                      spare_mags: int = 0):
    """
    Ekranın sağ alt köşesine altıpatar mermi hazne göstergesi çizer.

    Parametreler:
        surface      : Çizilecek yüzey (game_canvas).
        bullets      : Kalan mermi sayısı (0..REVOLVER_MAX_BULLETS).
        gun_cooldown : Kalan bekleme süresi (>0 = yeni atıldı).
        is_reloading : True ise şarjör dolduruluyor.

    Çizim düzeni (placeholder):
        - Arka panel: koyu, yarı saydam kutu
        - 6 mermi yuvası: dolu=sarı daire, boş=gri halka
        - Dönme animasyonu: atış sonrası hazne birkaç frame döner
        - "DOLDURULUYOR..." metni şarjör değişiminde görünür

    [TODO - UI ART]:
        revolver_cylinder.png, bullet.png, casing.png sprite'larıyla değiştir.
    """
    w = surface.get_width()

    # ── Panel boyutu ve konumu (sağ alt köşe) ──────────────────────────
    PANEL_W, PANEL_H = 220, 130
    PANEL_X = w - PANEL_W - 24
    PANEL_Y = surface.get_height() - PANEL_H - 24
    panel_rect = pygame.Rect(PANEL_X, PANEL_Y, PANEL_W, PANEL_H)

    # ── Arka panel ──────────────────────────────────────────────────────
    panel_surf = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
    panel_surf.fill((0, 0, 0, 200))
    surface.blit(panel_surf, panel_rect.topleft)
    border_col = (200, 160, 40) if not is_reloading else (255, 200, 60)
    pygame.draw.rect(surface, border_col, panel_rect, 2)

    # ── Başlık metni ─────────────────────────────────────────────────────
    title_font = pygame.font.Font(None, 20)
    title_surf = title_font.render("ALTIPATAR", True, border_col)
    surface.blit(title_surf, (PANEL_X + 8, PANEL_Y + 6))

    # ── Hazne dönüş açısı (atış sonrası 60° döner) ──────────────────────
    if is_reloading:
        # Dolum sırasında tam dönüş
        rotation_angle = (1.0 - (gun_cooldown / max(REVOLVER_RELOAD_TIME, 0.001))) * 360.0
    elif gun_cooldown > 0:
        # Normal atış sonrası bir yuva kadar döner (60°)
        rotation_angle = (1.0 - (gun_cooldown / max(REVOLVER_COOLDOWN, 0.001))) * 60.0
    else:
        rotation_angle = 0.0

    # ── Hazne merkezi ve yarıçapı ────────────────────────────────────────
    CX = PANEL_X + PANEL_W // 2
    CY = PANEL_Y + PANEL_H // 2 + 8
    RADIUS = 38
    SLOT_R = 9   # Her yuvanın yarıçapı

    # Hazne arka çemberi (silindir görünümü)
    pygame.draw.circle(surface, (40, 30, 10), (CX, CY), RADIUS + 6)
    pygame.draw.circle(surface, border_col,  (CX, CY), RADIUS + 6, 2)

    # ── 6 mermi yuvasını çiz ─────────────────────────────────────────────
    for i in range(REVOLVER_MAX_BULLETS):
        base_angle_deg = i * 60.0 + rotation_angle
        base_angle_rad = math.radians(base_angle_deg)

        sx = int(CX + math.cos(base_angle_rad) * RADIUS)
        sy = int(CY + math.sin(base_angle_rad) * RADIUS)

        if i < bullets:
            # Dolu mermi — parlak sarı daire
            pygame.draw.circle(surface, (80, 60, 0),   (sx, sy), SLOT_R)
            pygame.draw.circle(surface, (255, 210, 30), (sx, sy), SLOT_R - 2)
            # Parıltı noktası
            pygame.draw.circle(surface, (255, 255, 200), (sx - 2, sy - 2), 2)
        else:
            # Boş kovan — gri halka
            pygame.draw.circle(surface, (50, 40, 20),  (sx, sy), SLOT_R)
            pygame.draw.circle(surface, (120, 100, 50), (sx, sy), SLOT_R - 2)
            pygame.draw.circle(surface, (60, 50, 30),   (sx, sy), SLOT_R - 5)
            pygame.draw.circle(surface, (80, 70, 40),   (sx, sy), SLOT_R - 2, 1)

    # Orta delik (namlu girişi)
    pygame.draw.circle(surface, (10, 8, 4),    (CX, CY), 10)
    pygame.draw.circle(surface, border_col,    (CX, CY), 10, 1)

    # ── Mermi sayısı metni (sol alt) ────────────────────────────────────
    cnt_font = pygame.font.Font(None, 28)
    cnt_surf = cnt_font.render(f"{bullets}/{REVOLVER_MAX_BULLETS}", True, (240, 230, 180))
    surface.blit(cnt_surf, (PANEL_X + 8, PANEL_Y + PANEL_H - 28))

    # ── Yedek mermi satırı ───────────────────────────────────────────────
    spare_font = pygame.font.Font(None, 22)
    spare_col  = (200, 160, 40) if spare_mags > 0 else (120, 100, 60)
    spare_txt  = f"YEDEK: {spare_mags}" if spare_mags < 9990 else "YEDEK: ∞"
    spare_surf = spare_font.render(spare_txt, True, spare_col)
    surface.blit(spare_surf, (PANEL_X + 8, PANEL_Y + PANEL_H - 46))

    # ── Dolum veya bekleme çubuğu ────────────────────────────────────────
    BAR_X = PANEL_X + 8
    BAR_Y = PANEL_Y + PANEL_H - 42
    BAR_W = PANEL_W - 16
    BAR_H = 8

    if is_reloading:
        fill_pct = 1.0 - (gun_cooldown / max(REVOLVER_RELOAD_TIME, 0.001))
        bar_col  = (60, 200, 60)
        # "DOLDURULUYOR..." etiketi
        rl_font = pygame.font.Font(None, 22)
        rl_surf = rl_font.render("DOLDURULUYOR...", True, (100, 255, 100))
        surface.blit(rl_surf, (PANEL_X + PANEL_W // 2 - rl_surf.get_width() // 2,
                               PANEL_Y + 6))
        # Başlık metnini gizle (üstüne yazılır)
        pygame.draw.rect(surface, (0, 0, 0, 200),
                         pygame.Rect(PANEL_X + 6, PANEL_Y + 4, PANEL_W - 12, 18))
        surface.blit(rl_surf, (PANEL_X + PANEL_W // 2 - rl_surf.get_width() // 2,
                               PANEL_Y + 6))
    elif gun_cooldown > 0:
        fill_pct = 1.0 - (gun_cooldown / max(REVOLVER_COOLDOWN, 0.001))
        bar_col  = (200, 160, 40)
    else:
        fill_pct = 1.0
        bar_col  = (200, 160, 40)

    fill_pct = max(0.0, min(1.0, fill_pct))
    pygame.draw.rect(surface, (30, 25, 10), (BAR_X, BAR_Y, BAR_W, BAR_H))
    pygame.draw.rect(surface, bar_col,      (BAR_X, BAR_Y, int(BAR_W * fill_pct), BAR_H))
    pygame.draw.rect(surface, border_col,   (BAR_X, BAR_Y, BAR_W, BAR_H), 1)


# --- ANA RENDER YÖNETİCİSİ ---

def render_inventory_screen(surface, data, mouse_pos=(0, 0)):
    """
    I tuşuyla açılan tam ekran envanter menüsü.

    Gösterilen bilgiler:
      ┌─────────────────────────────────────────────────────────┐
      │  ENVANTER                              [I] KAPAT        │
      ├──────────────┬──────────────────────────────────────────┤
      │  SİLAHLAR   │  OYUNCU İSTATİSTİKLERİ                   │
      │  [REV] [SMG] │  Karma / Skor / HP / Stamina             │
      │  Mermi: 6/4  │                                          │
      ├──────────────┴──────────────────────────────────────────┤
      │  EKİPMAN SLOTLARI  (Genişletilebilir)                  │
      └─────────────────────────────────────────────────────────┘

    Returns: {} (bu ekranda tıklanabilir eleman yok şu an)
    """
    w, h = surface.get_width(), surface.get_height()

    # ── Renkler ─────────────────────────────────────────────────────────────
    _BG          = (6,   8,  14, 245)
    _BORDER      = (0,  160, 200)
    _ACCENT      = (0,  220, 255)
    _DIM         = (80, 100, 110)
    _GOLD        = (255, 200,  50)
    _RED         = (255,  60,  60)
    _GREEN       = (60,  220, 100)
    _WHITE       = (220, 220, 220)
    _PANEL_BG    = (0,   0,   0, 180)
    _SLOT_EMPTY  = (20,  25,  30)
    _SLOT_BORDER = (50,  70,  80)
    _REV_COL     = (220, 170,  40)
    _SMG_COL     = (0,   200, 255)

    # ── Tam ekran koyu overlay ───────────────────────────────────────────────
    bg_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    bg_surf.fill(_BG)
    surface.blit(bg_surf, (0, 0))

    # Üst başlık çizgisi
    pygame.draw.line(surface, _BORDER, (40, 70), (w - 40, 70), 2)
    pygame.draw.line(surface, _BORDER, (40, h - 40), (w - 40, h - 40), 2)

    title_font  = pygame.font.Font(None, 62)
    small_font  = pygame.font.Font(None, 28)
    med_font    = pygame.font.Font(None, 36)
    label_font  = pygame.font.Font(None, 22)

    # Başlık
    draw_text_with_shadow(surface, "ENVANTER", title_font, (w // 2, 42), _ACCENT, align='center')
    draw_text_with_shadow(surface, "[I] KAPAT", label_font, (w - 60, 42), _DIM, align='center')

    # ════════════════════════════════════════════════════
    # SOL PANEL — SİLAHLAR
    # ════════════════════════════════════════════════════
    LEFT_X    = 60
    LEFT_W    = 480
    LEFT_TOP  = 90
    LEFT_BOT  = h - 60

    left_panel = pygame.Rect(LEFT_X, LEFT_TOP, LEFT_W, LEFT_BOT - LEFT_TOP)
    panel_surf = pygame.Surface((LEFT_W, LEFT_BOT - LEFT_TOP), pygame.SRCALPHA)
    panel_surf.fill(_PANEL_BG)
    surface.blit(panel_surf, left_panel.topleft)
    pygame.draw.rect(surface, _BORDER, left_panel, 1)

    draw_text_with_shadow(surface, "─── SİLAHLAR ───",
                          label_font, (LEFT_X + LEFT_W // 2, LEFT_TOP + 18), _ACCENT, align='center')

    # Veri
    inventory_weapons = data.get('inventory_weapons', [])
    active_weapon     = data.get('active_weapon', None)
    player_bullets    = data.get('player_bullets', 0)
    spare_mags        = data.get('spare_mags', 0)
    mag_size          = data.get('mag_size', 6)

    WEAPON_META = {
        "revolver": {
            "label":   "ALTIPATAR",
            "desc":    "Tek atış, yüksek hasar.",
            "damage":  "50 hasar",
            "rate":    "Yarı-otomatik",
            "color":   _REV_COL,
            "icon_fn": _draw_revolver_icon,
        },
        "smg": {
            "label":   "HAFİF MAKİNALI",
            "desc":    "Hızlı, düşük hasar, sekme birikir.",
            "damage":  "18 hasar",
            "rate":    "Tam otomatik",
            "color":   _SMG_COL,
            "icon_fn": _draw_smg_icon,
        },

        "shotgun": {
            "label":   "POMPALI TÜFEK",
            "desc":    "Yakın mesafe terörü, geniş saçılım.",
            "damage":  "18x8 hasar",
            "rate":    "Pompalı",
            "color":   (220, 120, 30), # Turuncu-kahve
            "icon_fn": lambda surf, rect, col: draw_shotgun_hud(surf, rect, col),
        },
    }

    SLOT_H    = 130
    SLOT_W    = LEFT_W - 20
    cursor_y  = LEFT_TOP + 38

    if not inventory_weapons:
        no_wep = small_font.render("[ Henüz silah yok — sandık bul ]", True, _DIM)
        surface.blit(no_wep, (LEFT_X + 20, cursor_y + 20))
    else:
        for wtype in inventory_weapons:
            meta    = WEAPON_META.get(wtype, {"label": wtype.upper(), "desc": "", "damage": "?",
                                              "rate": "?", "color": _WHITE, "icon_fn": None})
            is_act  = (wtype == active_weapon)
            slot_r  = pygame.Rect(LEFT_X + 10, cursor_y, SLOT_W, SLOT_H)

            # Slot arka plan
            slot_s = pygame.Surface((SLOT_W, SLOT_H), pygame.SRCALPHA)
            if is_act:
                slot_s.fill((*meta["color"][:3], 30))
            else:
                slot_s.fill((15, 18, 22, 200))
            surface.blit(slot_s, slot_r.topleft)
            border_col = meta["color"] if is_act else _SLOT_BORDER
            border_w   = 2 if is_act else 1
            pygame.draw.rect(surface, border_col, slot_r, border_w)

            # İkon alanı
            ICON_BOX = 90
            icon_x = slot_r.x + 12
            icon_y = slot_r.y + (SLOT_H - ICON_BOX) // 2
            icon_r = pygame.Rect(icon_x, icon_y, ICON_BOX, ICON_BOX)
            pygame.draw.rect(surface, (10, 12, 16), icon_r)
            pygame.draw.rect(surface, meta["color"], icon_r, 1)
            if meta.get("icon_fn"):
                meta["icon_fn"](surface, icon_r, meta["color"])

            # Silah adı
            txt_x = slot_r.x + ICON_BOX + 22
            draw_text_with_shadow(surface, meta["label"], med_font,
                                  (txt_x, slot_r.y + 14), meta["color"], align='topleft')
            # Açıklama
            desc_s = label_font.render(meta["desc"], True, _DIM)
            surface.blit(desc_s, (txt_x, slot_r.y + 46))
            # Hasar / ateş hızı
            dmg_s  = label_font.render(f"Hasar: {meta['damage']}  |  {meta['rate']}", True, _WHITE)
            surface.blit(dmg_s, (txt_x, slot_r.y + 66))

            # Cephane bilgisi (sadece aktif silah için)
            if is_act:
                ammo_text = f"Şarjör: {player_bullets} / {mag_size}   Yedek: {spare_mags} mag"
                ammo_col  = _GREEN if player_bullets > 0 else _RED
                ammo_s    = small_font.render(ammo_text, True, ammo_col)
                surface.blit(ammo_s, (txt_x, slot_r.y + 90))

                # Mermi doluluk çubuğu
                BAR_W = SLOT_W - ICON_BOX - 34
                BAR_H = 6
                bar_x = txt_x
                bar_y = slot_r.y + SLOT_H - 16
                fill  = int(BAR_W * (player_bullets / max(mag_size, 1)))
                pygame.draw.rect(surface, (20, 25, 30), (bar_x, bar_y, BAR_W, BAR_H))
                pygame.draw.rect(surface, ammo_col,     (bar_x, bar_y, fill,  BAR_H))
                pygame.draw.rect(surface, meta["color"], (bar_x, bar_y, BAR_W, BAR_H), 1)

                # "AKTİF" rozeti
                badge_s = label_font.render("● AKTİF", True, _GREEN)
                surface.blit(badge_s, (slot_r.right - badge_s.get_width() - 10, slot_r.y + 8))

                # Tuş ipucu
                key_hint = label_font.render("1 / 2 ile değiştir   R ile doldur", True, _DIM)
                surface.blit(key_hint, (slot_r.x + 10, slot_r.bottom - 18))
            else:
                # Pasif slot tuş ipucu
                slot_idx = inventory_weapons.index(wtype)
                key_s = label_font.render(f"[{slot_idx + 1}] kuşan", True, _DIM)
                surface.blit(key_s, (slot_r.right - key_s.get_width() - 10, slot_r.y + 8))

            cursor_y += SLOT_H + 10

    # ════════════════════════════════════════════════════
    # SAĞ ÜST PANEL — OYUNCU İSTATİSTİKLERİ
    # ════════════════════════════════════════════════════
    RIGHT_X   = LEFT_X + LEFT_W + 30
    RIGHT_W   = w - RIGHT_X - 40
    STAT_H    = (h - 100) // 2 - 10
    stat_rect = pygame.Rect(RIGHT_X, LEFT_TOP, RIGHT_W, STAT_H)

    stat_s = pygame.Surface((RIGHT_W, STAT_H), pygame.SRCALPHA)
    stat_s.fill(_PANEL_BG)
    surface.blit(stat_s, stat_rect.topleft)
    pygame.draw.rect(surface, _BORDER, stat_rect, 1)

    draw_text_with_shadow(surface, "─── OYUNCU ───",
                          label_font, (RIGHT_X + RIGHT_W // 2, LEFT_TOP + 18), _ACCENT, align='center')

    karma      = data.get('karma', 0)
    score      = data.get('score', 0)
    hp         = data.get('player_hp', 0)
    hp_max     = data.get('player_hp_max', 100)
    stamina    = data.get('stamina', 0)
    stam_max   = data.get('stamina_max', 100)
    kills      = data.get('kills', 0)
    level_idx  = data.get('level_idx', 1)

    # Karma rengi
    karma_col = _GREEN if karma > 0 else (_RED if karma < 0 else _DIM)
    karma_sign = "+" if karma > 0 else ""

    stats = [
        ("BÖLÜM",     f"{level_idx}",             _WHITE),
        ("SKOR",      f"{int(score):,}",           _GOLD),
        ("KARMA",     f"{karma_sign}{karma}",      karma_col),
        ("CAN",       f"{hp} / {hp_max}",          _GREEN if hp > hp_max * 0.5 else _RED),
        ("STAMINA",   f"{int(stamina)} / {stam_max}", _ACCENT),
        ("ÖLDÜRÜLEN", f"{kills}",                  _DIM),
    ]

    sy = LEFT_TOP + 38
    for label, value, col in stats:
        lbl_s = label_font.render(label, True, _DIM)
        val_s = small_font.render(value, True, col)
        surface.blit(lbl_s, (RIGHT_X + 16, sy))
        surface.blit(val_s, (RIGHT_X + RIGHT_W - val_s.get_width() - 16, sy))
        # Ayırıcı çizgi
        pygame.draw.line(surface, (20, 25, 35),
                         (RIGHT_X + 16, sy + 26), (RIGHT_X + RIGHT_W - 16, sy + 26), 1)
        sy += 34

    # Karma çubuğu (-1000 .. +1000)
    karma_norm = (karma + 1000) / 2000
    BAR_W_K = RIGHT_W - 32
    bar_karma_x = RIGHT_X + 16
    bar_karma_y = sy + 6
    pygame.draw.rect(surface, (20, 25, 30), (bar_karma_x, bar_karma_y, BAR_W_K, 8))
    fill_k = int(BAR_W_K * max(0.0, min(1.0, karma_norm)))
    k_fill_col = _GREEN if karma >= 0 else _RED
    pygame.draw.rect(surface, k_fill_col, (bar_karma_x, bar_karma_y, fill_k, 8))
    pygame.draw.rect(surface, _BORDER, (bar_karma_x, bar_karma_y, BAR_W_K, 8), 1)
    # Orta nokta işareti
    mid_x = bar_karma_x + BAR_W_K // 2
    pygame.draw.line(surface, _WHITE, (mid_x, bar_karma_y - 2), (mid_x, bar_karma_y + 10), 1)

    karma_lbl = label_font.render("KARMA (-1000 ↔ +1000)", True, _DIM)
    surface.blit(karma_lbl, (RIGHT_X + RIGHT_W // 2 - karma_lbl.get_width() // 2,
                              bar_karma_y + 12))

    # ════════════════════════════════════════════════════
    # SAĞ ALT PANEL — EKİPMAN SLOTLARI
    # ════════════════════════════════════════════════════
    equip_rect = pygame.Rect(RIGHT_X, LEFT_TOP + STAT_H + 20,
                              RIGHT_W, h - (LEFT_TOP + STAT_H + 20) - 60)
    equip_s = pygame.Surface((equip_rect.width, equip_rect.height), pygame.SRCALPHA)
    equip_s.fill(_PANEL_BG)
    surface.blit(equip_s, equip_rect.topleft)
    pygame.draw.rect(surface, _BORDER, equip_rect, 1)

    draw_text_with_shadow(surface, "─── EKİPMAN SLOTLARI ───",
                          label_font, (equip_rect.centerx, equip_rect.y + 18),
                          _ACCENT, align='center')

    EQUIP_SLOTS = [
        ("BAŞLIK",   "helmet",   "🪖 Baş zırhı"),
        ("GÖVDE",    "chest",    "🧥 Göğüs zırhı"),
        ("TALİSMAN", "talisman", "🔮 Pasif güç"),
        ("İMPLANT",  "implant",  "⚡ Sibernetik"),
    ]
    has_talisman = data.get('has_talisman', False)

    ES_W = (equip_rect.width - 30) // 2
    ES_H = 52
    es_gap = 8
    col_x  = [equip_rect.x + 10, equip_rect.x + 10 + ES_W + 10]
    row_y  = equip_rect.y + 38

    for i, (slot_name, slot_key, slot_desc) in enumerate(EQUIP_SLOTS):
        ex = col_x[i % 2]
        ey = row_y + (i // 2) * (ES_H + es_gap)
        er = pygame.Rect(ex, ey, ES_W, ES_H)

        # Talisman dolu mu kontrol
        filled = (slot_key == "talisman" and has_talisman)

        slot_fill = pygame.Surface((ES_W, ES_H), pygame.SRCALPHA)
        if filled:
            slot_fill.fill((30, 20, 50, 200))
        else:
            slot_fill.fill(_SLOT_EMPTY + (200,))
        surface.blit(slot_fill, er.topleft)
        slot_border = _GOLD if filled else _SLOT_BORDER
        pygame.draw.rect(surface, slot_border, er, 1)

        name_s = label_font.render(slot_name, True, slot_border)
        surface.blit(name_s, (er.x + 8, er.y + 8))
        if filled:
            val_s = label_font.render("Talisman ✓", True, _GOLD)
        else:
            val_s = label_font.render("[ Boş ]", True, _DIM)
        surface.blit(val_s, (er.x + 8, er.y + 28))

    # Alt bilgi notu
    note_s = label_font.render("Ekipman slotları ileriki bölümlerde genişler.", True, _DIM)
    surface.blit(note_s, (equip_rect.x + 10, equip_rect.bottom - 22))

    return {}


# ─── Envanter ikon yardımcıları ──────────────────────────────────────────────

def _draw_revolver_icon(surface, rect, color):
    """Küçük altıpatar ikonu (placeholder geometri)."""
    cx, cy = rect.centerx, rect.centery
    # Namlu
    pygame.draw.line(surface, color, (cx - 28, cy), (cx + 28, cy), 4)
    # Tetikhane
    pygame.draw.circle(surface, color, (cx - 4, cy), 14, 2)
    # Kabza
    pygame.draw.line(surface, color, (cx - 14, cy + 2), (cx - 14, cy + 20), 4)
    # Tetik
    pygame.draw.line(surface, color, (cx - 4, cy + 6), (cx + 4, cy + 16), 2)


def _draw_smg_icon(surface, rect, color):
    """Küçük SMG ikonu (placeholder geometri)."""
    cx, cy = rect.centerx, rect.centery
    # Gövde
    pygame.draw.rect(surface, color, pygame.Rect(cx - 26, cy - 6, 38, 12), 2)
    # Namlu
    pygame.draw.rect(surface, color, pygame.Rect(cx + 12, cy - 3, 18, 6), 2)
    # Şarjör
    pygame.draw.rect(surface, color, pygame.Rect(cx - 8, cy + 6, 10, 14), 2)
    # Dipçik
    pygame.draw.rect(surface, color, pygame.Rect(cx - 34, cy - 4, 10, 10), 2)


def render_ui(surface, state, data, mouse_pos=(0, 0)):
    """Ana render yöneticisi — tüm state'leri karşılar."""
    time_ms = data.get('time_ms', pygame.time.get_ticks())
    w, h = surface.get_width(), surface.get_height()
    interactive_elements = {}

    if state == 'MENU':
        interactive_elements = render_main_menu(surface, mouse_pos, None)

    elif state == 'LEVEL_SELECT':
        page_index = data.get('level_select_page', 0)
        interactive_elements = render_level_select(surface, mouse_pos, data.get('save_data'), page_index)

    elif state == 'SETTINGS':
        interactive_elements = render_settings_menu(surface, mouse_pos, data['settings'])

    elif state == 'TERMINAL':
        interactive_elements = render_cheat_terminal(
            surface, data.get('term_input', ''), data.get('term_status', ''),
            debug_mode=data.get('is_debug_arena', False))

    elif state == 'LOADING':
        interactive_elements = render_loading_screen(surface, data['progress'])

    elif state in ('CUTSCENE', 'CHAT'):
        if data['story_manager'].is_cutscene:
            render_cutscene(surface, data['story_manager'])
        else:
            render_chat_interface(surface, data['story_manager'])

    elif state == 'PAUSED':
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill(PAUSE_OVERLAY_COLOR)
        surface.blit(overlay, (0, 0))

        panel_rect = pygame.Rect(w // 2 - 260, h // 2 - 130, 520, 260)
        draw_cyber_panel(surface, panel_rect, (0, 160, 240), "SİSTEM ASKIYA ALINDI")

        draw_glitch_text(surface, "DURAKLATILDI", 96, w // 2, h // 2 - 30, WHITE)
        msg_font = pygame.font.Font(None, 32)
        draw_text_with_shadow(surface, "'P' İLE DEVAM ET", msg_font,
                              (w // 2, h // 2 + 60), (160, 160, 160), align='center')

    elif state == 'INVENTORY':
        interactive_elements = render_inventory_screen(surface, data, mouse_pos)

    elif state == 'LEVEL_COMPLETE':
        interactive_elements = render_level_complete(
            surface, mouse_pos, data['level_data'], data['score'])

    elif state == 'GAME_OVER':
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((25, 0, 0, 230))
        surface.blit(overlay, (0, 0))

        draw_glitch_text(surface, "BAĞLANTI KOPTU", 85, w // 2, h // 2 - 130, (220, 50, 50))

        panel_rect = pygame.Rect(w // 2 - 240, h // 2 - 40, 480, 150)
        draw_cyber_panel(surface, panel_rect, (220, 50, 50), "HATA RAPORU")

        score_font = pygame.font.Font(None, 52)
        draw_text_with_shadow(surface, f"SKOR: {int(data['score'])}", score_font,
                              (w // 2, h // 2 + 10), WHITE, align='center')
        goal_font = pygame.font.Font(None, 34)
        draw_text_with_shadow(surface, f"HEDEF: {data['level_data']['goal_score']}", goal_font,
                              (w // 2, h // 2 + 65), (240, 200, 0), align='center')
        if time_ms % 1000 < 500:
            retry_font = pygame.font.Font(None, 42)
            draw_text_with_shadow(surface, "TEKRAR DENEMEK İÇİN 'R'", retry_font,
                                  (w // 2, h // 2 + 175), WHITE, align='center')

    elif state == 'PLAYING':
        current_theme = data.get('theme') or THEMES[0]
        border_col    = current_theme["border_color"]

        # ── Sol Panel: HP + Stamina ───────────────────────────────────────
        # Panel yüksekliği iki bar + etiket + marj = 140px
        left_panel = pygame.Rect(30, 30, 260, 140)
        draw_cyber_panel(surface, left_panel, border_col, f"BÖLÜM {data['level_idx']}")

        BAR_X   = 50          # Sol kenar
        BAR_W   = 220         # Bar genişliği
        LABEL_F = pygame.font.Font(None, 18)

        # ── HP Barı (y=55) ────────────────────────────────────────────────
        hp_cur = data.get('player_hp',     100)
        hp_max = data.get('player_hp_max', 100) or 1
        hp_pct = max(0.0, min(1.0, hp_cur / hp_max))

        HP_Y, HP_H = 55, 16
        hp_fill_col = (220, 30, 30) if hp_pct > 0.3 else (255, 80, 0) if hp_pct > 0.15 else (255, 0, 0)

        pygame.draw.rect(surface, (50, 0, 0),       (BAR_X, HP_Y, BAR_W, HP_H))
        pygame.draw.rect(surface, hp_fill_col,       (BAR_X, HP_Y, int(BAR_W * hp_pct), HP_H))
        pygame.draw.rect(surface, (180, 180, 180),   (BAR_X, HP_Y, BAR_W, HP_H), 1)

        lbl_hp = LABEL_F.render(f"HP  {max(0, int(hp_cur))} / {hp_max}", True, (230, 230, 230))
        surface.blit(lbl_hp, (BAR_X + BAR_W // 2 - lbl_hp.get_width() // 2, HP_Y + 1))

        # ── Stamina Barı (y=90) ───────────────────────────────────────────
        st_cur = data.get('stamina',     100)
        st_max = data.get('stamina_max', 100) or 1
        st_pct = max(0.0, min(1.0, st_cur / st_max))

        ST_Y, ST_H = 95, 14
        if st_pct > 0.60:
            st_fill_col = (0, 210, 255)     # Dolu  → cyan
        elif st_pct > 0.25:
            st_fill_col = (220, 200, 0)     # Yarı  → sarı
        else:
            st_fill_col = (255, 60, 60)     # Boş   → kırmızı

        pygame.draw.rect(surface, (10, 20, 35),     (BAR_X, ST_Y, BAR_W, ST_H))
        pygame.draw.rect(surface, st_fill_col,       (BAR_X, ST_Y, int(BAR_W * st_pct), ST_H))
        pygame.draw.rect(surface, (80, 160, 200),    (BAR_X, ST_Y, BAR_W, ST_H), 1)

        lbl_st = LABEL_F.render(f"STAMINA  {int(st_cur)}/{st_max}", True, (160, 220, 255))
        surface.blit(lbl_st, (BAR_X + BAR_W // 2 - lbl_st.get_width() // 2, ST_Y + 1))

        # ── Karma + Ölüm sayacı (panel sağına, ayrı küçük kutu) ──────────
        karma = data.get('karma', 0)
        kills = data.get('kills', 0)
        karma_color = (0, 220, 80) if karma > 20 else ((220, 50, 50) if karma < -20 else WHITE)
        karma_font  = pygame.font.Font(None, 24)
        draw_text_with_shadow(surface, f"KARMA: {karma}", karma_font, (310, 55), karma_color)
        draw_text_with_shadow(surface, f"ÖLÜM: {kills}",  karma_font, (310, 82), (200, 50, 50))

        # Skor paneli (sağ üst)
        goal = data['level_data'].get('goal_score', 0)
        current_score = data['score']
        progress = min(1.0, current_score / goal) if goal > 0 else 0.0
        score_text = f"{int(current_score)} / {goal}" if goal > 0 else f"SKOR: {int(current_score)}"

        score_rect = pygame.Rect(w - 340, 35, 305, 75)
        draw_cyber_panel(surface, score_rect, WHITE, "VERİ YÜKLEMESİ")

        pygame.draw.rect(surface, (35, 35, 35), (w - 320, 83, 265, 18))
        if goal > 0:
            pygame.draw.rect(surface, NEON_GREEN, (w - 320, 83, int(265 * progress), 18))

        score_font = pygame.font.Font(None, 28)
        draw_text_with_shadow(surface, score_text, score_font, (w - 188, 92), WHITE, align='center')

        # ── Silah HUD — Ammo Counter + Weapon Switch UI ───────────────────
        # ui_data'dan gelen silah bilgilerini çiz.
        # Anahtarlar: 'active_weapon', 'player_bullets', 'gun_cooldown',
        #             'is_reloading', 'inventory_weapons'
        _rev_bullets    = data.get('player_bullets', 0)
        _active_weapon  = data.get('active_weapon', None)   # None → silah yok
        _inventory      = data.get('inventory_weapons', [])

        # Gatekeeper: Aktif silah nesnesi yoksa HUD tamamen gizlenir.
        # Eski kontrol (mermi >= 0) sifiri silahsiz durumla ayirt edemiyordu.
        if _active_weapon is not None:
            draw_weapon_hud(
                surface,
                active_weapon   = _active_weapon,
                bullets         = _rev_bullets,
                mag_size        = data.get('mag_size', 6),
                spare_mags      = data.get('spare_mags', 0),
                gun_cooldown    = data.get('gun_cooldown', 0.0),
                is_reloading    = data.get('is_reloading', False),
                inventory       = _inventory,
            )

        # ── Sandık etkileşim ipucu ────────────────────────────────────────
        # main.py'den 'chest_prompt' True gönderilirse gösterilir.
        if data.get('chest_prompt'):
            _cpfont = pygame.font.Font(None, 32)
            _cp_txt = _cpfont.render("E: SİLAHI AL", True, (255, 255, 100))
            cx_ = w // 2 - _cp_txt.get_width() // 2
            cy_ = h - 200
            _cp_bg = pygame.Surface((_cp_txt.get_width() + 20, _cp_txt.get_height() + 8), pygame.SRCALPHA)
            _cp_bg.fill((0, 0, 0, 180))
            surface.blit(_cp_bg, (cx_ - 10, cy_ - 4))
            surface.blit(_cp_txt, (cx_, cy_))

    return interactive_elements