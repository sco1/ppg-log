from pathlib import Path

import dotenv
import typer

from ppg_log import db

dotenv.load_dotenv()

db_cli = typer.Typer(add_completion=False)


@db_cli.command()
def set_address(value: str = typer.Argument(...)) -> None:
    """Save the db address to a local .env file."""
    local_dotenv = Path(dotenv.find_dotenv())
    if not local_dotenv.is_file():
        local_dotenv = Path() / ".env"
        local_dotenv.write_text("")

    dotenv.set_key(local_dotenv, db.DB_URL_VARNAME, value)
