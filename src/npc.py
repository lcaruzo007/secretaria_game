import math
import os

import pygame

try:
	from src import settings
except ImportError:
	import settings


class NPC(pygame.sprite.Sprite):
	def __init__(self, x, y, nome, frases, sprite_name="gabinete.png", scale=1.0, intercept_radius=80):
		super().__init__()
		self.nome = nome
		self.frases = list(frases)
		self.sprite_name = sprite_name
		self.scale = scale
		self.intercept_radius = intercept_radius
		self.image = self._load_image(sprite_name)
		self.rect = self.image.get_rect(center=(x, y))

	def _load_image(self, sprite_name):
		image_path = os.path.join(settings.IMAGES_DIR, sprite_name)
		if not os.path.exists(image_path):
			return pygame.Surface((48, 48), pygame.SRCALPHA)

		image = pygame.image.load(image_path)
		if pygame.display.get_init() and pygame.display.get_surface() is not None:
			image = image.convert_alpha()
		else:
			image = image.copy()

		if self.scale != 1.0:
			new_size = (max(1, int(image.get_width() * self.scale)), max(1, int(image.get_height() * self.scale)))
			image = pygame.transform.smoothscale(image, new_size)

		return image

	def intercepts(self, player_rect):
		distance = math.hypot(self.rect.centerx - player_rect.centerx, self.rect.centery - player_rect.centery)
		return distance <= self.intercept_radius

	def get_phrase(self, index=0):
		if not self.frases:
			return ""

		return self.frases[index % len(self.frases)]

	def update(self):
		return None