"""HUD adaptado para o jogo atual."""

import pygame

try:
	from src import settings
except ImportError:
	import settings


class HUD:
	def __init__(self):
		self.tempo_inicio = 0
		self.ms_corridos = 0
		self.cronometro_ativo = False
		self.status_fixo = ""
		self.mensagem_temporaria = ""
		self.mensagem_expira_em = 0
		self.prazo_ms = 30000
		self.prazo_restante_ms = self.prazo_ms
		self.prazo_ativo = False
		self.layout_nome = ""
		self.fonte_grande = pygame.font.SysFont("Consolas", 28, bold=True)
		self.fonte_media = pygame.font.SysFont("Arial", 15)
		self.fonte_pequena = pygame.font.SysFont("Comi", 13)

	def iniciar_cronometro(self):
		self.tempo_inicio = pygame.time.get_ticks()
		self.ms_corridos = 0
		self.cronometro_ativo = True
		self.prazo_ativo = True
		self.prazo_restante_ms = self.prazo_ms

	def parar_cronometro(self):
		self.cronometro_ativo = False
		self.prazo_ativo = False

	def definir_prazo(self, prazo_ms):
		self.prazo_ms = max(1, prazo_ms)
		self.prazo_restante_ms = self.prazo_ms

	def definir_layout(self, nome):
		self.layout_nome = nome or ""

	def definir_mensagem(self, texto, duracao_ms=1000):
		self.mensagem_temporaria = texto
		self.mensagem_expira_em = pygame.time.get_ticks() + duracao_ms

	def definir_status(self, texto):
		self.status_fixo = texto or ""

	def atualizar(self):
		if self.cronometro_ativo:
			self.ms_corridos = pygame.time.get_ticks() - self.tempo_inicio
		if self.prazo_ativo:
			self.prazo_restante_ms = max(0, self.prazo_ms - self.ms_corridos)

		if self.mensagem_temporaria and pygame.time.get_ticks() >= self.mensagem_expira_em:
			self.mensagem_temporaria = ""

	def ms_para_tempo(self, ms):
		total_segundos = ms / 1000
		minutos = int(total_segundos // 60)
		segundos = int(total_segundos % 60)
		centesimos = int((total_segundos % 1) * 100)
		return f"{minutos:02d}:{segundos:02d}.{centesimos:02d}"

	def desenhar(self, superficie, player=None, player_lives=0, max_lives=0, current_dialogue="", active_npc=None, game_over=False, locked=False, lock_remaining_ms=0):
		painel = pygame.Surface((settings.WIDTH, 56), pygame.SRCALPHA)
		painel.fill((0, 0, 0, 150))
		superficie.blit(painel, (0, 0))

		tempo_str = self.ms_para_tempo(self.ms_corridos)
		cor_tempo = settings.GREEN if self.ms_corridos < 60000 else (255, 210, 90)
		texto_tempo = self.fonte_grande.render(f"⏱ {tempo_str}", True, cor_tempo)
		superficie.blit(texto_tempo, (settings.WIDTH // 2 - texto_tempo.get_width() // 2, 10))

		status_texto = self.status_fixo or self.mensagem_temporaria
		if status_texto:
			texto_msg = self.fonte_media.render(status_texto, True, settings.GREEN)
			superficie.blit(texto_msg, (10, settings.HEIGHT - 28))

		if self.layout_nome:
			texto_layout = self.fonte_pequena.render(f"Layout: {self.layout_nome}", True, settings.WHITE)
			superficie.blit(texto_layout, (settings.WIDTH - texto_layout.get_width() - 10, settings.HEIGHT - 22))
