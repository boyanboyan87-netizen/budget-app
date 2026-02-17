import pandas as pd

# ========================================
# BANK STATEMENT PARSERS
# ========================================
def parse_amex(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes a raw AMEX CSV DataFrame and returns a new DataFrame
    with standard columns: Date, Amount, Description, Account.
    """
    # Example: suppose AMEX CSV has columns:
    # 'Date', 'Description', 'Amount'
    standard = pd.DataFrame()
    standard['Date'] = pd.to_datetime(df['Date'], dayfirst=True).dt.date
    standard['Description'] = df['Description'].astype(str)
    standard['Amount'] = df['Amount'].astype(float)
    standard['Account'] = 'AMEX'
    return standard

def parse_barclays(df: pd.DataFrame) -> pd.DataFrame:
    """
    Barclays CSV → standard schema.

    Input columns:
    - Number
    - Date           (e.g. '05/02/2026')
    - Account        (e.g. '20-17-92 73108694')
    - Amount         (e.g. -32.99)
    - Subcategory    (e.g. 'Debit' or 'Direct Debit')
    - Memo           (e.g. 'THE EGGFREE CAKEBO    ON 04 FEB CPM')
    """

    # Create a new empty DataFrame that will hold ONLY our standard columns
    standard = pd.DataFrame()

    standard['Date'] = pd.to_datetime(df['Date'], dayfirst=True).dt.date
    standard['Amount'] = df['Amount'].astype(float)
    standard['Description'] = df['Memo'].astype(str)
    standard['Account'] = 'BARCLAYS'

    return standard

def parse_revolut(df: pd.DataFrame) -> pd.DataFrame:
    """
    Revolut CSV → standard schema.

    Input columns (from your example):
    - Type
    - Product
    - Completed Date
    - Description   
    - Amount           
    - Fee
    - Currency         
    - State            (we only want rows where State == 'COMPLETED')
    - Balance
    """
    # Clean the data first
    df_clean = df[
        (df['State'] == 'COMPLETED') &
        (df['Product'] == 'Current')
    ].copy()

    # DEV - TO REMOVE
    # Keep only the first 10 rows after filtering to avoid overwhelming the database during testing
    df_clean = df_clean.head(10)

    standard = pd.DataFrame()

    # 1) Parse 'Completed Date' into a Python date.
    #    Your format is 'day/month/year hour:minute', so we set dayfirst=True.
    standard['Date'] = pd.to_datetime(
        df_clean['Completed Date'],
        dayfirst=True,
        errors='coerce'  # if any bad values, they become NaT instead of crashing
    ).dt.date

    # 2) Amount: copy directly as float.
    standard['Amount'] = df_clean['Amount'].astype(float)

    # 3) Description: use Revolut's Description column directly.
    standard['Description'] = df_clean['Description'].astype(str)

    # 4) Account: since this is Revolut, we can just label it as such.
    #    Later you could make this 'Revolut Savings', 'Revolut Current', etc.
    standard['Account'] = 'REVOLUT'

    return standard