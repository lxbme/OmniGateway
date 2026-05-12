#ifndef LOCAL_EMBEDDING_SERVICE_MOCK_RERANK_BACKEND_H_
#define LOCAL_EMBEDDING_SERVICE_MOCK_RERANK_BACKEND_H_

#include "rerank_backend.h"

#include <string>
#include <vector>

namespace embedding_service {

class MockRerankBackend : public IRerankBackend {
 public:
  MockRerankBackend();

  bool Init(std::string* error_msg) override;

  bool Rerank(const std::string& query,
              const std::vector<std::string>& documents, int top_k,
              std::vector<RerankItem>* results,
              std::string* error_msg) override;

  std::string GetProvider() const override { return provider_; }
  std::string GetModel() const override { return model_; }

 private:
  std::string provider_;
  std::string model_;

  static std::string ReadStringEnv(const char* name,
                                   const char* default_value);
  static std::vector<std::string> Tokenize(const std::string& text);
};

}  // namespace embedding_service

#endif  // LOCAL_EMBEDDING_SERVICE_MOCK_RERANK_BACKEND_H_
