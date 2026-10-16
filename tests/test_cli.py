from pathlib import Path
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from nix_project_generator.cli import main
from nix_project_generator.generator import GenerationResult


def test_help_lists_language_visibility_and_directory_options() -> None:
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "--language" in result.output
    assert "rust" in result.output
    assert "typescript" in result.output
    assert "--private" in result.output
    assert "--directory" in result.output
    assert "~/personal" in result.output


def test_invalid_language_is_rejected_before_generation() -> None:
    result = CliRunner().invoke(main, ["demo", "--language", "ruby"])

    assert result.exit_code == 2
    assert "Invalid value for '--language'" in result.output


@pytest.fixture
def home_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)
    return home


@pytest.fixture
def generate(monkeypatch: pytest.MonkeyPatch) -> Mock:
    mock = Mock(
        side_effect=lambda options, runner: GenerationResult(
            destination=options.destination,
            url=f"https://github.com/example/{options.name}",
        )
    )
    monkeypatch.setattr("nix_project_generator.cli.generate_repository", mock)
    return mock


def test_defaults_to_existing_personal_directory(
    home_directory: Path, generate: Mock
) -> None:
    personal = home_directory / "personal"
    personal.mkdir()

    result = CliRunner().invoke(main, ["demo"])

    assert result.exit_code == 0, result.output
    assert generate.call_args.args[0].destination == personal / "demo"
    assert str(personal / "demo") in result.output


@pytest.mark.parametrize("personal_is_file", [False, True])
def test_requires_directory_when_personal_is_unavailable(
    home_directory: Path, generate: Mock, personal_is_file: bool
) -> None:
    if personal_is_file:
        (home_directory / "personal").write_text("not a directory")

    result = CliRunner().invoke(main, ["demo"])

    assert result.exit_code == 2
    assert "specify a parent directory with --directory" in result.output
    generate.assert_not_called()


@pytest.mark.parametrize("personal_exists", [False, True])
@pytest.mark.parametrize("path_style", ["absolute", "relative", "tilde"])
def test_explicit_directory_overrides_default(
    home_directory: Path,
    generate: Mock,
    personal_exists: bool,
    path_style: str,
) -> None:
    if personal_exists:
        (home_directory / "personal").mkdir()
    work = home_directory / "work"
    work.mkdir()
    directory = {
        "absolute": str(work),
        "relative": "home/work",
        "tilde": "~/work",
    }[path_style]

    result = CliRunner().invoke(main, ["demo", "--directory", directory])

    assert result.exit_code == 0, result.output
    assert generate.call_args.args[0].destination == work / "demo"


def test_explicit_directory_can_be_created(
    home_directory: Path, generate: Mock
) -> None:
    work = home_directory / "new" / "work"

    result = CliRunner().invoke(main, ["demo", "--directory", str(work)])

    assert result.exit_code == 0, result.output
    assert generate.call_args.args[0].destination == work / "demo"


@pytest.mark.parametrize("path_style", ["absolute", "tilde"])
def test_file_is_rejected_as_parent_directory(
    home_directory: Path, generate: Mock, path_style: str
) -> None:
    file = home_directory / "file"
    file.write_text("not a directory")
    directory = str(file) if path_style == "absolute" else "~/file"

    result = CliRunner().invoke(main, ["demo", "--directory", directory])

    assert result.exit_code == 2
    assert "--directory" in result.output
    generate.assert_not_called()
