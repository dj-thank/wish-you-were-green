"""Read frozen metadata from plain or gzip-compressed public snapshots."""
from pathlib import Path
import gzip
import json


def data_file(path):
    path = Path(path)
    if path.is_file():
        return path
    compressed = Path(str(path) + '.gz')
    if compressed.is_file():
        return compressed
    raise FileNotFoundError(path)


def load_json(path):
    path = data_file(path)
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8') as stream:
        return json.load(stream)


def read_dataframe(path, **kwargs):
    import pandas as pd
    return pd.read_csv(data_file(path), **kwargs)
