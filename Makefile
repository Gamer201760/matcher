.PHONY: test lint typecheck run pre-commit proto-gen fix-grpc-autogen build build-scheduler
PROTO_DIR := proto
GEN_DIR := gen
PROTO_FILES := $(shell find $(PROTO_DIR) -name '*.proto')

help:
	@echo "Доступные команды:"
	@echo "  make install               - Установить все зависимости"
	@echo "  make build                 - Собрать контейнер"
	@echo "  make build-scheduler       - Собрать контейнер"
	@echo "  make test                  - Запустить тесты pytest"
	@echo "  make lint                  - Запустить линтер ruff"
	@echo "  make typecheck             - Запустить проверку типов mypy"
	@echo "  make pre-commit            - Запустить все проверки (lint, typecheck, test)"

install:
	uv sync

make run:
	uv run main.py

test:
	uv run pytest -v

lint:
	uv run ruff check .

typecheck:
	uv run mypy .

fix-grpc-autogen:
	./fix_grpc_autogen.sh $(GEN_DIR) $(GEN_DIR)

pre-commit: lint typecheck test

build:
	docker-buildx build --platform linux/amd64,linux/arm64 --tag gglamer/matcher:latest .

build-scheduler:
	docker-buildx build --platform linux/amd64,linux/arm64 -f Dockerfile.scheduler --tag gglamer/matcher-scheduler:latest .

proto-gen: 	
	@echo "🧹 Cleaning up old generated files..."
	@rm -rf $(GEN_DIR)
	@mkdir -p $(GEN_DIR)
	@touch $(GEN_DIR)/__init__.py
	uv run python -m grpc_tools.protoc \
		-I=$(PROTO_DIR) \
		--python_out=$(GEN_DIR) \
		--grpc_python_out=$(GEN_DIR) \
		--mypy_out=$(GEN_DIR) \
		 $(PROTO_FILES) \

	$(MAKE) fix-grpc-autogen
