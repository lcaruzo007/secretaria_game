import os
import json
import math
import random

import pygame

try:
	from src import settings
	from src.player import Player
	from src.npc import NPC
except ImportError:
	import settings
	from player import Player
	from npc import NPC


# ── Dimensões originais do mapa ─────────────────────────────────
MAP_ORIG_W  = 1920
MAP_ORIG_H  = 1280
MAP_TILES_W = 60
MAP_TILES_H = 40
TILE_ORIG   = 32  # px por tile no mapa original

# ── Escala e offset (letterbox) ──────────────────────────────────
MAP_SCALE  = min(settings.WIDTH / MAP_ORIG_W, settings.HEIGHT / MAP_ORIG_H)
MAP_DISP_W = int(MAP_ORIG_W * MAP_SCALE)
MAP_DISP_H = int(MAP_ORIG_H * MAP_SCALE)
MAP_OFS_X  = (settings.WIDTH  - MAP_DISP_W) // 2
MAP_OFS_Y  = (settings.HEIGHT - MAP_DISP_H) // 2
TILE_SCR   = TILE_ORIG * MAP_SCALE

# Bounds do mapa completo na tela
MAP_BOUNDS = pygame.Rect(MAP_OFS_X, MAP_OFS_Y, MAP_DISP_W, MAP_DISP_H)

# ── Interior do prédio (tiles 3-55 cols, 5-35 rows) ─────────────
# Baseado no mapa real: paredes externas em col 3 e col 55, rows 4 e 36
_BLDG_COL_MIN, _BLDG_COL_MAX = 4,  54
_BLDG_ROW_MIN, _BLDG_ROW_MAX = 5,  35

BUILDING_BOUNDS = pygame.Rect(
	int(_BLDG_COL_MIN * TILE_ORIG * MAP_SCALE + MAP_OFS_X),
	int(_BLDG_ROW_MIN * TILE_ORIG * MAP_SCALE + MAP_OFS_Y),
	int((_BLDG_COL_MAX - _BLDG_COL_MIN) * TILE_ORIG * MAP_SCALE),
	int((_BLDG_ROW_MAX - _BLDG_ROW_MIN) * TILE_ORIG * MAP_SCALE),
)


def _tile_screen(col, row):
	"""Centro de um tile em coordenadas de tela."""
	ox = col * TILE_ORIG + TILE_ORIG // 2
	oy = row * TILE_ORIG + TILE_ORIG // 2
	return int(ox * MAP_SCALE + MAP_OFS_X), int(oy * MAP_SCALE + MAP_OFS_Y)


def _tile_rect_screen(col, row, w_tiles=1, h_tiles=1):
	"""pygame.Rect de um bloco de tiles em coordenadas de tela."""
	ox = col * TILE_ORIG
	oy = row * TILE_ORIG
	return pygame.Rect(
		int(ox * MAP_SCALE + MAP_OFS_X),
		int(oy * MAP_SCALE + MAP_OFS_Y),
		int(w_tiles * TILE_ORIG * MAP_SCALE),
		int(h_tiles * TILE_ORIG * MAP_SCALE),
	)


# ── Zonas importantes (corrigidas com base no mapa real) ─────────
# Copa/cozinha: canto inferior esquerdo do prédio (cols 4-17, rows 26-35)
COPA_ZONE            = _tile_rect_screen(4,  26, 13, 10)

# Secretaria: canto inferior direito (cols 40-55, rows 24-35)
SECRETARIA_ZONE      = _tile_rect_screen(40, 24, 15, 12)

# ── Saídas reais do mapa (baseadas nas aberturas nas paredes) ────
# Saída principal: gap no topo - cols 28-31, rows 0-4
SAIDA_PRINCIPAL_ZONE = _tile_rect_screen(28,  0,  4,  5)

# Saída inferior: gap no fundo - cols 9-13, rows 36-39
SAIDA_INFERIOR_ZONE  = _tile_rect_screen(9,  36,  5,  4)

# Saída lateral direita: gap no lado direito - col 55, rows 19-22
SAIDA_LATERAL_ZONE   = _tile_rect_screen(55, 19,  5,  4)

# ── Spawn do player: corredor interno ao lado da entrada (col 30, row 7) ──
# Escolhido porque é logo abaixo do gap da entrada principal (cols 28-31)
# e está claramente dentro do prédio, sem paredes blocando.
_PLAYER_SPAWN = _tile_screen(30, 7)

# ── Dados dos NPCs ────────────────────────────────────────────────
NPC_DATA = [
	{
		"nome": "RH",
		"frases": [
			"Preciso falar sobre seu ponto!",
			"Voce preencheu o formulario de ferias?",
			"Tem uma reuniao hoje as 14h!",
			"Seu contrato precisa de assinatura.",
			"Novo treinamento obrigatorio na sexta!",
			"O beneficio de transporte mudou!",
		],
	},
	{
		"nome": "Financeiro",
		"frases": [
			"O orcamento do setor precisa ser revisto!",
			"Tem uma nota fiscal pra aprovar!",
			"O relatorio mensal esta atrasado!",
			"Precisamos cortar 10% das despesas.",
			"A planilha do DRE precisa de atualizacao.",
			"Auditoria semana que vem — prepara tudo!",
		],
	},
	{
		"nome": "Gabinete",
		"frases": [
			"O diretor quer uma reuniao urgente!",
			"Voce viu o memorando de ontem?",
			"Preciso de uma assinatura do reitor.",
			"Evento institucional na sexta — confirma presenca!",
			"A pauta da reuniao mudou para amanha.",
			"Preciso de um relatorio pra reuniao de hoje!",
		],
	},
	{
		"nome": "TI",
		"frases": [
			"Seu computador precisa de atualizacao!",
			"Mudamos a senha do Wi-Fi institucional.",
			"Tem um chamado aberto no seu nome.",
			"O sistema SUAP vai cair amanha de manha.",
			"Voce fez backup dos seus arquivos?",
			"Novo antivirus instalado — reinicia agora!",
		],
	},
	{
		"nome": "ASCOM",
		"frases": [
			"Posso tirar uma foto pra divulgacao?",
			"Voce pode gravar um depoimento rapido?",
			"Preciso de pauta pra nota de imprensa!",
			"Qual e o tema da semana do setor?",
			"Tem materia sobre o IF no jornal hoje!",
			"Manda um resumo das atividades do mes!",
		],
	},
]


# ── Carregamento do mapa ─────────────────────────────────────────

def _load_map_data():
	search_paths = [
		os.path.join(os.path.dirname(__file__), "..", "assets", "images", "backgrounds", "mapas", "mapa_01.json"),
		os.path.join(os.path.dirname(__file__), "..", "assets", "mapas",       "mapa_01.json"),
		os.path.join(os.path.dirname(__file__), "..", "assets", "data",        "mapa_01.json"),
		os.path.join(os.path.dirname(__file__), "mapa_01.json"),
	]
	for p in search_paths:
		if os.path.exists(p):
			try:
				with open(p, "r", encoding="utf-8") as f:
					data = json.load(f)
				print(f"DEBUG: Mapa carregado de {p}")
				return data
			except Exception as e:
				print(f"Aviso: Erro ao ler {p}: {e}")
	print("Aviso: mapa_01.json não encontrado")
	return None


def _load_collision_rects(map_data):
	"""
	Converte os tiles de colisão do JSON para pygame.Rects no espaço de tela.
	Tile tipo 0 = sólido (bloqueia). Tipo 2 = porta (passa).
	"""
	if not map_data:
		return []
	try:
		mw = map_data.get("w", MAP_TILES_W)
		rects = []
		for entry in map_data.get("collisions", []):
			idx, tip = map(int, entry.split(":"))
			if tip == 2:
				continue  # porta não bloqueia
			col = idx % mw
			row = idx // mw
			rects.append(pygame.Rect(
				int(col * TILE_ORIG * MAP_SCALE + MAP_OFS_X),
				int(row * TILE_ORIG * MAP_SCALE + MAP_OFS_Y),
				max(1, int(TILE_ORIG * MAP_SCALE)),
				max(1, int(TILE_ORIG * MAP_SCALE)),
			))
		print(f"DEBUG: {len(rects)} tiles sólidos | scale={MAP_SCALE:.4f} tile_scr={TILE_SCR:.1f}px")
		return rects
	except Exception as e:
		print(f"Aviso: Erro ao processar colisões: {e}")
		return []


def _build_free_tile_list(map_data):
	"""
	Retorna lista de coordenadas de tela (cx, cy) para o centro de cada tile
	livre DENTRO do interior do prédio (rows 5-35, cols 4-54).
	Não inclui tiles sólidos (tipo 0). Portas (tipo 2) são consideradas livres.
	"""
	if not map_data:
		return []
	mw = map_data.get("w", MAP_TILES_W)
	solid = set()
	for entry in map_data.get("collisions", []):
		idx, tip = map(int, entry.split(":"))
		if tip == 0:
			solid.add((idx % mw, idx // mw))
	# Só tiles sólidos (tipo 0) bloqueiam spawn — portas tipo 2 são passáveis

	positions = []
	for row in range(_BLDG_ROW_MIN, _BLDG_ROW_MAX + 1):
		for col in range(_BLDG_COL_MIN, _BLDG_COL_MAX + 1):
			if (col, row) not in solid:
				positions.append(_tile_screen(col, row))

	print(f"DEBUG: {len(positions)} posições de spawn válidas (tiles livres do prédio)")
	return positions


# ── Objetos do jogo ──────────────────────────────────────────────

class CoffeeBottle(pygame.sprite.Sprite):
	"""Garrafa de café coletável com animação flutuante."""

	def __init__(self, x, y):
		super().__init__()
		path     = os.path.join(settings.IMAGES_DIR, "backgrounds", "cafe.png")
		target_h = max(20, int(64 * MAP_SCALE))
		if os.path.exists(path):
			raw   = pygame.image.load(path).convert_alpha()
			scale = target_h / raw.get_height()
			self.image = pygame.transform.smoothscale(
				raw, (max(1, int(raw.get_width() * scale)), target_h)
			)
		else:
			self.image = pygame.Surface((int(32 * MAP_SCALE), target_h), pygame.SRCALPHA)
			pygame.draw.rect(self.image, (180, 100, 30),
			                 (int(8 * MAP_SCALE), 0, int(16 * MAP_SCALE), target_h),
			                 border_radius=6)

		self.rect      = self.image.get_rect(center=(x, y))
		self.collected = False
		self._base_y   = y
		self._t        = 0.0

	def update(self, dt):
		if not self.collected:
			self._t += dt
			self.rect.centery = int(self._base_y + math.sin(self._t * 2.5) * 5)

	def collect(self):
		self.collected = True
		self.kill()


# ── Classe principal ─────────────────────────────────────────────

class Game:
	def __init__(self):
		pygame.init()
		pygame.display.set_caption(settings.TITLE)
		self.screen  = pygame.display.set_mode((settings.WIDTH, settings.HEIGHT))
		self.clock   = pygame.time.Clock()
		self.running = True
		self.state   = "menu"

		self.font_title    = pygame.font.SysFont("Comic Sans MS", 64, bold=True)
		self.font_subtitle = pygame.font.SysFont("Comic Sans MS", 28)
		self.font_body     = pygame.font.SysFont("Comic Sans MS", 24)
		self.font_small    = pygame.font.SysFont("Comic Sans MS", 20)
		self.font_hud      = pygame.font.SysFont("Comic Sans MS", 22, bold=True)
		self.font_dialogue = pygame.font.SysFont("Comic Sans MS", 21)

		self.logo       = self._load_logo()
		self.background = self._load_background()
		self.best_time_ms = 0

		self._npc_dialogue_timer = 0.0
		self._npc_dialogue_text  = ""
		self._npc_dialogue_name  = ""
		self._paralysis_duration = 2.0
		self._player_paralyzed   = False

		# Mapa e colisões
		self.map_data        = _load_map_data()
		self.collision_rects = _load_collision_rects(self.map_data)
		self.free_tiles      = _build_free_tile_list(self.map_data)

		self._reset_game_state()

	# ── carregamento ────────────────────────────────────────

	def _load_logo(self):
		p = os.path.join(settings.IMAGES_DIR, "backgrounds", "logo.png")
		if not os.path.exists(p):
			return None
		img = pygame.image.load(p).convert_alpha()
		s   = 300 / img.get_width()
		return pygame.transform.smoothscale(img, (int(img.get_width()*s), int(img.get_height()*s)))

	def _load_background(self):
		paths = [
			os.path.join(settings.IMAGES_DIR, "backgrounds", "mapas", "mapa_01.png"),
			os.path.join(settings.IMAGES_DIR, "backgrounds", "cenario.png"),
		]
		for p in paths:
			if os.path.exists(p):
				print(f"DEBUG: Background carregado de {p}")
				try:
					img = pygame.image.load(p).convert()
					return pygame.transform.smoothscale(img, (MAP_DISP_W, MAP_DISP_H))
				except Exception as e:
					print(f"Aviso: Erro ao carregar background {p}: {e}")
		print("Aviso: Nenhum background encontrado")
		return None

	# ── estado ──────────────────────────────────────────────

	def _pick_free_pos(self, exclude_rect=None, zone=None):
		"""
		Retorna posição aleatória de tile livre.
		- Se zone for fornecida, só retorna tiles DENTRO dessa zona.
		- Se exclude_rect for fornecido, evita aquela região.
		"""
		pool = self.free_tiles

		if zone is not None:
			in_zone = [(x, y) for x, y in pool if zone.collidepoint(x, y)]
			if in_zone:
				pool = in_zone

		if exclude_rect and pool:
			filtered = [(x, y) for x, y in pool if not exclude_rect.collidepoint(x, y)]
			if filtered:
				pool = filtered

		return random.choice(pool) if pool else (BUILDING_BOUNDS.centerx, BUILDING_BOUNDS.centery)

	def _reset_game_state(self):
		# Player aparece logo abaixo da entrada principal
		self.player = Player(
			_PLAYER_SPAWN[0], _PLAYER_SPAWN[1],
			sprite_name="bola_verde.png", scale=1.0
		)

		# ── Café spawna em tile livre aleatório do prédio, longe do player ──
		player_zone = pygame.Rect(
			_PLAYER_SPAWN[0] - int(120 * MAP_SCALE),
			_PLAYER_SPAWN[1] - int(120 * MAP_SCALE),
			int(240 * MAP_SCALE), int(240 * MAP_SCALE),
		)
		coffee_x, coffee_y = self._pick_free_pos(exclude_rect=player_zone)
		self.coffee_bottle = CoffeeBottle(coffee_x, coffee_y)
		print(f"DEBUG: Café spawnou em ({coffee_x}, {coffee_y})")

		self.timer_running    = True
		self.timer_start      = pygame.time.get_ticks()
		self.elapsed_ms       = 0
		self.has_coffee       = False
		self.coffee_delivered = False

		# ── NPCs em tiles livres dentro do prédio ──
		# Excluímos a zona de spawn do player para não aparecer em cima
		player_zone = pygame.Rect(
			_PLAYER_SPAWN[0] - int(60 * MAP_SCALE),
			_PLAYER_SPAWN[1] - int(60 * MAP_SCALE),
			int(120 * MAP_SCALE), int(120 * MAP_SCALE),
		)
		self.npcs = []
		for data in NPC_DATA:
			x, y  = self._pick_free_pos(exclude_rect=player_zone)
			speed = random.uniform(60, 100) * MAP_SCALE
			npc   = NPC(x, y,
			            nome=data["nome"],
			            frases=data["frases"],
			            intercept_radius=int(80 * MAP_SCALE),
			            patrol_speed=speed,
			            collision_rects=self.collision_rects,
			            building_bounds=BUILDING_BOUNDS)
			self.npcs.append(npc)

		self._npc_phrase_idx     = {npc.nome: 0 for npc in self.npcs}
		self._npc_dialogue_timer = 0.0
		self._npc_dialogue_text  = ""
		self._npc_dialogue_name  = ""
		self._player_paralyzed   = False

	# ── colisão ─────────────────────────────────────────────

	def _check_collision(self, rect):
		return any(rect.colliderect(cr) for cr in self.collision_rects)

	def _apply_player_movement(self, dx_px, dy_px):
		new_x = self.player.rect.centerx + int(dx_px)
		new_y = self.player.rect.centery + int(dy_px)

		# Clamp dentro do mapa completo (permite usar as saídas)
		test = self.player.rect.copy()
		test.centerx = new_x
		test.centery = new_y
		test.clamp_ip(MAP_BOUNDS)

		if not self._check_collision(test):
			self.player.rect.centerx = test.centerx
			self.player.rect.centery = test.centery
		else:
			# Deslizamento X
			tx = self.player.rect.copy()
			tx.centerx = new_x
			tx.clamp_ip(MAP_BOUNDS)
			if not self._check_collision(tx):
				self.player.rect.centerx = tx.centerx
			else:
				# Deslizamento Y
				ty = self.player.rect.copy()
				ty.centery = new_y
				ty.clamp_ip(MAP_BOUNDS)
				if not self._check_collision(ty):
					self.player.rect.centery = ty.centery

	# ── utilitários de desenho ───────────────────────────────

	def _draw_centered_text(self, text, font, color, y):
		s = font.render(text, True, color)
		self.screen.blit(s, s.get_rect(center=(settings.WIDTH // 2, y)))

	def _draw_rounded_box(self, rect, bg_color, border_color=None, radius=12, alpha=220):
		surf   = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
		r, g, b = bg_color
		pygame.draw.rect(surf, (r, g, b, alpha), surf.get_rect(), border_radius=radius)
		self.screen.blit(surf, rect.topleft)
		if border_color:
			pygame.draw.rect(self.screen, border_color, rect, width=2, border_radius=radius)

	def _format_time(self, ms):
		total_s = ms // 1000
		centis  = (ms % 1000) // 10
		m, s    = total_s // 60, total_s % 60
		return f"{m}:{s:02d}.{centis:02d}" if m else f"{s:02d}.{centis:02d}s"

	# ── menu ────────────────────────────────────────────────

	def draw_menu(self):
		self.screen.fill(settings.BACKGROUND_COLOR)
		pygame.draw.circle(self.screen, settings.ACCENT_COLOR,     (100, 100),                  50)
		pygame.draw.circle(self.screen, settings.SECONDARY_COLOR,  (settings.WIDTH - 120, 100), 70)

		self._draw_centered_text(settings.TITLE, self.font_title, settings.PRIMARY_DARK, 50)
		self._draw_centered_text("Busque o café na Copa e saia do prédio!",
		                         self.font_subtitle, (120, 90, 60), 105)

		cw, ch = 860, 520
		card   = pygame.Rect(0, 0, cw, ch)
		card.center = (settings.WIDTH // 2, settings.HEIGHT // 2 + 26)
		sh = pygame.Surface((cw + 20, ch + 20), pygame.SRCALPHA)
		pygame.draw.rect(sh, (0, 0, 0, 40), sh.get_rect(), border_radius=32)
		self.screen.blit(sh, sh.get_rect(topleft=(card.left + 10, card.top + 12)))
		pygame.draw.rect(self.screen, settings.CARD_COLOR, card, border_radius=28)

		if self.logo:
			lr  = self.logo.get_rect()
			off = int(math.sin(pygame.time.get_ticks() * 0.003) * 5)
			lr.center = (card.centerx, card.top + 150 + off)
			self.screen.blit(self.logo, lr)

		self._draw_centered_text("Comandos", self.font_body, settings.PRIMARY_DARK, card.top + 275)
		cmds = [
			"ENTER - Iniciar jogo",
			"ESC   - Voltar ao menu",
			"WASD / Setas - Mover o estagiário",
			"Dica: evite os colegas - eles te param!",
		]
		for i, cmd in enumerate(cmds):
			s = self.font_small.render(cmd, True, settings.TEXT_COLOR)
			self.screen.blit(s, s.get_rect(center=(card.centerx, card.top + 315 + i * 34)))

		if self.best_time_ms:
			self._draw_centered_text(
				f"Melhor tempo: {self._format_time(self.best_time_ms)}",
				self.font_small, (80, 140, 60), card.bottom - 85
			)

		btn   = pygame.Rect(0, 0, 260, 58)
		btn.center = (card.centerx, card.bottom - 50)
		hover = btn.collidepoint(pygame.mouse.get_pos())
		pygame.draw.rect(self.screen, (210, 140, 60) if hover else settings.ACCENT_COLOR, btn, border_radius=18)
		pygame.draw.rect(self.screen, settings.PRIMARY_DARK, btn, width=2, border_radius=18)
		self._draw_centered_text("Pressione ENTER", self.font_body, (30, 15, 5), btn.centery)
		self._draw_centered_text("Lucas Caruzo - 2026", self.font_small, (100, 100, 100), settings.HEIGHT - 20)

	# ── HUD ─────────────────────────────────────────────────

	def _draw_hud(self):
		displayed_ms = (pygame.time.get_ticks() - self.timer_start) if self.timer_running else self.elapsed_ms
		timer_text   = f"[T] {self._format_time(displayed_ms)}" if (self.timer_running or displayed_ms) else "[T] --.-s"
		ts  = self.font_hud.render(timer_text, True, (255, 220, 60) if self.timer_running else (200, 200, 200))
		tbg = pygame.Rect(settings.WIDTH // 2 - ts.get_width() // 2 - 10, 8, ts.get_width() + 20, 36)
		self._draw_rounded_box(tbg, (20, 20, 20), radius=10)
		self.screen.blit(ts, (tbg.x + 10, tbg.y + 4))

		if not self.has_coffee and not self.coffee_delivered:
			obj, oc = "Objetivo: Pegar o café na Copa (canto inferior esquerdo)", (255, 230, 100)
		elif self.has_coffee:
			obj, oc = "Objetivo: Sair por uma das saídas do prédio!", (120, 255, 120)
		else:
			obj, oc = "Café entregue! Parabéns!", (100, 220, 100)

		os_ = self.font_small.render(obj, True, oc)
		obg = pygame.Rect(8, 8, os_.get_width() + 18, 30)
		self._draw_rounded_box(obg, (20, 20, 20), radius=8)
		self.screen.blit(os_, (obg.x + 9, obg.y + 4))

		if self.has_coffee:
			ic  = self.font_small.render("Com café!", True, (255, 210, 80))
			ibg = pygame.Rect(settings.WIDTH - ic.get_width() - 26, 8, ic.get_width() + 18, 30)
			self._draw_rounded_box(ibg, (60, 35, 10), (200, 140, 40), radius=8)
			self.screen.blit(ic, (ibg.x + 9, ibg.y + 4))

		if self._player_paralyzed and self._npc_dialogue_timer > 0:
			ratio    = self._npc_dialogue_timer / self._paralysis_duration
			bar_w    = 160
			bar_rect = pygame.Rect(
				self.player.rect.centerx - bar_w // 2,
				self.player.rect.top - 18,
				int(bar_w * ratio), 8
			)
			bg_rect = pygame.Rect(bar_rect.x, bar_rect.y, bar_w, 8)
			pygame.draw.rect(self.screen, (60, 20, 20), bg_rect,  border_radius=4)
			pygame.draw.rect(self.screen, (220, 60, 60), bar_rect, border_radius=4)

	# ── diálogo NPC ─────────────────────────────────────────

	def _draw_npc_dialogue(self):
		if not self._npc_dialogue_text:
			return
		pad, max_w = 14, 500
		lines, line = [], ""
		for w in self._npc_dialogue_text.split():
			test = (line + " " + w).strip()
			if self.font_dialogue.size(test)[0] < max_w:
				line = test
			else:
				lines.append(line)
				line = w
		if line:
			lines.append(line)
		header = f"  {self._npc_dialogue_name}:"

		line_h = self.font_dialogue.get_linesize()
		box_w  = max(self.font_dialogue.size(header)[0], max_w) + pad * 2
		box_h  = (len(lines) + 1) * line_h + pad * 2

		bx = max(5, min(settings.WIDTH - box_w - 5,
		                self.player.rect.centerx - box_w // 2))
		by = max(5, self.player.rect.top - box_h - 12)

		box = pygame.Rect(bx, by, box_w, box_h)
		self._draw_rounded_box(box, (20, 10, 5), (200, 140, 40), radius=10, alpha=230)
		self.screen.blit(self.font_dialogue.render(header, True, (255, 200, 80)),  (bx + pad, by + pad))
		for i, ln in enumerate(lines):
			self.screen.blit(self.font_dialogue.render(ln, True, (255, 255, 230)),
			                 (bx + pad, by + pad + (i + 1) * line_h))

	# ── tela de vitória ─────────────────────────────────────

	def draw_victory(self):
		self._draw_map()
		ov = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA)
		ov.fill((0, 0, 0, 140))
		self.screen.blit(ov, (0, 0))
		box = pygame.Rect(0, 0, 700, 340)
		box.center = (settings.WIDTH // 2, settings.HEIGHT // 2)
		self._draw_rounded_box(box, (20, 40, 20), (80, 200, 80), radius=20, alpha=240)
		self._draw_centered_text("CAFÉ ENTREGUE!", self.font_title, (100, 230, 100), settings.HEIGHT // 2 - 100)
		self._draw_centered_text(f"Tempo: {self._format_time(self.elapsed_ms)}",
		                         self.font_body, (240, 240, 100), settings.HEIGHT // 2 - 20)
		if self.best_time_ms and self.elapsed_ms <= self.best_time_ms:
			self._draw_centered_text("Novo recorde! [Troféu]",
			                         self.font_body, (255, 220, 50), settings.HEIGHT // 2 + 25)
		self._draw_centered_text("ENTER - Jogar novamente     ESC - Menu",
		                         self.font_small, (200, 220, 200), settings.HEIGHT // 2 + 80)

	# ── render do fundo ─────────────────────────────────────

	def _draw_map(self):
		# Faixas laterais (pillarbox)
		if MAP_OFS_X > 0:
			pygame.draw.rect(self.screen, (15, 15, 15),
			                 pygame.Rect(0, 0, MAP_OFS_X, settings.HEIGHT))
			pygame.draw.rect(self.screen, (15, 15, 15),
			                 pygame.Rect(settings.WIDTH - MAP_OFS_X, 0, MAP_OFS_X, settings.HEIGHT))
		if MAP_OFS_Y > 0:
			pygame.draw.rect(self.screen, (15, 15, 15),
			                 pygame.Rect(0, 0, settings.WIDTH, MAP_OFS_Y))
			pygame.draw.rect(self.screen, (15, 15, 15),
			                 pygame.Rect(0, settings.HEIGHT - MAP_OFS_Y, settings.WIDTH, MAP_OFS_Y))
		if self.background:
			self.screen.blit(self.background, (MAP_OFS_X, MAP_OFS_Y))
		else:
			pygame.draw.rect(self.screen, settings.BACKGROUND_COLOR,
			                 pygame.Rect(MAP_OFS_X, MAP_OFS_Y, MAP_DISP_W, MAP_DISP_H))

	# ── lógica de jogo ───────────────────────────────────────

	def _handle_coffee_pickup(self):
		if not self.has_coffee and not self.coffee_bottle.collected:
			if self.coffee_bottle.rect.colliderect(self.player.rect):
				self.coffee_bottle.collect()
				self.has_coffee = True

	def _handle_delivery(self):
		if self.has_coffee and not self.coffee_delivered:
			zones = (SAIDA_PRINCIPAL_ZONE, SAIDA_LATERAL_ZONE, SAIDA_INFERIOR_ZONE)
			if any(z.colliderect(self.player.rect) for z in zones):
				self.coffee_delivered = True
				self.has_coffee       = False
				if self.timer_running:
					self.elapsed_ms   += pygame.time.get_ticks() - self.timer_start
					self.timer_running = False
				if self.elapsed_ms > 0 and (self.best_time_ms == 0 or self.elapsed_ms < self.best_time_ms):
					self.best_time_ms = self.elapsed_ms
				self.state = "victory"

	def _handle_npc_intercept(self):
		if self._player_paralyzed:
			return
		for npc in self.npcs:
			if npc.intercepts(self.player.rect):
				idx = self._npc_phrase_idx[npc.nome]
				self._npc_dialogue_text  = npc.get_phrase(idx)
				self._npc_dialogue_name  = npc.nome
				self._npc_dialogue_timer = self._paralysis_duration
				self._player_paralyzed   = True
				self._npc_phrase_idx[npc.nome] = idx + 1
				npc.cooldown = 3.0
				break

	def _move_player(self, dt):
		if self._player_paralyzed:
			return
		keys = pygame.key.get_pressed()
		h = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - \
		    int(keys[pygame.K_LEFT]  or keys[pygame.K_a])
		v = int(keys[pygame.K_DOWN]  or keys[pygame.K_s]) - \
		    int(keys[pygame.K_UP]    or keys[pygame.K_w])
		if h and v:
			fac = 1 / math.sqrt(2)
			h  *= fac
			v  *= fac
		dx = h * self.player.move_speed * dt
		dy = v * self.player.move_speed * dt

		if   h < 0: self.player.set_direction("left")
		elif h > 0: self.player.set_direction("right")
		elif v < 0: self.player.set_direction("up")
		elif v > 0: self.player.set_direction("down")
		self.player.set_moving(h != 0 or v != 0)

		self._apply_player_movement(dx, dy)

	def draw_game(self, dt):
		self._draw_map()

		for npc in self.npcs:
			npc.draw_radius(self.screen)

		if not self.coffee_bottle.collected:
			self.coffee_bottle.update(dt)
			self.screen.blit(self.coffee_bottle.image, self.coffee_bottle.rect)

		for npc in self.npcs:
			npc.update(dt=dt)
			self.screen.blit(npc.image, npc.rect)

		self.player.update()
		self.screen.blit(self.player.image, self.player.rect)

		self._draw_npc_dialogue()
		self._draw_hud()

		if self._player_paralyzed:
			self._npc_dialogue_timer -= dt
			if self._npc_dialogue_timer <= 0:
				self._player_paralyzed   = False
				self._npc_dialogue_text  = ""
				self._npc_dialogue_name  = ""
				self._npc_dialogue_timer = 0.0

	# ── loop principal ───────────────────────────────────────

	def handle_events(self):
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				self.running = False
			elif event.type == pygame.KEYDOWN:
				if event.key == pygame.K_ESCAPE:
					self.state = "menu" if self.state == "game" else None
					if self.state is None:
						self.running = False
				elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
					if self.state in ("menu", "victory"):
						self._reset_game_state()
						self.state = "game"

	def run(self):
		while self.running:
			dt = self.clock.tick(settings.FPS) / 1000.0
			self.handle_events()
			if   self.state == "menu":
				self.draw_menu()
			elif self.state == "game":
				self._move_player(dt)
				self._handle_npc_intercept()
				self._handle_coffee_pickup()
				self._handle_delivery()
				self.draw_game(dt)
			elif self.state == "victory":
				self.draw_victory()
			pygame.display.flip()
		pygame.quit()