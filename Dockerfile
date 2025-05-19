# syntax=docker/dockerfile:1

FROM python:3.13-slim
RUN pip install --upgrade pip
RUN apt -y update

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

RUN pip install poetry

# Install only dependencies
COPY requirements.txt ./

# Install only code
COPY . .
RUN pip3 install -r requirements.txt

EXPOSE 8050

CMD ["python", "main.py"]