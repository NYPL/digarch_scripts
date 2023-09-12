import argparse
import logging

LOGGER = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='test'
    )
    parser.add_argument(
        '--payload',
        required=True
    )
    parser.add_argument(
        '--log',
        required=True
    )
    parser.add_argument(
        '--md5',
        required=True
    )
    parser.add_argument(
        '--dest',
        required=True
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