import pygame

class AssetManager:
    def __init__(self):
        self.sprites = {}

    def load_sprite(self, name, path, alpha=True):
        image = pygame.image.load(path)
        # convert() performansı %300 artırır
        self.sprites[name] = image.convert_alpha() if alpha else image.convert()
        return self.sprites[name]

    def get_sprite(self, name):
        return self.sprites.get(name)

# Global erişim için
assets = AssetManager()