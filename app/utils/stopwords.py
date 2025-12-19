from app import db


def load_stopwords():
    """Load stopwords from Supabase if available, otherwise fall back to the local DB.

    Returns a set of lowercase stopwords (strings). This lets admins manage stopwords
    in the Supabase table named `stopwords` (expected column: `word`). If Supabase
    is not configured or an error occurs, the function will query the local
    database table `stopwords` and return those words.
    """
    words = set()

    # Load stopwords from the local database table `stopwords`.
    try:
        result = db.session.execute("SELECT word FROM stopwords")
        for row in result:
            val = getattr(row, 'word', None)
            if val is None:
                try:
                    val = row[0]
                except Exception:
                    val = None
            if val:
                words.add(str(val).strip().lower())
    except Exception as e:
        # If DB query fails, log and return empty set
        try:
            from app import app as flask_app
            flask_app.logger.exception('Error loading stopwords from local DB: %s', e)
        except Exception:
            pass

    return words


if __name__ == '__main__':
    # quick local test helper
    print(load_stopwords())


# Backwards-compatible alias
def load_stopwords_from_db():
    """Compatibility wrapper for older callers.

    Historically the project exposed `load_stopwords_from_db`. Keep that name
    working by delegating to `load_stopwords()`.
    """
    return load_stopwords()
