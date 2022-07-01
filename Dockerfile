FROM python
LABEL maintainer="sunyiwei24601@gmail.com"
RUN pip3 install -r requirements.txt
COPY . /src
WORKDIR /src
ENTRYPOINT ["sh"]