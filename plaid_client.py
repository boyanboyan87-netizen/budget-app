import os
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest


def get_plaid_client() -> plaid_api.PlaidApi:
    """Build and return a configured Plaid API client.
    Reads PLAID_ENV from .env to switch between sandbox and production.
    """
    env_map = {
        "sandbox": plaid.Environment.Sandbox,
        "production": plaid.Environment.Production,
    }
    plaid_env = os.getenv("PLAID_ENV", "sandbox")
    secret_key = "PLAID_SANDBOX_SECRET" if plaid_env == "sandbox" else "PLAID_PRODUCTION_SECRET"

    config = plaid.Configuration(
        host=env_map[plaid_env],
        api_key={
            "clientId": os.getenv("PLAID_CLIENT_ID"),
            "secret": os.getenv(secret_key),
        }
    )
    return plaid_api.PlaidApi(plaid.ApiClient(config))


def create_link_token(user_id: int) -> str:
    """Generate a short-lived link_token for the frontend to open Plaid Link.
    Called when the user clicks 'Connect a Bank'.
    """
    client = get_plaid_client()
    request = LinkTokenCreateRequest(
        products=[Products("transactions")],
        client_name="Budget App",
        country_codes=[CountryCode("GB")],
        language="en",
        user=LinkTokenCreateRequestUser(client_user_id=str(user_id))
    )
    response = client.link_token_create(request)
    return response["link_token"]


def exchange_public_token(public_token: str) -> dict:
    """Exchange the public_token (from Plaid Link) for a permanent access_token.
    The access_token is what we store in PlaidItem to make future API calls.
    """
    client = get_plaid_client()
    request = ItemPublicTokenExchangeRequest(public_token=public_token)
    response = client.item_public_token_exchange(request)
    return {
        "access_token": response["access_token"],
        "item_id": response["item_id"],
    }


def sync_transactions(item) -> tuple[list, list, str]:
    """Fetch new and removed transactions for a linked bank account.
    Uses cursor-based pagination — on first sync, cursor is None (full history).
    On subsequent syncs, cursor picks up only new changes (incremental).
    Returns: (added, removed, next_cursor)
    """
    client = get_plaid_client()
    added = []
    removed = []
    cursor = item.cursor  # None on first sync, saved value on subsequent syncs

    while True:
        request = TransactionsSyncRequest(
            access_token=item.access_token,
            **( {"cursor": cursor} if cursor else {} )
        )
        response = client.transactions_sync(request)
        added.extend(response["added"])
        removed.extend(response["removed"])
        cursor = response["next_cursor"]

        # Plaid paginates in batches — keep looping until all pages fetched
        if not response["has_more"]:
            break

    return added, removed, cursor



def get_balances(item) -> list[dict]:
    """Fetch current balances for all accounts in a PlaidItem."""
    client = get_plaid_client()
    request = AccountsBalanceGetRequest(access_token=item.access_token)
    response = client.accounts_balance_get(request)
    return [
        {
            'plaid_account_id': acct.account_id,
            'current': float(acct.balances.current or 0),
            'currency': acct.balances.iso_currency_code or 'GBP',
        }
        for acct in response.accounts
    ]
