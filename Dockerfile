FROM mysterysd/wzmlx:wzadv
# COPY --from=mysterysd/wzmlx:m-tools /usr/local /usr/local

WORKDIR /usr/src/app

COPY . .

ENTRYPOINT ["bash", "start.sh"]
