FROM python
LABEL maintainer="sunyiwei24601@gmail.com"
COPY . /src
WORKDIR /src
RUN pip3 install -r /src/requirements.txt
ENTRYPOINT ["sh"]