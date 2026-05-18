#ifndef LOCAL_EMBEDDING_SERVICE_TOKENIZER_H_
#define LOCAL_EMBEDDING_SERVICE_TOKENIZER_H_

#include <string>
#include <vector>

namespace embedding_service {

struct TokenPairEncoding {
  std::vector<int64_t> input_ids;
  std::vector<int64_t> token_type_ids;
  std::vector<int64_t> attention_mask;
};

class ITokenizer {
 public:
  virtual ~ITokenizer() = default;

  virtual std::vector<int64_t> Encode(const std::string& text) = 0;

  virtual TokenPairEncoding EncodePair(const std::string& text_a,
                                       const std::string& text_b);

  virtual int GetMaxLength() const = 0;
};

class SimpleTokenizer : public ITokenizer {
 public:
  explicit SimpleTokenizer(int max_length = 512);
  ~SimpleTokenizer() override = default;

  std::vector<int64_t> Encode(const std::string& text) override;

  int GetMaxLength() const override { return max_length_; }

 private:
  int max_length_;
};

}  // namespace embedding_service

#endif  // LOCAL_EMBEDDING_SERVICE_TOKENIZER_H_
