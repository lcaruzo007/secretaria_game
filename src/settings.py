import os

# Configurações de Janela
WIDTH = 1280
HEIGHT = 720
FPS = 60
TITLE = "CRA - COFFEE RUN"

# Cores do tema
BACKGROUND_COLOR = (230, 210, 180)
PRIMARY_DARK = (70, 35, 15)
SECONDARY_COLOR = (120, 70, 30)
ACCENT_COLOR = (192, 122, 44)
CARD_COLOR = (245, 230, 210)
HIGHLIGHT_COLOR = (245, 230, 204)
TEXT_COLOR = (40, 20, 10)

# Cores (RGB)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)

# Caminhos de Diretórios
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
DATA_DIR = os.path.join(ASSETS_DIR, "data")
