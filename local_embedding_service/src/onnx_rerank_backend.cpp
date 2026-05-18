#include "onnx_rerank_backend.h"
#include "bert_tokenizer.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>

#ifdef ENABLE_ONNX_BACKEND
#include <onnxruntime_cxx_api.h>
#endif

namespace embedding_service {

std::string OnnxRerankBackend::ReadStringEnv(const char* name,
                                             const char* default_value) {
  const char* value = std::getenv(name);
  if (value == nullptr || value[0] == '\0') {
    return default_value;
  }
  return value;
}

int OnnxRerankBackend::ReadIntEnv(const char* name, int default_value) {
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

OnnxRerankBackend::OnnxRerankBackend()
    : provider_(ReadStringEnv("LOCAL_RERANK_PROVIDER", "onnx-runtime")),
      model_(
          ReadStringEnv("LOCAL_RERANK_MODEL", "cross-encoder-ms-marco-MiniLM-L6-v2")),
      model_path_(ReadStringEnv("LOCAL_RERANK_MODEL_PATH", "")),
      vocab_path_(ReadStringEnv("LOCAL_RERANK_VOCAB_PATH", "")),
      max_length_(ReadIntEnv("LOCAL_RERANK_MAX_LENGTH", 512)) {
#ifdef ENABLE_ONNX_BACKEND
  ort_env_ = nullptr;
  ort_session_ = nullptr;
  session_options_ = nullptr;
#endif
}

OnnxRerankBackend::~OnnxRerankBackend() = default;

bool OnnxRerankBackend::Init(std::string* error_msg) {
#ifndef ENABLE_ONNX_BACKEND
  *error_msg =
      "ONNX backend not compiled. Rebuild with -DEMBEDDING_WITH_ONNXRUNTIME=ON";
  return false;
#else
  if (model_path_.empty()) {
    *error_msg =
        "LOCAL_RERANK_MODEL_PATH environment variable not set. Please provide "
        "path to ONNX rerank model file.";
    return false;
  }

  // Determine vocab path: use explicit path or derive from model directory
  std::string vocab_path = vocab_path_;
  if (vocab_path.empty()) {
    size_t last_slash = model_path_.find_last_of("/\\");
    if (last_slash != std::string::npos) {
      vocab_path = model_path_.substr(0, last_slash + 1) + "vocab.txt";
    } else {
      vocab_path = "vocab.txt";
    }
  }

  try {
    ort_env_ = std::make_unique<Ort::Env>(ORT_LOGGING_LEVEL_WARNING,
                                          "RerankBackend");
    session_options_ = std::make_unique<Ort::SessionOptions>();
    session_options_->SetIntraOpNumThreads(1);
    session_options_->SetGraphOptimizationLevel(
        GraphOptimizationLevel::ORT_ENABLE_ALL);

    std::cout << "[Info] Loading rerank ONNX model from: " << model_path_
              << std::endl;
    ort_session_ = std::make_unique<Ort::Session>(
        *ort_env_, model_path_.c_str(), *session_options_);

    Ort::AllocatorWithDefaultOptions allocator;
    size_t num_input_nodes = ort_session_->GetInputCount();
    size_t num_output_nodes = ort_session_->GetOutputCount();

    input_names_str_.reserve(num_input_nodes);
    input_names_.reserve(num_input_nodes);
    for (size_t i = 0; i < num_input_nodes; ++i) {
      auto name_ptr = ort_session_->GetInputNameAllocated(i, allocator);
      input_names_str_.push_back(name_ptr.get());
      input_names_.push_back(input_names_str_.back().c_str());
    }

    output_names_str_.reserve(num_output_nodes);
    output_names_.reserve(num_output_nodes);
    for (size_t i = 0; i < num_output_nodes; ++i) {
      auto name_ptr = ort_session_->GetOutputNameAllocated(i, allocator);
      output_names_str_.push_back(name_ptr.get());
      output_names_.push_back(output_names_str_.back().c_str());
    }

    std::cout << "[Info] Rerank ONNX model loaded. Inputs: " << num_input_nodes
              << ", Outputs: " << num_output_nodes << std::endl;

    // Initialize tokenizer
    auto bert_tokenizer = std::make_unique<BertTokenizer>(vocab_path, max_length_);
    std::string tok_error;
    if (!bert_tokenizer->LoadVocab(vocab_path, &tok_error)) {
      std::cerr << "[Warning] Rerank tokenizer vocab load failed: " << tok_error
                << ". Using simple tokenizer fallback." << std::endl;
    }
    tokenizer_ = std::move(bert_tokenizer);

    return true;
  } catch (const Ort::Exception& e) {
    *error_msg = std::string("ONNX Runtime error: ") + e.what();
    return false;
  } catch (const std::exception& e) {
    *error_msg = std::string("Error loading rerank ONNX model: ") + e.what();
    return false;
  }
#endif
}

bool OnnxRerankBackend::Rerank(const std::string& query,
                               const std::vector<std::string>& documents,
                               int top_k,
                               std::vector<RerankItem>* results,
                               std::string* error_msg) {
#ifndef ENABLE_ONNX_BACKEND
  *error_msg = "ONNX backend not enabled";
  return false;
#else
  if (!ort_session_) {
    *error_msg = "ONNX session not initialized. Call Init() first.";
    return false;
  }

  results->clear();
  if (documents.empty()) {
    return true;
  }

  results->reserve(documents.size());

  try {
    Ort::MemoryInfo memory_info =
        Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);

    for (size_t i = 0; i < documents.size(); ++i) {
      auto encoded = tokenizer_->EncodePair(query, documents[i]);
      int64_t seq_len = static_cast<int64_t>(encoded.input_ids.size());

      std::vector<int64_t> shape = {1, seq_len};

      std::vector<Ort::Value> input_tensors;
      // input_ids
      input_tensors.push_back(Ort::Value::CreateTensor<int64_t>(
          memory_info, encoded.input_ids.data(), encoded.input_ids.size(),
          shape.data(), shape.size()));
      // attention_mask
      input_tensors.push_back(Ort::Value::CreateTensor<int64_t>(
          memory_info, encoded.attention_mask.data(),
          encoded.attention_mask.size(), shape.data(), shape.size()));
      // token_type_ids
      input_tensors.push_back(Ort::Value::CreateTensor<int64_t>(
          memory_info, encoded.token_type_ids.data(),
          encoded.token_type_ids.size(), shape.data(), shape.size()));

      auto output_tensors =
          ort_session_->Run(Ort::RunOptions{nullptr}, input_names_.data(),
                            input_tensors.data(), input_tensors.size(),
                            output_names_.data(), output_names_.size());

      if (output_tensors.empty()) {
        *error_msg = "Rerank ONNX model returned no output";
        results->clear();
        return false;
      }

      float score = ExtractScore(output_tensors[0]);
      results->push_back(
          {static_cast<int>(i), documents[i], score});
    }

    // Sort by score descending
    std::stable_sort(results->begin(), results->end(),
                     [](const RerankItem& a, const RerankItem& b) {
                       return a.score > b.score;
                     });

    // Apply top_k
    int limit = top_k;
    if (limit <= 0 || limit > static_cast<int>(results->size())) {
      limit = static_cast<int>(results->size());
    }
    results->resize(static_cast<size_t>(limit));

    return true;
  } catch (const Ort::Exception& e) {
    *error_msg = std::string("ONNX rerank inference error: ") + e.what();
    results->clear();
    return false;
  } catch (const std::exception& e) {
    *error_msg = std::string("Error during rerank: ") + e.what();
    results->clear();
    return false;
  }
#endif
}

#ifdef ENABLE_ONNX_BACKEND
float OnnxRerankBackend::ExtractScore(Ort::Value& output_tensor) {
  float* data = output_tensor.GetTensorMutableData<float>();
  auto shape = output_tensor.GetTensorTypeAndShapeInfo().GetShape();

  // Shape is typically [1, 1] (single score) or [1, 2] (logits)
  size_t elem_count = 1;
  for (auto dim : shape) {
    if (dim > 0) elem_count *= static_cast<size_t>(dim);
  }

  if (elem_count >= 2) {
    // 2-element logits: apply softmax, return probability of class 1 (relevant)
    float logit0 = data[0];
    float logit1 = data[1];
    float max_logit = std::max(logit0, logit1);
    float exp0 = std::exp(logit0 - max_logit);
    float exp1 = std::exp(logit1 - max_logit);
    return exp1 / (exp0 + exp1);
  }

  // Single score
  return data[0];
}
#endif

}  // namespace embedding_service
