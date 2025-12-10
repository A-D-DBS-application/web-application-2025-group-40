from app import db

def load_stopwords_from_db():
    # Voer SQL uit om alle woorden op te halen
    result = db.session.execute("SELECT word FROM stopwords")
    
    # Zet alles om naar een Python-set voor snelle lookup
    return {row.word for row in result}
