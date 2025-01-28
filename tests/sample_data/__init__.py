from pathlib import Path


def sample_file(name: str) -> str:
    path = (Path(__file__).parent / name).absolute()
    return f"file://{path}"
