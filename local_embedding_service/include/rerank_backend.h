#ifndef LOCAL_EMBEDDING_SERVICE_RERANK_BACKEND_H_
#define LOCAL_EMBEDDING_SERVICE_RERANK_BACKEND_H_

#include <string>
#include <vector>

namespace embedding_service {

struct RerankItem {
  int index;
  std::string document;
  float score;
};

class IRerankBackend {
 public:
  virtual ~IRerankBackend() = default;

  virtual bool Init(std::string* error_msg) = 0;

  virtual bool Rerank(const std::string& query,
                      const std::vector<std::string>& documents, int top_k,
                      std::vector<RerankItem>* results,
                      std::string* error_msg) = 0;

  virtual std::string GetProvider() const = 0;
  virtual std::string GetModel() const = 0;
};

}  // namespace embedding_service

#endif  // LOCAL_EMBEDDING_SERVICE_RERANK_BACKEND_H_
