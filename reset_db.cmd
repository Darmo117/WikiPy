@echo off
del db.sqlite3
del WikiPy_app\SETUP_SECRET_KEY
del /S WikiPy_app\migrations\0*.py

python manage.py migrate
python manage.py makemigrations
python manage.py migrate
