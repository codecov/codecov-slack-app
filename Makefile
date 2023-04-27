BLACK = black
BLACK_ARGS = --line-length 79 --target-version py38

ISORT = isort
ISORT_ARGS = -rc 


.PHONY: format
format:
	$(BLACK) $(BLACK_ARGS) .
	$(ISORT) $(ISORT_ARGS) .

.PHONY: test

test:
	python3 -m pytest
