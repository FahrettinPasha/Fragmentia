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

    def update(self, camera_speed, dt, player_pos=None):
        self.x += self.vx
        self.y += self.vy
        self.x -= camera_speed
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
        # [PLACEHOLDER] — 80×80 hitbox kutusu
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
    BORDER = (255, 215, 0)      # Altın

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


# ─── VASİL BOSS (local) ─────────────────────────────────────────────────────
class VasilBoss(pygame.sprite.Sprite):
    BORDER = (180, 0, 200)      # Mor-kırmızı

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

    def shoot(self, player_pos):
        angle = self.fire_timer * 0.1
        dx    = math.cos(angle)
        dy    = math.sin(angle)
        bullet = EnemyBullet(self.x, self.y, dx * BULLET_SPEED, dy * BULLET_SPEED, BOSS_DAMAGE)
        self.spawn_queue.append(bullet)

    def enter_phase2(self):
        pass

    def draw(self, surface, theme):
        label = f"VASİL  P{self.phase}"
        if self.invulnerable_timer > 0:
            label += "  [INV]"
        # [PLACEHOLDER] — Vasi boyutunda kutu (62*1.4 ≈ 87 → 90px)
        # Pixel artist: draw_vasi_silhouette çağrısını burada kullanacak
        _boss_hitbox(surface, int(self.x), int(self.y),
                     90, 125, self.BORDER, label,
                     self.health, self.max_health)

    def take_damage(self, damage, vfx_group=None):
        if self.invulnerable_timer <= 0:
            self.health             -= damage
            self.invulnerable_timer  = BOSS_INVULNERABILITY_TIME
            if vfx_group is not None:
                vfx_group.add(Shockwave(self.x, self.y, (255, 0, 0), max_radius=60, width=3, speed=10))
            if self.health <= 0:
                self.kill()