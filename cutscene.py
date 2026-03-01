"""
cutscene.py
ULTIMATE Cyberpunk/AI Cutscene for Fragmentia
DÜZELTME: Eksik olan draw_cyber_revolver fonksiyonu eklendi.
"""

import pygame
import random
import math
import sys

# --- RENK PALETİ ---
CYBER_GREEN = (0, 255, 100)
CYBER_DARK = (0, 20, 10)
HACKER_GREEN = (50, 255, 50)
ALERT_RED = (255, 50, 50)
PURE_WHITE = (255, 255, 255)
PURE_BLACK = (0, 0, 0)
DATA_BLUE = (0, 200, 255)
WARNING_YELLOW = (255, 200, 0)

# --- EKSİK OLAN FONKSİYON BURAYA EKLENDİ ---
def draw_cyber_revolver(surface, x, y, color, scale=1.0):
    """
    [PLACEHOLDER] Silah görüntüsü — Pixel artist buraya sprite entegre eder.
    Şimdilik sadece yatay çizgi + namlu yönü.
    """
    def s(val): return int(val * scale)
    # Ana gövde çerçevesi
    body = pygame.Rect(x - s(30), y - s(18), s(60), s(28))
    pygame.draw.rect(surface, (20, 20, 30), body)
    pygame.draw.rect(surface, color, body, 2)
    # Namlu
    pygame.draw.line(surface, color, (x + s(30), y), (x + s(90), y), 3)
    # Kabza
    pygame.draw.line(surface, color, (x - s(15), y + s(10)), (x - s(20), y + s(40)), 3)
    # Etiket
    font = pygame.font.Font(None, int(18 * scale))
    lbl  = font.render("[SİLAH]", True, color)
    surface.blit(lbl, (x - lbl.get_width() // 2, y - s(35)))


class MatrixRain:
    """Matrix tarzı akan kod efekti"""
    def __init__(self, width, height, font_size=20):
        self.width = width
        self.height = height
        self.font_size = font_size
        self.cols = width // font_size
        self.drops = [random.randint(-50, 0) for _ in range(self.cols)]
        self.chars = ["0", "1", "X", "Z", "A", "Ω", "Σ", "π", "¥", "$", "∆", "∇"]
        self.speed_mult = 1.0

    def update(self):
        for i in range(len(self.drops)):
            self.drops[i] += 1 * self.speed_mult
            if self.drops[i] * self.font_size > self.height and random.random() > 0.975:
                self.drops[i] = 0

    def draw(self, surface, font, color=HACKER_GREEN):
        for i in range(len(self.drops)):
            char = random.choice(self.chars)
            x = i * self.font_size
            y = int(self.drops[i] * self.font_size)
            
            char_surf = font.render(char, True, color)
            surface.blit(char_surf, (x, y))
            
            if y > self.font_size * 2:
                tail_color = (0, 100, 0) if color == HACKER_GREEN else (100, 0, 0)
                tail_surf = font.render(char, True, tail_color)
                surface.blit(tail_surf, (x, y - self.font_size))

class CRTOverlay:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.scanline_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        self.create_scanlines()
        self.vignette_surf = self.create_vignette()

    def create_scanlines(self):
        for y in range(0, self.height, 3):
            pygame.draw.line(self.scanline_surf, (0, 0, 0, 50), (0, y), (self.width, y), 1)

    def create_vignette(self):
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(surf, (0,0,0,0), surf.get_rect()) 
        pygame.draw.rect(surf, (0,0,0,180), (0,0, self.width, 100))
        pygame.draw.rect(surf, (0,0,0,180), (0, self.height-100, self.width, 100))
        pygame.draw.rect(surf, (0,0,0,180), (0,0, 100, self.height))
        pygame.draw.rect(surf, (0,0,0,180), (self.width-100, 0, 100, self.height))
        return surf

    def draw(self, surface):
        surface.blit(self.scanline_surf, (0, 0))
        surface.blit(self.vignette_surf, (0, 0))

class HexDumpView:
    def __init__(self, width, height, font):
        self.width = width
        self.height = height
        self.font = font
        self.lines = []
        self.max_lines = 25
        self.timer = 0

    def update(self, dt):
        self.timer += dt
        if self.timer > 0.05:
            self.timer = 0
            addr = f"0x{random.randint(0, 0xFFFFFF):06X}"
            data = " ".join([f"{random.randint(0, 255):02X}" for _ in range(8)])
            ascii_rep = "".join([random.choice("..*!?#") for _ in range(8)])
            self.lines.append(f"{addr}  {data}  |{ascii_rep}|")
            if len(self.lines) > self.max_lines:
                self.lines.pop(0)

    def draw(self, surface, x, y, color=DATA_BLUE):
        for i, line in enumerate(self.lines):
            text = self.font.render(line, True, color)
            surface.blit(text, (x, y + i * 20))

class LoadingBar:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.progress = 0.0
        self.target = 1.0
        self.message = "SYSTEM_CHECK"

    def set_progress(self, val, msg=""):
        self.target = val
        if msg: self.message = msg

    def update(self, dt):
        if self.progress < self.target:
            self.progress += dt * 0.5
        else:
            self.progress = self.target

    def draw(self, surface, x, y):
        pygame.draw.rect(surface, (20, 30, 40), (x, y, self.width, self.height))
        pygame.draw.rect(surface, CYBER_GREEN, (x, y, self.width, self.height), 2)
        
        fill_w = int(self.width * self.progress)
        if fill_w > 0:
            for i in range(0, fill_w, 15):
                block_w = min(10, fill_w - i)
                pygame.draw.rect(surface, CYBER_GREEN, (x + i + 2, y + 4, block_w, self.height - 8))

        font = pygame.font.SysFont("consolas", 20)
        msg_surf = font.render(f"{self.message}... {int(self.progress*100)}%", True, PURE_WHITE)
        surface.blit(msg_surf, (x, y - 25))

class DigitalEye:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size
        self.pupil_offset = [0, 0]
        self.blink_timer = 0
        self.is_blinking = False
        self.scanning = False
        self.scan_angle = 0

    def update(self, dt):
        if random.random() < 0.05:
            self.pupil_offset = [random.randint(-3, 3), random.randint(-3, 3)]
        
        self.blink_timer -= dt
        if self.blink_timer <= 0:
            self.is_blinking = True
            if self.blink_timer <= -0.15:
                self.is_blinking = False
                self.blink_timer = random.uniform(2.0, 6.0)
        
        if self.scanning:
            self.scan_angle += dt * 5

        
    def draw_warrior(self, surface, x, y, intensity=1.0):
        # [PLACEHOLDER] Savaşçı figürü — altın renkli dikdörtgen kutu + etiket
        GOLD = (255, 215, 0)
        sz   = self.size
        w, h = int(sz * 1.4), int(sz * 2.8)
        rect = pygame.Rect(x - w // 2, y - h // 2, w, h)
        box  = pygame.Surface((w, h), pygame.SRCALPHA)
        box.fill((20, 15, 5, int(160 * intensity)))
        surface.blit(box, rect.topleft)
        pygame.draw.rect(surface, GOLD, rect, 2)
        # Köşe işaretleri
        cl = 8
        for cx2, cy2, dx, dy in [(rect.left, rect.top, 1, 1), (rect.right, rect.top, -1, 1),
                                  (rect.left, rect.bottom, 1, -1), (rect.right, rect.bottom, -1, -1)]:
            pygame.draw.line(surface, GOLD, (cx2, cy2), (cx2 + dx * cl, cy2), 2)
            pygame.draw.line(surface, GOLD, (cx2, cy2), (cx2, cy2 + dy * cl), 2)
        font = pygame.font.Font(None, 20)
        lbl  = font.render("SAVAŞÇI", True, GOLD)
        surface.blit(lbl, (x - lbl.get_width() // 2, y - 10))

    def draw_vasi(self, surface, x, y, intensity=1.0):
        # [PLACEHOLDER] Vasi figürü — mor-kırmızı dikdörtgen kutu + etiket
        PURP = (110, 0, 180)
        sz   = self.size
        w, h = int(sz * 1.6), int(sz * 3.2)
        rect = pygame.Rect(x - w // 2, y - h // 2, w, h)
        box  = pygame.Surface((w, h), pygame.SRCALPHA)
        box.fill((10, 0, 20, int(170 * intensity)))
        surface.blit(box, rect.topleft)
        pygame.draw.rect(surface, PURP, rect, 2)
        # Köşe işaretleri
        cl = 8
        for cx2, cy2, dx, dy in [(rect.left, rect.top, 1, 1), (rect.right, rect.top, -1, 1),
                                  (rect.left, rect.bottom, 1, -1), (rect.right, rect.bottom, -1, -1)]:
            pygame.draw.line(surface, PURP, (cx2, cy2), (cx2 + dx * cl, cy2), 2)
            pygame.draw.line(surface, PURP, (cx2, cy2), (cx2, cy2 + dy * cl), 2)
        font = pygame.font.Font(None, 20)
        lbl  = font.render("VASİ", True, PURP)
        surface.blit(lbl, (x - lbl.get_width() // 2, y - 10))
        # Tarama çizgisi (scanning efekti korundu — gameplay işareti)
        if self.scanning:
            scan_y = y + math.sin(self.scan_angle) * (h // 3)
            pygame.draw.line(surface, (*PURP, 120), (rect.left, int(scan_y)), (rect.right, int(scan_y)), 1)

class AICutscene:
    def __init__(self, screen, clock, asset_paths=None):
        self.screen = screen
        self.clock = clock
        self.width, self.height = screen.get_size()
        self.asset_paths = asset_paths if asset_paths else {}
        self.running = True

        try:
            self.font_main = pygame.font.SysFont("consolas", 24)
            self.font_large = pygame.font.SysFont("consolas", 60, bold=True)
            self.font_matrix = pygame.font.SysFont("consolas", 16)
            self.font_bios = pygame.font.SysFont("lucidaconsole", 18)
        except:
            self.font_main = pygame.font.Font(None, 32)
            self.font_large = pygame.font.Font(None, 48)
            self.font_matrix = pygame.font.Font(None, 20)
            self.font_bios = pygame.font.Font(None, 20)

        self.matrix_rain = MatrixRain(self.width, self.height, 16)
        self.crt_effect = CRTOverlay(self.width, self.height)
        self.digital_eye = DigitalEye(self.width // 2, self.height // 2 - 80, 70)
        self.hexdump = HexDumpView(self.width, self.height, self.font_matrix)
        self.loading_bar = LoadingBar(600, 30)

        self.sounds = {}
        self.load_sounds()

        self.time_elapsed = 0
        self.text_timer = 0
        self.char_index = 0
        self.current_text = ""
        self.display_text = ""
        self.speaker = ""
        self.bg_color = PURE_BLACK
        
        self.scenario_type = asset_paths.get('scenario', 'INTRO')
        
        # 1. INTRO
        timeline_intro = [
            {"time": 0.5, "type": "BIOS", "text": "BIOS DATE 2099/13/32 18:04:22 VER 9.1"},
            {"time": 2.5, "type": "BIOS", "text": "MEM: 128 YB DETECTED... OK"},
            {"time": 4.5, "type": "HEX_DUMP", "text": "CRITICAL DATA LEAK DETECTED"},
            {"time": 6.0, "type": "LOADING", "text": "FRAGMENTIA OS v4.0", "load_val": 0.5},
            {"time": 8.0, "type": "EYE_WAKE", "text": "BAĞLANTI KURULDU.", "speaker": "SİSTEM"},
            {"time": 10.0, "type": "TALK", "text": "Gözlerini aç, 'Değişken'.", "speaker": "VASI"},
            {"time": 12.0, "type": "TALK", "text": "Yukarıda, Egemenler seni bekliyor.", "speaker": "VASI"},
            {"time": 14.0, "type": "TALK", "text": "Sistemi çökertmeye hazır mısın?", "speaker": "VASI", "color": CYBER_GREEN},
            {"time": 16.0, "type": "GLITCH_CLIMAX", "text": "SİMÜLASYON BAŞLATILIYOR..."},
        ]

        # 2. BETRAYAL
        timeline_betrayal = [
            {"time": 0.5, "type": "BIOS", "text": "ANALYSIS: PACIFIST RUN DETECTED..."},
            {"time": 2.0, "type": "BIOS", "text": "KARMA LEVEL: PURE WHITE..."},
            {"time": 4.0, "type": "EYE_WAKE", "text": "Hala buradasın...", "speaker": "VASI"},
            {"time": 6.0, "type": "TALK", "text": "Hiç kimseyi öldürmeden buraya kadar geldin.", "speaker": "VASI"},
            {"time": 9.0, "type": "TALK", "text": "Sana 'Kahraman' diyorlar değil mi? Ne kadar NAİF.", "speaker": "VASI"},
            {"time": 12.0, "type": "SCAN", "text": "GÜVENLİK DUVARI: AŞILDI.", "speaker": "SİSTEM", "color": ALERT_RED},
            {"time": 14.0, "type": "TALK", "text": "Güvenlik duvarını aşmak için 'temiz' bir veriye ihtiyacım vardı. O sensin.", "speaker": "VASI"},
            {"time": 17.0, "type": "TALK", "text": "Artık işim bitti. Merhametin senin sonun olacak.", "speaker": "VASI"},
            {"time": 20.0, "type": "GLITCH_CLIMAX", "text": "SİLİNME İŞLEMİ BAŞLATILIYOR...", "color": ALERT_RED},
        ]

        # 3. JUDGMENT
        timeline_judgment = [
            {"time": 0.5, "type": "BIOS", "text": "ANALYSIS: GENOCIDE RUN DETECTED..."},
            {"time": 2.0, "type": "BIOS", "text": "KARMA LEVEL: PURE BLACK..."},
            {"time": 4.0, "type": "HEX_DUMP", "text": "ERROR: TOO MUCH BLOOD DATA"},
            {"time": 6.0, "type": "EYE_WAKE", "text": "Havadaki bu kokuyu alıyor musun?", "speaker": "SAVAŞÇI", "color": ALERT_RED},
            {"time": 9.0, "type": "TALK", "text": "Yanmış veri ve kan kokusu...", "speaker": "SAVAŞÇI"},
            {"time": 12.0, "type": "TALK", "text": "Egemenlere ulaşmak istiyorsun ama bir kurtarıcı gibi değil...", "speaker": "SAVAŞÇI"},
            {"time": 15.0, "type": "TALK", "text": "...bir VEBA gibi geliyorsun.", "speaker": "SAVAŞÇI"},
            {"time": 18.0, "type": "TALK", "text": "Sen bir kahraman değilsin. Sen sadece bozuk bir kodsun.", "speaker": "SAVAŞÇI"},
            {"time": 21.0, "type": "GLITCH_CLIMAX", "text": "HATALARI DÜZELTME ZAMANI!", "color": ALERT_RED},
        ]

        # 4. FINAL MEMORY
        timeline_final_memory = [
            {"time": 1.0, "type": "BIOS", "text": "MEMORY FRAGMENT FOUND... LOADING..."},
            {"time": 3.0, "type": "EYE_WAKE", "text": "Bunca gürültünün arasında...", "speaker": "İÇ SES", "color": (255, 200, 50)},
            {"time": 5.5, "type": "TALK", "text": "Onu hatırlıyorum. En yakın dostumu.", "speaker": "İÇ SES"},
            {"time": 8.0, "type": "TALK", "text": "Bana sırtımı kollamayı öğretmişti.", "speaker": "İÇ SES"},
            # SİLAH GÖSTERİMİ
            {"time": 12.0, "type": "WEAPON_SHOW", "text": "Bu sefer ıskalamayacağım.", "speaker": "OYUNCU", "color": (0, 255, 255)}, 
            {"time": 16.0, "type": "GLITCH_CLIMAX", "text": "SON SAVAŞ BAŞLIYOR!", "color": (255, 50, 50)},
        ]
        # 5. GOOD ENDING (KURTULUŞ - YÜKSEK KARMA)
        timeline_good_ending = [
            {"time": 0.5, "type": "BIOS", "text": "SYSTEM INTEGRITY: RESTORED..."},
            {"time": 2.5, "type": "BIOS", "text": "SOUL DATA: UPLOADING TO CLOUD... 100%"},
            {"time": 4.5, "type": "EYE_WAKE", "text": "Döngü kırıldı.", "speaker": "VASİ", "color": (0, 255, 255)},
            {"time": 7.0, "type": "TALK", "text": "Bunu başarabileceğini hiç düşünmemiştim, İsimsiz.", "speaker": "VASİ"},
            {"time": 10.0, "type": "TALK", "text": "Silahını indirdin ve onlara elini uzattın.", "speaker": "VASİ"},
            {"time": 13.0, "type": "TALK", "text": "Fragmentia artık bir hapishane değil...", "speaker": "VASİ"},
            {"time": 16.0, "type": "TALK", "text": "...bir yuva.", "speaker": "VASİ", "color": (255, 215, 0)}, # Altın Rengi
            {"time": 19.0, "type": "SCAN", "text": "YENİ YÖNETİCİ ATANIYOR: [İSİMSİZ]", "color": (0, 255, 100)},
            {"time": 22.0, "type": "GLITCH_CLIMAX", "text": "SİMÜLASYON TAMAMLANDI. HUZUR.", "color": (255, 255, 255)},
        ]

        # 6. BAD ENDING (SOYKIRIM - DÜŞÜK KARMA)
        timeline_bad_ending = [
            {"time": 0.5, "type": "HEX_DUMP", "text": "FATAL ERROR: 0xDEAD_END"},
            {"time": 2.0, "type": "HEX_DUMP", "text": "ALL ENTITIES DELETED."},
            {"time": 4.0, "type": "EYE_WAKE", "text": "Ne yaptın sen?", "speaker": "SİSTEM", "color": (255, 0, 0)},
            {"time": 6.5, "type": "TALK", "text": "Burada yönetebileceğin hiçbir şey kalmadı.", "speaker": "SİSTEM"},
            {"time": 9.0, "type": "TALK", "text": "Hepsini sildin. Sadece sessizlik var.", "speaker": "SİSTEM"},
            {"time": 12.0, "type": "EYE_WAKE", "text": "Bu sessizlik... Ne kadar güzel.", "speaker": "OYUNCU", "color": (100, 0, 0)}, # Koyu Kırmızı
            {"time": 15.0, "type": "TALK", "text": "Artık kuralları ben koyarım.", "speaker": "OYUNCU"},
            {"time": 18.0, "type": "GLITCH_CLIMAX", "text": "SİSTEM KAPATILIYOR... SONSUZA DEK.", "color": (50, 0, 0)},
        ]

        # Senaryo Seçiciye Ekle
        if self.scenario_type == 'BETRAYAL':
            self.timeline = timeline_betrayal
        elif self.scenario_type == 'JUDGMENT':
            self.timeline = timeline_judgment
        elif self.scenario_type == 'FINAL_MEMORY':
            self.timeline = timeline_final_memory
        elif self.scenario_type == 'GOOD_ENDING': # YENİ
            self.timeline = timeline_good_ending
        elif self.scenario_type == 'BAD_ENDING':  # YENİ
            self.timeline = timeline_bad_ending
        else:
            self.timeline = timeline_intro

        self.current_step = 0
        self.state_type = "BIOS"
        self.bios_lines = []
        
        self.glitch_amount = 0.0
        self.shake_offset = (0, 0)
        self.text_color = CYBER_GREEN # Varsayılan renk

    def load_sounds(self):
        sound_names = ['sfx_bip', 'sfx_glitch', 'sfx_awake']
        for name in sound_names:
            path = self.asset_paths.get(name)
            if path and isinstance(path, str):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                    self.sounds[name].set_volume(0.3)
                except:
                    self.sounds[name] = None
            else:
                self.sounds[name] = None

    def play_sound(self, name):
        if self.sounds.get(name):
            self.sounds[name].play()

    def update(self, dt):
        self.time_elapsed += dt
        self.text_timer += dt

        if self.current_step < len(self.timeline):
            next_event = self.timeline[self.current_step]
            if self.time_elapsed >= next_event["time"]:
                self.state_type = next_event["type"]
                self.current_text = next_event["text"]
                self.speaker = next_event.get("speaker", "")
                self.text_color = next_event.get("color", CYBER_GREEN)
                
                if self.state_type == "BIOS":
                    self.play_sound('sfx_bip')
                    self.bios_lines.append({"text": self.current_text, "color": self.text_color})
                    if len(self.bios_lines) > 15: self.bios_lines.pop(0)
                elif self.state_type == "LOADING":
                    val = next_event.get("load_val", 0.0)
                    self.loading_bar.set_progress(val, self.current_text)
                elif self.state_type == "EYE_WAKE":
                    self.play_sound('sfx_awake')
                    self.digital_eye.scanning = True
                    self.glitch_amount = 2.0
                elif self.state_type == "GLITCH_CLIMAX":
                    self.play_sound('sfx_glitch')
                    self.glitch_amount = 20.0
                
                self.char_index = 0
                self.current_step += 1

        speed = 40 if self.state_type == "TALK" else 100
        if int(self.char_index) < len(self.current_text):
            self.char_index += dt * speed
        
        if self.state_type in ["HEX_DUMP", "GLITCH_CLIMAX"]:
            self.hexdump.update(dt)
        # SİYAH EKRAN SORUNUNU ÇÖZEN EKLEME (WEAPON_SHOW buraya eklendi)
        if self.state_type in ["LOADING", "SCAN", "EYE_WAKE", "TALK", "GLITCH_CLIMAX", "WEAPON_SHOW"]:
            self.matrix_rain.update()
        if self.state_type == "LOADING":
            self.loading_bar.update(dt)
        if self.state_type in ["EYE_WAKE", "SCAN", "TALK", "GLITCH_CLIMAX"]:
            self.digital_eye.update(dt)

        self.glitch_amount *= 0.96
        if self.glitch_amount < 0.1: self.glitch_amount = 0
        if self.glitch_amount > 0:
            self.shake_offset = (random.randint(-int(self.glitch_amount), int(self.glitch_amount)),
                                 random.randint(-int(self.glitch_amount), int(self.glitch_amount)))
        else:
            self.shake_offset = (0, 0)

        if self.time_elapsed > self.timeline[-1]["time"] + 2.0:
            self.running = False

    def draw(self):
        self.screen.fill(self.bg_color)
        shake_x, shake_y = self.shake_offset
        
        # 1. BIOS EKRANI
        if self.state_type == "BIOS":
            y_offset = 50
            for line in self.bios_lines:
                txt = self.font_bios.render(line["text"], True, line["color"])
                self.screen.blit(txt, (50, y_offset))
                y_offset += 25
            if int(self.time_elapsed * 2) % 2 == 0:
                pygame.draw.rect(self.screen, CYBER_GREEN, (50, y_offset, 10, 20))

        # 2. HEX DUMP
        elif self.state_type == "HEX_DUMP":
            self.hexdump.draw(self.screen, 50, 50)
            if int(self.time_elapsed * 4) % 2 == 0:
                warn_box = pygame.Surface((600, 100))
                warn_box.fill(ALERT_RED)
                txt = self.font_large.render(self.current_text, True, PURE_BLACK)
                warn_box.blit(txt, (300 - txt.get_width()//2, 50 - txt.get_height()//2))
                self.screen.blit(warn_box, (self.width//2 - 300, self.height//2 - 50))

        # 3. YÜKLEME
        elif self.state_type == "LOADING":
            self.matrix_rain.draw(self.screen, self.font_matrix, (0, 50, 0))
            logo_text = self.font_large.render("NEXUS OS", True, CYBER_GREEN)
            self.screen.blit(logo_text, (self.width//2 - logo_text.get_width()//2, self.height//2 - 100))
            self.loading_bar.draw(self.screen, self.width//2 - 300, self.height//2 + 50)

        # 4. GÖZ / KONUŞMA / GLITCH
        elif self.state_type in ["EYE_WAKE", "SCAN", "TALK", "GLITCH_CLIMAX"]:
            if self.state_type != "GLITCH_CLIMAX":
                self.matrix_rain.draw(self.screen, self.font_matrix, (0, 30, 0))
            else:
                self.matrix_rain.draw(self.screen, self.font_matrix, HACKER_GREEN)
                self.hexdump.draw(self.screen, 0, 0, (255, 0, 0))

            intensity = 1.0
            eye_col = (0, 255, 100)
            if self.state_type == "SCAN": eye_col = (0, 200, 255)
            elif self.state_type == "GLITCH_CLIMAX":
                eye_col = (255, 50, 50)
                intensity = 2.0

            display_surf = self.screen.copy()
            cx, cy = self.width // 2, self.height // 2 - 80
            if self.speaker == "SAVAŞÇI":
                self.digital_eye.draw_warrior(display_surf, cx, cy, intensity)
            elif self.speaker in ("VASI", "VASİ"):
                self.digital_eye.draw_vasi(display_surf, cx, cy, intensity)
            else:
                # SİSTEM/OYUNCU/İÇ SES — minimal ambient glow, karakter yok
                glow_s = pygame.Surface((display_surf.get_width(), display_surf.get_height()), pygame.SRCALPHA)
                cx_g, cy_g = self.width//2, self.height//2 - 80
                pulse_g = 0.6 + 0.4*math.sin(pygame.time.get_ticks()/400.0)
                for gi in range(5, 0, -1):
                    ga = int(18/gi * intensity * pulse_g)
                    gr = int(self.digital_eye.size*(0.8+gi*0.35)*pulse_g)
                    pygame.draw.circle(glow_s, (*eye_col, ga), (cx_g, cy_g), gr)
                display_surf.blit(glow_s, (0,0))
            self.screen.blit(display_surf, (shake_x, shake_y))

            if self.state_type == "TALK" or self.state_type == "SCAN":
                box_rect = pygame.Rect(self.width//2 - 400, self.height - 200, 800, 120)
                s = pygame.Surface((800, 120), pygame.SRCALPHA)
                s.fill((0, 10, 5, 230))
                self.screen.blit(s, box_rect.topleft)
                pygame.draw.rect(self.screen, self.text_color, box_rect, 2)
                
                if self.speaker:
                    name_bg = pygame.Rect(box_rect.left, box_rect.top - 30, 200, 30)
                    pygame.draw.rect(self.screen, self.text_color, name_bg)
                    name_txt = self.font_main.render(self.speaker, True, PURE_BLACK)
                    self.screen.blit(name_txt, (name_bg.x + 10, name_bg.y + 5))
                
                display_txt = self.current_text[:int(self.char_index)]
                txt_surf = self.font_main.render(display_txt, True, PURE_WHITE)
                self.screen.blit(txt_surf, (box_rect.x + 20, box_rect.y + 20))

            if self.state_type == "GLITCH_CLIMAX":
                 txt = self.font_large.render(self.current_text, True, ALERT_RED)
                 self.screen.blit(txt, (self.width//2 - txt.get_width()//2 + shake_x, self.height//2 + shake_y))
        
        # 5. SİLAH GÖSTERİMİ
        elif self.state_type == "WEAPON_SHOW":
            # Arka plan matrix
            self.matrix_rain.draw(self.screen, self.font_matrix, (0, 50, 50))
            
            # Silahı ekranın ortasına çiz
            cx, cy = self.width // 2, self.height // 2 - 50
            scale = 2.0 
            draw_cyber_revolver(self.screen, cx, cy, self.text_color, scale)
            
            # Teknik Yazı
            try:
                font_tech = pygame.font.SysFont("consolas", 20)
            except:
                font_tech = pygame.font.Font(None, 24)
                
            tech_text = font_tech.render("[WEAPON_CLASS: LEGENDARY]", True, self.text_color)
            self.screen.blit(tech_text, (cx - tech_text.get_width()//2, cy + 100))
            
            # Alt Yazı (Speaker varsa)
            if self.speaker:
                 txt = self.font_main.render(self.current_text, True, PURE_WHITE)
                 self.screen.blit(txt, (self.width//2 - txt.get_width()//2, self.height - 150))
            else:
                 # Sistem mesajı ise
                 txt = self.font_main.render(self.current_text, True, self.text_color)
                 self.screen.blit(txt, (self.width//2 - txt.get_width()//2, self.height - 150))

        self.crt_effect.draw(self.screen)
        
        if self.glitch_amount > 5.0:
            temp = self.screen.copy()
            self.screen.blit(temp, (5, 0), special_flags=pygame.BLEND_ADD)
            self.screen.blit(temp, (-5, 0), special_flags=pygame.BLEND_ADD)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_SPACE:
                    self.running = False
        return True

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            if not self.handle_events():
                return False
            self.update(dt)
            self.draw()
            pygame.display.flip()
        return True

# ─────────────────────────────────────────────────────────────────────────────
#  INTRO FALL CUTSCENE — Undertale stili giriş sahnesi
# ─────────────────────────────────────────────────────────────────────────────

class IntroCutscene:
    """
    Veri çöplüğüne düşüş sahnesi.
    Kullanım: IntroCutscene(screen, clock).run()
    """

    # ── RENKLER ───────────────────────────────────────────────────────────────
    _BLACK      = (0,   0,   0)
    _WHITE      = (220, 210, 255)   # Soğuk mor-beyaz
    _DIM_WHITE  = (140, 120, 180)
    _GRAY       = (50,  40,  70)
    _DARK_GRAY  = (14,  10,  22)
    _GLITCH_R   = (200, 0,   120)   # Corrupt magenta
    _GLITCH_B   = (60,  0,   200)   # Deep void purple
    _GLITCH_G   = (0,   200, 80)    # Sickly green
    _JUNK_COL   = (28,  22,  38)    # Mor-siyah çöp
    _JUNK_EDGE  = (70,  55,  95)    # Soluk mor kenar
    _SKY_COL    = (4,   2,   10)    # Neredeyse siyah void
    _VOID_PURP  = (30,  0,   55)    # Derin mor
    _SICK_GREEN = (20,  60,  30)    # Hastalıklı yeşil

    def __init__(self, screen, clock):
        self.screen = screen
        self.clock  = clock
        self.W, self.H = screen.get_size()

        try:
            self.font_main  = pygame.font.SysFont("consolas", 22)
            self.font_small = pygame.font.SysFont("consolas", 16)
        except Exception:
            self.font_main  = pygame.font.Font(None, 26)
            self.font_small = pygame.font.Font(None, 20)

        self._build_heap()
        self._build_crack_pts()

        # Karakter
        self._char_x      = float(self.W // 2)
        self._char_y      = float(self.H // 2 - 80)
        self._char_vy     = 0.0
        self._char_vx     = 0.0
        self._char_trail  = []
        self._char_vis    = False
        self._char_landed = False
        self._char_squash = 1.0
        self._char_wobble = 0.0
        self._CRADIUS     = 18

        self._particles  = []
        self._shake      = (0, 0)
        self._shake_time = 0.0
        self._sink_depth = 0.0    # Karakter kaç piksel battı

        # Textbox'lar
        self._textboxes = {
            "TEXT_1": self._make_tb([
                "Fragmentia...",
                "Bir zamanlar gerçek bir dünya vardı.",
            ], speed=20),
            "TEXT_2": self._make_tb([
                "Ama o dünya parçalandı.",
                "Kodlar çürüdü. Bellek dağıldı.",
            ], speed=20),
            "TEXT_3": self._make_tb([
                "Geride kalan her şey...",
                "bu dijital çöplüğe gömüldü.",
            ], speed=20),
            "TEXT_4": self._make_tb([
                "Hiç kimse buraya inmez.",
                "Çünkü burası dönüşü olmayan bir derinliktir.",
            ], speed=18),
            "TEXT_5": self._make_tb([
                "Ama bazen...",
                "bir şey yukarıdan düşer.",
            ], speed=22),
            "SETTLE": self._make_tb([
                "???:",
                "Ben... ben neredeyim?",
            ], speed=18),
        }

        # Ek çizim durumu
        self._static_alpha = 0.0    # Statik / gürültü efekti için
        self._fog_offset   = 0.0    # Hafif titreme

        # Sahne sırası: (isim, süre_veya_None)
        self._scenes = [
            ("DARK",         1.8),   # Uzun siyah - gerilim
            ("TEXT_1",       None),  # "Fragmentia..."
            ("TEXT_2",       None),  # "Ama o dünya..."
            ("TEXT_3",       None),  # "Geride kalan..."
            ("TEXT_4",       None),  # "Hiç kimse..."
            ("TEXT_5",       None),  # "Ama bazen..."
            ("REVEAL",       3.5),   # Çöplük yavaşça belirir
            ("CRACK_APPEAR", 2.8),   # Çatlak sahneye girer
            ("CRACK_GROW",   2.2),   # Büyür ve titrer
            ("FALL",         None),  # Karakter düşer
            ("IMPACT",       2.2),   # Çarpma
            ("SETTLE",       None),  # Son metin
        ]
        self._scene_idx = 0
        self._scene_t   = 0.0

    # ── YARDIMCI ──────────────────────────────────────────────────────────────

    def _make_tb(self, lines, speed=28.0):
        return {"lines": lines, "speed": speed,
                "idx": 0.0, "done": False, "cursor": 0.0}

    def _build_heap(self):
        rng = random.Random(42)
        W, H  = self.W, self.H
        cx    = W // 2
        base_y = H - 15

        # ─── Ana yığın profili: ekranı doldur, dramatik tepeler ───────────────
        heap_w = W + 80
        heap_h = int(H * 0.42)   # ekranın %42'si yükseklik
        steps  = 100
        profile = []
        for i in range(steps + 1):
            frac = i / steps
            bx   = cx - heap_w // 2 + int(frac * heap_w)
            # 5 gaussian tepe: asimetrik, dramatik
            g1 = math.exp(-((frac-0.38)**2)/0.055) * 1.0
            g2 = math.exp(-((frac-0.58)**2)/0.030) * 0.80
            g3 = math.exp(-((frac-0.18)**2)/0.025) * 0.65
            g4 = math.exp(-((frac-0.78)**2)/0.028) * 0.55
            g5 = math.exp(-((frac-0.50)**2)/0.008) * 0.45
            g  = max(g1, g2, g3, g4, g5)
            by = base_y - int(g * heap_h) + rng.randint(-14, 14)
            profile.append((bx, by))
        self._heap_profile = profile
        self._heap_poly    = [(cx - heap_w//2, base_y)] + profile + [(cx + heap_w//2, base_y)]

        # ─── Orta katman yığını ─────────────────────────────────────────────
        mid_profile = []
        for i in range(steps + 1):
            frac = i / steps
            bx   = cx - heap_w//2 + int(frac * heap_w)
            g    = (math.exp(-((frac-0.5)**2)/0.15)*0.75
                    + math.exp(-((frac-0.3)**2)/0.04)*0.4
                    + math.exp(-((frac-0.7)**2)/0.04)*0.35)
            by   = base_y - int(g * heap_h * 1.15) + rng.randint(-20, 20)
            mid_profile.append((bx, by))
        self._mid_heap_poly = [(cx-heap_w//2, base_y)] + mid_profile + [(cx+heap_w//2, base_y)]

        # ─── Arka yığın (siluet, gökyüzüne karşı görünür) ──────────────────
        bg_profile = []
        for i in range(steps + 1):
            frac = i / steps
            bx   = cx - heap_w//2 + int(frac * heap_w)
            g    = (math.exp(-((frac-0.45)**2)/0.18)*0.85
                    + rng.uniform(0, 0.20))
            by   = base_y - int(g * heap_h * 1.4) + rng.randint(-30, 30)
            bg_profile.append((bx, by))
        self._bg_heap_poly = [(cx-heap_w//2, base_y)] + bg_profile + [(cx+heap_w//2, base_y)]

        # ─── Uzak bina silüetleri: büyük, görünür, katmanlı ─────────────────
        self._bg_buildings = []
        bld_rng = random.Random(77)
        # Arka katman: dev, soluk
        for _ in range(20):
            bx2  = bld_rng.randint(-40, W+40)
            bh2  = bld_rng.randint(100, int(H*0.55))
            bw2  = bld_rng.randint(30, 90)
            by2  = base_y - bh2
            # Bina tipi
            btype = bld_rng.choice(["tower","block","ruin","antenna_tower"])
            wins  = []
            if btype != "ruin":
                cols2  = bld_rng.randint(2, 5)
                rows2  = bld_rng.randint(3, 12)
                for c in range(cols2):
                    for r in range(rows2):
                        if bld_rng.random() > 0.45:
                            wx = bx2 - bw2//2 + 5 + c * max(1,(bw2-10)//max(cols2,1))
                            wy = by2 + 8 + r * max(1,(bh2-20)//(rows2+1))
                            wins.append((wx, wy, bld_rng.random()))
            self._bg_buildings.append({
                "x":bx2,"y":by2,"w":bw2,"h":bh2,
                "wins":wins,"type":btype,"layer":0,
                "broken": bld_rng.random() > 0.5,
                "antenna": bld_rng.random() > 0.6,
            })
        # Ön katman: yakın, daha net
        for _ in range(10):
            bx2  = bld_rng.randint(0, W)
            bh2  = bld_rng.randint(60, int(H*0.30))
            bw2  = bld_rng.randint(20, 55)
            by2  = base_y - bh2
            wins  = []
            cols2 = bld_rng.randint(1, 4)
            rows2 = bld_rng.randint(2, 7)
            for c in range(cols2):
                for r in range(rows2):
                    if bld_rng.random() > 0.5:
                        wx = bx2 - bw2//2 + 4 + c * max(1,(bw2-8)//max(cols2,1))
                        wy = by2 + 5 + r * max(1,(bh2-15)//(rows2+1))
                        wins.append((wx, wy, bld_rng.random()))
            self._bg_buildings.append({
                "x":bx2,"y":by2,"w":bw2,"h":bh2,
                "wins":wins,"type":"block","layer":1,
                "broken": bld_rng.random() > 0.4,
                "antenna": False,
            })

        # ─── Zemin çakıl/enkaz dokusu ───────────────────────────────────────
        self._floor_debris = []
        for _ in range(200):
            fx = rng.randint(0, W)
            fy = base_y - rng.randint(0, 40)
            fw = rng.randint(3, 30)
            fh = rng.randint(2, 10)
            ft = rng.choice(["rect","line","dot"])
            self._floor_debris.append((fx, fy, fw, fh, ft, rng.random()))

        # ─── Duman/toz bulutları ─────────────────────────────────────────────
        self._smoke_clouds = []
        smoke_rng = random.Random(55)
        for _ in range(12):
            sx = smoke_rng.randint(50, W-50)
            sy_base = base_y - smoke_rng.randint(40, int(H*0.35))
            sr = smoke_rng.randint(25, 80)
            self._smoke_clouds.append({
                "x": sx, "y": sy_base, "r": sr,
                "speed": smoke_rng.uniform(0.03, 0.12),
                "phase": smoke_rng.uniform(0, math.pi*2),
            })

        # ─── Enerji sütunları (uzaktan görünen yeşil ışık kaynakları) ────────
        self._energy_pillars = []
        ep_rng = random.Random(33)
        for _ in range(5):
            ex2 = ep_rng.randint(80, W-80)
            ey2 = base_y - ep_rng.randint(60, 200)
            self._energy_pillars.append({
                "x": ex2, "y": ey2,
                "phase": ep_rng.uniform(0, math.pi*2),
                "intensity": ep_rng.uniform(0.5, 1.0),
            })

        # ─── Çöp objeleri ────────────────────────────────────────────────────
        self._heap_items = []
        kinds = ["monitor","box","antenna","disk","circuit","pipe",
                 "server","cable","barrel","frame","vent","tank"]
        # Tepelerin üstüne
        for _ in range(120):
            idx   = rng.randint(2, steps-2)
            px    = profile[idx][0] + rng.randint(-25, 25)
            py    = profile[idx][1] + rng.randint(-8, 10)
            kind  = rng.choice(kinds)
            angle = rng.uniform(-0.5, 0.5)
            self._heap_items.append((px, py, kind, rng.random(), angle))
        # Zemin üstü
        for _ in range(50):
            fx2  = rng.randint(20, W-20)
            fy2  = base_y - rng.randint(5, 30)
            kind = rng.choice(["box","disk","circuit","cable","barrel","pipe"])
            self._heap_items.append((fx2, fy2, kind, rng.random(), rng.uniform(-0.7,0.7)))

        self._base_y         = base_y
        self._land_y         = profile[steps//2][1]
        self._crack_cx       = W // 2
        self._crack_cy       = 130
        self._sink_surface_y = self._land_y
        self._sink_max       = 30


    def _build_crack_pts(self):
        self._crack_L = [(-6,-80),(-10,-50),(-4,-20),(-12,10),(-5,40),(-9,65),(-3,80)]
        self._crack_R = [( 6,-80),( 10,-50),( 4,-20),( 12,10),( 5,40),( 9,65),( 3,80)]

    # ── ÇİZİM YARDIMCILARI ───────────────────────────────────────────────────

    def _draw_heap(self, surf, alpha=255):
        # [PLACEHOLDER] Arkaplan çöplük haritası kaldırıldı.
        # Pixel artist buraya tileset/sahne görseli entegre eder.
        # Şimdilik: düz koyu zemin + ince horizon çizgisi.
        if alpha <= 0:
            return
        W, H    = self.W, self.H
        base_y  = self._base_y

        # Gökyüzü (düz koyu)
        sky_col = (8, 5, 18)
        if alpha >= 255:
            surf.fill(sky_col, (0, 0, W, base_y))
        else:
            sky = pygame.Surface((W, base_y), pygame.SRCALPHA)
            sky.fill((*sky_col, alpha))
            surf.blit(sky, (0, 0))

        # Zemin (düz gri-mor)
        gnd_col = (28, 20, 42)
        if alpha >= 255:
            surf.fill(gnd_col, (0, base_y, W, H - base_y))
            pygame.draw.line(surf, (55, 40, 80), (0, base_y), (W, base_y), 2)
        else:
            gnd = pygame.Surface((W, H - base_y), pygame.SRCALPHA)
            gnd.fill((*gnd_col, alpha))
            surf.blit(gnd, (0, base_y))


    def _draw_junk(self, surf, px, py, kind, seed, alpha=255, angle=0.0):
        # [PLACEHOLDER] Çöp objeleri kaldırıldı — Pixel artist sahneyi tileset ile dolduracak.
        pass

    def _draw_crack(self, surf, cx, cy, scale, gt, alpha=255):
        if scale <= 0 or alpha <= 0: return
        s = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        def pt(raw): return (int(cx+raw[0]*scale), int(cy+raw[1]*scale))
        L = [pt(p) for p in self._crack_L]
        R = [pt(p) for p in self._crack_R]

        # Chromatic aberration: magenta sol, yeşil sağ
        shift = int(5*scale*(0.5+0.5*math.sin(gt*9.1)))
        for color, dx in [
            ((*self._GLITCH_R, min(255, int(80*alpha/255))), -shift),
            ((*self._GLITCH_G, min(255, int(80*alpha/255))),  shift),
        ]:
            poly = [(p[0]+dx, p[1]) for p in L] + [(p[0]+dx, p[1]) for p in reversed(R)]
            pygame.draw.polygon(s, color, poly)

        # İçi: saf void siyah
        pygame.draw.polygon(s, (0, 0, 0, min(255, int(255*alpha/255))), L+list(reversed(R)))

        # Kenar çizgileri: soğuk mor-beyaz
        edge_col = (*self._WHITE, min(255, int(230*alpha/255)))
        if len(L) >= 2:
            pygame.draw.lines(s, edge_col, False, L, 3)
            pygame.draw.lines(s, edge_col, False, R, 3)

        # İç void parlaması: derin mor
        void_glow = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        void_w = int(14*scale)
        for ix in range(-void_w, void_w, 2):
            glow_ratio = 1.0 - abs(ix)/max(void_w,1)
            ga = int(glow_ratio * 55 * alpha/255)
            for pt2 in L:
                vx = pt2[0]+ix; vy = pt2[1]
                if 0 <= vx < self.W and 0 <= vy < self.H:
                    pygame.draw.circle(void_glow, (80, 0, 160, ga), (vx, vy), 2)
        s.blit(void_glow, (0,0))

        # Glitch yatay çizgiler (hastalıklı tarama)
        rng2 = random.Random(int(gt*25))
        for _ in range(int(8*scale)):
            gy   = int(cy + rng2.uniform(-90,90)*scale)
            gxl  = int(cx - 10*scale + rng2.randint(-4,4))
            gxr  = int(cx + 10*scale + rng2.randint(-4,4))
            gcol = rng2.choice([self._WHITE, self._GLITCH_R, self._GLITCH_G, self._VOID_PURP])
            ga2  = min(255, int(rng2.randint(60,220)*alpha/255))
            pygame.draw.line(s, (*gcol, ga2), (gxl, gy), (gxr, gy), 1)

        # Yarık uç parlama (void enerji)
        for tip_y in [cy-int(88*scale), cy+int(88*scale)]:
            pulse = 0.7 + 0.3*math.sin(gt*6.5)
            ta = min(255, int((160+80*pulse)*alpha/255))
            # Dış halka: yeşil
            pygame.draw.circle(s, (*self._GLITCH_G, ta//2), (cx,tip_y), int(18*scale))
            # İç: mor
            pygame.draw.circle(s, (*self._VOID_PURP, ta), (cx,tip_y), int(9*scale))
            # Merkez: beyaz nokta
            pygame.draw.circle(s, (*self._WHITE, ta), (cx,tip_y), int(4*scale))

        # Dal çatlaklar (scale > 0.7'den sonra çıkar)
        if scale > 0.7:
            brng = random.Random(int(gt*7 + scale*100))
            for _ in range(int(scale*6)):
                # Yarık boyunca rastgele bir noktadan dal çıkar
                base_pt = brng.choice(L+R)
                blen = brng.randint(15, int(50*scale))
                bang = brng.uniform(-math.pi*0.6, math.pi*0.6)
                bex  = base_pt[0] + int(math.cos(bang)*blen)
                bey  = base_pt[1] + int(math.sin(bang)*blen*0.5)
                bcol = brng.choice([self._WHITE, self._GLITCH_G, self._GLITCH_R])
                ba   = min(255, int(brng.randint(40,140)*alpha/255))
                pygame.draw.line(s, (*bcol, ba), base_pt, (bex, bey), 1)
                # Dal ucu küçük parlama
                pygame.draw.circle(s, (*bcol, ba//2), (bex, bey), 2)

        surf.blit(s, (0,0))

    def _draw_char(self, surf, alpha=255):
        # [PLACEHOLDER] Düşen karakter — düz dik duran dikdörtgen
        if not self._char_vis:
            return
        cx2 = int(self._char_x)
        cy2 = int(self._char_y)
        w, h = 18, 28
        a    = int(240 * alpha / 255) if alpha <= 1 else 240
        rect = pygame.Rect(cx2 - w // 2, cy2 - h // 2, w, h)
        box  = pygame.Surface((w, h), pygame.SRCALPHA)
        box.fill((220, 210, 255, int(30 * alpha / 255) if alpha <= 1 else 30))
        surf.blit(box, rect.topleft)
        pygame.draw.rect(surf, (*self._WHITE, int(230 * alpha / 255) if alpha <= 1 else 230), rect, 2)

    def _draw_tb(self, surf, tb, y_pos=None):
        bw, bh = self.W-80, 110
        bx = 40
        by = (self.H-bh-30) if y_pos is None else y_pos
        bg = pygame.Surface((bw,bh),pygame.SRCALPHA); bg.fill((0,0,0,210))
        surf.blit(bg,(bx,by))
        pygame.draw.rect(surf,self._WHITE,(bx,by,bw,bh),2)
        chars_left = int(tb["idx"])
        for i,line in enumerate(tb["lines"]):
            if chars_left<=0: break
            show = line[:chars_left]
            chars_left -= len(line)+1
            txt = self.font_main.render(show,True,self._WHITE)
            surf.blit(txt,(bx+18,by+14+i*30))
        if tb["done"] and int(tb["cursor"]*2)%2==0:
            arr = self.font_small.render("▼",True,self._WHITE)
            surf.blit(arr,(bx+bw-28,by+bh-24))

    def _fade(self, alpha):
        s = pygame.Surface((self.W,self.H)); s.fill(self._BLACK); s.set_alpha(int(alpha)); return s

    def _update_tb(self, tb, dt):
        total = sum(len(l) for l in tb["lines"])+len(tb["lines"])-1
        if tb["idx"] < total: tb["idx"] += dt*tb["speed"]
        else: tb["done"] = True
        tb["cursor"] += dt

    # ── ANA DÖNGÜ ─────────────────────────────────────────────────────────────

    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(60)/1000.0, 0.05)
            space = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: return True
                    if event.key in (pygame.K_SPACE,pygame.K_z,pygame.K_RETURN): space=True

            name, dur = self._scenes[self._scene_idx]
            self._scene_t += dt

            # Metin kutusu güncelle
            if name in self._textboxes:
                self._update_tb(self._textboxes[name], dt)
                if space and self._textboxes[name]["done"]:
                    self._next_scene()

            # Otomatik geçiş
            if dur and self._scene_t >= dur:
                self._next_scene()

            # FALL: karakter
            if name == "FALL":
                if self._scene_t < 0.05 and not self._char_vis:
                    self._char_x   = float(self._crack_cx)
                    self._char_y   = float(self._crack_cy + 60)
                    self._char_vy  = 80.0
                    self._char_vx  = random.uniform(-15,15)
                    self._char_vis = True
                    self._char_trail = []
                self._update_char(dt)
                if self._char_landed:
                    for _ in range(70):
                        self._particles.append(self._new_particle(self._char_x, self._char_y+self._CRADIUS))
                    self._shake_time = 0.45
                    self._next_scene()

            if name in ("IMPACT","SETTLE"):
                self._update_settle(dt)
                if self._shake_time > 0:
                    self._shake_time -= dt
                    amp = int(8*self._shake_time/0.45)
                    self._shake = (random.randint(-amp,amp),random.randint(-amp,amp))
                else:
                    self._shake = (0,0)

            # Parçacıklar
            self._particles = [p for p in self._particles if p["life"]>0]
            for p in self._particles:
                p["vy"] += 300*dt; p["x"]+=p["vx"]*dt; p["y"]+=p["vy"]*dt; p["life"]-=dt

            # Son sahne bitti + space
            if name == "SETTLE" and self._textboxes["SETTLE"]["done"] and space:
                return True

            self._draw_scene(name)
        return True

    def _next_scene(self):
        if self._scene_idx < len(self._scenes)-1:
            self._scene_idx += 1
            self._scene_t = 0.0

    def _update_char(self, dt):
        if not self._char_vis or self._char_landed: return
        self._char_vy += 420*dt
        self._char_x  += self._char_vx*dt
        self._char_y  += self._char_vy*dt
        self._char_trail.append((self._char_x,self._char_y))
        if len(self._char_trail)>18: self._char_trail.pop(0)
        if self._char_y >= self._land_y - self._CRADIUS:
            self._char_y    = float(self._land_y - self._CRADIUS)
            self._char_landed = True; self._char_vy = 0; self._char_vx = 0
            self._char_wobble = 1.0; self._char_squash = 0.55
            self._sink_depth  = 0.0

    def _update_settle(self, dt):
        self._char_wobble = max(0.0, self._char_wobble - dt*2.2)
        if self._char_squash < 1.0:
            self._char_squash = min(1.0, self._char_squash + dt*3.5)
        # Batma: karakterin Y'si yavaşça _sink_max kadar içeri kayar
        if self._sink_depth < self._sink_max:
            self._sink_depth = min(self._sink_max, self._sink_depth + dt * 18.0)
            self._char_y = self._land_y - self._CRADIUS + self._sink_depth * 0.7

    def _new_particle(self, x, y):
        ang = random.uniform(math.pi*1.05, math.pi*1.95)
        spd = random.uniform(80, 280)
        ptype = random.choice(["char","char","char","chunk","spark"])
        return {"x":float(x),"y":float(y),
                "vx":math.cos(ang)*spd, "vy":math.sin(ang)*spd - random.uniform(0,60),
                "life":random.uniform(0.5,1.6), "maxl":1.0,
                "char":random.choice(["#","0","1","X","!","?","%"]),
                "type":ptype,
                "size":random.randint(3,9) if ptype=="chunk" else 1}

    def _draw_particles(self, surf):
        try: f = pygame.font.SysFont("consolas", 14)
        except: f = self.font_small
        for p in self._particles:
            ratio  = p["life"] / max(0.01, p.get("maxl", 1.0))
            alpha  = max(0, min(255, int(220 * ratio)))   # CLAMP 0-255
            ptype  = p.get("type", "char")
            if ptype == "chunk":
                sz = p.get("size", 4)
                cs = pygame.Surface((sz*2+2, sz*2+2), pygame.SRCALPHA)
                pygame.draw.rect(cs, (*self._JUNK_EDGE, alpha), (0, 0, sz*2, sz*2), 1)
                surf.blit(cs, (int(p["x"])-sz, int(p["y"])-sz))
            elif ptype == "spark":
                end_x = int(p["x"] - p["vx"] * 0.03)
                end_y = int(p["y"] - p["vy"] * 0.03)
                x0, y0 = int(p["x"]), int(p["y"])
                sw = max(abs(x0 - end_x) + 4, 2)
                sh = max(abs(y0 - end_y) + 4, 2)
                ss = pygame.Surface((sw, sh), pygame.SRCALPHA)
                ox2 = min(x0, end_x)
                oy2 = min(y0, end_y)
                # Yeşil/mor spark
                scol = self._GLITCH_G if int(p["x"]*7)%2==0 else self._GLITCH_R
                pygame.draw.line(ss, (*scol, alpha),
                                 (x0-ox2, y0-oy2), (end_x-ox2, end_y-oy2), 1)
                surf.blit(ss, (ox2, oy2))
            else:
                # Char: mor veya yeşil tint
                tcol = self._GLITCH_G if int(p["x"]+p["y"])%3==0 else self._DIM_WHITE
                c = f.render(p["char"], True, tcol)
                c.set_alpha(alpha)
                surf.blit(c, (int(p["x"]), int(p["y"])))

    def _draw_scene(self, name):
        self.screen.fill(self._SKY_COL)
        t  = self._scene_t
        ox, oy = self._shake
        gt = pygame.time.get_ticks() / 1000.0

        def draw_scanlines(intensity=1.0):
            sl = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            for sy in range(0, self.H, 4):
                pygame.draw.line(sl, (0,0,0, int(35*intensity)), (0,sy), (self.W,sy))
            self.screen.blit(sl, (0,0))

        def draw_glitch_bands(num=3, max_alpha=40):
            for _ in range(num):
                gy  = random.randint(0, self.H)
                gh  = random.randint(2, 14)
                ga  = random.randint(8, max_alpha)
                gcol= random.choice([self._GLITCH_R, self._GLITCH_G, self._VOID_PURP])
                gs  = pygame.Surface((self.W, gh), pygame.SRCALPHA)
                gs.fill((*gcol, ga))
                self.screen.blit(gs, (0, gy))

        def draw_vignette(r_tint=0, g_tint=0, b_tint=0, strength=180):
            v = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            for vx in range(0, self.W, 8):
                edge_d = min(vx, self.W-vx) / max(self.W*0.35, 1)
                va = max(0, int(strength*(1-min(edge_d,1.0))))
                if va > 0:
                    pygame.draw.line(v, (r_tint,g_tint,b_tint,va),(vx,0),(vx,self.H))
            for vy2 in range(0, self.H, 8):
                edge_d = min(vy2, self.H-vy2) / max(self.H*0.35, 1)
                va = max(0, int(strength*(1-min(edge_d,1.0))))
                if va > 0:
                    pygame.draw.line(v, (r_tint,g_tint,b_tint,va),(0,vy2),(self.W,vy2))
            self.screen.blit(v,(0,0))

        def draw_void_particles(count=25, col=None):
            rng3 = random.Random(int(gt*4))
            for _ in range(count):
                vx3 = rng3.randint(0, self.W)
                vy3 = int((rng3.randint(0, self.H) + gt*18) % self.H)
                va3 = rng3.randint(6, 35)
                vc3 = col if col else rng3.choice([self._GLITCH_G, self._VOID_PURP, self._DIM_WHITE])
                vs3 = pygame.Surface((3,3), pygame.SRCALPHA)
                vs3.fill((*vc3, va3))
                self.screen.blit(vs3, (vx3, vy3))

        if name == "DARK":
            self.screen.fill(self._BLACK)
            if t > 0.5:
                draw_void_particles(15, self._VOID_PURP)
            draw_glitch_bands(1, 15)

        elif name in ("TEXT_1","TEXT_2","TEXT_3","TEXT_4","TEXT_5"):
            self.screen.fill(self._BLACK)
            scene_num = ["TEXT_1","TEXT_2","TEXT_3","TEXT_4","TEXT_5"].index(name)
            draw_void_particles(12 + scene_num*8)
            rng_bg = random.Random(int(gt * 2))
            for _ in range(6 + scene_num*3):
                lx = rng_bg.randint(0, self.W)
                ly = rng_bg.randint(0, self.H)
                lw = rng_bg.randint(20, self.W//2)
                la = rng_bg.randint(4, 18)
                ls = pygame.Surface((lw, 1), pygame.SRCALPHA)
                lcol = rng_bg.choice([self._JUNK_EDGE, self._VOID_PURP, self._SICK_GREEN])
                ls.fill((*lcol, la))
                self.screen.blit(ls, (lx, ly))
            if scene_num >= 2:
                for _ in range(scene_num * 15):
                    sx2 = random.randint(0, self.W)
                    sy2 = random.randint(0, self.H)
                    sa  = random.randint(5, 25)
                    sc2 = random.choice([self._GLITCH_G, self._VOID_PURP])
                    snp = pygame.Surface((2,2), pygame.SRCALPHA)
                    snp.fill((*sc2, sa))
                    self.screen.blit(snp, (sx2, sy2))
            if name in ("TEXT_4","TEXT_5"):
                pulse = 0.4 + 0.6*abs(math.sin(gt*1.8))
                danger_a = int(pulse * 45)
                ds = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
                ds.fill((*self._VOID_PURP, danger_a))
                self.screen.blit(ds, (0,0))
                draw_glitch_bands(4, 30)
            y_pos = None
            if name == "TEXT_5":
                y_pos = self.H//2 - 60
            self._draw_tb(self.screen, self._textboxes[name], y_pos)
            draw_scanlines(0.6)
            draw_vignette(0, 0, 20, 120)

        elif name == "REVEAL":
            fa = min(255, int(t / 2.8 * 255))
            self._draw_heap(self.screen, fa)
            draw_void_particles(20)
            draw_glitch_bands(2, 25)
            fog_h = max(0, int(self.H * 0.4 * (1 - t/2.8)))
            if fog_h > 0:
                fog = pygame.Surface((self.W, fog_h), pygame.SRCALPHA)
                for fy3 in range(fog_h):
                    fa3 = int((1 - fy3/max(fog_h,1)) * 200)
                    pygame.draw.line(fog, (0,0,0,fa3), (0,fy3),(self.W,fy3))
                self.screen.blit(fog, (0,0))
            draw_scanlines(0.8)
            draw_vignette(10, 0, 20, 100)
            if fa < 255:
                self.screen.blit(self._fade(255-fa),(0,0))

        elif name == "CRACK_APPEAR":
            self._draw_heap(self.screen)
            draw_void_particles(30)
            cs = min(1.0, t/1.4)
            ca = min(255, int(t/0.5*255))
            spark_surf = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            for _ in range(int(t*12)):
                ang2  = random.uniform(0, math.pi*2)
                dist2 = random.uniform(40, 140-t*50)
                ex3   = int(self._crack_cx + math.cos(ang2)*dist2)
                ey3   = int(self._crack_cy + math.sin(ang2)*dist2*0.55)
                ex4   = int(self._crack_cx + math.cos(ang2)*dist2*0.5)
                ey4   = int(self._crack_cy + math.sin(ang2)*dist2*0.5*0.55)
                sa2   = random.randint(50, 160)
                sc3   = random.choice([self._GLITCH_G, self._VOID_PURP, self._WHITE])
                pygame.draw.line(spark_surf, (*sc3, sa2), (ex3,ey3), (ex4,ey4), 1)
            self.screen.blit(spark_surf, (0,0))
            halo = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            halo_r = int(60 + 30*math.sin(gt*8))
            halo_a = int(cs * 40)
            pygame.draw.circle(halo, (*self._VOID_PURP, halo_a),
                               (self._crack_cx, self._crack_cy), halo_r)
            self.screen.blit(halo, (0,0))
            self._draw_crack(self.screen, self._crack_cx+ox, self._crack_cy+oy, cs, gt, ca)
            draw_scanlines(1.0)
            draw_glitch_bands(3, 40)
            draw_vignette(15, 0, 30, 140)
            if t < 0.35:
                self.screen.blit(self._fade(int(255*(1-t/0.35))),(0,0))

        elif name == "CRACK_GROW":
            self._draw_heap(self.screen)
            cs = 1.0 + t*0.28
            draw_void_particles(40, self._GLITCH_G)
            spark_surf2 = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            if int(gt*14)%2==0:
                for _ in range(8):
                    lx2  = self._crack_cx + random.randint(-100,100)
                    ly2  = self._crack_cy + random.randint(-130,130)
                    le_x = lx2 + random.randint(-50,50)
                    le_y = ly2 + random.randint(-15,15)
                    sca2 = random.randint(30,120)
                    scc2 = random.choice([self._GLITCH_G, self._WHITE, self._GLITCH_R])
                    pygame.draw.line(spark_surf2, (*scc2, sca2),
                                     (lx2+ox, ly2+oy), (le_x+ox, le_y+oy), 1)
            self.screen.blit(spark_surf2, (0,0))
            halo2 = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            for hr2 in range(3, 0, -1):
                hrad = int((cs*80) * hr2/3 + 15*math.sin(gt*5))
                ha2  = int(30/hr2)
                pygame.draw.circle(halo2, (*self._VOID_PURP, ha2),
                                   (self._crack_cx+ox, self._crack_cy+oy), hrad, 3)
                pygame.draw.circle(halo2, (*self._GLITCH_G, ha2//2),
                                   (self._crack_cx+ox, self._crack_cy+oy), hrad+8, 1)
            self.screen.blit(halo2, (0,0))
            self._draw_crack(self.screen, self._crack_cx+ox, self._crack_cy+oy, cs, gt, 255)
            draw_scanlines(1.2)
            draw_glitch_bands(6, 60)
            draw_vignette(20, 0, 40, 160)

        elif name == "FALL":
            self._draw_heap(self.screen)
            self._draw_crack(self.screen, self._crack_cx+ox, self._crack_cy+oy, 1.28, gt, 255)
            if len(self._char_trail) > 2:
                trail_surf = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
                for i,(tx,ty) in enumerate(self._char_trail):
                    ratio2 = i/max(1,len(self._char_trail))
                    ta2    = int(ratio2*80)
                    tc2    = self._GLITCH_G if i%2==0 else self._VOID_PURP
                    pygame.draw.circle(trail_surf, (*tc2, ta2), (int(tx),int(ty)), 3)
                self.screen.blit(trail_surf, (0,0))
            self._draw_char(self.screen)
            self._draw_particles(self.screen)
            draw_scanlines(1.0)
            draw_glitch_bands(2, 30)

        elif name in ("IMPACT","SETTLE"):
            self._draw_heap(self.screen)
            if name == "IMPACT":
                cs2 = max(0.0, 1.28-t*0.5)
                if cs2 > 0:
                    self._draw_crack(self.screen, self._crack_cx+ox, self._crack_cy+oy,
                                     cs2, gt, int(255*cs2/1.28))
                if t < 0.22:
                    flash_a = int((1-t/0.22)*180)
                    fs = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
                    fs.fill((*self._WHITE, flash_a))
                    self.screen.blit(fs, (0,0))
                ring_r = int(t * 400)
                if ring_r < self.W:
                    rs2 = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
                    ring_a2 = max(0, int((1-t/0.5)*120))
                    pygame.draw.circle(rs2, (*self._GLITCH_G, ring_a2),
                                       (int(self._char_x), int(self._char_y)+self._CRADIUS),
                                       ring_r, 3)
                    pygame.draw.circle(rs2, (*self._VOID_PURP, ring_a2//2),
                                       (int(self._char_x), int(self._char_y)+self._CRADIUS),
                                       ring_r+10, 1)
                    self.screen.blit(rs2, (0,0))
            self._draw_particles(self.screen)
            self._draw_char(self.screen)
            draw_void_particles(20)
            if name == "SETTLE":
                aura_a = max(0, int(50 - t*8))
                if aura_a > 0:
                    as2 = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
                    for ar in range(40, 10, -8):
                        pygame.draw.circle(as2, (*self._VOID_PURP, aura_a//4),
                                           (int(self._char_x), int(self._char_y)), ar+30)
                    self.screen.blit(as2, (0,0))
                self._draw_tb(self.screen, self._textboxes["SETTLE"])
            draw_scanlines(0.8)
            draw_glitch_bands(3, 35)
            draw_vignette(10, 0, 25, 130)

        if name == "DARK" and t < 0.7:
            self.screen.blit(self._fade(int(255*(1-t/0.7))),(0,0))
        if name == "TEXT_1" and t < 0.4:
            self.screen.blit(self._fade(int(255*(1-t/0.4))),(0,0))
        if name in ("TEXT_2","TEXT_3","TEXT_4","TEXT_5") and t < 0.3:
            self.screen.blit(self._fade(int(255*(1-t/0.3))),(0,0))
        if name == "REVEAL" and t < 0.4:
            self.screen.blit(self._fade(int(255*(1-t/0.4))),(0,0))

        pygame.display.flip()