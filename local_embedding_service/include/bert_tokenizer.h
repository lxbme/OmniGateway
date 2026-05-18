#ifndef LOCAL_EMBEDDING_SERVICE_BERT_TOKENIZER_H_
#define LOCAL_EMBEDDING_SERVICE_BERT_TOKENIZER_H_

#include "tokenizer.h"

#include <string>
#include <unordered_map>
#include <vector>

namespace embedding_service {

class BertTokenizer : public ITokenizer {
 public:
  BertTokenizer(const std::string& vocab_path, int max_length = 512);

  bool LoadVocab(const std::string& vocab_path, std::string* error_msg);

  std::vector<int64_t> Encode(const std::string& text) override;
  TokenPairEncoding EncodePair(const std::string& text_a,
                               const std::string& text_b) override;
  int GetMaxLength() const override { return max_length_; }

 private:
  std::unordered_map<std::string, int64_t> vocab_;
  int max_length_;

  int64_t cls_id_ = 101;
  int64_t sep_id_ = 102;
  int64_t pad_id_ = 0;
  int64_t unk_id_ = 100;

  static std::string Normalize(const std::string& text);
  std::vector<std::string> BasicTokenize(const std::string& text) const;
  std::vector<std::string> WordPiece(const std::string& word) const;
  std::vector<int64_t> TokenizeToIds(const std::string& text);
};

}  // namespace embedding_service

#endif  // LOCAL_EMBEDDING_SERVICE_BERT_TOKENIZER_H_
