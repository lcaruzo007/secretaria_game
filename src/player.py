import os

import pygame

try:
	from src import settings
except ImportError:
	import settings


# ── Constantes de escala (devem bater com game.py) ───────────────
_MAP_ORIG_W = 1920
_MAP_ORIG_H = 1280
_MAP_SCALE  = min(settings.WIDTH / _MAP_ORIG_W, settings.HEIGHT / _MAP_ORIG_H)

# Tamanho-base do fallback (bolinha) no espaço original e escalado
_FALLBACK_SIZE_ORIG = 48
_FALLBACK_SIZE      = max(16, int(_FALLBACK_SIZE_ORIG * _MAP_SCALE))

# Velocidade-base do player (px/s no espaço original) escalada para tela
# O valor 220 era pensado para 1920×1280; na tela 1280×720 fica proporcional
_MOVE_SPEED_DEFAULT = int(220 * _MAP_SCALE)


class Player(pygame.sprite.Sprite):
	DIRECTIONS    = ("down", "left", "right", "up")
	FALLBACK_COLOR   = (70, 140, 255)
	FALLBACK_OUTLINE = (255, 255, 255)

	def __init__(self, x, y, sprite_name="player.png", scale=1.0,
	             animation_speed=120, move_speed=None):
		super().__init__()
		self.sprite_name     = sprite_name
		self.animation_speed = animation_speed
		# Se move_speed não for passado explicitamente, usa o valor escalado
		self.move_speed      = move_speed if move_speed is not None else _MOVE_SPEED_DEFAULT
		self.direction       = "down"
		self.moving          = False
		self.frame_index     = 0
		self.last_update     = 0
		self.scale           = scale
		self._fallback_sheet = False

		self.sheet = self._load_sheet(sprite_name)
		self.frame_width, self.frame_height = self._detect_frame_size(self.sheet)
		self.frames = self._build_frames(self.sheet)
		self.image  = self.frames[self.direction][0]
		self.rect   = self.image.get_rect(center=(x, y))

	# ── carregamento do sprite ───────────────────────────────

	def _detect_frame_size(self, sheet):
		if sheet.get_width() % 4 == 0 and sheet.get_height() % 4 == 0:
			return sheet.get_width() // 4, sheet.get_height() // 4
		return sheet.get_width(), sheet.get_height()

	def _load_sheet(self, sprite_name):
		image_path = os.path.join(settings.IMAGES_DIR, sprite_name)
		if not os.path.exists(image_path):
			self._fallback_sheet = True
			return self._build_fallback_surface()

		image = pygame.image.load(image_path)
		if pygame.display.get_init() and pygame.display.get_surface() is not None:
			image = image.convert_alpha()
		else:
			image = image.copy()

		# Escala do sprite: scale explícito × MAP_SCALE para ajustar ao mapa
		combined = self.scale * _MAP_SCALE
		if combined != 1.0:
			new_w = max(1, int(image.get_width()  * combined))
			new_h = max(1, int(image.get_height() * combined))
			image = pygame.transform.smoothscale(image, (new_w, new_h))

		return image

	def _build_fallback_surface(self):
		"""Bolinha azul proporcional ao MAP_SCALE, com brilho."""
		size   = max(16, int(_FALLBACK_SIZE * self.scale))
		surf   = pygame.Surface((size, size), pygame.SRCALPHA)
		center = (size // 2, size // 2)
		radius = max(6, size // 2 - 2)
		pygame.draw.circle(surf, self.FALLBACK_COLOR,   center, radius)
		pygame.draw.circle(surf, self.FALLBACK_OUTLINE, center, radius, max(1, radius // 8))
		# Brilho
		pygame.draw.circle(surf, (190, 225, 255),
		                   (center[0] - radius // 3, center[1] - radius // 3),
		                   max(2, radius // 4))
		return surf

	def _slice_frame(self, sheet, left, top, width, height):
		frame = sheet.subsurface(pygame.Rect(left, top, width, height)).copy()
		return frame

	def _build_frames(self, sheet):
		if self._fallback_sheet:
			return {d: [sheet.copy()] for d in self.DIRECTIONS}
		if sheet.get_width() < 4 or sheet.get_height() < 4:
			return {d: [sheet.copy()] for d in self.DIRECTIONS}
		if sheet.get_width() % 4 != 0 or sheet.get_height() % 4 != 0:
			return {d: [sheet.copy()] for d in self.DIRECTIONS}

		frame_map = {d: [] for d in self.DIRECTIONS}
		for row_idx, direction in enumerate(self.DIRECTIONS):
			top = row_idx * self.frame_height
			for col_idx in range(4):
				left = col_idx * self.frame_width
				frame_map[direction].append(
					self._slice_frame(sheet, left, top, self.frame_width, self.frame_height)
				)
		return frame_map

	# ── interface pública ────────────────────────────────────

	def set_direction(self, direction):
		if direction in self.DIRECTIONS:
			self.direction = direction

	def set_moving(self, moving):
		self.moving = moving

	def move(self, dx, dy):
		self.rect.x += dx
		self.rect.y += dy

	def move_with_input(self, horizontal, vertical, dt):
		if horizontal < 0:   self.set_direction("left")
		elif horizontal > 0: self.set_direction("right")
		elif vertical < 0:   self.set_direction("up")
		elif vertical > 0:   self.set_direction("down")
		self.moving  = horizontal != 0 or vertical != 0
		self.rect.x += int(horizontal * self.move_speed * dt)
		self.rect.y += int(vertical   * self.move_speed * dt)

	def update(self, direction=None, moving=None):
		if direction is not None:
			self.set_direction(direction)
		if moving is not None:
			self.set_moving(moving)

		frames = self.frames.get(self.direction, self.frames["down"])
		if not frames:
			return

		now = pygame.time.get_ticks()
		if self.moving and len(frames) > 1:
			if now - self.last_update >= self.animation_speed:
				self.frame_index = (self.frame_index + 1) % len(frames)
				self.last_update = now
		else:
			self.frame_index = 0

		self.image = frames[self.frame_index]