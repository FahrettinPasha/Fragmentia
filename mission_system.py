# mission_system.py — FRAGMENTIA: GÖREV SİSTEMİ
# =============================================================================
# "Çöplükten Fabrikaya, Fabrikadan Neon Town'a" görev yayının tam entegrasyonu.
#
# MİMARİ KURALLARI:
#   • Bu modül SIFIR pygame.draw çağrısı yapar — yalnızca veri üretir.
#   • main.py her karede poll_events() çağırır ve dönen eventleri işler.
#   • GC kuralı: döngü içinde yeni dict/list yaratılmaz, sabit listeler reuse edilir.
#   • Tüm zamanlayıcılar dt ile güncellenir (RULE 1).
# =============================================================================

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import random


# ─────────────────────────────────────────────────────────────────────────────
# 1. TEMEL VERİ YAPILARI
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class KarmaChoice:
    """
    Oyuncuya sunulan ahlaki seçim.
    main.py CHOICE_PENDING eventi aldığında bu nesneyi UI'a render eder.
    Oyuncu seçince mission_manager.resolve_choice(choice_id, 'A' | 'B') çağırır.
    """
    choice_id: str
    prompt_text: str        # Ekranda gösterilecek durum
    option_a: str           # Sol seçenek
    option_b: str           # Sağ seçenek
    option_a_karma: int
    option_b_karma: int
    option_a_tag: str = ""  # 'UNLOCK_GUN' | 'STEALTH_BONUS' | '' vb.
    option_b_tag: str = ""


@dataclass
class MissionObjective:
    """HUD'da gösterilecek aktif hedef."""
    obj_id: str
    text: str
    completed: bool = False
    optional: bool = False


@dataclass
class MissionEvent:
    """
    main.py'nin her karede tükettiği tek kullanımlık olay kapsülü.
    event_type değerleri:
        'DIALOGUE'       -> story_manager.set_dialogue() çağır
        'CHOICE_PENDING' -> KarmaChoice UI'ı aç (payload['choice'] = KarmaChoice)
        'OBJECTIVE_ADD'  -> HUD'a yeni hedef ekle
        'OBJECTIVE_DONE' -> Hedefi tamamlandı işaretle
        'UNLOCK'         -> save_manager üzerinde özellik aç
        'ALERT_RAISED'   -> stealth_system.raise_alert() tetikle
        'REWARD'         -> Skor bonusu ver (payload['score'])
    """
    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    consumed: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# 2. GÖREV AŞAMALARI — DATA-DRIVEN
# ─────────────────────────────────────────────────────────────────────────────

STAGE_DEFS: List[Dict[str, Any]] = [

    # ── STAGE 0: ÇÖPLÜKTE UYANIŞ ──────────────────────────────────────────
    {
        "stage_id": 0,
        "name": "ÇÖPLÜKTE UYANIŞ",
        "trigger_level": 1,
        "trigger_score": 0,
        "theme_index": 2,
        "objectives": [
            {"obj_id": "explore_junk",  "text": "Atık yığınını keşfet",      "optional": False},
            {"obj_id": "find_wall",     "text": "Fabrika dış duvarını bul",  "optional": False},
        ],
        "entry_events": [
            {"event_type": "DIALOGUE", "payload": {
                "speaker": "SİSTEM",
                "text": "YAMA İŞLEMİ BAŞARISIZ. HEDEF: 'İSİMSİZ'. SKOR: 0.",
                "is_cutscene": True
            }},
            {"event_type": "DIALOGUE", "payload": {
                "speaker": "SOKRAT",
                "text": "Gözlerini aç. Yama tutmamış — bu şehirde nadir bir lütuf.",
                "is_cutscene": False
            }},
            {"event_type": "DIALOGUE", "payload": {
                "speaker": "SOKRAT",
                "text": "İlerideki kapıyı görüyor musun? Kart ya da kurnazlık. Hangisi seni daha az iz bırakır?",
                "is_cutscene": False
            }},
            {"event_type": "OBJECTIVE_ADD", "payload": {"obj_id": "explore_junk"}},
        ],
        "karma_choices": {},
        "exit_condition": "score",
        "exit_value": 800,
        "exit_to_stage": 1,
    },

    # ── STAGE 1: FABRİKA GİRİŞİ ───────────────────────────────────────────
    {
        "stage_id": 1,
        "name": "FABRİKA GİRİŞİ — GÜVENLİK KAPISI",
        "trigger_level": 4,
        "trigger_score": 0,
        "theme_index": 3,
        "objectives": [
            {"obj_id": "reach_gate",    "text": "Güvenlik kapısına ulaş",           "optional": False},
            {"obj_id": "enter_factory", "text": "Fabrikaya gir",                    "optional": False},
            {"obj_id": "vent_route",    "text": "[GİZLİLİK] Havalandırma bacasını bul", "optional": True},
        ],
        "entry_events": [
            {"event_type": "DIALOGUE", "payload": {
                "speaker": "SİSTEM",
                "text": "FABRİKA ALGILAMA AĞINA GİRİLDİ.",
                "is_cutscene": True
            }},
            {"event_type": "DIALOGUE", "payload": {
                "speaker": "SOKRAT",
                "text": "Rampa solda. Havalandırma bacasını görüyor musun sağda? Gizlilik mi, güç mü?",
                "is_cutscene": False
            }},
            {"event_type": "OBJECTIVE_ADD", "payload": {"obj_id": "reach_gate"}},
            {"event_type": "OBJECTIVE_ADD", "payload": {"obj_id": "vent_route"}},
        ],
        "karma_choices": {
            "gate_entry": KarmaChoice(
                choice_id="gate_entry",
                prompt_text="Güvenlik kapısı önünde bir gardiyansın var. Ne yapacaksın?",
                option_a="[ÇATIŞMA] Gardiyanı alt et, kartı al",
                option_b="[GİZLİLİK] Havalandırma bacasından gir",
                option_a_karma=-2,
                option_b_karma=2,
                option_a_tag="COMBAT_ENTRY",
                option_b_tag="STEALTH_ENTRY",
            )
        },
        "exit_condition": "objective_done",
        "exit_value": "enter_factory",
        "exit_to_stage": 2,
    },

    # ── STAGE 2: KONVEYÖR BANT ALANI ──────────────────────────────────────
    {
        "stage_id": 2,
        "name": "ÇÖP ÖĞÜTÜCÜ ALANI",
        "trigger_level": 6,
        "trigger_score": 0,
        "theme_index": 3,
        "objectives": [
            {"obj_id": "cross_conveyors", "text": "Konveyör bantları geç",               "optional": False},
            {"obj_id": "avoid_arms",      "text": "Mekanik kollardan kaç",               "optional": False},
            {"obj_id": "tunnel_path",     "text": "[GİZLİLİK] Bakım tünellerini kullan", "optional": True},
        ],
        "entry_events": [
            {"event_type": "DIALOGUE", "payload": {
                "speaker": "SİSTEM",
                "text": "MEKANİK KOLLAR: BOZUK PROTOKOL. UYARI: TEHLİKELİ.",
                "is_cutscene": True
            }},
            {"event_type": "DIALOGUE", "payload": {
                "speaker": "SOKRAT",
                "text": "Bantların altındaki tüneller daha güvenli. Ama karanlık.",
                "is_cutscene": False
            }},
            {"event_type": "OBJECTIVE_ADD", "payload": {"obj_id": "cross_conveyors"}},
            {"event_type": "OBJECTIVE_ADD", "payload": {"obj_id": "tunnel_path"}},
        ],
        "karma_choices": {},
        "exit_condition": "score",
        "exit_value": 15000,
        "exit_to_stage": 3,
    },

    # ── STAGE 3: İŞÇİ MAHALLELERİ ────────────────────────────────────────
    {
        "stage_id": 3,
        "name": "İŞÇİ MAHALLELERİ",
        "trigger_level": 6,
        "trigger_score": 15000,
        "theme_index": 3,
        "objectives": [
            {"obj_id": "worker1_encounter", "text": "[OPSİYONEL] Yaşlı işçiyle konuş",       "optional": True},
            {"obj_id": "worker2_silence",   "text": "[OPSİYONEL] Korkak işçiyi sustur",      "optional": True},
            {"obj_id": "elevator_quest",    "text": "[YAN GÖREV] Gizli silah tesisi asansörü", "optional": True},
            {"obj_id": "proceed_security",  "text": "Güvenlik noktasına ilerle",              "optional": False},
        ],
        "entry_events": [
            {"event_type": "DIALOGUE", "payload": {
                "speaker": "IŞÇI-1",
                "text": "Dur! Sen... Yama tutmamışsın değil mi? Ben de. Beni kaçmama yardım edebilir misin?",
                "is_cutscene": False
            }},
            {"event_type": "OBJECTIVE_ADD", "payload": {"obj_id": "worker1_encounter"}},
            {"event_type": "OBJECTIVE_ADD", "payload": {"obj_id": "proceed_security"}},
        ],
        "karma_choices": {
            "worker1_help": KarmaChoice(
                choice_id="worker1_help",
                prompt_text="Yaşlı işçi 'Beni kaçmama yardım et' diyor. Ne yaparsın?",
                option_a="[YARDIM ET] Kapıyı aç, dikkat dağıt",
                option_b="[GEÇ] Riske girme, devam et",
                option_a_karma=3,
                option_b_karma=0,
                option_a_tag="SOUL_SAVED",
                option_b_tag="",
            ),
            "worker2_silence": KarmaChoice(
                choice_id="worker2_silence",
                prompt_text="Korkak işçi bağırmaya başlıyor! Gardiyanları çağıracak!",
                option_a="[İKNA ET] Fısılda, sustur",
                option_b="[BAYILT] Hızlıca etkisiz bırak",
                option_a_karma=1,
                option_b_karma=0,
                option_a_tag="PERSUADE",
                option_b_tag="KO_WORKER",
            ),
        },
        "exit_condition": "objective_done",
        "exit_value": "proceed_security",
        "exit_to_stage": 4,
    },

    # ── STAGE 4: GÜVENLİK NOKTALARI ───────────────────────────────────────
    {
        "stage_id": 4,
        "name": "GÜVENLİK NOKTALARI",
        "trigger_level": 7,
        "trigger_score": 0,
        "theme_index": 3,
        "objectives": [
            {"obj_id": "pass_checkpoint_1", "text": "1. güvenlik noktasını geç",              "optional": False},
            {"obj_id": "pass_checkpoint_2", "text": "2. güvenlik noktasını geç",              "optional": False},
            {"obj_id": "stealth_bonus",     "text": "[GİZLİLİK] Kamera kör noktalarını kullan", "optional": True},
        ],
        "entry_events": [
            {"event_type": "DIALOGUE", "payload": {
                "speaker": "SİSTEM",
                "text": "KROM MUHAFIZ ALGISI: AKTİF. GÖZETİM KAMERASI: 3 NOKTA.",
                "is_cutscene": True
            }},
            {"event_type": "DIALOGUE", "payload": {
                "speaker": "SOKRAT",
                "text": "Krom Muhafızlar güçlü. Ateşli silahla öldürmek kolay ama karma düşer.",
                "is_cutscene": False
            }},
            {"event_type": "OBJECTIVE_ADD", "payload": {"obj_id": "pass_checkpoint_1"}},
            {"event_type": "OBJECTIVE_ADD", "payload": {"obj_id": "stealth_bonus"}},
        ],
        "karma_choices": {
            "guard_takedown": KarmaChoice(
                choice_id="guard_takedown",
                prompt_text="Krom Muhafız yolu kesiyor. Nasıl geçeceksin?",
                option_a="[ÖLDÜR] Ateş et, hızlı geç",
                option_b="[BAYILT] Yakın dövüşle etkisiz bırak",
                option_a_karma=-3,
                option_b_karma=0,
                option_a_tag="LETHAL",
                option_b_tag="NON_LETHAL",
            )
        },
        "exit_condition": "objective_done",
        "exit_value": "pass_checkpoint_2",
        "exit_to_stage": 5,
    },

    # ── STAGE 5: İSTİHBARAT ODASI ─────────────────────────────────────────
    {
        "stage_id": 5,
        "name": "İSTİHBARAT ODASI",
        "trigger_level": 8,
        "trigger_score": 0,
        "theme_index": 3,
        "objectives": [
            {"obj_id": "reach_intel_room", "text": "Kırmızı kapıya ulaş",           "optional": False},
            {"obj_id": "get_tablet",       "text": "Tableti al (bölge haritası)",   "optional": False},
            {"obj_id": "read_chip",        "text": "Ölü casusun çipini oku",        "optional": False},
            {"obj_id": "hack_entry",       "text": "[HACK] Kapıyı hackle",          "optional": True},
        ],
        "entry_events": [
            {"event_type": "DIALOGUE", "payload": {
                "speaker": "SİSTEM",
                "text": "SINIFLANDIRILMIŞ AĞA ERİŞİM TESPİT EDİLDİ.",
                "is_cutscene": True
            }},
            {"event_type": "DIALOGUE", "payload": {
                "speaker": "SOKRAT",
                "text": "İçerideki tablette şehir haritası var. Ve... VASİ hakkında bir not.",
                "is_cutscene": False
            }},
            {"event_type": "OBJECTIVE_ADD", "payload": {"obj_id": "reach_intel_room"}},
        ],
        "karma_choices": {
            "intel_entry": KarmaChoice(
                choice_id="intel_entry",
                prompt_text="Kırmızı kapıda retina tarayıcı var. Yanındaki gardiyanı ne yapacaksın?",
                option_a="[VAHŞİ] Gardiyanın gözünü kullan (Karma -5)",
                option_b="[HACK / HAVALANDIRMA] Alternatif giriş",
                option_a_karma=-5,
                option_b_karma=1,
                option_a_tag="BRUTAL_ENTRY",
                option_b_tag="SMART_ENTRY",
            )
        },
        "exit_condition": "objective_done",
        "exit_value": "read_chip",
        "exit_to_stage": 6,
    },

    # ── STAGE 6: SİYAH KAPI ───────────────────────────────────────────────
    {
        "stage_id": 6,
        "name": "SİYAH KAPI — İLK ÇATIŞMA",
        "trigger_level": 9,
        "trigger_score": 0,
        "theme_index": 3,
        "objectives": [
            {"obj_id": "confront_guards",  "text": "Siyah kapıdaki gardiyanla yüzleş",      "optional": False},
            {"obj_id": "pass_black_door",  "text": "Siyah kapıyı geç",                      "optional": False},
            {"obj_id": "explore_weapons",  "text": "[YAN GÖREV] Silah üretim bölümünü keşfet", "optional": True},
        ],
        "entry_events": [
            {"event_type": "DIALOGUE", "payload": {
                "speaker": "GARDİYAN",
                "text": "Dur! Bu bölge yasak! Silahını koy yere!",
                "is_cutscene": False
            }},
            {"event_type": "DIALOGUE", "payload": {
                "speaker": "SİSTEM",
                "text": "UYARI: KAÇIŞ ROTASI KESİLDİ. ÇATIŞMA KAÇINILMAZ.",
                "is_cutscene": True
            }},
            {"event_type": "OBJECTIVE_ADD", "payload": {"obj_id": "confront_guards"}},
        ],
        "karma_choices": {
            "guard_lethal": KarmaChoice(
                choice_id="guard_lethal",
                prompt_text="Gardiyan silahını doğrultuyor. Karar ver!",
                option_a="[ÖLDÜR] Gardiyanı vur, silahını al",
                option_b="[ETKISIZ] Yakın dövüşle bayılt",
                option_a_karma=-5,
                option_b_karma=0,
                option_a_tag="UNLOCK_GUN",
                option_b_tag="NON_LETHAL",
            )
        },
        "exit_condition": "objective_done",
        "exit_value": "pass_black_door",
        "exit_to_stage": 7,
    },

    # ── STAGE 7: TREN İSTASYONU ────────────────────────────────────────────
    {
        "stage_id": 7,
        "name": "TREN İSTASYONU — NEON TOWN'A KAÇIŞ",
        "trigger_level": 9,
        "trigger_score": 30000,
        "theme_index": 3,
        "objectives": [
            {"obj_id": "reach_station",   "text": "Tren istasyonuna ulaş",           "optional": False},
            {"obj_id": "board_train",     "text": "Trene bin (konteynır veya alt)",  "optional": False},
            {"obj_id": "clear_train",     "text": "Trendeki gardiyanları geç",       "optional": False},
            {"obj_id": "reach_neon_town", "text": "Neon Town sınırına ulaş",         "optional": False},
        ],
        "entry_events": [
            {"event_type": "DIALOGUE", "payload": {
                "speaker": "SİSTEM",
                "text": "SANAYİCİLER LOJİSTİK — TREN KALKIŞ: 3 DAKİKA.",
                "is_cutscene": True
            }},
            {"event_type": "DIALOGUE", "payload": {
                "speaker": "SOKRAT",
                "text": "Konteynırların içinde ya da trenin altında. Fark edilirsen savaşmak zorundasın.",
                "is_cutscene": False
            }},
            {"event_type": "OBJECTIVE_ADD", "payload": {"obj_id": "reach_station"}},
            {"event_type": "REWARD",        "payload": {"score": 5000, "reason": "FABRİKA TRAVERSALI TAMAMLANDI"}},
        ],
        "karma_choices": {
            "train_combat": KarmaChoice(
                choice_id="train_combat",
                prompt_text="Tren gardiyanı seni fark etti!",
                option_a="[ÖLDÜR] Silahla hallet",
                option_b="[KAÇIŞ] Zıpla, atla, kaç",
                option_a_karma=-3,
                option_b_karma=1,
                option_a_tag="LETHAL",
                option_b_tag="PARKOUR_ESCAPE",
            )
        },
        "exit_condition": "objective_done",
        "exit_value": "reach_neon_town",
        "exit_to_stage": -1,   # -1 = misyon tamamlandı
    },

    # ── STAGE 8: EGEMENLERİN MALİKANESİ ──────────────────────────────────
    # Bölüm 16 — manor_stealth tipi
    # 4 adımlı senaryo: Bahçe → Terminal → Şifre → Kasa
    {
        "stage_id": 8,
        "name": "EGEMENLERİN MALİKANESİ — SIZMA",
        "trigger_level": 16,
        "trigger_score": 0,
        "theme_index": 6,   # MALİKANE teması
        "objectives": [
            {
                "obj_id": "cross_garden_wall",
                "text": "1) Bahçe duvarını havalandırma deliğinden aş",
                "optional": False
            },
            {
                "obj_id": "hack_terminal",
                "text": "2) Kütüphanedeki güvenlik terminalini hackle (E)",
                "optional": False
            },
            {
                "obj_id": "find_scroll",
                "text": "3) Efendi dairesinden Kasa Şifresini al (E)",
                "optional": False
            },
            {
                "obj_id": "find_secret_safe",
                "text": "4) Gizli Kasaya ulaş",
                "optional": False
            },
            {
                "obj_id": "stealth_optional_no_alert",
                "text": "[OPSİYONEL] Hiç alarm vermeden geç (+15 Karma)",
                "optional": True
            },
        ],
        "entry_events": [
            {
                "event_type": "DIALOGUE",
                "payload": {
                    "speaker": "SİSTEM",
                    "text": "EGEMEN MALİKANESİ — 5 KROM MUHAFIZ, 5 KAMERA. GİZLİLİK ZARURİ.",
                    "is_cutscene": True
                }
            },
            {
                "event_type": "DIALOGUE",
                "payload": {
                    "speaker": "SOKRAT",
                    "text": "Bahçe duvarını gördün mü? Kasalar üzerinden zıpla, duvardaki deliği bul.",
                    "is_cutscene": False
                }
            },
            {
                "event_type": "DIALOGUE",
                "payload": {
                    "speaker": "SOKRAT",
                    "text": "İçeri girince hedef: kütüphanedeki terminal. E tuşu hackler, kapı açılır.",
                    "is_cutscene": False
                }
            },
            {
                "event_type": "OBJECTIVE_ADD",
                "payload": {"obj_id": "cross_garden_wall"}
            },
            {
                "event_type": "OBJECTIVE_ADD",
                "payload": {"obj_id": "hack_terminal"}
            },
            {
                "event_type": "OBJECTIVE_ADD",
                "payload": {"obj_id": "find_scroll"}
            },
            {
                "event_type": "OBJECTIVE_ADD",
                "payload": {"obj_id": "find_secret_safe"}
            },
            {
                "event_type": "OBJECTIVE_ADD",
                "payload": {
                    "obj_id": "stealth_optional_no_alert",
                    "optional": True
                }
            },
        ],
        "karma_choices": {
            "manor_entry": KarmaChoice(
                choice_id="manor_entry",
                prompt_text="Malikane kapısı kilitli. Nasıl gireceksin?",
                option_a="[KABA KUVVETİ] Kapıyı kır, sesi duy",
                option_b="[GİZLİLİK] Bahçe duvarından tır",
                option_a_karma=-3,
                option_b_karma=2,
                option_a_tag="LOUD_ENTRY",
                option_b_tag="STEALTH_ENTRY",
            ),
            "found_scroll": KarmaChoice(
                choice_id="found_scroll",
                prompt_text="Efendi'nin yazışmaları elinde. İçinde masum isimler var. Ne yaparsın?",
                option_a="[YAK] Tehlikeli — yok et",
                option_b="[SAKLA] Belki işe yarar",
                option_a_karma=-1,
                option_b_karma=3,
                option_a_tag="",
                option_b_tag="INTEL_SAVED",
            ),
        },
        # ── ÇIKIŞ KOŞULU: area_reached — oyuncu kasaya ulaşınca ──────────
        # main.py her karede _flags["area_secret_safe"] değerini kontrol eder.
        "exit_condition": "area_reached",
        "exit_value": "secret_safe",
        "exit_to_stage": -1,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# 3. GÖREV YÖNETİCİSİ
# ─────────────────────────────────────────────────────────────────────────────

class MissionManager:
    """
    Ana görev yöneticisi. main.py'de bir kez örneklenir:
        mission_manager = MissionManager()

    Her karede iki çağrı:
        mission_manager.update(dt, player_x, player_y, score, level_idx)
        events = mission_manager.poll_events()   # List[MissionEvent]

    Karma seçimi için:
        delta = mission_manager.resolve_choice(choice_id, 'A' | 'B')
        save_manager.update_karma(delta)
    """

    def __init__(self):
        self.active_stage_idx: int = -1
        self.active_stage: Optional[Dict] = None
        self.objectives: List[MissionObjective] = []
        self.active_choice: Optional[KarmaChoice] = None
        self.choice_pending: bool = False
        self.mission_complete: bool = False

        # GC KURALI: sabit liste referansları — new list yaratılmaz
        self._event_queue: List[MissionEvent] = []
        self._activated_stages: set = set()
        self._resolved_choices: set = set()
        self._stage_transition_lock: bool = False
        self._flags: Dict[str, Any] = {}

        # Oyuncu durum takibi
        self.player_has_gun: bool = False
        self.soul_saved_count: int = 0
        self.used_stealth: bool = False
        self.intel_collected: bool = False

    # ── AŞAMA BAŞLAT ──────────────────────────────────────────────────────
    def _activate_stage(self, stage_def: Dict):
        sid = stage_def["stage_id"]
        if sid == self.active_stage_idx:
            return

        self.active_stage_idx = sid
        self.active_stage = stage_def
        self.objectives.clear()

        for obj_def in stage_def["objectives"]:
            self.objectives.append(MissionObjective(
                obj_id=obj_def["obj_id"],
                text=obj_def["text"],
                optional=obj_def.get("optional", False)
            ))

        # Giriş eventleri yalnızca ilk aktivasyonda kuyruğa girer
        if sid not in self._activated_stages:
            self._activated_stages.add(sid)
            for ev_def in stage_def["entry_events"]:
                self._event_queue.append(MissionEvent(
                    event_type=ev_def["event_type"],
                    payload=dict(ev_def.get("payload", {}))
                ))

        self._stage_transition_lock = False

    # ── GÜNCELLEME (her kare) ──────────────────────────────────────────────
    def update(self, dt: float, player_x: float, player_y: float,
               score: float, level_idx: int):
        if self.mission_complete or self.choice_pending:
            return

        # Tetikleme kontrolü
        for stage_def in STAGE_DEFS:
            sid = stage_def["stage_id"]
            # Aktif olan veya daha düşük id'li stage'i asla yeniden tetikleme
            if sid <= self.active_stage_idx:
                continue
            if sid in self._activated_stages:
                continue  # Zaten çalıştı

            if (level_idx == stage_def["trigger_level"] and
                    score >= stage_def["trigger_score"]):
                self._activate_stage(stage_def)
                break

        if not self.active_stage:
            return

        # Çıkış koşulu
        if not self._stage_transition_lock:
            self._check_exit(score)

    def _check_exit(self, score: float):
        if not self.active_stage:
            return
        cond  = self.active_stage["exit_condition"]
        value = self.active_stage["exit_value"]
        triggered = False

        if cond == "score":
            triggered = score >= value
        elif cond == "objective_done":
            triggered = any(
                o.obj_id == value and o.completed
                for o in self.objectives
            )
        elif cond == "combat_clear":
            triggered = self._flags.get("combat_cleared", False)
        elif cond == "area_reached":
            triggered = self._flags.get(f"area_{value}", False)

        if triggered:
            self._stage_transition_lock = True
            next_sid = self.active_stage.get("exit_to_stage", -1)
            if next_sid == -1:
                self._complete_mission()
            else:
                for sd in STAGE_DEFS:
                    if sd["stage_id"] == next_sid:
                        self._activate_stage(sd)
                        break

    def _complete_mission(self):
        self.mission_complete = True
        self._event_queue.append(MissionEvent(
            event_type="DIALOGUE",
            payload={
                "speaker": "SOKRAT",
                "text": "Fabrika geride kaldı. Neon Town sınırsız değil — ama en azından Mide değil.",
                "is_cutscene": False
            }
        ))
        self._event_queue.append(MissionEvent(
            event_type="UNLOCK",
            payload={"key": "neon_town_access", "value": True}
        ))
        self._event_queue.append(MissionEvent(
            event_type="REWARD",
            payload={"score": 10000, "reason": "GÖREV TAMAMLANDI: FABRİKA TRAVERSALI"}
        ))

    # ── OBJEKTİF İŞLEMLERİ ────────────────────────────────────────────────
    def complete_objective(self, obj_id: str) -> bool:
        for obj in self.objectives:
            if obj.obj_id == obj_id and not obj.completed:
                obj.completed = True
                self._event_queue.append(MissionEvent(
                    event_type="OBJECTIVE_DONE",
                    payload={"obj_id": obj_id}
                ))
                return True
        return False

    def add_objective(self, obj_id: str, text: str, optional: bool = False):
        for obj in self.objectives:
            if obj.obj_id == obj_id:
                return
        self.objectives.append(MissionObjective(obj_id=obj_id, text=text, optional=optional))
        self._event_queue.append(MissionEvent(
            event_type="OBJECTIVE_ADD",
            payload={"obj_id": obj_id, "text": text}
        ))

    # ── KARMA SEÇİMİ ──────────────────────────────────────────────────────
    def trigger_choice(self, choice_id: str) -> Optional[KarmaChoice]:
        """main.py belirli koşul oluşunca çağırır."""
        if not self.active_stage:
            return None
        if choice_id in self._resolved_choices:
            return None
        choice = self.active_stage.get("karma_choices", {}).get(choice_id)
        if choice:
            self.active_choice = choice
            self.choice_pending = True
            self._event_queue.append(MissionEvent(
                event_type="CHOICE_PENDING",
                payload={"choice": choice}
            ))
        return choice

    def resolve_choice(self, choice_id: str, option: str) -> int:
        """
        Oyuncu 'A' veya 'B' seçince çağrılır.
        Döndürdüğü int -> karma delta.
        main.py: save_manager.update_karma(mission_manager.resolve_choice(...))
        """
        if not self.active_choice or self.active_choice.choice_id != choice_id:
            return 0

        self._resolved_choices.add(choice_id)
        self.choice_pending = False

        if option == 'A':
            delta = self.active_choice.option_a_karma
            tag   = self.active_choice.option_a_tag
        else:
            delta = self.active_choice.option_b_karma
            tag   = self.active_choice.option_b_tag

        # Etiket etkileri
        if tag == "UNLOCK_GUN":
            self.player_has_gun = True
            self._event_queue.append(MissionEvent(
                event_type="UNLOCK",
                payload={"key": "player_gun", "value": True}
            ))
        elif tag == "SOUL_SAVED":
            self.soul_saved_count += 1
            self._event_queue.append(MissionEvent(
                event_type="UNLOCK",
                payload={"key": "saved_soul", "value": self.soul_saved_count}
            ))
        elif tag in ("STEALTH_ENTRY", "SMART_ENTRY"):
            self.used_stealth = True
            self._event_queue.append(MissionEvent(
                event_type="REWARD",
                payload={"score": 800, "reason": "GİZLİLİK BONUSU"}
            ))
        elif tag == "PARKOUR_ESCAPE":
            self._event_queue.append(MissionEvent(
                event_type="REWARD",
                payload={"score": 500, "reason": "PARKOUR KAÇIŞI"}
            ))

        self.active_choice = None
        return delta

    # ── FLAG SİSTEMİ ──────────────────────────────────────────────────────
    def set_flag(self, key: str, value: Any = True):
        self._flags[key] = value

    def get_flag(self, key: str, default: Any = False) -> Any:
        return self._flags.get(key, default)

    # ── İSTİHBARAT ODASI ÖZEL ─────────────────────────────────────────────
    def intel_pickup(self):
        """Tablet alındığında main.py çağırır."""
        if not self.intel_collected:
            self.intel_collected = True
            self.complete_objective("get_tablet")
            self._event_queue.append(MissionEvent(
                event_type="DIALOGUE",
                payload={
                    "speaker": "SİSTEM VERİSİ",
                    "text": (
                        "TREN KALKIŞ: 20:00  //  "
                        "VASİ: NEON TOWN NODE_7  //  "
                        "YASAKLI KARGO: SANAYİCİLER LOJİSTİK"
                    ),
                    "is_cutscene": True
                }
            ))
            self._event_queue.append(MissionEvent(
                event_type="UNLOCK",
                payload={"key": "map_unlocked", "value": True}
            ))
            self._event_queue.append(MissionEvent(
                event_type="REWARD",
                payload={"score": 2000, "reason": "İSTİHBARAT TOPLANDI"}
            ))

    # ── OLAY KUYRUĞU ──────────────────────────────────────────────────────
    def poll_events(self) -> List[MissionEvent]:
        """
        main.py her karede bu listeyi alır ve işler.
        GC KURALI: Var olan listeden kopyalanır, orijinal temizlenir.
        """
        if not self._event_queue:
            return []
        out = list(self._event_queue)
        self._event_queue.clear()
        return out

    # ── YARDIMCI SORGULAR ─────────────────────────────────────────────────
    def get_active_objectives(self) -> List[MissionObjective]:
        return [o for o in self.objectives if not o.completed]

    def get_current_stage_name(self) -> str:
        return self.active_stage.get("name", "") if self.active_stage else ""

    def is_stage_active(self, stage_id: int) -> bool:
        return self.active_stage_idx == stage_id

    def reset(self):
        """Yeni oyun başlarken çağrılır."""
        self.__init__()


# Global singleton
mission_manager = MissionManager()