BLACK = black
BLACK_ARGS = --line-length 79

ISORT = isort
ISORT_ARGS = -rc 


.PHONY: format
format:
	pip3 install black==22.3.0 isort
	$(BLACK) $(BLACK_ARGS) .
	$(ISORT) $(ISORT_ARGS) .

.PHONY: test

test:
	python3 -m pytest
