import argparse
from pathlib import Path
from database import Base, CAMINHO_DB, engine


def main(reiniciar_bd: bool = False) -> None:
    if CAMINHO_DB.exists():
        if reiniciar_bd:
            CAMINHO_DB.unlink()
        else:
            return

    Base.metadata.create_all(engine)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reiniciar_bd", action="store_true", help="apagar e recriar o arquivo .db")
    args = parser.parse_args()
    main(reiniciar_bd=args.force)
