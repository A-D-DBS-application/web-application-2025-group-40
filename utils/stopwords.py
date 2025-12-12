from app import db


def load_stopwords():
    """Load stopwords from Supabase if available, otherwise fall back to the local DB.

    Returns a set of lowercase stopwords (strings). This lets admins manage stopwords
    in the Supabase table named `stopwords` (expected column: `word`). If Supabase
    is not configured or an error occurs, the function will query the local
    database table `stopwords` and return those words.
    """
    words = set()

    # Prefer Supabase when configured in the app (non-blocking). Import here to
    # avoid circular import issues at module import time.
    try:
        from app import supabase, app as flask_app
    except Exception:
        supabase = None
        flask_app = None

    if supabase:
        try:
            # Try to select the `word` column from the stopwords table
            res = supabase.table('stopwords').select('word').execute()
            if getattr(res, 'error', None):
                if flask_app:
                    flask_app.logger.warning('Supabase stopwords fetch error: %s', res.error)
            else:
                data = getattr(res, 'data', None)
                if data:
                    for row in data:
                        # row is typically a dict like {'word': 'de'}
                        if isinstance(row, dict):
                            val = row.get('word')
                            if val:
                                words.add(str(val).strip().lower())
                        else:
                            # fallback: try to coerce
                            try:
                                words.add(str(row).strip().lower())
                            except Exception:
                                continue
        except Exception as e:
            if flask_app:
                flask_app.logger.exception('Error fetching stopwords from Supabase: %s', e)

    # If Supabase didn't return anything, or isn't configured, fall back to local DB
    if not words:
        try:
            result = db.session.execute("SELECT word FROM stopwords")
            for row in result:
                # row may be a Row object; access by attribute or index
                val = getattr(row, 'word', None)
                if val is None:
                    try:
                        val = row[0]
                    except Exception:
                        val = None
                if val:
                    words.add(str(val).strip().lower())
        except Exception as e:
            # If even the DB fallback fails, log and return empty set
            try:
                from app import app as flask_app
                flask_app.logger.exception('Error loading stopwords from local DB: %s', e)
            except Exception:
                pass

    return words


if __name__ == '__main__':
    # quick local test helper
    print(load_stopwords())
