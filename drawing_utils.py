import pygame
import math
from utils import wrap_text, draw_text_with_shadow

# ═══════════════════════════════════════════════════════════════════════════
# PLACEHOLDER — Pixel artist ekibi bu fonksiyonların içini dolduracak.
# Şu an sadece renkli çerçeveli etiket kutular çiziliyor.
# ═══════════════════════════════════════════════════════════════════════════

# --- RENK TANIMLAMALARI (çerçeve renkleri) ---
_GOLD      = (255, 215, 0)
_HOLY_BLUE = (100, 200, 255)
_PURP      = (180, 60, 255)
_BLOOD     = (200, 0, 30)
_WHITE     = (240, 240, 240)
_DARK      = (15, 15, 20)


def _draw_placeholder_box(surface, cx, cy, w, h, border_color, label, intensity=1.0):
    """
    Genel amaçlı placeholder kutu çizici.
    cx, cy: merkez koordinatları
    w, h  : genişlik ve yükseklik
    """
    alpha = int(255 * min(1.0, intensity))
    x = cx - w // 2
    y = cy - h // 2

    # İç dolgu — çok koyu, dikkat dağıtmaz
    box_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    box_surf.fill((*_DARK, 180))
    surface.blit(box_surf, (x, y))

    # Renkli dış çerçeve (2px)
    pygame.draw.rect(surface, border_color, (x, y, w, h), 2)

    # Köşe işaretleri — placeholder olduğunu belli eder
    corner = 8
    c = border_color
    for cx2, cy2, dx, dy in [
        (x, y, 1, 1), (x + w, y, -1, 1),
        (x, y + h, 1, -1), (x + w, y + h, -1, -1)
    ]:
        pygame.draw.line(surface, c, (cx2, cy2), (cx2 + dx * corner, cy2), 2)
        pygame.draw.line(surface, c, (cx2, cy2), (cx2, cy2 + dy * corner), 2)

    # Etiket metni
    font = pygame.font.Font(None, 20)
    lbl = font.render(label, True, border_color)
    lbl_rect = lbl.get_rect(center=(cx, cy))
    surface.blit(lbl, lbl_rect)


# ═══════════════════════════════════════════════════════════════════════════
# SAVAŞÇI SİLÜETİ — Placeholder
# ═══════════════════════════════════════════════════════════════════════════
def draw_warrior_silhouette(surface, x, y, sz=60, intensity=1.0):
    """
    [PLACEHOLDER] Savaşçı/kahraman figürü.
    Pixel artist: bu fonksiyonu ile sprite/animasyon koyun.
    """
    w = int(sz * 1.4)
    h = int(sz * 3.2)
    _draw_placeholder_box(surface, x, y, w, h, _GOLD, "WARRIOR", intensity)


# ═══════════════════════════════════════════════════════════════════════════
# VASİ SİLÜETİ — Placeholder
# ═══════════════════════════════════════════════════════════════════════════
def draw_vasi_silhouette(surface, x, y, sz=60, intensity=1.0, scanning=False, scan_angle=0):
    """
    [PLACEHOLDER] Vasi / yönetici figürü.
    Pixel artist: bu fonksiyona sprite/animasyon koyun.
    scanning=True olduğunda tarama hattı eklenir (ince çizgi yeter şimdilik).
    """
    w = int(sz * 1.4)
    h = int(sz * 3.2)
    _draw_placeholder_box(surface, x, y, w, h, _PURP, "VASİ", intensity)

    # Tarama göstergesi — minimal
    if scanning:
        end_x = int(x + math.cos(scan_angle) * w * 0.6)
        end_y = int(y + math.sin(scan_angle) * h * 0.4)
        pygame.draw.line(surface, (0, 220, 180), (x, y), (end_x, end_y), 1)


# ═══════════════════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR (mantık değişmedi, sadece görsel basitleşti)
# ═══════════════════════════════════════════════════════════════════════════
def rotate_point(point, angle, origin):
    """Bir noktayı orijin etrafında döndürür."""
    ox, oy = origin
    px, py = point
    qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
    qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
    return qx, qy


def draw_legendary_revolver(surface, x, y, angle, shoot_timer):
    """
    [PLACEHOLDER] Silah görseli.
    Şu an sadece küçük bir çizgi (namlu yönü) çiziliyor.
    """
    recoil_offset = 0
    recoil_angle = 0
    if shoot_timer < 0.15:
        recoil_value = (0.15 - shoot_timer) / 0.15
        recoil_angle = -0.3 * recoil_value
        recoil_offset = -6 * recoil_value

    final_angle = angle + recoil_angle
    pivot_x = x + math.cos(angle) * recoil_offset
    pivot_y = y + math.sin(angle) * recoil_offset

    # Namlu çizgisi
    tip_x = pivot_x + math.cos(final_angle) * 30
    tip_y = pivot_y + math.sin(final_angle) * 30
    pygame.draw.line(surface, (0, 255, 255), (int(pivot_x), int(pivot_y)), (int(tip_x), int(tip_y)), 3)
    pygame.draw.circle(surface, _GOLD, (int(pivot_x), int(pivot_y)), 4)

    return rotate_point((pivot_x + 30, pivot_y), final_angle, (pivot_x, pivot_y))


def draw_background_hero(surface, x, y, size=150):
    """[PLACEHOLDER] Arka plan kahraman silüeti."""
    sz = int(size * 0.45)
    draw_warrior_silhouette(surface, x, y, sz=sz, intensity=0.5)


def draw_background_boss_silhouette(surface, karma, width, height):
    """
    [PLACEHOLDER] Karma'ya göre arka plan boss silüeti.
    Karma < 0 → Savaşçı, karma >= 0 → Vasi
    """
    t = pygame.time.get_ticks() / 1000.0
    float_y = int(math.sin(t) * 12)
    cx = width // 2
    cy = height // 2 + float_y
    sz = 85

    if karma < 0:
        draw_warrior_silhouette(surface, cx, cy, sz=sz, intensity=0.4)
    else:
        draw_vasi_silhouette(surface, cx, cy, sz=sz, intensity=0.4)


# ═══════════════════════════════════════════════════════════════════════════
# SİNEMATİK OVERLAY — Değişmedi (UI, metin, diyalog sistemi)
# ═══════════════════════════════════════════════════════════════════════════
def draw_cinematic_overlay(surface, manager, time_ms, mouse_pos):
    """Oyun dünyasının üzerine çizilen sinematik katman"""
    w, h = surface.get_width(), surface.get_height()
    active_buttons = {}

    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    surface.blit(overlay, (0, 0))

    bar_height = 130
    pygame.draw.rect(surface, (0, 0, 0), (0, 0, w, bar_height))
    pygame.draw.rect(surface, (0, 0, 0), (0, h - bar_height, w, bar_height))

    line_color = (0, 255, 255)
    if manager.speaker == "SİSTEM" or manager.speaker == "MUHAFIZ" or "MAKİNE" in manager.speaker or "YARGIÇ" in manager.speaker:
        line_color = (255, 50, 50)
    elif manager.speaker == "VASI" or manager.speaker == "KURYE":
        line_color = (0, 255, 100)
    elif "OYUNCU" in manager.speaker or "İÇ SES" in manager.speaker:
        line_color = (255, 200, 50)

    pygame.draw.line(surface, line_color, (0, bar_height), (w, bar_height), 2)
    pygame.draw.line(surface, line_color, (0, h - bar_height), (w, h - bar_height), 2)

    if manager.speaker:
        font_title = pygame.font.Font(None, 55)
        icon_rect = pygame.Rect(50, bar_height // 2 - 20, 40, 40)
        pygame.draw.rect(surface, line_color, icon_rect, 2)
        pygame.draw.rect(surface, (*line_color, 100), icon_rect.inflate(-4, -4))
        draw_text_with_shadow(surface, manager.speaker, font_title, (110, bar_height // 2), line_color, align="midleft")

    font_text = pygame.font.Font(None, 36)
    text_area_rect = pygame.Rect(60, h - bar_height + 30, w - 120, bar_height - 60)

    if manager.is_cutscene:
        center_overlay = pygame.Surface((w, 200), pygame.SRCALPHA)
        center_overlay.fill((0, 0, 0, 180))
        surface.blit(center_overlay, (0, h // 2 - 100))

        lines = wrap_text(manager.display_text, font_text, w - 400)
        total_h = len(lines) * 45
        start_y = h // 2 - total_h // 2

        for i, line in enumerate(lines):
            col = (255, 255, 255)
            if "HATA" in line or "UYARI" in line or "DİKKAT" in line:
                col = (255, 50, 50)
            draw_text_with_shadow(surface, line, font_text, (w // 2, start_y + i * 45), col, align="center")
    else:
        lines = wrap_text(manager.display_text, font_text, text_area_rect.width)
        for i, line in enumerate(lines):
            draw_text_with_shadow(surface, line, font_text, (text_area_rect.x, text_area_rect.y + i * 35), (220, 220, 220), align="topleft")

    if manager.waiting_for_click and manager.state != "WAITING_CHOICE":
        blink = (time_ms // 500) % 2 == 0
        if blink:
            draw_text_with_shadow(surface, "DEVAM ETMEK İÇİN TIKLA >", pygame.font.Font(None, 24),
                                  (w - 50, h - 30), line_color, align="bottomright")

    if manager.state == "WAITING_CHOICE":
        btn_height = 80
        btn_width = 800
        start_y = h // 2 - (len(manager.current_choices) * 110) // 2 + 30

        draw_text_with_shadow(surface, "BİR SEÇİM YAP", pygame.font.Font(None, 60), (w // 2, start_y - 70), (255, 255, 0), align="center")

        for i, choice in enumerate(manager.current_choices):
            rect = pygame.Rect(w // 2 - btn_width // 2, start_y + i * 110, btn_width, btn_height)
            is_hover = rect.collidepoint(mouse_pos)

            s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            bg_col = (0, 40, 60, 230) if is_hover else (0, 20, 30, 200)
            s.fill(bg_col)
            surface.blit(s, rect.topleft)

            border_col = (0, 255, 255) if is_hover else (0, 100, 150)
            pygame.draw.rect(surface, border_col, rect, 3, border_radius=0)

            text_col = (255, 255, 255) if is_hover else (200, 200, 200)
            draw_text_with_shadow(surface, f"> {choice['text']}", font_text, rect.center, text_col, align="center")
            active_buttons[f'choice_{i}'] = rect

    return active_buttons


# ═══════════════════════════════════════════════════════════════════════════
# NPC SOHBET EKRANI — Değişmedi
# ═══════════════════════════════════════════════════════════════════════════
def draw_npc_chat(surface, current_npc, chat_history, chat_input, show_cursor, logical_width, logical_height):
    """NPC sohbet ekranını çiz"""
    if not current_npc:
        return

    overlay = pygame.Surface((logical_width, logical_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))

    chat_width = 800
    chat_height = 600
    chat_x = (logical_width - chat_width) // 2
    chat_y = (logical_height - chat_height) // 2

    pygame.draw.rect(surface, (20, 20, 30), (chat_x, chat_y, chat_width, chat_height), border_radius=15)
    pygame.draw.rect(surface, current_npc.color, (chat_x, chat_y, chat_width, chat_height), 3, border_radius=15)

    title_font = pygame.font.Font(None, 40)
    title = title_font.render(f"KONUŞUYOR: {current_npc.name}", True, current_npc.color)
    surface.blit(title, (chat_x + 20, chat_y + 20))

    type_font = pygame.font.Font(None, 24)
    status_text = "AI AKTİF" if current_npc.ai_active else "MANUEL MOD"
    status_color = (0, 255, 100) if current_npc.ai_active else (200, 200, 200)
    type_text = type_font.render(f"Kişilik: {current_npc.personality_type} | {status_text}", True, status_color)
    surface.blit(type_text, (chat_x + chat_width - 300, chat_y + 30))

    history_height = 400
    history_rect = pygame.Rect(chat_x + 20, chat_y + 80, chat_width - 40, history_height)
    pygame.draw.rect(surface, (10, 10, 15), history_rect, border_radius=10)

    font = pygame.font.Font(None, 28)
    y_offset = history_rect.y + 20

    for msg in chat_history[-8:]:
        if msg["speaker"] == "Oyuncu":
            text_color = (200, 255, 200)
            speaker = "Siz: "
        elif msg["speaker"] == "SİSTEM":
            text_color = (255, 100, 100)
            speaker = "SİSTEM: "
        else:
            text_color = current_npc.color
            speaker = f"{msg['speaker']}: "

        lines = wrap_text(msg["text"], font, history_rect.width - 40)
        for line in lines:
            text_surf = font.render(speaker + line, True, text_color)
            surface.blit(text_surf, (history_rect.x + 20, y_offset))
            y_offset += 35
        y_offset += 10

    input_y = chat_y + history_height + 100
    input_rect = pygame.Rect(chat_x + 20, input_y, chat_width - 40, 50)
    pygame.draw.rect(surface, (30, 30, 40), input_rect, border_radius=8)
    pygame.draw.rect(surface, (100, 100, 150), input_rect, 2, border_radius=8)

    input_font = pygame.font.Font(None, 32)
    display_text = chat_input
    if show_cursor:
        display_text += "|"
    input_text = input_font.render(display_text, True, (220, 220, 220))
    surface.blit(input_text, (input_rect.x + 15, input_rect.centery - 10))

    instruct_font = pygame.font.Font(None, 24)
    instruct1 = instruct_font.render("ENTER: Gönder | ESC: Çık | TAB: AI Modu Aç/Kapa", True, (150, 150, 150))

    if current_npc.ai_active:
        instruct2 = instruct_font.render("AI BAĞLANTISI KURULDU: Herhangi bir şey sorabilirsin!", True, (0, 255, 100))
    else:
        instruct2 = instruct_font.render("MANUEL MOD: Sadece ön tanımlı cevaplar.", True, (255, 200, 100))

    surface.blit(instruct1, (chat_x + 20, chat_y + chat_height - 40))
    surface.blit(instruct2, (chat_x + chat_width // 2 - instruct2.get_width() // 2, chat_y + chat_height - 70))

    # NPC avatar — [PLACEHOLDER] basit renkli çerçeve
    avatar_size = 60
    avatar_x = chat_x + chat_width - avatar_size - 30
    avatar_y = chat_y + 30
    pygame.draw.rect(surface, (30, 30, 40), (avatar_x, avatar_y, avatar_size, avatar_size))
    pygame.draw.rect(surface, current_npc.color, (avatar_x, avatar_y, avatar_size, avatar_size), 2)
    lbl_f = pygame.font.Font(None, 18)
    lbl_s = lbl_f.render("NPC", True, current_npc.color)
    surface.blit(lbl_s, (avatar_x + avatar_size // 2 - lbl_s.get_width() // 2,
                          avatar_y + avatar_size // 2 - lbl_s.get_height() // 2))