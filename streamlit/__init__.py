"""Investment application package.

This package groups together the Streamlit app and its database utilities.  It
does not expose a public API; instead, run the application via

    streamlit run app.py

provided that you have installed the dependencies listed in
``requirements.txt`` and defined a ``DATABASE_URL`` environment variable.
"""

__all__ = ["db_utils"]