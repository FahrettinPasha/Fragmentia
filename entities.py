# entities.py — PLACEHOLDER GÖRSELLEŞTİRME
# Tüm draw() metodları sadelestirildi:
#   - Oyuncu   → düz dikdörtgen (main.py'de çiziliyor)
#   - Düşmanlar → sadece hitbox çerçevesi + tür etiketi
#   - NPC'ler  → küçük renkli kutu + isim
#   - Platform → düz renk + tema çerçevesi (önceden sade hale getirilmişti)
# Pixel artist ekibi bu draw() metodlarını sprite ile dolduracak.

import pygame
import random
import math
from settings import *
from drawing_utils import draw_warrior_silhouette, draw_vasi_silhouette
# Sprite araçları — utils'ten alınıyor (önbellek + SpriteSheet)
try:
    from utils import get_image, SpriteSheet, FrameAnimator
except ImportError:
    # utils henüz güncellenmemişse sessizce devam et
    def get_image(p):
        s = pygame.Surface((1,1), pygame.SRCALPHA); return s
    SpriteSheet    = None
    FrameAnimator  = None

# --- KONUŞMA SİSTEMİ İÇİN KELİME LİSTESİ ---
ALIEN_SPEECH = [
    "ZGRR!", "0xDEAD", "##!!", "HATA", "KZZT...",
    "¥€$?", "NO_SIGNAL", "GÖRDÜM!", "∆∆∆", "SİLİN!"
]

# --- RENKLER ---
VOID_PURPLE  = (20,  0,  30)
TOXIC_GREEN  = ( 0, 255,  50)
CORRUPT_NEON = ( 0, 255, 200)

# ─── YARDIMCI: placeholder kutu + etiket ───────────────────────────────────
def _hitbox_rect(surface, rect, border_color, label, extra_info=""):
    """
    Düşman / nesne hitbox'ını çizer.
    Siyah yarı-saydam dolgu + renkli 2px çerçeve + etiket.
    """
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    s.fill((10, 10, 15, 160))
    surface.blit(s, rect.topleft)
    pygame.draw.rect(surface, border_color, rect, 2)

    font = pygame.font.Font(None, 18)
    lbl  = font.render(label, True, border_color)
    surface.blit(lbl, (rect.x + 3, rect.y + 3))
    if extra_info:
        lbl2 = font.render(extra_info, True, border_color)
        surface.blit(lbl2, (rect.x + 3, rect.y + rect.height - 14))


# --- ÇİZİM YARDIMCI (sadece çerçeve, glitch efekti kaldırıldı) ---
def draw_themed_glitch(surface, rect, body_color, neon_color):
    """[PLACEHOLDER] Sadece düz dolgu + çerçeve."""
    pygame.draw.rect(surface, body_color, rect)
    pygame.draw.rect(surface, neon_color,  rect, 1)


# ─── ENEMY BASE ─────────────────────────────────────────────────────────────
class EnemyBase(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.health   = 100
        self.is_active = True
        self.speech_text     = ""
        self.speech_timer    = 0
        self.speech_duration = 0
        self.speech_font     = pygame.font.Font(None, 24)
        self.spawn_queue     = []

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.is_active = False
            return True
        return False

    def update_speech(self, dt):
        if self.speech_duration > 0:
            self.speech_duration -= dt
            if self.speech_duration <= 0:
                self.speech_text = ""
        if self.speech_text == "" and random.random() < 0.005:
            self.speech_text    = random.choice(ALIEN_SPEECH)
            self.speech_duration = 2.0

    def draw_speech(self, surface, x, y):
        if self.speech_text:
            text_surf = self.speech_font.render(self.speech_text, True, (255, 50, 50))
            text_rect = text_surf.get_rect(center=(x, y - 30))
            bg_rect   = text_rect.inflate(10, 5)
            pygame.draw.rect(surface, (0, 0, 0), bg_rect)
            pygame.draw.rect(surface, (255, 0, 0), bg_rect, 1)
            surface.blit(text_surf, text_rect)


# ─── PLATFORM ───────────────────────────────────────────────────────────────
class Platform(pygame.sprite.Sprite):
    """
    Platform — 3-Parçalı Slice Sistemi
    ─────────────────────────────────────
    Sol uç (L), tekrarlanan orta kısım (M), sağ uç (R) olmak üzere
    üç ayrı PNG dosyası kullanılır.

    Dosya yolları (settings.PLATFORM_TILES_DIR altında tema klasörü):
        assets/tiles/theme_{theme_index}/platform_left.png
        assets/tiles/theme_{theme_index}/platform_mid.png
        assets/tiles/theme_{theme_index}/platform_right.png

    Bu dosyalar bulunamazsa eski düz renk+çerçeve yöntemiyle devam eder
    (backward-compatible fallback).
    """

    # Tema başına tile önbelleği — aynı tile'ı defalarca diskten yükleme
    _tile_cache: dict = {}

    def __init__(self, x, y, width, height, theme_index=0):
        super().__init__()
        self.width       = width
        self.height      = height
        self.theme_index = theme_index
        self.rect        = pygame.Rect(x, y, width, height)

        # Tile resimleri yükle (veya None — fallback çizer)
        self._load_tiles(theme_index)

        # Fallback için düz renk yüzeyi hazırla
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.generate_texture()

    # ------------------------------------------------------------------
    def _load_tiles(self, theme_index: int):
        """Tile dosyalarını önbellekten al ya da diskten yükle."""
        key = theme_index
        if key not in Platform._tile_cache:
            base = f"{PLATFORM_TILES_DIR}/theme_{theme_index}"
            Platform._tile_cache[key] = {
                "left":  get_image(f"{base}/platform_left.png"),
                "mid":   get_image(f"{base}/platform_mid.png"),
                "right": get_image(f"{base}/platform_right.png"),
            }
        tiles = Platform._tile_cache[key]
        # Geçerli tile mi? (1×1 placeholder = asset yok)
        self._tile_left  = tiles["left"]  if tiles["left"].get_width()  > 1 else None
        self._tile_mid   = tiles["mid"]   if tiles["mid"].get_width()   > 1 else None
        self._tile_right = tiles["right"] if tiles["right"].get_width() > 1 else None
        self._use_tiles  = all(t is not None for t in
                               [self._tile_left, self._tile_mid, self._tile_right])

    # ------------------------------------------------------------------
    def generate_texture(self):
        """Fallback: Düz renk + çerçeve (tile yoksa kullanılır)."""
        self.image.fill((0, 0, 0, 0))
        theme          = THEMES[self.theme_index % len(THEMES)]
        platform_color = theme.get("platform_color", (30, 30, 40))
        border_color   = theme.get("border_color",   (100, 100, 120))
        pygame.draw.rect(self.image, platform_color, (0, 0, self.width, self.height))
        pygame.draw.rect(self.image, border_color,   (0, 0, self.width, self.height), 2)

    # ------------------------------------------------------------------
    def update(self, camera_speed, dt=0.016):
        self.rect.x -= camera_speed
        if self.rect.right < 0:
            self.kill()

    # ------------------------------------------------------------------
    def draw(self, surface, theme=None, camera_offset=(0, 0)):
        ox, oy = camera_offset
        blit_x = self.rect.x + ox
        blit_y = self.rect.y + oy

        if self._use_tiles:
            self._draw_sliced(surface, blit_x, blit_y)
        else:
            surface.blit(self.image, (blit_x, blit_y))

    # ------------------------------------------------------------------
    def _draw_sliced(self, surface, blit_x: int, blit_y: int):
        """
        3-Parçalı Slice Çizimi
        Sol uç  → tekrarlanan orta → sağ uç

        Platformun yüksekliği tile yüksekliğiyle eşleşmiyorsa
        tile dikey olarak ölçeklenir.
        """
        l_w = self._tile_left.get_width()
        r_w = self._tile_right.get_width()
        m_w = self._tile_mid.get_width()
        t_h = self._tile_left.get_height()

        # Dikey ölçekleme gerekiyorsa (platform yüksekliği farklıysa)
        if t_h != self.height:
            scale_y = self.height / t_h
            def _scale(surf):
                return pygame.transform.scale(
                    surf, (surf.get_width(), self.height))
            tl = _scale(self._tile_left)
            tm = _scale(self._tile_mid)
            tr = _scale(self._tile_right)
            l_w = tl.get_width()
            r_w = tr.get_width()
            m_w = tm.get_width()
        else:
            tl, tm, tr = self._tile_left, self._tile_mid, self._tile_right

        # Orta alanın genişliği
        inner_w = self.width - l_w - r_w
        if inner_w < 0:
            # Platform çok dar — sadece sol+sağ
            surface.blit(tl, (blit_x, blit_y))
            surface.blit(tr, (blit_x + self.width - r_w, blit_y))
            return

        # Sol uç
        surface.blit(tl, (blit_x, blit_y))
        # Orta kısım — döşe
        cur_x = blit_x + l_w
        while cur_x < blit_x + l_w + inner_w:
            chunk_w = min(m_w, (blit_x + l_w + inner_w) - cur_x)
            if chunk_w == m_w:
                surface.blit(tm, (cur_x, blit_y))
            else:
                # Son parça: kırparak blit
                sub = tm.subsurface(pygame.Rect(0, 0, chunk_w, self.height))
                surface.blit(sub, (cur_x, blit_y))
            cur_x += chunk_w
        # Sağ uç
        surface.blit(tr, (blit_x + self.width - r_w, blit_y))



# ─── STAR ───────────────────────────────────────────────────────────────────
class Star:
    def __init__(self, screen_width, screen_height):
        self.x              = random.randrange(0, screen_width)
        self.y              = random.randrange(0, screen_height)
        self.size           = random.randint(1, 3)
        self.speed          = random.uniform(0.5, 1.5)
        self.brightness     = random.randint(150, 255)
        self.twinkle_speed  = random.uniform(0.5, 2.0)
        self.twinkle_offset = random.uniform(0, math.pi * 2)
        self.screen_width   = screen_width
        self.screen_height  = screen_height

    def update(self, camera_speed, dt=0.016):
        self.x -= self.speed * camera_speed / 3
        time    = pygame.time.get_ticks() * 0.001
        twinkle = (math.sin(time * self.twinkle_speed + self.twinkle_offset) + 1) / 2
        self.brightness = int(150 + twinkle * 105)
        if self.x < 0:
            self.x          = self.screen_width
            self.y          = random.randrange(0, self.screen_height)
            self.brightness = random.randint(150, 255)

    def draw(self, surface):
        color = (self.brightness, self.brightness, self.brightness)
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.size)


# ─── ENEMY PROJECTILE ───────────────────────────────────────────────────────
class EnemyProjectile(pygame.sprite.Sprite):
    def __init__(self, x, y, target_x=None, target_y=None, speed=10):
        super().__init__()
        self.rect = pygame.Rect(x, y, 15, 15)

        if target_x is not None and target_y is not None:
            dx = target_x - x
            dy = target_y - y
            angle = math.atan2(dy, dx)
            self.vx = math.cos(angle) * speed
            self.vy = math.sin(angle) * speed
        else:
            self.vx = -speed
            self.vy = 0

        self.color = (255, 0, 0)
        self.timer = 0

    def update(self, camera_speed, dt=0.016, player_pos=None):
        self.rect.x -= camera_speed
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.timer  += dt

        # Renk titremesi kaldırıldı — tek renk, sade
        if self.rect.right < 0 or self.rect.y > LOGICAL_HEIGHT or self.rect.y < 0:
            self.kill()

    def draw(self, surface, camera_offset=(0, 0), theme=None):
        offset_x, offset_y = camera_offset
        draw_rect = pygame.Rect(
            self.rect.x + offset_x,
            self.rect.y + offset_y,
            self.rect.width,
            self.rect.height
        )
        # [PLACEHOLDER] Mermi → küçük renkli dikdörtgen
        pygame.draw.rect(surface, self.color,       draw_rect)
        pygame.draw.rect(surface, (255, 255, 255),  draw_rect, 1)


# ─── CURSED ENEMY ───────────────────────────────────────────────────────────
class CursedEnemy(EnemyBase):
    def __init__(self, platform, theme_index=0):
        super().__init__()
        self.platform    = platform
        self.width       = 40
        self.height      = 40
        self.theme_index = theme_index

        safe_x   = random.randint(platform.rect.left, max(platform.rect.left, platform.rect.right - self.width))
        self.rect = pygame.Rect(safe_x, platform.rect.top - self.height, self.width, self.height)

        self.health    = 100
        self.max_health = 100
        self.speed     = 2
        self.direction = random.choice([-1, 1])
        self.timer     = 0

    def update(self, camera_speed, dt=0.016, player_pos=None):
        if not self.is_active: return
        self.update_speech(dt)
        self.rect.x -= camera_speed
        self.rect.x += self.speed * self.direction

        if self.rect.right > self.platform.rect.right:
            self.direction = -1
        elif self.rect.left < self.platform.rect.left:
            self.direction = 1

        self.timer += dt
        if self.rect.right < 0:        self.kill()
        if not self.platform.alive():  self.kill()

    def draw(self, surface, camera_offset=(0, 0), theme=None):
        if not self.is_active: return
        ox, oy = camera_offset
        neon   = theme['border_color'] if theme else (0, 255, 100)
        draw_r = self.rect.move(ox, oy)

        # ── SPRITE ──────────────────────────────────────────────────────
        # Pixel artist: assets/sprites/cursed_enemy_sheet.png dosyası
        # varsa FrameAnimator üzerinden o anki kare blit edilir.
        # Dosya yoksa eski hitbox placeholder çizilir.
        # Sprite boyutu: 40×40 px (self.width × self.height ile eşleşmeli).
        # Yön: direction == 1 → sağa bakar; pygame.transform.flip ile çevir.
        if hasattr(self, '_animator') and self._animator and \
                self._animator.get_frame() is not None:
            frame = self._animator.get_frame()
            if self.direction == 1:
                frame = pygame.transform.flip(frame, True, False)
            surface.blit(frame, draw_r.topleft)
        else:
            # [PLACEHOLDER] Düşman — hitbox çerçevesi
            _hitbox_rect(surface, draw_r, neon, "CURSED")
        # ── HP bar (can azaldığında görünür) ─────────────────────────────
        if self.health < self.max_health:
            bar_w = self.width
            bar_h = 4
            bx = draw_r.x
            by = draw_r.y - 7
            fill  = int(bar_w * max(0, self.health) / self.max_health)
            pygame.draw.rect(surface, (80, 0, 0),   (bx, by, bar_w, bar_h))
            pygame.draw.rect(surface, (0, 220, 80),  (bx, by, fill, bar_h))
        # ────────────────────────────────────────────────────────────────
        self.draw_speech(surface, draw_r.centerx, draw_r.top)


# ─── DRONE ENEMY ────────────────────────────────────────────────────────────
class DroneEnemy(EnemyBase):
    def __init__(self, x, y):
        super().__init__()
        self.width        = 40
        self.height       = 40
        self.rect         = pygame.Rect(x, y, self.width, self.height)
        self.health       = 80
        self.max_health   = 80
        self.timer        = random.uniform(0, 100)
        self.shoot_timer  = 0
        self.target_x     = x
        self.target_y     = y
        self.move_timer   = 0
        self.recoil_x     = 0

    def update(self, camera_speed, dt=0.016, player_pos=None):
        if not self.is_active: return
        self.update_speech(dt)

        self.rect.x   -= camera_speed
        self.target_x -= camera_speed

        self.move_timer -= dt
        if self.move_timer <= 0:
            self.move_timer = random.uniform(1.0, 2.5)
            self.target_x   = self.rect.x + random.uniform(-100, 100)
            self.target_y   = max(50, min(LOGICAL_HEIGHT - 150,
                                          self.rect.y + random.uniform(-80, 80)))

        self.rect.x  += (self.target_x - self.rect.x) * 2 * dt
        self.rect.y  += (self.target_y - self.rect.y) * 2 * dt
        self.recoil_x *= 0.9

        self.shoot_timer += dt
        if self.shoot_timer > 0.8:
            self.shoot_timer  = 0
            self.recoil_x     = 10

            px, py = None, None
            if player_pos:
                if hasattr(player_pos, 'center'):    px, py = player_pos.center
                elif isinstance(player_pos, (tuple, list)): px, py = player_pos[0], player_pos[1]

            if px is not None and py is not None:
                projectile = EnemyProjectile(self.rect.centerx, self.rect.centery, px, py, speed=15)
            else:
                projectile = EnemyProjectile(self.rect.centerx, self.rect.centery,
                                             target_x=self.rect.x - 100, target_y=self.rect.y, speed=15)
            for group in self.groups():
                group.add(projectile)

        if self.rect.right < 0: self.kill()

    def draw(self, surface, camera_offset=(0, 0), theme=None):
        if not self.is_active: return
        ox, oy = camera_offset
        neon   = theme['border_color'] if theme else (0, 255, 200)
        draw_r = self.rect.move(ox, oy)

        # ── SPRITE ──────────────────────────────────────────────────────
        # Pixel artist: assets/sprites/drone_sheet.png
        # Boyut: 40×40 px — havada süzülen animasyon.
        # Yön: hareket yönüne göre flip.
        if hasattr(self, '_animator') and self._animator and \
                self._animator.get_frame() is not None:
            frame = self._animator.get_frame()
            if hasattr(self, 'direction') and self.direction == 1:
                frame = pygame.transform.flip(frame, True, False)
            surface.blit(frame, draw_r.topleft)
        else:
            # [PLACEHOLDER] Drone — hitbox çerçevesi (elmas/kare)
            _hitbox_rect(surface, draw_r, neon, "DRONE")
        # ── HP bar (can azaldığında görünür) ─────────────────────────────
        if self.health < self.max_health:
            bar_w = self.width
            bar_h = 4
            bx = draw_r.x
            by = draw_r.y - 7
            fill  = int(bar_w * max(0, self.health) / self.max_health)
            pygame.draw.rect(surface, (80, 0, 0),   (bx, by, bar_w, bar_h))
            pygame.draw.rect(surface, (0, 200, 220), (bx, by, fill, bar_h))
        # ────────────────────────────────────────────────────────────────
        self.draw_speech(surface, draw_r.centerx, draw_r.top)


# ─── TANK ENEMY ─────────────────────────────────────────────────────────────
class TankEnemy(EnemyBase):
    def __init__(self, platform):
        super().__init__()
        self.platform = platform
        self.width    = 160
        self.height   = 140
        self.health   = 500

        self.rect = pygame.Rect(
            platform.rect.centerx - 80,
            platform.rect.top - self.height,
            self.width, self.height
        )
        self.max_health    = self.health
        self.vx            = 2
        self.vy            = 0
        self.on_ground     = True
        self.move_timer    = 0
        self.barrel_angle  = 0
        self.shoot_timer   = 0
        self.muzzle_flash  = 0

    def update(self, camera_speed, dt=0.016, player_pos=None):
        if not self.is_active: return
        self.update_speech(dt)

        self.rect.x -= camera_speed
        self.move_timer += dt
        self.vy += 0.8
        self.rect.y += self.vy

        if self.rect.bottom >= self.platform.rect.top and self.vy > 0:
            if self.rect.bottom - self.vy <= self.platform.rect.top + 10:
                self.rect.bottom = self.platform.rect.top
                self.vy = 0
                self.on_ground = True
        else:
            self.on_ground = False

        if self.on_ground:
            self.rect.x += self.vx
            self.move_timer += dt
            if self.rect.right > self.platform.rect.right:
                self.rect.right = self.platform.rect.right; self.vx *= -1
            elif self.rect.left < self.platform.rect.left:
                self.rect.left  = self.platform.rect.left;  self.vx *= -1

        target_x, target_y = self.rect.x - 200, self.rect.centery
        if player_pos:
            if hasattr(player_pos, 'center'):
                target_x, target_y = player_pos.center
            elif isinstance(player_pos, (tuple, list)):
                target_x, target_y = player_pos[0], player_pos[1]

        dx = target_x - self.rect.centerx
        dy = target_y - (self.rect.y + 30)
        target_angle = math.atan2(dy, dx)
        self.barrel_angle += (target_angle - self.barrel_angle) * 0.1

        self.shoot_timer  += dt
        self.muzzle_flash  = max(0, self.muzzle_flash - 1)

        angle_diff = abs(target_angle - self.barrel_angle)
        if self.shoot_timer > 1.5 and angle_diff < 0.2:
            self.shoot_timer  = 0
            self.muzzle_flash = 5
            barrel_len        = 80
            bx = self.rect.centerx + math.cos(self.barrel_angle) * barrel_len
            by = (self.rect.y + 30) + math.sin(self.barrel_angle) * barrel_len
            projectile = EnemyProjectile(bx, by, target_x, target_y, speed=15)
            projectile.rect.width  = 25
            projectile.rect.height = 25
            for group in self.groups():
                group.add(projectile)

        if self.rect.right < 0:            self.kill()
        if not self.platform.alive():      self.kill()

    def draw(self, surface, camera_offset=(0, 0), theme=None):
        if not self.is_active: return
        ox, oy = camera_offset
        neon   = theme['border_color'] if theme else (255, 100, 0)
        draw_r = self.rect.move(ox, oy)

        # [PLACEHOLDER] Tank — büyük hitbox çerçevesi
        hp_pct = self.health / self.max_health
        _hitbox_rect(surface, draw_r, neon, "TANK", f"HP {int(hp_pct*100)}%")

        # Namlu yönü — ince çizgi
        end_x = draw_r.centerx + math.cos(self.barrel_angle) * 40
        end_y = draw_r.centery + math.sin(self.barrel_angle) * 40
        pygame.draw.line(surface, neon, draw_r.center, (int(end_x), int(end_y)), 2)

        self.draw_speech(surface, draw_r.centerx, draw_r.top)


# ─── NPC ────────────────────────────────────────────────────────────────────
class NPC:
    def __init__(self, x, y, name, color, personality_type="philosopher", prompt=None):
        self.x = x
        self.y = y
        self.name             = name
        self.color            = color
        self.personality_type = personality_type
        self.prompt           = prompt
        self.ai_active        = False

        self.width  = 28
        self.height = 48
        self.rect   = pygame.Rect(x - 14, y - 48, 28, 48)

        self.talk_radius  = 200
        self.can_talk     = False
        self.talking      = False

        self.float_timer  = random.uniform(0, 100)
        self.glitch_timer = 0
        self.eye_offset_x = 0
        self.eye_offset_y = 0

    def update(self, player_x, player_y, dt=0.016):
        self.float_timer += dt * 2

        dx   = player_x - self.x
        dy   = (player_y - 40) - (self.y - 40)
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            self.eye_offset_x = (dx / dist) * 3
            self.eye_offset_y = (dy / dist) * 2

        if random.random() < 0.01:
            self.glitch_timer = 5
        if self.glitch_timer > 0:
            self.glitch_timer -= 1

        self.can_talk = dist < self.talk_radius

    def draw(self, surface, camera_offset=(0, 0)):
        ox, oy = camera_offset
        float_y = math.sin(self.float_timer) * 4
        draw_x  = int(self.x + ox)
        draw_y  = int(self.y + oy + float_y)

        # [PLACEHOLDER] NPC — renk-kodlu dikdörtgen + isim
        w, h = self.width, self.height
        rect = pygame.Rect(draw_x - w // 2, draw_y - h, w, h)

        box = pygame.Surface((w, h), pygame.SRCALPHA)
        box.fill((10, 10, 20, 180))
        surface.blit(box, rect.topleft)
        pygame.draw.rect(surface, self.color, rect, 2)

        font  = pygame.font.Font(None, 17)
        label = font.render(self.name[:8], True, self.color)
        surface.blit(label, (rect.x + 2, rect.y + 2))

        # "E" balonu — yakınsa göster
        if self.can_talk:
            bubble = pygame.Rect(draw_x + 10, draw_y - h - 20, 20, 16)
            pygame.draw.rect(surface, (240, 240, 240), bubble, border_radius=3)
            ef   = pygame.font.Font(None, 18)
            etxt = ef.render("E", True, (0, 0, 0))
            surface.blit(etxt, (bubble.x + 5, bubble.y + 1))
            # Talk radius çemberi — ince, yarı saydamlık ile
            radius_surf = pygame.Surface((self.talk_radius * 2, self.talk_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(radius_surf, (*self.color, 25),
                               (self.talk_radius, self.talk_radius), self.talk_radius, 1)
            surface.blit(radius_surf, (draw_x - self.talk_radius, draw_y - self.talk_radius - h // 2))

    def start_conversation(self):
        self.talking = True
        if self.prompt: return self.prompt
        return "..."

    def send_message(self, player_message, game_context=None):
        return "Sistem verisi analiz ediliyor..."

    def end_conversation(self):
        self.talking = False
        return ""


# ─── ARES BOSS (entities) ───────────────────────────────────────────────────
class AresBoss(EnemyBase):
    def __init__(self, x, y):
        super().__init__()
        self.width, self.height = 100, 140
        self.x, self.y = x, y
        self.rect       = pygame.Rect(x, y, self.width, self.height)
        self.health     = 2500
        self.max_health = 2500
        self.state      = "IDLE"
        self.timer      = 0
        self.target_x   = x
        self.vy         = 0

    def update(self, camera_speed, dt=0.016, player_pos=None):
        if not self.is_active: return
        self.update_speech(dt)
        px, py = 0, 0
        if player_pos:
            if isinstance(player_pos, tuple): px, py = player_pos
            else: px, py = player_pos.center
        self.timer += dt

        if self.state == "IDLE":
            direction = 1 if px > self.rect.centerx else -1
            self.rect.x += direction * 2
            if self.timer > 2.0:
                self.timer = 0
                r = random.random()
                if r < 0.4:   self.state = "PREP_DASH";  self.speech_text = "KAÇAMAZSIN!"
                elif r < 0.7: self.state = "PREP_SMASH"; self.speech_text = "EZİLECEKSİN!"
                else:         self.state = "PREP_BEAM";  self.speech_text = "KESİP ATACAĞIM!"
                self.speech_duration = 1.0

        elif self.state == "PREP_DASH":
            if self.timer > 0.5: self.state = "DASH"; self.timer = 0; self.target_x = px
        elif self.state == "DASH":
            self.rect.x += (1 if self.target_x > self.rect.centerx else -1) * 25
            if self.timer > 0.8: self.state = "IDLE"; self.timer = 0

        elif self.state == "PREP_SMASH":
            if self.timer < 0.02: self.vy = -20
            self.vy += 1
            self.rect.y += self.vy
            if self.rect.bottom >= LOGICAL_HEIGHT - 50:
                self.rect.bottom = LOGICAL_HEIGHT - 50
                self.state = "IDLE"; self.timer = 0
                wave = EnemyProjectile(self.rect.centerx, self.rect.bottom - 20,
                                       self.rect.centerx - 500, self.rect.bottom - 20, speed=15)
                wave.rect.width, wave.rect.height, wave.color = 40, 20, (255, 100, 0)
                self.spawn_queue.append(wave)

        elif self.state == "PREP_BEAM":
            if self.timer > 0.8:
                self.state = "IDLE"; self.timer = 0
                beam = EnemyProjectile(self.rect.centerx, self.rect.centery, px, py, speed=20)
                beam.rect.width, beam.rect.height, beam.color = 10, 100, (200, 200, 255)
                self.spawn_queue.append(beam)

        if self.state != "PREP_SMASH":
            self.rect.bottom = min(self.rect.bottom, LOGICAL_HEIGHT - 50)

    def draw(self, surface, camera_offset=(0, 0), theme=None):
        if not self.is_active: return
        ox, oy = camera_offset
        GOLD   = (255, 215, 0)
        draw_r = self.rect.move(ox, oy)

        # [PLACEHOLDER] AresBoss — hitbox + HP bar
        _hitbox_rect(surface, draw_r, GOLD, f"ARES [{self.state}]")

        bw  = draw_r.width
        bx  = draw_r.x
        by  = draw_r.bottom + 6
        pygame.draw.rect(surface, (40, 20, 0),  (bx, by, bw, 7))
        pygame.draw.rect(surface, GOLD,          (bx, by, int(bw * self.health / self.max_health), 7))

        self.draw_speech(surface, draw_r.centerx, draw_r.top - 60)


# ─── VASİL BOSS (entities) ──────────────────────────────────────────────────
class VasilBoss(EnemyBase):
    def __init__(self, x, y):
        super().__init__()
        self.width, self.height = 180, 180
        self.x, self.y = x, y
        self.rect       = pygame.Rect(x, y, self.width, self.height)
        self.health     = 3000
        self.max_health = 3000
        self.state      = "IDLE"; self.timer = 0; self.angle_cnt = 0

    def update(self, camera_speed, dt=0.016, player_pos=None):
        if not self.is_active: return
        self.update_speech(dt)
        self.rect.y = self.y + math.sin(pygame.time.get_ticks() * 0.002) * 30
        px, py = 0, 0
        if player_pos: px, py = (player_pos if isinstance(player_pos, tuple) else player_pos.center)
        self.timer += dt

        if self.state == "IDLE":
            if self.timer > 2.0:
                self.timer = 0; r = random.random()
                if r < 0.4:   self.state = "SPIRAL"
                elif r < 0.7: self.state = "WALL"
                else:         self.state = "SNIPER"
                self.speech_text    = "VERİ TEMİZLİĞİ."
                self.speech_duration = 1.0

        elif self.state == "SPIRAL":
            self.angle_cnt += 0.5
            if self.timer % 0.1 < 0.02:
                for i in range(4):
                    angle = self.angle_cnt + (i * (math.pi / 2))
                    tx = self.rect.centerx + math.cos(angle) * 1000
                    ty = self.rect.centery + math.sin(angle) * 1000
                    p  = EnemyProjectile(self.rect.centerx, self.rect.centery, tx, ty, speed=8)
                    p.color = (0, 255, 255)
                    self.spawn_queue.append(p)
            if self.timer > 3.0: self.state = "IDLE"; self.timer = 0

        elif self.state == "WALL":
            if self.timer < 0.1:
                for i in range(5):
                    p = EnemyProjectile(self.rect.left - 50, self.rect.top + (i * 40),
                                        -1000, self.rect.top + (i * 40), speed=10)
                    p.color = (255, 255, 255)
                    self.spawn_queue.append(p)
            if self.timer > 1.0: self.state = "IDLE"; self.timer = 0

        elif self.state == "SNIPER":
            if (0.5 < self.timer < 0.6) or (0.8 < self.timer < 0.9):
                p = EnemyProjectile(self.rect.centerx, self.rect.centery, px, py, speed=20)
                p.color = (255, 0, 0)
                self.spawn_queue.append(p)
            if self.timer > 1.1: self.state = "IDLE"; self.timer = 0

    def draw(self, surface, camera_offset=(0, 0), theme=None):
        if not self.is_active: return
        ox, oy  = camera_offset
        BLOOD   = (180, 0, 20)
        draw_r  = self.rect.move(ox, oy)

        # [PLACEHOLDER] VasilBoss — hitbox + HP bar
        _hitbox_rect(surface, draw_r, BLOOD, f"VASİL [{self.state}]")

        bw  = draw_r.width
        bx  = draw_r.x
        by  = draw_r.top - 14
        pygame.draw.rect(surface, (50, 0, 10), (bx, by, bw, 7))
        pygame.draw.rect(surface, BLOOD,       (bx, by, int(bw * self.health / self.max_health), 7))

        self.draw_speech(surface, draw_r.centerx, draw_r.top - 35)


# ─── NEXUS BOSS (entities) ──────────────────────────────────────────────────
class NexusBoss(EnemyBase):
    def __init__(self, x, y):
        super().__init__()
        self.width, self.height = 200, 300
        self.x, self.y = x, y
        self.rect        = pygame.Rect(x, y, self.width, self.height)
        self.health      = 2000
        self.max_health  = 2000
        self.state       = "IDLE"; self.timer = 0; self.float_offset = 0

    def update(self, camera_speed, dt=0.016, player_pos=None):
        if not self.is_active: return
        self.update_speech(dt)
        self.timer += dt
        self.float_offset = math.sin(pygame.time.get_ticks() * 0.001) * 20
        self.rect.y = self.y + self.float_offset
        px, py = 0, 0
        if player_pos: px, py = (player_pos if isinstance(player_pos, tuple) else player_pos.center)

        if self.state == "IDLE":
            if self.timer > 2.5:
                self.timer = 0; r = random.random()
                if r < 0.4:   self.state = "SCATTER"
                elif r < 0.7: self.state = "HOMING"
                else:         self.state = "SWEEP"
                self.speech_text     = "HEDEF KİLİTLENDİ."
                self.speech_duration = 1.0

        elif self.state == "SCATTER":
            if self.timer < 0.1:
                for i in range(-2, 3):
                    p = EnemyProjectile(self.rect.centerx, self.rect.centery,
                                        px, py + (i * 100), speed=12)
                    p.color = (255, 0, 255)
                    self.spawn_queue.append(p)
            if self.timer > 1.0: self.state = "IDLE"; self.timer = 0

        elif self.state == "HOMING":
            if self.timer < 0.1:
                p = EnemyProjectile(self.rect.centerx, self.rect.top + 50, px, py, speed=10)
                p.rect.inflate_ip(10, 10); p.color = (255, 50, 50)
                self.spawn_queue.append(p)
            if self.timer > 1.5: self.state = "IDLE"; self.timer = 0

        elif self.state == "SWEEP":
            cnt = int(self.timer / 0.2)
            if cnt < 5 and (self.timer % 0.2 < 0.05):
                yp = self.rect.bottom - (cnt * 60)
                p  = EnemyProjectile(self.rect.left, yp, -1000, yp, speed=15)
                p.color = (255, 255, 0); p.rect.height = 10; p.rect.width = 40
                self.spawn_queue.append(p)
            if self.timer > 2.0: self.state = "IDLE"; self.timer = 0

    def draw(self, surface, camera_offset=(0, 0), theme=None):
        if not self.is_active: return
        ox, oy  = camera_offset
        neon    = (255, 0, 100)
        draw_r  = self.rect.move(ox, oy)

        # [PLACEHOLDER] NexusBoss — hitbox + HP
        hp_pct = self.health / self.max_health
        _hitbox_rect(surface, draw_r, neon, f"NEXUS [{self.state}]", f"HP {int(hp_pct*100)}%")

        # Yan HP şeridi
        fh = int(draw_r.height * hp_pct)
        pygame.draw.rect(surface, (50, 0, 0),  (draw_r.x - 12, draw_r.y, 8, draw_r.height))
        pygame.draw.rect(surface, neon,         (draw_r.x - 12, draw_r.bottom - fh, 8, fh))

        self.draw_speech(surface, draw_r.centerx, draw_r.top - 40)


# ─── PARALLAX ARKA PLAN ──────────────────────────────────────────────────────
class ParallaxBackground:
    """
    Sonsuz döngülü çok katmanlı parallax arka plan.

    Her katman ayrı bir PNG dosyasıdır.  Kamera hızıyla çarpılmış
    speed_mult oranında kaydırılır.  PNG ekran genişliğinden dar olsa
    bile boşluk oluşmaz — iki kopya yan yana blit edilir.

    Kullanım (init_game içinde):
        bg_far  = ParallaxBackground("assets/backgrounds/gutter_far.png",  0.15)
        bg_mid  = ParallaxBackground("assets/backgrounds/gutter_mid.png",  0.40)
        bg_near = ParallaxBackground("assets/backgrounds/gutter_near.png", 0.75)

    Oyun döngüsünde (update → draw sırası önemli):
        for layer in [bg_far, bg_mid, bg_near]:
            layer.update(camera_speed)
            layer.draw(game_canvas)

    Dosya bulunamazsa hiçbir şey çizmez (güvenli fallback).
    """

    def __init__(self, image_path: str, speed_mult: float = 0.3,
                 y_offset: int = 0):
        """
        image_path  : PNG dosya yolu
        speed_mult  : kamera hızı ile çarpılacak ilerleme katsayısı
                      (0.0 = sabit, 1.0 = platform hızıyla aynı)
        y_offset    : dikey konumlama (varsayılan 0 = üst kenar)
        """
        self.speed_mult = speed_mult
        self.y_offset   = y_offset
        self._x: float  = 0.0

        raw = get_image(image_path)
        # 1×1 placeholder → görüntü yok demektir
        if raw.get_width() > 1:
            # Ekran yüksekliğine göre dikey ölçekle (en boy korunur)
            ratio   = LOGICAL_HEIGHT / raw.get_height()
            new_w   = max(LOGICAL_WIDTH, int(raw.get_width() * ratio))
            self._image = pygame.transform.scale(raw, (new_w, LOGICAL_HEIGHT))
        else:
            self._image = None

    # ------------------------------------------------------------------ #
    def update(self, camera_speed: float):
        """Her karede camera_speed × speed_mult kadar sola kaydır."""
        if self._image is None:
            return
        self._x -= camera_speed * self.speed_mult
        # Sonsuz döngü: resim tam olarak solun dışına çıktığında sıfırla
        img_w = self._image.get_width()
        if self._x <= -img_w:
            self._x += img_w

    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface):
        """İki kopya yan yana blit ederek kesintisiz döngü sağlar."""
        if self._image is None:
            return
        img_w = self._image.get_width()
        x0    = int(self._x)
        surface.blit(self._image, (x0,              self.y_offset))
        surface.blit(self._image, (x0 + img_w,      self.y_offset))
        # İkinci kopya yetmezse (çok geniş atlama) üçüncü kopya
        if x0 + img_w < LOGICAL_WIDTH:
            surface.blit(self._image, (x0 + img_w * 2, self.y_offset))


class BlankBackground:
    """
    Geriye-dönük uyumluluk için tutulan boş arka plan.
    Artık yeni kodda ParallaxBackground kullanılmalı.
    Pixel art dosyası gelene kadar temiz arka plan bırakır.
    """
    def __init__(self, screen_width=0, screen_height=0):
        pass

    def update(self, camera_speed):
        pass

    def draw(self, surface):
        pass


# ─── HEALTH ORB (Can Küresi) ─────────────────────────────────────────────────
class HealthOrb(pygame.sprite.Sprite):
    """
    Düşmanlar öldüğünde %15-20 ihtimalle düşen toplanabilir can küresi.
    Oyuncu üzerine basınca player_hp.heal() tetiklenir.
    """
    HEAL_AMOUNT = 25

    def __init__(self, x, y):
        super().__init__()
        self.rect   = pygame.Rect(x - 8, y - 8, 16, 16)
        self.vy     = -4.0          # Küre yukarı fırlar, sonra düşer
        self.timer  = 0.0
        self.life   = 8.0           # 8 saniye sonra kaybolur
        self._pulse = 0.0

    def update(self, camera_speed, dt=0.016, player_pos=None):
        self.rect.x -= camera_speed
        self.vy     += 0.3          # Yerçekimi
        self.rect.y += int(self.vy)
        if self.vy > 0 and self.rect.bottom >= LOGICAL_HEIGHT - 80:
            self.rect.bottom = LOGICAL_HEIGHT - 80
            self.vy = -1.0          # Hafif sekme
        self.life   -= dt
        self._pulse += dt * 5
        if self.life <= 0 or self.rect.right < 0:
            self.kill()

    def draw(self, surface, camera_offset=(0, 0), theme=None):
        ox, oy = camera_offset
        cx = self.rect.centerx + ox
        cy = self.rect.centery + oy
        radius = 8 + int(math.sin(self._pulse) * 2)
        # Dış parıltı
        glow = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (0, 255, 80, 60), (radius * 2, radius * 2), radius * 2)
        surface.blit(glow, (cx - radius * 2, cy - radius * 2))
        # Küre
        pygame.draw.circle(surface, (0, 220, 80),  (cx, cy), radius)
        pygame.draw.circle(surface, (150, 255, 180), (cx - 2, cy - 2), radius // 3)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), radius, 1)

# ─── OYUNCU MERMİSİ (ALTIPATAR) ─────────────────────────────────────────────
class PlayerProjectile(pygame.sprite.Sprite):
    """
    Oyuncunun altıpatar reviolveriyle ateşlediği mermi.

    Oluşturma (main.py içinde):
        proj = PlayerProjectile(player_x + 15, player_y + 15, player_direction)
        all_player_projectiles.add(proj)

    Mermi yatay düz bir çizgide ilerler; ekran dışına çıkınca kendini yok eder.
    Çarpışma tespiti main.py içinde groupcollide ile yapılır.

    Çizim: [PLACEHOLDER] küçük parlak dikdörtgen.
    [TODO - PIXEL ART]: bullet.png ile değiştir.
    """

    # Renk sabitleri
    _COL_CORE  = (255, 240, 100)   # Parlak sarı merkez
    _COL_GLOW  = (255, 160,  30)   # Turuncu parıltı
    _COL_TRAIL = (255, 200,  60, 80)  # Iz rengi (alfa)

    def __init__(self, x: float, y: float, direction: int):
        """
        x, y        : Merminin başlangıç merkez koordinatları.
        direction   : +1 sağa, -1 sola.
        """
        super().__init__()
        self.rect      = pygame.Rect(int(x) - 4, int(y) - 3, 12, 6)
        self.vx        = direction * PLAYER_BULLET_SPEED
        self.direction = direction

        # İz için önceki konumları tut (son 4 kare)
        self._trail: list = [(self.rect.centerx, self.rect.centery)] * 4

    # ------------------------------------------------------------------
    def update(self, camera_speed=0, dt: float = 0.016):
        """Mermiyi hareket ettir; ekran dışına çıkınca kendini yok et."""
        # İz listesini güncelle
        self._trail.append((self.rect.centerx, self.rect.centery))
        if len(self._trail) > 4:
            self._trail.pop(0)

        self.rect.x += int(self.vx)

        # Ekran dışı kontrolü
        if self.rect.left > LOGICAL_WIDTH or self.rect.right < 0:
            self.kill()

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera_offset=(0, 0)):
        """[PLACEHOLDER] Küçük parlak dikdörtgen + hafif iz çizgisi."""
        ox, oy = camera_offset
        draw_r = self.rect.move(ox, oy)

        # İz (trailing glow)
        for i, (tx, ty) in enumerate(self._trail):
            alpha = int(60 * (i + 1) / len(self._trail))
            trail_s = pygame.Surface((8, 4), pygame.SRCALPHA)
            trail_s.fill((*self._COL_GLOW, alpha))
            surface.blit(trail_s, (tx + ox - 4, ty + oy - 2))

        # Dış parıltı
        glow_s = pygame.Surface((draw_r.width + 8, draw_r.height + 8), pygame.SRCALPHA)
        glow_s.fill((*self._COL_GLOW, 80))
        surface.blit(glow_s, (draw_r.x - 4, draw_r.y - 4))

        # Mermi gövdesi
        pygame.draw.rect(surface, self._COL_GLOW,  draw_r)
        # Parlak merkez şeridi
        core_r = pygame.Rect(draw_r.x + 2, draw_r.y + 1, draw_r.width - 4, draw_r.height - 2)
        pygame.draw.rect(surface, self._COL_CORE, core_r)


# ─── MALİKANE: KİLİTLİ KAPI ────────────────────────────────────────────────
class Door:
    """
    Kilitli kapı — oyuncunun geçmesini engelleyen çarpışma nesnesi.
    Sadece manor_stealth bölümlerinde kullanılır.

    Kullanım (main.py / init_game içinde):
        door = Door(x=1300, y=600, width=18, height=190, door_id="door_library_to_bedroom")
        manor_doors.append(door)

    Kilit açma:
        door.unlock()   → self.active = False, çarpışma ve çizim devre dışı kalır.

    Çarpışma (main.py PLAYING loop):
        if door.active and player_rect.colliderect(door.rect):
            if old_x + 15 < door.rect.centerx:
                player_x = float(door.rect.left - 30)
            else:
                player_x = float(door.rect.right)

    Çizim (main.py step 5b):
        door.draw(game_canvas, camera_offset=(_manor_draw_ox, _manor_draw_oy))
    """

    _COL_LOCKED_FILL   = (100, 55, 20)     # Koyu kahve dolgu
    _COL_LOCKED_BORDER = (180, 120, 40)    # Altın çerçeve
    _COL_LOCK_ICON     = (255, 200, 60)    # Kilit simgesi sarısı
    _COL_LABEL         = (255, 220, 120)   # Etiket metni

    def __init__(self, x: int, y: int, width: int, height: int, door_id: str):
        self.rect    = pygame.Rect(x, y, width, height)
        self.door_id = door_id
        self.locked  = True
        self.active  = True   # False → çarpışma + çizim yok

    def unlock(self):
        """Kapıyı aç: çarpışma ve çizim tamamen devre dışı."""
        self.locked = False
        self.active = False

    def draw(self, surface: pygame.Surface, camera_offset=(0, 0)):
        """Sadece active=True iken çizilir."""
        if not self.active:
            return
        ox, oy = camera_offset
        draw_r = self.rect.move(ox, oy)

        # Yarı saydam kahverengi dolgu
        s = pygame.Surface((draw_r.width, draw_r.height), pygame.SRCALPHA)
        s.fill((*self._COL_LOCKED_FILL, 220))
        surface.blit(s, draw_r.topleft)

        # Altın çerçeve
        pygame.draw.rect(surface, self._COL_LOCKED_BORDER, draw_r, 3)

        # Dikey tahta çizgileri (kapı görünümü)
        for _i in range(1, 3):
            _lx = draw_r.x + (_i * draw_r.width // 3)
            pygame.draw.line(surface, self._COL_LOCKED_BORDER,
                             (_lx, draw_r.top + 4), (_lx, draw_r.bottom - 4), 1)

        # Kilit simgesi — kapının ortasında
        cx = draw_r.centerx
        cy = draw_r.centery
        # Gövde (dikdörtgen)
        lock_body = pygame.Rect(cx - 6, cy, 12, 9)
        pygame.draw.rect(surface, self._COL_LOCK_ICON, lock_body)
        # Kanca (yarım daire)
        pygame.draw.arc(surface, self._COL_LOCK_ICON,
                        pygame.Rect(cx - 5, cy - 7, 10, 10),
                        0, math.pi, 2)

        # "KİLİTLİ" etiketi — dikey (kapı dar olduğu için döndürülür)
        _font = pygame.font.Font(None, 15)
        _lbl  = _font.render("KİLİTLİ", True, self._COL_LABEL)
        _lbl  = pygame.transform.rotate(_lbl, 90)
        surface.blit(_lbl, (draw_r.x + 1, draw_r.y + 6))


# ─── MALİKANE: ETKİLEŞİMLİ TERMİNAL / PARŞÖMEN ────────────────────────────
class InteractiveTerminal:
    """
    Etkileşimli nesne — E tuşuyla aktive edilir, ardından devre dışı kalır.

    terminal_id değerine göre main.py farklı mantık çalıştırır:
        "security_terminal"  →  kütüphane → efendi dairesi kapısını açar
        "safe_scroll"        →  efendi dairesi → kasa odası kapısını açar

    Kullanım (main.py / init_game içinde):
        term = InteractiveTerminal(
            x=760, y=735, width=40, height=50,
            terminal_id="security_terminal",
            prompt_text="E: Terminali Hackle"
        )
        manor_terminals.append(term)

    Etkileşim (main.py E tuşu):
        if term.try_interact(player_x + 15, player_y + 15, reach=100):
            # terminal_id'ye göre kapı aç / görev tamamla

    Çizim (main.py step 5b):
        term.draw(game_canvas, player_x + 15, player_y + 15,
                  camera_offset=(_manor_draw_ox, _manor_draw_oy))
    """

    _COL_TERM_FILL     = (0,   50,  60)    # Terminalde koyu cyan
    _COL_TERM_BORDER   = (0,  200, 180)    # Parlak cyan çerçeve
    _COL_SCROLL_FILL   = (50,  40,   0)    # Parşömende koyu sarı
    _COL_SCROLL_BORDER = (220, 180,  50)   # Altın çerçeve
    _COL_PROMPT_TERM   = (0,  255, 220)    # Terminal ipucu rengi
    _COL_PROMPT_SCROLL = (255, 220,  80)   # Parşömen ipucu rengi
    _PROXIMITY_RADIUS  = 120               # İpucunun göründüğü mesafe (px)

    def __init__(self, x: int, y: int, width: int, height: int,
                 terminal_id: str, prompt_text: str = "E: Etkileşim"):
        self.rect        = pygame.Rect(x, y, width, height)
        self.terminal_id = terminal_id
        self.prompt_text = prompt_text
        self.activated   = False
        self._pulse_t    = 0.0   # 0..60 arası döngü (kare sayacı)

    def try_interact(self, px: float, py: float, reach: float = 100) -> bool:
        """
        Oyuncu yeterince yakınsa ve henüz aktive edilmemişse True döndürür,
        terminali aktive eder (bir daha çalışmaz).
        """
        if self.activated:
            return False
        dist = math.sqrt((px - self.rect.centerx) ** 2 +
                         (py - self.rect.centery) ** 2)
        if dist < reach:
            self.activated = True
            return True
        return False

    def draw(self, surface: pygame.Surface,
             player_px: float, player_py: float,
             camera_offset=(0, 0)):
        """Sadece activated=False iken çizilir. Pulsing parıltı efekti içerir."""
        if self.activated:
            return

        self._pulse_t = (self._pulse_t + 1) % 60
        pulse = abs(math.sin(self._pulse_t * math.pi / 30))   # 0..1 parlama

        ox, oy = camera_offset
        draw_r = self.rect.move(ox, oy)

        # Terminal mi, parşömen mi?
        is_scroll    = (self.terminal_id == "safe_scroll")
        fill_col     = self._COL_SCROLL_FILL   if is_scroll else self._COL_TERM_FILL
        border_col   = self._COL_SCROLL_BORDER if is_scroll else self._COL_TERM_BORDER
        prompt_col   = self._COL_PROMPT_SCROLL if is_scroll else self._COL_PROMPT_TERM

        # Pulsing dolgu (alpha 160–255)
        alpha = int(160 + 95 * pulse)
        s = pygame.Surface((draw_r.width, draw_r.height), pygame.SRCALPHA)
        s.fill((*fill_col, alpha))
        surface.blit(s, draw_r.topleft)

        # Çerçeve — parlama zirvesinde kalın
        thickness = 3 if pulse > 0.5 else 2
        pygame.draw.rect(surface, border_col, draw_r, thickness)

        # İkon — terminal: ekran+klavye, parşömen: rulo çizgileri
        cx, cy = draw_r.centerx, draw_r.centery
        if is_scroll:
            # Rulo: 3 yatay çizgi
            for _dy in (-5, 0, 5):
                pygame.draw.line(surface, border_col,
                                 (cx - 10, cy + _dy), (cx + 10, cy + _dy), 2)
            # Rulo uçları (dikey)
            pygame.draw.line(surface, border_col, (cx - 10, cy - 7), (cx - 10, cy + 7), 2)
            pygame.draw.line(surface, border_col, (cx + 10, cy - 7), (cx + 10, cy + 7), 2)
        else:
            # Terminal ekranı
            pygame.draw.rect(surface, border_col,
                             pygame.Rect(cx - 10, cy - 9, 20, 13), 2)
            # İmleç (yanıp söner)
            if self._pulse_t < 30:
                pygame.draw.rect(surface, border_col,
                                 pygame.Rect(cx - 7, cy - 5, 5, 7))
            # Klavye (iki küçük tuş)
            pygame.draw.rect(surface, border_col, pygame.Rect(cx - 7, cy + 6, 5, 3))
            pygame.draw.rect(surface, border_col, pygame.Rect(cx + 2, cy + 6, 5, 3))

        # Yakınlık ipucu (oyuncu _PROXIMITY_RADIUS içindeyse görünür)
        dist = math.sqrt((player_px - self.rect.centerx) ** 2 +
                         (player_py - self.rect.centery) ** 2)
        if dist < self._PROXIMITY_RADIUS:
            _font = pygame.font.Font(None, 20)
            hint  = _font.render(self.prompt_text, True, prompt_col)
            hx    = draw_r.centerx - hint.get_width() // 2
            hy    = draw_r.top - 24
            # İpucu arka planı (okunabilirlik için)
            bg = pygame.Surface((hint.get_width() + 8, hint.get_height() + 4), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 170))
            surface.blit(bg, (hx - 4, hy - 2))
            surface.blit(hint, (hx, hy))