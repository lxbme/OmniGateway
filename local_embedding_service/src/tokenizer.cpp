#include "tokenizer.h"

#include <algorithm>
#include <cctype>
#include <sstream>

namespace embedding_service {

SimpleTokenizer::SimpleTokenizer(int max_length) : max_length_(max_length) {}

std::vector<int64_t> SimpleTokenizer::Encode(const std::string& text) {
  std::vector<int64_t> token_ids;
  token_ids.reserve(max_length_);

  std::string normalized = text;
  std::transform(normalized.begin(), normalized.end(), normalized.begin(),
                 [](unsigned char c) { return std::tolower(c); });

  std::istringstream stream(normalized);
  std::string word;
  int count = 0;
  while (stream >> word && count < max_length_) {
    uint32_t hash = 2166136261u;
    for (unsigned char ch : word) {
      hash ^= static_cast<uint32_t>(ch);
      hash *= 16777619u;
    }
    token_ids.push_back(static_cast<int64_t>(hash % 30000));
    ++count;
  }

  if (token_ids.empty()) {
    token_ids.push_back(0);
  }

  return token_ids;
}

TokenPairEncoding ITokenizer::EncodePair(const std::string& text_a,
                                         const std::string& text_b) {
  std::string combined = text_a + " " + text_b;
  auto ids = Encode(combined);
  TokenPairEncoding result;
  result.input_ids = ids;
  result.token_type_ids.assign(ids.size(), 0);
  result.attention_mask.assign(ids.size(), 1);

  int max_len = GetMaxLength();
  if (static_cast<int>(result.input_ids.size()) > max_len) {
    result.input_ids.resize(static_cast<size_t>(max_len));
    result.token_type_ids.resize(static_cast<size_t>(max_len));
    result.attention_mask.resize(static_cast<size_t>(max_len));
  } else {
    size_t pad = static_cast<size_t>(max_len) - result.input_ids.size();
    result.input_ids.insert(result.input_ids.end(), pad, 0);
    result.token_type_ids.insert(result.token_type_ids.end(), pad, 0);
    result.attention_mask.insert(result.attention_mask.end(), pad, 0);
  }
  return result;
}

}  // namespace embedding_service
