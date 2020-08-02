passwd=password

python manage.py migrate
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser --username=Darmo --email=darmo117@gmail.com <<!
$passwd
$passwd
y
!
