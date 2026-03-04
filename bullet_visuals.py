import pygame
import math

# ============================================================
#  bullet_visuals.py
#  PlayerProjectile için özel draw fonksiyonu.
#
#  Sorun: PlayerProjectile.draw() merminin hareket yönünü
#  bilmeden sabit bir şekil çiziyordu — doğu/batıya sıkınca
#  mermi dikey, kuzey/güneye sıkınca yatay görünüyordu.
#
#  Çözüm: rect merkezinden vx/vy alıp yönü hesapla,
#  mermiye o yönde uzayan kapsül/çizgi çiz.
#
#  API: draw_player_bullet(surface, proj, theme_color)
#  main.py'de:
#    _p.draw(game_canvas)  →  draw_player_bullet(game_canvas, _p, BULLET_COLOR)
# ============================================================

# Silah tipine göre renk tablosu (fallback: beyaz)
BULLET_COLORS = {
    'revolver':  (255, 220,  60),   # Altın sarısı
    'smg':       (100, 220, 255),   # Elektrik mavisi
    'shotgun':   (255, 140,  30),   # Turuncu
    'default':   (255, 255, 200),   # Krem beyaz
}


def _get_direction(proj):
    """
    Mermiнin hareket yönünü radyan cinsinden döndür.
    vx/vy yoksa rect'in son konumundan tahmin edilemez;
    o zaman sağa (0 rad) varsayılır.
    """
    vx = getattr(proj, 'vx', None)
    vy = getattr(proj, 'vy', None)
    if vx is None or vy is None:
        # Bazı implementasyonlar velocity'i farklı isimlendiriyor
        vx = getattr(proj, 'vel_x', getattr(proj, 'speed_x', None))
        vy = getattr(proj, 'vel_y', getattr(proj, 'speed_y', None))
    if vx is None or vy is None:
        angle = getattr(proj, 'angle', getattr(proj, 'direction', 0.0))
        return angle
    if abs(vx) < 0.001 and abs(vy) < 0.001:
        return getattr(proj, 'angle', 0.0)
    return math.atan2(vy, vx)


def draw_player_bullet(surface, proj, weapon_type='default'):
    """
    Merminin gerçek hareket yönüne hizalanmış kapsül çizer.
    weapon_type: 'revolver' | 'smg' | 'shotgun' | 'default'
    """
    cx = proj.rect.centerx
    cy = proj.rect.centery
    angle = _get_direction(proj)

    col_main  = BULLET_COLORS.get(weapon_type, BULLET_COLORS['default'])
    col_core  = (255, 255, 255)                # Parlak iç çekirdek
    col_trail = (col_main[0]//3, col_main[1]//3, col_main[2]//3)

    # Silah tipine göre görsel parametre
    if weapon_type == 'revolver':
        body_len = 14     # Uzun, yavaş — iri mermi
        body_w   = 5
        glow_r   = 7
    elif weapon_type == 'smg':
        body_len = 10     # Kısa hızlı saçma
        body_w   = 3
        glow_r   = 5
    elif weapon_type == 'shotgun':
        body_len = 7      # Kısa ve yuvarlak saçma
        body_w   = 4
        glow_r   = 6
    else:
        body_len = 10
        body_w   = 4
        glow_r   = 6

    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    # ── Kuyruk noktası (merminin arkası) ─────────────────────
    tail_x = cx - cos_a * body_len
    tail_y = cy - sin_a * body_len

    # ── Dış glow (şeffaf halo) ────────────────────────────────
    try:
        glow_surf = pygame.Surface((glow_r * 2 + 2, glow_r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*col_main, 55), (glow_r + 1, glow_r + 1), glow_r)
        surface.blit(glow_surf, (int(cx) - glow_r - 1, int(cy) - glow_r - 1))
    except Exception:
        pass

    # ── Gövde çizgisi (kalın — mermi bedeni) ─────────────────
    pygame.draw.line(surface, col_main,
                     (int(tail_x), int(tail_y)),
                     (int(cx),     int(cy)), body_w)

    # ── İnce parlak iç çizgi ─────────────────────────────────
    if body_w >= 3:
        pygame.draw.line(surface, col_core,
                         (int(tail_x), int(tail_y)),
                         (int(cx),     int(cy)), max(1, body_w - 3))

    # ── Uç nokta (mermi başı) — dolu nokta ───────────────────
    pygame.draw.circle(surface, col_main, (int(cx), int(cy)), max(2, body_w // 2 + 1))
    pygame.draw.circle(surface, col_core, (int(cx), int(cy)), max(1, body_w // 2 - 1))