# claude_client.py

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError("ANTHROPIC_API_KEY is not set in .env")

client = Anthropic(api_key=api_key)


def categorise_with_claude(transactions, category_names):
    """
    Ask Claude to categorise a list of transactions.

    Returns: dict[int, str] mapping transaction id -> category
    """
    print(f"DEBUG: categorise_with_claude called with {len(transactions)} txs") #DEBUG

    category_list_str = ", ".join(category_names)

    system_prompt = (
        "You are an assistant that categorises bank transactions for personal budgeting.\n"
        "Return a JSON object mapping transaction id to a short category string.\n"
        "Important: respond with JSON only, no explanations, no markdown code fences.\n"
        f"Use ONLY these categories: {category_list_str}.\n"
        "If unsure, pick the closest match from this list.\n"
    )

    # Build the user prompt with one transaction per line
    lines = []
    for tx in transactions:
        line = (
            f"id={tx['id']}; "
            f"date={tx['date']}; "
            f"amount={tx['amount']}; "
            f"description={tx['description']}; "
            f"account={tx['account']}"
        )
        lines.append(line)

    user_prompt = (
        "Categorise the following transactions.\n"
        "For each line, respond with an entry in a JSON object where the key is the id "
        "and the value is the category string.\n\n"
        "Transactions:\n" +
        "\n".join(lines) +
        "\n\nExample of the JSON format:\n"
        '{ "123": "Groceries", "124": "Rent" }'
    )

    print("DEBUG: sending prompt to Claude...") #DEBUG

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            timeout=15,
        )
    except Exception as e:
        print("DEBUG: Claude API call raised:", repr(e)) #DEBUG
        raise

    print("DEBUG: got response from Claude") #DEBUG

    # Concatenate all text blocks
    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text

    print("DEBUG: raw Claude text:", repr(text)) #DEBUG

# ---- CLEAN THE TEXT INTO PURE JSON ----
    text_clean = text.strip()

    # 1) Strip ```json fences if present
    if text_clean.startswith("```"):
        lines = text_clean.splitlines()
        if lines:
            lines = lines[1:]  # drop first line (``` or ```json)
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]  # drop last line if it's a closing fence
        text_clean = "\n".join(lines).strip()

    print("DEBUG: cleaned Claude text:", repr(text_clean)) #DEBUG

    # 2) Regex-based repair: keep only well-formed `"id": "Category"` pairs
    import re
    pattern = r'"(\d+)"\s*:\s*"[^\n"]*"'
    matches = list(re.finditer(pattern, text_clean))
    if matches:
        last_match = matches[-1]
        end_pos = last_match.end()
        # Keep from first '{' to end of last valid pair, rebuild object
        start_brace = text_clean.find("{")
        if start_brace != -1:
            trimmed_body = text_clean[start_brace + 1 : end_pos]
            repaired = "{\n" + trimmed_body + "\n}"
            print("DEBUG: repaired JSON:", repr(repaired)) #DEBUG
            text_clean = repaired
    else:
        print("DEBUG: regex repair found no matches, using original text") #DEBUG

    # 3) Parse JSON directly; let json.loads be the judge
    try:
        categories_raw = json.loads(text_clean)
    except json.JSONDecodeError as e:
        print("DEBUG: JSON decode error even after regex repair:", e) #DEBUG
        raise ValueError(f"Claude returned invalid JSON: {text_clean}")

    # 4) Convert keys to ints and values to strings
    result = {}
    for key, value in categories_raw.items():
        try:
            tx_id = int(key)
            result[tx_id] = str(value)
        except (ValueError, TypeError):
            continue

    print("DEBUG: parsed categories:", result) #DEBUG
    return result