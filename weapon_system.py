# weapon_system.py
# Silah Oyun Mantığı Katmanı
# ─────────────────────────────────────────────────────────────────────────────
# Bu dosya main.py'nin doğrudan import ettiği Revolver, SMG ve create_weapon
# sembollerini tanımlar.
#
# Görsel çizim → weapon_entities.py (RevolverVisual / SMGVisual)
# Cephane/envanter yönetimi → inventory_manager.py (InventoryManager)
# Sabitlerin hepsi → settings.py
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations
import pygame
from typing import Optional

from settings import (
    REVOLVER_MAX_BULLETS, REVOLVER_DAMAGE, REVOLVER_COOLDOWN, REVOLVER_RELOAD_TIME,
    REVOLVER_MAX_MAGS,
    SMG_DAMAGE, SMG_FIRE_RATE, SMG_MAG_SIZE, SMG_MAX_MAGS,
    PLAYER_BULLET_SPEED,
)

# Pompalı sabitleri — settings.py'de yoksa varsayılan değerler
try:
    from settings import (
        SHOTGUN_DAMAGE, SHOTGUN_MAG_SIZE, SHOTGUN_MAX_MAGS,
        SHOTGUN_COOLDOWN, SHOTGUN_RELOAD_TIME, SHOTGUN_PELLET_COUNT,
        SHOTGUN_SPREAD_ANGLE,
    )
except ImportError:
    SHOTGUN_DAMAGE        = 18    # Saçma başına hasar (toplam: 18×8 = 144 max)
    SHOTGUN_MAG_SIZE      = 6     # Şarjörde 6 mermi
    SHOTGUN_MAX_MAGS      = 4     # Maks yedek şarjör
    SHOTGUN_COOLDOWN      = 0.75  # Atışlar arası bekleme (sn) — pump sesi süresi
    SHOTGUN_RELOAD_TIME   = 2.2   # Reload süresi (sn)
    SHOTGUN_PELLET_COUNT  = 8     # Her atışta 8 saçma
    SHOTGUN_SPREAD_ANGLE  = 0.30  # Toplam koni açısı (radyan) — ~17°

# Görsel bileşenler (çizim için)
try:
    from weapon_entities import RevolverVisual, SMGVisual
    _HAS_VISUAL = True
except ImportError:
    _HAS_VISUAL = False
    RevolverVisual = None
    SMGVisual = None


# ---------------------------------------------------------------------------
# WeaponBase — Ortak temel sınıf
# ---------------------------------------------------------------------------

class WeaponBase:
    """
    Tüm silah sınıflarının ortak arayüzü.

    main.py bu özelliklere doğrudan erişir:
        .bullets          → Şu anki şarjördeki mermi sayısı
        .spare_mags       → Yedek şarjör sayısı
        .cooldown         → Kalan bekleme süresi (sn, >0 → ateş edilemez)
        .is_reloading     → True ise şarjör dolduruluyor
        .WEAPON_TYPE      → "revolver" | "smg"
        .is_automatic     → True ise tuşa basılı tutunca ateş eder (SMG)
        .fire_interval    → Otomatik ateş aralığı (sn)
        .damage           → Mermi başına hasar
    """

    WEAPON_TYPE   : str  = "base"
    is_automatic  : bool = False
    damage        : int  = 0

    # ── Mermi hurtbox yarıçapı (piksel) ─────────────────────────────────────
    # main.py'nin CCD döngüsü bu değeri okuyarak fat-hitbox oluşturur.
    # Alt sınıflar kendi değerini override eder.
    BULLET_RADIUS : int  = 6

    def __init__(self, mag_size: int, max_spare: int, cooldown_time: float,
                 reload_time: float):
        self.mag_size        = mag_size
        self.max_spare       = max_spare
        self._cooldown_time  = cooldown_time   # Atışlar arası bekleme (sn)
        self._reload_time    = reload_time     # Tam dolum süresi (sn)

        self.bullets         = mag_size        # Şarjördeki mermi
        self.spare_mags      = 0              # Yedek şarjör
        self.cooldown        = 0.0            # Kalan bekleme
        self.is_reloading    = False
        self._reload_elapsed = 0.0
        self.fire_interval   = cooldown_time   # (SMG bu değeri override eder)

        # ── Mekanik geri tepme (mermi dağılımı / spread) ─────────────────────
        # Her fire() çağrısında current_spread artar, zamanla 0'a döner.
        # main.py: final_angle = aim_angle + random.uniform(-spread, spread)
        self.current_spread    = 0.0
        self._spread_inc       = 0.05   # Her atışta eklenen miktar (radyan)
        self._spread_max       = 0.20   # Maksimum birikim
        self._spread_recovery  = 2.5    # Saniyede azalma hızı (rad/sn)

        # Görsel bileşen (opsiyonel)
        self.visual          = None

    # ── Güncelleme ───────────────────────────────────────────────────────────

    def update(self, dt: float):
        """Her frame çağrılır."""
        if self.cooldown > 0:
            self.cooldown = max(0.0, self.cooldown - dt)

        if self.is_reloading:
            self._reload_elapsed += dt
            if self._reload_elapsed >= self._reload_time:
                # Reload tamamlandı
                self.spare_mags  -= 1
                self.bullets      = self.mag_size
                self.is_reloading = False
                self._reload_elapsed = 0.0
                self.cooldown = 0.0

        # Spread zamanla sıfıra yaklaşır
        if self.current_spread > 0:
            self.current_spread = max(
                0.0, self.current_spread - self._spread_recovery * dt
            )

        if self.visual is not None:
            self.visual.update(dt)

    # ── Ateş ─────────────────────────────────────────────────────────────────

    def fire(self) -> bool:
        """
        Bir mermi ateşler.
        Dönen değer: ateş başarılı mı?
        """
        if self.cooldown > 0 or self.is_reloading or self.bullets <= 0:
            return False
        self.bullets  -= 1
        self.cooldown  = self._cooldown_time
        # Mekanik spread birikimi
        self.current_spread = min(
            self.current_spread + self._spread_inc, self._spread_max
        )
        if self.visual is not None:
            self.visual.notify_fired()
        return True

    def _get_fire_cooldown(self) -> float:
        return self._cooldown_time

    # ── Reload ───────────────────────────────────────────────────────────────

    def start_reload(self) -> bool:
        """
        Dolum işlemini başlatır.
        Dönen değer: başlatma başarılı mı?
        """
        if self.is_reloading:
            return False
        if self.spare_mags <= 0:
            return False
        if self.bullets >= self.mag_size:
            return False  # Şarjör zaten dolu
        self.is_reloading    = True
        self._reload_elapsed = 0.0
        self.cooldown        = self._reload_time   # Bekleme süresini reload'a çevir
        return True

    # ── Cephane ──────────────────────────────────────────────────────────────

    def add_spare_mag(self, count: int = 1) -> bool:
        """Yedek şarjör ekler. Limiti aşmaz."""
        if self.spare_mags < self.max_spare:
            self.spare_mags = min(self.spare_mags + count, self.max_spare)
            return True
        return False

    # ── Görsel Çizim ─────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, cx: float, cy: float,
             angle: float, shoot_timer: float = 0.0):
        """
        Silahı çizer. Muzzle point döndürür.
        Görsel bileşen yoksa None döner.
        """
        if self.visual is not None:
            return self.visual.draw(surface, cx, cy, angle, shoot_timer)
        return None

    def get_muzzle_point(self, cx: float, cy: float, angle: float,
                         shoot_timer: float = 0.0):
        """Namlu ucunun koordinatını döndürür."""
        if self.visual is not None:
            return self.visual.get_muzzle_point(cx, cy, angle, shoot_timer)
        return (int(cx), int(cy))

    # ── Trajectory ızgara noktaları (UI katmanı için) ────────────────────────

    def get_trajectory_grid_points(
        self,
        muzzle_x: float,
        muzzle_y: float,
        aim_angle: float,
        step_px: int   = 45,
        total_px: int  = 320,
    ) -> dict:
        """
        Mermi yolu ızgarasının çizim noktalarını hesaplar.

        Döndürür:
            {
              'center' : [(x,y), ...],           # Merkez çizgisi nokta dizisi
              'upper'  : [(x,y), ...],           # Üst spread sınırı
              'lower'  : [(x,y), ...],           # Alt spread sınırı
              'rungs'  : [((x1,y1),(x2,y2)),...] # Enine "rung" çizgi çiftleri
              'spread' : float,                  # Hesaplamada kullanılan spread
            }

        Kurallar (Rule 3):
            Bu metot import'lar dahil HİÇBİR yeni obje yaratmaz; sadece
            int/float hesaplamaları ve tuple döndürür. Pygame surface veya
            list comprehension kullanılmaz.
        """
        import math as _m
        spread = self.current_spread

        steps      = max(1, total_px // step_px)
        center_pts = []
        upper_pts  = []
        lower_pts  = []
        rungs      = []

        for i in range(steps + 1):
            d  = i * step_px
            cx = int(muzzle_x + _m.cos(aim_angle) * d)
            cy = int(muzzle_y + _m.sin(aim_angle) * d)
            center_pts.append((cx, cy))

            if spread > 0.001:
                ux = int(muzzle_x + _m.cos(aim_angle - spread) * d)
                uy = int(muzzle_y + _m.sin(aim_angle - spread) * d)
                lx = int(muzzle_x + _m.cos(aim_angle + spread) * d)
                ly = int(muzzle_y + _m.sin(aim_angle + spread) * d)
                upper_pts.append((ux, uy))
                lower_pts.append((lx, ly))
                if i > 0:
                    rungs.append(((ux, uy), (lx, ly)))
            else:
                # Spread sıfır: sınır noktaları merkez ile özdeş
                upper_pts.append((cx, cy))
                lower_pts.append((cx, cy))

        return {
            'center': center_pts,
            'upper' : upper_pts,
            'lower' : lower_pts,
            'rungs' : rungs,
            'spread': spread,
        }

    # ── Auto-fire desteği (SMG override eder) ────────────────────────────────

    def can_auto_fire(self, dt: float) -> bool:
        """SMG için otomatik ateş tetikleyicisi. Base sınıfta her zaman False."""
        return False


# ---------------------------------------------------------------------------
# Revolver — Altıpatar
# ---------------------------------------------------------------------------

class Revolver(WeaponBase):
    """
    Altıpatar silahı — "Sabır Nişancısı" Mekaniği

    Özellikler:
    - 6 mermilik şarjör
    - Her atışta 0.4 sn bekleme
    - 1.5 sn reload süresi
    - Manuellen ateş (yarı-otomatik)

    Spread Mekaniği (Binary State):
    - Son atıştan bu yana >= 3 saniye geçtiyse → spread = 0.0  (kusursuz isabet)
    - 3 saniyeden kısa sürede tekrar ateş edilirse → spread = 0.35  (panik atışı)
    Bu eski kademeli spread mantığının yerine geçer; base sınıfın _spread_inc
    ve _spread_recovery değerleri Revolver tarafından kullanılmaz.
    """

    WEAPON_TYPE  = "revolver"
    is_automatic = False
    damage       = REVOLVER_DAMAGE
    BULLET_RADIUS = 7   # Altıpatar: ağır mermi → biraz daha geniş hurtbox

    # Sabır eşiği ve panik spread değeri
    _PATIENCE_THRESHOLD  : float = 3.0   # sn — bu kadar bekleyince tam isabet
    _PANIC_SPREAD        : float = 0.35  # rad — erken atışta açı sapması

    def __init__(self, spare_mags: int = 0):
        super().__init__(
            mag_size     = REVOLVER_MAX_BULLETS,
            max_spare    = REVOLVER_MAX_MAGS,
            cooldown_time= REVOLVER_COOLDOWN,
            reload_time  = REVOLVER_RELOAD_TIME,
        )
        self.spare_mags    = spare_mags
        self.fire_interval = REVOLVER_COOLDOWN

        # "Son atıştan bu yana geçen süre" sayacı.
        # Başlangıçta eşiğe eşit → ilk mermi her zaman isabetli.
        self._time_since_last_shot: float = self._PATIENCE_THRESHOLD

        # _spread_max değerini panik spread ile eşleştir
        # → debug konisi _sp_pct hesabında 1.0'ı aşmaz (main.py'deki clamp ile çift güvence)
        self._spread_max = self._PANIC_SPREAD   # 0.35

        # Görsel bileşen
        if _HAS_VISUAL and RevolverVisual is not None:
            self.visual = RevolverVisual()

    # ── Güncelleme ───────────────────────────────────────────────────────────

    def update(self, dt: float):
        super().update(dt)
        # Sabır sayacını ilerlet (eşiği geçince sabit tut, overflow önlenir)
        if self._time_since_last_shot < self._PATIENCE_THRESHOLD:
            self._time_since_last_shot = min(
                self._time_since_last_shot + dt, self._PATIENCE_THRESHOLD
            )
        # current_spread: binary state'i UI'ya yansıt
        # (base sınıfın recovery mantığı override edildi — burada elle ayarlanır)
        # Spread değeri fire() içinde set edilir, burada base'in recovery'sini
        # çalıştırmak istemiyoruz. Base zaten super().update() ile çağrıldı;
        # fakat base spread recovery'yi düzeltebilir, bu yüzden son sözü biz
        # söylüyoruz:
        if self._time_since_last_shot >= self._PATIENCE_THRESHOLD:
            self.current_spread = 0.0   # 3 sn doldu → nişangah kapandı
        else:
            self.current_spread = self._PANIC_SPREAD  # hâlâ panik modunda

    # ── Ateş ─────────────────────────────────────────────────────────────────

    def fire(self) -> bool:
        """
        Binary spread ataması:
        - T_last >= 3.0 sn  → spread = 0.0  (kusursuz)
        - T_last <  3.0 sn  → spread = PANIC_SPREAD
        Her iki durumda da T_last = 0.0 sıfırlanır.
        Base sınıfın kademeli spread birikimi KULLANILMAZ.
        """
        if self.cooldown > 0 or self.is_reloading or self.bullets <= 0:
            return False

        # Spread'i binary state'e göre belirle
        if self._time_since_last_shot >= self._PATIENCE_THRESHOLD:
            self.current_spread = 0.0
        else:
            self.current_spread = self._PANIC_SPREAD

        # Ortak atış işlemleri (mermi azalt, cooldown başlat, visual bildir)
        self.bullets  -= 1
        self.cooldown  = self._cooldown_time
        if self.visual is not None:
            self.visual.notify_fired()

        # Sayacı sıfırla — bir sonraki isabetli atış için 3 sn beklemek gerekecek
        self._time_since_last_shot = 0.0
        return True


# ---------------------------------------------------------------------------
# SMG — Hafif Makinali Tüfek
# ---------------------------------------------------------------------------

class SMG(WeaponBase):
    """
    Hafif Makinali Tüfek — "Kontrollü Patlama (Burst)" Mekaniği

    Özellikler:
    - 30 mermilik şarjör
    - 8 atış/sn (fire_interval ≈ 0.125 sn)
    - Tuşa basılı tutulunca otomatik ateş

    Spread Mekaniği (Burst Counter):
    - İlk 5 mermi (C_burst <= 5) → spread = 0.0  (lazer hassasiyeti)
    - 6. mermiden itibaren      → spread lineer olarak artar:
          S = min(S_max, (C_burst - 5) * ΔS)
    - Tetikten parmak çekilip >= 1.0 sn beklenirse C_burst sıfırlanır.
    - 1 sn dolmadan tekrar ateş edilirse C_burst kaldığı yerden devam eder.
    """

    WEAPON_TYPE  = "smg"
    is_automatic = True
    damage       = SMG_DAMAGE
    BULLET_RADIUS = 5   # SMG: küçük kalibre, orta hurtbox

    # Burst parametreleri
    _BURST_FREE_SHOTS    : int   = 5     # Bu kadar mermi sıfır spread
    _BURST_SPREAD_STEP   : float = 0.05  # Her ekstra mermide artan miktar (ΔS)
    _BURST_SPREAD_MAX    : float = 0.35  # Maksimum spread tavanı (S_max)
    _RECOVERY_THRESHOLD  : float = 1.0   # Bu kadar bekleyince burst sıfırlanır (sn)

    def __init__(self, spare_mags: int = 0):
        _fire_interval = 1.0 / max(SMG_FIRE_RATE, 0.01)
        super().__init__(
            mag_size     = SMG_MAG_SIZE,
            max_spare    = SMG_MAX_MAGS,
            cooldown_time= _fire_interval,
            reload_time  = 2.0,   # SMG dolumu biraz daha uzun
        )
        self.spare_mags    = spare_mags
        self.fire_interval = _fire_interval
        self._auto_timer   = 0.0   # Otomatik ateş iç sayacı

        # Burst state değişkenleri
        self._burst_count    : int   = 0    # Mevcut seride atılan mermi sayısı
        self._recovery_timer : float = self._RECOVERY_THRESHOLD  # Toparlanma sayacı

        # Base sınıfın kademeli spread mantığı SMG'de de kullanılmaz;
        # current_spread fire() içinde burst formülüyle set edilir.
        # _spread_recovery = 0 → base update() spread'i kendi sıfırlamasın.
        self._spread_recovery = 0.0

        # _spread_max değerini burst maksimum spread ile eşleştir
        self._spread_max  = self._BURST_SPREAD_MAX   # 0.35

        # Görsel bileşen
        if _HAS_VISUAL and SMGVisual is not None:
            self.visual = SMGVisual()

    # ── Güncelleme ───────────────────────────────────────────────────────────

    def update(self, dt: float):
        super().update(dt)

        if self._auto_timer > 0:
            self._auto_timer = max(0.0, self._auto_timer - dt)

        # Toparlanma sayacını ilerlet
        self._recovery_timer = min(
            self._recovery_timer + dt, self._RECOVERY_THRESHOLD
        )

        # 1 saniye dolunca burst sayacını sıfırla
        if self._recovery_timer >= self._RECOVERY_THRESHOLD:
            self._burst_count = 0

        # current_spread'i burst durumuna göre güncelle (UI nişangahı için)
        self._apply_burst_spread()

    def _apply_burst_spread(self):
        """Burst sayacına göre current_spread değerini hesapla ve ata."""
        if self._burst_count <= self._BURST_FREE_SHOTS:
            self.current_spread = 0.0
        else:
            excess = self._burst_count - self._BURST_FREE_SHOTS
            self.current_spread = min(
                self._BURST_SPREAD_MAX,
                excess * self._BURST_SPREAD_STEP
            )

    # ── Otomatik ateş desteği ────────────────────────────────────────────────

    def can_auto_fire(self, dt: float) -> bool:
        """SMG'nin otomatik ateş zamanlayıcısını kontrol eder."""
        return self._auto_timer <= 0 and not self.is_reloading and self.bullets > 0

    # ── Ateş ─────────────────────────────────────────────────────────────────

    def fire(self) -> bool:
        """
        Burst spread ataması:
        1. C_burst artır
        2. Spread = 0  eğer C_burst <= 5,
           Spread = min(S_max, (C_burst-5) * ΔS)  eğer C_burst > 5
        3. T_recovery = 0 sıfırla (toparlanma tekrar baştan başlar)
        Base sınıfın kademeli spread birikimi KULLANILMAZ.
        """
        if self.cooldown > 0 or self.is_reloading or self.bullets <= 0:
            return False

        # Burst sayacını artır
        self._burst_count += 1

        # Spread formülünü uygula
        self._apply_burst_spread()

        # Ortak atış işlemleri
        self.bullets  -= 1
        self.cooldown  = self._cooldown_time
        if self.visual is not None:
            self.visual.notify_fired()

        # Toparlanma sayacını sıfırla — sürekli ateşte 1 sn'ye asla ulaşamaz
        self._recovery_timer = 0.0
        self._auto_timer     = self.fire_interval
        return True


# ---------------------------------------------------------------------------
# Shotgun — Pompalı Tüfek
# ---------------------------------------------------------------------------

class Shotgun(WeaponBase):
    """
    Pompalı Tüfek — "Yakın Mesafe Terörü"

    Özellikler:
    - 6 mermilik şarjör (1 atış = 1 mermi harcanır ama 8 saçma çıkar)
    - 0.75 sn pump süresi (yarı-otomatik, tuşa basılı tutunca ateş etmez)
    - Yüksek yakın mesafe hasarı, uzakta dağılım artar
    - Stamina harcamaz

    Spread Mekaniği (Sabit Koni):
    - current_spread her zaman SHOTGUN_SPREAD_ANGLE değerinde sabitlenir.
    - main.py'nin "tek mermi" mantığının YANINA pompa saçmaları EK olarak eklenir.
    - fire() True döndürdüğünde main.py shotgun_pellets değerini okuyarak
      SHOTGUN_PELLET_COUNT adet mermi eşit açı aralıklarıyla fırlatır.
    """

    WEAPON_TYPE  = "shotgun"
    is_automatic = False
    damage       = SHOTGUN_DAMAGE
    BULLET_RADIUS = 8   # Pompalı saçma: geniş hurtbox, yakın mesafe terörü

    # Saçma sayısı ve koni — main.py bu değerleri okur
    PELLET_COUNT  : int   = SHOTGUN_PELLET_COUNT
    SPREAD_ANGLE  : float = SHOTGUN_SPREAD_ANGLE   # toplam koni (radyan)

    def __init__(self, spare_mags: int = 0):
        super().__init__(
            mag_size     = SHOTGUN_MAG_SIZE,
            max_spare    = SHOTGUN_MAX_MAGS,
            cooldown_time= SHOTGUN_COOLDOWN,
            reload_time  = SHOTGUN_RELOAD_TIME,
        )
        self.spare_mags    = spare_mags
        self.fire_interval = SHOTGUN_COOLDOWN

        # Spread sabit koni — eski kademeli spread mantığı devre dışı
        self._spread_recovery = 0.0   # base sınıfın recovery'sini durdur
        self._spread_max      = SHOTGUN_SPREAD_ANGLE

        # Ekran pump animasyonu için sayaç (visual feedback)
        self._pump_timer : float = 0.0

        if _HAS_VISUAL and RevolverVisual is not None:
            # Geçici: Revolver görselini fallback olarak kullan.
            # weapon_entities.py'ye ShotgunVisual eklendiğinde burası değişir.
            self.visual = None   # Fallback geometrik çizim

    # ── Güncelleme ────────────────────────────────────────────────────────────

    def update(self, dt: float):
        super().update(dt)
        # Spread her zaman sabit koni — base sınıfın sıfırlamasını geri al
        self.current_spread = self.SPREAD_ANGLE
        # Pump animasyon sayacı
        if self._pump_timer > 0:
            self._pump_timer = max(0.0, self._pump_timer - dt)

    # ── Ateş ──────────────────────────────────────────────────────────────────

    def fire(self) -> bool:
        """
        Pompalı ateş.
        True döndürdüğünde main.py PELLET_COUNT adet saçmayı
        SPREAD_ANGLE konisinde eşit açı aralıklarıyla fırlatmalıdır.
        Base sınıfın tek mermi mantığı override edilir.
        """
        if self.cooldown > 0 or self.is_reloading or self.bullets <= 0:
            return False

        self.bullets  -= 1
        self.cooldown  = self._cooldown_time
        self._pump_timer = self._cooldown_time   # Pump animasyonunu başlat
        # Spread sabit — override gerekmez, update() hallediyor

        if self.visual is not None:
            self.visual.notify_fired()
        return True


# ---------------------------------------------------------------------------
# Factory fonksiyonu
# ---------------------------------------------------------------------------

_WEAPON_REGISTRY = {
    "revolver": Revolver,
    "smg":      SMG,
    "shotgun":  Shotgun,
}

def create_weapon(weapon_type: str, spare_mags: int = 0) -> Optional[WeaponBase]:
    """
    Belirtilen türde yeni bir silah nesnesi oluşturur.

    Kullanım:
        weapon = create_weapon("revolver")
        weapon = create_weapon("smg", spare_mags=2)

    Dönen değer:
        WeaponBase alt sınıfı (Revolver/SMG) veya bilinmeyen tür için None.
    """
    cls = _WEAPON_REGISTRY.get(weapon_type)
    if cls is None:
        print(f"[weapon_system] Bilinmeyen silah türü: {weapon_type!r}")
        return None
    return cls(spare_mags=spare_mags)