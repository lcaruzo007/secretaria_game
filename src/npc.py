import os
import random
import math
import pygame


try:
	from src import settings
except ImportError:
	import settings


# Cache de sprites de imagem já carregados, por (nome, tamanho_px) -> Surface
_SPRITE_CACHE = {}


class GridPath:
	"""
	Pathfinding em grid usando BFS (busca em largura).
	Permite que os NPCs desviem de móveis/paredes em vez de andar em
	linha reta e travar contra o primeiro obstáculo no caminho.
	"""

	def __init__(self, solid_tiles, col_min, col_max, row_min, row_max,
	             tile_px, map_ofs_x, map_ofs_y, map_scale):
		self.solid = solid_tiles  # set de (col, row) sólidos
		self.col_min, self.col_max = col_min, col_max
		self.row_min, self.row_max = row_min, row_max
		self.tile_px = tile_px
		self.ofs_x, self.ofs_y = map_ofs_x, map_ofs_y
		self.scale = map_scale

	def world_to_tile(self, x, y):
		col = int((x - self.ofs_x) / (self.tile_px * self.scale))
		row = int((y - self.ofs_y) / (self.tile_px * self.scale))
		return col, row

	def tile_to_world(self, col, row):
		ox = col * self.tile_px + self.tile_px // 2
		oy = row * self.tile_px + self.tile_px // 2
		return int(ox * self.scale + self.ofs_x), int(oy * self.scale + self.ofs_y)

	def is_walkable(self, col, row):
		if col < self.col_min or col > self.col_max or row < self.row_min or row > self.row_max:
			return False
		return (col, row) not in self.solid

	def _nearest_walkable(self, tile, max_tiles=200):
		"""BFS auxiliar: acha o tile caminhável mais próximo de `tile`."""
		seen = {tile}
		frontier = [tile]
		while frontier:
			nxt_frontier = []
			for cx, cy in frontier:
				if self.is_walkable(cx, cy):
					return (cx, cy)
				for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
					n = (cx + dx, cy + dy)
					if n not in seen:
						seen.add(n)
						nxt_frontier.append(n)
			frontier = nxt_frontier
			if len(seen) > max_tiles:
				break
		return None

	def find_path(self, start_xy, target_xy, max_nodes=4000):
		"""Retorna lista de waypoints (x, y) em pixels de tela do start até o target, ou None."""
		start = self.world_to_tile(*start_xy)
		goal = self.world_to_tile(*target_xy)

		if not self.is_walkable(*goal):
			nearest = self._nearest_walkable(goal)
			if nearest is None:
				return None
			goal = nearest

		if start == goal:
			return []

		frontier = [start]
		came_from = {start: None}
		visited = 0
		found = False

		while frontier:
			nxt_frontier = []
			for current in frontier:
				if current == goal:
					found = True
					break
				cx, cy = current
				for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
					n = (cx + dx, cy + dy)
					if n in came_from or not self.is_walkable(*n):
						continue
					came_from[n] = current
					nxt_frontier.append(n)
					visited += 1
			if found or visited > max_nodes:
				break
			frontier = nxt_frontier

		if goal not in came_from:
			return None

		# Reconstrói o caminho de trás pra frente
		tiles = []
		node = goal
		while node is not None:
			tiles.append(node)
			node = came_from[node]
		tiles.reverse()

		return [self.tile_to_world(c, r) for c, r in tiles[1:]]


_DIRECTIONS = ("down", "left", "right", "up")  # linha 1=down, 2=left, 3=right, 4=up


def _load_png(path):
	"""Carrega um PNG do disco, convertendo pra alpha quando possível."""
	img = pygame.image.load(path)
	if pygame.display.get_init() and pygame.display.get_surface() is not None:
		img = img.convert_alpha()
	return img


def _find_named_sprite(npc_dir, png_files):
	"""
	Procura, dentro da pasta do NPC, um arquivo PNG cujo nome (sem extensão)
	seja igual ao nome da própria pasta — ex: assets/npcs/ASCOM/ASCOM.png.

	Quando esse arquivo existe, ele é a ÚNICA imagem usada como sprite do
	NPC: qualquer outro PNG na pasta (rowX_colY.png, sobras de recortes
	antigos, variações, etc.) é ignorado. Retorna o Surface carregado ou
	None se não existir um arquivo com esse nome.
	"""
	folder_name = os.path.basename(npc_dir)
	match = next(
		(f for f in png_files if os.path.splitext(f)[0].lower() == folder_name.lower()),
		None
	)
	if match is None:
		return None
	return _load_png(os.path.join(npc_dir, match))


def _load_npc_frames_raw(nome):
	"""
	Carrega os frames de animação do NPC.

	Prioridade:
	  1) Um PNG com o MESMO NOME da pasta (ex: ASCOM/ASCOM.png) — se existir,
	     é usado como sprite único e estático (mesma imagem nas 4 direções),
	     e qualquer outro arquivo na pasta é ignorado.
	  2) Arquivos rowX_colY.png (spritesheet fatiado em grid, com animação
	     por direção).

	Tolerante a pastas incompletas: linhas/colunas faltando usam o frame
	disponível mais próximo como substituto.
	Retorna dict {"down": [Surface,...], "left": [...], ...} ou None.
	"""
	npc_dir = os.path.join(settings.ASSETS_DIR, "npcs", nome.upper())
	if not os.path.exists(npc_dir):
		return None

	png_files = [f for f in os.listdir(npc_dir) if f.endswith('.png')]
	if not png_files:
		return None

	# 1) Prioridade máxima: PNG com o nome da própria pasta.
	named_sprite = _find_named_sprite(npc_dir, png_files)
	if named_sprite is not None:
		return {d: [named_sprite] for d in _DIRECTIONS}

	# 2) Sem arquivo "de nome próprio": tenta o formato rowX_colY.png
	available = set()
	max_row, max_col = 0, 0
	for fname in png_files:
		if fname.startswith('row') and '_col' in fname:
			try:
				parts = fname.replace('row', '').replace('_col', ' ').replace('.png', '')
				row, col = map(int, parts.split())
				available.add((row, col))
				max_row = max(max_row, row)
				max_col = max(max_col, col)
			except:
				pass

	if not available:
		return None

	def _frame_path(row, col):
		return os.path.join(npc_dir, f"row{row}_col{col}.png")

	rows_with_data = sorted({r for r, c in available})
	frame_map = {}

	for row in range(1, max_row + 1):
		if row > len(_DIRECTIONS):
			break
		direction = _DIRECTIONS[row - 1]

		# IMPORTANTE: se um frame (rowX_colY.png) estiver faltando, repetimos
		# o último frame válido da MESMA linha/direção. Nunca pegamos frame
		# de outra linha (outra direção) — isso era o que causava o sprite
		# "trocando" pra outra pose no meio da animação.
		frames = []
		last_good = None
		if row in rows_with_data:
			for col in range(1, max_col + 1):
				path = _frame_path(row, col)
				if os.path.exists(path):
					img = _load_png(path)
					last_good = img
				else:
					img = last_good  # repete o último frame válido da própria direção
				if img is not None:
					frames.append(img)

		frame_map[direction] = frames

	# Garante que toda direção tenha ao menos 1 frame (usa outra direção como fallback)
	any_frames = next((v for v in frame_map.values() if v), None)
	if not any_frames:
		return None
	for d in _DIRECTIONS:
		if not frame_map.get(d):
			frame_map[d] = any_frames

	return frame_map


# Paleta de cores pastel usada no círculo de fundo dos NPCs
_PASTEL_PALETTE = [
	(255, 209, 220),  # rosa pastel
	(255, 229, 180),  # pêssego pastel
	(253, 253, 150),  # amarelo pastel
	(197, 225, 165),  # verde pastel
	(179, 229, 252),  # azul claro pastel
	(197, 202, 233),  # lavanda pastel
	(230, 190, 230),  # lilás pastel
	(255, 204, 188),  # coral pastel
]


def _pastel_color_for(nome):
	"""Escolhe uma cor pastel de forma determinística a partir do nome do NPC
	(mesmo NPC sempre recebe a mesma cor entre execuções)."""
	idx = sum(ord(c) for c in nome) % len(_PASTEL_PALETTE)
	return _PASTEL_PALETTE[idx]


def _load_npc_sprite(nome, diameter_px):
	"""
	Carrega e escala (por frame individual) os sprites de animação do NPC.
	Primeiro tenta a pasta de frames (com prioridade pro PNG de nome igual
	à pasta — ver `_load_npc_frames_raw`); se não achar nada, tenta um
	único arquivo player.png (fatiado em grid 4x4 tradicional).
	Retorna dict {"down": [Surface,...], ...} já escalado, ou None.
	"""
	cache_key = (nome, diameter_px)
	if cache_key in _SPRITE_CACHE:
		return _SPRITE_CACHE[cache_key]

	frame_map = _load_npc_frames_raw(nome)

	# Fallback: arquivo único player.png em grid 4x4 (formato legado)
	if frame_map is None:
		search_dir = os.path.join(settings.ASSETS_DIR, "npcs", nome.upper())
		sheet = None
		for ext in [".png", ".jpg", ".jpeg"]:
			path = os.path.join(search_dir, f"player{ext}")
			if os.path.exists(path):
				sheet = pygame.image.load(path)
				if pygame.display.get_init() and pygame.display.get_surface() is not None:
					sheet = sheet.convert_alpha()
				break
		if sheet is not None and sheet.get_width() % 4 == 0 and sheet.get_height() % 4 == 0:
			fw, fh = sheet.get_width() // 4, sheet.get_height() // 4
			frame_map = {}
			for row_idx, direction in enumerate(_DIRECTIONS):
				frame_map[direction] = [
					sheet.subsurface(pygame.Rect(c * fw, row_idx * fh, fw, fh)).copy()
					for c in range(4)
				]
		elif sheet is not None:
			frame_map = {d: [sheet] for d in _DIRECTIONS}

	if frame_map is None:
		return None

	# Escala cada frame individualmente para diameter_px de altura.
	# (O círculo de alcance NÃO é desenhado aqui — ele é desenhado à parte,
	# em NPC.draw(), pra não inflar o rect de colisão do sprite.)
	scaled = {}
	for direction, frames in frame_map.items():
		scaled_frames = []
		for img in frames:
			scale = diameter_px / img.get_height()
			new_w = max(1, int(img.get_width() * scale))
			new_h = max(1, diameter_px)
			scaled_frames.append(pygame.transform.smoothscale(img, (new_w, new_h)))
		scaled[direction] = scaled_frames

	_SPRITE_CACHE[cache_key] = scaled
	return scaled


class NPC(pygame.sprite.Sprite):
	"""Personagem não-jogável (NPC) com sprite animado, movimento e diálogo."""

	DIRECTIONS = ("down", "left", "right", "up")
	FALLBACK_COLOR = (200, 100, 100)
	FALLBACK_OUTLINE = (255, 255, 255)

	def __init__(self, x, y, nome, frases, intercept_radius=80, patrol_speed=150, 
	             collision_rects=None, building_bounds=None, diameter_px=48,
	             sprite_folder=None, pathfinder=None, free_tiles=None):
		"""
		Args:
			x, y: posição inicial em pixels de tela
			nome: nome de exibição do NPC (ex: "RH", "Financeiro", "Prof.MT")
			frases: lista de strings de diálogo
			intercept_radius: distância em pixels para interceptar player
			patrol_speed: velocidade de patrulha em px/s (default: 150, antes era 80)
			collision_rects: lista de pygame.Rect para colisão (checagem de segurança)
			building_bounds: pygame.Rect dos limites do prédio (fallback sem pathfinder)
			diameter_px: tamanho do sprite em pixels
			sprite_folder: nome real da pasta em assets/npcs/ (se diferente de `nome`)
			pathfinder: instância de GridPath para calcular rotas via BFS
			free_tiles: lista de (x, y) de tiles livres para escolher alvos de patrulha
		"""
		super().__init__()
		self.nome = nome
		self.x = float(x)
		self.y = float(y)
		self.frases = frases
		self.intercept_radius = intercept_radius
		self.patrol_speed = patrol_speed
		self.collision_rects = collision_rects or []
		self.building_bounds = building_bounds
		self.diameter_px = diameter_px
		self.direction = "down"
		self.moving = False
		self.frame_index = 0
		self.last_update = 0
		self.animation_speed = 80  # ms entre frames (reduzido de 100 para fluir melhor com velocidade maior)

		# Cor pastel do círculo de alcance (fixa por NPC, baseada no nome)
		self.circle_color = _pastel_color_for(nome)

		# Pathfinding (BFS em grid) — evita que o NPC trave em móveis
		self.pathfinder = pathfinder
		self.free_tiles = free_tiles or []
		self.path = []  # fila de waypoints (x, y) em coordenadas de tela
		# Stagger inicial aleatório (negativo) no timer de "travado": evita que
		# todos os NPCs recalculem rota no mesmo frame, o que causava
		# "ondas" sincronizadas de recálculo e piorava os engarrafamentos.
		self._stuck_accum = -random.uniform(0.0, 0.3)
		self._stuck_check_x = self.x
		self._stuck_check_y = self.y
		self._stuck_strikes = 0  # nº de travamentos consecutivos sem progresso
		self.npc_separation = 46  # px mínimos entre NPCs (antes 32 — cede espaço mais cedo)
		self._last_random_move = 0.0  # timestamp do último movimento aleatório
		self._dir_waypoint = None  # último waypoint usado pra calcular direção

		# Estado do "empurrão de escape" (_nudge_free): em vez de teleportar
		# pra posição corrigida, desliza suavemente até lá em ~0.15s — assim
		# não parece um pulo instantâneo, em nenhum FPS.
		self._escape_remaining_x = 0.0
		self._escape_remaining_y = 0.0
		self._escape_timer = 0.0

		# Prioridade pra desempate em deadlocks mútuos (dois NPCs se
		# bloqueando um ao outro numa porta estreita): o de prioridade
		# menor cede espaço, o de prioridade maior segue em frente.
		# Assim eles não ficam os dois "cedendo" pro lado errado pra sempre.
		self.priority = id(self)

		# Largura da hitbox de colisão, limitada a menos que um tile, pra
		# garantir que o NPC realmente cabe passando por portas de 1 tile.
		self._hitbox_w_cap = None
		if pathfinder is not None:
			tile_scr = pathfinder.tile_px * pathfinder.scale
			self._hitbox_w_cap = max(6, int(tile_scr * 0.6))

		# Carrega frames de animação (usa sprite_folder se fornecido, senão o próprio nome)
		self.frames = _load_npc_sprite(sprite_folder or nome, diameter_px)
		if self.frames is None:
			fallback = self._build_fallback_sprite()
			self.frames = {d: [fallback] for d in self.DIRECTIONS}

		self.image = self.frames[self.direction][0]
		self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

		# Movimento e comportamento
		self.target_x = None
		self.target_y = None
		self.cooldown = 0.12  # tempo em segundos antes de poder interceptar novamente

	def _build_fallback_sprite(self):
		"""Cria círculo com outline como fallback."""
		size = self.diameter_px
		surf = pygame.Surface((size, size), pygame.SRCALPHA)
		center = (size // 2, size // 2)
		radius = max(6, size // 2 - 2)
		pygame.draw.circle(surf, self.FALLBACK_COLOR, center, radius)
		pygame.draw.circle(surf, self.FALLBACK_OUTLINE, center, radius, max(1, radius // 8))
		return surf

	def get_phrase(self, phrase_index):
		"""Retorna frase de diálogo (rotaciona)."""
		if not self.frases:
			return "..."
		return self.frases[phrase_index % len(self.frases)]

	def intercepts(self, player_rect):
		"""Retorna True se o NPC está próximo do player."""
		if self.cooldown > 0:
			return False
		dx = self.rect.centerx - player_rect.centerx
		dy = self.rect.centery - player_rect.centery
		dist_sq = dx * dx + dy * dy
		return dist_sq < (self.intercept_radius ** 2)

	def draw_radius(self, surface):
		"""Desenha o círculo pastel da área de alcance (intercept_radius),
		preenchido e semi-transparente, com contorno."""
		radius = self.intercept_radius
		center = (int(self.rect.centerx), int(self.rect.centery))

		circle_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
		fill_color = (*self.circle_color, 90)  # preenchimento suave
		pygame.draw.circle(circle_surf, fill_color, (radius, radius), radius)

		outline_color = tuple(max(0, c - 45) for c in self.circle_color) + (255,)
		pygame.draw.circle(circle_surf, outline_color, (radius, radius), radius, 2)

		surface.blit(circle_surf, (center[0] - radius, center[1] - radius))

	def draw(self, surface):
		"""Desenha o NPC completo: círculo pastel da área de alcance por
		trás, e o sprite animado por cima. Use isso no lugar de
		`surface.blit(npc.image, npc.rect)` no loop principal do jogo."""
		self.draw_radius(surface)
		surface.blit(self.image, self.rect)

	def _pick_new_target(self, others=None):
		"""Escolhe um novo alvo de patrulha e calcula a rota (BFS) até ele.
		Tenta até 30 vezes. Se falhar, usa fallback de movimento aleatório.

		Evita, quando possível, escolher um alvo perto de onde outro NPC
		já está — sem isso, com vários NPCs sorteando alvo livremente, é
		questão de estatística vários acabarem convergindo pro mesmo
		cantinho e formando bando."""
		self.path = []
		others = others or []
		# Raio mínimo (em px) que um alvo deve manter de outros NPCs nas
		# primeiras tentativas de sorteio.
		_MIN_TARGET_SEP = 140

		if self.pathfinder and self.free_tiles:
			# Tenta MUITO mais vezes para garantir que acha uma rota (30 tentativas)
			for attempt in range(30):
				tx, ty = random.choice(self.free_tiles)
				# Nas primeiras ~2/3 das tentativas, pula alvos colados em
				# outro NPC. Nas últimas tentativas relaxa a exigência pra
				# não ficar sem alvo nenhum (ex: mapa pequeno/lotado).
				if others and attempt < 20:
					perto_de_outro = any(
						(tx - o.x) ** 2 + (ty - o.y) ** 2 < _MIN_TARGET_SEP ** 2
						for o in others
					)
					if perto_de_outro:
						continue
				route = self.pathfinder.find_path((self.x, self.y), (tx, ty))
				if route:
					self.path = route
					self.target_x, self.target_y = tx, ty
					return

			# Se AINDA não achou rota em 30 tentativas: fallback para movimento aleatório
			# Escolhe um ponto aleatório perto do NPC (raio de 60-100 px)
			angle = random.uniform(0, 2 * math.pi)
			dist = random.uniform(60, 100)
			tx = int(self.x + dist * math.cos(angle))
			ty = int(self.y + dist * math.sin(angle))
			# Limita ao mapa/prédio
			if self.building_bounds:
				tx = max(self.building_bounds.left, min(self.building_bounds.right, tx))
				ty = max(self.building_bounds.top, min(self.building_bounds.bottom, ty))
			self.path = [(tx, ty)]
			self.target_x, self.target_y = tx, ty
			return

		# Fallback sem pathfinder: comportamento antigo (linha reta dentro do prédio)
		if self.building_bounds:
			self.target_x = random.randint(
				int(self.building_bounds.left + 50),
				int(self.building_bounds.right - 50)
			)
			self.target_y = random.randint(
				int(self.building_bounds.top + 50),
				int(self.building_bounds.bottom - 50)
			)
			self.path = [(self.target_x, self.target_y)]

	def _nudge_free(self):
		"""
		Empurrão pequeno e aleatório pra sair de um deadlock persistente
		(ex: vários NPCs travados mutuamente numa porta estreita, onde
		simplesmente recalcular a rota não resolve porque o novo alvo
		também passa pelo mesmo gargalo). Tenta algumas direções até achar
		uma que não bata em parede/móvel; se nenhuma servir, não faz nada.
		"""
		for _ in range(8):
			angle = random.uniform(0, 2 * math.pi)
			dist = random.uniform(30, 55)  # nudge visível, mas sem parecer teleporte
			nx = self.x + dist * math.cos(angle)
			ny = self.y + dist * math.sin(angle)
			if self.collision_rects:
				w = max(6, int(self.rect.width * 0.5))
				if self._hitbox_w_cap is not None:
					w = min(w, self._hitbox_w_cap)
				h = max(6, int(self.rect.height * 0.35))
				test_rect = pygame.Rect(0, 0, w, h)
				test_rect.midbottom = (int(nx), int(ny + self.rect.height / 2))
				if any(test_rect.colliderect(cr) for cr in self.collision_rects):
					continue
			# Em vez de "self.x, self.y = nx, ny" (teleporte instantâneo),
			# guarda a distância a percorrer e desliza até lá em update().
			self._escape_remaining_x = nx - self.x
			self._escape_remaining_y = ny - self.y
			self._escape_timer = 0.15
			return

	def _check_stuck(self, dt, intending_to_move):
		"""
		Detecta oscilação/travamento: se o NPC deveria estar andando mas
		mal se moveu no intervalo, descarta a rota atual para forçar recálculo.
		Isso evita deadlocks (ex: dois NPCs travados um no caminho do outro).
		Intervalo reduzido para 0.3s (era 0.6s) para reagir mais rápido.

		Se o NPC travar várias vezes SEGUIDAS mesmo depois de recalcular rota
		(sinal de deadlock persistente num gargalo, não só um encontro
		passageiro), aplica um pequeno empurrão aleatório pra quebrar o ciclo.
		"""
		self._stuck_accum += dt
		if self._stuck_accum < 0.3:  # Reduzido de 0.6 para 0.3
			return
		moved = math.hypot(self.x - self._stuck_check_x, self.y - self._stuck_check_y)
		if intending_to_move and moved < 8:  # Aumentado threshold de 4 para 8 (mais sensível)
			self.path = []
			self.target_x = self.target_y = None
			self._stuck_strikes += 1
			if self._stuck_strikes >= 3:
				self._nudge_free()
				self._stuck_strikes = 0
		else:
			self._stuck_strikes = 0
		self._stuck_check_x, self._stuck_check_y = self.x, self.y
		self._stuck_accum = 0.0

	def update(self, dt, others=None):
			"""
			Atualiza posição, animação e comportamento do NPC.
			
			Args:
				dt: delta time em segundos
				others: lista de outros NPCs para evitar colisão
			"""
			others = others or []
			self.cooldown = max(0, self.cooldown - dt)

			# Deslizamento do empurrão de escape em andamento? Move uma fração
			# proporcional ao tempo restante (frame-rate independente) e pula
			# a movimentação normal de patrulha nesse frame.
			if self._escape_timer > 0:
				frac = min(1.0, dt / self._escape_timer)
				step_x = self._escape_remaining_x * frac
				step_y = self._escape_remaining_y * frac
				self.x += step_x
				self.y += step_y
				self._escape_remaining_x -= step_x
				self._escape_remaining_y -= step_y
				self._escape_timer = max(0.0, self._escape_timer - dt)
				self.moving = True
			else:
				# Sem rota ativa? Escolhe novo alvo e calcula caminho via BFS
				if not self.path:
					self._pick_new_target(others)

				self.moving = False
			intending_to_move = bool(self.path)

			if self.path:
				wx, wy = self.path[0]
				dx = wx - self.x
				dy = wy - self.y
				dist_sq = dx * dx + dy * dy

				# Chegou no waypoint atual: avança para o próximo
				# Tolerância aumentada de 6 para 12 para evitar oscilação
				if dist_sq < (12 ** 2):
					self.path.pop(0)
				else:
					dist = math.sqrt(dist_sq)
					vx = (dx / dist) * self.patrol_speed
					vy = (dy / dist) * self.patrol_speed

					new_x = self.x + vx * dt
					new_y = self.y + vy * dt

					# Direção calculada a partir do vetor até o waypoint ATUAL
					if (wx, wy) != self._dir_waypoint:
						if abs(dx) > abs(dy):
							self.direction = "right" if dx > 0 else "left"
						else:
							self.direction = "down" if dy > 0 else "up"
						self._dir_waypoint = (wx, wy)

					# Separação suave entre NPCs (Lógica existente)
					blocked_by_npc = False
					for other in others:
						if other is self:
							continue
						if (other.x - new_x) ** 2 + (other.y - new_y) ** 2 < (self.npc_separation ** 2):
							if other.priority > self.priority:
								blocked_by_npc = True
								break

					# Checagem de segurança contra colisão do mapa
					can_move = True
					w = max(6, int(self.rect.width * 0.5))
					if self._hitbox_w_cap is not None:
						w = min(w, self._hitbox_w_cap)
					h = max(6, int(self.rect.height * 0.35))
					if self.collision_rects:
						test_rect = pygame.Rect(0, 0, w, h)
						test_rect.midbottom = (int(new_x), int(new_y + self.rect.height / 2))
						can_move = not any(test_rect.colliderect(cr) for cr in self.collision_rects)

					# Aplica o movimento
					if can_move:
						if not blocked_by_npc:
							self.x = new_x
							self.y = new_y
							self.moving = True
						else:
							# Bloqueado por outro NPC: tenta se mover perpendicularmente
							perp_x = -vy / dist * self.patrol_speed * 0.5 * dt
							perp_y = vx / dist * self.patrol_speed * 0.5 * dt
							test_rect2 = pygame.Rect(0, 0, w, h)
							test_rect2.midbottom = (int(self.x + perp_x), int(self.y + perp_y + self.rect.height / 2))
							if not any(test_rect2.colliderect(cr) for cr in self.collision_rects):
								self.x += perp_x
								self.y += perp_y
								self.moving = True

				# ── LÓGICA DE COLISÃO ENTRE NPCS (Evitar Sobreposição) ──
			if others:
				distancia_minima = 64  # antes 40 — bando formado precisa de empurrão de verdade
				push_x, push_y = 0.0, 0.0

				for outro in others:
					if outro is self:
						continue # Ignora a colisão consigo mesmo

					# Usamos self.x e self.y, que é onde a posição real está guardada!
					dx = self.x - outro.x
					dy = self.y - outro.y

					dist = math.hypot(dx, dy)

					if 0 < dist < distancia_minima:
						sobreposicao = distancia_minima - dist
						nx = dx / dist
						ny = dy / dist
						# Acumula a correção de TODOS os vizinhos sobrepostos antes
						# de aplicar — se não, com vários grudados de uma vez a soma
						# das correções "teleportava" o NPC pra longe num frame só.
						push_x += nx * sobreposicao
						push_y += ny * sobreposicao

				if push_x or push_y:
					# Limita a correção por segundo (não por frame), pra virar um
					# deslizar suave mesmo com framerate variável ou muita gente
					# sobreposta ao mesmo tempo — nunca um salto instantâneo.
					push_len = math.hypot(push_x, push_y)
					max_push = 180 * dt
					if push_len > max_push:
						escala = max_push / push_len
						push_x *= escala
						push_y *= escala
					self.x += push_x
					self.y += push_y

			# Detecta e resolve travamentos
			self._check_stuck(dt, intending_to_move)

			# Atualiza animação
			frames = self.frames.get(self.direction, self.frames["down"])
			if not frames:
				frames = self.frames["down"]

			now = pygame.time.get_ticks()
			if self.moving and len(frames) > 1:
				if now - self.last_update >= self.animation_speed:
					self.frame_index = (self.frame_index + 1) % len(frames)
					self.last_update = now
			else:
				self.frame_index = 0

			self.image = frames[self.frame_index]
			# Aqui o rect finalmente recebe as posições X e Y corrigidas pela repulsão
			self.rect.center = (int(self.x), int(self.y))