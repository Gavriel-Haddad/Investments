import sqlalchemy as sa
import pandas as pd
import os

from prices_fetcher import get_price_for_code


DB_URL = os.getenv("DB_URL")
ENGINE = sa.create_engine(DB_URL)

TABLE = "products"
CODE_COLUMN = "tase_number"
CURRENT_VALUE_COLUMN = "current unit value"

def get_codes():
    return pd.read_sql(TABLE, ENGINE.connect())[CODE_COLUMN].tolist()

def update_db():
    codes = get_codes()
    update_query = """"""

    for code in codes:
        price = get_price_for_code(code)
        price = str(price)
        print(f"Price for {code}: {price}.")

        update_query += f"""
            update {TABLE}
            set "{CURRENT_VALUE_COLUMN}" = {price}
            where "{CODE_COLUMN}" like '{code}';
        """

    with ENGINE.begin() as con:
        con.execute(sa.text(update_query))


if __name__ == "__main__":
    try:
        update_db()
        print("All successfull")
    except Exception as e:
        print(f"There was a problem: {str(e)}")
 