import pygame
import random
import math
from settings import LOGICAL_HEIGHT, LOGICAL_WIDTH

# Boss Sabitleri
BULLET_SPEED = 8
BOSS_HEALTH = 1000
BOSS_DAMAGE = 10
BOSS_FIRE_RATE = 60
BOSS_INVULNERABILITY_TIME = 30

# --- BOSS SALDIRI NESNELERİ ---

class BossSpike(pygame.sprite.Sprite):
    def __init__(self, platform, karma):
        super().__init__()
        self.platform = platform
        self.karma = karma
        
        margin = 5
        self.width = platform.width - (margin * 2)
        self.height = 130 
        
        self.x = platform.rect.left + margin
        self.y = platform.rect.top - self.height
        
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        
        self.timer = 0
        self.warning_duration = 25
        self.active_duration = 30
        self.state = 'WARNING' 
        
    def update(self, camera_speed):
        self.rect.x -= camera_speed
        self.x -= camera_speed
        
        self.timer += 1
        
        if self.state == 'WARNING':
            if self.timer >= self.warning_duration:
                self.state = 'ACTIVE'
                self.timer = 0 
        elif self.state == 'ACTIVE':
            if self.timer >= self.active_duration:
                self.state = 'DONE'
                self.kill() 
    
    def draw(self, surface):
        # WARNING: yanıp sönen ince çizgi + yön oku (gameplay açısından gerekli)
        if self.state == 'WARNING':
            if (self.timer // 4) % 2 == 0:
                warn_color = (0, 255, 255) if self.karma < 0 else (200, 0, 255)
                pygame.draw.rect(surface, warn_color, (self.rect.x, self.rect.bottom - 4, self.width, 4))
                arrow_count = max(1, self.width // 50)
                for i in range(arrow_count):
                    ax = self.rect.x + (i * 50) + 25
                    ay = self.rect.bottom - 14
                    pygame.draw.polygon(surface, warn_color,
                                        [(ax, ay - 8), (ax - 5, ay), (ax + 5, ay)])
        elif self.state == 'ACTIVE':
            # [PLACEHOLDER] Kazık aktif — düz dikdörtgen + kenar
            progress    = min(1.0, self.timer / 4.0)
            current_h   = int(self.height * progress)
            col         = (0, 200, 220) if self.karma < 0 else (160, 0, 240)
            base_y      = self.rect.bottom
            spike_rect  = pygame.Rect(self.rect.x, base_y - current_h, self.width, current_h)
            pygame.draw.rect(surface, (10, 10, 15), spike_rect)
            pygame.draw.rect(surface, col, spike_rect, 2)

class BossLightning(pygame.sprite.Sprite):
    def __init__(self, x, karma):
        super().__init__()
        self.x = x
        self.karma = karma
        self.width = 60
        self.height = LOGICAL_HEIGHT
        self.rect = pygame.Rect(self.x - self.width//2, 0, self.width, self.height)
        self.timer = 0
        self.warning_duration = 30
        self.active_duration = 10
        self.state = 'WARNING'
        
    def update(self, camera_speed):
        self.x -= camera_speed
        self.rect.x -= camera_speed
        self.timer += 1
        
        if self.state == 'WARNING':
            if self.timer >= self.warning_duration:
                self.state = 'ACTIVE'
                self.timer = 0
        elif self.state == 'ACTIVE':
            if self.timer >= self.active_duration:
                self.state = 'DONE'
                self.kill()
                
    def draw(self, surface):
        warn_col = (0, 255, 255) if self.karma < 0 else (200, 0, 255)
        if self.state == 'WARNING':
            if (self.timer // 5) % 2 == 0:
                # İnce uyarı çizgisi + ! işareti
                pygame.draw.line(surface, (*warn_col, 80), (self.x, 0), (self.x, LOGICAL_HEIGHT), 1)
                target_rect = pygame.Rect(self.x - 20, LOGICAL_HEIGHT - 60, 40, 20)
                pygame.draw.ellipse(surface, warn_col, target_rect, 2)
                font = pygame.font.Font(None, 30)
                txt  = font.render("!", True, warn_col)
                surface.blit(txt, (self.x - 5, 50))
        elif self.state == 'ACTIVE':
            # [PLACEHOLDER] Aktif yıldırım — düz renkli çizgi
            pygame.draw.line(surface, warn_col, (self.x, 0), (self.x, LOGICAL_HEIGHT), 6)
            pygame.draw.line(surface, (255, 255, 255), (self.x, 0), (self.x, LOGICAL_HEIGHT), 2)

class BossGiantArrow(pygame.sprite.Sprite):
    def __init__(self, x, karma):
        super().__init__()
        self.x = x
        self.karma = karma
        self.width = 150
        self.height = 400
        self.rect = pygame.Rect(x, LOGICAL_HEIGHT, self.width, self.height)
        self.timer = 0
        self.warning_duration = 45
        self.active_duration = 20
        self.state = 'WARNING'
        
    def update(self, camera_speed):
        self.x -= camera_speed
        self.rect.x -= camera_speed
        self.timer += 1
        
        if self.state == 'WARNING':
            if self.timer >= self.warning_duration:
                self.state = 'ACTIVE'
                self.timer = 0
        elif self.state == 'ACTIVE':
            if self.timer >= self.active_duration:
                self.state = 'DONE'
                self.kill()

    def draw(self, surface):
        col = (255, 0, 0) if self.karma < 0 else (150, 0, 255)
        if self.state == 'WARNING':
            if (self.timer // 10) % 2 == 0:
                # Yarı-saydam dikdörtgen + altta bar
                s = pygame.Surface((self.width, LOGICAL_HEIGHT), pygame.SRCALPHA)
                s.fill((*col, 40))
                surface.blit(s, (self.rect.x, 0))
                pygame.draw.rect(surface, col, (self.rect.x, LOGICAL_HEIGHT - 18, self.width, 18))
        elif self.state == 'ACTIVE':
            # [PLACEHOLDER] — dolu renkli dikdörtgen, yükselen şerit
            progress   = min(1.0, self.timer / 5.0)
            h          = int(LOGICAL_HEIGHT * progress)
            draw_rect  = pygame.Rect(self.rect.x, LOGICAL_HEIGHT - h, self.width, h)
            pygame.draw.rect(surface, (10, 10, 15), draw_rect)
            pygame.draw.rect(surface, col,           draw_rect, 3)

class BossOrbitalStrike(pygame.sprite.Sprite):
    def __init__(self, x, y, karma):
        super().__init__()
        self.x = x
        self.y = y
        self.karma = karma
        self.timer = 0
        self.radius = 0
        self.max_radius = 300
        self.state = 'CHARGING'
        self.beams = []
        
    def update(self, camera_speed):
        self.x -= camera_speed
        self.timer += 1
        
        if self.state == 'CHARGING':
            if self.timer < 60:
                self.radius = (self.timer / 60) * 40
            else:
                self.state = 'BLAST'
                self.timer = 0
                for _ in range(random.randint(5, 8)):
                    offset = random.randint(-self.max_radius, self.max_radius)
                    self.beams.append(self.x + offset)
        elif self.state == 'BLAST':
            if self.timer > 20:
                self.kill()
                
    def draw(self, surface):
        # [PLACEHOLDER] Orbital Strike — uyarı dairesi + ışın çizgileri
        col = (0, 220, 220) if self.karma < 0 else (220, 0, 220)
        if self.state == 'CHARGING':
            pygame.draw.circle(surface, col, (int(self.x), int(self.y)), max(1, int(self.radius)), 2)
            target_rect = pygame.Rect(self.x - self.max_radius, LOGICAL_HEIGHT - 18,
                                      self.max_radius * 2, 18)
            pygame.draw.ellipse(surface, col, target_rect, 2)
        elif self.state == 'BLAST':
            pygame.draw.circle(surface, (240, 240, 240), (int(self.x), int(self.y)), 30)
            for bx in self.beams:
                pygame.draw.line(surface, col, (int(self.x), int(self.y)), (int(bx), LOGICAL_HEIGHT), 4)
                pygame.draw.circle(surface, col, (int(bx), LOGICAL_HEIGHT), 20, 2)

    def check_collision(self, player_rect):
        if self.state == 'BLAST':
            for bx in self.beams:
                beam_rect = pygame.Rect(bx - 20, 0, 40, LOGICAL_HEIGHT)
                if beam_rect.colliderect(player_rect):
                    return True
        return False

# --- BOSS SINIFLARI ---

class NexusBoss(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y
        self.health = BOSS_HEALTH
        self.max_health = BOSS_HEALTH
        self.fire_timer = 0
        self.invulnerable_timer = 0
        self.spawn_queue = []
        self.phase = 1

    def update(self, camera_speed, dt, player_pos):
        self.x -= camera_speed
        self.fire_timer += 1
        if self.fire_timer >= BOSS_FIRE_RATE:
            self.fire_timer = 0
            self.shoot(player_pos)
        if self.health <= self.max_health * 0.5 and self.phase == 1:
            self.phase = 2
            self.enter_phase2()

    def shoot(self, player_pos):
        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        dist = max(0.1, math.sqrt(dx*dx + dy*dy))
        dx /= dist
        dy /= dist
        bullet = EnemyBullet(self.x, self.y, dx * BULLET_SPEED, dy * BULLET_SPEED, BOSS_DAMAGE)
        self.spawn_queue.append(bullet)

    def enter_phase2(self):
        global BOSS_FIRE_RATE
        BOSS_FIRE_RATE = max(20, BOSS_FIRE_RATE - 20)

    def draw(self, surface, theme):
        # [PLACEHOLDER] NexusBoss — hitbox + HP bar
        col  = (255, 100, 100) if self.invulnerable_timer > 0 else (255, 0, 100)
        bw   = 80
        rect = pygame.Rect(int(self.x) - bw // 2, int(self.y) - bw // 2, bw, bw)
        s = pygame.Surface((bw, bw), pygame.SRCALPHA)
        s.fill((10, 10, 20, 150))
        surface.blit(s, rect.topleft)
        pygame.draw.rect(surface, col, rect, 2)
        font = pygame.font.Font(None, 18)
        surface.blit(font.render("NEXUS", True, col), (rect.x + 3, rect.y + 3))
        # HP bar
        bar_w = 200
        bar_x = int(self.x) - bar_w // 2
        bar_y = int(self.y) - 50
        pygame.draw.rect(surface, (60, 0, 0),  (bar_x, bar_y, bar_w, 10))
        pygame.draw.rect(surface, col,          (bar_x, bar_y, int(bar_w * max(0, self.health) / self.max_health), 10))
        pygame.draw.rect(surface, col,          (bar_x, bar_y, bar_w, 10), 1)

    def take_damage(self, damage):
        if self.invulnerable_timer <= 0:
            self.health -= damage
            self.invulnerable_timer = BOSS_INVULNERABILITY_TIME
            if self.health <= 0:
                self.kill()

class AresBoss(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y
        self.health = BOSS_HEALTH
        self.max_health = BOSS_HEALTH
        self.fire_timer = 0
        self.invulnerable_timer = 0
        self.spawn_queue = []
        self.phase = 1

    def update(self, camera_speed, dt, player_pos):
        self.x -= camera_speed
        self.fire_timer += 1
        if self.fire_timer >= BOSS_FIRE_RATE:
            self.fire_timer = 0
            self.shoot(player_pos)
        if self.health <= self.max_health * 0.5 and self.phase == 1:
            self.phase = 2
            self.enter_phase2()

    def shoot(self, player_pos):
        for angle in [-0.2, 0, 0.2]:
            dx = player_pos[0] - self.x
            dy = player_pos[1] - self.y
            dist = max(0.1, math.sqrt(dx*dx + dy*dy))
            dx /= dist
            dy /= dist
            new_dx = dx * math.cos(angle) - dy * math.sin(angle)
            new_dy = dx * math.sin(angle) + dy * math.cos(angle)
            bullet = EnemyBullet(self.x, self.y, new_dx * BULLET_SPEED, new_dy * BULLET_SPEED, BOSS_DAMAGE)
            self.spawn_queue.append(bullet)

    def enter_phase2(self):
        global BOSS_FIRE_RATE
        BOSS_FIRE_RATE = max(15, BOSS_FIRE_RATE - 25)

    def draw(self, surface, theme):
        # [PLACEHOLDER] AresBoss — hitbox + HP bar
        col  = (255, 80, 80) if self.invulnerable_timer > 0 else (255, 215, 0)
        bw, bh = 100, 100
        rect   = pygame.Rect(int(self.x) - bw // 2, int(self.y) - bh // 2, bw, bh)
        s = pygame.Surface((bw, bh), pygame.SRCALPHA)
        s.fill((10, 10, 20, 150))
        surface.blit(s, rect.topleft)
        pygame.draw.rect(surface, col, rect, 2)
        font = pygame.font.Font(None, 18)
        surface.blit(font.render("ARES", True, col), (rect.x + 3, rect.y + 3))
        bar_w = 200
        bar_x = int(self.x) - bar_w // 2
        bar_y = int(self.y) - 70
        pygame.draw.rect(surface, (40, 20, 0),  (bar_x, bar_y, bar_w, 10))
        pygame.draw.rect(surface, col,           (bar_x, bar_y, int(bar_w * max(0, self.health) / self.max_health), 10))
        pygame.draw.rect(surface, col,           (bar_x, bar_y, bar_w, 10), 1)

    def take_damage(self, damage):
        if self.invulnerable_timer <= 0:
            self.health -= damage
            self.invulnerable_timer = BOSS_INVULNERABILITY_TIME
            if self.health <= 0:
                self.kill()

class VasilBoss(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y
        self.health = BOSS_HEALTH
        self.max_health = BOSS_HEALTH
        self.fire_timer = 0
        self.invulnerable_timer = 0
        self.spawn_queue = []
        self.phase = 1

    def update(self, camera_speed, dt, player_pos):
        self.x -= camera_speed
        self.fire_timer += 1
        if self.fire_timer >= BOSS_FIRE_RATE:
            self.fire_timer = 0
            self.shoot(player_pos)
        if self.health <= self.max_health * 0.5 and self.phase == 1:
            self.phase = 2
            self.enter_phase2()

    def shoot(self, player_pos):
        angle = self.fire_timer * 0.1
        dx = math.cos(angle)
        dy = math.sin(angle)
        bullet = EnemyBullet(self.x, self.y, dx * BULLET_SPEED, dy * BULLET_SPEED, BOSS_DAMAGE)
        self.spawn_queue.append(bullet)

    def enter_phase2(self):
        global BOSS_FIRE_RATE
        BOSS_FIRE_RATE = max(10, BOSS_FIRE_RATE - 30)

    def draw(self, surface, theme):
        # [PLACEHOLDER] VasilBoss — hitbox + HP bar
        col  = (255, 80, 80) if self.invulnerable_timer > 0 else (180, 0, 200)
        bw, bh = 100, 110
        rect   = pygame.Rect(int(self.x) - bw // 2, int(self.y) - bh // 2, bw, bh)
        s = pygame.Surface((bw, bh), pygame.SRCALPHA)
        s.fill((10, 10, 20, 150))
        surface.blit(s, rect.topleft)
        pygame.draw.rect(surface, col, rect, 2)
        font = pygame.font.Font(None, 18)
        surface.blit(font.render("VASİL", True, col), (rect.x + 3, rect.y + 3))
        bar_w = 200
        bar_x = int(self.x) - bar_w // 2
        bar_y = int(self.y) - 75
        pygame.draw.rect(surface, (50, 0, 10), (bar_x, bar_y, bar_w, 10))
        pygame.draw.rect(surface, col,         (bar_x, bar_y, int(bar_w * max(0, self.health) / self.max_health), 10))
        pygame.draw.rect(surface, col,         (bar_x, bar_y, bar_w, 10), 1)

    def take_damage(self, damage):
        if self.invulnerable_timer <= 0:
            self.health -= damage
            self.invulnerable_timer = BOSS_INVULNERABILITY_TIME
            if self.health <= 0:
                self.kill()

class EnemyBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy, damage):
        super().__init__()
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.radius = 8

    def update(self, camera_speed, dt, player_pos=None):
        self.x += self.vx
        self.y += self.vy
        self.x -= camera_speed
        if self.x < -100 or self.x > LOGICAL_WIDTH + 100 or self.y < -100 or self.y > LOGICAL_HEIGHT + 100:
            self.kill()

    def draw(self, surface, theme):
        # [PLACEHOLDER] Mermi — düz dolu daire + ince kenar
        pygame.draw.circle(surface, (220, 30,  30), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (255, 200,  0), (int(self.x), int(self.y)), self.radius, 1)
class VasilCompanion(pygame.sprite.Sprite):
    """Oyuncuyu takip eden ve düşmanları yok eden Mini-Vasi"""
    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y
        self.target_x = x
        self.target_y = y
        self.float_offset = 0.0
        
        # Saldırı Zamanlayıcıları
        self.laser_timer = 0
        self.spike_timer = 0
        self.shield_timer = 0
        
        # Görsel
        self.size = 20 # Oyuncuyla aynı boyutta (biraz küçük)
        self.color = (0, 255, 100) # Matrix Yeşili
        self.eye_color = (255, 0, 0) # Kırmızı Göz (Kötücül mod)

    def update(self, player_x, player_y, all_enemies, boss_manager_system, camera_speed):
        # 1. Takip Hareketi (Süzülerek)
        # Oyuncunun sol üstünde duracak
        target_dest_x = player_x - 40
        target_dest_y = player_y - 40
        
        # Yumuşak geçiş (Lerp)
        self.x += (target_dest_x - self.x) * 0.1
        self.y += (target_dest_y - self.y) * 0.1
        
        # Süzülme efekti
        self.float_offset += 0.1
        draw_y = self.y + math.sin(self.float_offset) * 5
        
        # 2. Lazer Saldırısı (Sık sık)
        self.laser_timer += 1
        if self.laser_timer > 30: # Saniyede 2 kez
            # En yakın düşmanı bul
            nearest_enemy = None
            min_dist = 400 # Menzil
            
            for enemy in all_enemies:
                # Mermileri hedef alma
                if isinstance(enemy, EnemyBullet): continue
                
                dist = math.sqrt((enemy.rect.centerx - self.x)**2 + (enemy.rect.centery - draw_y)**2)
                if dist < min_dist:
                    min_dist = dist
                    nearest_enemy = enemy
            
            if nearest_enemy:
                self.laser_timer = 0
                return ("LASER", nearest_enemy) # Main.py'de işlenecek

        # 3. Kazık Saldırısı (Nadir - Karma -250 altındaysa)
        # Bunu main.py içinde karma kontrolüyle tetikleyeceğiz
        
        return None

    def draw(self, surface):
        # [PLACEHOLDER] Vasil Companion — küçük renkli dikdörtgen kutu
        draw_y = self.y + math.sin(self.float_offset) * 4
        cx, cy = int(self.x), int(draw_y)
        w, h   = 24, 24
        rect   = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        box    = pygame.Surface((w, h), pygame.SRCALPHA)
        box.fill((0, 40, 20, 180))
        surface.blit(box, rect.topleft)
        pygame.draw.rect(surface, self.color, rect, 2)
        font = pygame.font.Font(None, 14)
        lbl  = font.render("VC", True, self.color)
        surface.blit(lbl, (rect.x + 3, rect.y + 5))
        
        # Göz (Kırmızı)
        pygame.draw.circle(surface, self.eye_color, (cx, cy), 5)