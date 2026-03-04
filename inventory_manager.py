# inventory_manager.py
# Merkezi Silah Envanter Sistemi
# ─────────────────────────────────────────────────────────────────────────────
# Bu modül oyuncu silah envanterini ve gerçekçi cephane mantığını yönetir.
#
# Sorumluluklar:
#   1. Sahip olunan silahları (unlocked_weapons) liste olarak tutar.
#   2. Aktif silah referansını yönetir (başlangıçta None = silahsız).
#   3. Gerçekçi cephane: şarjördeki mermi + yedek şarjör sayısı ayrımı.
#   4. Silah değiştirme (switch) — slot tuşları veya doğrudan tür adı ile.
#   5. SaveManager ile senkronize olur (yükle / kaydet).
#
# Kullanım (main.py):
#   from inventory_manager import inventory_manager
#   inventory_manager.init_from_save(save_manager)
#   inventory_manager.unlock(weapon_type, weapon_obj)
#   inventory_manager.switch_to(weapon_type)
#   ...
#   active = inventory_manager.active_weapon   # None veya weapon nesnesi
#   bullets, spare = inventory_manager.ammo_state()
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations
from typing import Optional, Dict, List, Any
from settings import (
    REVOLVER_MAX_BULLETS, REVOLVER_MAX_MAGS,
    SMG_MAG_SIZE, SMG_MAX_MAGS
)

# ---------------------------------------------------------------------------
# Şarjör kapasitesi ve yedek limit sabitleri (settings.py'den)
# ---------------------------------------------------------------------------


_MAG_SIZE: Dict[str, int] = {
    "revolver": REVOLVER_MAX_BULLETS,
    "smg":      SMG_MAG_SIZE,
    "shotgun":  6,  # EKLENDİ
}

_MAX_SPARE_MAGS: Dict[str, int] = {
    "revolver": REVOLVER_MAX_MAGS,
    "smg":      SMG_MAX_MAGS,
    "shotgun":  4,  # EKLENDİ
}

# ---------------------------------------------------------------------------
# WeaponSlot — Silah başına cephane kaydı
# ---------------------------------------------------------------------------

class WeaponSlot:
    """
    Bir silah türüne ait cephane durumunu tutar.

    Özellikler:
        weapon_type  : "revolver" veya "smg"
        current_mag  : Şu an takılı şarjördeki mermi sayısı
        spare_mags   : Yedek tam şarjör sayısı
        mag_size     : Bu silah türünün şarjör kapasitesi
        max_spare    : Taşınabilecek maksimum yedek şarjör
    """

    def __init__(self, weapon_type: str, current_mag: int = -1, spare_mags: int = 0):
        self.weapon_type = weapon_type
        self.mag_size  = _MAG_SIZE.get(weapon_type, 6)
        self.max_spare = _MAX_SPARE_MAGS.get(weapon_type, 3)
        # -1 → tam dolu şarjörle başla
        self.current_mag = self.mag_size if current_mag == -1 else max(0, current_mag)
        self.spare_mags  = max(0, spare_mags)

    # ── Sorgu ───────────────────────────────────────────────────────────────

    @property
    def can_fire(self) -> bool:
        return self.current_mag > 0

    @property
    def can_reload(self) -> bool:
        return self.spare_mags > 0 and self.current_mag < self.mag_size

    @property
    def spare_at_limit(self) -> bool:
        return self.spare_mags >= self.max_spare

    # ── İşlemler ────────────────────────────────────────────────────────────

    def consume_bullet(self) -> bool:
        """Ateş edildiğinde mermiyi tüketir. Başarılıysa True döner."""
        if self.current_mag > 0:
            self.current_mag -= 1
            return True
        return False

    def reload(self) -> bool:
        """
        Yeni bir şarjör takar.
        - Mevcut şarjördeki kalan mermiler çöpe gider (gerçekçi taktik nişancı modu).
        - Yedek şarjör eksilir.
        - Dönen değer: reload başlatıldı mı?
        """
        if self.spare_mags > 0 and self.current_mag < self.mag_size:
            self.spare_mags  -= 1
            self.current_mag  = self.mag_size
            return True
        return False

    def add_spare_mag(self, count: int = 1) -> int:
        """Yedek şarjör ekler. Kaç şarjör eklenebildiğini döner."""
        can_add = self._MAX_SPARE_MAGS - self.spare_mags
        can_add = max(0, min(can_add, count))
        self.spare_mags += can_add
        return can_add

    @property
    def _MAX_SPARE_MAGS(self) -> int:
        return self.max_spare

    def to_dict(self) -> dict:
        return {
            "weapon_type": self.weapon_type,
            "current_mag": self.current_mag,
            "spare_mags":  self.spare_mags,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WeaponSlot":
        return cls(
            weapon_type=d.get("weapon_type", "revolver"),
            current_mag=d.get("current_mag", -1),
            spare_mags=d.get("spare_mags",  0),
        )


# ---------------------------------------------------------------------------
# InventoryManager — Ana Sınıf
# ---------------------------------------------------------------------------

class InventoryManager:
    """
    Oyuncunun silah envanterini ve aktif silahı yöneten merkezi sistem.

    Kullanım:
        from inventory_manager import inventory_manager

        # Oyun başlangıcında kayıttan yükle:
        inventory_manager.init_from_save(save_manager)

        # Sandıktan silah kilidini aç:
        inventory_manager.unlock("revolver", revolver_weapon_obj)

        # Silahı değiştir:
        inventory_manager.switch_to("smg")

        # Ateş et:
        if inventory_manager.fire():
            spawn_bullet()

        # Reload (R tuşu):
        if inventory_manager.start_reload():
            play_reload_sound()

        # Ammo paket toplandığında:
        inventory_manager.pickup_spare_mag("revolver")

        # HUD'a gönder:
        bullets, spare = inventory_manager.ammo_state()
        wtype = inventory_manager.active_type
    """

    def __init__(self):
        # {weapon_type: WeaponSlot}
        self._slots: Dict[str, WeaponSlot] = {}
        # Sıralanmış silah türleri listesi (switch sırası için)
        self._order: List[str] = []
        # Şu an aktif silah türü (None = silahsız)
        self._active_type: Optional[str] = None
        # TİP BAZLI silah nesneleri — {weapon_type: weapon_obj}
        # Her silah türünün ayrı nesnesi var; switch yapınca karışmaz.
        self._weapon_objects: Dict[str, Any] = {}

    # ── Başlatma ─────────────────────────────────────────────────────────────

    def reset(self):
        """Tüm envanteri sıfırlar (bölüm/oyun yeniden başlatma)."""
        self._slots.clear()
        self._order.clear()
        self._active_type = None
        self._weapon_objects.clear()

    def init_from_save(self, save_manager) -> None:
        """
        save_manager'dan envanter verisini yükler.
        Mevcut envanter temizlenir.
        """
        self.reset()
        inv_data = save_manager.get_weapon_inventory()
        unlocked = inv_data.get("unlocked_weapons", [])
        ammo_data = inv_data.get("current_ammo", {})
        equipped  = inv_data.get("equipped_weapon", None)

        for wtype in unlocked:
            spare = ammo_data.get(wtype, 0)
            slot  = WeaponSlot(wtype, current_mag=-1, spare_mags=spare)
            self._slots[wtype]  = slot
            if wtype not in self._order:
                self._order.append(wtype)

        if equipped and equipped in self._slots:
            self._active_type = equipped

    def sync_to_save(self, save_manager) -> None:
        """
        Mevcut cephane durumunu save_manager'a yazar.
        Oyun kapatılmadan / bölüm değişmeden önce çağrılmalı.
        """
        for wtype, slot in self._slots.items():
            if wtype not in save_manager.get_weapon_inventory().get("unlocked_weapons", []):
                save_manager.unlock_weapon(wtype)
            save_manager.update_ammo(wtype, slot.spare_mags)
        if self._active_type:
            save_manager.set_equipped_weapon(self._active_type)

    # ── Kilit Açma ───────────────────────────────────────────────────────────

    def unlock(self, weapon_type: str, weapon_obj=None) -> bool:
        """
        Sandıktan bulunan silahı envantere ekler.

        Parametreler:
            weapon_type : "revolver" veya "smg"
            weapon_obj  : weapon_system.py'den gelen Revolver/SMG nesnesi

        Dönen değer:
            True  → Yeni silah eklendi
            False → Zaten envanterde var (yine de aktif hale getirildi)
        """
        is_new = weapon_type not in self._slots
        if is_new:
            self._slots[weapon_type] = WeaponSlot(weapon_type, current_mag=-1, spare_mags=0)
            self._order.append(weapon_type)

        # Silah nesnesini tipe göre kaydet (BUG FIX: tek ref yerine per-type dict)
        if weapon_obj is not None:
            self._weapon_objects[weapon_type] = weapon_obj

        # İlk silahsa veya aktif silah yoksa, hemen kuşan
        if self._active_type is None:
            self.switch_to(weapon_type)
        return is_new

    # ── Silah Değiştirme ──────────────────────────────────────────────────────

    def switch_to(self, weapon_type: str, weapon_obj=None) -> bool:
        """
        Belirtilen türe geç.

        weapon_obj sağlanırsa o türün weapon nesnesi güncellenir.
        Dönen değer: geçiş başarılı mı?
        """
        if weapon_type not in self._slots:
            return False
        self._active_type = weapon_type
        # Eğer dışarıdan yeni nesne verilmişse kaydet
        if weapon_obj is not None:
            self._weapon_objects[weapon_type] = weapon_obj
        # O tipe ait nesneyi al
        wobj = self._weapon_objects.get(weapon_type)
        # Slotla senkronize et
        slot = self._slots[weapon_type]
        if wobj is not None:
            try:
                wobj.bullets    = slot.current_mag
                wobj.spare_mags = slot.spare_mags
            except AttributeError:
                pass
        return True

    def switch_by_slot_index(self, idx: int) -> Optional[str]:
        """
        Envanter sıralamasına göre slot indisiyle geçiş yapar.
        Silah nesnesi _weapon_objects dict'ten otomatik alınır.
        Dönen değer: yeni aktif tür (başarısız → None).
        """
        if idx < 0 or idx >= len(self._order):
            return None
        wtype = self._order[idx]
        self.switch_to(wtype)
        return wtype

    def switch_next(self) -> Optional[str]:
        """Sıradaki silaha geç (döngüsel)."""
        if not self._order:
            return None
        if self._active_type not in self._order:
            self.switch_to(self._order[0])
            return self._order[0]
        idx = self._order.index(self._active_type)
        next_idx = (idx + 1) % len(self._order)
        wtype = self._order[next_idx]
        self.switch_to(wtype)
        return wtype

    # ── Ateş / Reload ────────────────────────────────────────────────────────

    def fire(self) -> bool:
        """
        Aktif silahtan bir mermi tüketir.
        Dönen değer: ateş gerçekleşti mi?
        """
        slot = self._active_slot
        if slot is None:
            return False
        success = slot.consume_bullet()
        # weapon_obj ile senkronize
        wobj = self._weapon_objects.get(self._active_type)
        if success and wobj is not None:
            try:
                wobj.bullets = slot.current_mag
            except AttributeError:
                pass
        return success

    def start_reload(self) -> bool:
        """
        Aktif silahın reload işlemini başlatır.
        Dönen değer: reload başlatıldı mı?
        """
        slot = self._active_slot
        if slot is None:
            return False
        return slot.reload()

    def consume_reload(self) -> bool:
        """
        Reload animasyonu bittiğinde çağrılır —
        şarjörü tam dolu olarak işaretler (slot zaten güncellendi).
        weapon_obj ile senkronize eder.
        """
        slot = self._active_slot
        if slot is None:
            return False
        wobj = self._weapon_objects.get(self._active_type)
        if wobj is not None:
            try:
                wobj.bullets    = slot.current_mag
                wobj.spare_mags = slot.spare_mags
            except AttributeError:
                pass
        return True

    # ── Cephane Toplama ───────────────────────────────────────────────────────

    def pickup_spare_mag(self, weapon_type: str, count: int = 1) -> int:
        """
        Düşman / AmmoPickup üzerinden şarjör paketi toplar.
        Dönen değer: kaç şarjör eklenebildi.
        """
        if weapon_type not in self._slots:
            return 0
        return self._slots[weapon_type].add_spare_mag(count)

    def chest_add_ammo(self, weapon_type: str) -> dict:
        """
        Sandıktan aynı silahın tekrar alınması için atomik metod.

        Sorun: add_spare_mag() sadece weapon_obj'i güncelliyor, slot 0 kalıyor.
        Sonraki switch_to() çağrısında slot → weapon_obj yazılınca her şey sıfırlanıyor.

        Bu metod slot + weapon_obj'i tek seferde günceller:
          1. Slot'a +1 yedek şarjör ekle
          2. Şarjör boşsa hemen doldur (otomatik reload, R'ya basmak gerekmez)
          3. weapon_obj'i slot'la senkronize et

        Döner: {'bullets': int, 'spare_mags': int, 'was_empty': bool}
        """
        slot = self._slots.get(weapon_type)
        if slot is None:
            return {'bullets': 0, 'spare_mags': 0, 'was_empty': False}

        # Slot'a +1 yedek şarjör ekle
        slot.add_spare_mag(1)

        # Şarjör boşsa hemen doldur — eklediğimiz şarjörü kullan
        was_empty = False
        if slot.current_mag <= 0 and slot.spare_mags > 0:
            slot.spare_mags  -= 1
            slot.current_mag  = slot.mag_size
            was_empty = True

        # weapon_obj'i slot ile senkronize et
        wobj = self._weapon_objects.get(weapon_type)
        if wobj is not None:
            try:
                wobj.bullets      = slot.current_mag
                wobj.spare_mags   = slot.spare_mags
                wobj.is_reloading = False
                wobj.cooldown     = 0.0
            except AttributeError:
                pass

        return {
            'bullets':    slot.current_mag,
            'spare_mags': slot.spare_mags,
            'was_empty':  was_empty,
        }

    # ── Sorgu API'si ──────────────────────────────────────────────────────────

    @property
    def active_type(self) -> Optional[str]:
        return self._active_type

    @property
    def active_weapon(self):
        """Aktif silah tipine ait weapon nesnesi (weapon_system.py)."""
        if self._active_type is None:
            return None
        return self._weapon_objects.get(self._active_type)

    @active_weapon.setter
    def active_weapon(self, obj):
        """Aktif tipe bir weapon nesnesi atar."""
        if self._active_type is not None and obj is not None:
            self._weapon_objects[self._active_type] = obj

    @property
    def _active_slot(self) -> Optional[WeaponSlot]:
        if self._active_type is None:
            return None
        return self._slots.get(self._active_type)

    def ammo_state(self):
        """
        Döner: (current_bullets, spare_mags) tuple.
        Aktif silah yoksa (0, 0).
        """
        slot = self._active_slot
        if slot is None:
            return (0, 0)
        return (slot.current_mag, slot.spare_mags)

    def mag_size_for(self, weapon_type: str) -> int:
        """Belirtilen silah türünün şarjör kapasitesini döndürür."""
        return _MAG_SIZE.get(weapon_type, 6)

    @property
    def active_mag_size(self) -> int:
        slot = self._active_slot
        return slot.mag_size if slot else 0

    @property
    def unlocked_weapons(self) -> List[str]:
        return list(self._order)

    @property
    def is_empty(self) -> bool:
        return len(self._order) == 0

    def has_weapon(self, weapon_type: str) -> bool:
        return weapon_type in self._slots

    def slot_for(self, weapon_type: str) -> Optional[WeaponSlot]:
        return self._slots.get(weapon_type)

    # ── Debug ─────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        slot = self._active_slot
        if slot:
            return (f"<InventoryManager active={self._active_type} "
                    f"mag={slot.current_mag}/{slot.mag_size} "
                    f"spare={slot.spare_mags}>")
        return "<InventoryManager silahsız>"


# ---------------------------------------------------------------------------
# Singleton — tek global örnek
# ---------------------------------------------------------------------------

inventory_manager = InventoryManager()