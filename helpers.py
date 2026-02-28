# Standard library
from collections import Counter
import re

# Third‑party
import pandas as pd

# Local
from models import db, Transaction, Category
from parsers import parse_amex, parse_barclays, parse_revolut


# Only allow CSV files for now
ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename: str) -> bool:
    """
    Helper function: checks that the uploaded file has a .csv extension.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def normalise_description(description: str) -> str:
    """
    Try to strip variable parts (like dates) from merchant descriptions
    so 'BUTTERNUT BOX ON 01 FEB BCC' becomes 'BUTTERNUT BOX'.
    This is a simple heuristic; we can refine it later.
    """
    if not description:
        return ""

    # Collapse multiple spaces
    text = " ".join(description.split())

    # Remove patterns like 'ON 01 FEB', 'ON 12 MAR', etc. (rough heuristic)
    text = re.sub(r"\bON\s+\d{1,2}\s+[A-Z]{3}\b", "", text)

    # Strip trailing 'BCC', 'POS', etc. (add more as you discover patterns)
    text = re.sub(r"\b(BCC|POS|DD|CARD)\b$", "", text)

    # Remove date patterns like 12/01/2024, 01-02-2024
    text = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", "", text)

    # Remove REF: patterns like REF:123456789
    text = re.sub(r"\bREF:\d+\b", "", text)

    # Final cleanup: collapse spaces again and uppercase for consistent matching
    text = " ".join(text.split()).upper()

    return text

def guess_category_from_history(description: str, user_id: int) -> str | None:
    norm = normalise_description(description)
    if not norm:
        return None

    rows = (
        Transaction.query
        .filter(
            Transaction.normalised_description == norm,
            Transaction.category_id.isnot(None),
            Transaction.user_id == user_id
        )
        .all()
    )

    if not rows:
        return None

    counts = Counter(t.category for t in rows if t.category)
    if not counts:
        return None

    return counts.most_common(1)[0][0]

def get_all_category_names() -> list[str]:
    """
    Return a list of all category names currently in the database, for display in dropdowns.
    """
    return [c.name for c in Category.query.for_current_user().order_by(Category.name).all()]

def build_claude_payload(transactions: list[Transaction]) -> list[dict]:
    """
    Given a list of Transaction objects, build the payload we will send to Claude.
    """
    payload = []
    for t in transactions:
        payload.append(
            {
                "id": t.id,
                "date": t.date.isoformat() if t.date else None,
                "amount": t.amount,
                "description": t.description,
                "account": t.account,
            }
        )
    return payload

def load_uploaded_csv(request) -> pd.DataFrame:
    """
    Validate the uploaded file and return a Pandas DataFrame.
    Raises ValueError with a user-friendly message on problems.
    """
    if "file" not in request.files:
        raise ValueError("No file part in request")

    file = request.files["file"]

    if file.filename == "":
        raise ValueError("No file selected")

    if not allowed_file(file.filename):
        raise ValueError("Only .csv files are allowed")

    # Try UTF-8, fall back to latin-1
    try:
        return pd.read_csv(file)
    except UnicodeDecodeError:
        file.stream.seek(0)
        return pd.read_csv(file, encoding="latin-1")

def parse_bank_dataframe(df: pd.DataFrame, bank: str) -> pd.DataFrame:
    """
    Given the raw CSV DataFrame and a bank identifier string,
    return a standardised DataFrame with Date, Amount, Description, Account.
    """
    if not bank:
        raise ValueError("Please select a bank")

    if bank == "amex":
        return parse_amex(df)
    elif bank == "barclays":
        return parse_barclays(df)
    elif bank == "revolut":
        return parse_revolut(df)
    else:
        raise ValueError(f"Unknown bank type: {bank}")

def build_transactions_from_df(standard_df: pd.DataFrame, user_id: int) -> list[Transaction]:
    """
    Turn the standardised DataFrame into a list of Transaction objects.
    Uses guess_category_from_history to auto-fill category when possible.
    Raises ValueError if any row is invalid.
    """
    created = []

    for idx, row in standard_df.iterrows():
        try:
            description = str(row["Description"])
            normalised = normalise_description(description)

            tx = Transaction(
                date=row["Date"],
                amount=float(row["Amount"]),
                description=description,
                account=str(row["Account"]),
                normalised_description=normalised,
                user_id=user_id,
            )

            # Try to reuse past categorizations
            guessed = guess_category_from_history(description, user_id)
            if guessed is not None:
                tx.category = guessed

            created.append(tx)

        except Exception as e:
            # Turn any row error into a clear message with the row number
            raise ValueError(f"Upload failed on row {idx + 1}: {e}")

    return created


def build_transactions_from_plaid(
    plaid_txs: list,
    account_map: dict[str, int],  # plaid_account_id → Account.id
    user_id: int
) -> list:
    # Fetch all already-imported Plaid transaction IDs for this user
    # This is our deduplication check — skip anything we've seen before
    existing_ids = {
        tx.plaid_transaction_id
        for tx in Transaction.query.for_user(user_id)
        .filter(Transaction.plaid_transaction_id.isnot(None)).all()
    }

    transactions = []
    for pt in plaid_txs:
        tx_id = pt["transaction_id"]

        # Skip if already imported (e.g. sync ran twice)
        if tx_id in existing_ids:
            continue

        description = pt["name"]  # Plaid's merchant/description field

        tx = Transaction(
            user_id=user_id,
            date=pt["date"],
            amount=pt["amount"],       # Positive = debit (same convention as CSV imports)
            description=description[:200],
            account_id=account_map.get(pt["account_id"]),
            normalised_description=normalise_description(description),
            plaid_transaction_id=tx_id,  # Store for future dedup
        )

        # Try to reuse past categorizations
        guessed = guess_category_from_history(description, user_id)
        if guessed is not None:
            tx.category = guessed

        transactions.append(tx)

    return transactions



def save_transactions(transactions: list[Transaction]) -> None:
    """
    Save a list of Transaction objects in an all-or-nothing way.
    Rolls back on any error and raises ValueError with a user-friendly message.
    """
    try:
        for tx in transactions:
            db.session.add(tx)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise ValueError(f"Upload failed. No transactions were saved. Error: {e}")