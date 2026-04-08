import os

# Configurações de Janela
WIDTH = 1280
HEIGHT = 720
FPS = 60
TITLE = "CRA - COFFEE RUN"

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
