import math
import os
import random
from collections import deque

import pygame

try:
	from src import settings
except ImportError:
	import settings


# Cache de sprites de imagem já carregados, por (nome, tamanho_px) -> Surface
_SPRITE_CACHE: dict = {}


def _load_npc_sprite(nome, diameter_px):
	"""
	Tenta carregar assets/images/npcs/<nome>.png e escalar para o diâmetro
	desejado. Retorna None se o arquivo não existir (quem chamou deve usar
	o fallback de bolinha).
	"""
	key = (nome, diameter_px)
	if key in _SPRITE_CACHE:
		return _SPRITE_CACHE[key]

	path = os.path.join(settings.IMAGES_DIR, "npcs", f"{nome}.png")
	if not os.path.exists(path):
		_SPRITE_CACHE[key] = None
		return None

	try:
		raw = pygame.image.load(path).convert_alpha()
		scaled = pygame.transform.smoothscale(raw, (diameter_px, diameter_px))
	except Exception as e:
		print(f"Aviso: falha ao carregar sprite de '{nome}' ({path}): {e}")
		scaled = None

	_SPRITE_CACHE[key] = scaled
	return scaled


NPC_COLORS = {
	"RH":           ((220,  80,  80), (160,  20,  20)),
	"Financeiro":   (( 80, 150, 220), ( 20,  70, 160)),
	"Gabinete":     ((220, 180,  50), (160, 120,  10)),
	"TI":           (( 80, 200, 100), ( 20, 130,  50)),
	"ASCOM":        ((200,  80, 200), (130,  20, 140)),
	"Biblioteca":   ((100, 180, 210), ( 30, 100, 140)),
	"Extensao":     ((240, 130,  50), (170,  70,  10)),
	"Prof.EF":      ((100, 210,  80), ( 40, 140,  20)),
	"Prof.PT":      ((240, 160,  80), (170,  90,  10)),
	"Prof.MT":      ((180,  50, 180), (110,  10, 110)),
	"Prof.HT":      ((190, 140,  60), (120,  80,  10)),
	"Prof.GEO":     (( 40, 180, 140), ( 10, 110,  80)),
	"Prof.CIE":     ((100, 200, 240), ( 30, 120, 160)),
}

_MAP_SCALE      = min(settings.WIDTH / 1920, settings.HEIGHT / 1280)
_NPC_RADIUS     = max(6, int(14 * _MAP_SCALE))
_WAYPOINT_REACH = max(14, int(28 * _MAP_SCALE))
_TILE_SCR       = 32 * _MAP_SCALE   # tamanho de um tile em px na tela

_STUCK_THRESHOLD   = 45   # frames sem mover → muda waypoint
_OSCILLATE_WINDOW  = 90   # frames para detectar oscilação
_OSCILLATE_THRESH  = 0.15 # se desvio padrão da posição < X*patrol_bounds, está oscilando


# ── Pathfinding compartilhado (calculado uma vez, reutilizado por todos os NPCs) ──
# Mapa de tiles em coordenadas de tile (col, row), construído a partir dos
# collision_rects passados pelo game.py no espaço de tela.
_SHARED_TILE_ADJ: dict = {}   # (col, row) -> [(col, row), ...]
_TILE_GRID_BUILT = False


def _build_tile_adj(collision_rects, patrol_bounds, tile_scr):
	"""
	Converte collision_rects (espaço de tela) para um grafo de tiles navegáveis.
	Chamado uma vez na criação do primeiro NPC.
	"""
	global _SHARED_TILE_ADJ, _TILE_GRID_BUILT
	if _TILE_GRID_BUILT:
		return

	# Inferir grade de tiles a partir do patrol_bounds e tile_scr
	t = max(1, int(tile_scr))
	col_min = int(patrol_bounds.left  / t)
	col_max = int(patrol_bounds.right / t)
	row_min = int(patrol_bounds.top   / t)
	row_max = int(patrol_bounds.bottom / t)

	# Marcar tiles bloqueados
	blocked = set()
	for rect in collision_rects:
		# Todos os tiles que o rect toca
		c0 = int(rect.left   / t)
		c1 = int(rect.right  / t)
		r0 = int(rect.top    / t)
		r1 = int(rect.bottom / t)
		for c in range(c0, c1 + 1):
			for r in range(r0, r1 + 1):
				blocked.add((c, r))

	# Construir adjacência
	adj = {}
	for c in range(col_min, col_max + 1):
		for r in range(row_min, row_max + 1):
			if (c, r) in blocked:
				continue
			neighbors = []
			for dc, dr in [(1,0),(-1,0),(0,1),(0,-1)]:
				nb = (c + dc, r + dr)
				if nb not in blocked and col_min <= nb[0] <= col_max and row_min <= nb[1] <= row_max:
					neighbors.append(nb)
			adj[(c, r)] = neighbors

	_SHARED_TILE_ADJ = adj
	_TILE_GRID_BUILT = True


def _screen_to_tile(sx, sy, tile_scr):
	t = max(1, int(tile_scr))
	return (int(sx / t), int(sy / t))


def _tile_to_screen_center(col, row, tile_scr):
	t = max(1, int(tile_scr))
	return (col * t + t // 2, row * t + t // 2)


def _bfs_waypoint(start_tile, min_dist_tiles=6, max_dist_tiles=30):
	"""
	Escolhe um waypoint via BFS a partir de start_tile.
	Garante que o destino é alcançável por caminho real,
	e está entre min_dist e max_dist tiles de distância BFS.
	"""
	if not _SHARED_TILE_ADJ:
		return None

	visited = {start_tile: 0}
	q = deque([start_tile])
	candidates = []

	while q:
		u = q.popleft()
		d = visited[u]
		if d > max_dist_tiles:
			break
		if d >= min_dist_tiles:
			candidates.append(u)
		for v in _SHARED_TILE_ADJ.get(u, []):
			if v not in visited:
				visited[v] = d + 1
				q.append(v)

	if not candidates:
		# Relaxar distância mínima
		candidates = [t for t, d in visited.items() if d >= 3]
	if not candidates:
		candidates = list(visited.keys())

	return random.choice(candidates) if candidates else start_tile


class NPC(pygame.sprite.Sprite):

	def __init__(self, x, y, nome, frases, sprite_name="", scale=1.0,
	             intercept_radius=80, patrol_speed=90,
	             collision_rects=None, building_bounds=None):
		super().__init__()
		self.nome             = nome
		self.frases           = list(frases)
		self.intercept_radius = intercept_radius
		self.patrol_speed     = patrol_speed
		self.collision_rects  = list(collision_rects) if collision_rects else []

		if building_bounds is not None:
			self.patrol_bounds = building_bounds
		else:
			_dw = int(1920 * _MAP_SCALE)
			_dh = int(1280 * _MAP_SCALE)
			self.patrol_bounds = pygame.Rect(
				(settings.WIDTH  - _dw) // 2,
				(settings.HEIGHT - _dh) // 2,
				_dw, _dh,
			)

		# Construir grafo de tiles (só faz uma vez)
		_build_tile_adj(self.collision_rects, self.patrol_bounds, _TILE_SCR)

		self._radius = _NPC_RADIUS
		self.image   = self._make_ball_surface()
		self.rect    = self.image.get_rect(center=(x, y))
		self.rect.clamp_ip(self.patrol_bounds)

		self._vel_x = 0.0
		self._vel_y = 0.0

		# Caminho BFS atual (lista de tiles)
		self._path:       list = []
		self._path_idx:   int  = 0
		self._waypoint         = (x, y)   # ponto de tela atual
		self._request_new_path()

		self._stuck_frames     = 0
		self._wall_frames      = 0
		self._wall_mode_frames = 0
		self.cooldown          = 0.0

		self._exact_x = float(x)
		self._exact_y = float(y)

		# Histórico de posição para detectar oscilação
		self._pos_history: list = []

	# ── visual ───────────────────────────────────────────────────────

	def _make_ball_surface(self):
		r    = self._radius
		size = r * 2 + 4

		sprite = _load_npc_sprite(self.nome, size)
		if sprite is not None:
			return sprite

		surf = pygame.Surface((size, size), pygame.SRCALPHA)
		fill_color, border_color = NPC_COLORS.get(self.nome, ((180, 180, 180), (80, 80, 80)))
		cx = cy = size // 2
		pygame.draw.circle(surf, (0, 0, 0, 60),       (cx + 2, cy + 3), r)
		pygame.draw.circle(surf, fill_color,           (cx, cy), r)
		pygame.draw.circle(surf, border_color,         (cx, cy), r, max(1, r // 7))
		pygame.draw.circle(surf, (255, 255, 255, 120),
		                   (cx - max(1, r // 4), cy - max(1, r // 3)), max(2, r // 3))
		try:
			font = pygame.font.SysFont("Arial", max(8, int(14 * _MAP_SCALE)), bold=True)
			txt  = font.render(self.nome[0], True, (255, 255, 255))
			surf.blit(txt, txt.get_rect(center=(cx, cy)))
		except Exception:
			pass
		return surf

	# ── pathfinding ──────────────────────────────────────────────────

	def _request_new_path(self):
		"""Calcula novo caminho BFS para um waypoint aleatório alcançável."""
		start_tile = _screen_to_tile(self.rect.centerx, self.rect.centery, _TILE_SCR)

		dest_tile  = _bfs_waypoint(start_tile, min_dist_tiles=8, max_dist_tiles=35)
		if dest_tile is None or dest_tile == start_tile:
			self._path     = []
			self._path_idx = 0
			self._waypoint = (self.rect.centerx, self.rect.centery)
			return

		# BFS para reconstruir caminho
		path = self._bfs_path(start_tile, dest_tile)
		if path:
			self._path     = path
			self._path_idx = 0
			self._advance_waypoint()
		else:
			self._path     = []
			self._path_idx = 0
			self._waypoint = _tile_to_screen_center(*dest_tile, _TILE_SCR)

		self._stuck_frames     = 0
		self._wall_frames      = 0
		self._wall_mode_frames = 0

	def _bfs_path(self, start, end):
		"""Retorna lista de tiles do caminho BFS de start até end."""
		if start == end:
			return [start]
		prev    = {start: None}
		q       = deque([start])
		found   = False
		while q:
			u = q.popleft()
			if u == end:
				found = True
				break
			for v in _SHARED_TILE_ADJ.get(u, []):
				if v not in prev:
					prev[v] = u
					q.append(v)
		if not found:
			return []
		path = []
		cur  = end
		while cur is not None:
			path.append(cur)
			cur = prev[cur]
		path.reverse()
		return path

	def _advance_waypoint(self):
		"""Move para o próximo tile do caminho."""
		if self._path_idx < len(self._path):
			tile = self._path[self._path_idx]
			self._waypoint = _tile_to_screen_center(*tile, _TILE_SCR)
			self._path_idx += 1
		else:
			self._request_new_path()

	def _aim_at_waypoint(self):
		dx   = self._waypoint[0] - self.rect.centerx
		dy   = self._waypoint[1] - self.rect.centery
		dist = math.hypot(dx, dy) or 1
		self._vel_x = (dx / dist) * self.patrol_speed
		self._vel_y = (dy / dist) * self.patrol_speed

	# ── colisão ──────────────────────────────────────────────────────

	def _check_collision(self, rect):
		return any(rect.colliderect(cr) for cr in self.collision_rects)

	def _try_escape(self, dt):
		"""Varre ângulos em passos de 15° para encontrar direção livre."""
		ang = math.atan2(self._vel_y, self._vel_x)
		for step in range(1, 13):
			for sign in (1, -1):
				candidate = ang + sign * step * (math.pi / 12)
				vx = math.cos(candidate) * self.patrol_speed
				vy = math.sin(candidate) * self.patrol_speed
				probe = self.rect.copy()
				probe.centerx = int(self.rect.centerx + vx * dt * 10)
				probe.centery = int(self.rect.centery + vy * dt * 10)
				probe.clamp_ip(self.patrol_bounds)
				if not self._check_collision(probe):
					self._vel_x = vx
					self._vel_y = vy
					self._wall_mode_frames = max(60, int(_TILE_SCR / (self.patrol_speed * dt) * 1.5))
					return True
		return False

	def _is_oscillating(self):
		"""
		Detecta vai-e-vem: se o desvio padrão da posição nos últimos
		_OSCILLATE_WINDOW frames for menor que o limiar, está preso.
		"""
		if len(self._pos_history) < _OSCILLATE_WINDOW:
			return False
		xs = [p[0] for p in self._pos_history]
		ys = [p[1] for p in self._pos_history]
		mean_x = sum(xs) / len(xs)
		mean_y = sum(ys) / len(ys)
		std_x  = math.sqrt(sum((x - mean_x)**2 for x in xs) / len(xs))
		std_y  = math.sqrt(sum((y - mean_y)**2 for y in ys) / len(ys))
		# Limiar: menos de 1.5 tiles de variação em ambos os eixos
		thresh = _TILE_SCR * 1.5
		return std_x < thresh and std_y < thresh

	# ── update ───────────────────────────────────────────────────────

	def update(self, dt=1/60, others=None):
		if self.cooldown > 0:
			self.cooldown = max(0.0, self.cooldown - dt)

		# Histórico de posição (janela deslizante)
		self._pos_history.append((self.rect.centerx, self.rect.centery))
		if len(self._pos_history) > _OSCILLATE_WINDOW:
			self._pos_history.pop(0)

		# Detectar oscilação → pedir novo caminho imediatamente
		if self._is_oscillating():
			self._pos_history.clear()
			self._request_new_path()

		# Chegou no waypoint atual do caminho → avançar para o próximo tile
		if math.hypot(self._waypoint[0] - self.rect.centerx,
		              self._waypoint[1] - self.rect.centery) <= _WAYPOINT_REACH:
			self._advance_waypoint()

		# Steering — só recalcula fora do modo desvio de parede
		if self._wall_mode_frames <= 0:
			dx   = self._waypoint[0] - self.rect.centerx
			dy   = self._waypoint[1] - self.rect.centery
			dist = math.hypot(dx, dy) or 1
			desired_x = (dx / dist) * self.patrol_speed
			desired_y = (dy / dist) * self.patrol_speed

			# Separação entre NPCs
			if others:
				sep_radius = self._radius * 10
				for other in others:
					odx   = self.rect.centerx - other.rect.centerx
					ody   = self.rect.centery - other.rect.centery
					odist = math.hypot(odx, ody) or 1
					if 0 < odist < sep_radius:
						force      = ((sep_radius - odist) / sep_radius) * self.patrol_speed * 2.0
						desired_x += (odx / odist) * force
						desired_y += (ody / odist) * force

			spd = math.hypot(desired_x, desired_y) or 1
			self._vel_x = (desired_x / spd) * self.patrol_speed
			self._vel_y = (desired_y / spd) * self.patrol_speed
		else:
			self._wall_mode_frames -= 1

		if math.hypot(self._vel_x, self._vel_y) < 1.0:
			self._aim_at_waypoint()
			self._wall_mode_frames = 0

		# ── mover ────────────────────────────────────────────────────
		new_x = self._exact_x + self._vel_x * dt
		new_y = self._exact_y + self._vel_y * dt

		test = self.rect.copy()
		test.centerx = int(new_x)
		test.centery = int(new_y)
		test.clamp_ip(self.patrol_bounds)

		moved = False

		if not self._check_collision(test):
			self.rect.center  = test.center
			self._exact_x     = self.rect.centerx + (new_x - int(new_x))
			self._exact_y     = self.rect.centery + (new_y - int(new_y))
			moved             = True
			self._wall_frames = 0
		else:
			tx = self.rect.copy()
			tx.centerx = int(new_x)
			tx.clamp_ip(self.patrol_bounds)
			ty = self.rect.copy()
			ty.centery = int(new_y)
			ty.clamp_ip(self.patrol_bounds)

			can_x = not self._check_collision(tx)
			can_y = not self._check_collision(ty)

			if can_x:
				self.rect.centerx = tx.centerx
				self.rect.clamp_ip(self.patrol_bounds)
				self._exact_x = self.rect.centerx + (new_x - int(new_x))
				moved = True
			elif can_y:
				self.rect.centery = ty.centery
				self.rect.clamp_ip(self.patrol_bounds)
				self._exact_y = self.rect.centery + (new_y - int(new_y))
				moved = True

			self._wall_frames += 1
			if self._wall_frames >= 8:
				if not self._try_escape(dt):
					self._request_new_path()
				self._wall_frames = 0

		# ── stuck ────────────────────────────────────────────────────
		if not moved:
			self._stuck_frames += 1
			if self._stuck_frames >= _STUCK_THRESHOLD:
				self._request_new_path()
				self._stuck_frames = 0
		else:
			self._stuck_frames = 0

		self.rect.clamp_ip(self.patrol_bounds)

	# ── intercept / frases ───────────────────────────────────────────

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
		r = self.intercept_radius
		s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
		fill, _ = NPC_COLORS.get(self.nome, ((180, 180, 180), (80, 80, 80)))
		pygame.draw.circle(s, (*fill, 22), (r, r), r)
		pygame.draw.circle(s, (*fill, 55), (r, r), r, 1)
		surface.blit(s, (self.rect.centerx - r, self.rect.centery - r))