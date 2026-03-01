import pygame
import json
import re
import math
import random
import warnings
from settings import *  # <--- BU SATIR ÇOK ÖNEMLİ, UNUTMA!

# Gemini AI entegrasyonu için import
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    print("UYARI: google.generativeai kütüphanesi yüklü değil. AI özellikleri devre dışı.")

# Google Generative AI uyarısını gizle
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

class StoryManager:
    def __init__(self):
        self.current_text = ""
        self.display_text = ""
        self.char_index = 0.0
        self.state = "IDLE"  # TYPING, WAITING_INPUT, THINKING, FINISHED
        self.speaker = ""
        self.text_speed = 0.5
        self.waiting_for_click = False
        self.is_cutscene = False
        
        # AI Özellikleri
        self.ai_active = False
        self.chat_session = None
        self.model = None
        self.ai_thinking = False
        self.conversation_history = []
        
        # Bölüm sistemi
        self.current_chapter = 1
        self.dialogue_index = 0
        self.chapter_data = None
        self.dialogue_queue = []
        
        # Oyun manipülasyonu için flagler
        self.world_modifiers = {
            "gravity_mult": 1.0,
            "speed_mult": 1.0,
            "glitch_mode": False
        }
        
        # AI bağlantısını kur
        self.setup_ai()

    def setup_ai(self):
        """Gemini API Bağlantısını Kurar"""
        if not HAS_GENAI:
            self.ai_active = False
            return
        
        if not GENAI_API_KEY or GENAI_API_KEY == "BURAYA_GEMINI_API_KEY_YAZILACAK":
            print("UYARI: API Key girilmemiş! AI çalışmayacak.")
            self.ai_active = False
            return

        try:
            genai.configure(api_key=GENAI_API_KEY)
            self.model = genai.GenerativeModel(
                AI_MODEL_NAME,
                system_instruction=FRAGMENTIA_SYSTEM_PROMPT
            )
            # Vasi sohbeti için oturum başlat
            self.chat_session = self.model.start_chat(history=[])
            self.ai_active = True
            print("FRAGMENTIA VASI PROTOKOLÜ: AKTİF")
        except Exception as e:
            print(f"AI Bağlantı Hatası: {e}")
            self.ai_active = False

    def load_chapter(self, chapter_id):
        """Yeni bir bölüm yükler"""
        self.current_chapter = chapter_id
        self.chapter_data = STORY_CHAPTERS.get(chapter_id, None)
        self.dialogue_queue = []

        if self.chapter_data:
            for line in self.chapter_data['dialogues']:
                self.dialogue_queue.append(line)
            self.next_line()

    def next_line(self):
        """Sıradaki diyalog satırını yükler"""
        if self.dialogue_queue:
            data = self.dialogue_queue.pop(0)
            self.speaker = data['speaker']
            self.current_text = data['text']
            self.is_cutscene = data.get('type', 'chat') == 'cutscene'
            self.display_text = ""
            self.char_index = 0.0
            self.state = "TYPING"
            self.waiting_for_click = False
        else:
            self.state = "FINISHED"

    def set_dialogue(self, speaker, text, is_cutscene=False):
        """Doğrudan diyalog ayarlar"""
        self.speaker = speaker
        self.current_text = text
        self.display_text = ""
        self.char_index = 0
        self.state = "TYPING"
        self.waiting_for_click = False
        self.is_cutscene = is_cutscene

    def send_ai_message(self, user_text, game_context=None):
        """Oyuncunun mesajını AI'ya gönderir (Ana Hikaye/Vasi İçin)"""
        if not self.ai_active or not self.chat_session:
            self.speaker = "SİSTEM"
            self.current_text = "BAĞLANTI HATASI: Vasi'ye ulaşılamıyor (API Key veya Bağlantı Sorunu)."
            self.state = "TYPING"
            self.char_index = 0
            return

        # Bağlamı ekle
        context_str = ""
        if game_context:
            context_str = f"[SİSTEM VERİSİ: Oyuncu Skoru: {int(game_context.get('score',0))}, Ölüm Sayısı: {game_context.get('deaths',0)}]. "

        full_prompt = context_str + user_text

        self.ai_thinking = True
        self.speaker = "VASI"
        self.current_text = "Analiz ediliyor..."
        self.display_text = "Analiz ediliyor..."
        self.state = "THINKING"

        try:
            response = self.chat_session.send_message(full_prompt)
            raw_text = response.text

            # JSON Komutlarını Ayıkla
            clean_text, commands = self.extract_commands(raw_text)

            # Komutları Uygula
            if commands:
                self.apply_world_modifiers(commands)

            self.current_text = clean_text
            self.char_index = 0
            self.state = "TYPING"
            self.ai_thinking = False

        except Exception as e:
            self.current_text = f"SİSTEM HATASI: {str(e)}"
            self.state = "TYPING"
            self.ai_thinking = False

    def generate_npc_response(self, npc, user_text, history):
        """
        Belirli bir NPC için anlık AI yanıtı oluşturur.
        Bu fonksiyon stateless çalışır (her seferinde bağlamı yeniden verir),
        böylece her NPC'nin kendi oturumu varmış gibi davranır.
        """
        if not self.ai_active:
             return "AI Sistemi çevrimdışı. Lütfen ayarlarınızı kontrol edin."
        
        # Sohbet geçmişini metne dök (Son 5 mesaj)
        history_text = ""
        for msg in history[-5:]: 
            history_text += f"{msg['speaker']}: {msg['text']}\n"
            
        # NPC'ye özel sistem promptu
        system_prompt = f"""
        Rol Yapma Oyunu Modu:
        Senin Adın: {npc.name}
        Kişilik Tipin: {npc.personality_type}
        Görevin/Rolün: "{npc.prompt}"
        
        Bulunduğun Evren: Fragmentia (Siberpunk, distopik bir dijital dünya).
        
        Kural: Oyuncu ile konuşuyorsun. Rolünün dışına ASLA çıkma. 
        Kısa, öz ve karakterine uygun cevaplar ver (Maksimum 2-3 cümle).
        
        Şu ana kadar konuşulanlar:
        {history_text}
        
        Oyuncu son olarak dedi ki: "{user_text}"
        
        {npc.name} olarak cevabın:
        """
        
        try:
             # GenerativeModel kullanarak tek seferlik içerik üretimi
             response = self.model.generate_content(system_prompt)
             return response.text.strip()
        except Exception as e:
             return f"Nöral Ağ Hatası: {str(e)}"

    def extract_commands(self, text):
        """Metin içindeki JSON bloklarını bulur ve ayırır"""
        commands = {}
        # Markdown code block içindeki JSON'ı bulmaya çalış
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        clean_text = text

        if json_match:
            json_str = json_match.group(1)
            try:
                commands = json.loads(json_str)
                # JSON kısmını metinden çıkar, oyuncu görmesin
                clean_text = text.replace(json_match.group(0), "").strip()
            except:
                pass
        else:
            # Düz JSON arama
            json_match = re.search(r'(\{.*\})', text, re.DOTALL)
            if json_match:
                try:
                    commands = json.loads(json_match.group(1))
                    clean_text = text.replace(json_match.group(0), "").strip()
                except:
                    pass

        return clean_text, commands

    def apply_world_modifiers(self, commands):
        """AI'dan gelen emirlere göre fizik kurallarını güncelle"""
        print(f"VASI DÜNYAYI DEĞİŞTİRİYOR: {commands}")

        if "gravity" in commands:
            self.world_modifiers["gravity_mult"] = float(commands["gravity"])

        if "speed" in commands:
            self.world_modifiers["speed_mult"] = float(commands["speed"])

        if "glitch" in commands:
            self.world_modifiers["glitch_mode"] = bool(commands["glitch"])

    def update(self, dt):
        """Diyalog animasyonunu günceller"""
        if self.state == "TYPING":
            self.char_index += self.text_speed * (dt * 60)
            if int(self.char_index) > len(self.current_text):
                self.char_index = len(self.current_text)
                self.state = "WAITING_INPUT"
                self.waiting_for_click = True
            self.display_text = self.current_text[:int(self.char_index)]

        elif self.state == "THINKING":
            # Düşünme efekti
            dots = "." * (int(pygame.time.get_ticks() / 500) % 4)
            self.display_text = f"VASI BAĞLANIYOR{dots}"

    def handle_input(self):
        """Kullanıcı girişini işler"""
        if self.state == "TYPING":
            # Yazma animasyonunu atla
            self.char_index = len(self.current_text)
            self.display_text = self.current_text
            self.state = "WAITING_INPUT"
            self.waiting_for_click = True
            return False
        elif self.state == "WAITING_INPUT":
            # Sonraki satıra geç veya diyaloğu bitir
            if not self.ai_active:
                self.next_line()
            self.waiting_for_click = False
            return True
        return False

class AIChatEffect:
    """NEXUS AI Görsel Efektleri"""
    def __init__(self):
        self.timer = 0
        self.glitch_chars = "01FRAGMENTIA_ERROR_#!"

    def draw_ai_avatar(self, surface, x, y, size, thinking=False):
        """AI avatarını çizer"""
        center = (x, y)
        color = (0, 255, 100) if not thinking else (255, 100, 0)

        # Dış Halka (Statik)
        pygame.draw.circle(surface, (20, 20, 20), center, size)
        pygame.draw.circle(surface, color, center, size, 2)

        # İç Göz (Dinamik)
        t = pygame.time.get_ticks()

        if thinking:
            # Hızlı titreyen göz
            offset_x = random.randint(-2, 2)
            offset_y = random.randint(-2, 2)
            pygame.draw.circle(surface, color, (x + offset_x, y + offset_y), size // 2)
        else:
            # Nefes alan göz
            pulse = math.sin(t * 0.005) * 5
            pygame.draw.circle(surface, color, center, int((size // 2) + pulse))

        # Bağlantı çizgileri
        for i in range(3):
            angle = t * 0.002 + (i * 2.09)
            px = x + math.cos(angle) * (size + 10)
            py = y + math.sin(angle) * (size + 10)
            pygame.draw.line(surface, color, center, (px, py), 1)

# Global instance
story_manager = StoryManager()
ai_chat_effect = AIChatEffect()