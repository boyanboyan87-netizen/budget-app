import pandas as pd
import pytest
from parsers import parse_standard_csv


def test_basic_parse():
    """Standard-format CSV produces correct columns and types."""
    raw_df = pd.read_csv("tests/fixtures/sample-amex.csv")
    df = parse_standard_csv(raw_df, invert_amounts=False)

    assert len(df) > 0
    assert list(df.columns) == ["Date", "Amount", "Description"]
    assert pd.api.types.is_datetime64_any_dtype(df["Date"])
    assert pd.api.types.is_float_dtype(df["Amount"])


def test_invert_amounts():
    """invert_amounts=True flips the sign on all amounts."""
    raw_df = pd.DataFrame({
        "Date": ["01/01/2025"],
        "Amount": [-50.0],
        "Description": ["Grocery shop"],
    })
    df = parse_standard_csv(raw_df, invert_amounts=True)
    assert df["Amount"].iloc[0] == 50.0


def test_reference_appended_to_description():
    """Non-empty Reference is appended to Description with ' | '."""
    raw_df = pd.DataFrame({
        "Date": ["01/01/2025"],
        "Amount": [10.0],
        "Description": ["Payment"],
        "Reference": ["REF123"],
    })
    df = parse_standard_csv(raw_df, invert_amounts=False)
    assert df["Description"].iloc[0] == "Payment | REF123"


def test_missing_required_column_raises():
    """Missing required column raises ValueError."""
    raw_df = pd.DataFrame({
        "Date": ["01/01/2025"],
        "Amount": [10.0],
        # Description missing
    })
    with pytest.raises(ValueError, match="Description"):
        parse_standard_csv(raw_df, invert_amounts=False)
