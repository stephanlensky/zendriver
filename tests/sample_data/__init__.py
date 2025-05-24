from pathlib import Path


def sample_file(name: str) -> str:
    path = (Path(__file__).parent / name).resolve()
    return path.as_uri()
