FROM ubuntu:22.04

# This toolchain has to setup a lot of stuff.
# python3, pip, go, rust, scala, jvm, npm, node

# Python3, pip3, jvm, gcc, g++
RUN apt update && apt install python3 python3-pip python-is-python3 wget openjdk-17-jdk-headless gnupg2 git gcc g++ make --no-install-recommends -y

# Go
RUN wget -O /tmp/go1.20.1.linux-amd64.tar.gz https://go.dev/dl/go1.20.1.linux-amd64.tar.gz && \
    tar -xzf /tmp/go1.20.1.linux-amd64.tar.gz -C /usr/local && \
    echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc && rm -rf /tmp/go1.20.1.linux-amd64.tar.gz

# Rust
RUN wget -q -O - https://sh.rustup.rs | sh -s -- -y --profile minimal

# Scala
RUN echo "deb https://repo.scala-sbt.org/scalasbt/debian all main" | tee /etc/apt/sources.list.d/sbt.list && \
    echo "deb https://repo.scala-sbt.org/scalasbt/debian /" | tee /etc/apt/sources.list.d/sbt_old.list && \
    wget -q -O - "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x2EE0EA64E40A89B84B2DF73499E82A75642AC823" | apt-key add && \
    apt update && apt install sbt --no-install-recommends -y && echo "alias sbt='sbt -Dsbt.rootdir=true'" >> ~/.bashrc

# Node and NPM
RUN wget -q -O - https://deb.nodesource.com/setup_18.x | bash - && \
    apt install -y nodejs
