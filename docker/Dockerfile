FROM python:3.9.2-slim

RUN pip3 install vbmc4vsphere

WORKDIR /vsbmc

RUN chown 1001:0 . && \
    chmod 770 .

USER 1001

ENTRYPOINT ["vbmcd"]
CMD ["--foreground"]

