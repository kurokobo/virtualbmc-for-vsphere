FROM python:3.10-slim
ARG UID=1000

WORKDIR /vsbmc
RUN useradd -d /vsbmc -u ${UID} vsbmc && \
    chown -R vsbmc:root /vsbmc && \
    chmod -R 770 /vsbmc

RUN python -m pip install vbmc4vsphere

USER vsbmc

ENTRYPOINT ["vsbmcd"]
CMD ["--foreground"]
