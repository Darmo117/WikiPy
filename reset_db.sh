rm db.sqlite3
rm WikiPy/SETUP_SECRET_KEY
rm -rf WikiPy/migrations/[0-9]*.py

python manage.py migrate
python manage.py makemigrations
python manage.py migrate
