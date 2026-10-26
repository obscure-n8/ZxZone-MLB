<<<<<<< HEAD
FROM mysterysd/wzmlx:v3

WORKDIR /usr/src/app

RUN chmod 777 /usr/src/app

COPY requirements.txt .
RUN uv pip install --python /wzvenv/bin/python --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["bash", "start.sh"]
=======
FROM mysterysd/wzmlx:wzadv
# COPY --from=mysterysd/wzmlx:m-tools /usr/local /usr/local

WORKDIR /usr/src/app

COPY . .

ENTRYPOINT ["bash", "start.sh"]
>>>>>>> dc9f6270dd208eb8a6a5a49f09fd36dc91a1f363
