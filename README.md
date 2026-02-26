# 🎮 FRAGMENTIA - Teknik Sistem Açıklaması

## 🎯 Oyunun Temel Fikri

**FRAGMENTIA** bir **cyberpunk runner oyunu**. Sen bir kişisizsin (İsimsiz) ve "Fragmentia" adlı bir şehirde hayatta kalmaya çalışıyorsun. Platformlar arasında zıpla, çevikliğini göster, engelleri aş ve öl. Ama dikkat: **Karma sistemi** var. İyi mü kötü mü davranırsan, oyun sana bu davranışla cevap verir.

---

## 🏗️ Sistem Mimarisi

```
OYUN AKIŞI:
┌─────────────────────────────────────────────────────────┐
│ MENU / SEVİYE SEÇ                                       │
├─────────────────────────────────────────────────────────┤
│ LOADING EKRANI (Hikaye Yükleniyor)                     │
├─────────────────────────────────────────────────────────┤
│ OYUN LOOP (60 FPS)                                     │
│  ├─ Oyuncu Hareketi (WASD, Space, Shift)             │
│  ├─ Platform & Düşman Yönetimi                        │
│  ├─ Karma & AI Sistemi                                │
│  ├─ Çarpışma Kontrolü                                 │
│  └─ Ekrana Çiz                                        │
├─────────────────────────────────────────────────────────┤
│ SEVİYE BITTI / BOSS SAVAŞI / CUTSCENE                 │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Dosya Yapısı & Görevleri

### **settings.py** 🎛️
Tüm **sabitleri** burada saklıyoruz (oyun sabitleri değil, değişkenler).

```
✓ Ekran boyutu (1920x1080)
✓ Fizik sabitleri (Yerçekimi = 1.0, Zıplama Gücü = 28)
✓ 30 Seviyenin Konfigürasyonu
✓ 5 Tema (Renk Şemaları)
✓ Ses Ayarları
```

**Örnek:**
```python
GRAVITY = 1.0          # Her frame'de aşağı düş
JUMP_POWER = 28        # Zıplama hızı
DASH_SPEED = 90        # Hızlı hareket hızı
LOGICAL_WIDTH = 1920   # Oyun alanı genişliği
```

---

### **main.py** 🎮 (Ana Oyun Döngüsü)
Oyunun **kalbi**. Her frame'de:
1. Girdileri oku
2. Fizikteki güncellemeleri yap
3. Çarpışmaları kontrol et
4. Ekrana çiz

```
Her Frame (60 kez/saniye):
  1. event.get() → Fare, Klavye, XBox kontrolörü girdileri
  2. update() → Oyuncuyu, düşmanları, platformları taşı
  3. check_collisions() → Çarptı mı? Hasar al!
  4. render() → Ekrana çiz
  5. clock.tick(60) → 16ms bekle (60 FPS)
```

**Önemli Değişkenler:**
```python
camera_speed = 5.0          # Platformlar ne kadar hızlı geliyor?
player_x, player_y = 150, 300  # Oyuncunun konumu
y_velocity = 0              # Dikey hız (atıldığında = -JUMP_POWER)
is_dashing = False          # Şu an çakmak yapıyor mu?
```

---

### **entities.py** 👥 (Nesneler)
Oyunda görünen her şey burası:

#### **Platform**
```python
# Rastgele oluşturulan yatay platformlar
class Platform:
    def __init__(self, x, y, width, height, theme_index):
        # theme_index: 0=Neon, 1=Nexus, 2=Çöplük, 3=Sanayi, 4=Dinlenme
        self.rect = pygame.Rect(x, y, width, height)
        # Farklı temalara göre renkli doku üretilir
```

#### **Düşmanlar** 
```python
class CursedEnemy:     # Zıplayan küçük kırmızı melez
class DroneEnemy:      # Hava da uçan otomat  
class TankEnemy:       # Ağır, yavaş, ateş etmez
```

#### **NPC** (Sohbet Edilebilecek Karakterler)
```python
class NPC:
    def __init__(self, x, y, name, color, personality_type):
        # personality_type: "philosopher", "warrior", "mystic"
        # Oyuncu konuşabilir ve AI cevap verebilir (Gemini API ile)
```

#### **Arka Planlar**
```python
class CityBackground:       # Şehir silüetleri + uçan arabalar
class GutterBackground:     # Kirli çöplük teması
class IndustrialBackground: # Fabrika + dişliler + pistonlar
```

---

### **animations.py** 🎨 (Görsel Efektler)

Oyuncunun hareketi animasyonlu:

```python
class CharacterAnimator:
    # İdlede titrer, koşarken ayakları döner, zıplarken kuyruğu sallanır
    def update(self, dt, state, is_grounded, velocity_y):
        if state == 'idle':
            self._update_idle(dt)  # Nefes al
        elif state == 'running':
            self._update_running(dt)  # Ayakları döndür
        elif state == 'jumping':
            self._update_jumping(dt)  # Gövde geri eğ
        elif state == 'dashing':
            self._update_dashing(dt)  # Işık parçacıkları
```

**Efektler:**
- **Trail** = Oyuncunun arkasında bıraktığı iz
- **Particles** = Patlayıcı güç gösterişi
- **ScreenShake** = Ağır darbelerde kamera titrer
- **ElectricParticle** = Siyah-mavi çakıldı görüntüsü

---

### **boss_entities.py** & **local_bosses.py** 👹 (Üç Ana Boss)

#### **NexusBoss** (Orta)
```
- Basit dairesel görünüm
- Oyuncunun konumuna doğru ateş eder
- Sağlık barı: 1000 HP
```

#### **AresBoss** (Düşük Karma - Ares, Savaşçı)
```
- Kare şekil
- 3 yönlü mermiler fırlatır
- Daha agresif ve hızlı
```

#### **VasilBoss** (Yüksek Karma - Vasi, Admin)
```
- Üçgen şekli (Piramit = Yönetim)
- Dönermiş miş gibi ateş eder
- En zor boss
- Sesi: "Seni simülasyondan sileceğim"
```

#### **Boss Saldırıları** (BossManager ile kontrol edilir):
```python
class BossSpike:         # Platformdan şut alan kazıklar
class BossLightning:     # Dikey yıldırım sütunları
class BossGiantArrow:    # Aşağıdan yükselen dev oklar
class BossOrbitalStrike: # Çember şeklinde enerji dalgaları
```

---

### **save_system.py** 💾 (Kayıt Sistemi)

Oyuncu ilerleme, ayarlar, karma verilerini saklar:

```json
{
  "karma": 50,
  "saved_souls": 3,
  "easy_mode": {
    "unlocked_levels": [1, 2, 3],
    "high_scores": {
      "1": 50000,
      "2": 75000
    }
  },
  "settings": {
    "fullscreen": true,
    "sound_volume": 0.7,
    "music_volume": 0.5
  }
}
```

---

### **story_system.py** 📖 (AI Hikaye Motoru)

**Google Gemini API** ile NPC'ler **gerçekten** sohbet edebiliyor:

```python
class StoryManager:
    def setup_ai(self):
        # Gemini API'yi başlat
        genai.configure(api_key=GENAI_API_KEY)
        self.model = genai.GenerativeModel(AI_MODEL_NAME)
        
    def send_ai_message(self, user_text):
        # Oyuncu mesaj gönder → API → NPC cevap ver
        response = self.chat_session.send_message(user_text)
        return response.text
```

**UYARI:** Gemini API Key olmadan AI kapalı kalır. 🔐

---

### **vfx.py** ✨ (Görsel Efektler Kütüphanesi)

Tüm güzel efektler:

```python
class LightningBolt:        # Çakıldı (Rastgele dalgalı çizgi)
class FlameSpark:           # Alev parçacığı
class Shockwave:            # Dalgalı enerji yayılması
class SpeedLine:            # Hızlanma izleri
class ParticleExplosion:    # Patlama
class GhostTrail:           # Hayalet izi (holografik)
class SavedSoul:            # Kurtarılan ruh (sarı melek)
```

---

### **auxiliary_systems.py** 🔧 (Gelecek Sistemler)

Henüz tamamlanmadı ama şunları barındırıyor:

```python
class RestAreaManager:      # Dinlenme bölgeleri
class RealityShiftSystem:   # Paralel gerçeklikler
class TimeLayerSystem:      # Zaman katmanları
class ReactiveFragmentia:   # Dünya oyuncu davranışına tepki verir
class LivingNPC:            # AI NPC'ler
```

---

## 🎮 Oyun Mekanikler

### **Karma Sistemi** 📊

```
KARMA SKORU: -1000 ... 0 ... +1000

KÖTÜYEKİ GÖREVLİ EYLEMLER (-Karma):
  ✗ Düşman öl
  ✗ NPC ile saldır
  ✗ Zararlı seçimler yap
  → Ares Boss'u Limbo'da görürsün
  → Kırmızı tema, savaş müziği

İYİYEKİ BARIŞ YOLU (+Karma):
  ✓ Kimseyi öldürme
  ✓ NPC'ler ile sohbet
  ✓ Yararlı seçimler yap
  → Vasi Boss'u Limbo'da görürsün
  → Yeşil tema, hüzünlü müzik

NÖTR OYUN (0 Karma):
  ◇ Karışık davranış
  → Nexus Boss savaşı
```

### **Çakmak (Dash)** ⚡

```python
if is_dashing:
    player_x += DASH_SPEED * cos(angle)
    trail_effects.append(GhostTrail(...))
    screen_shake = 10
```

- **Süre:** 18 frame (0.3 saniye)
- **Hızı:** 90 px/frame
- **Bekleme:** 60 frame (1 saniye)
- **Efekt:** Işık izi, titreşim

### **Çakma (Slam)** 💥

```python
if is_slamming:
    y_velocity = SLAM_GRAVITY * 5  # Düş
    on_ground → Patlama efekti + Şok dalgası
```

- **Türe binilir:** Zıplama sırasında Shift
- **Sonuç:** Düşmanları saç saça beraber vur

---

## 🎨 Görsel Sistem (Temalar)

| Tema | Renk | Kullanım | BGM |
|------|------|----------|-----|
| **Neon Pazarı** (0) | Mavi/Mor | 11-23. Seviyeler | cyber_chase.mp3 |
| **Nexus ÇEKİRDEĞİ** (1) | Beyaz/Kırmızı | Boss Savaşları | final_boss.mp3 |
| **Çöplük (Gutter)** (2) | Yeşil | 1-5. Seviyeler | ara1.mp3 |
| **Sanayi** (3) | Turuncu/Pas | 6-10. Seviyeler | ara2.mp3 |
| **Dinlenme** (4) | Sakin Mavi | Rest Alanları | calm.mp3 |

---

## 🔊 Ses Sistemi

```python
class AudioManager:
    def play_music(self, sound_obj):
        # Müzik her zaman Channel 0'da çalar
        
    def play_sfx(self, sound_obj):
        # Efekt sesini boş kanalde çalar
        
    def update_settings(self, volume_dict):
        # Master × Özel Seviye
        final_volume = master_vol * music_vol
```

**Ses Türleri:**
- `DASH_SOUND` → Şut hareketi
- `SLAM_SOUND` → Çakma iniş
- `EXPLOSION_SOUND` → Patlama
- Müzikler → Her tema için farklı

---

## 🔐 Kaydedilen Veriler

```
save_data.json
├─ karma: 42
├─ saved_souls: 5
├��� easy_mode
│  ├─ unlocked_levels: 1-15
│  └─ high_scores: {1: 50000, 2: 75000, ...}
├─ settings
│  ├─ fullscreen: true
│  ├─ res_index: 1 (1920x1080)
│  ├─ fps_index: 1 (60 FPS)
│  └─ volume: {master: 0.7, music: 0.5, sfx: 0.8}
└─ nexus_simulation
   └─ npc_memory: {Sokrat: {...}, Ares: {...}, ...}
```

---

## 🎯 Oyun Akışı (30 Seviye)

```
ACT 1: MİDE (1-5)
  └─ Öğrenme fazı, yavaş

ACT 2: SANAYI (6-10) + BOSS ARA
  └─ İlk Boss Savaşı

ACT 3: ŞEHIR (11-24) + ARASI DİNLENME (19)
  └─ Ana oyun bölümü, hızlanma

ACT 4: NEXUS (25-29) + FINAL BOSS (30)
  └─ En zor, en hızlı
```

---

## 🛠️ Teknik İpuçları

### **Çarpışma Kontrolü**
```python
# Dikdörtgen çarpışması
if player_rect.colliderect(platform_rect):
    # Oyuncu platforma dokundu
    is_grounded = True
    y_velocity = 0
```

### **Kamera Hareketi**
```python
# Platformlar oyuncunun soluna doğru gelir
camera_speed = 5.0  # 300 px/saniye
platform.x -= camera_speed * dt
```

### **AI İntegrasyonu**
```
Google Gemini API → Python SDK → Chat Session → Gerçek cevaplar
```

---

## ⚠️ Bilinen Sınırlamalar

1. **Ses Dosyaları** kayıt altında değil, procedural üretiliyor (CPU yoğun)
2. **Gemini API Key** olmadan AI kapalı
3. **Bellek Optimizasyonu** eksik (100+ VFX yavaşlatabilir)
4. **Mobile Uyumluluğu** yok (sadece PC)
5. **Çok Oyunculu** desteklenmiyor

---

## 🚀 Nasıl Çalıştırılır?

```bash
# 1. Bağımlılıkları Yükle
pip install pygame numpy google-generativeai

# 2. Gemini API Key'i Ekle (settings.py'ye)
GENAI_API_KEY = "AIza..."

# 3. Oyunu Başlat
python main.py
```

---

## 📊 Performans Metrikleri

```
FPS Target:      60
Çözünürlük:      1920×1080
Minimum Gerekli: 
  - CPU: Intel i5 2.0GHz+
  - RAM: 4GB
  - GPU: Intel UHD 620+

Optimize Etmeler:
  - UI Cache (Son Skor 20 kare boyunca değişmezse yeniden çizilmez)
  - VFX Limiti (Max 100 Sprite)
  - Sprite Batching (Tüm platformlar 1 draw call'da)
```

---

## 🎓 Neden Böyle Tasarlandı?

| Tasarım Seçimi | Neden |
|-----------------|-------|
| 30 Seviye | Kademeli zorluk artışı |
| 3 Boss | Karma seçimlerine göre |
| Temalar | Eşyalar konularını pekiştir |
| AI NPC | Hikaye interaktif hale gelir |
| Procedural Ses | Dosya boyutunu küçüt |

---

