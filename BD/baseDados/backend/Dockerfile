FROM python:3.11-slim

WORKDIR /baseDados

COPY . /baseDados

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "baseDados.py"]
