FROM python:3.7.4

LABEL maintainer="Joe Saia <joe5saia@gmail.com>"

WORKDIR /app
COPY requirements.txt /app/
RUN pip --disable-pip-version-check --no-cache-dir install -r requirements.txt
RUN mkdir /app/data && chmod 777 /app/data

COPY . /app

CMD ["python", "make_asset_dataset.py"]