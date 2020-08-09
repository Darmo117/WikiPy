@echo off
del db.sqlite3
del /S /Q WikiPy_app\migrations\0*.py

python manage.py migrate
python manage.py makemigrations
python manage.py migrate
