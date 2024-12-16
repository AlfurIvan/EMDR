FROM python:3.13-alpine

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt

RUN python manage.py makemigrations
RUN python manage.py migrate

RUN python manage.py loaddata data.json

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
