"""
Database utility functions for the investment Streamlit application.

This module defines helper functions to interact with a relational database
containing investment transactions, products and purposes.  It uses
SQLAlchemy's ``create_engine`` to establish connections and executes raw
SQL statements for data manipulation.  No ORM models are declared – the
logic stays close to the underlying schema definitions supplied by the user.

The schema consists of three tables:

* ``purposes``: tracks investment goals and the amount of money needed for each.
* ``investments``: records individual purchases of investment products.
* ``products``: catalogues the financial instruments available for purchase.

Constants are provided for table and column names to avoid scattering
strings throughout the codebase.  Should the schema evolve, changes can be
made here and automatically propagated everywhere these constants are used.
"""

from __future__ import annotations

import os
import streamlit as st

from typing import Iterable, List, Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Result


# ---------------------------------------------------------------------------
# Configuration constants
#
# The names of the tables in the database.  If your database uses different
# names, change them here and throughout the rest of the application will
# pick up the new values.
PURPOSES_TABLE: str = "purposes"
INVESTMENTS_TABLE: str = "investments"
PRODUCTS_TABLE: str = "products"

DEFAULT_CONNECTION_URL_ENV = "DATABASE_URL"


def get_engine(connection_url: Optional[str] = None) -> Engine:
    """Create and return a SQLAlchemy Engine.

    Parameters
    ----------
    connection_url : str, optional
        Full database connection URL.  If not provided, the value is read
        from the ``DATABASE_URL`` environment variable.  The URL should
        include the database dialect and credentials, for example:

            postgresql+psycopg2://user:password@localhost:5432/mydb

    Returns
    -------
    sqlalchemy.engine.Engine
        An engine bound to the provided database.

    Raises
    ------
    RuntimeError
        If no connection URL is provided and the environment variable is not
        set.
    """

    url = connection_url or os.environ.get(DEFAULT_CONNECTION_URL_ENV)
    url = r'postgresql://neondb_owner:npg_QxLWPijMkC46@ep-rapid-forest-agjxejfn-pooler.c-2.eu-central-1.aws.neon.tech/investments?sslmode=require&channel_binding=require'
    if not url:
        raise RuntimeError(
            f"A database connection URL must be provided either via the ``connection_url`` "
            f"argument or the {DEFAULT_CONNECTION_URL_ENV} environment variable."
        )
    return create_engine(url)


def validate_investment(
    date: str,
    product: str,
    units: int,
    buying_value: int,
    purpose: str,
) -> None | bool:
    if not date:
        raise ValueError("Missing date")
    if not product:
        raise ValueError("Missing product")
    if not units:
        raise ValueError("Missing units")
    if not buying_value:
        raise ValueError("Missing buying_value")
    if not purpose:
        raise ValueError("Missing purpose")
    if product not in st.session_state["products"]:
        raise ValueError("Product does not exist")
    if purpose not in st.session_state["purposes"]:
        raise ValueError("Purpose does not exist")
    
    return True

def insert_investment(
    date: str,
    product: str,
    units: int,
    buying_value: int,
    purpose: str,
) -> None:
    """Insert a new transaction into the ``investments`` table.

    Parameters
    ----------
    date : str
        Timestamp of the transaction.  Should be a format accepted by the
        database (ISO-8601 works for PostgreSQL and SQLite).  The column
        expects a ``timestamp without time zone``.
    product : str
        The product identifier or name.  This must exist in the ``products``
        table.
    units : int
        Number of units bought.
    buying_value : int
        Total value spent on the purchase (e.g., in the account currency).
    purpose : str
        The purpose for which the investment was made.  Must exist in the
        ``purposes`` table.
    """

    query = text(
        f"INSERT INTO {INVESTMENTS_TABLE} (date, product, units, \"buying value\", purpose) "
        f"VALUES (:date, :product, :units, :buying_value, :purpose)"
    )
    with st.session_state["engine"].begin() as conn:
        conn.execute(
            query,
            {
                "date": date,
                "product": product,
                "units": units,
                "buying_value": buying_value,
                "purpose": purpose,
            },
        )


def validate_product(
    product: str,
    type_: str,
    tase_number: str,
) -> None | bool:
    if not product:
        raise ValueError("Missing product")
    if not type_:
        raise ValueError("Missing type_")
    if not tase_number:
        raise ValueError("Missing tase_number")
    if product in st.session_state["products"]:
        raise ValueError("Product already exist")
    
    return True

def insert_product(
    product: str,
    type_: str,
    index: str,
    tase_number: str,
) -> None:
    """Insert a new product into the ``products`` table."""

    query = text(
        f"INSERT INTO {PRODUCTS_TABLE} (product, \"current unit value\", type, index, tase_number) "
        f"VALUES (:product, :current_unit_value, :type, :index, :tase_number)"
    )
    with st.session_state["engine"].begin() as conn:
        conn.execute(
            query,
            {
                "product": product,
                "current_unit_value": 0.00,
                "type": type_,
                "index": index,
                "tase_number": tase_number,
            },
        )


def validate_purpose(purpose: str, needed_amount: int) -> None | bool:
    if not purpose:
        raise ValueError("Missing purpose name")
    if not needed_amount:
        raise ValueError("Missing needed_amount")
    if purpose in st.session_state["purposes"]:
        raise ValueError("Purpose already exist")
    
    return True
    
def insert_purpose(purpose: str, needed_amount: int) -> None:
    """Insert a new purpose into the ``purposes`` table."""

    query = text(
        f"INSERT INTO {PURPOSES_TABLE} (purpose, \"needed amount\") VALUES (:purpose, :needed_amount)"
    )
    with st.session_state["engine"].begin() as conn:
        conn.execute(query, {"purpose": purpose, "needed_amount": needed_amount})


def get_products() -> List[Tuple[str, float]]:
    """Retrieve available products and their current unit values.

    Returns a list of 2-tuples: (product_name, current_unit_value).
    """

    query = text(f"SELECT product, \"current unit value\" FROM {PRODUCTS_TABLE} ORDER BY product")
    with st.session_state["engine"].connect() as conn:
        result: Result = conn.execute(query)
        # In SQLAlchemy 1.4/2.x, a row can be treated as a tuple.  To access
        # columns by name, use the mapping interface.  Calling
        # ``result.mappings()`` yields dictionaries keyed by column name.
        rows = result.mappings().all()
        return [(r["product"], r["current unit value"]) for r in rows]


def get_purposes() -> List[Tuple[str, int]]:
    """Retrieve available purposes and their needed amounts.

    Returns a list of 2-tuples: (purpose_name, needed_amount).
    """

    query = text(f"SELECT purpose, \"needed amount\" FROM {PURPOSES_TABLE} ORDER BY purpose")
    with st.session_state["engine"].connect() as conn:
        result: Result = conn.execute(query)
        rows = result.mappings().all()
        return [(r["purpose"], r["needed amount"]) for r in rows]


def get_latest_transactions(limit: int = 10) -> List[Tuple[str, str, int, int, str]]:
    """Fetch the most recent transactions for display.

    Returns
    -------
    A list of tuples: (date, product, units, buying_value, purpose).
    """

    query = text(
        f"SELECT date, product, units, \"buying value\", purpose "
        f"FROM {INVESTMENTS_TABLE} ORDER BY date DESC LIMIT :limit"
    )
    with st.session_state["engine"].connect() as conn:
        result: Result = conn.execute(query, {"limit": limit})
        rows = result.mappings().all()
        return [
            (
                str(r["date"]),
                r["product"],
                r["units"],
                r["buying value"],
                r["purpose"],
            )
            for r in rows
        ]