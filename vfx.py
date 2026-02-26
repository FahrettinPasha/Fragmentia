import pygame
import math
import random
from settings import *

# ============================================================
#  VFX PLACEHOLDER MODÜLÜ
#
#  Tüm görsel efektler PLACEHOLDER modunda çalışıyor.
#  Glow, multi-layer çizim, karmaşık parçacık hesapları kaldırıldı.
#
#  [TODO - PIXEL ART]: Her sınıfın draw() metoduna sprite veya
#  animasyon karesi entegrasyonu yapılacak.
#
#  API ve update() mantığı korundu — sadece draw() sadeleştirildi.
# ============================================================


class LightningBolt(pygame.sprite.Sprite):
    """
    PLACEHOLDER: Yıldırım efekti.
    [TODO - PIXEL ART]: Tek düz çizgi -> Animasyonlu sprite ile değiştir.
    """
    def __init__(self, start_x, start_y, end_x, end_y, color, life=15, displace=15):
        super().__init__()
        self.color = color
        self.life = life
        self.initial_life = life
        self.alpha = 255
        self.segments = [(start_x, start_y), (end_x, end_y)]
        self.vx = 0
        self.vy = 0

    def update(self, camera_speed):
        self.segments = [(x - camera_speed + self.vx, y + self.vy) for x, y in self.segments]
        self.vy += 0.5
        self.life -= 1
        self.alpha = int(255 * max(0, self.life / self.initial_life))
        if self.life <= 0:
            self.kill()

    def draw(self, surface):
        if self.life > 0 and len(self.segments) >= 2:
            pygame.draw.lines(surface, self.color, False, self.segments, 2)


class FlameSpark(pygame.sprite.Sprite):
    """
    PLACEHOLDER: Ateş kıvılcımı.
    [TODO - PIXEL ART]: Küçük dolu daire -> Sprite ile değiştir.
    """
    def __init__(self, x, y, angle, speed, base_color, life=40, size=8):
        super().__init__()
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.base_color = base_color
        self.life = life
        self.initial_life = life
        self.size = size

    def update(self, camera_speed):
        self.x -= camera_speed
        self.vy += 0.15
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.97
        self.vy *= 0.97
        self.life -= 1
        if self.life <= 0:
            self.kill()

    def draw(self, surface):
        if self.life > 0:
            alpha = int(255 * max(0, self.life / self.initial_life))
            size = max(2, int(self.size * (self.life / self.initial_life)))
            pygame.draw.circle(surface, self.base_color, (int(self.x), int(self.y)), size)


class Shockwave(pygame.sprite.Sprite):
    """
    PLACEHOLDER: Şok dalgası — tek genişleyen halka.
    [TODO - PIXEL ART]: Sprite animasyonuyla değiştir.
    """
    def __init__(self, x, y, color, max_radius=150, width=8, speed=10, rings=3):
        super().__init__()
        self.x, self.y = x, y
        self.color = color
        self.max_radius = max_radius
        self.radius = 5
        self.speed = speed * 1.5
        self.alpha = 255

    def update(self, camera_speed):
        self.x -= camera_speed
        self.radius += self.speed
        progress = self.radius / self.max_radius
        self.alpha = int(255 * max(0, 1 - progress))
        if self.radius >= self.max_radius:
            self.kill()

    def draw(self, surface):
        if self.alpha > 5:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.radius), 2)


class SpeedLine(pygame.sprite.Sprite):
    """
    PLACEHOLDER: Hız çizgisi — tek düz çizgi.
    [TODO - PIXEL ART]: Hareket blur sprite'ıyla değiştir.
    """
    def __init__(self, x, y, angle, speed, color):
        super().__init__()
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed * 2.0
        self.vy = math.sin(angle) * speed * 2.0
        self.color = color
        self.life = 25
        self.initial_life = 25

    def update(self, camera_speed):
        self.x -= camera_speed
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.life <= 0:
            self.kill()

    def draw(self, surface):
        if self.life > 0:
            end_x = self.x - self.vx * 3
            end_y = self.y - self.vy * 3
            pygame.draw.line(surface, self.color,
                             (int(self.x), int(self.y)),
                             (int(end_x), int(end_y)), 1)


class GhostTrail(pygame.sprite.Sprite):
    """
    PLACEHOLDER: Hayalet iz — saydam dikdörtgen.
    [TODO - PIXEL ART]: Oyuncu sprite'ının soluk kopyası ile değiştir.
    """
    def __init__(self, x, y, color, life=20, size=15):
        super().__init__()
        self.x, self.y = x, y
        self.color = color
        self.life = life
        self.initial_life = life
        self.size = size

    def update(self, camera_speed):
        self.x -= camera_speed
        self.life -= 1
        if self.life <= 0:
            self.kill()

    def draw(self, surface):
        if self.life > 0:
            alpha = int(120 * (self.life / self.initial_life))
            # Oyuncuyla aynı dikdörtgen oranı (utils.draw_animated_player referansı)
            rect = pygame.Rect(int(self.x) - self.size,
                               int(self.y) - int(self.size * 2.5),
                               self.size * 2,
                               int(self.size * 2.5))
            try:
                s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                s.fill((*self.color, alpha))
                surface.blit(s, rect.topleft)
            except:
                pass


class EnergyOrb(pygame.sprite.Sprite):
    """
    PLACEHOLDER: Enerji topu — dolu daire.
    [TODO - PIXEL ART]: Toplanabilir item sprite'ıyla değiştir.
    """
    def __init__(self, x, y, color, size=10, life=30):
        super().__init__()
        self.x, self.y = x, y
        self.color = color
        self.size = size
        self.initial_size = size
        self.life = life
        self.initial_life = life

    def update(self, camera_speed):
        self.x -= camera_speed
        self.life -= 1
        if self.life <= 0:
            self.kill()

    def draw(self, surface):
        if self.life > 0:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.size)
            pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.size, 1)


class ParticleExplosion(pygame.sprite.Sprite):
    """
    PLACEHOLDER: Patlama efekti — küçük dolu kareler.
    [TODO - PIXEL ART]: Animasyonlu sprite veya sprite sheet ile değiştir.
    """
    def __init__(self, x, y, color, count=20, size_range=(3, 8), life_range=(20, 40)):
        super().__init__()
        self.particles = []
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(3, 8)
            size = random.uniform(size_range[0], size_range[1])
            life = random.randint(life_range[0], life_range[1])
            self.particles.append({
                'x': x, 'y': y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'size': size,
                'initial_size': size,
                'life': life,
                'initial_life': life,
                'color': color,
            })
        self.alive = True

    def update(self, camera_speed):
        if not self.alive:
            return
        alive_count = 0
        for p in self.particles:
            p['x'] -= camera_speed
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.15
            p['vx'] *= 0.94
            p['vy'] *= 0.94
            p['life'] -= 1
            if p['life'] > 0:
                alive_count += 1
        if alive_count == 0:
            self.kill()
            self.alive = False

    def draw(self, surface):
        for p in self.particles:
            if p['life'] > 0:
                size = max(2, int(p['size'] * (p['life'] / p['initial_life'])))
                rect = pygame.Rect(int(p['x']), int(p['y']), size, size)
                pygame.draw.rect(surface, p['color'], rect)


class ScreenFlash(pygame.sprite.Sprite):
    """Ekran flaşı — değişmedi, saf renk overlay."""
    def __init__(self, color, intensity=100, duration=10):
        super().__init__()
        self.color = color
        self.intensity = intensity
        self.duration = duration
        self.life = duration
        self.alpha = intensity

    def update(self, camera_speed):
        self.life -= 1
        self.alpha = int(self.intensity * (self.life / self.duration))
        if self.life <= 0:
            self.kill()

    def draw(self, surface):
        if self.alpha > 0:
            flash_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            flash_surf.fill((*self.color, self.alpha))
            surface.blit(flash_surf, (0, 0))


def draw_cyber_grid(surface, time_ms):
    """
    PLACEHOLDER: Hareketli ızgara kaldırıldı.
    [TODO - PIXEL ART]: Arkaplan tileset/sprite ile değiştirilecek.
    Şimdilik hiçbir şey çizmiyor — arkaplan düz tema rengiyle dolu.
    """
    pass  # Kasıtlı boş bırakıldı


class VFXManager:
    def __init__(self):
        self.group = pygame.sprite.Group()

    def add(self, sprite):
        self.group.add(sprite)

    def update(self, camera_speed):
        for sprite in self.group:
            sprite.update(camera_speed)

    def draw(self, surface):
        for sprite in self.group:
            if hasattr(sprite, 'draw'):
                sprite.draw(surface)
            else:
                surface.blit(sprite.image, sprite.rect)


class SavedSoul(pygame.sprite.Sprite):
    """
    PLACEHOLDER: Kurtarılan ruh efekti — küçük parlak daire + yukarı yüzen metin.
    [TODO - PIXEL ART]: Melek / ruh animasyonlu sprite ile değiştir.
    """
    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y
        self.life = 60
        self.initial_life = 60
        self.vy = -2
        self.size = 10
        self.wobble = random.uniform(0, 6.28)

    def update(self, camera_speed):
        self.life -= 1
        self.y += self.vy
        self.x += math.sin(self.wobble + self.life * 0.1) * 2
        self.x -= camera_speed
        if self.life <= 0:
            self.kill()

    def draw(self, surface):
        if self.life > 0:
            alpha = int(255 * (self.life / self.initial_life))
            # Gövde: altın sarısı dolu daire
            pygame.draw.circle(surface, (255, 215, 0), (int(self.x), int(self.y)), self.size)
            # Çerçeve
            pygame.draw.circle(surface, (255, 255, 200), (int(self.x), int(self.y)), self.size, 2)