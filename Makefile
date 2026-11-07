.DEFAULT_GOAL := help

# Pinned so the local gate and CI validate with the same rules.
CLAUDE_CODE_VERSION := 2.1.310
ZIZMOR_VERSION := 1.27.0
CLAUDE := npx -y @anthropic-ai/claude-code@$(CLAUDE_CODE_VERSION)

.PHONY: install
install: ## Install for development
	uv sync --all-groups

.PHONY: format
format: ## Auto-format code
	uv run ruff check --fix
	uv run ruff format

.PHONY: lint
lint: ## Lint code (no auto-fix)
	uv run ruff check
	uv run ruff format --check

.PHONY: typecheck
typecheck: ## Type check with pyright
	uv run pyright

.PHONY: test
test: ## Run unit tests (no network)
	uv run pytest -q

.PHONY: test-live
test-live: ## Check the published mcpscore CLI's report against the skill (network)
	uv run pytest -q -m live

.PHONY: check
check: ## Check manifests, skill, evals and changelog agree with each other
	uv run python scripts/check_plugin.py --report tests/fixtures/report-deepwiki.json

.PHONY: validate
validate: ## Validate the marketplace and the plugin with Claude Code's validator
	$(CLAUDE) plugin validate .
	$(CLAUDE) plugin validate --profile directory plugins/mcpscore

.PHONY: workflows
workflows: ## Audit the GitHub workflows with zizmor (pinned, as CI does)
	uvx zizmor==$(ZIZMOR_VERSION) --no-progress .github/workflows/

.PHONY: all
all: lint typecheck test check validate workflows ## Run all checks (mirrors CI)

.PHONY: eval
eval: ## Run the agent eval suite: real Claude sessions on your account (costs money)
	cd plugins/mcpscore && claude plugin eval . --scaffold --allow-tools "Bash(uvx mcpscore@latest:*)" "Bash(pipx run mcpscore:*)" Edit

.PHONY: eval-smoke
eval-smoke: ## One run per case, no baseline arm
	cd plugins/mcpscore && claude plugin eval . --scaffold --runs 1 --ablation none --allow-tools "Bash(uvx mcpscore@latest:*)" "Bash(pipx run mcpscore:*)" Edit

.PHONY: help
help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'
