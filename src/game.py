import os
import math

import pygame

try:
	from src import settings
	from src.hud import HUD
	from src.npc import NPC
	from src.player import Player
except ImportError:
	import settings
	from hud import HUD
	from npc import NPC
	from player import Player


DADOS = [
	dict(nome="RH", frases=["Voce assinou o ponto hoje?", "Faltou atualizar sua ficha funcional!", "Tem uma capacitacao amanha, viu o e-mail?", "Preciso do seu atestado ate sexta!", "Suas ferias vencem esse mes, ja solicitou?", "Voce nao trabalha nao?"],),
	dict(nome="Financeiro", frases=["A nota de empenho ainda nao chegou...", "O orcamento desse ano ta zerado!", "Assina esse oficio aqui rapidinho!", "Quando saem as diarias? Sabe nao?", "Bloqueio orcamentario de novo, infelizmente.", "Voce nao trabalha nao?"],),
	dict(nome="Gabinete", frases=["O diretor quer falar contigo!", "Viu a nova portaria que saiu hoje?", "Reuniao de colegiado hoje as 14h!", "Protocola esse documento urgente!", "Tem auditoria semana que vem, prepara!", "Voce nao trabalha nao?"],),
	dict(nome="TI", frases=["Seu computador ta lento? Formata!", "Muda de senha! A sua tem 3 anos!", "A impressora do 2o andar travou dnv", "Tem um patch novo no sistema SUAP!", "Seu e-mail ta cheio, apaga uns!", "Voce nao trabalha nao?"],),
	dict(nome="ASCOM", frases=["Voce aqui Carudo!", "Voce aqui Carudo! Precisamos de foto!", "Voce aqui Carudo! Faz uma nota pra gente?", "Voce aqui Carudo! Assina nossa lista!", "Voce aqui Carudo! Aparece no insta do IF!", "Voce nao trabalha nao?"],),
]

NPC_SPRITES = {
	"RH": "rh.png",
	"Financeiro": "gabinete.png",
	"Gabinete": "gabinete.png",
	"TI": "nti.png",
	"ASCOM": "ascom.png",
}


class Game:
	def __init__(self):
		pygame.init()
		pygame.display.set_caption(settings.TITLE)
		self.screen = pygame.display.set_mode((settings.WIDTH, settings.HEIGHT))
		self.clock = pygame.time.Clock()
		self.running = True
		self.state = "menu"

		self.font_title = pygame.font.SysFont("Comic Sans MS", 64, bold=True)
		self.font_subtitle = pygame.font.SysFont("Comic Sans MS", 28)
		self.font_body = pygame.font.SysFont("Comic Sans MS", 24)
		self.font_small = pygame.font.SysFont("Comic Sans MS", 20)

		self.logo = self._load_logo()
		self.bg_image = None
		self.play_area = pygame.Rect(0, 56, settings.WIDTH, settings.HEIGHT - 56)
		self.hud = HUD()
		self.hud.definir_prazo(30000)
		self.secretaria_area = pygame.Rect(settings.WIDTH - 220, settings.HEIGHT - 170, 190, 120)
		self.copa_area = pygame.Rect(20, 72, 190, 120)
		self.player = Player(settings.WIDTH // 2, settings.HEIGHT // 2 + 110)
		self.npcs = self._build_npcs()
		self.estava_na_secretaria = True
		self.timer_finalizado = False
		self.cafe_coletado = False
		self.cafe_image = self._load_cafe_item()
		self.cafe_rect = self.cafe_image.get_rect(center=self.copa_area.center)
		self.hud.definir_status("Vá até o café e pegue!")

	def _build_npcs(self):
		layout = [
			("RH", pygame.Rect(120, 140, 280, 24), (0, 1)),
			("Financeiro", pygame.Rect(520, 120, 24, 220), (1, 0)),
			("Gabinete", pygame.Rect(700, 260, 280, 24), (0, 1)),
			("TI", pygame.Rect(220, 420, 24, 180), (1, 0)),
			("ASCOM", pygame.Rect(500, 520, 300, 24), (0, 1)),
		]
		npcs = []
		for nome, area, direction in layout:
			frases = next(item["frases"] for item in DADOS if item["nome"] == nome)
			sprite_name = NPC_SPRITES.get(nome, "gabinete.png")
			start_x, start_y = area.center
			npc = NPC(start_x, start_y, nome, frases, sprite_name=sprite_name, patrol_area=area, patrol_speed=90)
			npc._direction_x, npc._direction_y = direction
			npcs.append(npc)
		return npcs

	def _move_player_with_collisions(self, horizontal, vertical, dt):
		if horizontal < 0:
			self.player.set_direction("left")
		elif horizontal > 0:
			self.player.set_direction("right")
		elif vertical < 0:
			self.player.set_direction("up")
		elif vertical > 0:
			self.player.set_direction("down")

		dx = int(horizontal * self.player.move_speed * dt)
		dy = int(vertical * self.player.move_speed * dt)

		if dx != 0:
			self.player.rect.x += dx
			if not self.play_area.contains(self.player.rect):
				self.player.rect.x -= dx

		if dy != 0:
			self.player.rect.y += dy
			if not self.play_area.contains(self.player.rect):
				self.player.rect.y -= dy

	def _update_timer_state(self):
		player_in_secretaria = self.player.rect.colliderect(self.secretaria_area)
		if self.estava_na_secretaria and not player_in_secretaria and not self.hud.cronometro_ativo and not self.timer_finalizado:
			self.estava_na_secretaria = False
			self.hud.iniciar_cronometro()
			self.hud.definir_status("Pegue o café!")

		if self.cafe_coletado and player_in_secretaria and self.hud.cronometro_ativo:
			self.hud.parar_cronometro()
			self.timer_finalizado = True
			self.hud.definir_status("Café entregue!")

	def _draw_world(self):
		self.screen.fill(settings.BACKGROUND_COLOR)

		pygame.draw.rect(self.screen, (210, 190, 150), self.play_area)
		pygame.draw.rect(self.screen, settings.PRIMARY_DARK, self.play_area, 2)

		secretaria_surface = pygame.Surface(self.secretaria_area.size, pygame.SRCALPHA)
		secretaria_surface.fill((90, 160, 90, 80))
		self.screen.blit(secretaria_surface, self.secretaria_area)
		pygame.draw.rect(self.screen, settings.GREEN, self.secretaria_area, 3)
		secretaria_label = self.font_small.render("SECRETARIA", True, settings.PRIMARY_DARK)
		self.screen.blit(secretaria_label, secretaria_label.get_rect(center=(self.secretaria_area.centerx, self.secretaria_area.top - 14)))

		copa_surface = pygame.Surface(self.copa_area.size, pygame.SRCALPHA)
		copa_surface.fill((220, 160, 80, 70))
		self.screen.blit(copa_surface, self.copa_area)
		pygame.draw.rect(self.screen, (230, 140, 40), self.copa_area, 3)
		copa_label = self.font_small.render("COPA", True, settings.PRIMARY_DARK)
		self.screen.blit(copa_label, copa_label.get_rect(center=(self.copa_area.centerx, self.copa_area.top - 14)))

		for npc in self.npcs:
			if npc.patrol_area is not None:
				area_surface = pygame.Surface(npc.patrol_area.size, pygame.SRCALPHA)
				area_surface.fill((120, 120, 120, 35))
				self.screen.blit(area_surface, npc.patrol_area)
				pygame.draw.rect(self.screen, (90, 90, 90), npc.patrol_area, 1)

		if not self.cafe_coletado:
			self.screen.blit(self.cafe_image, self.cafe_rect)

	def _start_game(self):
		self.player.rect.center = self.secretaria_area.center
		self.player.rect.y -= 10
		self.npcs = self._build_npcs()
		self.estava_na_secretaria = True
		self.timer_finalizado = False
		self.cafe_coletado = False
		self.cafe_rect = self.cafe_image.get_rect(center=self.copa_area.center)
		self.hud.parar_cronometro()
		self.hud.ms_corridos = 0
		self.hud.prazo_restante_ms = self.hud.prazo_ms
		self.hud.mensagem_temporaria = ""
		self.hud.mensagem_expira_em = 0
		self.hud.definir_status("Saia da secretaria para começar o cronômetro")

	def _clamp_player_to_area(self):
		if self.player.rect.left < self.play_area.left:
			self.player.rect.left = self.play_area.left
		if self.player.rect.right > self.play_area.right:
			self.player.rect.right = self.play_area.right
		if self.player.rect.top < self.play_area.top:
			self.player.rect.top = self.play_area.top
		if self.player.rect.bottom > self.play_area.bottom:
			self.player.rect.bottom = self.play_area.bottom

	def _draw_hud(self):
		self.hud.desenhar(self.screen)

	def _load_cafe_item(self):
		cafe_path = os.path.join(settings.IMAGES_DIR, "backgrounds", "cafe.png")
		if not os.path.exists(cafe_path):
			fallback = pygame.Surface((44, 44), pygame.SRCALPHA)
			pygame.draw.circle(fallback, (170, 120, 70), (22, 22), 18)
			pygame.draw.circle(fallback, settings.WHITE, (22, 22), 18, 2)
			return fallback

		image = pygame.image.load(cafe_path).convert_alpha()
		target_height = 72
		scale = target_height / image.get_height()
		target_size = (max(1, int(image.get_width() * scale)), target_height)
		return pygame.transform.smoothscale(image, target_size)

	def _load_logo(self):
		logo_path = os.path.join(settings.IMAGES_DIR, "backgrounds", "logo.png")
		if not os.path.exists(logo_path):
			return None

		image = pygame.image.load(logo_path).convert_alpha()
		max_width = 300
		scale = max_width / image.get_width()
		target_size = (int(image.get_width() * scale), int(image.get_height() * scale))
		return pygame.transform.smoothscale(image, target_size)

	def _draw_centered_text(self, text, font, color, y):
		surface = font.render(text, True, color)
		rect = surface.get_rect(center=(settings.WIDTH // 2, y))
		self.screen.blit(surface, rect)

	def _draw_menu_card(self):
		card_width = 860
		card_height = 520
		card_rect = pygame.Rect(0, 0, card_width, card_height)
		card_rect.center = (settings.WIDTH // 2, settings.HEIGHT // 2 + 26)

		shadow_surface = pygame.Surface((card_rect.width + 20, card_rect.height + 20), pygame.SRCALPHA)
		pygame.draw.rect(shadow_surface, (0, 0, 0, 40), shadow_surface.get_rect(), border_radius=32)
		self.screen.blit(shadow_surface, shadow_surface.get_rect(topleft=(card_rect.left + 10, card_rect.top + 12)))
		pygame.draw.rect(self.screen, settings.CARD_COLOR, card_rect, border_radius=28)

		return card_rect

	def draw_menu(self):
		self.screen.fill(settings.BACKGROUND_COLOR)

		pygame.draw.circle(self.screen, settings.ACCENT_COLOR, (100, 100), 50)
		pygame.draw.circle(self.screen, settings.SECONDARY_COLOR, (settings.WIDTH - 120, 100), 70)

		self._draw_centered_text(settings.TITLE, self.font_title, settings.PRIMARY_DARK, 50)
		self._draw_centered_text("Menu inicial", self.font_subtitle, (120, 90, 60), 105)

		card_rect = self._draw_menu_card()

		if self.logo:
			logo_rect = self.logo.get_rect()
			offset = int(math.sin(pygame.time.get_ticks() * 0.003) * 5)
			logo_rect.center = (card_rect.centerx, card_rect.top + 150 + offset)
			self.screen.blit(self.logo, logo_rect)

		self._draw_centered_text("Comandos", self.font_body, settings.PRIMARY_DARK, card_rect.top + 285)

		commands = [
			"ENTER - Iniciar jogo",
			"ESC - Sair",
			"SETAS ou WASD - Mover",
			"ESPACO - Ação",
		]

		start_y = card_rect.top + 315
		for index, command in enumerate(commands):
			surface = self.font_small.render(command, True, settings.TEXT_COLOR)
			rect = surface.get_rect(center=(card_rect.centerx, start_y + index * 34))
			self.screen.blit(surface, rect)

		button_rect = pygame.Rect(0, 0, 260, 58)
		button_rect.center = (card_rect.centerx, card_rect.bottom - 58)

		mouse_pos = pygame.mouse.get_pos()
		hover = button_rect.collidepoint(mouse_pos)
		button_color = (210, 140, 60) if hover else settings.ACCENT_COLOR

		pygame.draw.rect(self.screen, button_color, button_rect, border_radius=18)
		pygame.draw.rect(self.screen, settings.PRIMARY_DARK, button_rect, width=2, border_radius=18)
		self._draw_centered_text("Pressione ENTER", self.font_body, (30, 15, 5), button_rect.centery)

	def draw_game_placeholder(self):
		self._draw_world()

		keys = pygame.key.get_pressed()
		horizontal = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
		vertical = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])

		if horizontal != 0 and vertical != 0:
			factor = 1 / math.sqrt(2)
			horizontal *= factor
			vertical *= factor

		dt = self.clock.get_time() / 1000.0
		self.hud.atualizar()
		self._move_player_with_collisions(horizontal, vertical, dt)
		self._clamp_player_to_area()
		self._update_timer_state()
		self.player.update(moving=(horizontal != 0 or vertical != 0))
		for npc in self.npcs:
			npc.update(dt)

		if not self.cafe_coletado and self.player.rect.colliderect(self.cafe_rect):
			self.cafe_coletado = True
			self.hud.definir_status("Volte para a secretaria!")
			self.hud.definir_mensagem("Café coletado!")

		for npc in self.npcs:
			npc.draw(self.screen)
		self.screen.blit(self.player.image, self.player.rect)

		self._draw_hud()

	def handle_events(self):
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				self.running = False
			elif event.type == pygame.KEYDOWN:
				if event.key == pygame.K_ESCAPE:
					if self.state == "menu":
						self.running = False
					else:
						self.state = "menu"
				elif self.state == "game" and event.key == pygame.K_r and self.game_over:
					self._start_game()
				elif self.state == "menu" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
					self.state = "game"
					self._start_game()

	def run(self):
		while self.running:
			self.handle_events()

			if self.state == "menu":
				self.draw_menu()
			else:
				self.draw_game_placeholder()

			pygame.display.flip()
			self.clock.tick(settings.FPS)

		pygame.quit()
