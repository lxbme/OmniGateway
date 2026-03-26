#include <cstdlib>
#include <iostream>
#include <limits>
#include <memory>
#include <string>
#include <vector>

#include <google/protobuf/empty.pb.h>
#include <grpcpp/grpcpp.h>

#include "embedding.grpc.pb.h"

namespace {

int ReadIntEnv(const char* name, int default_value) {
  const char* value = std::getenv(name);
  if (value == nullptr || value[0] == '\0') {
    return default_value;
  }

  try {
    return std::stoi(value);
  } catch (...) {
    return default_value;
  }
}

std::string ReadStringEnv(const char* name, const char* default_value) {
  const char* value = std::getenv(name);
  if (value == nullptr || value[0] == '\0') {
    return default_value;
  }
  return value;
}

uint32_t HashText(const std::string& text, int counter) {
  uint32_t hash = 2166136261u;
  for (unsigned char ch : text) {
    hash ^= static_cast<uint32_t>(ch);
    hash *= 16777619u;
  }
  hash ^= static_cast<uint32_t>(counter);
  hash *= 16777619u;
  return hash;
}

std::vector<float> BuildVector(const std::string& text, int dimensions) {
  std::vector<float> values;
  values.reserve(dimensions);

  int counter = 0;
  while (static_cast<int>(values.size()) < dimensions) {
    uint32_t state = HashText(text, counter++);
    for (int i = 0; i < 8 && static_cast<int>(values.size()) < dimensions; ++i) {
      state = state * 1664525u + 1013904223u;
      const float normalized =
          static_cast<float>(state) /
              static_cast<float>(std::numeric_limits<uint32_t>::max()) * 2.0f -
          1.0f;
      values.push_back(normalized);
    }
  }

  return values;
}

class EmbeddingServiceImpl final : public embedding::EmbeddingService::Service {
 public:
  EmbeddingServiceImpl()
      : provider_(ReadStringEnv("LOCAL_EMBED_PROVIDER", "local-mock")),
        model_(ReadStringEnv("LOCAL_EMBED_MODEL", "local-mock-embedding")),
        dimensions_(ReadIntEnv("LOCAL_EMBED_DIMENSIONS",
                               ReadIntEnv("EMBED_DIMENSIONS", 1536))) {}

  grpc::Status GetEmbedding(grpc::ServerContext*,
                            const embedding::EmbeddingRequest* request,
                            embedding::EmbeddingResponse* response) override {
    const auto values = BuildVector(request->text(), dimensions_);
    for (float value : values) {
      response->add_embedding(value);
    }
    response->set_error("");
    return grpc::Status::OK;
  }

  grpc::Status Info(grpc::ServerContext*,
                    const google::protobuf::Empty*,
                    embedding::InfoResponse* response) override {
    response->set_provider(provider_);
    response->set_model(model_);
    response->set_dimensions(dimensions_);
    return grpc::Status::OK;
  }

 private:
  std::string provider_;
  std::string model_;
  int dimensions_;
};

}  // namespace

int main() {
  const std::string port = ReadStringEnv("SERVE_PORT", "50051");
  const std::string address = "0.0.0.0:" + port;

  EmbeddingServiceImpl service;
  grpc::ServerBuilder builder;
  builder.AddListeningPort(address, grpc::InsecureServerCredentials());
  builder.RegisterService(&service);

  std::unique_ptr<grpc::Server> server(builder.BuildAndStart());
  if (!server) {
    std::cerr << "[Error] Failed to start local embedding mock on port " << port
              << std::endl;
    return 1;
  }

  std::cout << "[Info] Local embedding mock listening on port " << port
            << std::endl;
  server->Wait();
  return 0;
}
