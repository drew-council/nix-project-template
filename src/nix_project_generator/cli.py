from __future__ import annotations

from pathlib import Path

import click

from .commands import CommandError, SubprocessRunner
from .generator import GenerationError, GenerationOptions, generate_repository
from .profiles import Language, normalized_languages


@click.command()
@click.argument("repository_name")
@click.option(
    "--directory",
    type=click.Path(file_okay=False, path_type=Path),
    help=(
        "Parent directory for the new repository. Defaults to ~/personal "
        "if it exists; otherwise this option is required."
    ),
)
@click.option(
    "--language",
    "languages",
    type=click.Choice([language.value for language in Language]),
    multiple=True,
    help="Add a language profile. May be supplied more than once.",
)
@click.option(
    "--private",
    "private_repository",
    is_flag=True,
    help="Create a private repository and omit license files.",
)
def main(
    repository_name: str,
    directory: Path | None,
    languages: tuple[str, ...],
    private_repository: bool,
) -> None:
    """Create and publish REPOSITORY_NAME below ~/personal or --directory."""
    if directory is None:
        directory = Path.home() / "personal"
        if not directory.is_dir():
            raise click.UsageError(
                "~/personal is not an existing directory; "
                "specify a parent directory with --directory."
            )
    directory = directory.expanduser().resolve()
    if directory.exists() and not directory.is_dir():
        raise click.BadParameter(
            "must be a directory", param_hint="--directory"
        )

    options = GenerationOptions(
        name=repository_name,
        destination=directory / repository_name,
        languages=normalized_languages(languages),
        private=private_repository,
    )
    try:
        result = generate_repository(options, SubprocessRunner())
    except (GenerationError, CommandError) as error:
        raise click.ClickException(str(error)) from error

    click.secho("new repository configured:", fg="green")
    click.echo(result.destination)
    click.echo(result.url)


if __name__ == "__main__":
    main()
