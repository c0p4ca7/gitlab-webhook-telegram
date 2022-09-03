FROM python:3.9-alpine3.16

WORKDIR /app
COPY ["./*.py", "./*.json", "./requirements.txt","./"]

RUN pip install -U pip && \
    pip install -U -r requirements.txt

EXPOSE 8080

CMD python main.py
