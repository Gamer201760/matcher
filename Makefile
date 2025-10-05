.PHONY: test lint typecheck run pre-commit proto-gen

PROTO_DIR := proto
GEN_DIR := gen

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
	@mkdir -p $(GEN_DIR)
	uv run python -m grpc_tools.protoc \
	    -I=$(PROTO_DIR) \
	    --python_out=$(GEN_DIR) \
	    --grpc_python_out=$(GEN_DIR) \
	    $(PROTO_DIR)/group/*.proto
	uv run python -m grpc_tools.protoc \
	    -I=$(PROTO_DIR) \
	    --python_out=$(GEN_DIR) \
	    --grpc_python_out=$(GEN_DIR) \
	    $(PROTO_DIR)/form/*.proto
