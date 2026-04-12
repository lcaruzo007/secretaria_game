import os
import math

import pygame

try:
	from src import settings
	from src.npc import NPC
	from src.player import Player
except ImportError:
	import settings
	from npc import NPC
	from player import Player


DADOS = [
	dict(nome="RH", frases=[
		"Voce assinou o ponto hoje?",
		"Faltou atualizar sua ficha funcional!",
		"Tem uma capacitacao amanha, viu o e-mail?",
		"Preciso do seu atestado ate sexta!",
		"Suas ferias vencem esse mes, ja solicitou?",
		"Voce nao trabalha nao?",
	]),
	dict(nome="Financeiro", frases=[
		"A nota de empenho ainda nao chegou...",
		"O orcamento desse ano ta zerado!",
		"Assina esse oficio aqui rapidinho!",
		"Quando saem as diarias? Sabe nao?",
		"Bloqueio orcamentario de novo, infelizmente.",
		"Voce nao trabalha nao?",
	]),
	dict(nome="Gabinete", frases=[
		"O diretor quer falar contigo!",
		"Viu a nova portaria que saiu hoje?",
		"Reuniao de colegiado hoje as 14h!",
		"Protocola esse documento urgente!",
		"Tem auditoria semana que vem, prepara!",
		"Voce nao trabalha nao?",
	]),
	dict(nome="TI", frases=[
		"Seu computador ta lento? Formata!",
		"Muda de senha! A sua tem 3 anos!",
		"A impressora do 2o andar travou dnv",
		"Tem um patch novo no sistema SUAP!",
		"Seu e-mail ta cheio, apaga uns!",
		"Voce nao trabalha nao?",
	]),
	dict(nome="ASCOM", frases=[
		"Voce aqui Carudo!",
		"Voce aqui Carudo! Precisamos de foto!",
		"Voce aqui Carudo! Faz uma nota pra gente?",
		"Voce aqui Carudo! Assina nossa lista!",
		"Voce aqui Carudo! Aparece no insta do IF!",
		"Voce nao trabalha nao?",
	]),
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
		self.player = Player(settings.WIDTH // 2, settings.HEIGHT // 2 + 110)
		self.npcs = self._build_npcs()
		self.current_dialogue = ""
		self.interact_requested = False
		self.active_npc = None

	def _build_npcs(self):
		positions = [
			(340, settings.HEIGHT // 2 + 90),
			(560, settings.HEIGHT // 2 + 50),
			(780, settings.HEIGHT // 2 + 90),
			(940, settings.HEIGHT // 2 + 50),
			(1100, settings.HEIGHT // 2 + 90),
		]

		npcs = []
		for data, (x, y) in zip(DADOS, positions):
			sprite_name = NPC_SPRITES.get(data["nome"], "gabinete.png")
			npcs.append(NPC(x, y, data["nome"], data["frases"], sprite_name=sprite_name))

		return npcs

	def _load_logo(self):
		logo_path = os.path.join(settings.IMAGES_DIR, "logo.png")
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

	def _find_nearby_npc(self):
		for npc in self.npcs:
			if npc.intercepts(self.player.rect):
				return npc

		return None

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

		self._draw_centered_text("Comandos", self.font_body, settings.PRIMARY_DARK, card_rect.top + 275)

		commands = [
			"ENTER - Iniciar jogo",
			"ESC - Sair",
			"SETAS ou WASD - Mover",
			"ESPACO - Acao",
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
		self.screen.fill(settings.BACKGROUND_COLOR)
		self._draw_centered_text("Tela de Teste", self.font_title, settings.TEXT_COLOR, 44)
		self._draw_centered_text("Teste inicial de movimento e conversa com NPCs", self.font_subtitle, settings.PRIMARY_DARK, 96)
		self._draw_centered_text("ESC - Voltar ao menu", self.font_small, settings.PRIMARY_DARK, 138)

		arena_rect = pygame.Rect(90, 180, settings.WIDTH - 180, settings.HEIGHT - 260)
		pygame.draw.rect(self.screen, (224, 202, 170), arena_rect, border_radius=24)
		pygame.draw.rect(self.screen, settings.PRIMARY_DARK, arena_rect, width=2, border_radius=24)
		for line_x in range(arena_rect.left + 40, arena_rect.right, 120):
			pygame.draw.line(self.screen, (210, 190, 155), (line_x, arena_rect.top + 18), (line_x, arena_rect.bottom - 18), 1)

		keys = pygame.key.get_pressed()
		horizontal = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
		vertical = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])

		if horizontal != 0 and vertical != 0:
			factor = 1 / math.sqrt(2)
			horizontal *= factor
			vertical *= factor

		dt = self.clock.get_time() / 1000.0
		self.player.move_with_input(horizontal, vertical, dt)
		self.player.update(moving=horizontal != 0 or vertical != 0)
		self.screen.blit(self.player.image, self.player.rect)

		self.active_npc = self._find_nearby_npc()
		if self.interact_requested:
			if self.active_npc:
				self.current_dialogue = f"{self.active_npc.nome}: {self.active_npc.get_phrase()}"
			else:
				self.current_dialogue = "Chegue mais perto de um NPC para interagir."
			self.interact_requested = False

		hint_text = ""
		for npc in self.npcs:
			self.screen.blit(npc.image, npc.rect)
			if npc is self.active_npc:
				hint_text = f"{npc.nome} pronto para conversar"

		if self.active_npc and not self.current_dialogue:
			hint_surface = self.font_small.render("Pressione ESPACO para conversar", True, settings.PRIMARY_DARK)
			hint_rect = hint_surface.get_rect(midtop=(self.active_npc.rect.centerx, self.active_npc.rect.top - 36))
			self.screen.blit(hint_surface, hint_rect)

		if hint_text:
			status_surface = self.font_small.render(hint_text, True, settings.PRIMARY_DARK)
			status_rect = status_surface.get_rect(midbottom=(settings.WIDTH // 2, arena_rect.top - 10))
			self.screen.blit(status_surface, status_rect)

		if self.current_dialogue:
			dialogue_surface = self.font_body.render(self.current_dialogue, True, settings.PRIMARY_DARK)
			dialogue_rect = dialogue_surface.get_rect(midbottom=(settings.WIDTH // 2, settings.HEIGHT - 30))
			padding_rect = dialogue_rect.inflate(28, 18)
			pygame.draw.rect(self.screen, settings.CARD_COLOR, padding_rect, border_radius=14)
			pygame.draw.rect(self.screen, settings.PRIMARY_DARK, padding_rect, width=2, border_radius=14)
			self.screen.blit(dialogue_surface, dialogue_rect)

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
				elif self.state == "game" and event.key == pygame.K_SPACE:
					self.interact_requested = True
				elif self.state == "menu" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
					self.state = "game"

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
