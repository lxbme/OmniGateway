#include "mock_rerank_backend.h"

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <unordered_set>

namespace embedding_service {

std::string MockRerankBackend::ReadStringEnv(const char* name,
                                             const char* default_value) {
  const char* value = std::getenv(name);
  if (value == nullptr || value[0] == '\0') {
    return default_value;
  }
  return value;
}

std::vector<std::string> MockRerankBackend::Tokenize(const std::string& text) {
  std::vector<std::string> tokens;
  std::string current;
  current.reserve(text.size());
  for (unsigned char ch : text) {
    if (std::isalnum(ch)) {
      current.push_back(static_cast<char>(std::tolower(ch)));
    } else if (!current.empty()) {
      tokens.push_back(current);
      current.clear();
    }
  }
  if (!current.empty()) {
    tokens.push_back(current);
  }
  return tokens;
}

MockRerankBackend::MockRerankBackend()
    : provider_(ReadStringEnv("LOCAL_RERANK_PROVIDER", "local-mock")),
      model_(ReadStringEnv("LOCAL_RERANK_MODEL", "local-mock-reranker")) {}

bool MockRerankBackend::Init(std::string* error_msg) {
  (void)error_msg;
  return true;
}

bool MockRerankBackend::Rerank(const std::string& query,
                               const std::vector<std::string>& documents,
                               int top_k,
                               std::vector<RerankItem>* results,
                               std::string* error_msg) {
  (void)error_msg;

  results->clear();
  if (query.empty() || documents.empty()) {
    return true;
  }

  // Build query token set
  auto query_tokens = Tokenize(query);
  std::unordered_set<std::string> query_set(query_tokens.begin(),
                                             query_tokens.end());

  std::vector<RerankItem> candidates;
  candidates.reserve(documents.size());

  for (size_t i = 0; i < documents.size(); ++i) {
    auto doc_tokens = Tokenize(documents[i]);
    std::unordered_set<std::string> doc_set(doc_tokens.begin(),
                                             doc_tokens.end());
    int overlap = 0;
    for (const auto& token : doc_set) {
      if (query_set.count(token) > 0) {
        ++overlap;
      }
    }
    candidates.push_back(
        {static_cast<int>(i), documents[i], static_cast<float>(overlap)});
  }

  std::stable_sort(candidates.begin(), candidates.end(),
                   [](const RerankItem& a, const RerankItem& b) {
                     return a.score > b.score;
                   });

  int limit = top_k;
  if (limit <= 0 || limit > static_cast<int>(candidates.size())) {
    limit = static_cast<int>(candidates.size());
  }

  results->assign(candidates.begin(),
                  candidates.begin() + static_cast<size_t>(limit));
  return true;
}

}  // namespace embedding_service
