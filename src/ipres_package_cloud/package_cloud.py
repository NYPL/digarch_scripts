import argparse
import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    def extant_path(p):
        path = Path(p)
        if not path.exists():
            raise argparse.ArgumentTypeError(f"{path} does not exist")
        return path


    parser = argparse.ArgumentParser(
        description='test'
    )
    parser.add_argument(
        '--payload',
        required=True,
        type=extant_path
    )
    parser.add_argument(
        '--log',
        required=True,
        type=extant_path
    )
    parser.add_argument(
        '--md5',
        required=True,
        type=extant_path
    )
    parser.add_argument(
        '--dest',
        required=True,
        type=extant_path
    )
    parser.add_argument(
        '--id',
        required=True
    )

    return parser.parse_args()

def main():
    args = parse_args()
    LOGGER.info("I do not package anything yet")

if __name__ == "__main__":
    main()