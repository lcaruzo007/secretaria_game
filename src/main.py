try:
	from src.game import Game
except ImportError:
	from game import Game


def main():
	Game().run()


if __name__ == "__main__":
	main()
 
