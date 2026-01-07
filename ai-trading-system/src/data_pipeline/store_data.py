"""Store data to disk or a database."""

def store_to_csv(df, path: str):
    """Write processed dataframe to CSV path (stub)."""
    with open(path, "w", encoding="utf-8") as f:
        f.write("# csv placeholder\n")
