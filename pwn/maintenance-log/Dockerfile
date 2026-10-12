FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    socat \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash ctf

WORKDIR /home/ctf

COPY chall .
COPY flag.txt .

RUN chown -R root:ctf /home/ctf && \
    chmod 750 /home/ctf/chall && \
    chmod 440 /home/ctf/flag.txt

USER ctf
EXPOSE 7312

CMD ["socat", "-T30", "TCP-LISTEN:7312,reuseaddr,fork", "EXEC:./chall,stderr"]