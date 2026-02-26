import json
import os

SAVE_FILE = "save_data.json"

class SaveManager:
    def __init__(self):
        self.data = self.load_data()

    def load_data(self):
        """Kayıt dosyasını yükler, yoksa varsayılanı oluşturur."""
        if not os.path.exists(SAVE_FILE):
            default = self.create_default_data()
            self.save_data(default)
            return default

        try:
            with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Veri yapısı eksikse onar
                if "settings" not in data:
                    data["settings"] = {}
                return data
        except (json.JSONDecodeError, IOError) as e:
            print(f"Kayıt dosyası bozuk, varsayılanlar yükleniyor. Hata: {e}")
            default = self.create_default_data()
            self.save_data(default)
            return default

    def create_default_data(self):
        """Varsayılan oyun verilerini oluşturur."""
        default_data = {
            "karma": 0,
            "saved_souls": 0,
            "easy_mode": {
                "unlocked_levels": 1,
                "completed_levels": [],
                "high_scores": {}
            },
            "settings": {
                "fullscreen": True,   # EKLENDİ
                "res_index": 1,       # EKLENDİ
                "fps_index": 1,       # EKLENDİ
                "sound_volume": 0.7,
                "music_volume": 0.5,
                "effects_volume": 0.8
            },
            "nexus_simulation": {
                "economy": {
                    "credits": 100,
                    "stocks": {"NEXUS": 10, "GUTTER": 5, "AMMO": 20},
                    "inflation_rate": 1.0
                },
                "factions": {
                    "NEXUS": 50,
                    "GUTTER": 50,
                    "VOID": 50
                },
                "npc_memory": {}
            }
        }
        return default_data

    def save_data(self, data=None):
        if data is not None:
            self.data = data
        try:
            with open(SAVE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"Kayıt Hatası: {e}")

    # --- SETTINGS YÖNETİMİ (BURASI HATAYI ÇÖZER) ---
    def get_settings(self):
        """Ayarları döndürür, eksik anahtarları varsayılanlarla doldurur."""
        current_settings = self.data.get("settings", {})
        
        # Varsayılanlar
        defaults = {
            "fullscreen": True,
            "res_index": 1,
            "fps_index": 1,
            "sound_volume": 0.7,
            "music_volume": 0.5,
            "effects_volume": 0.8
        }
        
        # Eksik olanları tamamla
        for key, value in defaults.items():
            if key not in current_settings:
                current_settings[key] = value
        
        # Tamamlanmış ayarları geri kaydet (Memory'ye)
        self.data["settings"] = current_settings
        return current_settings

    def update_settings(self, settings_dict):
        if "settings" not in self.data:
            self.data["settings"] = {}
        self.data["settings"].update(settings_dict)
        self.save_data()
        return True

    # --- OYUN VERİLERİ ---
    def update_karma(self, amount):
        if "karma" not in self.data: self.data["karma"] = 0
        self.data["karma"] = max(-1000, min(1000, self.data["karma"] + amount))
        self.save_data()

    def get_karma(self):
        return self.data.get("karma", 0)

    def add_saved_soul(self, amount=1):
        if "saved_souls" not in self.data: self.data["saved_souls"] = 0
        self.data["saved_souls"] += amount
        self.save_data()

    def update_high_score(self, mode, level_idx, score):
        if mode not in self.data:
            self.data[mode] = {"unlocked_levels": 1, "completed_levels": [], "high_scores": {}}
        
        str_level = str(level_idx)
        current_high = self.data[mode]["high_scores"].get(str_level, 0)
        
        if score > current_high:
            self.data[mode]["high_scores"][str_level] = int(score)
            self.save_data()
            return True
        return False

    def unlock_next_level(self, mode, current_level_idx):
        if mode not in self.data:
            self.data[mode] = {"unlocked_levels": 1, "completed_levels": [], "high_scores": {}}
            
        if current_level_idx not in self.data[mode]["completed_levels"]:
            self.data[mode]["completed_levels"].append(current_level_idx)
            
        next_level = current_level_idx + 1
        if next_level > self.data[mode]["unlocked_levels"]:
            self.data[mode]["unlocked_levels"] = next_level
        self.save_data()
        return True

    def reset_progress(self):
        self.data = self.create_default_data()
        self.save_data()
        return True

    # --- NEXUS SİMÜLASYON VERİLERİ ---
    def get_npc_data(self, npc_name):
        if "nexus_simulation" not in self.data:
            self.data["nexus_simulation"] = self.create_default_data()["nexus_simulation"]
        return self.data["nexus_simulation"]["npc_memory"].get(npc_name, None)

    def save_npc_data(self, npc_name, profile_obj):
        if "nexus_simulation" not in self.data:
            self.data["nexus_simulation"] = self.create_default_data()["nexus_simulation"]
            
        self.data["nexus_simulation"]["npc_memory"][npc_name] = {
            "trust": profile_obj.trust,
            "fear": profile_obj.fear,
            "memories": profile_obj.memories
        }
        self.save_data()

# Global instance
save_manager = SaveManager()