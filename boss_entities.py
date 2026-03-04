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

# ─────────────────────────────────────────────────────────────
#  YARDIMCI ÇİZİM FONKSİYONLARI
#  Mimariye uyum: Bu fonksiyonlar yalnızca draw() içinde çağrılır.
#  Döngüde list/dict tahsisatı yoktur; tümü yerel scope'ta kalır.
# ─────────────────────────────────────────────────────────────

def _draw_hex(surface, color, cx, cy, radius, width=0):
    """6 köşeli düzgün çokgen çizer."""
    pts = []
    for i in range(6):
        a = math.pi / 180 * (60 * i - 30)
        pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    pygame.draw.polygon(surface, color, pts, width)


def _draw_zigzag_line(surface, color, x1, y1, x2, y2, amplitude, segments, width=2):
    """
    İki nokta arasında zigzag yıldırım çizer.
    Döngü içinde list oluşturulmuyor — yerel pts sabit uzunluklu.
    """
    pts = []
    for i in range(segments + 1):
        t = i / segments
        bx = x1 + (x2 - x1) * t
        by = y1 + (y2 - y1) * t
        if 0 < i < segments:
            perp_x = -(y2 - y1)
            perp_y =  (x2 - x1)
            length = max(0.001, math.hypot(perp_x, perp_y))
            perp_x /= length
            perp_y /= length
            offset = random.uniform(-amplitude, amplitude)
            bx += perp_x * offset
            by += perp_y * offset
        pts.append((bx, by))
    if len(pts) >= 2:
        pygame.draw.lines(surface, color, False, pts, width)


def _draw_glow_circle(surface, color, cx, cy, radius, layers=3):
    """
    İç içe geçen şeffaf halkalarla glow etkisi.
    Surface tahsisatı draw() çağrısına bırakılmıştır; pool'da değil.
    """
    for i in range(layers, 0, -1):
        alpha = int(60 * (i / layers))
        r = radius + (layers - i) * 6
        try:
            s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color, alpha), (r + 1, r + 1), r)
            surface.blit(s, (cx - r - 1, cy - r - 1))
        except Exception:
            pass


def _draw_energy_core(surface, color, cx, cy, radius, pulse, width=2):
    """Nabız atan enerji çekirdeği — iç dolu + dış halka."""
    inner_r = max(2, int(radius * 0.5 * (0.8 + 0.2 * math.sin(pulse))))
    outer_r = max(3, int(radius * (1.0 + 0.12 * math.sin(pulse * 1.3))))
    pygame.draw.circle(surface, color, (int(cx), int(cy)), inner_r)
    pygame.draw.circle(surface, color, (int(cx), int(cy)), outer_r, width)


# ─────────────────────────────────────────────────────────────
#  BOSS SALDIRI NESNELERİ
# ─────────────────────────────────────────────────────────────

class BossSpike(pygame.sprite.Sprite):
    """
    Platformdan fışkıran enerji kazıkları.
    MANTIK DEĞİŞMEDİ — sadece draw() güçlendirildi.
    """
    def __init__(self, platform, karma):
        super().__init__()
        self.platform = platform
        self.karma = karma

        margin = 5
        self.width  = platform.width - (margin * 2)
        self.height = 130

        self.x = platform.rect.left + margin
        self.y = platform.rect.top  - self.height

        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

        self.timer            = 0
        self.warning_duration = 25
        self.active_duration  = 30
        self.state            = 'WARNING'

        # Görsel: uyarı nabzı için iç sayaç
        self._pulse = 0.0

    # ── MANTIK (değişmedi) ────────────────────────────────────
    def update(self, camera_speed):
        self.rect.x -= camera_speed
        self.x      -= camera_speed
        self._pulse += 0.25
        self.timer  += 1

        if self.state == 'WARNING':
            if self.timer >= self.warning_duration:
                self.state = 'ACTIVE'
                self.timer = 0
        elif self.state == 'ACTIVE':
            if self.timer >= self.active_duration:
                self.state = 'DONE'
                self.kill()

    # ── ÇİZİM (güçlendirildi) ────────────────────────────────
    def draw(self, surface):
        col_main = (0, 255, 255) if self.karma < 0 else (200, 0, 255)
        col_core = (200, 255, 255) if self.karma < 0 else (255, 180, 255)
        col_dark = (0, 30, 40)    if self.karma < 0 else (20, 0, 40)

        if self.state == 'WARNING':
            # Flaş ritmi
            if (self.timer // 3) % 2 == 0:
                # Zemin uyarı çizgisi — kalın + titreyen
                line_y = self.rect.bottom - 3
                pygame.draw.rect(surface, col_main,
                                 (self.rect.x, line_y - 4, self.width, 6))
                pygame.draw.rect(surface, col_core,
                                 (self.rect.x, line_y - 1, self.width, 2))

                # Kazık silueti (yarı-saydam)
                tip_count = max(1, self.width // 28)
                tip_w     = self.width // tip_count
                try:
                    ghost = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                    for i in range(tip_count):
                        tx = i * tip_w + tip_w // 2
                        pts = [(tx - tip_w // 2 + 3, self.height),
                               (tx + tip_w // 2 - 3, self.height),
                               (tx, 8)]
                        pygame.draw.polygon(ghost, (*col_main, 45), pts)
                        pygame.draw.polygon(ghost, (*col_main, 120), pts, 1)
                    surface.blit(ghost, (self.rect.x, self.rect.y))
                except Exception:
                    pass

        elif self.state == 'ACTIVE':
            progress  = min(1.0, self.timer / 5.0)
            tip_count = max(1, self.width // 28)
            tip_w     = self.width // tip_count
            tip_h     = int(self.height * progress)

            base_y = self.rect.bottom

            for i in range(tip_count):
                tx = self.rect.x + i * tip_w + tip_w // 2

                # Gölge gövde
                body_rect = pygame.Rect(self.rect.x + i * tip_w + 2,
                                        base_y - tip_h, tip_w - 4, tip_h)
                pygame.draw.rect(surface, col_dark, body_rect)

                # Üçgen uç — uç noktası
                tip_pts = [
                    (tx - tip_w // 2 + 2, base_y - tip_h + 1),
                    (tx + tip_w // 2 - 2, base_y - tip_h + 1),
                    (tx, base_y - tip_h - int(24 * progress)),
                ]
                pygame.draw.polygon(surface, col_main, tip_pts)

                # Parlak iç çizgi
                pygame.draw.line(surface, col_core,
                                 (tx, base_y),
                                 (tx, base_y - tip_h - int(18 * progress)), 2)

            # Dış kenar (tüm genişlik)
            border = pygame.Rect(self.rect.x, base_y - tip_h,
                                 self.width, tip_h)
            pygame.draw.rect(surface, col_main, border, 2)

            # Taban nabzı
            pulse_w = int(4 + 2 * math.sin(self._pulse * 2))
            pygame.draw.rect(surface, col_core,
                             (self.rect.x, base_y - 4, self.width, pulse_w))


class BossLightning(pygame.sprite.Sprite):
    """
    Tüm ekranı kesen şimşek sütunu.
    MANTIK DEĞİŞMEDİ — draw() dramatik zigzag yıldırım olarak yeniden yazıldı.
    """
    def __init__(self, x, karma):
        super().__init__()
        self.x    = x
        self.karma = karma
        self.width  = 60
        self.height = LOGICAL_HEIGHT
        self.rect   = pygame.Rect(self.x - self.width // 2, 0, self.width, self.height)
        self.timer            = 0
        self.warning_duration = 30
        self.active_duration  = 10
        self.state            = 'WARNING'
        self._pulse = 0.0

    # ── MANTIK (değişmedi) ────────────────────────────────────
    def update(self, camera_speed):
        self.x      -= camera_speed
        self.rect.x -= camera_speed
        self.timer  += 1
        self._pulse += 0.3

        if self.state == 'WARNING':
            if self.timer >= self.warning_duration:
                self.state = 'ACTIVE'
                self.timer = 0
        elif self.state == 'ACTIVE':
            if self.timer >= self.active_duration:
                self.state = 'DONE'
                self.kill()

    # ── ÇİZİM (güçlendirildi) ────────────────────────────────
    def draw(self, surface):
        warn_col = (0, 255, 255) if self.karma < 0 else (200, 0, 255)
        core_col = (220, 255, 255) if self.karma < 0 else (255, 220, 255)

        if self.state == 'WARNING':
            if (self.timer // 4) % 2 == 0:
                # Geniş titreyen uyarı bantı
                try:
                    band = pygame.Surface((self.width + 20, LOGICAL_HEIGHT), pygame.SRCALPHA)
                    band.fill((*warn_col, 18))
                    surface.blit(band, (int(self.x) - self.width // 2 - 10, 0))
                except Exception:
                    pass

                # İnce önizleme yıldırım
                _draw_zigzag_line(surface, (*warn_col, 100),
                                  self.x, 0, self.x, LOGICAL_HEIGHT,
                                  amplitude=12, segments=14, width=1)

                # Uyarı ! işareti
                warn_radius = int(18 + 3 * math.sin(self._pulse))
                pygame.draw.circle(surface, warn_col,
                                   (int(self.x), 45), warn_radius, 2)
                try:
                    font = pygame.font.Font(None, 32)
                    txt  = font.render("!", True, warn_col)
                    surface.blit(txt, (int(self.x) - 5, 32))
                except Exception:
                    pass

                # Altta hedef elipsi
                target_rect = pygame.Rect(int(self.x) - 20,
                                          LOGICAL_HEIGHT - 55, 40, 18)
                pygame.draw.ellipse(surface, warn_col, target_rect, 2)
                # Nabız halkaları
                for r in range(3):
                    er = 22 + r * 10 + int(5 * math.sin(self._pulse + r))
                    pygame.draw.ellipse(surface, warn_col,
                                        pygame.Rect(int(self.x) - er // 2,
                                                    LOGICAL_HEIGHT - 10 - er // 4,
                                                    er, er // 2), 1)

        elif self.state == 'ACTIVE':
            # Dış glow (geniş, şeffaf)
            try:
                glow_w = 40
                glow = pygame.Surface((glow_w * 2, LOGICAL_HEIGHT), pygame.SRCALPHA)
                glow.fill((*warn_col, 35))
                surface.blit(glow, (int(self.x) - glow_w, 0))
            except Exception:
                pass

            # 3 zigzag katmanı — kalınlıktan inceye
            for layer, (amp, segs, lw, alpha_col) in enumerate([
                (22, 10, 6, warn_col),
                (14,  8, 3, core_col),
                ( 6, 12, 1, (255, 255, 255)),
            ]):
                _draw_zigzag_line(surface, alpha_col,
                                  self.x, 0, self.x, LOGICAL_HEIGHT,
                                  amplitude=amp, segments=segs, width=lw)

            # Zemin çarpma efekti
            impact_r = int(18 + 6 * math.sin(self._pulse * 4))
            pygame.draw.circle(surface, warn_col,
                                (int(self.x), LOGICAL_HEIGHT - 4), impact_r, 2)
            pygame.draw.circle(surface, (255, 255, 255),
                                (int(self.x), LOGICAL_HEIGHT - 4), impact_r // 2)


class BossGiantArrow(pygame.sprite.Sprite):
    """
    Yerden yükselen enerji sütunu.
    MANTIK DEĞİŞMEDİ — draw() lazer kolon görünümüne dönüştürüldü.
    """
    def __init__(self, x, karma):
        super().__init__()
        self.x    = x
        self.karma = karma
        self.width  = 150
        self.height = 400
        self.rect   = pygame.Rect(x, LOGICAL_HEIGHT, self.width, self.height)
        self.timer            = 0
        self.warning_duration = 45
        self.active_duration  = 20
        self.state            = 'WARNING'
        self._pulse = 0.0

    # ── MANTIK (değişmedi) ────────────────────────────────────
    def update(self, camera_speed):
        self.x      -= camera_speed
        self.rect.x -= camera_speed
        self.timer  += 1
        self._pulse += 0.18

        if self.state == 'WARNING':
            if self.timer >= self.warning_duration:
                self.state = 'ACTIVE'
                self.timer = 0
        elif self.state == 'ACTIVE':
            if self.timer >= self.active_duration:
                self.state = 'DONE'
                self.kill()

    # ── ÇİZİM (güçlendirildi) ────────────────────────────────
    def draw(self, surface):
        col      = (255, 40,  40)  if self.karma < 0 else (160, 0, 255)
        col_core = (255, 200, 200) if self.karma < 0 else (220, 180, 255)
        cx       = self.rect.x + self.width // 2

        if self.state == 'WARNING':
            if (self.timer // 8) % 2 == 0:
                # Yarı-saydam zemin dolgusu
                try:
                    s = pygame.Surface((self.width, LOGICAL_HEIGHT), pygame.SRCALPHA)
                    alpha = int(30 + 20 * math.sin(self._pulse))
                    s.fill((*col, alpha))
                    surface.blit(s, (self.rect.x, 0))
                except Exception:
                    pass

                # Altta yoğunlaşan enerji çubuğu
                bar_h = int(18 + 4 * math.sin(self._pulse * 2))
                pygame.draw.rect(surface, col,
                                 (self.rect.x, LOGICAL_HEIGHT - bar_h,
                                  self.width, bar_h))
                pygame.draw.rect(surface, col_core,
                                 (self.rect.x + 4, LOGICAL_HEIGHT - bar_h + 3,
                                  self.width - 8, bar_h - 6))

                # Yükselen ince çizgiler (şarj hissi)
                stripe_count = 5
                for i in range(stripe_count):
                    sx = self.rect.x + (i + 1) * (self.width // (stripe_count + 1))
                    line_h = int(LOGICAL_HEIGHT * 0.3 * ((self.timer / self.warning_duration)))
                    alpha_stripe = int(80 + 60 * math.sin(self._pulse + i))
                    try:
                        ls = pygame.Surface((2, line_h), pygame.SRCALPHA)
                        ls.fill((*col_core, alpha_stripe))
                        surface.blit(ls, (sx - 1, LOGICAL_HEIGHT - line_h))
                    except Exception:
                        pass

        elif self.state == 'ACTIVE':
            progress = min(1.0, self.timer / 5.0)
            h        = int(LOGICAL_HEIGHT * progress)
            top_y    = LOGICAL_HEIGHT - h

            # Dış glow katmanı
            try:
                glow_extra = 20
                gs = pygame.Surface((self.width + glow_extra * 2, h), pygame.SRCALPHA)
                gs.fill((*col, 25))
                surface.blit(gs, (self.rect.x - glow_extra, top_y))
            except Exception:
                pass

            # Koyu dolgu gövde
            pygame.draw.rect(surface, (10, 5, 15),
                             (self.rect.x, top_y, self.width, h))

            # Dış kenar
            pygame.draw.rect(surface, col,
                             (self.rect.x, top_y, self.width, h), 3)

            # İç parlak hat (orta sütun)
            core_w = max(6, int(self.width * 0.15 * (1 + 0.2 * math.sin(self._pulse * 3))))
            pygame.draw.rect(surface, col_core,
                             (cx - core_w // 2, top_y, core_w, h))

            # Yükselen enerji dalgası (yatay bantlar)
            band_spacing = 18
            band_count   = h // band_spacing
            for i in range(band_count):
                by = top_y + i * band_spacing + int(4 * math.sin(self._pulse * 4 + i))
                try:
                    bs = pygame.Surface((self.width - 6, 2), pygame.SRCALPHA)
                    bs.fill((*col, 80))
                    surface.blit(bs, (self.rect.x + 3, by))
                except Exception:
                    pass

            # Üst ok başı
            tip_pts = [
                (cx - self.width // 2, top_y + 2),
                (cx + self.width // 2, top_y + 2),
                (cx, top_y - int(35 * progress)),
            ]
            pygame.draw.polygon(surface, col, tip_pts)
            pygame.draw.polygon(surface, col_core, tip_pts, 2)


class BossOrbitalStrike(pygame.sprite.Sprite):
    """
    Orbital bomba + zemin ışın patlaması.
    MANTIK DEĞİŞMEDİ — draw() çok katmanlı dramatik efektle yeniden yazıldı.
    """
    def __init__(self, x, y, karma):
        super().__init__()
        self.x     = x
        self.y     = y
        self.karma = karma
        self.timer      = 0
        self.radius     = 0
        self.max_radius = 300
        self.state      = 'CHARGING'
        self.beams      = []
        self._pulse     = 0.0
        self._orbit_angle = 0.0

    # ── MANTIK (değişmedi) ────────────────────────────────────
    def update(self, camera_speed):
        self.x     -= camera_speed
        self.timer += 1
        self._pulse       += 0.2
        self._orbit_angle += 0.08

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

    # ── ÇİZİM (güçlendirildi) ────────────────────────────────
    def draw(self, surface):
        col      = (0, 220, 220) if self.karma < 0 else (220, 0, 220)
        col_core = (200, 255, 255) if self.karma < 0 else (255, 200, 255)
        cx, cy   = int(self.x), int(self.y)

        if self.state == 'CHARGING':
            charge_pct = min(1.0, self.timer / 60.0)

            # Büyüyen glow halkalar (iç içe, şeffaf)
            for layer in range(4):
                ring_r = int(self.radius) + layer * 8
                if ring_r < 2:
                    continue
                a = max(0, 90 - layer * 20)
                try:
                    rs = pygame.Surface((ring_r * 2 + 4, ring_r * 2 + 4), pygame.SRCALPHA)
                    pygame.draw.circle(rs, (*col, a),
                                       (ring_r + 2, ring_r + 2), ring_r, 2)
                    surface.blit(rs, (cx - ring_r - 2, cy - ring_r - 2))
                except Exception:
                    pass

            # Yörüngede dönen küçük enerji parçacıkları (3 adet, döner)
            orbit_r = int(self.radius) + 12
            for i in range(3):
                a = self._orbit_angle + i * (math.pi * 2 / 3)
                ox = cx + int(orbit_r * math.cos(a))
                oy = cy + int(orbit_r * math.sin(a))
                pygame.draw.circle(surface, col_core, (ox, oy), 3)

            # Merkez çekirdek
            core_r = max(3, int(self.radius * 0.4))
            pygame.draw.circle(surface, col_core, (cx, cy), core_r)
            pygame.draw.circle(surface, col, (cx, cy), core_r, 1)

            # Zemin hedef bölgesi (elips + yatay çizgiler)
            zone_w = int(self.max_radius * 2 * charge_pct)
            if zone_w > 4:
                pygame.draw.ellipse(surface, col,
                                    pygame.Rect(cx - zone_w // 2,
                                                LOGICAL_HEIGHT - 16,
                                                zone_w, 16), 2)
                # İç dolgu (hafif)
                try:
                    zs = pygame.Surface((zone_w, 16), pygame.SRCALPHA)
                    zs.fill((*col, 20))
                    surface.blit(zs, (cx - zone_w // 2, LOGICAL_HEIGHT - 16))
                except Exception:
                    pass

            # Şarj yüzdesi ışını — merkez-zemin arası ince çizgi
            if charge_pct > 0.3:
                beam_alpha = int(180 * (charge_pct - 0.3) / 0.7)
                try:
                    bl = pygame.Surface((4, LOGICAL_HEIGHT - cy), pygame.SRCALPHA)
                    bl.fill((*col, beam_alpha))
                    surface.blit(bl, (cx - 2, cy))
                except Exception:
                    pass

        elif self.state == 'BLAST':
            blast_pct = min(1.0, self.timer / 10.0)
            fade      = max(0.0, 1.0 - self.timer / 20.0)

            # Merkez patlaması
            burst_r = int(30 + 20 * blast_pct)
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy), burst_r)
            pygame.draw.circle(surface, col_core, (cx, cy), burst_r, 3)

            # Dışa açılan halkalar
            for ring in range(3):
                rr = burst_r + ring * 14
                try:
                    rs = pygame.Surface((rr * 2 + 4, rr * 2 + 4), pygame.SRCALPHA)
                    ra = int(120 * fade * (1 - ring * 0.3))
                    pygame.draw.circle(rs, (*col, ra), (rr + 2, rr + 2), rr, 2)
                    surface.blit(rs, (cx - rr - 2, cy - rr - 2))
                except Exception:
                    pass

            # Her ışın (merkez → zemin)
            for bx in self.beams:
                ibx = int(bx)

                # Glow gövde
                try:
                    gw = 30
                    gh = LOGICAL_HEIGHT - cy
                    if gh > 0:
                        gs = pygame.Surface((gw * 2, gh), pygame.SRCALPHA)
                        gs.fill((*col, int(40 * fade)))
                        surface.blit(gs, (ibx - gw, cy))
                except Exception:
                    pass

                # Çekirdek çizgi + kenara ince çizgi
                pygame.draw.line(surface, col,
                                 (ibx, cy), (ibx, LOGICAL_HEIGHT), 5)
                pygame.draw.line(surface, (255, 255, 255),
                                 (ibx, cy), (ibx, LOGICAL_HEIGHT), 2)

                # Zemin çarpma çemberi
                impact_r = int(22 + 8 * math.sin(self._pulse * 5))
                pygame.draw.circle(surface, col,
                                   (ibx, LOGICAL_HEIGHT - 3), impact_r, 3)
                pygame.draw.circle(surface, col_core,
                                   (ibx, LOGICAL_HEIGHT - 3), impact_r // 2)

    def check_collision(self, player_rect):
        if self.state == 'BLAST':
            for bx in self.beams:
                beam_rect = pygame.Rect(bx - 20, 0, 40, LOGICAL_HEIGHT)
                if beam_rect.colliderect(player_rect):
                    return True
        return False


# ─────────────────────────────────────────────────────────────
#  BOSS SINIFLARI
# ─────────────────────────────────────────────────────────────

class NexusBoss(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.x   = x
        self.y   = y
        self.health        = BOSS_HEALTH
        self.max_health    = BOSS_HEALTH
        self.fire_timer    = 0
        self.invulnerable_timer = 0
        self.spawn_queue   = []
        self.phase         = 1
        self._pulse        = 0.0
        self._spin         = 0.0

    def update(self, camera_speed, dt, player_pos):
        self.x          -= camera_speed
        self.fire_timer += 1
        self._pulse     += 0.07
        self._spin      += 0.04
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1
        if self.fire_timer >= BOSS_FIRE_RATE:
            self.fire_timer = 0
            self.shoot(player_pos)
        if self.health <= self.max_health * 0.5 and self.phase == 1:
            self.phase = 2
            self.enter_phase2()

    def shoot(self, player_pos):
        dx   = player_pos[0] - self.x
        dy   = player_pos[1] - self.y
        dist = max(0.1, math.sqrt(dx * dx + dy * dy))
        dx  /= dist
        dy  /= dist
        bullet = EnemyBullet(self.x, self.y, dx * BULLET_SPEED, dy * BULLET_SPEED,
                             BOSS_DAMAGE, color=(0, 220, 255))
        self.spawn_queue.append(bullet)

    def enter_phase2(self):
        global BOSS_FIRE_RATE
        BOSS_FIRE_RATE = max(20, BOSS_FIRE_RATE - 20)

    def draw(self, surface, theme):
        col  = (255, 80, 80) if self.invulnerable_timer > 0 else (0, 220, 255)
        col2 = (255, 255, 255) if self.invulnerable_timer > 0 else (180, 255, 255)
        cx, cy = int(self.x), int(self.y)
        bw = 80

        # Dış glow halkalar
        _draw_glow_circle(surface, col, cx, cy, bw // 2, layers=3)

        # Dönen dış altıgen
        outer_r = int(bw // 2 + 8 + 4 * math.sin(self._pulse))
        _draw_hex(surface, col, cx, cy, outer_r, width=2)

        # Dönen iç kare (45 derece)
        inner_r = bw // 2 - 4
        rot_pts = []
        for i in range(4):
            a = self._spin + i * (math.pi / 2)
            rot_pts.append((cx + inner_r * math.cos(a),
                            cy + inner_r * math.sin(a)))
        if len(rot_pts) == 4:
            pygame.draw.polygon(surface, col, rot_pts, 2)

        # Koyu dolgu iç
        try:
            body = pygame.Surface((bw, bw), pygame.SRCALPHA)
            body.fill((5, 15, 30, 180))
            surface.blit(body, (cx - bw // 2, cy - bw // 2))
        except Exception:
            pass

        # Nabız atan çekirdek
        _draw_energy_core(surface, col2, cx, cy,
                          radius=12, pulse=self._pulse)

        # Faz 2 ise ek dönen yörüngeler
        if self.phase == 2:
            for i in range(4):
                a = self._spin * 1.5 + i * (math.pi / 2)
                ox = cx + int(35 * math.cos(a))
                oy = cy + int(35 * math.sin(a))
                pygame.draw.circle(surface, col, (ox, oy), 4)
                pygame.draw.circle(surface, col2, (ox, oy), 2)

        # İsim etiketi
        try:
            font = pygame.font.Font(None, 20)
            lbl  = font.render("NEXUS", True, col)
            surface.blit(lbl, (cx - lbl.get_width() // 2, cy - bw // 2 - 18))
        except Exception:
            pass

        # HP bar (kalın, kenarlıklı)
        self._draw_hp_bar(surface, cx, cy - bw // 2 - 38, col, 220)

    def take_damage(self, damage):
        if self.invulnerable_timer <= 0:
            self.health            -= damage
            self.invulnerable_timer = BOSS_INVULNERABILITY_TIME
            if self.health <= 0:
                self.kill()

    def _draw_hp_bar(self, surface, cx, top_y, col, bar_w):
        ratio = max(0, self.health) / self.max_health
        pygame.draw.rect(surface, (40, 5, 5),
                         (cx - bar_w // 2, top_y, bar_w, 10))
        pygame.draw.rect(surface, col,
                         (cx - bar_w // 2, top_y, int(bar_w * ratio), 10))
        pygame.draw.rect(surface, col,
                         (cx - bar_w // 2, top_y, bar_w, 10), 1)
        # Parlaklık üst şerit
        pygame.draw.rect(surface, (255, 255, 255),
                         (cx - bar_w // 2, top_y, int(bar_w * ratio), 2))


class AresBoss(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.x   = x
        self.y   = y
        self.health        = BOSS_HEALTH
        self.max_health    = BOSS_HEALTH
        self.fire_timer    = 0
        self.invulnerable_timer = 0
        self.spawn_queue   = []
        self.phase         = 1
        self._pulse        = 0.0
        self._rage_flicker = 0

    def update(self, camera_speed, dt, player_pos):
        self.x          -= camera_speed
        self.fire_timer += 1
        self._pulse     += 0.06
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1
            self._rage_flicker      += 1
        else:
            self._rage_flicker = 0
        if self.fire_timer >= BOSS_FIRE_RATE:
            self.fire_timer = 0
            self.shoot(player_pos)
        if self.health <= self.max_health * 0.5 and self.phase == 1:
            self.phase = 2
            self.enter_phase2()

    def shoot(self, player_pos):
        for angle in [-0.2, 0, 0.2]:
            dx   = player_pos[0] - self.x
            dy   = player_pos[1] - self.y
            dist = max(0.1, math.sqrt(dx * dx + dy * dy))
            dx  /= dist
            dy  /= dist
            new_dx = dx * math.cos(angle) - dy * math.sin(angle)
            new_dy = dx * math.sin(angle) + dy * math.cos(angle)
            bullet = EnemyBullet(self.x, self.y,
                                 new_dx * BULLET_SPEED,
                                 new_dy * BULLET_SPEED,
                                 BOSS_DAMAGE, color=(255, 200, 0))
            self.spawn_queue.append(bullet)

    def enter_phase2(self):
        global BOSS_FIRE_RATE
        BOSS_FIRE_RATE = max(15, BOSS_FIRE_RATE - 25)

    def draw(self, surface, theme):
        is_hit = self.invulnerable_timer > 0
        col    = (255, 80, 80) if is_hit else (255, 215, 0)
        col2   = (255, 255, 200) if not is_hit else (255, 180, 180)
        cx, cy = int(self.x), int(self.y)
        bw, bh = 100, 100

        # Dış ateş halkası (glow)
        aura_r = int(bw // 2 + 10 + 6 * math.sin(self._pulse))
        _draw_glow_circle(surface, col, cx, cy, aura_r, layers=4)

        # Koyu gövde
        try:
            body = pygame.Surface((bw, bh), pygame.SRCALPHA)
            body.fill((20, 10, 0, 190))
            surface.blit(body, (cx - bw // 2, cy - bh // 2))
        except Exception:
            pass

        # Dış sekizgen (Ares kalkanı)
        pts8 = []
        for i in range(8):
            a = math.pi / 8 + i * (math.pi / 4) + self._pulse * 0.3
            r = bw // 2 + int(4 * math.sin(self._pulse * 2 + i))
            pts8.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        if len(pts8) == 8:
            pygame.draw.polygon(surface, col, pts8, 3)

        # İç çapraz çizgiler (X işareti)
        cross_size = bw // 2 - 8
        lw = 3 if not is_hit else 5
        pygame.draw.line(surface, col2,
                         (cx - cross_size, cy - cross_size),
                         (cx + cross_size, cy + cross_size), lw)
        pygame.draw.line(surface, col2,
                         (cx + cross_size, cy - cross_size),
                         (cx - cross_size, cy + cross_size), lw)

        # Nabız atan merkez
        _draw_energy_core(surface, col, cx, cy, radius=14, pulse=self._pulse)

        # Faz 2 ek efekt: dönen iç üçgen
        if self.phase == 2:
            tri_r = 20
            tri_pts = []
            for i in range(3):
                a = self._pulse * 1.8 + i * (math.pi * 2 / 3)
                tri_pts.append((cx + int(tri_r * math.cos(a)),
                                cy + int(tri_r * math.sin(a))))
            if len(tri_pts) == 3:
                pygame.draw.polygon(surface, col2, tri_pts, 2)

        # İsim
        try:
            font = pygame.font.Font(None, 22)
            lbl  = font.render("ARES", True, col)
            surface.blit(lbl, (cx - lbl.get_width() // 2, cy - bh // 2 - 20))
        except Exception:
            pass

        self._draw_hp_bar(surface, cx, cy - bh // 2 - 40, col, 220)

    def take_damage(self, damage):
        if self.invulnerable_timer <= 0:
            self.health            -= damage
            self.invulnerable_timer = BOSS_INVULNERABILITY_TIME
            if self.health <= 0:
                self.kill()

    def _draw_hp_bar(self, surface, cx, top_y, col, bar_w):
        ratio = max(0, self.health) / self.max_health
        pygame.draw.rect(surface, (40, 20, 0),
                         (cx - bar_w // 2, top_y, bar_w, 10))
        pygame.draw.rect(surface, col,
                         (cx - bar_w // 2, top_y, int(bar_w * ratio), 10))
        pygame.draw.rect(surface, col,
                         (cx - bar_w // 2, top_y, bar_w, 10), 1)
        pygame.draw.rect(surface, (255, 255, 255),
                         (cx - bar_w // 2, top_y, int(bar_w * ratio), 2))


class VasilBoss(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.x   = x
        self.y   = y
        self.health        = BOSS_HEALTH
        self.max_health    = BOSS_HEALTH
        self.fire_timer    = 0
        self.invulnerable_timer = 0
        self.spawn_queue   = []
        self.phase         = 1
        self._pulse        = 0.0
        self._wave         = 0.0

    def update(self, camera_speed, dt, player_pos):
        self.x          -= camera_speed
        self.fire_timer += 1
        self._pulse     += 0.05
        self._wave      += 0.12
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1
        if self.fire_timer >= BOSS_FIRE_RATE:
            self.fire_timer = 0
            self.shoot(player_pos)
        if self.health <= self.max_health * 0.5 and self.phase == 1:
            self.phase = 2
            self.enter_phase2()

    def shoot(self, player_pos):
        angle  = self.fire_timer * 0.1
        dx     = math.cos(angle)
        dy     = math.sin(angle)
        bullet = EnemyBullet(self.x, self.y,
                             dx * BULLET_SPEED,
                             dy * BULLET_SPEED,
                             BOSS_DAMAGE, color=(200, 0, 255))
        self.spawn_queue.append(bullet)

    def enter_phase2(self):
        global BOSS_FIRE_RATE
        BOSS_FIRE_RATE = max(10, BOSS_FIRE_RATE - 30)

    def draw(self, surface, theme):
        is_hit = self.invulnerable_timer > 0
        col    = (255, 80, 80) if is_hit else (180, 0, 220)
        col2   = (255, 200, 255) if not is_hit else (255, 180, 180)
        cx, cy = int(self.x), int(self.y)
        bw, bh = 100, 110

        # Dalgalanma efekti (mor enerji halkası)
        wave_r = int(bw // 2 + 12 + 8 * math.sin(self._wave))
        _draw_glow_circle(surface, col, cx, cy, wave_r, layers=4)

        # Gövde (koyu mor)
        try:
            body = pygame.Surface((bw, bh), pygame.SRCALPHA)
            body.fill((15, 0, 25, 185))
            surface.blit(body, (cx - bw // 2, cy - bh // 2))
        except Exception:
            pass

        # Dış elips (Vasil'in yörüngesi)
        elips_rx = int(bw // 2 + 6 + 4 * math.sin(self._pulse))
        elips_ry = int(bh // 2 + 4 + 2 * math.sin(self._pulse * 1.4))
        pygame.draw.ellipse(surface, col,
                            pygame.Rect(cx - elips_rx, cy - elips_ry,
                                        elips_rx * 2, elips_ry * 2), 3)

        # Dönen yörünge halkası (ince)
        orbit_pts = []
        for i in range(12):
            a = self._wave + i * (math.pi * 2 / 12)
            ox = cx + int((bw // 2 - 5) * math.cos(a))
            oy = cy + int((bh // 2 - 5) * math.sin(a))
            orbit_pts.append((ox, oy))
        if len(orbit_pts) >= 2:
            pygame.draw.lines(surface, (*col2, 80) if False else col2,
                              True, orbit_pts, 1)

        # Yörüngede parlayan enerji noktaları (3 adet)
        for i in range(3):
            a = self._wave * 1.3 + i * (math.pi * 2 / 3)
            ox = cx + int((bw // 2) * math.cos(a))
            oy = cy + int((bh // 2) * math.sin(a))
            pygame.draw.circle(surface, col2, (ox, oy), 4)
            pygame.draw.circle(surface, col,  (ox, oy), 6, 1)

        # Nabız çekirdek
        _draw_energy_core(surface, col, cx, cy, radius=15, pulse=self._pulse)

        # Faz 2: ikinci yörünge (ters yön)
        if self.phase == 2:
            for i in range(4):
                a = -self._wave * 0.8 + i * (math.pi / 2)
                ox = cx + int(25 * math.cos(a))
                oy = cy + int(25 * math.sin(a))
                pygame.draw.circle(surface, col, (ox, oy), 3)

        # İsim
        try:
            font = pygame.font.Font(None, 22)
            lbl  = font.render("VASİL", True, col)
            surface.blit(lbl, (cx - lbl.get_width() // 2, cy - bh // 2 - 20))
        except Exception:
            pass

        self._draw_hp_bar(surface, cx, cy - bh // 2 - 40, col, 220)

    def take_damage(self, damage):
        if self.invulnerable_timer <= 0:
            self.health            -= damage
            self.invulnerable_timer = BOSS_INVULNERABILITY_TIME
            if self.health <= 0:
                self.kill()

    def _draw_hp_bar(self, surface, cx, top_y, col, bar_w):
        ratio = max(0, self.health) / self.max_health
        pygame.draw.rect(surface, (30, 0, 40),
                         (cx - bar_w // 2, top_y, bar_w, 10))
        pygame.draw.rect(surface, col,
                         (cx - bar_w // 2, top_y, int(bar_w * ratio), 10))
        pygame.draw.rect(surface, col,
                         (cx - bar_w // 2, top_y, bar_w, 10), 1)
        pygame.draw.rect(surface, (255, 255, 255),
                         (cx - bar_w // 2, top_y, int(bar_w * ratio), 2))


# ─────────────────────────────────────────────────────────────
#  MERMİ
# ─────────────────────────────────────────────────────────────

class EnemyBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy, damage, color=(220, 30, 30)):
        super().__init__()
        self.x      = x
        self.y      = y
        self.vx     = vx
        self.vy     = vy
        self.damage = damage
        self.radius = 8
        self.color  = color
        self._spin  = random.uniform(0, math.pi * 2)
        self._trail = []   # (x, y) geçmiş konumları — max 5 kayıt

    def update(self, camera_speed, dt, player_pos=None):
        self.x     += self.vx
        self.y     += self.vy
        self.x     -= camera_speed
        self._spin += 0.18

        # Trail güncelle — max 5 nokta (FIFO, listte)
        self._trail.append((self.x, self.y))
        if len(self._trail) > 5:
            self._trail.pop(0)

        if (self.x < -100 or self.x > LOGICAL_WIDTH + 100 or
                self.y < -100 or self.y > LOGICAL_HEIGHT + 100):
            self.kill()

    def draw(self, surface, theme):
        cx, cy = int(self.x), int(self.y)
        col    = self.color
        bright = (min(255, col[0] + 80),
                  min(255, col[1] + 80),
                  min(255, col[2] + 80))

        # Trail iz (soluk halkalar)
        trail_len = len(self._trail)
        for i, (tx, ty) in enumerate(self._trail):
            frac = (i + 1) / trail_len
            r    = max(2, int(self.radius * 0.5 * frac))
            try:
                ts = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(ts, (*col, int(60 * frac)),
                                   (r + 1, r + 1), r)
                surface.blit(ts, (int(tx) - r - 1, int(ty) - r - 1))
            except Exception:
                pass

        # Dış glow
        _draw_glow_circle(surface, col, cx, cy, self.radius, layers=2)

        # Dönen elmas (dört köşe)
        diamond_pts = []
        for i in range(4):
            a = self._spin + i * (math.pi / 2)
            diamond_pts.append((cx + int(self.radius * math.cos(a)),
                                 cy + int(self.radius * math.sin(a))))
        if len(diamond_pts) == 4:
            pygame.draw.polygon(surface, col, diamond_pts)
            pygame.draw.polygon(surface, bright, diamond_pts, 1)

        # Parlak merkez nokta
        pygame.draw.circle(surface, bright, (cx, cy), 3)


# ─────────────────────────────────────────────────────────────
#  VASİL YARDIMCISI (değişmedi — sadece draw() hafif iyileştirildi)
# ─────────────────────────────────────────────────────────────

class VasilCompanion(pygame.sprite.Sprite):
    """Oyuncuyu takip eden ve düşmanları yok eden Mini-Vasil"""
    def __init__(self, x, y):
        super().__init__()
        self.x       = x
        self.y       = y
        self.target_x = x
        self.target_y = y
        self.float_offset = 0.0

        self.laser_timer  = 0
        self.spike_timer  = 0
        self.shield_timer = 0

        self.size      = 20
        self.color     = (0, 255, 100)
        self.eye_color = (255, 0, 0)
        self._pulse    = 0.0

    def update(self, player_x, player_y, all_enemies, boss_manager_system, camera_speed):
        target_dest_x = player_x - 40
        target_dest_y = player_y - 40
        self.x += (target_dest_x - self.x) * 0.1
        self.y += (target_dest_y - self.y) * 0.1
        self.float_offset += 0.1
        self._pulse       += 0.15
        draw_y = self.y + math.sin(self.float_offset) * 5

        self.laser_timer += 1
        if self.laser_timer > 30:
            nearest_enemy = None
            min_dist      = 400
            for enemy in all_enemies:
                if isinstance(enemy, EnemyBullet):
                    continue
                dist = math.hypot(enemy.rect.centerx - self.x,
                                  enemy.rect.centery - draw_y)
                if dist < min_dist:
                    min_dist      = dist
                    nearest_enemy = enemy
            if nearest_enemy:
                self.laser_timer = 0
                return ("LASER", nearest_enemy)

        return None

    def draw(self, surface):
        draw_y = self.y + math.sin(self.float_offset) * 4
        cx, cy = int(self.x), int(draw_y)
        w, h   = 24, 24

        # Glow
        _draw_glow_circle(surface, self.color, cx, cy, w // 2 + 4, layers=2)

        # Gövde
        try:
            box = pygame.Surface((w, h), pygame.SRCALPHA)
            box.fill((0, 40, 20, 180))
            surface.blit(box, (cx - w // 2, cy - h // 2))
        except Exception:
            pass

        # Dış altıgen (küçük)
        _draw_hex(surface, self.color, cx, cy, w // 2 + 2, width=2)

        # Nabız çekirdek
        _draw_energy_core(surface, self.color, cx, cy,
                          radius=5, pulse=self._pulse, width=1)

        # Göz (kırmızı — pulsing)
        eye_r = max(2, int(4 + 1.5 * math.sin(self._pulse * 2)))
        pygame.draw.circle(surface, self.eye_color, (cx, cy), eye_r)