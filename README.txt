Food Bridge - run steps
1. python -m venv venv  &&  activate it
2. pip install -r requirements.txt
3. python manage.py makemigrations core
4. python manage.py migrate
5. python manage.py seed_locations
6. python manage.py createsuperuser   (optional, for /admin/)
7. python manage.py runserver  ->  http://127.0.0.1:8000/
