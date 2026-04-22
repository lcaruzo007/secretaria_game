import math
import os

import pygame

try:
	from src import settings
except ImportError:
	import settings


# Paleta de cores por setor — cada NPC tem identidade visual única
NPC_PALETTES = {
	"RH": {
		"skin":    (255, 220, 185),
		"hair":    (60,  35,  10),
		"shirt":   (180, 60,  60),
		"pants":   (60,  60,  90),
		"shoes":   (40,  25,  10),
		"badge":   (220, 180, 50),
		"detail":  (255, 100, 100),
	},
	"Financeiro": {
		"skin":    (255, 210, 170),
		"hair":    (90,  70,  20),
		"shirt":   (30,  120, 60),
		"pants":   (50,  70,  50),
		"shoes":   (35,  25,  10),
		"badge":   (180, 220, 100),
		"detail":  (60,  180, 100),
	},
	"Gabinete": {
		"skin":    (240, 200, 160),
		"hair":    (30,  20,  10),
		"shirt":   (30,  60,  160),
		"pants":   (20,  40,  100),
		"shoes":   (20,  20,  30),
		"badge":   (200, 210, 255),
		"detail":  (100, 140, 255),
	},
	"TI": {
		"skin":    (220, 195, 165),
		"hair":    (50,  50,  50),
		"shirt":   (60,  60,  60),
		"pants":   (40,  40,  40),
		"shoes":   (25,  25,  25),
		"badge":   (80,  220, 200),
		"detail":  (0,   200, 180),
	},
	"ASCOM": {
		"skin":    (255, 225, 195),
		"hair":    (180, 100, 20),
		"shirt":   (160, 30,  140),
		"pants":   (80,  20,  80),
		"shoes":   (50,  20,  50),
		"badge":   (255, 180, 240),
		"detail":  (220, 80,  200),
	},
}

NPC_ACCESSORIES = {
	"RH":         "clipboard",
	"Financeiro": "briefcase",
	"Gabinete":   "tie",
	"TI":         "glasses",
	"ASCOM":      "camera",
}

_DEFAULT_PALETTE = {
	"skin":   (240, 200, 160),
	"hair":   (80,  50,  20),
	"shirt":  (120, 120, 180),
	"pants":  (70,  70,  100),
	"shoes":  (40,  30,  15),
	"badge":  (200, 200, 200),
	"detail": (160, 160, 220),
}


def _draw_pixel_npc(surface, palette, accessory):
	W, H = surface.get_size()
	pw = W / 12.0
	ph = H / 16.0

	def rect(col, row, w=1, h=1, color=None):
		if color is None:
			return
		r = pygame.Rect(int(col * pw), int(row * ph), max(1, int(w * pw)), max(1, int(h * ph)))
		pygame.draw.rect(surface, color, r)

	def circle(cx_col, cy_row, r_px, color):
		pygame.draw.circle(
			surface, color,
			(int(cx_col * pw), int(cy_row * ph)),
			max(1, int(r_px * min(pw, ph)))
		)

	skin    = palette["skin"]
	hair    = palette["hair"]
	shirt   = palette["shirt"]
	pants   = palette["pants"]
	shoes   = palette["shoes"]
	badge   = palette["badge"]
	detail  = palette["detail"]
	shirt_d = tuple(max(0, c - 45) for c in shirt)

	# Sombra no chão
	shadow_surf = pygame.Surface((int(8 * pw), int(2 * ph)), pygame.SRCALPHA)
	pygame.draw.ellipse(shadow_surf, (0, 0, 0, 55), shadow_surf.get_rect())
	surface.blit(shadow_surf, (int(2 * pw), int(14 * ph)))

	# Cabelo
	rect(3, 0, 6, 1,   hair)
	rect(2, 1, 8, 1,   hair)
	rect(2, 2, 1, 1,   hair)
	rect(9, 2, 1, 1,   hair)

	# Rosto
	rect(3, 1, 6, 4,   skin)
	rect(2, 2, 1, 2,   skin)
	rect(9, 2, 1, 2,   skin)

	# Olhos
	rect(4, 3,   1, 1, (40, 25, 10))
	rect(7, 3,   1, 1, (40, 25, 10))
	rect(4, 3, 0.4, 0.4, (255, 255, 255))
	rect(7, 3, 0.4, 0.4, (255, 255, 255))

	# Boca
	rect(5, 5, 2, 0.5, (180, 100, 80))

	# Bochechas
	rect(3,   4, 1, 0.7, (255, 190, 170))
	rect(8,   4, 1, 0.7, (255, 190, 170))

	# Pescoço
	rect(5, 5, 2, 1, skin)

	# Corpo
	rect(2, 6, 8, 5, shirt)
	rect(2, 6, 1, 5, shirt_d)
	rect(9, 6, 1, 5, shirt_d)
	rect(4, 6, 1, 1, (240, 240, 240))
	rect(7, 6, 1, 1, (240, 240, 240))

	# Braços
	rect(0,  6, 2, 4, shirt)
	rect(10, 6, 2, 4, shirt)
	rect(0,  10, 2, 1, skin)
	rect(10, 10, 2, 1, skin)

	# Crachá
	rect(5,   7, 2, 1.5, badge)
	rect(5,   7, 2, 0.3, (200, 200, 200))

	# Calça
	rect(2, 11, 4, 3, pants)
	rect(6, 11, 4, 3, pants)
	rect(5, 11, 2, 3, tuple(max(0, c - 30) for c in pants))

	# Sapatos
	rect(2, 14, 4, 2, shoes)
	rect(6, 14, 4, 2, shoes)
	rect(2, 14, 1, 0.5, tuple(min(255, c + 60) for c in shoes))
	rect(6, 14, 1, 0.5, tuple(min(255, c + 60) for c in shoes))

	# Acessório
	if accessory == "clipboard":
		rect(10, 7, 2,   3,   (200, 175, 130))
		rect(10, 7, 2,   0.4, (120, 90, 50))
		rect(10.2, 7.6, 1.5, 0.3, (80, 80, 80))
		rect(10.2, 8.2, 1.5, 0.3, (80, 80, 80))
		rect(10.2, 8.8, 1.0, 0.3, (80, 80, 80))

	elif accessory == "briefcase":
		rect(0, 8, 2, 2,   (120, 85, 40))
		rect(0.3, 7.5, 1.4, 0.6, (120, 85, 40))
		rect(0.7, 9,   0.6, 0.3, (180, 150, 80))

	elif accessory == "tie":
		rect(5.5, 6.5, 1, 4, detail)
		rect(5.2, 6.5, 1.6, 1, detail)
		rect(5.3, 10, 0.8, 0.5, tuple(max(0, c - 30) for c in detail))

	elif accessory == "glasses":
		rect(3.5, 2.8, 2,   1,   (60, 60, 60))
		rect(6.5, 2.8, 2,   1,   (60, 60, 60))
		rect(5.5, 3.1, 1,   0.3, (60, 60, 60))
		rect(3,   3.1, 0.5, 0.3, (60, 60, 60))
		rect(8.5, 3.1, 0.5, 0.3, (60, 60, 60))
		lente = pygame.Surface((int(2 * pw), int(1 * ph)), pygame.SRCALPHA)
		lente.fill((100, 200, 255, 70))
		surface.blit(lente, (int(3.5 * pw), int(2.8 * ph)))
		surface.blit(lente, (int(6.5 * pw), int(2.8 * ph)))

	elif accessory == "camera":
		rect(9.5, 8, 2.5, 2, (50, 50, 50))
		circle(10.8, 9, 0.7,  (80, 80, 80))
		circle(10.8, 9, 0.35, (30, 30, 30))
		circle(10.8, 9, 0.15, (200, 220, 255))
		rect(10.5, 7.5, 1, 0.5, (50, 50, 50))


def build_npc_sprite(nome, size=64):
	w = int(size * 0.75)
	h = size
	surface = pygame.Surface((w, h), pygame.SRCALPHA)
	palette   = NPC_PALETTES.get(nome, _DEFAULT_PALETTE)
	accessory = NPC_ACCESSORIES.get(nome, None)
	_draw_pixel_npc(surface, palette, accessory)
	return surface


class NPC(pygame.sprite.Sprite):
	FALLBACK_COLOR     = (220, 80, 80)
	FALLBACK_OUTLINE   = (255, 255, 255)
	FALLBACK_HIGHLIGHT = (255, 220, 220)

	def __init__(self, x, y, nome, frases, sprite_name="gabinete.png",
	             scale=1.0, intercept_radius=80, patrol_area=None, patrol_speed=80):
		super().__init__()
		self.nome             = nome
		self.frases           = list(frases)
		self.sprite_name      = sprite_name
		self.scale            = scale
		self.intercept_radius = intercept_radius
		self.patrol_speed     = patrol_speed
		self.patrol_area      = patrol_area.copy() if patrol_area is not None else None
		self._direction_x     = 1
		self._direction_y     = 1

		self.image = self._load_image(sprite_name)
		self.rect  = self.image.get_rect(center=(x, y))
		self._label = self._build_label()

		# Posição em float para movimento suave (evita tremido por arredondamento)
		self._fx = float(self.rect.x)
		self._fy = float(self.rect.y)

	def _load_image(self, sprite_name):
		image_path = os.path.join(settings.IMAGES_DIR, "characters", sprite_name)
		if os.path.exists(image_path):
			image = pygame.image.load(image_path)
			if pygame.display.get_init() and pygame.display.get_surface() is not None:
				image = image.convert_alpha()
			else:
				image = image.copy()
			if self.scale != 1.0:
				new_size = (
					max(1, int(image.get_width()  * self.scale)),
					max(1, int(image.get_height() * self.scale)),
				)
				image = pygame.transform.smoothscale(image, new_size)
			return image

		base_size = max(48, int(64 * self.scale))
		return build_npc_sprite(self.nome, size=base_size)

	def _build_label(self):
		try:
			font = pygame.font.SysFont("Arial", 11, bold=True)
		except Exception:
			return None
		palette = NPC_PALETTES.get(self.nome, _DEFAULT_PALETTE)
		color   = palette["shirt"]
		shadow  = font.render(self.nome, True, (0, 0, 0))
		text    = font.render(self.nome, True, color)
		w = text.get_width() + 2
		h = text.get_height() + 2
		surf = pygame.Surface((w, h), pygame.SRCALPHA)
		surf.blit(shadow, (1, 1))
		surf.blit(text,   (0, 0))
		return surf

	def intercepts(self, player_rect):
		distance = math.hypot(
			self.rect.centerx - player_rect.centerx,
			self.rect.centery - player_rect.centery,
		)
		return distance <= self.intercept_radius

	def get_phrase(self, index=0):
		if not self.frases:
			return ""
		return self.frases[index % len(self.frases)]

	def update(self, dt=0):
		if self.patrol_area is None:
			return

		# Acumula deslocamento em float — evita que int() arredonde para 0 a cada frame
		self._fx += self.patrol_speed * dt * self._direction_x
		self._fy += self.patrol_speed * dt * self._direction_y

		self.rect.x = int(self._fx)
		self.rect.y = int(self._fy)

		if self.rect.left <= self.patrol_area.left:
			self.rect.left    = self.patrol_area.left
			self._fx          = float(self.rect.x)
			self._direction_x = 1
		elif self.rect.right >= self.patrol_area.right:
			self.rect.right   = self.patrol_area.right
			self._fx          = float(self.rect.x)
			self._direction_x = -1

		if self.rect.top <= self.patrol_area.top:
			self.rect.top     = self.patrol_area.top
			self._fy          = float(self.rect.y)
			self._direction_y = 1
		elif self.rect.bottom >= self.patrol_area.bottom:
			self.rect.bottom  = self.patrol_area.bottom
			self._fy          = float(self.rect.y)
			self._direction_y = -1

	def collides_with_player(self, player_rect):
		return self.rect.colliderect(player_rect)

	def draw(self, surface):
		"""Desenha sprite + label de nome abaixo."""
		surface.blit(self.image, self.rect)
		if self._label:
			lx = self.rect.centerx - self._label.get_width() // 2
			ly = self.rect.bottom + 2
			surface.blit(self._label, (lx, ly))
