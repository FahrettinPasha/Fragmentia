# combat_system.py
# ============================================================
#  FRAGMENTIA — Dövüş Sistemi (Beat 'em up + Action-Platform)
#
#  Bu modül iki yeni oyun mekaniği katmanı ekler:
#
#  1) BeatArenaManager   — "beat_arena" tipi bölümler için
#     kamera durur, düşman dalgaları sahneye girer, hepsi
#     yenilince arena temizlenir ve oyun devam eder.
#
#  2) ComboSystem        — yakın dövüş kombo zinciri.
#     J/K tuşlarıyla hafif/ağır vuruş yapılır,
#     COMBO_CHAINS sözlüğüne göre özel finişer tetiklenir.
#
#  3) MeleeHitbox        — geçici yakın dövüş çarpışma kutusu.
#     Vuruş animasyon frameleriyle senkron.
#
#  4) ArenaEnemy         — beat-em-up bölümleri için yer tabanlı
#     düşman tipi. Yana hareket eder, oyuncuya yaklaşır,
#     blok/saldırı döngüsü vardır.
#
#  5) ArenaDropReward    — dalga temizleme ödülleri (enerji orbu).
#
#  Mimariye Uyum Kuralları (agent.md):
#   - Tüm draw() metotlarında PLACEHOLDER + fallback mevcut.
#   - Hareketler dt / frame_mul ile çarpılıyor.
#   - Ses / asset yükleme __init__ içinde, döngü dışında.
#   - Z-İndex'e dokunulmadı — draw() yalnızca kendini çizer.
# ============================================================

import pygame
import math
import random
from settings import (
    LOGICAL_WIDTH, LOGICAL_HEIGHT, THEMES,
    CURSED_PURPLE, CURSED_RED, GLITCH_BLACK,
    PLAYER_SPEED, GRAVITY, WHITE
)

# ────────────────────────────────────────────────
# SABITLER
# ────────────────────────────────────────────────

# Kombo zinciri tanımları:
#   anahtar  → (hafif/ağır) dizisi ("L"=light, "H"=heavy)
#   değer    → {"name": str, "damage_mult": float, "vfx": str, "karma": int}
COMBO_CHAINS = {
    ("L", "L", "L"): {
        "name": "ÜÇ DARBE",
        "damage_mult": 1.5,
        "vfx": "spark",
        "karma": 3,
        "score_bonus": 200
    },
    ("L", "L", "H"): {
        "name": "KIRIŞ VURUŞU",
        "damage_mult": 2.0,
        "vfx": "shockwave",
        "karma": 5,
        "score_bonus": 400
    },
    ("H", "H"): {
        "name": "ÇİFT KAMA",
        "damage_mult": 2.2,
        "vfx": "lightning",
        "karma": 4,
        "score_bonus": 350
    },
    ("L", "H", "L", "H"): {
        "name": "FRAG MANTRASI",
        "damage_mult": 3.0,
        "vfx": "explosion",
        "karma": 8,
        "score_bonus": 800
    },
    ("H", "L", "H"): {
        "name": "NEKSİS PARÇALAMA",
        "damage_mult": 2.7,
        "vfx": "shockwave",
        "karma": 6,
        "score_bonus": 600
    },
}

# Kombo girişi için pencere süresi (saniye)
COMBO_WINDOW   = 1.2
# Maksimum kombo derinliği
MAX_COMBO_DEPTH = 4
# Hafif / Ağır vuruş temel hasarı
LIGHT_DAMAGE   = 20
HEAVY_DAMAGE   = 40
# Melee hitbox yarı genişliği / yüksekliği
MELEE_REACH    = 80    # piksel
MELEE_HEIGHT   = 60

# Arena düşmanı renkleri
ARENA_GRUNT_COLOR   = (180,  30,  30)
ARENA_BRUTE_COLOR   = (150,  20, 200)
ARENA_SPEEDER_COLOR = ( 30, 180, 180)
ARENA_SHIELD_COLOR  = ( 80,  80, 220)

# ────────────────────────────────────────────────
# YARDIMCI: basit etiket çizici
# ────────────────────────────────────────────────
_FONT_CACHE: dict = {}

def _get_font(size: int) -> pygame.font.Font:
    if size not in _FONT_CACHE:
        _FONT_CACHE[size] = pygame.font.Font(None, size)
    return _FONT_CACHE[size]


def _draw_label(surface, text, x, y, color, size=18):
    font = _get_font(size)
    surf = font.render(text, True, color)
    surface.blit(surf, (x - surf.get_width() // 2, y))


# ════════════════════════════════════════════════
#  1. MeleeHitbox — Geçici çarpışma kutusu
# ════════════════════════════════════════════════
class MeleeHitbox:
    """
    Oyuncunun vuruş yaptığı andaki geçici çarpışma bölgesi.
    ComboSystem tarafından oluşturulur, birkaç frame sonra yok olur.

    active     → bu frame çarpışma aktif mi?
    direction  → +1 sağa, -1 sola
    hit_set    → aynı vuruşta iki kez hasar almayı engeller
    """

    # Oyuncu hitbox sabitleri (main.py PLAYER_W/H ile senkron)
    _PLAYER_W = 30
    _PLAYER_H = 30

    def __init__(self, player_x: float, player_y: float,
                 direction: int, life_frames: int = 6,
                 reach: int = MELEE_REACH, height: int = MELEE_HEIGHT,
                 is_heavy: bool = False):
        self.direction    = direction
        self.life         = life_frames
        self.is_heavy     = is_heavy
        self.active       = True
        self.hit_set: set = set()

        # Oyuncu dikey merkezi
        player_cy = player_y + self._PLAYER_H // 2   # player_y + 15

        # Hitbox oyuncunun kenarından başlar, ileri uzanır
        if direction >= 0:
            hx = int(player_x + self._PLAYER_W)      # sağ kenardan başla
        else:
            hx = int(player_x - reach)                # sol tarafa uzat

        # *** DÜZELTME: Oyuncunun ayak noktasından yukarı 90px kapsasın
        # player_y + PLAYER_H = ayaklar (zemin seviyesi)
        # Oradan 90px yukarısına kadar = düşman gövdesinin tamamı
        hit_height = 90
        player_feet = int(player_y + self._PLAYER_H)   # zemin seviyesi
        hy = player_feet - hit_height                   # yukarı doğru uzat

        self.rect = pygame.Rect(hx, hy, reach, hit_height)

        # Ağır vuruşta kutu daha geniş ve biraz daha uzun
        if is_heavy:
            self.rect.inflate_ip(24, 20)

    # ── Güncelleme ─────────────────────────────────────────
    def update(self):
        self.life -= 1
        if self.life <= 0:
            self.active = False

    # ── Çizim (PLACEHOLDER) ────────────────────────────────
    def draw(self, surface, camera_offset=(0, 0)):
        """[PLACEHOLDER] Turuncu/kırmızı yarı-saydam dikdörtgen — vuruş yönü ok ile."""
        if not self.active:
            return
        ox, oy  = camera_offset
        draw_r  = self.rect.move(ox, oy)
        color   = CURSED_RED if self.is_heavy else (255, 150, 50)
        alpha   = max(40, int(220 * self.life / 8))

        try:
            s = pygame.Surface((draw_r.width, draw_r.height), pygame.SRCALPHA)
            s.fill((*color, alpha))
            surface.blit(s, draw_r.topleft)
        except Exception:
            pass
        pygame.draw.rect(surface, color, draw_r, 3)


# ════════════════════════════════════════════════
#  2. ComboSystem — Kombo zinciri yöneticisi
# ════════════════════════════════════════════════
class ComboSystem:
    """
    Yakın dövüş kombo mantığını yönetir.

    Kullanım (main.py içinde):
        combo_sys = ComboSystem()

        # Tuş basışında:
        if event.key == pygame.K_j:
            result = combo_sys.input_light(player_x, player_y, player_direction)
        if event.key == pygame.K_k:
            result = combo_sys.input_heavy(player_x, player_y, player_direction)

        # Her frame:
        combo_sys.update(dt)
        hit_result = combo_sys.check_hits(all_enemies)
        if hit_result:
            score += hit_result['score_bonus']
            ...

        # Draw (VFX yüzeyine, oyuncu render sonrası):
        combo_sys.draw(vfx_surface)
    """

    def __init__(self):
        self.chain: list[str]         = []      # "L" / "H" dizisi
        self.window_timer: float      = 0.0     # Geri sayım
        self.current_hitbox: MeleeHitbox | None = None
        self.last_result: dict | None = None    # Son tetiklenen kombo
        self.display_timer: float     = 0.0     # Kombo adı ekranda süre
        self.hit_count: int           = 0       # Streak sayısı (HUD)
        self._pending_vfx: list       = []      # (tür, x, y) kuyruğu

    # ── Hafif / Ağır Vuruş Girişi ──────────────────────────
    def input_light(self, px: float, py: float, direction: int) -> dict | None:
        self.chain.append("L")
        self.window_timer = COMBO_WINDOW
        self.current_hitbox = MeleeHitbox(px, py, direction, 6, is_heavy=False)
        return self._check_combo()

    def input_heavy(self, px: float, py: float, direction: int) -> dict | None:
        self.chain.append("H")
        self.window_timer = COMBO_WINDOW
        self.current_hitbox = MeleeHitbox(px, py, direction, 8, is_heavy=True)
        return self._check_combo()

    # ── Kombo Kontrolü ─────────────────────────────────────
    def _check_combo(self) -> dict | None:
        if len(self.chain) > MAX_COMBO_DEPTH:
            self.chain = self.chain[-MAX_COMBO_DEPTH:]

        key = tuple(self.chain)
        result = COMBO_CHAINS.get(key)
        if result:
            self.last_result    = result
            self.display_timer  = 2.5
            self.chain.clear()
            return result

        # Kısmi eşleşme var mı?  → zinciri koru
        for chain_key in COMBO_CHAINS:
            if chain_key[:len(self.chain)] == tuple(self.chain):
                return None   # Devam edebilir

        # Hiçbir şeye uymadı → sıfırla
        self.chain.clear()
        return None

    # ── Çarpışma Tespiti ───────────────────────────────────
    def check_hits(self, enemies_group) -> list[dict]:
        """
        Aktif hitbox ile düşmanlara çarptı mı kontrol eder.
        Her çarpışma için {'enemy': ..., 'damage': int, 'combo': dict|None}
        listesi döndürür.  Hasar hesabı main.py'e bırakılmıştır.
        """
        hits = []
        if not self.current_hitbox or not self.current_hitbox.active:
            return hits

        for enemy in enemies_group:
            if id(enemy) in self.current_hitbox.hit_set:
                continue
            if self.current_hitbox.rect.colliderect(enemy.rect):
                self.current_hitbox.hit_set.add(id(enemy))
                base_dmg = HEAVY_DAMAGE if self.current_hitbox.is_heavy else LIGHT_DAMAGE
                mult     = self.last_result["damage_mult"] if self.last_result else 1.0
                vfx_type = self.last_result["vfx"] if self.last_result else "spark"
                hits.append({
                    "enemy":       enemy,
                    "damage":      int(base_dmg * mult),
                    "combo":       self.last_result,
                    "vfx_type":    vfx_type,
                    "hit_pos":     enemy.rect.center
                })
                self.hit_count += 1
                # VFX kuyruğuna ekle (main.py okur)
                self._pending_vfx.append((vfx_type, *enemy.rect.center))
        return hits

    def pop_vfx(self) -> list:
        """main.py her frame bunu çağırıp VFX'leri kuyruktan alır."""
        out = self._pending_vfx.copy()
        self._pending_vfx.clear()
        return out

    # ── Güncelleme ─────────────────────────────────────────
    def update(self, dt: float):
        # Kombo penceresi geri sayımı
        if self.window_timer > 0:
            self.window_timer -= dt
            if self.window_timer <= 0:
                self.chain.clear()
                self.hit_count = 0
        # Sonuç gösterim süresi
        if self.display_timer > 0:
            self.display_timer -= dt
            if self.display_timer <= 0:
                self.last_result = None
        # Hitbox güncelle
        if self.current_hitbox and self.current_hitbox.active:
            self.current_hitbox.update()

    # ── Çizim ──────────────────────────────────────────────
    def draw(self, surface, camera_offset=(0, 0)):
        """PLACEHOLDER: Hitbox çerçevesi + kombo adı."""
        if self.current_hitbox:
            self.current_hitbox.draw(surface, camera_offset)

        if self.last_result and self.display_timer > 0:
            alpha = min(255, int(255 * self.display_timer / 2.5))
            cx    = LOGICAL_WIDTH // 2
            cy    = 120
            color = (255, 220, 50)
            _draw_label(surface, f"★ {self.last_result['name']} ★", cx, cy, color, 36)
            mult_text = f"x{self.last_result['damage_mult']:.1f}  +" \
                        f"{self.last_result['score_bonus']} SKOR"
            _draw_label(surface, mult_text, cx, cy + 36, (200, 200, 255), 22)

    # ── HUD Bilgisi ────────────────────────────────────────
    def get_hud_info(self) -> dict:
        return {
            "chain":      list(self.chain),
            "hit_count":  self.hit_count,
            "last_combo": self.last_result["name"] if self.last_result else "",
            "window":     self.window_timer > 0
        }

    def reset(self):
        self.chain.clear()
        self.window_timer   = 0.0
        self.current_hitbox = None
        self.last_result    = None
        self.display_timer  = 0.0
        self.hit_count      = 0
        self._pending_vfx.clear()


# ════════════════════════════════════════════════
#  3. ArenaEnemy — Beat 'em up düşman tipi
# ════════════════════════════════════════════════
class ArenaEnemy(pygame.sprite.Sprite):
    """
    Yere bağlı, oyuncuya doğru yürüyen beat-em-up düşmanı.
    Türler: grunt, brute, speeder, shielder

    Durum makinesi: IDLE → WALK → ATTACK → STUN → DEAD

    PLACEHOLDER draw() — sadece hitbox + etiket.
    [TODO - PIXEL ART]: Her tür için ayrı sprite sheet row haritası.
    """

    # Tür tabanlı istatistikler
    STATS = {
        "grunt":   {"hp": 60,  "speed": 2.5, "dmg": 15,  "atk_range": 55,  "color": ARENA_GRUNT_COLOR},
        "brute":   {"hp": 180, "speed": 1.3, "dmg": 35,  "atk_range": 70,  "color": ARENA_BRUTE_COLOR},
        "speeder": {"hp": 40,  "speed": 4.5, "dmg": 10,  "atk_range": 45,  "color": ARENA_SPEEDER_COLOR},
        "shielder":{"hp": 100, "speed": 1.8, "dmg": 20,  "atk_range": 60,  "color": ARENA_SHIELD_COLOR},
    }

    def __init__(self, x: float, y: float, enemy_type: str = "grunt"):
        super().__init__()
        stats = self.STATS.get(enemy_type, self.STATS["grunt"])

        self.enemy_type  = enemy_type
        self.x           = float(x)
        self.y           = float(y)
        self.speed       = stats["speed"]
        self.health      = stats["hp"]
        self.max_health  = stats["hp"]
        self.damage      = stats["dmg"]
        self.atk_range   = stats["atk_range"]
        self.color       = stats["color"]
        self.is_active   = True

        # Boyut (tür bazlı)
        w = 55 if enemy_type == "brute" else (30 if enemy_type == "speeder" else 40)
        h = 80 if enemy_type == "brute" else (55 if enemy_type == "speeder" else 70)
        self.rect = pygame.Rect(int(self.x), int(self.y - h), w, h)

        # Durum makinesi
        self.state       = "WALK"
        self.state_timer = 0.0
        self.direction   = 1     # +1 sağa, -1 sola
        self.stun_timer  = 0.0
        self.atk_cooldown = 0.0
        self.is_blocking = (enemy_type == "shielder")  # Shielder başlangıçta bloklu

        # Minimal parçacık kuyruğu (main.py okur)
        self.spawn_queue: list = []

    # ── Hasar al ───────────────────────────────────────────
    def take_damage(self, amount: int, bypass_block: bool = False) -> bool:
        """True döndüğünde düşman öldü."""
        if not self.is_active:
            return False
        if self.is_blocking and not bypass_block:
            amount = max(1, amount // 4)   # Blok %75 azaltma
        self.health -= amount
        if self.health <= 0:
            self.is_active = False
            self.state     = "DEAD"
            return True
        self.stun_timer = 0.15  # Kısa stun
        return False

    # ── Güncelleme ─────────────────────────────────────────
    def update(self, dt: float, player_x: float, player_y: float,
               camera_speed: float = 0.0, frame_mul: float = 1.0):
        if not self.is_active:
            return

        # Kamera kayması
        self.x -= camera_speed * frame_mul
        self.rect.x = int(self.x)

        # Stun
        if self.stun_timer > 0:
            self.stun_timer -= dt
            self.state = "STUN"
            return
        else:
            if self.state == "STUN":
                self.state = "WALK"

        self.state_timer += dt
        self.atk_cooldown = max(0.0, self.atk_cooldown - dt)

        # *** DÜZELTME: player_x sol kenar — merkeze çevir ***
        player_cx = player_x + 15   # PLAYER_W // 2
        player_cy = player_y + 15   # PLAYER_H // 2
        dx   = player_cx - self.rect.centerx
        dist = abs(dx)

        # Shielder blok kararı
        if self.enemy_type == "shielder":
            self.is_blocking = (dist > self.atk_range * 1.5)

        if self.state == "WALK":
            if dist < self.atk_range:
                self.state       = "ATTACK"
                self.state_timer = 0.0
            else:
                self.direction = 1 if dx > 0 else -1
                self.x        += self.direction * self.speed * frame_mul
                self.rect.x    = int(self.x)

        elif self.state == "ATTACK":
            if self.state_timer > 0.4 and self.atk_cooldown <= 0:
                # Saldırı gerçekleşti — spawn_queue'ya ekle
                # x/y: düşmanın mevcut konumu (main.py okur)
                self.spawn_queue.append({
                    "type":   "melee_hit",
                    "x":      self.rect.centerx,
                    "y":      self.rect.centery,
                    "damage": self.damage,
                    # Saldırı anındaki oyuncu MERKEZİ de kaydet
                    "player_cx": player_cx,
                    "player_cy": player_cy,
                    # Saldırı mesafesi (main.py'de ek kontrol için)
                    "dist": dist,
                })
                self.atk_cooldown = 1.2
            if self.state_timer > 0.8:
                self.state       = "WALK"
                self.state_timer = 0.0
            if dist > self.atk_range * 1.5:
                self.state       = "WALK"
                self.state_timer = 0.0

    # ── Çizim (PLACEHOLDER) ────────────────────────────────
    def draw(self, surface, camera_offset=(0, 0), theme=None):
        if not self.is_active:
            return
        ox, oy  = camera_offset
        draw_r  = self.rect.move(ox, oy)

        # Yarı saydam gövde
        try:
            s = pygame.Surface((draw_r.width, draw_r.height), pygame.SRCALPHA)
            s.fill((*self.color, 160))
            surface.blit(s, draw_r.topleft)
        except Exception:
            pass

        border_col = (255, 255, 255) if self.state == "STUN" else self.color
        pygame.draw.rect(surface, border_col, draw_r, 2)

        # Blok kalkanı (shielder)
        if self.is_blocking:
            shield_r = pygame.Rect(draw_r.x - 8, draw_r.y + 10, 10, draw_r.height - 20)
            pygame.draw.rect(surface, ARENA_SHIELD_COLOR, shield_r)
            pygame.draw.rect(surface, WHITE, shield_r, 1)

        # Etiket
        type_map = {"grunt": "GRUNT", "brute": "BRUTE",
                    "speeder": "SPEEDER", "shielder": "SAVAŞÇI"}
        label = f"[{type_map.get(self.enemy_type,'?')}]"
        _draw_label(surface, label,
                    draw_r.centerx, draw_r.top - 14, self.color, 16)

        # HP çubuğu
        bw  = draw_r.width
        bx  = draw_r.x
        by  = draw_r.top - 8
        hp_pct = max(0.0, self.health / self.max_health)
        pygame.draw.rect(surface, (50, 0, 0),   (bx, by, bw, 5))
        pygame.draw.rect(surface, (220, 30, 30), (bx, by, int(bw * hp_pct), 5))

        # Saldırı göstergesi
        if self.state == "ATTACK":
            pygame.draw.circle(surface, (255, 50, 50),
                               (draw_r.centerx, draw_r.top - 22), 5)


# ════════════════════════════════════════════════
#  4. ArenaDropReward — Dalga ödülü
# ════════════════════════════════════════════════
class ArenaDropReward(pygame.sprite.Sprite):
    """
    Düşman dalgası temizlenince düşen enerji topu.
    Oyuncu üzerine gelince toplanır → bonus skor/karma.
    PLACEHOLDER: Altın daire.
    """

    def __init__(self, x: float, y: float,
                 reward_type: str = "score",
                 value: int = 500):
        super().__init__()
        self.x            = float(x)
        self.y            = float(y)
        self.vy           = -6.0
        self.reward_type  = reward_type   # "score" | "karma" | "health"
        self.value        = value
        self.life         = 300           # ~5 saniye @ 60fps
        self.size         = 14
        self.collected    = False

        color_map = {"score": (255, 215, 0), "karma": (100, 255, 180), "health": (255, 80, 80)}
        self.color = color_map.get(reward_type, (255, 255, 255))
        self.rect  = pygame.Rect(int(x) - self.size, int(y) - self.size,
                                 self.size * 2, self.size * 2)

    def update(self, camera_speed: float, frame_mul: float = 1.0):
        if self.collected:
            self.kill()
            return
        self.x   -= camera_speed * frame_mul
        self.vy  += 0.4 * frame_mul
        if self.vy > 0 and self.y > LOGICAL_HEIGHT - 100:   # zemin = -80, biraz tolerans
            self.vy = -abs(self.vy) * 0.5     # Basit zıplama
        self.y   += self.vy * frame_mul
        self.rect.x = int(self.x) - self.size
        self.rect.y = int(self.y) - self.size
        self.life -= 1
        if self.life <= 0:
            self.kill()

    def draw(self, surface, camera_offset=(0, 0)):
        if self.collected:
            return
        ox, oy  = camera_offset
        cx      = int(self.x) + ox
        cy      = int(self.y) + oy
        pulse   = int(4 * math.sin(pygame.time.get_ticks() * 0.005))
        r       = self.size + pulse
        pygame.draw.circle(surface, self.color, (cx, cy), r)
        pygame.draw.circle(surface, WHITE,       (cx, cy), r, 2)
        label_map = {"score": "S", "karma": "K", "health": "H"}
        _draw_label(surface, label_map.get(self.reward_type, "?"),
                    cx, cy - 8, (0, 0, 0), 18)


# ════════════════════════════════════════════════
#  5. BeatArenaManager — Arena bölümü yöneticisi
# ════════════════════════════════════════════════
class BeatArenaManager:
    """
    "beat_arena" tipi bölümlerin tüm mantığını yönetir.

    Bölüm yapısı:
      • Kamera DURUR (camera_speed = 0 olmalı, main.py'e bırakıldı).
      • Girişte "ARENA BAŞLIYOR" banner gösterilir.
      • ARENA_WAVES listesi sırayla işlenir.
        Her dalga: belirli sayı/tip ArenaEnemy sahneye girer.
      • Dalga temizlenince ArenaDropReward bırakılır.
      • Tüm dalgalar bitince: "ARENA TEMİZLENDİ" → normal oyuna dön.

    Kullanım (main.py):
        if lvl_config.get('type') == 'beat_arena':
            if not beat_arena.active:
                beat_arena.start(level_idx)
            beat_arena.update(dt, frame_mul, player_x, player_y, camera_speed,
                              all_enemies, score, save_manager, all_vfx)
            if beat_arena.is_complete:
                camera_speed = INITIAL_CAMERA_SPEED   # Kamerayı serbest bırak
                score += beat_arena.total_bonus
                beat_arena.reset()
    """

    # Bölüm başına dalga tanımları.
    # Her dalga bir dict: {"enemies": [("tür", x, y), ...], "reward": dict}
    ARENA_WAVES: dict[int, list] = {
        # Bölüm 3 — Gutter temalı, 2 dalga
        3: [
            {
                "enemies": [
                    ("grunt",  700, LOGICAL_HEIGHT - 80),
                    ("grunt",  900, LOGICAL_HEIGHT - 80),
                    ("grunt", 1100, LOGICAL_HEIGHT - 80),
                ],
                "reward": {"type": "score",  "value": 500}
            },
            {
                "enemies": [
                    ("grunt",   750, LOGICAL_HEIGHT - 80),
                    ("speeder", 950, LOGICAL_HEIGHT - 80),
                    ("grunt",  1150, LOGICAL_HEIGHT - 80),
                ],
                "reward": {"type": "karma",  "value": 10}
            },
        ],
        # Bölüm 7 — Industrial, 3 dalga
        7: [
            {
                "enemies": [
                    ("grunt",   600, LOGICAL_HEIGHT - 80),
                    ("grunt",   800, LOGICAL_HEIGHT - 80),
                    ("speeder", 500, LOGICAL_HEIGHT - 80),
                ],
                "reward": {"type": "score",  "value": 1000}
            },
            {
                "enemies": [
                    ("brute",   700, LOGICAL_HEIGHT - 80),
                    ("grunt",   950, LOGICAL_HEIGHT - 80),
                    ("grunt",  1100, LOGICAL_HEIGHT - 80),
                ],
                "reward": {"type": "health", "value": 1}
            },
            {
                "enemies": [
                    ("shielder", 600, LOGICAL_HEIGHT - 80),
                    ("speeder",  800, LOGICAL_HEIGHT - 80),
                    ("speeder", 1000, LOGICAL_HEIGHT - 80),
                ],
                "reward": {"type": "score",  "value": 2000}
            },
        ],
        # Bölüm 13 — Şehir içi, 3 dalga + brute son dalga
        13: [
            {
                "enemies": [
                    ("speeder",  500, LOGICAL_HEIGHT - 80),
                    ("speeder",  700, LOGICAL_HEIGHT - 80),
                    ("grunt",    900, LOGICAL_HEIGHT - 80),
                    ("grunt",   1100, LOGICAL_HEIGHT - 80),
                ],
                "reward": {"type": "score",  "value": 1500}
            },
            {
                "enemies": [
                    ("shielder",  600, LOGICAL_HEIGHT - 80),
                    ("brute",     850, LOGICAL_HEIGHT - 80),
                    ("speeder",  1050, LOGICAL_HEIGHT - 80),
                ],
                "reward": {"type": "karma",  "value": 15}
            },
            {
                "enemies": [
                    ("brute",    600, LOGICAL_HEIGHT - 80),
                    ("brute",    900, LOGICAL_HEIGHT - 80),
                    ("shielder",1150, LOGICAL_HEIGHT - 80),
                ],
                "reward": {"type": "score",  "value": 3000}
            },
        ],
        # Bölüm 22 — Neon meydanı, zorlu 4 dalga
        22: [
            {
                "enemies": [
                    ("speeder",  500, LOGICAL_HEIGHT - 80),
                    ("speeder",  700, LOGICAL_HEIGHT - 80),
                    ("speeder",  900, LOGICAL_HEIGHT - 80),
                    ("grunt",   1100, LOGICAL_HEIGHT - 80),
                ],
                "reward": {"type": "score",  "value": 2000}
            },
            {
                "enemies": [
                    ("brute",    500, LOGICAL_HEIGHT - 80),
                    ("shielder", 750, LOGICAL_HEIGHT - 80),
                    ("shielder",1000, LOGICAL_HEIGHT - 80),
                ],
                "reward": {"type": "health", "value": 1}
            },
            {
                "enemies": [
                    ("brute",    600, LOGICAL_HEIGHT - 80),
                    ("speeder",  800, LOGICAL_HEIGHT - 80),
                    ("speeder", 1000, LOGICAL_HEIGHT - 80),
                    ("grunt",   1200, LOGICAL_HEIGHT - 80),
                ],
                "reward": {"type": "karma",  "value": 20}
            },
            {
                "enemies": [
                    ("brute",    500, LOGICAL_HEIGHT - 80),
                    ("brute",    800, LOGICAL_HEIGHT - 80),
                    ("shielder",1000, LOGICAL_HEIGHT - 80),
                    ("speeder", 1200, LOGICAL_HEIGHT - 80),
                ],
                "reward": {"type": "score",  "value": 5000}
            },
        ],
        # Bölüm 28 — Nexus Çekirdeği, maksimum zorluk
        28: [
            {
                "enemies": [
                    ("brute",    500, LOGICAL_HEIGHT - 80),
                    ("brute",    800, LOGICAL_HEIGHT - 80),
                    ("speeder",  650, LOGICAL_HEIGHT - 80),
                    ("speeder",  950, LOGICAL_HEIGHT - 80),
                    ("shielder",1150, LOGICAL_HEIGHT - 80),
                ],
                "reward": {"type": "score",  "value": 5000}
            },
            {
                "enemies": [
                    ("shielder",  500, LOGICAL_HEIGHT - 80),
                    ("shielder",  750, LOGICAL_HEIGHT - 80),
                    ("brute",    1000, LOGICAL_HEIGHT - 80),
                    ("speeder",  1200, LOGICAL_HEIGHT - 80),
                ],
                "reward": {"type": "karma",  "value": 25}
            },
            {
                "enemies": [
                    ("brute",    500, LOGICAL_HEIGHT - 80),
                    ("brute",    700, LOGICAL_HEIGHT - 80),
                    ("brute",    900, LOGICAL_HEIGHT - 80),
                    ("shielder",1100, LOGICAL_HEIGHT - 80),
                    ("speeder", 1300, LOGICAL_HEIGHT - 80),
                ],
                "reward": {"type": "score",  "value": 10000}
            },
        ],
    }

    def __init__(self):
        self.active        = False
        self.is_complete   = False
        self.current_wave  = 0
        self.total_waves   = 0
        self.arena_enemies = pygame.sprite.Group()
        self.drops         = pygame.sprite.Group()
        self.total_bonus   = 0
        self.banner_timer  = 0.0
        self.banner_text   = ""
        self.level_idx     = -1

    # ── Başlat ─────────────────────────────────────────────
    def start(self, level_idx: int):
        self.active       = True
        self.is_complete  = False
        self.current_wave = 0
        self.total_bonus  = 0
        self.level_idx    = level_idx
        waves             = self.ARENA_WAVES.get(level_idx, [])
        self.total_waves  = len(waves)
        self.banner_text  = f"ARENA BAŞLIYOR — {self.total_waves} DALGA"
        self.banner_timer = 2.5
        self._spawn_wave(level_idx, 0)

    # ── Dalga Spawnla ──────────────────────────────────────
    def _spawn_wave(self, level_idx: int, wave_idx: int):
        waves = self.ARENA_WAVES.get(level_idx, [])
        if wave_idx >= len(waves):
            return
        wave_data = waves[wave_idx]
        for etype, ex, ey in wave_data["enemies"]:
            e = ArenaEnemy(ex, ey, etype)
            self.arena_enemies.add(e)
        self.banner_text  = f"DALGA {wave_idx + 1} / {self.total_waves}"
        self.banner_timer = 1.5

    # ── Güncelleme ─────────────────────────────────────────
    def update(self, dt: float, frame_mul: float,
               player_x: float, player_y: float,
               camera_speed: float):
        if not self.active or self.is_complete:
            return

        if self.banner_timer > 0:
            self.banner_timer -= dt

        # Arena düşmanları güncelle (camera_speed = 0 beklenir)
        for enemy in list(self.arena_enemies):
            enemy.update(dt, player_x, player_y, camera_speed, frame_mul)
            if not enemy.is_active:
                enemy.kill()

        # Ödüller güncelle
        for drop in list(self.drops):
            drop.update(camera_speed, frame_mul)

        # Dalga bitti mi?
        if len(self.arena_enemies) == 0:
            waves   = self.ARENA_WAVES.get(self.level_idx, [])
            if self.current_wave < len(waves):
                reward_info = waves[self.current_wave].get("reward", {})
                rx          = LOGICAL_WIDTH // 2
                ry          = LOGICAL_HEIGHT - 200
                drop        = ArenaDropReward(rx, ry,
                                             reward_info.get("type", "score"),
                                             reward_info.get("value", 500))
                self.drops.add(drop)
                self.total_bonus += reward_info.get("value", 0) if reward_info.get("type") == "score" else 0

            self.current_wave += 1
            if self.current_wave >= self.total_waves:
                # Tüm dalgalar bitti
                self.banner_text  = "ARENA TEMİZLENDİ!"
                self.banner_timer = 3.0
                self.is_complete  = True
            else:
                self._spawn_wave(self.level_idx, self.current_wave)

    # ── Ödül Topla ─────────────────────────────────────────
    def collect_drops(self, player_rect: pygame.Rect) -> list[dict]:
        """
        Oyuncunun üzerine geldiği ödülleri döndürür.
        Ana döngü bu listeyi işler (skor/karma/can artışı).
        """
        collected = []
        for drop in list(self.drops):
            if player_rect.colliderect(drop.rect):
                collected.append({
                    "type":  drop.reward_type,
                    "value": drop.value
                })
                drop.collected = True
        return collected

    # ── Çizim ──────────────────────────────────────────────
    def draw(self, surface, camera_offset=(0, 0)):
        if not self.active:
            return

        # Düşmanlar
        for enemy in self.arena_enemies:
            enemy.draw(surface, camera_offset)

        # Ödüller
        for drop in self.drops:
            drop.draw(surface, camera_offset)

        # Banner
        if self.banner_timer > 0:
            alpha  = min(255, int(255 * min(1.0, self.banner_timer / 1.5)))
            cx     = LOGICAL_WIDTH // 2
            # Arka plan çubuk
            bar_w, bar_h = 500, 60
            try:
                bar_s = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
                bar_s.fill((0, 0, 0, int(alpha * 0.7)))
                surface.blit(bar_s, (cx - bar_w // 2, 180))
            except Exception:
                pass
            _draw_label(surface, self.banner_text, cx, 190, (255, 220, 50), 32)

        # Dalga HUD (sağ üst köşe)
        if self.active and not self.is_complete:
            wave_txt = f"DALGA {self.current_wave + 1}/{self.total_waves}"
            rem_txt  = f"KALAN DÜŞMAN: {len(self.arena_enemies)}"
            _draw_label(surface, wave_txt, LOGICAL_WIDTH - 200, 20, (255, 200, 50), 22)
            _draw_label(surface, rem_txt,  LOGICAL_WIDTH - 200, 42, (255, 100, 100), 18)

    # ── Arena düşmanlarından gelen melee attack kontrolü ──
    def get_enemy_attacks(self) -> list[dict]:
        """
        ArenaEnemy.spawn_queue'dan gelen saldırı olaylarını toplar.
        main.py bunu her frame çağırarak oyuncuya hasar uygular.
        """
        attacks = []
        for enemy in self.arena_enemies:
            if enemy.spawn_queue:
                attacks.extend(enemy.spawn_queue)
                enemy.spawn_queue.clear()
        return attacks

    # ── Sıfırla ────────────────────────────────────────────
    def reset(self):
        self.active       = False
        self.is_complete  = False
        self.current_wave = 0
        self.total_bonus  = 0
        self.banner_timer = 0.0
        self.arena_enemies.empty()
        self.drops.empty()


# ════════════════════════════════════════════════
#  6. PlayerHealth — Beat-em-up can sistemi
# ════════════════════════════════════════════════
class PlayerHealth:
    """
    Beat-em-up bölümleri için canın yönetilmesi.
    Side-scroller bölümlerinde tek dokunuşla ölüm; arena bölümlerinde
    bu sınıf devreye girerek birden fazla hasar alınabilir.

    Entegrasyon (main.py):
        player_hp = PlayerHealth(max_hp=100)

        # Arena düşman saldırısında:
        if player_hp.take_damage(hit_dmg):
            # ölüm → GAME_OVER
            GAME_STATE = 'GAME_OVER'

        # Ödül toplamada:
        player_hp.heal(20)

        # HUD'da:
        player_hp.draw_hud(game_canvas)
    """

    def __init__(self, max_hp: int = 100):
        self.max_hp        = max_hp
        self.current_hp    = max_hp
        self.invincible    = False
        self.inv_timer     = 0.0
        self.inv_duration  = 0.8    # Hasar sonrası geçici dokunulmazlık (sn)
        self._shake_timer  = 0.0

    # ── Hasar al ───────────────────────────────────────────
    def take_damage(self, amount: int) -> bool:
        """True → oyuncu öldü."""
        if self.invincible:
            return False
        self.current_hp   -= amount
        self.invincible    = True
        self.inv_timer     = self.inv_duration
        self._shake_timer  = 0.3
        return self.current_hp <= 0

    # ── İyileş ─────────────────────────────────────────────
    def heal(self, amount: int):
        self.current_hp = min(self.max_hp, self.current_hp + amount)

    # ── Güncelleme ─────────────────────────────────────────
    def update(self, dt: float):
        if self.inv_timer > 0:
            self.inv_timer -= dt
            if self.inv_timer <= 0:
                self.invincible = False
        if self._shake_timer > 0:
            self._shake_timer -= dt

    # ── HUD çizimi ─────────────────────────────────────────
    def draw_hud(self, surface, x: int = 20, y: int = 20):
        """
        PLACEHOLDER: Kırmızı dikdörtgen HP çubuğu.
        [TODO - PIXEL ART]: Pixel art kalp / enerji kristali.
        """
        bar_w, bar_h = 200, 18
        pct = max(0.0, self.current_hp / self.max_hp)

        # Yanıp sönme efekti (invincible)
        if self.invincible:
            tick_mod = (pygame.time.get_ticks() // 80) % 2
            if tick_mod == 1:
                return   # Bu frame çizme → yanıp söner

        pygame.draw.rect(surface, (50, 0, 0),   (x, y, bar_w, bar_h))
        fill_color = (220, 30, 30) if pct > 0.3 else (255, 80, 0) if pct > 0.15 else (255, 0, 0)
        pygame.draw.rect(surface, fill_color,    (x, y, int(bar_w * pct), bar_h))
        pygame.draw.rect(surface, (200, 200, 200), (x, y, bar_w, bar_h), 2)

        hp_txt = f"HP  {max(0, self.current_hp)} / {self.max_hp}"
        _draw_label(surface, hp_txt, x + bar_w // 2, y + 2, WHITE, 16)

    @property
    def needs_screen_shake(self) -> bool:
        return self._shake_timer > 0


# ════════════════════════════════════════════════
#  7. CombatHUD — Dövüş bilgi ekranı
# ════════════════════════════════════════════════
class CombatHUD:
    """
    Ekranın sol altına kombo zinciri + streak sayısını çizer.
    ComboSystem.get_hud_info() ile beslenir.
    """

    def draw(self, surface, combo_info: dict):
        chain    = combo_info.get("chain", [])
        hit_cnt  = combo_info.get("hit_count", 0)
        in_win   = combo_info.get("window", False)
        last_c   = combo_info.get("last_combo", "")

        bx, by   = 20, LOGICAL_HEIGHT - 120
        bw, bh   = 280, 100

        # Arka plan
        try:
            bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 160))
            surface.blit(bg, (bx, by))
        except Exception:
            pass

        pygame.draw.rect(surface, (80, 80, 80), (bx, by, bw, bh), 1)

        # Başlık
        title_col = (255, 220, 50) if in_win else (150, 150, 150)
        _draw_label(surface, "KOMBO", bx + bw // 2, by + 6, title_col, 18)

        # Zincir girdileri
        cx = bx + 20
        for i, inp in enumerate(chain):
            col = (255, 100, 100) if inp == "H" else (100, 200, 255)
            lbl = "AĞIR" if inp == "H" else "HAFİF"
            f   = _get_font(20)
            s   = f.render(f"[{lbl}]", True, col)
            surface.blit(s, (cx + i * 90, by + 32))

        # Hit sayısı
        if hit_cnt > 0:
            _draw_label(surface, f"✦ {hit_cnt} VURUŞ", bx + bw // 2, by + 58, (255, 200, 50), 22)

        # Son kombo adı (küçük)
        if last_c:
            _draw_label(surface, last_c, bx + bw // 2, by + 80, (200, 255, 200), 16)