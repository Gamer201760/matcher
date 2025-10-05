.PHONY: test lint typecheck run pre-commit proto-gen
PROTO_DIR := proto
GEN_DIR := gen
PROTO_FILES := $(shell find $(PROTO_DIR) -name '*.proto')

help:
	@echo "Доступные команды:"
	@echo "  make install      - Установить все зависимости"
	@echo "  make test         - Запустить тесты pytest"
	@echo "  make lint         - Запустить линтер ruff"
	@echo "  make typecheck    - Запустить проверку типов mypy"
	@echo "  make pre-commit   - Запустить все проверки (lint, typecheck, test)"

install:
	uv sync

test:
	uv run pytest -v

lint:
	uv run ruff check .

typecheck:
	uv run mypy .

pre-commit: lint typecheck test

proto-gen:
	@echo "🧹 Cleaning up old generated files..."
	@rm -rf $(GEN_DIR)
	@mkdir -p $(GEN_DIR)
	@touch $(GEN_DIR)/__init__.py
	@echo "📝 Generating protobuf files..."
	@for proto in $(PROTO_FILES); do \
		echo "  Processing $$proto..."; \
		proto_dir=$$(dirname $$proto | sed "s|^$(PROTO_DIR)/||"); \
		uv run python -m grpc_tools.protoc \
			-I=$(PROTO_DIR)/$$proto_dir \
			--python_out=$(GEN_DIR) \
			--grpc_python_out=$(GEN_DIR) \
			--mypy_out=$(GEN_DIR) \
			$$(basename $$proto); \
	done
	@echo "✅ Proto generation complete!"
