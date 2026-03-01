import pandas as pd


def parse_standard_csv(df: pd.DataFrame, invert_amounts: bool | None) -> pd.DataFrame:
    """
    Parse a standard-format CSV into a normalised DataFrame.

    Expected columns: Date (DD-MM-YYYY), Amount, Description, Reference (optional)
    Returns columns:  Date, Amount, Description
    """
    required = {"Date", "Amount", "Description"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")

    result = pd.DataFrame()
    result["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y")
    result["Amount"] = df["Amount"].astype(float)
    result["Description"] = df["Description"].astype(str).str.strip()

    # Append Reference to Description if the column exists and is non-empty
    if "Reference" in df.columns:
        ref = df["Reference"].astype(str).str.strip()
        mask = ref.notna() & (ref != "") & (ref != "nan")
        result.loc[mask, "Description"] = result.loc[mask, "Description"] + " | " + ref[mask]

    # Flip signs if expenses are stored as negatives in the file
    if invert_amounts is True:
        result["Amount"] = result["Amount"] * -1

    return result
