import os
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


# ── Zonas importantes (pixels 1280x720) ──────────────────────
COPA_ZONE          = pygame.Rect( 70, 520, 320, 170)
SECRETARIA_ZONE    = pygame.Rect(1005, 500, 220, 150)
SAIDA_LATERAL_ZONE = pygame.Rect(1208, 230,  64, 170)
SAIDA_PRINCIPAL_ZONE = pygame.Rect(575,   8, 145, 112)

MAP_BOUNDS = pygame.Rect(10, 10, 1260, 690)

# ── Zonas de spawn validas para os NPCs (evitar Copa/Secretaria) ──
NPC_SPAWN_ZONES = [
	pygame.Rect(200, 250, 800, 220),   # corredor central
	pygame.Rect( 50, 250, 180, 300),   # ala esquerda
	pygame.Rect(900, 200, 300, 200),   # ala direita superior
	pygame.Rect(700, 420, 400, 200),   # ala direita inferior
]

# ── Dados dos NPCs ────────────────────────────────────────────
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



def _random_npc_position():
	"""Retorna (x, y) aleatorio numa zona valida de spawn sem parede."""
	for _ in range(200):
		zone = random.choice(NPC_SPAWN_ZONES)
		x = random.randint(zone.left + 30, zone.right - 30)
		y = random.randint(zone.top + 30, zone.bottom - 30)
		# Nao pode nascer dentro das zonas especiais
		pt = pygame.Rect(x - 5, y - 5, 10, 10)
		if any(pt.colliderect(z) for z in (COPA_ZONE, SECRETARIA_ZONE,
										   SAIDA_PRINCIPAL_ZONE, SAIDA_LATERAL_ZONE)):
			continue
		return x, y
	# Fallback
	return random.randint(300, 900), random.randint(280, 500)


class CoffeeBottle(pygame.sprite.Sprite):
	"""Garrafa de cafe coletavel com animacao flutuante."""

	def __init__(self, x, y):
		super().__init__()
		path = os.path.join(settings.IMAGES_DIR, "backgrounds", "cafe.png")
		if os.path.exists(path):
			raw = pygame.image.load(path).convert_alpha()
			target_h = 64
			scale = target_h / raw.get_height()
			self.image = pygame.transform.smoothscale(
				raw, (max(1, int(raw.get_width() * scale)), target_h)
			)
		else:
			self.image = pygame.Surface((32, 64), pygame.SRCALPHA)
			pygame.draw.rect(self.image, (180, 100, 30), (8, 0, 16, 64), border_radius=6)

		self.rect = self.image.get_rect(center=(x, y))
		self.collected = False
		self._base_y = y
		self._t = 0.0

	def update(self, dt):
		if not self.collected:
			self._t += dt
			self.rect.centery = int(self._base_y + math.sin(self._t * 2.5) * 5)

	def collect(self):
		self.collected = True
		self.kill()


class Game:
	def __init__(self):
		pygame.init()
		pygame.display.set_caption(settings.TITLE)
		self.screen = pygame.display.set_mode((settings.WIDTH, settings.HEIGHT))
		self.clock  = pygame.time.Clock()
		self.running = True
		self.state   = "menu"

		# Fontes sem emojis para compatibilidade
		self.font_title    = pygame.font.SysFont("Comic Sans MS", 64, bold=True)
		self.font_subtitle = pygame.font.SysFont("Comic Sans MS", 28)
		self.font_body     = pygame.font.SysFont("Comic Sans MS", 24)
		self.font_small    = pygame.font.SysFont("Comic Sans MS", 20)
		self.font_hud      = pygame.font.SysFont("Comic Sans MS", 22, bold=True)
		self.font_dialogue = pygame.font.SysFont("Comic Sans MS", 21)

		self.logo       = self._load_logo()
		self.background = self._load_background()
		self.best_time_ms = 0

		# Estado de dialogo com NPC
		self._npc_dialogue_timer = 0.0
		self._npc_dialogue_text  = ""
		self._npc_dialogue_name  = ""
		self._paralysis_duration = 2.0
		self._player_paralyzed   = False

		self._reset_game_state()

	# ── helpers de carregamento ──────────────────────────────

	def _load_logo(self):
		p = os.path.join(settings.IMAGES_DIR, "backgrounds", "logo.png")
		if not os.path.exists(p):
			return None
		img = pygame.image.load(p).convert_alpha()
		s = 300 / img.get_width()
		return pygame.transform.smoothscale(img, (int(img.get_width()*s), int(img.get_height()*s)))

	def _load_background(self):
		p = os.path.join(settings.IMAGES_DIR, "backgrounds", "cenario.png")
		if not os.path.exists(p):
			return None
		return pygame.transform.smoothscale(
			pygame.image.load(p).convert(), (settings.WIDTH, settings.HEIGHT)
		)

	# ── estado do jogo ───────────────────────────────────────

	def _reset_game_state(self):
		self.player = Player(
			SAIDA_PRINCIPAL_ZONE.centerx, SAIDA_PRINCIPAL_ZONE.centery,
			sprite_name="bola_verde.png", scale=1.0
		)
		self.coffee_bottle = CoffeeBottle(205, 600)

		self.timer_running   = True
		self.timer_start     = pygame.time.get_ticks()
		self.elapsed_ms      = 0
		self.has_coffee      = False
		self.coffee_delivered = False

		# NPCs com posicoes aleatorias a cada reinicio
		self.npcs = []
		for data in NPC_DATA:
			x, y = _random_npc_position()
			speed = random.uniform(70, 120)
			npc = NPC(x, y,
					  nome=data["nome"],
					  frases=data["frases"],
					  intercept_radius=85,
					  patrol_speed=speed)
			self.npcs.append(npc)

		# Contadores de frases por NPC
		self._npc_phrase_idx = {npc.nome: 0 for npc in self.npcs}

		# Dialogo limpo
		self._npc_dialogue_timer = 0.0
		self._npc_dialogue_text  = ""
		self._npc_dialogue_name  = ""
		self._player_paralyzed   = False

	# ── movimento livre ──────────────────────────────────────

	def _apply_player_movement(self, dx_px, dy_px):
		self.player.rect.centerx += int(dx_px)
		self.player.rect.centery += int(dy_px)
		self.player.rect.clamp_ip(MAP_BOUNDS)

	# ── utilitarios de desenho ───────────────────────────────

	def _draw_centered_text(self, text, font, color, y):
		s = font.render(text, True, color)
		self.screen.blit(s, s.get_rect(center=(settings.WIDTH // 2, y)))

	def _draw_rounded_box(self, rect, bg_color, border_color=None, radius=12, alpha=220):
		surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
		r, g, b = bg_color
		pygame.draw.rect(surf, (r, g, b, alpha), surf.get_rect(), border_radius=radius)
		self.screen.blit(surf, rect.topleft)
		if border_color:
			pygame.draw.rect(self.screen, border_color, rect, width=2, border_radius=radius)

	def _format_time(self, ms):
		total_s = ms // 1000
		centis  = (ms % 1000) // 10
		m = total_s // 60
		s = total_s % 60
		return f"{m}:{s:02d}.{centis:02d}" if m else f"{s:02d}.{centis:02d}s"

	# ── menu ─────────────────────────────────────────────────

	def draw_menu(self):
		self.screen.fill(settings.BACKGROUND_COLOR)
		pygame.draw.circle(self.screen, settings.ACCENT_COLOR, (100, 100), 50)
		pygame.draw.circle(self.screen, settings.SECONDARY_COLOR, (settings.WIDTH-120, 100), 70)

		self._draw_centered_text(settings.TITLE, self.font_title, settings.PRIMARY_DARK, 50)
		self._draw_centered_text("Busque o café e entregue na Secretaria!",
		                         self.font_subtitle, (120, 90, 60), 105)

		cw, ch = 860, 520
		card = pygame.Rect(0, 0, cw, ch)
		card.center = (settings.WIDTH//2, settings.HEIGHT//2+26)
		sh = pygame.Surface((cw+20, ch+20), pygame.SRCALPHA)
		pygame.draw.rect(sh, (0,0,0,40), sh.get_rect(), border_radius=32)
		self.screen.blit(sh, sh.get_rect(topleft=(card.left+10, card.top+12)))
		pygame.draw.rect(self.screen, settings.CARD_COLOR, card, border_radius=28)

		if self.logo:
			lr = self.logo.get_rect()
			off = int(math.sin(pygame.time.get_ticks()*0.003)*5)
			lr.center = (card.centerx, card.top+150+off)
			self.screen.blit(self.logo, lr)

		self._draw_centered_text("Comandos", self.font_body, settings.PRIMARY_DARK, card.top+275)
		cmds = [
			"ENTER - Iniciar jogo",
			"ESC   - Voltar ao menu",
			"WASD / Setas - Mover o estagiario",
			"Dica: evite os colegas - eles te param!",

		]
		for i, cmd in enumerate(cmds):
			s = self.font_small.render(cmd, True, settings.TEXT_COLOR)
			self.screen.blit(s, s.get_rect(center=(card.centerx, card.top+315+i*34)))

		if self.best_time_ms:
			self._draw_centered_text(
				f"Melhor tempo: {self._format_time(self.best_time_ms)}",
				self.font_small, (80, 140, 60), card.bottom-85
			)

		btn = pygame.Rect(0, 0, 260, 58)
		btn.center = (card.centerx, card.bottom-50)
		hover = btn.collidepoint(pygame.mouse.get_pos())
		pygame.draw.rect(self.screen, (210,140,60) if hover else settings.ACCENT_COLOR, btn, border_radius=18)
		pygame.draw.rect(self.screen, settings.PRIMARY_DARK, btn, width=2, border_radius=18)
		self._draw_centered_text("Pressione ENTER", self.font_body, (30,15,5), btn.centery)
		self._draw_centered_text("Lucas Caruzo - 2026", self.font_small, (100, 100, 100), settings.HEIGHT - 20)
	# ── HUD ──────────────────────────────────────────────────

	def _draw_hud(self):
		displayed_ms = (pygame.time.get_ticks()-self.timer_start) if self.timer_running else self.elapsed_ms
		timer_text = f"[T] {self._format_time(displayed_ms)}" if (self.timer_running or displayed_ms) else "[T] --.-s"
		ts = self.font_hud.render(timer_text, True, (255,220,60) if self.timer_running else (200,200,200))
		tbg = pygame.Rect(settings.WIDTH//2 - ts.get_width()//2 - 10, 8, ts.get_width()+20, 36)
		self._draw_rounded_box(tbg, (20,20,20), radius=10)
		self.screen.blit(ts, (tbg.x+10, tbg.y+4))

		if not self.has_coffee and not self.coffee_delivered:
			obj, oc = "Objetivo: Pegar o café na Copa", (255, 230, 100)
		elif self.has_coffee:
			obj, oc = "Objetivo: Sair por uma das saidas", (120, 255, 120)
		else:
			obj, oc = "Café entregue! Parabens!", (100, 220, 100)

		os_ = self.font_small.render(obj, True, oc)
		obg = pygame.Rect(8, 8, os_.get_width()+18, 30)
		self._draw_rounded_box(obg, (20,20,20), radius=8)
		self.screen.blit(os_, (obg.x+9, obg.y+4))

		if self.has_coffee:
			ic = self.font_small.render("Com café!", True, (255, 210, 80))
			ibg = pygame.Rect(settings.WIDTH-ic.get_width()-26, 8, ic.get_width()+18, 30)
			self._draw_rounded_box(ibg, (60,35,10), (200,140,40), radius=8)
			self.screen.blit(ic, (ibg.x+9, ibg.y+4))

		# Barra de paralisacao
		if self._player_paralyzed and self._npc_dialogue_timer > 0:
			ratio = self._npc_dialogue_timer / self._paralysis_duration
			bar_w = 160
			bar_rect = pygame.Rect(
				self.player.rect.centerx - bar_w//2,
				self.player.rect.top - 18,
				int(bar_w * ratio), 8
			)
			bg_rect = pygame.Rect(bar_rect.x, bar_rect.y, bar_w, 8)
			pygame.draw.rect(self.screen, (60,20,20), bg_rect, border_radius=4)
			pygame.draw.rect(self.screen, (220,60,60), bar_rect, border_radius=4)

	# ── dialogo NPC ──────────────────────────────────────────

	def _draw_npc_dialogue(self):
		if not self._npc_dialogue_text:
			return
		pad = 14
		max_w = 500
		lines = []
		words = self._npc_dialogue_text.split()
		line = ""
		for w in words:
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
		box_w = max(self.font_dialogue.size(header)[0], max_w) + pad * 2
		box_h = (len(lines) + 1) * line_h + pad * 2

		bx = self.player.rect.centerx - box_w // 2
		by = self.player.rect.top - box_h - 12
		bx = max(5, min(settings.WIDTH - box_w - 5, bx))
		by = max(5, by)

		box = pygame.Rect(bx, by, box_w, box_h)
		self._draw_rounded_box(box, (20, 10, 5), (200, 140, 40), radius=10, alpha=230)

		hs = self.font_dialogue.render(header, True, (255, 200, 80))
		self.screen.blit(hs, (bx + pad, by + pad))
		for i, ln in enumerate(lines):
			ts = self.font_dialogue.render(ln, True, (255, 255, 230))
			self.screen.blit(ts, (bx + pad, by + pad + (i + 1) * line_h))

	# ── tela de vitoria ──────────────────────────────────────

	def draw_victory(self):
		if self.background:
			self.screen.blit(self.background, (0, 0))
		else:
			self.screen.fill(settings.BACKGROUND_COLOR)
		ov = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA)
		ov.fill((0, 0, 0, 140))
		self.screen.blit(ov, (0, 0))
		box = pygame.Rect(0, 0, 700, 340)
		box.center = (settings.WIDTH//2, settings.HEIGHT//2)
		self._draw_rounded_box(box, (20, 40, 20), (80, 200, 80), radius=20, alpha=240)
		self._draw_centered_text("CAFÉ ENTREGUE!",
		                         self.font_title, (100, 230, 100), settings.HEIGHT//2-100)
		self._draw_centered_text(f"Tempo: {self._format_time(self.elapsed_ms)}",
		                         self.font_body, (240, 240, 100), settings.HEIGHT//2-20)
		if self.best_time_ms and self.elapsed_ms <= self.best_time_ms:
			self._draw_centered_text("Novo recorde! [Trofeu]",
			                         self.font_body, (255, 220, 50), settings.HEIGHT//2+25)
		self._draw_centered_text("ENTER - Jogar novamente     ESC - Menu",
		                         self.font_small, (200, 220, 200), settings.HEIGHT//2+80)

	# ── logica de jogo ────────────────────────────────────────

	def _handle_timer(self):
		if self.coffee_delivered and self.timer_running:
			self.elapsed_ms += pygame.time.get_ticks() - self.timer_start
			self.timer_running = False

	def _handle_coffee_pickup(self):
		if not self.has_coffee and not self.coffee_bottle.collected:
			if COPA_ZONE.colliderect(self.player.rect) and \
					self.coffee_bottle.rect.colliderect(self.player.rect):
				self.coffee_bottle.collect()
				self.has_coffee = True

	def _handle_delivery(self):
		if self.has_coffee and not self.coffee_delivered:
			if any(zone.colliderect(self.player.rect) for zone in
				   (SAIDA_LATERAL_ZONE, SAIDA_PRINCIPAL_ZONE)):
				self.coffee_delivered = True
				self.has_coffee = False
				if self.timer_running:
					self.elapsed_ms += pygame.time.get_ticks() - self.timer_start
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
			h *= fac
			v *= fac
		dx = h * self.player.move_speed * dt
		dy = v * self.player.move_speed * dt

		# Passa pelos metodos do player para animar
		if h < 0:   self.player.set_direction("left")
		elif h > 0: self.player.set_direction("right")
		elif v < 0: self.player.set_direction("up")
		elif v > 0: self.player.set_direction("down")
		self.player.set_moving(h != 0 or v != 0)

		self._apply_player_movement(dx, dy)

	def draw_game(self, dt):
		if self.background:
			self.screen.blit(self.background, (0, 0))
		else:
			self.screen.fill(settings.BACKGROUND_COLOR)

		# Raios de deteccao dos NPCs
		for npc in self.npcs:
			npc.draw_radius(self.screen)

		# Garrafa de cafe
		if not self.coffee_bottle.collected:
			self.coffee_bottle.update(dt)
			self.screen.blit(self.coffee_bottle.image, self.coffee_bottle.rect)

		# NPCs
		for npc in self.npcs:
			npc.update(dt=dt)
			self.screen.blit(npc.image, npc.rect)

		# Player
		self.player.update()
		self.screen.blit(self.player.image, self.player.rect)

		# Dialogo
		self._draw_npc_dialogue()
		self._draw_hud()

		# Atualiza timer de paralisacao
		if self._player_paralyzed:
			self._npc_dialogue_timer -= dt
			if self._npc_dialogue_timer <= 0:
				self._player_paralyzed   = False
				self._npc_dialogue_text  = ""
				self._npc_dialogue_name  = ""
				self._npc_dialogue_timer = 0.0

	# ── eventos e loop ────────────────────────────────────────

	def handle_events(self):
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				self.running = False
			elif event.type == pygame.KEYDOWN:
				if event.key == pygame.K_ESCAPE:
					if self.state == "game":
						self.state = "menu"
					else:
						self.running = False
				elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
					if self.state in ("menu", "victory"):
						self._reset_game_state()
						self.state = "game"

	def run(self):
		while self.running:
			dt = self.clock.tick(settings.FPS) / 1000.0
			self.handle_events()
			if self.state == "menu":
				self.draw_menu()
			elif self.state == "game":
				self._move_player(dt)
				self._handle_npc_intercept()
				self._handle_timer()
				self._handle_coffee_pickup()
				self._handle_delivery()
				self.draw_game(dt)
			elif self.state == "victory":
				self.draw_victory()
			pygame.display.flip()
		pygame.quit()
