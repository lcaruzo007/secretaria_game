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

# Pasta dedicada do sprite do player (assets/PLAYER/player.png).
# Se não achar lá, cai pra assets/images/<sprite_name> (comportamento antigo).
_PLAYER_DIR = os.path.join(settings.ASSETS_DIR, "PLAYER")

# Velocidade-base do player (px/s no espaço original) escalada para tela
# O valor 350 era pensado para 1920×1280; na tela 1280×720 fica proporcional
_MOVE_SPEED_DEFAULT = int(270 * _MAP_SCALE)


class Player(pygame.sprite.Sprite):
	DIRECTIONS    = ("down", "left", "right", "up")
	FALLBACK_COLOR   = (70, 140, 255)
	FALLBACK_OUTLINE = (255, 255, 255)

	def __init__(self, x, y, sprite_name="player.png", scale=1.0,
	             animation_speed=120, move_speed=None, diameter_px=48):
		super().__init__()
		self.sprite_name     = sprite_name
		self.animation_speed = animation_speed
		# Se move_speed não for passado explicitamente, usa o valor escalado
		self.move_speed      = move_speed if move_speed is not None else _MOVE_SPEED_DEFAULT
		self.base_move_speed = self.move_speed
		self.direction       = "down"
		self.moving          = False
		self.frame_index     = 0
		self.last_update     = 0
		self.scale           = scale
		# Altura-alvo do sprite em px (mesma lógica usada pros NPCs) —
		# controla o TAMANHO do personagem, independente da resolução
		# original do arquivo player.png
		self.diameter_px     = diameter_px
		self._fallback_sheet = False

		# Boost / dash (ativado apertando espaço)
		self.boost_multiplier      = 2.0   # quão mais rápido fica durante o boost
		self.boost_duration        = 0.25  # segundos de duração do boost
		self.boost_cooldown        = 0.7   # segundos até poder usar de novo
		self._boost_timer          = 0.0
		self._boost_cooldown_timer = 0.0

		self.sheet = self._load_sheet(sprite_name)
		# frame_width/frame_height já ficam definidos dentro de _load_sheet
		# (não redetectamos a partir do sheet escalado — ver comentário lá)
		self.frames = self._build_frames(self.sheet)
		self.image  = self.frames[self.direction][0]
		self.rect   = self.image.get_rect(center=(x, y))

	# ── carregamento do sprite ───────────────────────────────

	def _load_sheet(self, sprite_name):
		# 1ª tentativa: assets/PLAYER/<sprite_name> (pasta dedicada do player)
		image_path = os.path.join(_PLAYER_DIR, sprite_name)
		if not os.path.exists(image_path):
			# 2ª tentativa: assets/images/<sprite_name> (comportamento antigo)
			image_path = os.path.join(settings.IMAGES_DIR, sprite_name)
		if not os.path.exists(image_path):
			self._fallback_sheet = True
			self._is_grid_sheet  = False
			sheet = self._build_fallback_surface()
			self.frame_width, self.frame_height = sheet.get_width(), sheet.get_height()
			return sheet

		image = pygame.image.load(image_path)
		if pygame.display.get_init() and pygame.display.get_surface() is not None:
			image = image.convert_alpha()
		else:
			image = image.copy()

		# IMPORTANTE: decide se é uma spritesheet 4x4 (4 direções x 4 frames)
		# UMA ÚNICA VEZ, olhando pro arquivo ORIGINAL (antes de escalar).
		# Se decidirmos isso de novo depois de escalar, arredondamentos de
		# tamanho podem "por acidente" virar múltiplos de 4 mesmo quando o
		# arquivo é uma imagem única — daí o jogo tenta cortar essa imagem
		# única em 16 pedaços e mostra fatias erradas ao animar.
		self._is_grid_sheet = (image.get_width() % 4 == 0 and image.get_height() % 4 == 0)
		raw_frame_h = (image.get_height() // 4) if self._is_grid_sheet else image.get_height()

		# Escala pra bater com diameter_px de altura (de UM frame), igual
		# à lógica usada pros NPCs — tamanho final previsível.
		target_scale = (self.diameter_px / raw_frame_h) if raw_frame_h else 1.0
		combined = self.scale * target_scale
		if combined != 1.0:
			new_w = max(1, int(image.get_width()  * combined))
			new_h = max(1, int(image.get_height() * combined))
			image = pygame.transform.smoothscale(image, (new_w, new_h))

		if self._is_grid_sheet:
			self.frame_width  = image.get_width()  // 4
			self.frame_height = image.get_height() // 4
		else:
			self.frame_width  = image.get_width()
			self.frame_height = image.get_height()

		return image

	def _build_fallback_surface(self):
		"""Bolinha azul do tamanho de diameter_px, com brilho."""
		size   = max(16, int(self.diameter_px * self.scale))
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
		if self._fallback_sheet or not self._is_grid_sheet:
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

	def trigger_boost(self):
		"""Ativa um boost curto de velocidade (dash). Não faz nada se ainda
		estiver em cooldown. Retorna True se o boost foi ativado."""
		if self._boost_cooldown_timer > 0:
			return False
		self._boost_timer = self.boost_duration
		self._boost_cooldown_timer = self.boost_cooldown
		return True

	def update_boost(self, dt):
		"""Atualiza os timers do boost e ajusta self.move_speed de acordo.
		Chamar uma vez por frame, antes de usar move_speed."""
		if self._boost_timer > 0:
			self._boost_timer = max(0.0, self._boost_timer - dt)
		if self._boost_cooldown_timer > 0:
			self._boost_cooldown_timer = max(0.0, self._boost_cooldown_timer - dt)

		self.move_speed = self.base_move_speed * (
			self.boost_multiplier if self._boost_timer > 0 else 1.0
		)

	@property
	def is_boosting(self):
		return self._boost_timer > 0

	@property
	def boost_ready(self):
		return self._boost_cooldown_timer <= 0

	@property
	def boost_cooldown_ratio(self):
		"""0.0 = acabou de usar o boost, 1.0 = pronto pra usar de novo."""
		if self.boost_cooldown <= 0:
			return 1.0
		ratio = 1.0 - (self._boost_cooldown_timer / self.boost_cooldown)
		return max(0.0, min(1.0, ratio))

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

	def change_sprite(self, new_sprite_name):
		"""Troca a spritesheet do player durante o jogo."""
		self.sprite_name = new_sprite_name
		self._fallback_sheet = False # Reseta o fallback caso o arquivo exista
		
		# Recarrega a nova imagem e refaz o fatiamento dos frames
		self.sheet = self._load_sheet(self.sprite_name)
		self.frames = self._build_frames(self.sheet)
		
		# Atualiza a imagem atual para evitar que ele pisque ou suma
		self.image = self.frames[self.direction][self.frame_index if self.frame_index < len(self.frames[self.direction]) else 0]