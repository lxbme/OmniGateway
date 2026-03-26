# Contribute Guide

本仓库当前主要面向两类开发工作：

- `integration_tests/` 下的端到端链路测试开发
- `local_embedding_service/` 下的本地 C++ gRPC mock 服务开发

以下流程请优先遵守，避免不同目录的开发方式不一致。

## 基础流程

首次拉取或更新子模块后，先执行：

```bash
make init
```

同步主仓库与子模块时，执行：

```bash
make pull
```

*每次开始开发前都需要执行本命令*

本地启动整套服务时，执行：

```bash
make deploy
```

停止并清理容器、网络、卷时，执行：

```bash
make down
```

运行端到端测试时，执行：

```bash
make test-e2e
```

或直接执行：

```bash
pytest integration_tests -v
```

## `integration_tests/` 开发规范

`integration_tests/` 下的测试应以 `pytest` 作为统一入口，保证在仓库根目录执行 `pytest` 或 `make test-e2e` 时都能被收集并运行。

建议遵循以下约定：

- 测试文件使用 `.py` 结尾，并放在 `integration_tests/` 目录下。
- 测试应尽量覆盖真实链路，不绕过 `docker compose`、`gateway`、`auth-service`、`completion-service` 和 `embedding-service`。
- 同一个测试文件应尽量自包含，包括启动依赖、等待服务就绪、创建 token、发起请求、清理环境。
- 若测试依赖固定 prompt，请保证断言稳定，避免依赖随机输出。
- 对同一 prompt 的重复请求测试，至少验证多次结果一致，避免链路存在不稳定行为。

当前参考实现见 `integration_tests/basic.py`。

## `local_embedding_service/` 开发规范

`local_embedding_service/` 当前是一个本地 C++ gRPC mock，用于替代未来正式的 C++ embedding 服务。

开发时请遵循以下约定：

- 服务接口必须兼容 `embedding.EmbeddingService`（embedding.proto）。
- 默认监听端口保持为 `50051`，以兼容 `docker-compose.yml` 中的 `embedding-service` 定义。
- `Info` 返回的 `provider`、`model`、`dimensions` 必须与环境变量语义保持一致。
- `GetEmbedding` 返回值应稳定可复现，避免相同输入产生不同向量，影响缓存链路验证。
- 如需调整 proto，请优先保持与网关侧契约一致，再同步更新生成产物。

当前目录中的以下文件属于服务实现的一部分：

- `main.cpp`
- `embedding.proto`
- `embedding.pb.cc`
- `embedding.pb.h`
- `embedding.grpc.pb.cc`
- `embedding.grpc.pb.h`
- `Dockerfile`

## Proto 与生成产物约定

`local_embedding_service/embedding.proto` 是本目录内的本地兼容副本，目的是让 C++ 服务可以独立维护和生成产物。

修改 proto 后，请同步更新生成文件：

- `embedding.pb.cc`
- `embedding.pb.h`
- `embedding.grpc.pb.cc`
- `embedding.grpc.pb.h`

不要只改 `main.cpp` 而不更新生成产物，否则 Docker 构建结果和源码会不一致。

## Docker 与联调要求

根目录 `docker-compose.yml` 是当前联调入口。

其中关键依赖关系如下：

- `embedding-service` 使用 `local_embedding_service/Dockerfile`
- `cache-service` 依赖 `embedding-service:50051`
- `completion-service` 依赖 `upstream-service`
- `gateway` 对外暴露 `8080`，管理接口暴露 `8081`

涉及这两类目录的改动后，至少执行一次：

```bash
make test-e2e
```

如果改动了 `local_embedding_service/` 的构建逻辑，建议额外执行一次：

```bash
docker compose build embedding-service cache-service
```

## 提交前检查

提交前至少确认以下几点：

- `make test-e2e` 可以通过
- `docker compose up -d --build` 可以成功拉起服务
- `docker compose down` 或 `make down` 后环境可正常清理
- 未提交本地运行数据目录
- 未提交临时调试文件

## 不建议的做法

- 不要在测试里写死只适用于个人机器的路径
- 不要绕过 `Makefile` 中已有的统一入口重复造命令
- 不要手动修改生成的 proto 产物内容后不回溯 proto 源文件
- 不要让 mock 行为依赖随机数而没有固定种子或稳定映射
