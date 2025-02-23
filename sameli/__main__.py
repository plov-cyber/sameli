import argparse

from loguru import logger

import sameli
from sameli.conf import Conf
from sameli.server import Server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--conf", default="/conf/local.yaml")

    args = parser.parse_args()

    conf = Conf.from_yaml(filename=args.conf)

    logger.info(f"Starting SAMELI[ver. {sameli.__version__}] - {conf.app_name}")

    server = Server(settings=conf)

    server.start()


if __name__ == "__main__":
    main()
