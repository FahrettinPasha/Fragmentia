# stealth_system.py — FRAGMENTIA: GİZLİLİK SİSTEMİ
# =============================================================================
# Görev belgesindeki tüm gizlilik mekaniğini (kamera kör noktaları, görüş
# konisi, uyarı seviyeleri, saklanma noktaları) tek modülde toplar.
#
# MİMARİ KURALLARI:
#   • Tüm zamanlayıcılar dt ile çalışır (RULE 1).
#   • draw() metodları main.py'nin Step 7 (VFX / HUD) katmanında çağrılır (RULE 2).
#   • GC kuralı: listelerde object pooling; update döngüsünde yeni nesne yaratılmaz.
#   • Pixel Art geçişi: tüm görsel fallback'ler pygame.Rect üzerinden çalışır.
# =============================================================================

from __future__ import annotations
import math
import pygame
import random
from typing import Optional, List, Tuple, Dict, Any


# ─────────────────────────────────────────────────────────────────────────────
# 1. SABİTLER
# ─────────────────────────────────────────────────────────────────────────────

# Uyarı seviyeleri
ALERT_UNDETECTED  = 0   # Oyuncu fark edilmedi
ALERT_SUSPICIOUS  = 1   # Şüphe var, dedektör saatleniyor
ALERT_DETECTED    = 2   # Oyuncu tespit edildi — alarm!

# Görüş konisi
VISION_RANGE_DEFAULT  = 300   # px
VISION_ANGLE_DEFAULT  = 80    # derece (toplam, yani ±40)
VISION_RANGE_PATROL   = 220   # devriye modunda kısaltılmış
SUSPICION_BUILD_RATE  = 1.5   # saniye başına dolum (0..1 arası)
SUSPICION_DECAY_RATE  = 0.8   # görüş dışında azalma

# Kamera döngü süresi
CAMERA_SWEEP_PERIOD   = 4.0   # saniye

# Saklanma noktası bonusu
HIDE_KARMA_BONUS      = 1

# Renk sabitleri (fallback çizim)
_COL_UNDETECTED = (0, 255, 80,   60)   # Yeşil yarı saydam
_COL_SUSPICIOUS = (255, 180, 0,  80)   # Sarı yarı saydam
_COL_DETECTED   = (255, 30,  30, 100)  # Kırmızı yarı saydam
_COL_HIDE       = (0,  200, 255, 120)  # Saklanma noktası mavi


# ─────────────────────────────────────────────────────────────────────────────
# 2. SAKLANMA NOKTASI
# ─────────────────────────────────────────────────────────────────────────────

class HideSpot:
    """
    Oyuncunun içine girince görünmez olduğu bölge.
    main.py'de Platform gibi statik nesnelerle birlikte oluşturulur.

    Kullanım:
        spot = HideSpot(x=400, y=900, width=80, height=100, label="KONTEYNIR")
        stealth.register_hide_spot(spot)
    """

    def __init__(self, x: int, y: int, width: int, height: int,
                 label: str = "SAKLANMA"):
        self.rect  = pygame.Rect(x, y, width, height)
        self.label = label
        self.occupied = False

    def contains(self, px: float, py: float) -> bool:
        return self.rect.collidepoint(int(px), int(py))

    def draw(self, surface: pygame.Surface, camera_offset: Tuple[int, int] = (0, 0)):
        """Step 7 — fallback dikdörtgen."""
        ox, oy = camera_offset
        draw_r = self.rect.move(ox, oy)
        s = pygame.Surface((draw_r.width, draw_r.height), pygame.SRCALPHA)
        s.fill(_COL_HIDE)
        surface.blit(s, draw_r.topleft)
        pygame.draw.rect(surface, (0, 200, 255), draw_r, 2)
        font = pygame.font.Font(None, 18)
        lbl  = font.render(self.label, True, (0, 200, 255))
        surface.blit(lbl, (draw_r.x + 3, draw_r.y + 3))


# ─────────────────────────────────────────────────────────────────────────────
# 3. GÖZETİM KAMERASI
# ─────────────────────────────────────────────────────────────────────────────

class SurveillanceCamera:
    """
    Duvara monte, belirli aç tarama yapan kamera.

    sweep_left / sweep_right: görüş konisinin salınım sınır açıları (derece)
    Kamera sweep_period saniyede tam gidiş-dönüş yapar.
    """

    def __init__(self, x: int, y: int,
                 sweep_left: float  = 200.0,
                 sweep_right: float = 340.0,
                 vision_range: float = VISION_RANGE_DEFAULT,
                 sweep_period: float = CAMERA_SWEEP_PERIOD):
        self.x = x
        self.y = y
        self.sweep_left  = math.radians(sweep_left)
        self.sweep_right = math.radians(sweep_right)
        self.vision_range = vision_range
        self.sweep_period = sweep_period

        self._timer: float = 0.0
        self._current_angle: float = self.sweep_left
        self._going_right: bool = True

        # Nesne havuzu: görüş konisi köşe noktaları (GC kuralı)
        self._cone_pts: List[Tuple[float, float]] = [(0.0, 0.0)] * 7

    # ── GÜNCELLEME ────────────────────────────────────────────────────────
    def update(self, dt: float):
        # Sinüs tabanlı salınım — dt çarpımı (RULE 1)
        self._timer += dt
        t = (self._timer % self.sweep_period) / self.sweep_period   # 0..1
        # Lerp: left -> right -> left (sin eğrisi)
        lerp = (math.sin(t * math.pi * 2 - math.pi / 2) + 1) / 2
        self._current_angle = (
            self.sweep_left + (self.sweep_right - self.sweep_left) * lerp
        )

    # ── OYUNCU GÖZLEMİ ───────────────────────────────────────────────────
    def can_see(self, px: float, py: float,
                hide_spots: List[HideSpot]) -> bool:
        """
        Oyuncu görüş konisi içinde mi VE herhangi bir saklanma noktasında değil mi?
        """
        # Mesafe kontrolü
        dx = px - self.x
        dy = py - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > self.vision_range or dist < 1.0:
            return False

        # Açı kontrolü
        angle_to_player = math.atan2(dy, dx)
        half_fov = math.radians(VISION_ANGLE_DEFAULT / 2)

        # İki köşe açısının ortasını bul
        mid_angle = self.sweep_left + (self.sweep_right - self.sweep_left) * 0.5
        diff = abs(self._normalize_angle(angle_to_player - mid_angle))
        if diff > half_fov:
            return False

        # Saklanma noktasında mı?
        for spot in hide_spots:
            if spot.occupied and spot.contains(px, py):
                return False

        return True

    def _normalize_angle(self, a: float) -> float:
        while a >  math.pi: a -= 2 * math.pi
        while a < -math.pi: a += 2 * math.pi
        return a

    # ── ÇİZİM (fallback) ─────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, alert_level: int,
             camera_offset: Tuple[int, int] = (0, 0)):
        """Step 7 — kamera gövdesi + görüş konisi."""
        ox, oy = camera_offset
        cx = int(self.x + ox)
        cy = int(self.y + oy)

        # Renk: uyarı seviyesine göre
        if alert_level == ALERT_DETECTED:
            cone_color = _COL_DETECTED
            body_color = (255, 30, 30)
        elif alert_level == ALERT_SUSPICIOUS:
            cone_color = _COL_SUSPICIOUS
            body_color = (255, 180, 0)
        else:
            cone_color = _COL_UNDETECTED
            body_color = (0, 200, 100)

        # Görüş konisi (dolgulu üçgen)
        half_fov = math.radians(VISION_ANGLE_DEFAULT / 2)
        mid_angle = self.sweep_left + (self.sweep_right - self.sweep_left) * 0.5
        # 5 ara nokta ile yumuşak koni
        cone_surf = pygame.Surface(
            (int(self.vision_range * 2 + 4),
             int(self.vision_range * 2 + 4)),
            pygame.SRCALPHA
        )
        pts = [(cx, cy)]
        steps = 8
        for i in range(steps + 1):
            a = (self._current_angle - half_fov) + (2 * half_fov) * (i / steps)
            px2 = cx + math.cos(a) * self.vision_range
            py2 = cy + math.sin(a) * self.vision_range
            pts.append((px2, py2))
        if len(pts) >= 3:
            pygame.draw.polygon(surface, cone_color, pts)

        # Kamera gövdesi (küçük dikdörtgen)
        pygame.draw.rect(surface, body_color, (cx - 8, cy - 5, 16, 10))
        pygame.draw.rect(surface, (220, 220, 220), (cx - 8, cy - 5, 16, 10), 1)

        # Yön çizgisi
        lx = cx + int(math.cos(self._current_angle) * 30)
        ly = cy + int(math.sin(self._current_angle) * 30)
        pygame.draw.line(surface, body_color, (cx, cy), (lx, ly), 2)


# ─────────────────────────────────────────────────────────────────────────────
# 4. KROM MUHAFIZ (Stealth-aware)
# ─────────────────────────────────────────────────────────────────────────────

class ChromeGuard:
    """
    Gizlilik sistemiyle entegre devriye muhafızı.
    entities.py'deki CursedEnemy'den bağımsızdır — arena/fabrika bölümlerine özgü.
    """

    _STATES = ("PATROL", "SUSPICIOUS", "ALERT", "STUNNED")

    def __init__(self, x: float, y: float,
                 patrol_left: float, patrol_right: float,
                 vision_range: float = VISION_RANGE_DEFAULT,
                 vision_angle: float = VISION_ANGLE_DEFAULT):
        self.x = x
        self.y = y
        self.patrol_left  = patrol_left
        self.patrol_right = patrol_right
        self.patrol_dir   = 1   # +1 sağa, -1 sola
        self.patrol_speed = 80  # px/s (dt ile çarpılır — RULE 1)

        self.health     = 60
        self.max_health = 60
        self.is_active  = True

        self.state       = "PATROL"
        self.suspicion   = 0.0   # 0.0 .. 1.0
        self.alert_timer = 0.0   # Tespit sonrası kaç saniye geçti
        self.stun_timer  = 0.0

        self.vision_range = vision_range
        self.vision_angle = vision_angle

        self.rect   = pygame.Rect(int(x), int(y), 32, 48)
        self.facing = 1   # görüş yönü (+1 sağ, -1 sol)

        # Spawn kuyruğu — main.py bu listeyi her karede boşaltır
        self.spawn_queue: List[Dict] = []

        self._font = pygame.font.Font(None, 18)

    # ── GÜNCELLEME (her kare) ─────────────────────────────────────────────
    def update(self, dt: float, player_x: float, player_y: float,
               hide_spots: List[HideSpot]) -> int:
        """
        dt — delta time (RULE 1)
        Döndürdüğü int:
            ALERT_UNDETECTED / ALERT_SUSPICIOUS / ALERT_DETECTED
        """
        if not self.is_active:
            return ALERT_UNDETECTED

        if self.state == "STUNNED":
            self.stun_timer -= dt
            if self.stun_timer <= 0:
                self.state = "PATROL"
                self.suspicion = 0.0
            return ALERT_UNDETECTED

        # Devriye hareketi
        if self.state == "PATROL":
            self.x += self.patrol_dir * self.patrol_speed * dt  # RULE 1
            if self.x >= self.patrol_right:
                self.x = self.patrol_right
                self.patrol_dir = -1
                self.facing     = -1
            elif self.x <= self.patrol_left:
                self.x = self.patrol_left
                self.patrol_dir = 1
                self.facing     = 1
            self.rect.x = int(self.x)

        # Görüş konisi ile oyuncu tespiti
        in_sight = self._check_vision(player_x, player_y, hide_spots)

        if in_sight:
            self.suspicion = min(1.0, self.suspicion + SUSPICION_BUILD_RATE * dt)
        else:
            self.suspicion = max(0.0, self.suspicion - SUSPICION_DECAY_RATE * dt)

        # Durum geçişleri
        if self.suspicion >= 1.0 and self.state != "ALERT":
            self.state = "ALERT"
            self.alert_timer = 0.0
            self._on_detect(player_x, player_y)
            return ALERT_DETECTED
        elif 0.3 <= self.suspicion < 1.0 and self.state == "PATROL":
            self.state = "SUSPICIOUS"
            return ALERT_SUSPICIOUS
        elif self.suspicion < 0.3 and self.state == "SUSPICIOUS":
            self.state = "PATROL"

        if self.state == "ALERT":
            self.alert_timer += dt
            # Takip: muhafız oyuncuya doğru hareket eder
            dx = player_x - self.x
            if abs(dx) > 5:
                self.x += (1 if dx > 0 else -1) * self.patrol_speed * 1.5 * dt  # RULE 1
                self.facing = 1 if dx > 0 else -1
                self.rect.x = int(self.x)
            # 8 saniye sonra pes eder
            if self.alert_timer > 8.0:
                self.state      = "PATROL"
                self.suspicion  = 0.0
                self.alert_timer= 0.0
            return ALERT_DETECTED

        return ALERT_UNDETECTED if self.suspicion < 0.3 else ALERT_SUSPICIOUS

    def _check_vision(self, px: float, py: float, hide_spots: List[HideSpot]) -> bool:
        # Gizlenme kontrolü
        for spot in hide_spots:
            if spot.occupied and spot.contains(px, py):
                return False

        dx  = px - self.x
        dy  = py - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > self.vision_range:
            return False

        # Açı (muhafızın baktığı yön)
        guard_angle  = 0.0 if self.facing > 0 else math.pi
        player_angle = math.atan2(dy, dx)
        diff = abs(player_angle - guard_angle)
        if diff > math.pi:
            diff = 2 * math.pi - diff
        return diff <= math.radians(self.vision_angle / 2)

    def _on_detect(self, px: float, py: float):
        """Tespit anında alarm mesajı üretir."""
        self.spawn_queue.append({
            "type": "alert_bark",
            "text": random.choice(["ALARM! ALARM!", "DURDUR!", "HEDEF TESPİT!"]),
            "x": self.x,
            "y": self.y - 50
        })

    def take_damage(self, amount: int, lethal: bool = False) -> bool:
        """
        lethal=True   → HP sıfırlanır, öldü.
        lethal=False  → STUNNED durumuna düşer.
        Döndürdüğü bool: True = deaktive edildi.
        """
        if not lethal:
            self.state      = "STUNNED"
            self.stun_timer = 5.0
            self.suspicion  = 0.0
            return False
        else:
            self.health -= amount
            if self.health <= 0:
                self.is_active = False
                return True
            return False

    def stealth_kill(self, player_x: float, player_y: float,
                     reach: float = 90.0) -> bool:
        """
        Sessiz suikast kontrolü.
        Başarılı olabilmesi için iki şart:
          1) suspicion < 0.5  → Muhafız seni fark etmemiş (PATROL veya hafif SUSPICIOUS).
          2) Oyuncu, muhafızın arkasında → facing yönüyle oyuncunun pozisyonu ters tarafta.
             Yani:  facing=+1 (sağa bakıyor)  → oyuncu solda (player_x < self.x)
                    facing=-1 (sola bakıyor)   → oyuncu sağda (player_x > self.x)
          3) Oyuncu yeterince yakın (reach piksel içinde).

        Başarılıysa muhafızı anında deaktive eder ve True döndürür.
        main.py bu dönen True'yu kullanarak karma ve skor günceller.
        """
        if not self.is_active:
            return False
        if self.state in ("ALERT", "STUNNED"):
            return False

        # Şart 1: Şüphe barı düşük
        if self.suspicion >= 0.5:
            return False

        # Şart 2: Oyuncu arkada mı?
        #   facing=+1 → muhafız sağa bakıyor → sağ tarafı görüş konisi.
        #   Oyuncunun muhafızın ARKASINDA olması = oyuncu muhafızın solunda.
        dx = player_x - self.x
        dy = player_y - self.y
        dist = (dx * dx + dy * dy) ** 0.5

        # Şart 3: Mesafe kontrolü
        if dist > reach:
            return False

        behind = (self.facing > 0 and dx < 0) or (self.facing < 0 and dx > 0)
        if not behind:
            return False

        # Tüm şartlar sağlandı — sessiz suikast
        self.is_active = False
        self.health    = 0
        return True

    # ── ÇİZİM (fallback) ─────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, camera_offset: Tuple[int, int] = (0, 0)):
        if not self.is_active:
            return
        ox, oy = camera_offset
        draw_r = self.rect.move(ox, oy)

        # Durum rengi
        if self.state == "ALERT":
            border = (255, 30, 30)
        elif self.state == "SUSPICIOUS":
            border = (255, 180, 0)
        elif self.state == "STUNNED":
            border = (100, 100, 100)
        else:
            border = (150, 200, 255)

        # Gövde
        body_surf = pygame.Surface((draw_r.width, draw_r.height), pygame.SRCALPHA)
        body_surf.fill((*border[:3], 140))
        surface.blit(body_surf, draw_r.topleft)
        pygame.draw.rect(surface, border, draw_r, 2)

        # Etiket
        lbl = self._font.render(f"KROM [{self.state}]", True, border)
        surface.blit(lbl, (draw_r.x + 2, draw_r.y + 2))

        # Şüphe çubuğu
        if self.suspicion > 0:
            bar_w = draw_r.width
            fill  = int(bar_w * self.suspicion)
            pygame.draw.rect(surface, (40, 40, 0), (draw_r.x, draw_r.top - 8, bar_w, 5))
            bar_col = (255, 180, 0) if self.suspicion < 1.0 else (255, 30, 30)
            pygame.draw.rect(surface, bar_col, (draw_r.x, draw_r.top - 8, fill, 5))

        # HP çubuğu
        hp_pct = self.health / self.max_health
        hp_w   = int(draw_r.width * hp_pct)
        pygame.draw.rect(surface, (60, 0, 0),   (draw_r.x, draw_r.top - 15, draw_r.width, 5))
        pygame.draw.rect(surface, (200, 50, 50), (draw_r.x, draw_r.top - 15, hp_w, 5))

        # Görüş yönü oku
        arrow_x = draw_r.centerx + self.facing * 25
        pygame.draw.line(surface, border,
                         (draw_r.centerx, draw_r.centery),
                         (arrow_x, draw_r.centery), 2)


# ─────────────────────────────────────────────────────────────────────────────
# 5. GİZLİLİK SİSTEMİ YÖNETİCİSİ
# ─────────────────────────────────────────────────────────────────────────────

class StealthSystem:
    """
    Tüm kameraları, muhafızları ve saklanma noktalarını tek yerden yönetir.

    main.py'deki entegrasyon:
        stealth = StealthSystem()
        # Bölüm başında:
        stealth.setup_level(level_idx)
        # Her karede PLAYING state içinde:
        alert = stealth.update(dt, player_x, player_y)
        # Step 7'de (VFX/HUD sonrası):
        stealth.draw(game_canvas)
        # Olayları işle:
        events = stealth.poll_events()
    """

    def __init__(self):
        self.cameras:    List[SurveillanceCamera] = []
        self.guards:     List[ChromeGuard]        = []
        self.hide_spots: List[HideSpot]           = []

        self.global_alert: int  = ALERT_UNDETECTED
        self.player_hidden: bool = False

        # Yüksek alarm süresi (saniye)
        self._alert_cooldown: float = 0.0
        self._alert_duration: float = 12.0

        # Event kuyruğu (GC: temizlenip doldurulur)
        self._event_queue: List[Dict[str, Any]] = []

        # Stealth karma bonusu sayacı (her 3 saniye gizli geçişe +1 karma)
        self._stealth_timer: float = 0.0
        self._stealth_karma_interval: float = 8.0

    # ── BÖLÜM HAZIRLIĞI ───────────────────────────────────────────────────
    def setup_level(self, level_idx: int):
        """
        init_game() içinde çağrılır. Level veri sözlüğünden
        kamera / muhafız / saklanma noktalarını oluşturur.
        Data-driven: STEALTH_LEVEL_CONFIGS[level_idx] okunur.
        """
        self.cameras.clear()
        self.guards.clear()
        self.hide_spots.clear()
        self.global_alert = ALERT_UNDETECTED
        self.player_hidden = False
        self._alert_cooldown = 0.0
        self._stealth_timer  = 0.0
        self._event_queue.clear()

        config = STEALTH_LEVEL_CONFIGS.get(level_idx)
        if not config:
            return

        for cam_def in config.get("cameras", []):
            cam = SurveillanceCamera(
                x=cam_def["x"], y=cam_def["y"],
                sweep_left=cam_def.get("sweep_left", 200),
                sweep_right=cam_def.get("sweep_right", 340),
                vision_range=cam_def.get("range", VISION_RANGE_DEFAULT),
                sweep_period=cam_def.get("period", CAMERA_SWEEP_PERIOD),
            )
            self.cameras.append(cam)

        for g_def in config.get("guards", []):
            g = ChromeGuard(
                x=g_def["x"], y=g_def["y"],
                patrol_left=g_def["patrol_left"],
                patrol_right=g_def["patrol_right"],
                vision_range=g_def.get("range", VISION_RANGE_DEFAULT),
            )
            self.guards.append(g)

        for h_def in config.get("hide_spots", []):
            hs = HideSpot(
                x=h_def["x"], y=h_def["y"],
                width=h_def.get("w", 80),
                height=h_def.get("h", 100),
                label=h_def.get("label", "SAKLANMA")
            )
            self.hide_spots.append(hs)

    # ── GÜNCELLEME ────────────────────────────────────────────────────────
    def update(self, dt: float, player_x: float, player_y: float) -> int:
        """
        Her karede PLAYING state içinde çağrılır.
        Döndürdüğü int: ALERT_UNDETECTED | ALERT_SUSPICIOUS | ALERT_DETECTED
        """
        # Saklanma noktası kontrolü
        self.player_hidden = False
        for spot in self.hide_spots:
            if spot.contains(player_x, player_y):
                spot.occupied = True
                self.player_hidden = True
            else:
                spot.occupied = False

        # Kamera güncelleme
        cam_alert = ALERT_UNDETECTED
        for cam in self.cameras:
            cam.update(dt)
            if cam.can_see(player_x, player_y, self.hide_spots):
                cam_alert = ALERT_DETECTED

        # Muhafız güncelleme
        guard_alert = ALERT_UNDETECTED
        for guard in self.guards:
            if not guard.is_active:
                continue
            g_alert = guard.update(dt, player_x, player_y, self.hide_spots)
            if g_alert > guard_alert:
                guard_alert = g_alert
            # Muhafızın spawn kuyruğunu işle
            while guard.spawn_queue:
                item = guard.spawn_queue.pop()
                self._event_queue.append({"type": "guard_bark", "data": item})

        # Global uyarı seviyesi
        new_alert = max(cam_alert, guard_alert)

        if new_alert == ALERT_DETECTED and self.global_alert < ALERT_DETECTED:
            self._alert_cooldown = self._alert_duration
            self._fire_detection_event(player_x, player_y)

        if self.global_alert == ALERT_DETECTED:
            self._alert_cooldown -= dt
            if self._alert_cooldown <= 0:
                self.global_alert = ALERT_UNDETECTED
        else:
            self.global_alert = new_alert

        # Gizlilik karma bonusu
        if self.global_alert == ALERT_UNDETECTED and not self.player_hidden is False:
            self._stealth_timer += dt
            if self._stealth_timer >= self._stealth_karma_interval:
                self._stealth_timer = 0.0
                self._event_queue.append({
                    "type": "stealth_karma",
                    "delta": 1,
                    "text": "GİZLİLİK BONUS +1 KARMA"
                })

        return self.global_alert

    def _fire_detection_event(self, px: float, py: float):
        self._event_queue.append({
            "type": "player_detected",
            "x": px, "y": py,
            "text": "TESPİT EDİLDİN!"
        })

    # ── SUİKAST (F TUŞU) ──────────────────────────────────────────────────
    def try_stealth_kill(self, player_x: float, player_y: float,
                         reach: float = 90.0) -> Dict[str, Any]:
        """
        main.py F tuşuna basıldığında çağrılır.
        En yakın uygun muhafız üzerinde stealth_kill() dener.

        Döndürdüğü dict:
          {"success": True,  "guard_idx": i,  "x": gx, "y": gy}   → başarı
          {"success": False, "reason": "..."}                       → başarısız

        main.py bu sonucu kullanarak karma/skor günceller ve VFX tetikler.
        """
        best_idx  = -1
        best_dist = float("inf")

        for i, g in enumerate(self.guards):
            if not g.is_active:
                continue
            dx   = player_x - g.x
            dy   = player_y - g.y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_idx  = i

        if best_idx == -1:
            return {"success": False, "reason": "YAKINDA MUHAFIZ YOK"}

        g = self.guards[best_idx]

        # ChromeGuard.stealth_kill() tüm şartları kontrol eder
        killed = g.stealth_kill(player_x, player_y, reach)
        if killed:
            self._event_queue.append({
                "type": "stealth_kill",
                "guard_idx": best_idx,
                "x": g.x,
                "y": g.y
            })
            return {"success": True, "guard_idx": best_idx, "x": g.x, "y": g.y}

        # Başarısızlık nedenini belirle
        if best_dist > reach:
            reason = "ÇOK UZAK"
        elif g.suspicion >= 0.5:
            reason = "MUHAFIZ UYARILDI — GİZLİNİ KAYBET"
        elif g.state in ("ALERT", "STUNNED"):
            reason = f"MUHAFIZ DURUMU: {g.state}"
        else:
            reason = "ARKASINDA DEĞİLSİN"
        return {"success": False, "reason": reason}

    # ── MUHAFIZa hasar ────────────────────────────────────────────────────
    def hit_guard(self, guard_idx: int, damage: int, lethal: bool) -> bool:
        """
        main.py melee hit sonrası çağırır.
        lethal=False → STUNNED   lethal=True → ölüm
        Döndürdüğü bool: guard deaktive mi oldu?
        """
        if 0 <= guard_idx < len(self.guards):
            g = self.guards[guard_idx]
            killed = g.take_damage(damage, lethal)
            if lethal and killed:
                self._event_queue.append({"type": "guard_killed", "guard_idx": guard_idx})
            elif not lethal:
                self._event_queue.append({"type": "guard_stunned", "guard_idx": guard_idx})
            return killed
        return False

    def get_guard_at(self, player_rect: pygame.Rect, reach: int = 80) -> int:
        """
        Belirtilen mesafe içindeki ilk aktif muhafızın indeksini döndürür.
        Bulunamazsa -1.
        """
        for i, g in enumerate(self.guards):
            if not g.is_active:
                continue
            dist = abs(g.x - player_rect.centerx)
            if dist <= reach:
                return i
        return -1

    # ── OLAY KUYRUĞU ──────────────────────────────────────────────────────
    def poll_events(self) -> List[Dict[str, Any]]:
        """main.py her karede çağırır. GC: kopyalanıp temizlenir."""
        if not self._event_queue:
            return []
        out = list(self._event_queue)
        self._event_queue.clear()
        return out

    # ── ÇİZİM ─────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, camera_offset: Tuple[int, int] = (0, 0)):
        """
        main.py Step 7 (VFX katmanı) içinde çağrılır.
        Sıra: kamera konileri → muhafızlar → saklanma noktaları → uyarı HUD.
        """
        for cam in self.cameras:
            cam.draw(surface, self.global_alert, camera_offset)

        for g in self.guards:
            if g.is_active:
                g.draw(surface, camera_offset)

        for hs in self.hide_spots:
            hs.draw(surface, camera_offset)

        # Üst HUD: alarm banner
        if self.global_alert == ALERT_DETECTED:
            self._draw_alert_hud(surface)
        elif self.global_alert == ALERT_SUSPICIOUS:
            self._draw_suspicious_hud(surface)

    def _draw_alert_hud(self, surface: pygame.Surface):
        font = pygame.font.Font(None, 52)
        txt  = font.render("!! TESPİT EDİLDİN !!", True, (255, 30, 30))
        x    = (surface.get_width() - txt.get_width()) // 2
        surface.blit(txt, (x, 20))

    def _draw_suspicious_hud(self, surface: pygame.Surface):
        font = pygame.font.Font(None, 36)
        txt  = font.render("! Şüphe !", True, (255, 180, 0))
        x    = (surface.get_width() - txt.get_width()) // 2
        surface.blit(txt, (x, 20))

    # ── YARDIMCI ──────────────────────────────────────────────────────────
    def is_player_hidden(self) -> bool:
        return self.player_hidden

    def active_guard_count(self) -> int:
        return sum(1 for g in self.guards if g.is_active)

    def reset(self):
        """Yeni bölüm başında çağrılır."""
        self.cameras.clear()
        self.guards.clear()
        self.hide_spots.clear()
        self.global_alert = ALERT_UNDETECTED
        self.player_hidden = False
        self._alert_cooldown = 0.0
        self._stealth_timer  = 0.0
        self._event_queue.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 6. BÖLÜM KONFIGÜRASYONLARI — DATA-DRIVEN
# ─────────────────────────────────────────────────────────────────────────────
# Anahtar = level_idx (settings.py EASY_MODE_LEVELS ile eşleşir)
# Pixel art entegrasyonunda kamera/muhafız sprite yolları buraya eklenir.

STEALTH_LEVEL_CONFIGS: Dict[int, Dict] = {

    # Bölüm 4: Fabrika Girişi — güvenlik kapısı
    # Kameralar kaldırıldı: Fabrika ortamında kamera yok, sadece ChromeGuard + saklanma noktaları.
    4: {
        "guards": [
            {"x": 700,  "y": 960,  "patrol_left": 550,  "patrol_right": 900},
            {"x": 1300, "y": 960,  "patrol_left": 1100, "patrol_right": 1500},
        ],
        "hide_spots": [
            {"x": 480, "y": 880,  "w": 90,  "h": 110, "label": "ÇÖPLER"},
            {"x": 950, "y": 880,  "w": 80,  "h": 110, "label": "VARIL"},
        ],
    },

    # Bölüm 6: Konveyör Bant Alanı
    # Kameralar kaldırıldı: Fabrika ortamında kamera yok, sadece ChromeGuard + saklanma noktaları.
    6: {
        "guards": [
            {"x": 600,  "y": 960, "patrol_left": 400,  "patrol_right": 800},
            {"x": 1200, "y": 960, "patrol_left": 1000, "patrol_right": 1400},
        ],
        "hide_spots": [
            {"x": 300,  "y": 700,  "w": 100, "h": 120, "label": "TÜNEL"},
            {"x": 750,  "y": 700,  "w": 100, "h": 120, "label": "TÜNEL"},
            {"x": 1250, "y": 700,  "w": 100, "h": 120, "label": "TÜNEL"},
        ],
    },

    # Bölüm 7: Güvenlik Noktaları (Beat Arena ile birlikte çalışır)
    # Kameralar kaldırıldı: Fabrika ortamında kamera yok, sadece ChromeGuard + saklanma noktaları.
    7: {
        "guards": [
            {"x": 350,  "y": 960, "patrol_left": 200,  "patrol_right": 600},
            {"x": 900,  "y": 960, "patrol_left": 700,  "patrol_right": 1100},
            {"x": 1500, "y": 960, "patrol_left": 1300, "patrol_right": 1700},
        ],
        "hide_spots": [
            {"x": 180,  "y": 860,  "w": 90, "h": 110, "label": "KUTU"},
            {"x": 620,  "y": 860,  "w": 90, "h": 110, "label": "KUTU"},
            {"x": 1120, "y": 860,  "w": 90, "h": 110, "label": "KUTU"},
        ],
    },

    # Bölüm 8: İstihbarat Odası
    # Kameralar kaldırıldı: Fabrika ortamında kamera yok, sadece ChromeGuard + saklanma noktaları.
    8: {
        "guards": [
            {"x": 800,  "y": 960, "patrol_left": 600,  "patrol_right": 1000, "range": 250},
            {"x": 1600, "y": 960, "patrol_left": 1400, "patrol_right": 1800, "range": 250},
        ],
        "hide_spots": [
            {"x": 450,  "y": 850,  "w": 100, "h": 120, "label": "HAVALANDIRMA"},
            {"x": 1050, "y": 850,  "w": 100, "h": 120, "label": "DOLAP"},
            {"x": 1700, "y": 850,  "w": 100, "h": 120, "label": "SERVER KASASI"},
        ],
    },

    # Bölüm 9: Siyah Kapı + Tren İstasyonu
    # Kameralar kaldırıldı: Fabrika ortamında kamera yok, sadece ChromeGuard + saklanma noktaları.
    9: {
        "guards": [
            {"x": 400,  "y": 960, "patrol_left": 250,  "patrol_right": 600,  "range": 270},
            {"x": 900,  "y": 960, "patrol_left": 700,  "patrol_right": 1100, "range": 270},
            {"x": 1400, "y": 960, "patrol_left": 1200, "patrol_right": 1650, "range": 270},
        ],
        "hide_spots": [
            {"x": 200,  "y": 840, "w": 110, "h": 130, "label": "KONTEYNIR"},
            {"x": 650,  "y": 840, "w": 110, "h": 130, "label": "KONTEYNIR"},
            {"x": 1150, "y": 840, "w": 110, "h": 130, "label": "KONTEYNIR"},
            {"x": 1700, "y": 840, "w": 110, "h": 130, "label": "TREN ALTI"},
        ],
    },

    # ──────────────────────────────────────────────────────────────────────────
    # Bölüm 16: EGEMENLERİN MALİKANESİ — Devasa gizlilik haritası
    # ──────────────────────────────────────────────────────────────────────────
    # Platform düzeni (init_game tarafından üretilir, koordinatlar buraya referans):
    #
    #   ZEMİN KAT  (y ≈ 980): Giriş holü, şömine salonu, mutfak koridoru
    #   1. KAT     (y ≈ 800): Kütüphane, misafir odaları, balkon
    #   2. KAT     (y ≈ 620): Efendi dairesi, teras, gizli oda kapısı
    #   ÇATI       (y ≈ 440): Teras, havalandırma, çatı bacaları
    #   GİZLİ KAT  (y ≈ 260): Gizli kasa odası (HEDEF)
    #
    # Harita genişliği: ~4000 px — oyuncu hem sağa hem sola hareket edebilir.
    # ──────────────────────────────────────────────────────────────────────────
    16: {
        "cameras": [
            # ── ZEMİN KAT KAMERALARI ──
            {"x": 350,  "y": 950, "sweep_left": 190, "sweep_right": 330, "range": 280, "period": 4.0},
            {"x": 800,  "y": 950, "sweep_left": 170, "sweep_right": 310, "range": 300, "period": 3.5},
            {"x": 1250, "y": 950, "sweep_left": 200, "sweep_right": 340, "range": 280, "period": 4.5},
            {"x": 1700, "y": 950, "sweep_left": 180, "sweep_right": 320, "range": 290, "period": 3.8},
            {"x": 2200, "y": 950, "sweep_left": 195, "sweep_right": 335, "range": 300, "period": 4.2},
            {"x": 2700, "y": 950, "sweep_left": 175, "sweep_right": 315, "range": 275, "period": 3.6},
            {"x": 3200, "y": 950, "sweep_left": 185, "sweep_right": 325, "range": 285, "period": 4.0},
            {"x": 3700, "y": 950, "sweep_left": 200, "sweep_right": 340, "range": 280, "period": 3.5},
            # ── 1. KAT KAMERALARI ──
            {"x": 600,  "y": 770, "sweep_left": 200, "sweep_right": 340, "range": 260, "period": 3.0},
            {"x": 1100, "y": 770, "sweep_left": 180, "sweep_right": 320, "range": 260, "period": 2.8},
            {"x": 1600, "y": 770, "sweep_left": 190, "sweep_right": 330, "range": 270, "period": 3.2},
            {"x": 2100, "y": 770, "sweep_left": 200, "sweep_right": 340, "range": 255, "period": 2.5},
            {"x": 2600, "y": 770, "sweep_left": 185, "sweep_right": 325, "range": 265, "period": 3.0},
            {"x": 3100, "y": 770, "sweep_left": 195, "sweep_right": 335, "range": 260, "period": 2.8},
            {"x": 3600, "y": 770, "sweep_left": 175, "sweep_right": 315, "range": 270, "period": 3.3},
            # ── 2. KAT KAMERALARI (daha kısa aralıklı — güvenlik yüksek) ──
            {"x": 500,  "y": 590, "sweep_left": 200, "sweep_right": 340, "range": 250, "period": 2.5},
            {"x": 950,  "y": 590, "sweep_left": 185, "sweep_right": 325, "range": 250, "period": 2.3},
            {"x": 1400, "y": 590, "sweep_left": 195, "sweep_right": 335, "range": 245, "period": 2.8},
            {"x": 1900, "y": 590, "sweep_left": 200, "sweep_right": 340, "range": 255, "period": 2.5},
            {"x": 2400, "y": 590, "sweep_left": 180, "sweep_right": 320, "range": 250, "period": 2.2},
            {"x": 2900, "y": 590, "sweep_left": 190, "sweep_right": 330, "range": 255, "period": 2.6},
            {"x": 3400, "y": 590, "sweep_left": 200, "sweep_right": 340, "range": 250, "period": 2.4},
            # ── ÇATI / GİZLİ KAT KAMERALARI ──
            {"x": 1800, "y": 410, "sweep_left": 195, "sweep_right": 345, "range": 240, "period": 2.0},
            {"x": 2800, "y": 410, "sweep_left": 185, "sweep_right": 335, "range": 240, "period": 1.9},
            {"x": 3500, "y": 230, "sweep_left": 190, "sweep_right": 350, "range": 220, "period": 1.8},  # Kasanın koruması
        ],
        "guards": [
            # ── ZEMİN KAT DEVRİYELERİ (7 muhafız) ──
            {"x": 250,  "y": 980, "patrol_left": 100,  "patrol_right": 500,  "range": 280},
            {"x": 700,  "y": 980, "patrol_left": 500,  "patrol_right": 1000, "range": 280},
            {"x": 1150, "y": 980, "patrol_left": 950,  "patrol_right": 1400, "range": 280},
            {"x": 1600, "y": 980, "patrol_left": 1400, "patrol_right": 1900, "range": 280},
            {"x": 2100, "y": 980, "patrol_left": 1900, "patrol_right": 2400, "range": 280},
            {"x": 2600, "y": 980, "patrol_left": 2400, "patrol_right": 2900, "range": 285},
            {"x": 3200, "y": 980, "patrol_left": 2900, "patrol_right": 3700, "range": 285},
            # ── 1. KAT DEVRİYELERİ (5 muhafız) ──
            {"x": 500,  "y": 800, "patrol_left": 200,  "patrol_right": 800,  "range": 260},
            {"x": 1100, "y": 800, "patrol_left": 800,  "patrol_right": 1400, "range": 260},
            {"x": 1700, "y": 800, "patrol_left": 1400, "patrol_right": 2100, "range": 265},
            {"x": 2400, "y": 800, "patrol_left": 2100, "patrol_right": 2800, "range": 260},
            {"x": 3100, "y": 800, "patrol_left": 2800, "patrol_right": 3800, "range": 270},
            # ── 2. KAT DEVRİYELERİ (4 muhafız — daha dar, daha keskin görüş) ──
            {"x": 600,  "y": 620, "patrol_left": 300,  "patrol_right": 900,  "range": 250},
            {"x": 1300, "y": 620, "patrol_left": 900,  "patrol_right": 1700, "range": 255},
            {"x": 2100, "y": 620, "patrol_left": 1700, "patrol_right": 2600, "range": 250},
            {"x": 2900, "y": 620, "patrol_left": 2600, "patrol_right": 3500, "range": 255},
            # ── GİZLİ KAT BEKÇİSİ (2 muhafız — kasanın kapısı önünde sabit patroli) ──
            {"x": 3400, "y": 440, "patrol_left": 3200, "patrol_right": 3700, "range": 220},
            {"x": 3650, "y": 260, "patrol_left": 3500, "patrol_right": 3850, "range": 200},
        ],
        "hide_spots": [
            # ── ZEMİN KAT SAKLANMA YERLERİ ──
            {"x": 150,  "y": 890, "w": 90,  "h": 110, "label": "PERDE"},
            {"x": 420,  "y": 890, "w": 80,  "h": 110, "label": "KANEPE ARKASI"},
            {"x": 650,  "y": 890, "w": 100, "h": 110, "label": "ŞÖMINE KOVUĞI"},
            {"x": 920,  "y": 890, "w": 90,  "h": 110, "label": "BÜFE DOLABI"},
            {"x": 1180, "y": 890, "w": 85,  "h": 110, "label": "PERDE"},
            {"x": 1450, "y": 890, "w": 95,  "h": 110, "label": "VAZO GRUBU"},
            {"x": 1720, "y": 890, "w": 80,  "h": 110, "label": "KILER KAPISI"},
            {"x": 2000, "y": 890, "w": 90,  "h": 110, "label": "PERDE"},
            {"x": 2280, "y": 890, "w": 100, "h": 110, "label": "BÜYÜK VARIL"},
            {"x": 2560, "y": 890, "w": 85,  "h": 110, "label": "MUTFAK TEZGAHI"},
            {"x": 2830, "y": 890, "w": 90,  "h": 110, "label": "PERDE"},
            {"x": 3100, "y": 890, "w": 95,  "h": 110, "label": "KANEPE ARKASI"},
            {"x": 3380, "y": 890, "w": 80,  "h": 110, "label": "HALKA KASASI"},
            {"x": 3650, "y": 890, "w": 90,  "h": 110, "label": "PERDE"},
            # ── 1. KAT SAKLANMA YERLERİ ──
            {"x": 300,  "y": 710, "w": 90,  "h": 100, "label": "KİTAP RAFI"},
            {"x": 600,  "y": 710, "w": 80,  "h": 100, "label": "PERDE"},
            {"x": 900,  "y": 710, "w": 95,  "h": 100, "label": "DOLAP"},
            {"x": 1200, "y": 710, "w": 85,  "h": 100, "label": "BÜYÜK VAZO"},
            {"x": 1500, "y": 710, "w": 90,  "h": 100, "label": "PERDE"},
            {"x": 1800, "y": 710, "w": 80,  "h": 100, "label": "KOLTUK ARKASI"},
            {"x": 2100, "y": 710, "w": 95,  "h": 100, "label": "BOYA TUVALI"},
            {"x": 2400, "y": 710, "w": 85,  "h": 100, "label": "PERDE"},
            {"x": 2700, "y": 710, "w": 90,  "h": 100, "label": "PİYANO ARKASI"},
            {"x": 3000, "y": 710, "w": 80,  "h": 100, "label": "DOLAP"},
            {"x": 3300, "y": 710, "w": 95,  "h": 100, "label": "PERDE"},
            {"x": 3600, "y": 710, "w": 85,  "h": 100, "label": "KANEPE"},
            # ── 2. KAT SAKLANMA YERLERİ ──
            {"x": 400,  "y": 530, "w": 85,  "h": 100, "label": "YATAK ALTI"},
            {"x": 700,  "y": 530, "w": 80,  "h": 100, "label": "PERDE"},
            {"x": 1000, "y": 530, "w": 90,  "h": 100, "label": "GARDROP"},
            {"x": 1350, "y": 530, "w": 85,  "h": 100, "label": "PERDE"},
            {"x": 1700, "y": 530, "w": 80,  "h": 100, "label": "ŞÖVALE ARKASI"},
            {"x": 2050, "y": 530, "w": 90,  "h": 100, "label": "GARDROP"},
            {"x": 2400, "y": 530, "w": 85,  "h": 100, "label": "PERDE"},
            {"x": 2750, "y": 530, "w": 80,  "h": 100, "label": "BÜYÜK BAVUL"},
            {"x": 3100, "y": 530, "w": 90,  "h": 100, "label": "PERDE"},
            {"x": 3450, "y": 530, "w": 85,  "h": 100, "label": "DOLAP"},
            # ── GİZLİ KAT SAKLANMA YERLERİ (az ama kritik) ──
            {"x": 1700, "y": 360, "w": 90,  "h": 90,  "label": "HAVALANDIRMA BACASI"},
            {"x": 2500, "y": 360, "w": 80,  "h": 90,  "label": "TAVAN BOŞLUĞU"},
            {"x": 3200, "y": 180, "w": 100, "h": 90,  "label": "KASA ODASI DOLABI"},
        ],
    },
}


# Global singleton — main.py'de: from stealth_system import stealth_system
stealth_system = StealthSystem()