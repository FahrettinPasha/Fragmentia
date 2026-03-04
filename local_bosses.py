import pygame
import math
from settings import LOGICAL_WIDTH, LOGICAL_HEIGHT
from game_config import BULLET_SPEED, BOSS_HEALTH, BOSS_DAMAGE, BOSS_FIRE_RATE, BOSS_INVULNERABILITY_TIME
from vfx import Shockwave
from drawing_utils import draw_warrior_silhouette, draw_vasi_silhouette

# ═══════════════════════════════════════════════════════════════════════════
# LOCAL BOSS SINIFLARI — PLACEHOLDER GÖRSELLEŞTİRME
#
# Tüm draw() metodları sadeleştirildi:
#   - Hitbox dikdörtgeni (renkli çerçeve)
#   - HP bar (üstte)
#   - Faz / durum etiketi
#
# Pixel artist ekibi bu draw() içlerine sprite koyacak.
# Mantıksal (update/shoot/take_damage) hiçbir şey değişmedi.
# ═══════════════════════════════════════════════════════════════════════════

def draw_vasil_arena_bg(surface, fight_timer: float, logical_w: int, logical_h: int):
    """
    Level 0 Vasil intro fight için özel arena arka plan katmanı.
    Bu fonksiyon main.py'nin çizim pipeline'ında Step 4 (boss bg shadow) yerine
    current_level_idx == 0 iken çağrılır.

    Çizer:
      - Koyu kırmızı-mor gradyan zemin sis katmanı
      - Hareketli enerji çizgileri (dikey, pillar efekti)
      - Dönen sinirsel bağlantı ağı (background pulse)
      - Zemin ortasındaki "uçurum" görsel uyarısı (kırmızı parlayan çizgi)
      - Köşe çerçeve çizgileri (arena sınırı hissi)
    """
    # ── Gradyan zemin sisi ────────────────────────────────────────────────
    for row in range(0, logical_h, 6):
        ratio   = row / logical_h
        r_val   = int(6  + ratio * 18)
        g_val   = int(0  + ratio * 2)
        b_val   = int(10 + ratio * 22)
        alpha   = max(0, int(110 - ratio * 80))
        strip_s = pygame.Surface((logical_w, 6), pygame.SRCALPHA)
        strip_s.fill((r_val, g_val, b_val, alpha))
        surface.blit(strip_s, (0, row))

    # ── Hareketli dikey enerji sütunları ─────────────────────────────────
    import math as _m
    pulse_base = fight_timer * 1.4
    for col_i, col_x in enumerate([100, 260, 480, logical_w - 480,
                                    logical_w - 260, logical_w - 100]):
        flicker = abs(_m.sin(pulse_base + col_i * 1.1))
        a_line  = int(flicker * 55 + 5)
        ls      = pygame.Surface((2, logical_h), pygame.SRCALPHA)
        ls.fill((160, 0, 200, a_line))
        surface.blit(ls, (col_x, 0))
        # Alt parlama noktası
        glow_y  = logical_h - 105
        glow_r  = int(8 + flicker * 12)
        gs2     = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(gs2, (180, 0, 220, int(flicker * 60 + 10)),
                           (glow_r, glow_r), glow_r)
        surface.blit(gs2, (col_x - glow_r, glow_y - glow_r))

    # ── Zemin uçurum çizgisi (orta boşluğun kırmızı uyarısı) ─────────────
    pit_cx     = logical_w // 2
    pit_half   = 230
    pit_pulse  = abs(_m.sin(fight_timer * 2.2))
    pit_a      = int(pit_pulse * 130 + 40)
    pit_s      = pygame.Surface((pit_half * 2, 4), pygame.SRCALPHA)
    pit_s.fill((220, 0, 30, pit_a))
    surface.blit(pit_s, (pit_cx - pit_half, logical_h - 100))
    # Uçurum altına inen kırmızı "sonsuzluk" çizgileri
    for edge_x in (pit_cx - pit_half, pit_cx + pit_half - 2):
        ls2 = pygame.Surface((2, logical_h - 100), pygame.SRCALPHA)
        ls2.fill((180, 0, 25, int(pit_a * 0.55)))
        surface.blit(ls2, (edge_x, 100))

    # ── Köşe arena çerçevesi ──────────────────────────────────────────────
    arm = 60
    cf  = int(abs(_m.sin(fight_timer * 0.9)) * 40 + 80)
    corner_col = (cf, 0, int(cf * 1.3))
    for cx2, cy2, sx, sy in [
        (0,           0,            1,  1),
        (logical_w-1, 0,           -1,  1),
        (0,           logical_h-1,  1, -1),
        (logical_w-1, logical_h-1, -1, -1),
    ]:
        pygame.draw.line(surface, corner_col, (cx2, cy2), (cx2 + sx * arm, cy2), 2)
        pygame.draw.line(surface, corner_col, (cx2, cy2), (cx2, cy2 + sy * arm), 2)


def _boss_hitbox(surface, x, y, w, h, border_color, label, health, max_health):
    """Ortak boss placeholder çizici: hitbox + HP bar + etiket."""
    rect = pygame.Rect(x - w // 2, y - h // 2, w, h)

    # Yarı-saydam iç dolgu
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((10, 10, 20, 160))
    surface.blit(s, rect.topleft)

    # Çerçeve
    pygame.draw.rect(surface, border_color, rect, 2)

    # Köşe işaretleri
    corner = 10
    for cx, cy, dx, dy in [
        (rect.left,  rect.top,    1,  1),
        (rect.right, rect.top,   -1,  1),
        (rect.left,  rect.bottom, 1, -1),
        (rect.right, rect.bottom,-1, -1),
    ]:
        pygame.draw.line(surface, border_color, (cx, cy), (cx + dx * corner, cy), 2)
        pygame.draw.line(surface, border_color, (cx, cy), (cx, cy + dy * corner), 2)

    # Etiket
    font = pygame.font.Font(None, 22)
    lbl  = font.render(label, True, border_color)
    surface.blit(lbl, (rect.x + 4, rect.y + 4))

    # HP bar
    bw   = w
    bx   = rect.x
    by   = rect.top - 14
    pygame.draw.rect(surface, (40, 10, 10), (bx, by, bw, 8))
    pygame.draw.rect(surface, border_color, (bx, by, int(bw * max(0, health) / max_health), 8))
    pygame.draw.rect(surface, border_color, (bx, by, bw, 8), 1)


# ─── ENEMY BULLET ───────────────────────────────────────────────────────────
class EnemyBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy, damage):
        super().__init__()
        self.x      = x
        self.y      = y
        self.vx     = vx
        self.vy     = vy
        self.damage = damage
        self.radius = 8
        self.rect   = pygame.Rect(int(x) - 8, int(y) - 8, 16, 16)

    def update(self, camera_speed, dt, player_pos=None):
        self.x += self.vx
        self.y += self.vy
        self.x -= camera_speed
        self.rect.center = (int(self.x), int(self.y))
        if (self.x < -100 or self.x > LOGICAL_WIDTH + 100
                or self.y < -100 or self.y > LOGICAL_HEIGHT + 100):
            self.kill()

    def draw(self, surface, theme):
        # [PLACEHOLDER] Mermi — kırmızı dolu daire
        pygame.draw.circle(surface, (220, 30,  30), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (255, 200,   0), (int(self.x), int(self.y)), self.radius, 1)


# ─── NEXUS BOSS (local) ─────────────────────────────────────────────────────
class NexusBoss(pygame.sprite.Sprite):
    BORDER = (255, 0, 100)

    def __init__(self, x, y):
        super().__init__()
        self.x                  = x
        self.y                  = y
        self.health             = BOSS_HEALTH
        self.max_health         = BOSS_HEALTH
        self.fire_timer         = 0
        self.invulnerable_timer = 0
        self.spawn_queue        = []
        self.phase              = 1
        self.rect               = pygame.Rect(int(x) - 40, int(y) - 40, 80, 80)

    def update(self, camera_speed, dt, player_pos):
        if not getattr(self, 'ignore_camera_speed', False):
            self.x -= camera_speed
        self.fire_timer += 1
        if self.fire_timer >= BOSS_FIRE_RATE:
            self.fire_timer = 0
            self.shoot(player_pos)
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1
        if self.health <= self.max_health * 0.5 and self.phase == 1:
            self.phase = 2
            self.enter_phase2()
        self.rect.center = (int(self.x), int(self.y))

    def shoot(self, player_pos):
        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        dist = max(0.1, math.sqrt(dx * dx + dy * dy))
        dx /= dist; dy /= dist
        bullet = EnemyBullet(self.x, self.y, dx * BULLET_SPEED, dy * BULLET_SPEED, BOSS_DAMAGE)
        self.spawn_queue.append(bullet)

    def enter_phase2(self):
        pass

    def draw(self, surface, theme):
        label = f"NEXUS  P{self.phase}"
        if self.invulnerable_timer > 0:
            label += "  [INV]"
        _boss_hitbox(surface, int(self.x), int(self.y),
                     80, 80, self.BORDER, label,
                     self.health, self.max_health)

    def take_damage(self, damage, vfx_group=None):
        if self.invulnerable_timer <= 0:
            self.health             -= damage
            self.invulnerable_timer  = BOSS_INVULNERABILITY_TIME
            if vfx_group is not None:
                vfx_group.add(Shockwave(self.x, self.y, (255, 0, 0), max_radius=60, width=3, speed=10))
            if self.health <= 0:
                self.kill()


# ─── ARES BOSS (local) ──────────────────────────────────────────────────────
class AresBoss(pygame.sprite.Sprite):
    BORDER = (255, 215, 0)

    def __init__(self, x, y):
        super().__init__()
        self.x                  = x
        self.y                  = y
        self.health             = BOSS_HEALTH
        self.max_health         = BOSS_HEALTH
        self.fire_timer         = 0
        self.invulnerable_timer = 0
        self.spawn_queue        = []
        self.phase              = 1
        self.rect               = pygame.Rect(int(x) - 40, int(y) - 55, 80, 110)

    def update(self, camera_speed, dt, player_pos):
        if not getattr(self, 'ignore_camera_speed', False):
            self.x -= camera_speed
        self.fire_timer += 1
        if self.fire_timer >= BOSS_FIRE_RATE:
            self.fire_timer = 0
            self.shoot(player_pos)
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1
        if self.health <= self.max_health * 0.5 and self.phase == 1:
            self.phase = 2
            self.enter_phase2()
        self.rect.center = (int(self.x), int(self.y))

    def shoot(self, player_pos):
        for angle in [-0.2, 0, 0.2]:
            dx = player_pos[0] - self.x
            dy = player_pos[1] - self.y
            dist = max(0.1, math.sqrt(dx * dx + dy * dy))
            dx /= dist; dy /= dist
            new_dx = dx * math.cos(angle) - dy * math.sin(angle)
            new_dy = dx * math.sin(angle) + dy * math.cos(angle)
            bullet = EnemyBullet(self.x, self.y, new_dx * BULLET_SPEED, new_dy * BULLET_SPEED, BOSS_DAMAGE)
            self.spawn_queue.append(bullet)

    def enter_phase2(self):
        pass

    def draw(self, surface, theme):
        label = f"ARES  P{self.phase}"
        if self.invulnerable_timer > 0:
            label += "  [INV]"
        # [PLACEHOLDER] — Savaşçı boyutunda kutu (55*1.4 ≈ 77 → 80px)
        # Pixel artist: draw_warrior_silhouette çağrısını burada kullanacak
        _boss_hitbox(surface, int(self.x), int(self.y),
                     80, 110, self.BORDER, label,
                     self.health, self.max_health)

    def take_damage(self, damage, vfx_group=None):
        if self.invulnerable_timer <= 0:
            self.health             -= damage
            self.invulnerable_timer  = BOSS_INVULNERABILITY_TIME
            if vfx_group is not None:
                vfx_group.add(Shockwave(self.x, self.y, (255, 0, 0), max_radius=60, width=3, speed=10))
            if self.health <= 0:
                self.kill()


# ─── VASİL BOSS (local) — HAVADA SÜZÜLEN, YENİLEMEZ ─────────────────────────
class VasilBoss(pygame.sprite.Sprite):
    BORDER = (180, 0, 200)

    # Havada süzülme sabitleri
    _HOVER_SPEED  = 1.8    # Salınım hızı (rad/sn)
    _HOVER_AMP    = 22     # Yukarı-aşağı genlik (px)
    _HOVER_TARGET = 0.36   # Ekranın % kaçında duracak (irtifa)
    _LERP_SPEED   = 2.8    # Havaya kalkış yumuşaklığı

    # Boss konuşmaları — iyileşme sırasına göre
    _SPEECH = [
        "Sen kim olduğunu sanıyorsun?",          # Açılış
        "Zayıfsın. Daha iyi yapabilirsin.",       # 1. iyileşme
        "Mermi bitirmek mi? İlginç deneme.",      # 2. iyileşme
        "Son şansın. Göster kendini.",             # 3. iyileşme
        "Yeterince çırpındın. Artık dinlen.",      # Final / kill tetikleyici
    ]

    def __init__(self, x, y):
        super().__init__()
        self.x                  = float(x)
        self.y                  = float(y)
        self._base_y            = LOGICAL_HEIGHT * self._HOVER_TARGET
        self.health             = BOSS_HEALTH
        self.max_health         = BOSS_HEALTH
        self.fire_timer         = 0
        self._fire_rate         = float(BOSS_FIRE_RATE)   # Faz 2'de hızlanır
        self.invulnerable_timer = 0
        self.spawn_queue        = []
        self.phase              = 1
        self.rect               = pygame.Rect(int(x) - 45, int(y) - 62, 90, 125)
        self.heal_count         = 0
        self.kill_player        = False
        self._heal_flash        = 0
        self._speech_text       = ""
        self._speech_timer      = 0.0
        self._speech_shown      = False
        # Zamanlayıcılar
        self._float_timer       = 0.0   # Süzülme fazı (radyan)
        self._fight_timer       = 0.0   # Toplam savaş süresi (saniye)
        self._glow_pulse        = 0.0   # Aura nabız efekti
        self._pattern_cycle     = 0     # Hangi atış deseni aktif

    # ── GÜNCELLEME ──────────────────────────────────────────────────────────
    def update(self, camera_speed, dt, player_pos):
        # Kamera
        if not getattr(self, 'ignore_camera_speed', False):
            self.x -= camera_speed

        # Süre sayaçları
        self._float_timer += dt * self._HOVER_SPEED
        self._fight_timer += dt
        self._glow_pulse  += dt * 3.5
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1
        if self._heal_flash > 0:
            self._heal_flash -= 1
        if self._speech_timer > 0:
            self._speech_timer -= dt

        # Açılış diyalogu
        if not self._speech_shown:
            self._speech_shown = True
            self.say(self._SPEECH[0], duration=3.5)

        # Havaya kalkış + sürekli süzülme
        hover_y = self._base_y + math.sin(self._float_timer) * self._HOVER_AMP
        self.y  += (hover_y - self.y) * min(1.0, self._LERP_SPEED * dt)

        # Faz 2 geçişi (%50 can altında)
        if self.health <= self.max_health * 0.5 and self.phase == 1:
            self.phase = 2
            self.enter_phase2()

        # Ateş döngüsü
        self.fire_timer += 1
        if self.fire_timer >= self._fire_rate:
            self.fire_timer = 0
            self._shoot(player_pos)
            self._pattern_cycle = (self._pattern_cycle + 1) % 3

        # 20. saniyede uyarı
        if 19.5 <= self._fight_timer < 20.0 and not self.kill_player:
            self.say("Zaman daralıyor... son fırsatın.", duration=3.0)

        # 30 saniyede zaman aşımı — oyuncu yetişemez
        if self._fight_timer >= 30.0 and not self.kill_player:
            self.kill_player = True
            self.say(self._SPEECH[-1], duration=3.0)

        self.rect.center = (int(self.x), int(self.y))

    # ── ATIŞ DESENLERİ ──────────────────────────────────────────────────────
    def _shoot(self, player_pos):
        """Her atış döngüsünde farklı bir desen seç."""
        pat = self._pattern_cycle
        if pat == 0:
            # Oyuncuya nişanlı yelpaze — kaçılması güç
            self._shoot_aimed(player_pos,
                              spread_count=3 if self.phase == 1 else 5,
                              spread_angle=0.22)
        elif pat == 1:
            # Döner sarmal — alanı kontrol eder
            self._shoot_spiral(arms=2 if self.phase == 1 else 4)
        else:
            # Her yöne halka — duvara sıkıştırır
            self._shoot_ring(count=6 if self.phase == 1 else 10)

    def _shoot_aimed(self, player_pos, spread_count=3, spread_angle=0.22):
        dx   = player_pos[0] - self.x
        dy   = player_pos[1] - self.y
        dist = max(0.1, math.sqrt(dx * dx + dy * dy))
        dx  /= dist
        dy  /= dist
        base = math.atan2(dy, dx)
        half = (spread_count - 1) / 2.0
        spd  = BULLET_SPEED * (1.25 if self.phase == 2 else 1.0)
        for i in range(spread_count):
            a = base + (i - half) * spread_angle
            self.spawn_queue.append(
                EnemyBullet(self.x, self.y, math.cos(a) * spd, math.sin(a) * spd, BOSS_DAMAGE)
            )

    def _shoot_spiral(self, arms=2):
        base = self.fire_timer * 0.14
        spd  = BULLET_SPEED
        for i in range(arms):
            a = base + (math.pi * 2 / arms) * i
            self.spawn_queue.append(
                EnemyBullet(self.x, self.y, math.cos(a) * spd, math.sin(a) * spd, BOSS_DAMAGE)
            )

    def _shoot_ring(self, count=6):
        spd = BULLET_SPEED * 0.9
        for i in range(count):
            a = (math.pi * 2 / count) * i
            self.spawn_queue.append(
                EnemyBullet(self.x, self.y, math.cos(a) * spd, math.sin(a) * spd, BOSS_DAMAGE)
            )

    # ── YARDIMCILAR ─────────────────────────────────────────────────────────
    def say(self, text, duration=3.0):
        self._speech_text  = text
        self._speech_timer = duration

    def enter_phase2(self):
        """Faz 2: Daha hızlı ateş, daha geniş salınım."""
        self._fire_rate   = max(18, self._fire_rate - 22)
        self._HOVER_AMP   = 38
        self._LERP_SPEED  = 4.5
        self.say("Gerçek savaş şimdi başlıyor.", duration=2.5)

    # ── HASAR — GERÇEKTEN YENİLEMEZ ─────────────────────────────────────────
    def take_damage(self, damage, vfx_group=None):
        """
        Vasil hiçbir zaman ölmez.
        %20 can altına düştüğünde ya da HP sıfırlandığında daima iyileşir.
        4 iyileşmeden sonra kill_player = True sinyali verir.
        """
        if self.invulnerable_timer > 0:
            return False

        self.health             -= damage
        self.invulnerable_timer  = BOSS_INVULNERABILITY_TIME

        if vfx_group is not None:
            vfx_group.add(Shockwave(self.x, self.y, (255, 0, 0),
                                    max_radius=60, width=3, speed=10))

        # İyileşme eşiği: %20 canın altı VEYA HP <= 0
        needs_heal = (self.health <= self.max_health * 0.20) or (self.health <= 0)
        if needs_heal:
            self.health             = int(self.max_health * 0.70)
            self._heal_flash        = 60
            self.invulnerable_timer = 120
            self.heal_count        += 1

            speech_idx = min(self.heal_count, len(self._SPEECH) - 2)
            self.say(self._SPEECH[speech_idx], duration=3.0)

            if vfx_group is not None:
                vfx_group.add(Shockwave(self.x, self.y, (0, 255, 120),
                                        max_radius=210, width=7, speed=22))

            # 4 iyileşmeden sonra → oyuncuyu öldür
            if self.heal_count >= 4:
                self.say(self._SPEECH[-1], duration=2.5)
                self.kill_player = True

        return False   # Vasil hiçbir zaman "öldü" sinyali vermez

    # ── ÇİZİM ───────────────────────────────────────────────────────────────
    def draw(self, surface, theme):
        cx = int(self.x)
        cy = int(self.y)

        # 1. Zemin gölgesi (boss havada, gölge aşağıda küçülür)
        shadow_y = LOGICAL_HEIGHT - 108
        dist_to_floor = max(1, shadow_y - cy)
        shadow_w = max(10, int(65 - dist_to_floor * 0.06))
        shadow_h = max(3, int(shadow_w * 0.18))
        shs = pygame.Surface((shadow_w * 2, shadow_h * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(shs, (70, 0, 90, 55), (0, 0, shadow_w * 2, shadow_h * 2))
        surface.blit(shs, (cx - shadow_w, shadow_y - shadow_h))

        # 2. Dıştan içe nefes alan aura halkası
        glow_r = int(62 + math.sin(self._glow_pulse) * 14)
        alpha  = int(35 + math.sin(self._glow_pulse * 1.4) * 18)
        gs = pygame.Surface((glow_r * 2 + 6, glow_r * 2 + 6), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*self.BORDER, alpha), (glow_r + 3, glow_r + 3), glow_r, 4)
        surface.blit(gs, (cx - glow_r - 3, cy - glow_r - 3))

        # 3. İç nabız halkası (iyileşme sırasında genişler)
        if self._heal_flash > 0:
            hf_r = int(45 + (60 - self._heal_flash) * 2.5)
            hfs  = pygame.Surface((hf_r * 2 + 4, hf_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(hfs, (0, 255, 120, 90), (hf_r + 2, hf_r + 2), hf_r, 5)
            surface.blit(hfs, (cx - hf_r - 2, cy - hf_r - 2))

        # 4. Boss hitbox + HP bar + etiket
        border = (0, 255, 120) if self._heal_flash > 0 else self.BORDER
        label  = f"VASİL  P{self.phase}"
        if self.invulnerable_timer > 0:
            label += "  [INV]"
        if self._heal_flash > 0:
            label += "  [İYİLEŞİYOR!]"
        _boss_hitbox(surface, cx, cy, 90, 125, border, label,
                     self.health, self.max_health)

        # 5. Konuşma balonu
        if self._speech_timer > 0 and self._speech_text:
            self._draw_speech_bubble(surface)

    def _draw_speech_bubble(self, surface):
        try:
            font = pygame.font.Font(None, 22)
        except Exception:
            return
        pad = 10
        txt = font.render(self._speech_text, True, (220, 210, 255))
        bw  = txt.get_width()  + pad * 2
        bh  = txt.get_height() + pad * 2
        bx  = int(self.x) - bw // 2
        by  = int(self.y) - 62 - bh - 18
        bg  = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bg.fill((10, 0, 20, 210))
        surface.blit(bg, (bx, by))
        pygame.draw.rect(surface, self.BORDER, pygame.Rect(bx, by, bw, bh), 2)
        tip_x = int(self.x)
        tip_y = int(self.y) - 62 - 4
        pygame.draw.polygon(surface, self.BORDER, [
            (tip_x - 6, by + bh),
            (tip_x + 6, by + bh),
            (tip_x,     tip_y),
        ])
        surface.blit(txt, (bx + pad, by + pad))