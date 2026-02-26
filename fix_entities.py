import os

file_path = 'entities.py'

# Yeni ve sağlam CityBackground sınıfı kodu
new_city_bg_class = """
class CityBackground:
    def __init__(self, screen_width, screen_height):
        self.width = screen_width
        self.height = screen_height
        self.layers = []
        self.create_layers()

    def create_layers(self):
        # Katman Ayarları
        layer_configs = [
            # Katman 1: En arkada, devasa silüetler (Gökdelenler)
            {'speed': 0.05, 'color': (5, 5, 8), 'count': 10, 'w_range': (150, 400), 'h_range': (400, 900), 'windows': False, 'neon': False},
            # Katman 2: Orta mesafe, detaylı binalar
            {'speed': 0.2, 'color': (15, 15, 25), 'count': 20, 'w_range': (100, 250), 'h_range': (200, 600), 'windows': True, 'neon': False},
            # Katman 3: Yakın, hızlı, neonlu ve detaylı
            {'speed': 0.6, 'color': (25, 25, 40), 'count': 30, 'w_range': (60, 180), 'h_range': (100, 400), 'windows': True, 'neon': True}
        ]

        for config in layer_configs:
            # Sonsuz döngü için ekranın biraz fazlasını oluştur
            surface_width = self.width + 400
            layer_surface = pygame.Surface((surface_width, self.height)).convert_alpha()
            layer_surface.fill((0,0,0,0))

            current_x = 0
            while current_x < surface_width:
                w = random.randint(*config['w_range'])
                h = random.randint(*config['h_range'])
                
                rect = pygame.Rect(current_x, self.height - h, w, h)
                pygame.draw.rect(layer_surface, config['color'], rect)
                
                # Pencereler
                if config['windows']:
                    win_cols = random.randint(2, 5)
                    win_rows = random.randint(5, 15)
                    win_w = max(1, w // (win_cols + 2))
                    win_h = max(1, h // (win_rows + 2))
                    win_gap_x = max(1, (w - (win_cols * win_w)) // (win_cols + 1))
                    win_gap_y = max(1, (h - (win_rows * win_h)) // (win_rows + 1))
                    
                    win_color = random.choice([(50, 50, 80), (80, 80, 100), (100, 100, 50)])
                    lit_chance = 0.3
                    
                    for row in range(win_rows):
                        for col in range(win_cols):
                            if random.random() < lit_chance:
                                wx = current_x + win_gap_x + (col * (win_w + win_gap_x))
                                wy = (self.height - h) + win_gap_y + (row * (win_h + win_gap_y))
                                pygame.draw.rect(layer_surface, win_color, (wx, wy, win_w, win_h))

                # Neonlar
                if config['neon'] and random.random() < 0.3:
                    neon_color = random.choice([(0, 255, 255), (255, 0, 100), (50, 255, 50)])
                    if random.random() < 0.5:
                        pygame.draw.rect(layer_surface, neon_color, (current_x + 10, self.height - h + 20, 5, h - 40))
                    else:
                        sign_h = 40
                        safe_max_y = h - 60
                        if safe_max_y > 20:
                            sign_y_offset = random.randint(20, safe_max_y)
                            sign_y = self.height - h + sign_y_offset
                            
                            pygame.draw.rect(layer_surface, (0, 0, 0), (current_x - 10, sign_y, w + 20, sign_h))
                            pygame.draw.rect(layer_surface, neon_color, (current_x - 10, sign_y, w + 20, sign_h), 2)
                            for i in range(3):
                                ly = sign_y + 10 + (i * 8)
                                pygame.draw.line(layer_surface, neon_color, (current_x, ly), (current_x + w - 10, ly), 2)

                # Antenler
                if random.random() < 0.4:
                    ant_h = random.randint(20, 80)
                    pygame.draw.line(layer_surface, (50, 50, 50), (current_x + w//2, self.height - h), (current_x + w//2, self.height - h - ant_h), 2)
                    if random.random() < 0.5:
                        pygame.draw.circle(layer_surface, (200, 0, 0), (current_x + w//2, self.height - h - ant_h), 2)

                current_x += w + random.randint(-5, 5)

            # Twin Surface Tekniği (x1, x2)
            self.layers.append({
                'surface': layer_surface,
                'speed': config['speed'],
                'x1': 0,
                'x2': surface_width,
                'width': surface_width
            })
            
        # Uçan Arabalar
        self.cars = []
        for _ in range(10):
            self.cars.append({
                'x': random.randint(0, self.width),
                'y': random.randint(100, 600),
                'speed': random.uniform(2, 5),
                'color': random.choice([(255, 200, 200), (200, 200, 255), (255, 255, 200)])
            })

    def update(self, camera_speed):
        # Katmanları kaydır (Sonsuz Döngü)
        for layer in self.layers:
            move = layer['speed'] * (camera_speed * 0.8)
            layer['x1'] -= move
            layer['x2'] -= move
            
            if layer['x1'] <= -layer['width']:
                layer['x1'] = layer['x2'] + layer['width']
            
            if layer['x2'] <= -layer['width']:
                layer['x2'] = layer['x1'] + layer['width']
                
        # Arabaları hareket ettir
        for car in self.cars:
            car['x'] -= car['speed'] + (camera_speed * 0.1)
            if car['x'] < -50:
                car['x'] = self.width + random.randint(50, 200)
                car['y'] = random.randint(100, 600)

    def draw(self, surface):
        # Katmanları çiz
        for layer in self.layers:
            if layer['x1'] < self.width:
                surface.blit(layer['surface'], (int(layer['x1']), 0))
            if layer['x2'] < self.width:
                surface.blit(layer['surface'], (int(layer['x2']), 0))
                
        # Arabaları çiz
        for car in self.cars:
            pygame.draw.circle(surface, car['color'], (int(car['x']), int(car['y'])), 2)
            pygame.draw.line(surface, (*car['color'], 100), 
                             (int(car['x']), int(car['y'])), (int(car['x'] + 20), int(car['y'])), 1)
"""

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Eski sınıfı bul ve oradan sonrasını kes
    start_index = content.find("class CityBackground:")

    if start_index != -1:
        new_content = content[:start_index] + new_city_bg_class
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("BAŞARILI: entities.py düzeltildi. Artık oyunu başlatabilirsiniz!")
    else:
        print("HATA: 'class CityBackground:' bulunamadı.")
except Exception as e:
    print(f"HATA: {e}")