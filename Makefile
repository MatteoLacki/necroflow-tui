PYTHON   = .venv/bin/python
NF_TUI   = $(abspath .venv/bin/necroflow-tui)
NF_SRC   = $(abspath ../nectroflow/necroflow)
STAMP    = .venv/.stamp

$(STAMP): pyproject.toml
	python3 -m venv .venv
	.venv/bin/pip install -e $(NF_SRC) -e ../panelview -e . -q
	touch $(STAMP)

# Run the necroalchemy example from the necroflow root so that the relative
# .pipeline path in necroalchemy_job.toml resolves correctly.
example: $(STAMP)
	cd $(NF_SRC) && $(NF_TUI) \
	    --outdir $(abspath .)/examples/output \
	    examples/necroalchemy_job.toml

clean-example:
	rm -rf examples/output

.PHONY: example clean-example
