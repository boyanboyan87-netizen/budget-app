import pandas as pd
from parsers import parse_amex, parse_barclays, parse_revolut

def test_parse_amex():
    """Test AMEX CSV parser."""
    raw_df = pd.read_csv("tests/fixtures/sample-amex.csv")
    df = parse_amex(raw_df)
    
    assert len(df) > 0
    assert 'Date' in df.columns
    assert 'Amount' in df.columns
    assert 'Description' in df.columns

def test_parse_barclays():
    """Test Barclays CSV parser."""
    
    raw_df = pd.read_csv("tests/fixtures/sample-barclays.csv")
    df = parse_barclays(raw_df)
    
    assert len(df) > 0
    assert 'Date' in df.columns
    assert 'Amount' in df.columns
    assert 'Description' in df.columns

def test_parse_revolut():
    """Test Revolut CSV parser."""
    raw_df = pd.read_csv("tests/fixtures/sample-revolut.csv")
    df = parse_revolut(raw_df)
    
    assert len(df) > 0
    assert 'Date' in df.columns
    assert 'Amount' in df.columns
    assert 'Description' in df.columns