import logging

import click

from .resolver import Resolver

logger = logging.getLogger(__name__)


def positive_validator(ctx, param, value):
    if value is None or value > 0:
        return
    raise click.BadParameter(f"positive integer required, got {value}")


@click.command()
@click.argument("url")
@click.option(
    "-m",
    "--method",
    type=click.Choice(("GET", "HEAD"), case_sensitive=False),
    help="HTTP method.",
)
@click.option(
    "--max-redirects",
    type=int,
    callback=positive_validator,
    help="Max redirects count.",
)
@click.option(
    "--max-body", type=int, callback=positive_validator, help="Max body size."
)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Verbose mode.")
def resolve(url, method, max_redirects, max_body, verbose):
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    params = {}
    if max_redirects:
        params["max_redirects"] = max_redirects
    if method:
        params["method"] = method
    logger.debug("resolve url: '%s', forced_params='%s'", url, params)
    resolver = Resolver(**params)
    print(resolver.resolve(url))
