"""
Streamlit application for recording investment transactions, products and
purposes.

This module defines the user interface for managing investments.  It exposes
three pages accessible via the sidebar:

* **Record Transaction** – Capture a new purchase of an investment product.
* **Add Product** – Register a new investment product in the catalogue.
* **Add Purpose** – Define a new investment goal or purpose.

The app relies on the utility functions defined in ``db_utils.py`` to
communicate with the underlying database.  To run the app locally, ensure
that a ``DATABASE_URL`` environment variable is defined pointing to your
database (for example, ``sqlite:///investments.db`` for SQLite or
``postgresql+psycopg2://user:pass@host:port/dbname`` for PostgreSQL).

Example usage::

    $ export DATABASE_URL=sqlite:///./investments.db
    $ streamlit run app.py

"""

from __future__ import annotations

import datetime
import os

import pandas as pd
import streamlit as st

import db_utils


def main() -> None:
    # Set a descriptive title and configure page layout.
    st.set_page_config(page_title="Investments Manager", layout="centered")
    
    if "engine" not in st.session_state:
        try:
            st.session_state["engine"] = db_utils.get_engine()
        except RuntimeError as exc:
            st.error(str(exc))
            return
    if "products" not in st.session_state:
        st.session_state["products"] = db_utils.get_products()
    if "purposes" not in st.session_state:
        st.session_state["purposes"] = db_utils.get_purposes()

    st.title("💼 Investment Transactions Manager")

    # Provide navigation via sidebar.
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select an action",
        ("Record Transaction", "Add Product", "Add Purpose"),
    )

    if page == "Record Transaction":
        record_transaction_page()
    elif page == "Add Product":
        add_product_page()
    elif page == "Add Purpose":
        add_purpose_page()

    # Optionally show recent transactions at bottom of any page.


def show_recent_transactions():
    with st.expander("Recent transactions"):
        transactions = db_utils.get_latest_transactions(limit=10)
        if transactions:
            df = pd.DataFrame(
                transactions,
                columns=["Date", "Product", "Units", "Buying Value", "Purpose"],
            )
            st.dataframe(df)
        else:
            st.info("No transactions recorded yet.")

def record_transaction_page() -> None:
    """Render the page for recording a new investment transaction."""

    products = st.session_state["products"]
    purposes = st.session_state["purposes"]

    st.header("Record a new transaction")
    st.write(
        "Log your purchase of a financial product.  Please select the date, product, "
        "number of units purchased, total cost and the associated purpose.  "
        "If the product or purpose you need does not exist, navigate to the "
        "appropriate page to add it first."
    )


    if not products:
        st.warning(
            "No products available.  Please add a product via the 'Add Product' page first."
        )
        return
    if not purposes:
        st.warning(
            "No purposes defined.  Please add a purpose via the 'Add Purpose' page first."
        )
        return

    with st.form("transaction_form"):
        date = st.date_input("Date", value=datetime.date.today())
        # convert to string for DB insertion
        date_str = date.isoformat()

        product_names = [p[0] for p in products]
        product = st.selectbox("Product", product_names, index=None)

        units = st.number_input("Units", min_value=1, step=1, format="%d")
        buying_value = st.number_input("Value at purchase", min_value=0.00, format="%0.2f", value=0.00)

        purpose_names = [p[0] for p in purposes]
        purpose = st.selectbox("Purpose", purpose_names, index=None)

        submitted = st.form_submit_button("Record Transaction")
        if submitted:
            try:
                is_valid_transaction = db_utils.validate_investment(
                    date=date_str,
                    product=product,
                    units=units,
                    buying_value=buying_value,
                    purpose=purpose,
                )
                if is_valid_transaction:
                    db_utils.insert_investment(
                        date=date_str,
                        product=product,
                        units=int(units),
                        buying_value=int(buying_value),
                        purpose=purpose,
                    )
                    st.success("Transaction recorded successfully!")
            except Exception as exc:
                st.error(f"Error recording transaction: {exc}")        

    show_recent_transactions()

def add_product_page() -> None:
    """Render the page for adding a new product."""

    st.header("Add a new product")
    st.write(
        "Register a new financial product.  Provide its name, current unit value, "
        "type, index and TASE number.  The name must be unique within the database."
    )

    with st.form("product_form"):
        product_name = st.text_input("Product name")
        type_ = st.text_input("Type")
        index = st.text_input("Index")
        tase_number = st.text_input("TASE number")

        submitted = st.form_submit_button("Add Product")
        if submitted:
            try:
                is_valid_product = db_utils.validate_product(
                    product=product_name,
                    type_=type_,
                    tase_number=tase_number,
                )
                if is_valid_product:
                    db_utils.insert_product(
                        product=product_name,
                        type_=type_,
                        index=index,
                        tase_number=tase_number,
                    )
                    st.session_state.pop("products")
                    st.success(f"Product '{product_name}' added successfully!")
            except Exception as exc:
                st.error(f"Error adding product: {exc}")

def add_purpose_page() -> None:
    """Render the page for adding a new purpose."""

    st.header("Add a new purpose")
    st.write(
        "Define a new investment goal.  Provide a name and optionally a needed amount "
        "to quantify the target.  The name must be unique within the database."
    )

    with st.form("purpose_form"):
        purpose_name = st.text_input("Purpose name")
        needed_amount = st.number_input(
            "Needed amount", min_value=0, step=1, format="%d", value=0
        )
        
        
        submitted = st.form_submit_button("Add Purpose")
        if submitted:
            try:
                is_valid_purpose = db_utils.validate_purpose(
                    purpose=purpose_name,
                    needed_amount=needed_amount
                )
                if is_valid_purpose:
                    db_utils.insert_purpose(
                        purpose=purpose_name, needed_amount=int(needed_amount)
                    )

                    st.session_state.pop("purposes")
                    st.success(f"Purpose '{purpose_name}' added successfully!")
            except Exception as exc:
                st.error(f"Error adding purpose: {exc}")


if __name__ == "__main__":
    main()