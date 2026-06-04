import math
import random

import pygame

try:
	from src import settings
except ImportError:
	import settings


# Paleta de cores para os NPCs (bolinha + borda)
NPC_COLORS = {
	"RH":         ((220,  80,  80), (160,  20,  20)),
	"Financeiro": (( 80, 150, 220), ( 20,  70, 160)),
	"Gabinete":   ((220, 180,  50), (160, 120,  10)),
	"TI":         (( 80, 200, 100), ( 20, 130,  50)),
	"ASCOM":      ((200,  80, 200), (130,  20, 140)),
}

# ── Constantes de escala ─────────────────────────────────────────
_MAP_ORIG_W  = 1920
_MAP_ORIG_H  = 1280
_MAP_SCALE   = min(settings.WIDTH / _MAP_ORIG_W, settings.HEIGHT / _MAP_ORIG_H)
_MAP_DISP_W  = int(_MAP_ORIG_W * _MAP_SCALE)
_MAP_DISP_H  = int(_MAP_ORIG_H * _MAP_SCALE)
_MAP_OFS_X   = (settings.WIDTH  - _MAP_DISP_W) // 2
_MAP_OFS_Y   = (settings.HEIGHT - _MAP_DISP_H) // 2

# MAP_BOUNDS = todo o mapa visível (para o player sair pelas saídas)
MAP_BOUNDS = pygame.Rect(_MAP_OFS_X, _MAP_OFS_Y, _MAP_DISP_W, _MAP_DISP_H)

# Raio base do NPC no espaço original (px), escalado para tela
_NPC_RADIUS_ORIG = 20
_NPC_RADIUS = max(8, int(_NPC_RADIUS_ORIG * _MAP_SCALE))


class NPC(pygame.sprite.Sprite):
	"""
	NPC representado como uma bolinha colorida que patrulha o mapa.
	Intercepta o player quando entra no raio de detecção.
	Todas as coordenadas e tamanhos já estão no espaço de TELA.

	Parâmetros:
	  building_bounds: pygame.Rect que limita a área de patrulha do NPC.
	                   Se None, usa MAP_BOUNDS (o mapa inteiro).
	"""

	def __init__(self, x, y, nome, frases, sprite_name="", scale=1.0,
	             intercept_radius=80, patrol_speed=90,
	             collision_rects=None, building_bounds=None):
		super().__init__()
		self.nome  = nome
		self.frases = list(frases)
		self.intercept_radius = intercept_radius  # pixels de tela
		self.patrol_speed     = patrol_speed       # pixels/s de tela
		self.collision_rects  = collision_rects or []

		# NPCs ficam confinados dentro do prédio, não em todo o mapa
		self.patrol_bounds = building_bounds if building_bounds is not None else MAP_BOUNDS

		self._radius = _NPC_RADIUS
		self.image   = self._make_ball_surface()
		self.rect    = self.image.get_rect(center=(x, y))
		# Garante que o NPC começa dentro dos limites do prédio
		self.rect.clamp_ip(self.patrol_bounds)

		# Movimento de patrulha
		self._vel_x = 0.0
		self._vel_y = 0.0
		self._choose_direction()
		self._move_timer    = 0.0
		self._move_interval = random.uniform(1.5, 3.5)

		# Cooldown de intercept
		self.cooldown = 0.0

	def _make_ball_surface(self):
		r    = self._radius
		size = r * 2 + 4
		surf = pygame.Surface((size, size), pygame.SRCALPHA)
		fill_color, border_color = NPC_COLORS.get(self.nome, ((180, 180, 180), (80, 80, 80)))
		cx = cy = size // 2

		# Sombra
		pygame.draw.circle(surf, (0, 0, 0, 60), (cx + 2, cy + 3), r)
		# Corpo
		pygame.draw.circle(surf, fill_color, (cx, cy), r)
		# Borda
		pygame.draw.circle(surf, border_color, (cx, cy), r, max(1, r // 7))
		# Brilho
		pygame.draw.circle(surf, (255, 255, 255, 120),
		                   (cx - max(1, r // 4), cy - max(1, r // 3)), max(2, r // 3))
		# Inicial do nome
		try:
			font_size = max(8, int(14 * _MAP_SCALE))
			font = pygame.font.SysFont("Arial", font_size, bold=True)
			txt  = font.render(self.nome[0], True, (255, 255, 255))
			surf.blit(txt, txt.get_rect(center=(cx, cy)))
		except Exception:
			pass
		return surf

	def _choose_direction(self):
		angle        = random.uniform(0, 2 * math.pi)
		self._vel_x  = math.cos(angle) * self.patrol_speed
		self._vel_y  = math.sin(angle) * self.patrol_speed

	def _check_collision(self, rect):
		for cr in self.collision_rects:
			if rect.colliderect(cr):
				return True
		return False

	def update(self, dt=1/60):
		# Cooldown de intercept
		if self.cooldown > 0:
			self.cooldown = max(0.0, self.cooldown - dt)

		# Timer para mudar direção aleatoriamente
		self._move_timer += dt
		if self._move_timer >= self._move_interval:
			self._move_timer    = 0.0
			self._move_interval = random.uniform(1.5, 3.5)
			self._choose_direction()

		# Tenta mover com detecção de colisão
		new_x = self.rect.centerx + self._vel_x * dt
		new_y = self.rect.centery + self._vel_y * dt

		test_rect = self.rect.copy()
		test_rect.centerx = int(new_x)
		test_rect.centery = int(new_y)

		# Clamp dentro dos patrol_bounds (prédio), não o mapa inteiro
		test_rect.clamp_ip(self.patrol_bounds)

		if not self._check_collision(test_rect):
			self.rect.center = test_rect.center
		else:
			# Deslizamento em X
			test_x = self.rect.copy()
			test_x.centerx = int(new_x)
			test_x.clamp_ip(self.patrol_bounds)
			if not self._check_collision(test_x):
				self.rect.centerx = test_x.centerx
				self.rect.clamp_ip(self.patrol_bounds)
			else:
				# Deslizamento em Y
				test_y = self.rect.copy()
				test_y.centery = int(new_y)
				test_y.clamp_ip(self.patrol_bounds)
				if not self._check_collision(test_y):
					self.rect.centery = test_y.centery
					self.rect.clamp_ip(self.patrol_bounds)
				else:
					# Bloqueado dos dois lados — muda direção imediatamente
					self._choose_direction()

		# Segurança: garante que nunca sai dos patrol_bounds
		self.rect.clamp_ip(self.patrol_bounds)

	def intercepts(self, player_rect):
		dist = math.hypot(
			self.rect.centerx - player_rect.centerx,
			self.rect.centery - player_rect.centery,
		)
		return dist <= self.intercept_radius and self.cooldown <= 0

	def get_phrase(self, index=0):
		if not self.frases:
			return ""
		return self.frases[index % len(self.frases)]

	def draw_radius(self, surface):
		"""Desenha círculo de detecção semi-transparente."""
		r = self.intercept_radius
		s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
		fill, _ = NPC_COLORS.get(self.nome, ((180, 180, 180), (80, 80, 80)))
		pygame.draw.circle(s, (*fill, 22), (r, r), r)
		pygame.draw.circle(s, (*fill, 55), (r, r), r, 1)
		surface.blit(s, (self.rect.centerx - r, self.rect.centery - r))