import pygame
import random
from settings import LOGICAL_WIDTH, LOGICAL_HEIGHT
from boss_entities import BossSpike, BossLightning, BossGiantArrow, BossOrbitalStrike, NexusBoss, AresBoss, VasilBoss, EnemyBullet
from vfx import ScreenFlash, ParticleExplosion, Shockwave

class BossManager:
    def __init__(self):
        # Gruplar
        self.spikes = pygame.sprite.Group()
        self.lightning = pygame.sprite.Group()
        self.giant_arrows = pygame.sprite.Group()
        self.orbitals = pygame.sprite.Group()
        
        # Zamanlayıcılar
        self.timers = {
            'spike': 0,
            'lightning': 0,
            'difficulty': 0
        }
        
    def reset(self):
        """Tüm boss öğelerini temizler ve zamanlayıcıları sıfırlar"""
        self.spikes.empty()
        self.lightning.empty()
        self.giant_arrows.empty()
        self.orbitals.empty()
        self.timers = {key: 0 for key in self.timers}

    def update_logic(self, level_idx, platforms, player_x, player_karma, camera_speed, frame_mul, is_weakened=False):
        
        if level_idx not in [10, 30]: return

        # ZAYIFLAMA ÇARPANLARI
        time_mult = 0.25 if is_weakened else 1.0  # Zaman yavaşlar
        spawn_mult = 0.25 if is_weakened else 1.0 # Mermi sayısı azalır

        self.timers['difficulty'] += 1 * time_mult
        
        current_difficulty = 1
        if self.timers['difficulty'] > 300: current_difficulty = 2
        if self.timers['difficulty'] > 900: current_difficulty = 3

        # 1. KAZIKLAR
        self.timers['spike'] += 1 * time_mult
        if self.timers['spike'] > 10:
            self.timers['spike'] = 0
            visible_platforms = [p for p in platforms if 0 < p.rect.centerx < 1920]
            
            if visible_platforms:
                max_targets = 1 if is_weakened else 3
                if not is_weakened or random.random() < 0.5:
                    target_count = min(len(visible_platforms), random.randint(1, max_targets))
                    for p in random.sample(visible_platforms, target_count):
                        if not any(s.platform == p for s in self.spikes):
                            self.spikes.add(BossSpike(p, player_karma))

        # 2. YILDIRIMLAR
        self.timers['lightning'] += 1 * time_mult
        if self.timers['lightning'] > 40:
            self.timers['lightning'] = 0
            count = int(current_difficulty * 2 * spawn_mult)
            if count < 1 and not is_weakened: count = 1
            
            for _ in range(max(1, count)):
                tx = player_x + random.randint(-100, 300) if random.random() < 0.7 else random.randint(50, 1800)
                self.lightning.add(BossLightning(tx, player_karma))

        # 3. DEV OKLAR
        if current_difficulty >= 2 and int(self.timers['difficulty']) % 60 == 0:
            arrow_count = 1 if is_weakened else random.randint(2, 4)
            for _ in range(arrow_count):
                gx = max(50, min(1800, player_x + random.randint(-200, 800)))
                self.giant_arrows.add(BossGiantArrow(gx, player_karma))

        # 4. ORBITAL STRIKE
        if current_difficulty >= 3 and int(self.timers['difficulty']) % 120 == 0:
            orb_count = 1 if is_weakened else random.randint(2, 3)
            for _ in range(orb_count):
                self.orbitals.add(BossOrbitalStrike(random.randint(100, 1800), random.randint(50, 150), player_karma))

        self.spikes.update(camera_speed * frame_mul)
        self.lightning.update(camera_speed * frame_mul)
        self.giant_arrows.update(camera_speed * frame_mul)
        self.orbitals.update(camera_speed * frame_mul)

    def check_collisions(self, player_rect, player_obj, all_vfx, save_manager):
        """Oyuncu ile boss saldırılarının çarpışmasını kontrol eder"""
        hit_occurred = False
        
        # 1. Kazıklar
        for spike in self.spikes:
            if spike.state == 'ACTIVE' and player_rect.colliderect(spike.rect):
                spike.kill()
                hit_occurred = True

        # 2. Yıldırımlar
        for bolt in self.lightning:
            if bolt.state == 'ACTIVE' and player_rect.colliderect(bolt.rect):
                bolt.state = 'DONE'
                bolt.kill()
                hit_occurred = True

        # 3. Dev Oklar
        for arrow in self.giant_arrows:
            if arrow.state == 'ACTIVE' and arrow.rect.colliderect(player_rect):
                hit_occurred = True

        # 4. Orbitals
        for orb in self.orbitals:
            if orb.check_collision(player_rect):
                orb.kill()
                hit_occurred = True
        
        # Eğer bir darbe alındıysa hasar ve efekt uygula
        if hit_occurred:
            # Efektler
            all_vfx.add(ScreenFlash((255, 255, 255), 150, 5))
            all_vfx.add(ParticleExplosion(player_obj['x'] + 15, player_obj['y'] + 15, (255, 0, 0), 15))
            
            # Karma İşlemleri
            current_k = save_manager.get_karma()
            damage = 5
            
            if current_k > 0:
                save_manager.update_karma(-damage)
                # Sıfırın altına düşerse pozitife çevir (Can mantığı)
                if save_manager.get_karma() < 0: 
                    save_manager.update_karma(0 - save_manager.get_karma())
            elif current_k < 0:
                save_manager.update_karma(damage)
                # Sıfırın üstüne çıkarsa negatife çevir
                if save_manager.get_karma() > 0: 
                    save_manager.update_karma(0 - save_manager.get_karma())
                
        return hit_occurred

    def draw(self, surface):
        """Tüm saldırıları çizer"""
        for group in [self.spikes, self.lightning, self.giant_arrows, self.orbitals]:
            for entity in group:
                entity.draw(surface)