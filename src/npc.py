import math
import random

import pygame

try:
	from src import settings
except ImportError:
	import settings


# Paleta de cores para os NPCs (bolinha + borda)
NPC_COLORS = {
	"RH":         ((220,  80,  80), (160,  20,  20)),   # vermelho
	"Financeiro": (( 80, 150, 220), ( 20,  70, 160)),   # azul
	"Gabinete":   ((220, 180,  50), (160, 120,  10)),   # amarelo-ouro
	"TI":         (( 80, 200, 100), ( 20, 130,  50)),   # verde
	"ASCOM":      ((200,  80, 200), (130,  20, 140)),   # roxo
}

MAP_BOUNDS = pygame.Rect(10, 10, settings.WIDTH - 20, settings.HEIGHT - 30)


class NPC(pygame.sprite.Sprite):
	"""
	NPC representado como uma bolinha colorida que patrulha o mapa.
	Intercepta o player quando entra no raio de deteccao.
	"""

	def __init__(self, x, y, nome, frases, sprite_name="", scale=1.0,
				 intercept_radius=80, patrol_speed=90):
		super().__init__()
		self.nome = nome
		self.frases = list(frases)
		self.intercept_radius = intercept_radius
		self.patrol_speed = patrol_speed

		self._radius = 20
		self.image = self._make_ball_surface()
		self.rect = self.image.get_rect(center=(x, y))

		# Movimento de patrulha
		self._vel_x = 0.0
		self._vel_y = 0.0
		self._choose_direction()
		self._move_timer = 0.0
		self._move_interval = random.uniform(1.5, 3.5)

		# Cooldown de intercept
		self.cooldown = 0.0

	def _make_ball_surface(self):
		size = self._radius * 2 + 4
		surf = pygame.Surface((size, size), pygame.SRCALPHA)
		fill_color, border_color = NPC_COLORS.get(self.nome, ((180, 180, 180), (80, 80, 80)))
		cx = cy = size // 2
		# Sombra
		pygame.draw.circle(surf, (0, 0, 0, 60), (cx + 2, cy + 3), self._radius)
		# Corpo
		pygame.draw.circle(surf, fill_color, (cx, cy), self._radius)
		# Borda
		pygame.draw.circle(surf, border_color, (cx, cy), self._radius, 3)
		# Brilho
		pygame.draw.circle(surf, (255, 255, 255, 120), (cx - 5, cy - 6), self._radius // 3)
		# Inicial do nome
		try:
			font = pygame.font.SysFont("Arial", 14, bold=True)
			txt = font.render(self.nome[0], True, (255, 255, 255))
			surf.blit(txt, txt.get_rect(center=(cx, cy)))
		except Exception:
			pass
		return surf

	def _choose_direction(self):
		angle = random.uniform(0, 2 * math.pi)
		self._vel_x = math.cos(angle) * self.patrol_speed
		self._vel_y = math.sin(angle) * self.patrol_speed

	def update(self, dt=1/60):

		# Cooldown de intercept
		if self.cooldown > 0:
			self.cooldown = max(0.0, self.cooldown - dt)

		# Timer para mudar direcao aleatoriamente
		self._move_timer += dt
		if self._move_timer >= self._move_interval:
			self._move_timer = 0.0
			self._move_interval = random.uniform(1.5, 3.5)
			self._choose_direction()

		# Tenta mover
		new_x = self.rect.centerx + self._vel_x * dt
		new_y = self.rect.centery + self._vel_y * dt

		self.rect.centerx = int(new_x)
		self.rect.centery = int(new_y)
		self.rect.clamp_ip(MAP_BOUNDS)

	def intercepts(self, player_rect):
		distance = math.hypot(
			self.rect.centerx - player_rect.centerx,
			self.rect.centery - player_rect.centery
		)
		return distance <= self.intercept_radius and self.cooldown <= 0

	def get_phrase(self, index=0):
		if not self.frases:
			return ""
		return self.frases[index % len(self.frases)]

	def draw_radius(self, surface):
		"""Desenha circulo de deteccao semi-transparente."""
		r = self.intercept_radius
		s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
		fill, _ = NPC_COLORS.get(self.nome, ((180, 180, 180), (80, 80, 80)))
		pygame.draw.circle(s, (*fill, 22), (r, r), r)
		pygame.draw.circle(s, (*fill, 55), (r, r), r, 1)
		surface.blit(s, (self.rect.centerx - r, self.rect.centery - r))