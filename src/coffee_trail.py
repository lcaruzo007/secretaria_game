import random
import pygame


class CoffeeDrop:
	"""Uma gotinha de café no chão com fade out."""

	LIFETIME = 3.5  # segundos até sumir completamente

	def __init__(self, x, y, scale=1.0):
		self.x    = x
		self.y    = y
		self.age  = 0.0
		r         = max(3, int(random.uniform(3, 6) * scale))
		# Offset aleatório pequeno para parecer derramado
		self.x   += random.randint(-6, 6)
		self.y   += random.randint(-4, 4)
		self._r   = r
		# Cor marrom-café com variação
		brown = random.randint(90, 130)
		self._color = (brown, int(brown * 0.45), int(brown * 0.1))

	@property
	def alive(self):
		return self.age < self.LIFETIME

	@property
	def alpha(self):
		ratio = 1.0 - (self.age / self.LIFETIME)
		return int(255 * ratio * ratio)  # quadrático → some mais suave no final

	def update(self, dt):
		self.age += dt

	def draw(self, surface):
		a = self.alpha
		if a <= 0:
			return
		r = self._r
		s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
		r2, g2, b2 = self._color
		pygame.draw.circle(s, (r2, g2, b2, a),        (r + 1, r + 1), r)
		pygame.draw.circle(s, (255, 255, 255, a // 2), (r + 1, r + 1), r + 1, 1)  # ← borda branca
		surface.blit(s, (int(self.x) - r - 1, int(self.y) - r - 1))

class CoffeeTrail:
	"""
	Gerencia todas as gotinhas do rastro de café.

	Uso em game.py:
	  - Criar: self.coffee_trail = CoffeeTrail(map_scale)
	  - A cada frame de jogo com café:
	      self.coffee_trail.try_emit(player.rect.centerx, player.rect.centery, moving)
	  - Update + draw:
	      self.coffee_trail.update(dt)
	      self.coffee_trail.draw(screen)
	  - Limpar ao reiniciar:
	      self.coffee_trail.clear()
	"""

	EMIT_DISTANCE = 18  # pixels entre cada gota (espaço entre gotinhas)
	MAX_DROPS     = 400  # limite de partículas simultâneas

	def __init__(self, scale=1.0):
		self._scale      = scale
		self._drops: list[CoffeeDrop] = []
		self._last_x     = None
		self._last_y     = None
		self._accum_dist = 0.0

	def try_emit(self, x, y, moving=True):
		"""Chama a cada frame enquanto o player carrega café e está se movendo."""
		if not moving:
			self._last_x = x
			self._last_y = y
			return

		if self._last_x is None:
			self._last_x, self._last_y = x, y
			return

		dx = x - self._last_x
		dy = y - self._last_y
		dist = (dx * dx + dy * dy) ** 0.5
		self._accum_dist += dist
		self._last_x, self._last_y = x, y

		while self._accum_dist >= self.EMIT_DISTANCE:
			self._accum_dist -= self.EMIT_DISTANCE
			if len(self._drops) < self.MAX_DROPS:
				self._drops.append(CoffeeDrop(x, y, self._scale))

	def update(self, dt):
		for d in self._drops:
			d.update(dt)
		self._drops = [d for d in self._drops if d.alive]

	def draw(self, surface):
		for d in self._drops:
			d.draw(surface)

	def clear(self):
		self._drops.clear()
		self._last_x = self._last_y = None
		self._accum_dist = 0.0
