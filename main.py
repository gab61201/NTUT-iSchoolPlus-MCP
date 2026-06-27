import logging

from server.tools import mcp

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
