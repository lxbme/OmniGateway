FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libgrpc++-dev \
        libprotobuf-dev \
        pkg-config \
        protobuf-compiler-grpc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . ./local_embedding_service

RUN g++ -std=c++17 -O2 -pthread \
      local_embedding_service/src/main.cpp \
      local_embedding_service/src/embedding_service_impl.cpp \
      local_embedding_service/generated/embedding.pb.cc \
      local_embedding_service/generated/embedding.grpc.pb.cc \
      -I/app/local_embedding_service/include \
      -I/app/local_embedding_service/generated \
      $(pkg-config --cflags protobuf grpc++) \
      $(pkg-config --libs protobuf grpc++) \
      -o /usr/local/bin/local_embedding_service

EXPOSE 50051

CMD ["/usr/local/bin/local_embedding_service"]
