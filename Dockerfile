FROM python:3-alpine AS compile-image
RUN apk add --no-cache build-base libffi-dev python3-dev
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY Docker/requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

FROM python:3-alpine AS build-image
WORKDIR /app
COPY . /app
COPY Docker/entrypoint.sh /entrypoint.sh
COPY --from=compile-image /opt/venv /opt/venv
RUN chmod 755 /entrypoint.sh
    
ENV PATH="/opt/venv/bin:$PATH"
EXPOSE 5000
ENTRYPOINT [ "/entrypoint.sh" ]
