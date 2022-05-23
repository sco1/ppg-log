from __future__ import annotations

import typing as t

from pytest_check import check_func

if t.TYPE_CHECKING:
    import pandas as pd


@check_func  # type: ignore[misc]  # fine with this untyped decorator
def is_col(df: pd.DataFrame, col_name: str) -> None:
    assert col_name in df.columns


@check_func  # type: ignore[misc]  # fine with this untyped decorator
def is_dtype(df: pd.DataFrame, col_name: str, type_check: t.Callable) -> None:
    """
    Check that the query dataframe matches the correct type.

    `type_check` is assumed to be a callable function that returns a boolean. The intent is to use
    pandas` built-in `pandas.api.types.is_*` functions.
    """
    assert type_check(df[col_name])
