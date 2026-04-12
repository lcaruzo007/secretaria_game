import os

import pygame

try:
	from src import settings
except ImportError:
	import settings


class Player(pygame.sprite.Sprite):
	DIRECTIONS = ("down", "left", "right", "up")

	def __init__(self, x, y, sprite_name="player.png", scale=1.0, animation_speed=120, move_speed=220):
		super().__init__()
		self.sprite_name = sprite_name
		self.animation_speed = animation_speed
		self.move_speed = move_speed
		self.direction = "down"
		self.moving = False
		self.frame_index = 0
		self.last_update = 0
		self.scale = scale
		self.sheet = self._load_sheet(sprite_name)
		self.frame_width, self.frame_height = self._detect_frame_size(self.sheet)
		self.frames = self._build_frames(self.sheet)
		self.image = self.frames[self.direction][0]
		self.rect = self.image.get_rect(center=(x, y))

	def _detect_frame_size(self, sheet):
		if sheet.get_width() % 4 == 0 and sheet.get_height() % 4 == 0:
			return sheet.get_width() // 4, sheet.get_height() // 4

		return sheet.get_width(), sheet.get_height()

	def _load_sheet(self, sprite_name):
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

	def _slice_frame(self, sheet, left, top, width, height):
		frame_rect = pygame.Rect(left, top, width, height)
		frame = sheet.subsurface(frame_rect).copy()
		if self.scale != 1.0:
			frame = pygame.transform.smoothscale(frame, (max(1, int(frame.get_width() * self.scale)), max(1, int(frame.get_height() * self.scale))))
		return frame

	def _build_frames(self, sheet):
		if sheet.get_width() < 4 or sheet.get_height() < 4:
			return {direction: [sheet.copy()] for direction in self.DIRECTIONS}

		if sheet.get_width() % 4 != 0 or sheet.get_height() % 4 != 0:
			return {direction: [sheet.copy()] for direction in self.DIRECTIONS}

		frame_map = {direction: [] for direction in self.DIRECTIONS}
		for row_index, direction in enumerate(self.DIRECTIONS):
			top = row_index * self.frame_height
			for column_index in range(4):
				left = column_index * self.frame_width
				frame_map[direction].append(self._slice_frame(sheet, left, top, self.frame_width, self.frame_height))

		return frame_map

	def set_direction(self, direction):
		if direction in self.DIRECTIONS:
			self.direction = direction

	def set_moving(self, moving):
		self.moving = moving

	def move(self, dx, dy):
		self.rect.x += dx
		self.rect.y += dy

	def move_with_input(self, horizontal, vertical, dt):
		if horizontal < 0:
			self.set_direction("left")
		elif horizontal > 0:
			self.set_direction("right")
		elif vertical < 0:
			self.set_direction("up")
		elif vertical > 0:
			self.set_direction("down")

		self.moving = horizontal != 0 or vertical != 0
		self.rect.x += int(horizontal * self.move_speed * dt)
		self.rect.y += int(vertical * self.move_speed * dt)

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
