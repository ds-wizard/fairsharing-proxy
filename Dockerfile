FROM python:3.9-slim
WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY . /app

RUN pip install .

CMD ["uvicorn", "fairsharing_proxy:app", \
     "--host", "0.0.0.0", \
     "--port", "80", \
     "--proxy-headers", \
     "--no-use-colors"]
