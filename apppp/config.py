import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    #Haalt SECRET_KEY op uit de omgevingsvariabelen (.env)
    SECRET_KEY = os.environ.get('SECRET_KEY')

    #Haalt DATABASE_URL op uit de omgevingsvariabelen (.env)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    #SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:Group40Ufora%21@db.aicnouxwbuydippwukbs.supabase.co:5432/postgres'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    #Eventuele Supabase URL's / sleutels, mochten we deze later nodig hebben
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

