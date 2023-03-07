BLACK = black 
BLACK_ARGS = --line-length 79 --target-version py38 

.PHONY: format
format:
	$(BLACK) $(BLACK_ARGS) .