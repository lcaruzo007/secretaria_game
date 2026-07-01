import os
import json
import math
import random

import pygame

try:
	from src import settings
	from src.player import Player
	from src.npc import NPC, GridPath
	from src.hud import HUD
	from src.coffee_trail import CoffeeTrail
except ImportError:
	import settings
	from player import Player
	from npc import NPC, GridPath
	from hud import HUD
	from coffee_trail import CoffeeTrail
 
 


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
_BLDG_COL_MIN, _BLDG_COL_MAX = 5,  53  # Recuamos 1 tile de cada lado
_BLDG_ROW_MIN, _BLDG_ROW_MAX = 6,  33

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




# Secretaria: canto inferior direito (cols 40-55, rows 24-35)
SECRETARIA_ZONE      = _tile_rect_screen(40, 24, 15, 12)

# ── Saídas reais do mapa (baseadas nas aberturas nas paredes) ────
# Saída principal: gap no topo - cols 28-31, rows 0-4
SAIDA_PRINCIPAL_ZONE = _tile_rect_screen(28,  0,  4,  5)


# ── Spawn do player: corredor interno ao lado da entrada (col 30, row 7) ──
# Escolhido porque é logo abaixo do gap da entrada principal (cols 28-31)
# e está claramente dentro do prédio, sem paredes blocando.
_PLAYER_SPAWN = _tile_screen(30, 7)

# ── Dados dos NPCs ────────────────────────────────────────────────
NPC_DATA = [
	{
		"nome": "RH",
		"pasta": "RH",
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
		"pasta": "FINANCEIRO",
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
		"pasta": "GABINETE",
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
		"pasta": "NTI",
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
		"pasta": "ASCOM",
		"frases": [
			"Posso tirar uma foto pra divulgacao?",
			"Voce pode gravar um depoimento rapido?",
			"Preciso de pauta pra nota de imprensa!",
			"Qual e o tema da semana do setor?",
			"Tem materia sobre o IF no jornal hoje!",
			"Manda um resumo das atividades do mes!",
		],
	},
	# ── Professores de matérias básicas ──────────────────────────────
	{
		"nome": "Prof.PT",
		"pasta": "PROFESSOR_PORTUGUES",
		"frases": [
			"Crase! Quantas vezes vou ter que explicar?",
			"Sua redacao tem paragrafos sem coesao!",
			"Voce leu o texto que passei na semana passada?",
			"Interpretacao de texto nao e adivinhar o que o autor quis dizer!",
			"Entrega da redacao e amanha sem falta!",
			"Concordancia verbal incorreta — refaz essa frase!",
		],
	},
	{
		"nome": "Prof.MT",
		"pasta": "PROFESSOR_MATEMATICA",
		"frases": [
			"Voce sabe fatorar esse polinomio?",
			"A prova de funcoes e na proxima semana!",
			"Lista de exercicios 4 ainda nao foi entregue!",
			"Me explica como voce chegou nesse resultado!",
			"Calculadora nao resolve se voce nao sabe o metodo!",
			"Geometria analitica cai no ENEM — presta atencao!",
		],
	},
	{
		"nome": "Prof.HT",
		"pasta": "PROFESSOR_HISTORIA",
		"frases": [
			"Qual foi a causa da Primeira Guerra Mundial?",
			"O seminario de historia contemporanea e sexta!",
			"Voce confundiu Primeira com Segunda Guerra de novo!",
			"Linha do tempo entregue ate quinta ou zero!",
			"Historia nao e so data, e contexto — entende?",
			"Voce assistiu ao documentario que indiquei?",
		],
	},
	{
		"nome": "Prof.GEO",
		"pasta": "PROFESSOR_GEOGRAFIA",
		"frases": [
			"Onde fica o Tropico de Capricornio? Me aponta no mapa!",
			"Trabalho sobre biomas e para a proxima aula!",
			"Voce sabe diferenciar clima de tempo atmosferico?",
			"Geopolitica cai no vestibular — nao negligencie!",
			"Mapa tematico entregue ate sexta ou desconto na nota!",
			"O aquecimento global nao e opiniao, e ciencia!",
		],
	},
	{
		"nome": "Prof.CIE",
		"pasta": "PROFESSOR_CIENCIAS",
		"frases": [
			"Voce sabe a diferenca entre celula animal e vegetal?",
			"Relatorio do experimento ainda esta pendente!",
			"Prova de quimica organica e semana que vem!",
			"Como funciona a fotossintese? Me explica agora!",
			"O laboratorio precisa de limpeza — escala e sua!",
			"Tabela periodica voce tem que saber de cabeca!",
		],
	},
 {
		"nome": "Prof.EF",
		"pasta": "PROFESSOR_EDUCACAO_FISICA",
		"frases": [
			"Esqueceu a roupa de ginastica de novo?",
			"Faltou na aula pratica ontem!",
			"Avaliacao fisica e semana que vem!",
			"Voce vai participar dos JIFs?",
			"Atestado medico vencido nao vale mais!",
			"Hidratacao e fundamental — cade a garrafinha?",
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


def _build_solid_tile_set(map_data):
	"""Retorna o set de tiles (col, row) marcados como sólidos (tipo 0) no mapa."""
	if not map_data:
		return set()
	mw = map_data.get("w", MAP_TILES_W)
	solid = set()
	for entry in map_data.get("collisions", []):
		idx, tip = map(int, entry.split(":"))
		if tip == 0:
			solid.add((idx % mw, idx // mw))
	return solid


def _build_free_tile_list(map_data):
	"""
	Retorna lista de coordenadas de tela (cx, cy) para o centro de cada tile
	livre DENTRO do interior do prédio (rows 5-35, cols 4-54).
	Não inclui tiles sólidos (tipo 0). Portas (tipo 2) são consideradas livres.
	"""
	if not map_data:
		return []
	solid = _build_solid_tile_set(map_data)
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
		self.font_dialogue = pygame.font.SysFont("Comic Sans MS", 21)

		self.hud = HUD()

		self.logo       = self._load_logo()
		self.background = self._load_background()
		self.best_time_ms = self._carregar_recorde() # <--- Agora ele puxa do TXT!
		self.coffee_trail = CoffeeTrail(scale=MAP_SCALE)
		self._npc_dialogue_timer = 0.0
		self._npc_dialogue_text  = ""
		self._npc_dialogue_name  = ""
		self._paralysis_duration = 2.0
		self._player_paralyzed   = False
		self._menu_btn_rect      = pygame.Rect(0, 0, 0, 0)
		self._menu_quit_btn_rect = pygame.Rect(0, 0, 0, 0)
		self._victory_quit_btn_rect = pygame.Rect(0, 0, 0, 0)

		# ── Áudios do Jogo ──
		# Defina os caminhos dos arquivos (crie uma pasta 'audio' dentro de 'assets')
		self.bg_music_path = os.path.join(settings.ASSETS_DIR, "audio", "fundo.mp3")
		
		# Carrega o efeito sonoro da garrafa de café
		sfx_path = os.path.join(settings.ASSETS_DIR, "audio", "pegar_cafe.mp3")
		try:
			self.sfx_pickup = pygame.mixer.Sound(sfx_path)
		except Exception as e:
			print(f"Aviso: Efeito sonoro não encontrado: {e}")
			self.sfx_pickup = None
  		

		# Mapa e colisões
		self.map_data        = _load_map_data()
		self.collision_rects = _load_collision_rects(self.map_data)
		self.free_tiles      = _build_free_tile_list(self.map_data)
		self.pathfinder = GridPath(
			solid_tiles=_build_solid_tile_set(self.map_data),
			col_min=_BLDG_COL_MIN, col_max=_BLDG_COL_MAX,
			row_min=_BLDG_ROW_MIN, row_max=_BLDG_ROW_MAX,
			tile_px=TILE_ORIG, map_ofs_x=MAP_OFS_X, map_ofs_y=MAP_OFS_Y,
			map_scale=MAP_SCALE,
		)

		self._reset_game_state()


	def _carregar_recorde(self):
			"""Lê o melhor tempo salvo no arquivo record.txt."""
			caminho_arquivo = os.path.join(os.path.dirname(__file__), "record.txt")
			try:
				if os.path.exists(caminho_arquivo):
					with open(caminho_arquivo, "r", encoding="utf-8") as f:
						return int(f.read().strip())
			except Exception as e:
				print(f"Aviso: Erro ao ler record.txt: {e}")
			return 0  # Se o arquivo não existir ou der erro, o recorde é 0

	def _salvar_recorde(self, tempo_ms):
			"""Salva o novo melhor tempo no arquivo record.txt."""
			caminho_arquivo = os.path.join(os.path.dirname(__file__), "record.txt")
			try:
				with open(caminho_arquivo, "w", encoding="utf-8") as f:
					f.write(str(tempo_ms))
			except Exception as e:
				print(f"Aviso: Erro ao salvar record.txt: {e}")
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
				sprite_name="player.png", scale=1.0, diameter_px=48
			)

			# ── Café spawna em qualquer lugar livre, mas longe do player ──
			zona_segura_cafe = pygame.Rect(0, 0, int(400 * MAP_SCALE), int(400 * MAP_SCALE))
			zona_segura_cafe.center = _PLAYER_SPAWN
			
			# Não passamos mais a 'zone', apenas excluímos a área do player
			coffee_x, coffee_y = self._pick_free_pos(exclude_rect=zona_segura_cafe)
			self.coffee_bottle = CoffeeBottle(coffee_x, coffee_y)
			print(f"DEBUG: Café spawnou aleatoriamente em ({coffee_x}, {coffee_y})")

			self.has_coffee       = False
			self.coffee_delivered = False
			
			# HUD — reinicia cronômetro e status (mudei o texto já que não é mais na Copa)
			self.hud.iniciar_cronometro()
			self.hud.definir_status("Objetivo: Encontrar o café pelo prédio!")

			# ── NPCs BEM longe do player e uns dos outros ──
			zona_segura_npcs = pygame.Rect(0, 0, int(800 * MAP_SCALE), int(800 * MAP_SCALE))
			zona_segura_npcs.center = _PLAYER_SPAWN
			
			self.npcs = []
			for data in NPC_DATA:
				# Tenta sortear uma posição até 30 vezes para achar um lugar vazio e longe de outros NPCs
				for _ in range(30):
					x, y = self._pick_free_pos(exclude_rect=zona_segura_npcs)
					
					# Checa se essa posição está muito perto de algum NPC já criado
					perto_demais = False
					for outro_npc in self.npcs:
						dist = math.hypot(x - outro_npc.rect.centerx, y - outro_npc.rect.centery)
						if dist < (160 * MAP_SCALE):  # Distância mínima de 160px entre eles
							perto_demais = True
							break
					
					if not perto_demais:
						break # A posição é boa! Sai do loop de tentativas.

				speed = random.uniform(85, 130) * MAP_SCALE
				npc   = NPC(x, y,
							nome=data["nome"],
							frases=data["frases"],
							intercept_radius=int(80 * MAP_SCALE),
							patrol_speed=speed,
							collision_rects=self.collision_rects,
							building_bounds=BUILDING_BOUNDS,
							sprite_folder=data.get("pasta", data["nome"]),
							pathfinder=self.pathfinder,
							free_tiles=self.free_tiles)
				self.npcs.append(npc)

			self._npc_phrase_idx     = {npc.nome: 0 for npc in self.npcs}
			self._npc_dialogue_timer = 0.0
			self._npc_dialogue_text  = ""
			self._npc_dialogue_name  = ""
			self._player_paralyzed   = False
			self.coffee_trail.clear()
			
			# ── Tocar música de fundo ──
			try:
				pygame.mixer.music.load(self.bg_music_path)
				pygame.mixer.music.play(-1) # O -1 faz a música tocar em loop infinito
			except Exception as e:
				print("Aviso: Música de fundo não encontrada ou erro ao tocar.")
	# ── colisão ─────────────────────────────────────────────

	def _check_collision(self, rect):
		return any(rect.colliderect(cr) for cr in self.collision_rects)

	def _player_hitbox(self, rect):
		"""
		Hitbox de colisão menor que o sprite inteiro, ancorada nos "pés"
		do personagem (midbottom). Usar o rect inteiro do sprite (que tem
		espaço vazio em cima, cabelo, etc.) fazia o player parecer travar
		longe da parede e prender em quinas de tile. Com uma hitbox menor
		e ancorada embaixo, o movimento fica muito mais suave e natural.
		"""
		w = max(6, int(rect.width * 0.5))
		h = max(6, int(rect.height * 0.35))
		hb = pygame.Rect(0, 0, w, h)
		hb.midbottom = rect.midbottom
		return hb

	def _apply_player_movement(self, dx_px, dy_px):
		new_x = self.player.rect.centerx + int(dx_px)
		new_y = self.player.rect.centery + int(dy_px)

		def blocked(rect):
			return self._check_collision(self._player_hitbox(rect))

		# Clamp dentro do mapa completo (permite usar as saídas)
		test = self.player.rect.copy()
		test.centerx = new_x
		test.centery = new_y
		test.clamp_ip(MAP_BOUNDS)

		if not blocked(test):
			self.player.rect.centerx = test.centerx
			self.player.rect.centery = test.centery
		else:
			# Deslizamento X
			tx = self.player.rect.copy()
			tx.centerx = new_x
			tx.clamp_ip(MAP_BOUNDS)
			if not blocked(tx):
				self.player.rect.centerx = tx.centerx
			else:
				# Deslizamento Y
				ty = self.player.rect.copy()
				ty.centery = new_y
				ty.clamp_ip(MAP_BOUNDS)
				if not blocked(ty):
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

		cw, ch = 860, 560
		card   = pygame.Rect(0, 0, cw, ch)
		card.centerx = settings.WIDTH // 2
		# Topo fixo (igual ao layout antigo) — só cresce pra baixo, pra não
		# encostar no subtítulo lá em cima.
		card.top = (settings.HEIGHT // 2 + 26) - 260
		sh = pygame.Surface((cw + 20, ch + 20), pygame.SRCALPHA)
		pygame.draw.rect(sh, (0, 0, 0, 40), sh.get_rect(), border_radius=32)
		self.screen.blit(sh, sh.get_rect(topleft=(card.left + 10, card.top + 12)))
		pygame.draw.rect(self.screen, settings.CARD_COLOR, card, border_radius=28)

		if self.logo:
			lr  = self.logo.get_rect()
			off = int(math.sin(pygame.time.get_ticks() * 0.003) * 5)
			lr.center = (card.centerx, card.top + 150 + off)
			self.screen.blit(self.logo, lr)

		cmds = [
			"ENTER - Iniciar jogo",
			"ESC   - Voltar ao menu",
			"WASD / Setas - Mover o estagiário",
			"Dica: evite os colegas - eles te param!",
		]
		for i, cmd in enumerate(cmds):
			s = self.font_small.render(cmd, True, settings.TEXT_COLOR)
			self.screen.blit(s, s.get_rect(center=(card.centerx, card.top + 295 + i * 28)))

		if self.best_time_ms:
				tempo_str = self.hud.ms_para_tempo(self.best_time_ms)
				texto_recorde = f"Melhor tempo: {tempo_str}"

				# Renderiza o texto usando a fonte body (um pouquinho maior) e cor clara
				surf_texto = self.font_body.render(texto_recorde, True, (255, 235, 180))
				
				# Ancorado a partir do topo do card, com folga garantida abaixo
				# da lista de comandos (que agora termina em card.top + 379).
				rect_texto = surf_texto.get_rect(center=(card.centerx, card.top + 440))
				
				# Cria um retângulo de fundo baseado no tamanho do texto, dando uma "gordurinha"
				caixa_bg = rect_texto.inflate(40, 12) 
				
				# Desenha o fundo marrom escuro (combinando com o café) e uma borda dourada
				pygame.draw.rect(self.screen, (60, 30, 15), caixa_bg, border_radius=12)
				pygame.draw.rect(self.screen, (200, 150, 50), caixa_bg, width=2, border_radius=12)
				
				# Desenha o texto por cima do fundo
				self.screen.blit(surf_texto, rect_texto)

		# Botão Jogar
		btn_play = pygame.Rect(0, 0, 240, 52)
		btn_play.center = (card.centerx - 135, card.top + 510)
		self._menu_btn_rect = btn_play
		hover_play = btn_play.collidepoint(pygame.mouse.get_pos())
		pygame.draw.rect(self.screen, (210, 140, 60) if hover_play else settings.ACCENT_COLOR, btn_play, border_radius=18)
		pygame.draw.rect(self.screen, settings.PRIMARY_DARK, btn_play, width=2, border_radius=18)
		s = self.font_body.render("Jogar (ENTER)", True, (30, 15, 5))
		self.screen.blit(s, s.get_rect(center=btn_play.center))

		# Botão Sair
		btn_quit = pygame.Rect(0, 0, 190, 52)
		btn_quit.center = (card.centerx + 125, card.top + 510)
		self._menu_quit_btn_rect = btn_quit
		hover_quit = btn_quit.collidepoint(pygame.mouse.get_pos())
		pygame.draw.rect(self.screen, (180, 60, 60) if hover_quit else (140, 40, 40), btn_quit, border_radius=18)
		pygame.draw.rect(self.screen, (220, 100, 100), btn_quit, width=2, border_radius=18)
		s = self.font_body.render("Sair (ESC)", True, (255, 220, 220))
		self.screen.blit(s, s.get_rect(center=btn_quit.center))

		self._draw_centered_text("Lucas Caruzo - 2026", self.font_small, (100, 100, 100), settings.HEIGHT - 20)
	# ── HUD ─────────────────────────────────────────────────

	def _draw_hud(self):
		self.hud.atualizar()
		self.hud.desenhar(self.screen)

		self._draw_boost_bar()

		# Barra de paralisia acima do player
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

	def _draw_boost_bar(self):
		"""Barra fixa no canto inferior esquerdo mostrando o estado do boost:
		pronto (verde-pastel), recarregando (azul-pastel, enchendo aos poucos)
		ou ativo no momento (dourado)."""
		player = self.player
		bar_w, bar_h = 180, 16
		x = 20
		y = settings.HEIGHT - bar_h - 30

		ratio = player.boost_cooldown_ratio

		bg_rect   = pygame.Rect(x, y, bar_w, bar_h)
		fill_rect = pygame.Rect(x, y, max(0, int(bar_w * ratio)), bar_h)

		if player.is_boosting:
			fill_color = (255, 221, 148)   # dourado pastel — boost ativo agora
			label = "BOOST!"
		elif player.boost_ready:
			fill_color = (168, 230, 194)   # verde pastel — pronto pra usar
			label = "BOOST pronto (ESPAÇO)"
		else:
			fill_color = (168, 202, 235)   # azul pastel — recarregando
			label = "recarregando..."

		pygame.draw.rect(self.screen, (40, 24, 16), bg_rect, border_radius=7)
		if fill_rect.width > 0:
			pygame.draw.rect(self.screen, fill_color, fill_rect, border_radius=7)
		pygame.draw.rect(self.screen, (255, 255, 255), bg_rect, width=2, border_radius=7)

		text_color = (255, 255, 255) if (player.boost_ready or player.is_boosting) else (215, 215, 215)
		s = self.font_small.render(label, True, text_color)
		self.screen.blit(s, (x + 8, y - s.get_height() - 6))

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
		tempo_str = self.hud.ms_para_tempo(self.hud.ms_corridos)
		self._draw_centered_text(f"Tempo: {tempo_str}",
		                         self.font_body, (240, 240, 100), settings.HEIGHT // 2 - 20)
		if self.best_time_ms and self.hud.ms_corridos <= self.best_time_ms:
			self._draw_centered_text("Novo recorde! : )",
			                         self.font_body, (255, 220, 50), settings.HEIGHT // 2 + 25)
		# Botão Jogar novamente
		btn_play = pygame.Rect(0, 0, 250, 52)
		btn_play.center = (box.centerx - 140, box.bottom - 44)
		self._menu_btn_rect = btn_play
		hover_play = btn_play.collidepoint(pygame.mouse.get_pos())
		pygame.draw.rect(self.screen, (80, 200, 80) if hover_play else (50, 160, 50), btn_play, border_radius=16)
		pygame.draw.rect(self.screen, (180, 255, 180), btn_play, width=2, border_radius=16)
		s = self.font_body.render("Jogar (ENTER)", True, (20, 40, 20))
		self.screen.blit(s, s.get_rect(center=btn_play.center))

		# Botão Sair (ESC → menu)
		btn_quit = pygame.Rect(0, 0, 200, 52)
		btn_quit.center = (box.centerx + 130, box.bottom - 44)
		self._victory_quit_btn_rect = btn_quit
		hover_quit = btn_quit.collidepoint(pygame.mouse.get_pos())
		pygame.draw.rect(self.screen, (180, 60, 60) if hover_quit else (140, 40, 40), btn_quit, border_radius=16)
		pygame.draw.rect(self.screen, (220, 100, 100), btn_quit, width=2, border_radius=16)
		s = self.font_body.render("Sair (ESC)", True, (255, 220, 220))
		self.screen.blit(s, s.get_rect(center=btn_quit.center))

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
				self.hud.definir_mensagem("Café pego! Corre pra saída!", duracao_ms=2000)
				self.player.change_sprite("PLAYER_CAFE.png")
				# 1. Toca o efeito sonoro de pegar o café
				if self.sfx_pickup:
					self.sfx_pickup.play()

	def _handle_delivery(self):
		if self.has_coffee and not self.coffee_delivered:
			if SAIDA_PRINCIPAL_ZONE.colliderect(self.player.rect):
				self.coffee_delivered = True
				self.has_coffee = False
				self.hud.parar_cronometro()
				self.hud.definir_status("Café entregue! Parabéns!")
				# Para a música de tensão ao vencer
				pygame.mixer.music.stop()

				elapsed = self.hud.ms_corridos
				# Se for a primeira vez jogando OU se bateu o recorde atual
				if elapsed > 0 and (self.best_time_ms == 0 or elapsed < self.best_time_ms):
					self.best_time_ms = elapsed
					self._salvar_recorde(elapsed) # <--- Salva o novo recorde no TXT!

				self.state = "victory"

	def _handle_npc_intercept(self):
		if self._player_paralyzed:
			return
		triggered = False
		for npc in self.npcs:
			if npc.intercepts(self.player.rect):
				if not triggered:
					idx = self._npc_phrase_idx[npc.nome]
					self._npc_dialogue_text  = npc.get_phrase(idx)
					self._npc_dialogue_name  = npc.nome
					self._npc_dialogue_timer = self._paralysis_duration
					self._player_paralyzed   = True
					self._npc_phrase_idx[npc.nome] = idx + 1
					triggered = True
				# Todo NPC que está encostando no player agora entra em
				# cooldown, não só o que "ganhou" o diálogo — se não, quando
				# tem vários grudados, o player toma delay de um atrás do
				# outro assim que a paralisia atual termina.
				npc.cooldown = 3.0

	def _move_player(self, dt):
		if self._player_paralyzed:
			return
		self.player.update_boost(dt)
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

		if not self.coffee_bottle.collected:
			self.coffee_bottle.update(dt)
			self.screen.blit(self.coffee_bottle.image, self.coffee_bottle.rect)

		# ── rastro de café ──────────────────────────────────────────
		if self.has_coffee:
			keys = pygame.key.get_pressed()
			moving = any([keys[pygame.K_LEFT], keys[pygame.K_RIGHT],
						keys[pygame.K_UP],   keys[pygame.K_DOWN],
						keys[pygame.K_a],    keys[pygame.K_d],
						keys[pygame.K_w],    keys[pygame.K_s]])
			self.coffee_trail.try_emit(
				self.player.rect.centerx,
				self.player.rect.centery,
				moving and not self._player_paralyzed
			)
		self.coffee_trail.update(dt)
		self.coffee_trail.draw(self.screen)
		# ────────────────────────────────────────────────────────────


		for npc in self.npcs:
			others = [n for n in self.npcs if n is not npc]
			npc.update(dt=dt, others=others)
			npc.draw(self.screen)

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
					if self.state == "game":
						self.state = "menu"
					else:
						# ESC no menu ou vitória → sair
						self.running = False

				elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
					if self.state in ("menu", "victory"):
						self._reset_game_state()
						self.state = "game"

				elif event.key == pygame.K_SPACE:
					if self.state == "game" and not self._player_paralyzed:
						self.player.trigger_boost()

			elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
				pos = event.pos

				if self.state == "menu":
					# Botão Jogar
					if hasattr(self, "_menu_btn_rect") and self._menu_btn_rect.collidepoint(pos):
						self._reset_game_state()
						self.state = "game"
					# Botão Sair
					elif hasattr(self, "_menu_quit_btn_rect") and self._menu_quit_btn_rect.collidepoint(pos):
						self.running = False

				elif self.state == "victory":
					# Botão Jogar novamente
					if hasattr(self, "_menu_btn_rect") and self._menu_btn_rect.collidepoint(pos):
						self._reset_game_state()
						self.state = "game"
					# Botão Sair
					elif hasattr(self, "_victory_quit_btn_rect") and self._victory_quit_btn_rect.collidepoint(pos):
						self.state = "menu"

	def run(self):
		while self.running:
			dt = min(self.clock.tick(settings.FPS) / 1000.0, 0.05)  # máx 50ms = 20fps mínimo
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