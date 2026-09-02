# PyADQL - pyadql turns an ADQL query into an AST
# Copyright (C) 2026 - Centre National d'Etudes Spatiales (Jean-Christophe Malapert for PDSSP)
# This file is part of PyADQL <https://gitlab.cnes.fr/pdssp/common/pyadql>
# SPDX-License-Identifier: Apache-2.0
"""Main program."""

import argparse
import json
import signal
import sys
import time
from dataclasses import fields, is_dataclass
from pprint import pformat
from typing import Any

from loguru import logger

from pyadql import __author__, __copyright__, __description__, __version__

from .config import configure_logging
from .parser import parse_adql, parse_tree

logger.remove()


class SmartFormatter(argparse.HelpFormatter):
    """Smart formatter for argparse - The lines are split for long text"""

    def _split_lines(self, text, width):
        if text.startswith("R|"):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(  # pylint: disable=protected-access
            self, text, width
        )


class SigintHandler:  # pylint: disable=too-few-public-methods
    """Handles the signal"""

    def __init__(self):
        self.SIGINT = False  # pylint: disable=invalid-name

    def signal_handler(self, sig: int, frame):
        """Trap the signal

        Args:
            sig (int): the signal number
            frame: the current stack frame
        """
        # pylint: disable=unused-argument
        logger.error("You pressed Ctrl+C")
        self.SIGINT = True
        sys.exit(2)


def str2bool(string_to_test: str) -> bool:
    """Checks if a given string is a boolean

    Args:
        string_to_test (str): string to test

    Returns:
        bool: True when the string is a boolean otherwise False
    """
    return string_to_test.lower() in ("yes", "true", "True", "t", "1")


def parse_cli() -> argparse.ArgumentParser:
    """Parse command line inputs.

    Returns
    -------
    argparse.ArgumentParser
        Command line options
    """
    parser = argparse.ArgumentParser(
        description=__description__,
        formatter_class=SmartFormatter,
        epilog=__author__ + " - " + __copyright__,
    )
    parser.add_argument(
        "-v", "--version", action="version", version="%(prog)s " + __version__
    )

    parser.add_argument(
        "--level",
        choices=[
            "INFO",
            "DEBUG",
            "WARNING",
            "ERROR",
            "CRITICAL",
            "TRACE",
        ],
        default="ERROR",
        help="set Level log (default: %(default)s)",
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="ADQL query to parse. If omitted, read from --file or standard input.",
    )
    parser.add_argument(
        "-f",
        "--file",
        metavar="PATH",
        help="Read the ADQL query from a file instead of the argument or stdin.",
    )
    parser.add_argument(
        "--tree",
        action="store_true",
        help="Print the raw Lark parse tree instead of the typed AST.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the AST as JSON instead of a Python repr.",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only print errors (overrides -v).",
    )

    return parser


def _read_query(args: argparse.Namespace) -> str:
    if args.query:
        logger.debug("Query supplied as an argument ({} characters)", len(args.query))
        return args.query
    if args.file:
        logger.info("Reading the query from file {}", args.file)
        with open(args.file, encoding="utf-8") as f:
            return f.read()
    if not sys.stdin.isatty():
        logger.info("Reading the query from standard input")
        return sys.stdin.read()
    logger.error("No query supplied (neither an argument, --file, nor stdin)")
    raise SystemExit(2)


def node_to_dict(obj: Any) -> Any:
    """Recursively convert an AST node (dataclass) into a JSON-compatible
    dict, keeping the class name under the "_type" key to disambiguate
    between the various expression types."""
    if is_dataclass(obj) and not isinstance(obj, type):
        result = {"_type": type(obj).__name__}
        for f in fields(obj):
            result[f.name] = node_to_dict(getattr(obj, f.name))
        return result
    if isinstance(obj, (list, tuple)):
        return [node_to_dict(item) for item in obj]
    return obj


def run(argv: list[str] | None = None) -> int:
    """Main function that instanciates the library."""
    handler = SigintHandler()
    signal.signal(signal.SIGINT, handler.signal_handler)
    args = parse_cli().parse_args(argv)
    configure_logging(args.level)

    t_start = time.perf_counter()

    query = _read_query(args)

    query = query.strip()
    if not query:
        logger.error("The query is empty")
        return 2

    logger.debug("Query to parse ({} characters):\n{}", len(query), query)

    try:
        if args.tree:
            logger.info("Parsing in raw Lark tree mode")
            tree = parse_tree(query)
            print(tree.pretty())
        else:
            logger.info("Parsing into a typed AST")
            ast = parse_adql(query)
            logger.success(
                "Query parsed successfully (root type: {})", type(ast).__name__
            )
            if args.json:
                print(json.dumps(node_to_dict(ast), indent=2, ensure_ascii=False))
            else:
                print(pformat(ast, width=100, compact=False))
    except Exception as exc:
        logger.opt(exception=exc).error("ADQL parsing failed: {}", exc)
        return 1
    finally:
        logger.debug(
            "Command finished in {:.1f} ms", (time.perf_counter() - t_start) * 1000
        )

    return 0


if __name__ == "__main__":
    # execute only if run as a script
    raise SystemExit(run)
