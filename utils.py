import pygame
import random
import math
import numpy as np
import os

# ─── MERKEZI ASSET ÖNBELLEĞİ ────────────────────────────────────────────────
# Aynı resmi defalarca diskten yüklemekten kaçınmak için global sözlük.
# Kullanım: img = get_image("assets/sprites/player.png")
ASSET_CACHE: dict = {}

def get_image(path: str) -> pygame.Surface:
    """
    Resmi diskten yükler ve önbelleğe alır.
    İkinci çağrıda aynı nesneyi döndürür — disk I/O yoktur.
    convert_alpha() ile VRAM'e uygun formata çevrilir (FPS kritik).
    Dosya bulunamazsa 1×1 şeffaf yüzey döndürür (kırılmaz fallback).
    """
    if path not in ASSET_CACHE:
        if os.path.exists(path):
            try:
                ASSET_CACHE[path] = pygame.image.load(path).convert_alpha()
            except Exception as e:
                print(f"[get_image] Yüklenemedi: {path} — {e}")
                surf = pygame.Surface((1, 1), pygame.SRCALPHA)
                surf.fill((0, 0, 0, 0))
                ASSET_CACHE[path] = surf
        else:
            surf = pygame.Surface((1, 1), pygame.SRCALPHA)
            surf.fill((0, 0, 0, 0))
            ASSET_CACHE[path] = surf
    return ASSET_CACHE[path]


def clear_asset_cache():
    """Bellek baskısı varsa önbelleği boşalt (bölüm geçişlerinde çağrılabilir)."""
    ASSET_CACHE.clear()


# ─── SPRITE SHEET İŞLEYİCİ ───────────────────────────────────────────────────
class SpriteSheet:
    """
    Tek bir sprite sheet PNG dosyasından dikdörtgen kareler keser.

    Kullanım örneği:
        sheet = SpriteSheet("assets/sprites/player_sheet.png")
        idle_frame_0 = sheet.get_image(0, 0, 32, 48)          # x, y, w, h
        run_frame_1  = sheet.get_image(32, 0, 32, 48, scale=2) # 2× büyütme
    """
    def __init__(self, filename: str):
        # convert_alpha() — şeffaflık + GPU uyumluluğu için zorunlu
        self.sheet = pygame.image.load(filename).convert_alpha()
        self._cache: dict = {}

    def get_image(self, x: int, y: int, width: int, height: int,
                  scale: float = 1.0) -> pygame.Surface:
        """
        Sheet'ten (x, y, width, height) dikdörtgenini keser.
        scale > 1 büyütür, scale < 1 küçültür.
        Sonuç iç önbellekte tutulur.
        """
        key = (x, y, width, height, scale)
        if key not in self._cache:
            image = pygame.Surface((width, height), pygame.SRCALPHA)
            image.blit(sheet, (0, 0), (x, y, width, height))
            if scale != 1.0:
                new_w = max(1, int(width  * scale))
                new_h = max(1, int(height * scale))
                image = pygame.transform.scale(image, (new_w, new_h))
            self._cache[key] = image
        return self._cache[key]

    def get_row(self, row: int, frame_count: int,
                frame_w: int, frame_h: int,
                scale: float = 1.0) -> list:
        """
        Sheet'teki tek bir satırı (row) eşit genişlikli kareler olarak döndürür.
        Animasyon kareleri için kısa yol.
        """
        return [
            self.get_image(i * frame_w, row * frame_h, frame_w, frame_h, scale)
            for i in range(frame_count)
        ]


# ─── BASIT ANİMASYON KONTROLCÜSÜ ─────────────────────────────────────────────
class FrameAnimator:
    """
    Belirtilen kare listesini belirli bir hızda döngüsel oynatır.

    Kullanım:
        animator = FrameAnimator(frames=sheet.get_row(0, 4, 32, 48), fps=10)
        # oyun döngüsünde:
        animator.update(dt)
        current_surface = animator.get_frame()
    """
    def __init__(self, frames: list, fps: float = 10.0, loop: bool = True):
        self.frames     = frames if frames else []
        self.fps        = max(1.0, fps)
        self.loop       = loop
        self._timer     = 0.0
        self._idx       = 0
        self._finished  = False

    @property
    def frame_duration(self) -> float:
        return 1.0 / self.fps

    def update(self, dt: float):
        if self._finished or not self.frames:
            return
        self._timer += dt
        while self._timer >= self.frame_duration:
            self._timer -= self.frame_duration
            self._idx   += 1
            if self._idx >= len(self.frames):
                if self.loop:
                    self._idx = 0
                else:
                    self._idx      = len(self.frames) - 1
                    self._finished = True
                    break

    def get_frame(self) -> pygame.Surface | None:
        """Mevcut kareyi döndürür. Kare yoksa None."""
        if not self.frames:
            return None
        return self.frames[self._idx]

    def reset(self):
        self._timer    = 0.0
        self._idx      = 0
        self._finished = False

    @property
    def finished(self) -> bool:
        return self._finished

# --- GELİŞMİŞ SES YÖNETİCİSİ ---
class AudioManager:
    def __init__(self):
        try:
            pygame.mixer.init(44100, -16, 2, 512)
            pygame.mixer.set_num_channels(32)
        except:
            print("Ses kartı başlatılamadı.")

        self.music_channel = pygame.mixer.Channel(0)

        self.master_vol = 1.0
        self.music_vol = 0.5
        self.sfx_vol = 0.8

    def update_settings(self, settings_dict):
        self.master_vol = settings_dict.get("sound_volume", 1.0)
        self.music_vol = settings_dict.get("music_volume", 0.5)
        self.sfx_vol = settings_dict.get("effects_volume", 0.8)
        self._apply_volumes()

    def _apply_volumes(self):
        final_music_vol = self.master_vol * self.music_vol
        self.music_channel.set_volume(final_music_vol)

    def play_music(self, sound_obj, loops=-1):
        if not sound_obj: return
        if self.music_channel.get_busy():
            self.music_channel.stop()
        self.music_channel.play(sound_obj, loops=loops)
        self._apply_volumes()

    def play_sfx(self, sound_obj):
        if not sound_obj: return
        channel = pygame.mixer.find_channel(True)
        if channel:
            if channel == self.music_channel:
                channel = pygame.mixer.find_channel(True)
            final_sfx_vol = self.master_vol * self.sfx_vol
            channel.set_volume(final_sfx_vol)
            channel.play(sound_obj)

    def stop_music(self):
        self.music_channel.stop()

    def pause_all(self):
        pygame.mixer.pause()

    def unpause_all(self):
        pygame.mixer.unpause()

# Global Instance
audio_manager = AudioManager()


# --- SES ÜRETİM FONKSİYONLARI (DEĞİŞMEDİ) ---

def generate_sound_effect(base_freq, duration, volume=1.0):
    try:
        sample_rate = 44100
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = np.sin(2 * np.pi * base_freq * t)
        envelope = np.ones_like(t)
        attack_len = int(sample_rate * 0.01)
        decay_len = int(sample_rate * (duration * 0.8))
        if attack_len > 0:
            envelope[:attack_len] = np.linspace(0, 1, attack_len)
        if decay_len > 0:
            envelope[-decay_len:] = np.linspace(1, 0, decay_len)
        wave = wave * envelope
        if base_freq > 100:
            harmonic_1 = 0.3 * np.sin(2 * np.pi * base_freq * 2 * t)
            harmonic_2 = 0.15 * np.sin(2 * np.pi * base_freq * 0.5 * t)
            wave = wave + harmonic_1 + harmonic_2
        wave = wave / np.max(np.abs(wave)) if np.max(np.abs(wave)) > 0 else wave
        wave = (wave * 32767).astype(np.int16)
        wave = np.repeat(wave.reshape(-1, 1), 2, axis=1)
        sound = pygame.sndarray.make_sound(wave)
        return sound
    except Exception as e:
        return get_silent_sound()

def generate_ambient_fallback():
    try:
        sample_rate = 44100
        duration = 10.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        drone = 0.5 * np.sin(2 * np.pi * 55.0 * t)
        envelope = np.ones_like(t)
        fade = int(sample_rate * 2.0)
        if fade > 0:
            envelope[:fade] = np.linspace(0, 1, fade)
            envelope[-fade:] = np.linspace(1, 0, fade)
        wave = drone * envelope
        wave = (wave * 32767 * 0.3).astype(np.int16)
        wave = np.repeat(wave.reshape(-1, 1), 2, axis=1)
        return pygame.sndarray.make_sound(wave)
    except Exception:
        return get_silent_sound()

def generate_calm_ambient():
    try:
        sample_rate = 44100
        duration = 15.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = 0.3 * np.sin(2 * np.pi * 110.0 * t)
        wave += 0.2 * np.sin(2 * np.pi * 165.0 * t)
        envelope = np.ones_like(t)
        fade = int(sample_rate * 3.0)
        if fade > 0:
            envelope[:fade] = np.linspace(0, 1, fade)
            envelope[-fade:] = np.linspace(1, 0, fade)
        wave = wave * envelope
        wave = (wave * 32767 * 0.25).astype(np.int16)
        wave = np.repeat(wave.reshape(-1, 1), 2, axis=1)
        return pygame.sndarray.make_sound(wave)
    except:
        return generate_ambient_fallback()

def get_silent_sound():
    try:
        buffer = bytearray([0] * 200)
        return pygame.mixer.Sound(buffer=buffer)
    except:
        class MockSound:
            def play(self, *args, **kwargs): pass
            def set_volume(self, v): pass
            def stop(self): pass
        return MockSound()

def load_sound_asset(filepath, fallback_generator=None, volume=1.0):
    if not os.path.exists(filepath):
        if fallback_generator: return fallback_generator()
        return get_silent_sound()
    try:
        return pygame.mixer.Sound(filepath)
    except Exception:
        if fallback_generator: return fallback_generator()
        return get_silent_sound()


# --- ÇİZİM FONKSİYONLARI ---

def draw_text(surface, text, color, rect, font_size, aa=False, bkg=None):
    try:
        font = pygame.font.Font(None, font_size)
        text_surface = font.render(text, aa, color, bkg)
        text_rect = text_surface.get_rect()
        text_rect.center = (rect[0] + rect[2] // 2, rect[1] + rect[3] // 2)
        surface.blit(text_surface, text_rect)
    except:
        pygame.draw.rect(surface, color, rect, 1)

def draw_text_with_shadow(surface, text, font, pos, color, shadow_color=(0, 0, 0), offset=(2, 2), align='topleft'):
    try:
        text_surf = font.render(text, True, color)
        shadow_surf = font.render(text, True, shadow_color)
        text_rect = text_surf.get_rect()
        shadow_rect = shadow_surf.get_rect()
        if hasattr(text_rect, align):
            setattr(text_rect, align, pos)
            shadow_pos = (getattr(text_rect, align)[0] + offset[0],
                          getattr(text_rect, align)[1] + offset[1])
            setattr(shadow_rect, align, shadow_pos)
        else:
            text_rect.topleft = pos
            shadow_rect.topleft = (pos[0] + offset[0], pos[1] + offset[1])
        surface.blit(shadow_surf, shadow_rect)
        surface.blit(text_surf, text_rect)
    except Exception as e:
        print(f"Shadow text error: {e}")

def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        w, h = font.size(test_line)
        if w < max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    lines.append(' '.join(current_line))
    return lines


def draw_animated_player(surface, shape, x, y, size, color, anim_params):
    """
    PLACEHOLDER: Oyuncu şu an düz dikdörtgen olarak çiziliyor.
    [TODO - PIXEL ART]: Bu fonksiyon, sprite sheet'ten animasyon karesi
    çizen bir versiyonla değiştirilecek.
    
    Pixel artistler için boyut referansı:
      - Genişlik: size * 2  (varsayılan ~30px)
      - Yükseklik: size * 2.5 (dik duran, boylu karakter)
    """
    shake_offset = anim_params.get('shake_offset', (0, 0))
    draw_x = int(x + shake_offset[0])
    draw_y = int(y + shake_offset[1])

    # Karakter gövdesi — dik duran dikdörtgen
    char_w = size * 2
    char_h = int(size * 2.5)
    body_rect = pygame.Rect(draw_x - size, draw_y - char_h, char_w, char_h)
    pygame.draw.rect(surface, color, body_rect)

    # Yön göstergesi — üst kısımda küçük bir işaret (kafa yönü)
    head_rect = pygame.Rect(draw_x - size // 2, draw_y - char_h - size // 2, size, size // 2)
    pygame.draw.rect(surface, color, head_rect)

    # [DEBUG] Şekil adını küçük yazı ile göster (geliştirme aşamasında faydalı)
    # Üretimde kapatmak için bu bloğu yorum satırına al:
    # debug_font = pygame.font.Font(None, 16)
    # debug_surf = debug_font.render(shape[0].upper(), True, (0, 0, 0))
    # surface.blit(debug_surf, (body_rect.x + 2, body_rect.y + 2))


def lerp(start, end, t):
    return start + (end - start) * t

def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))