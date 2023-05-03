BLACK = black
BLACK_ARGS = --line-length 79

ISORT = isort
ISORT_ARGS = -rc 

image := us-docker.pkg.dev/genuine-polymer-165712/codecov/codecov-slack-app
release_version := `cat VERSION`
sha := $(shell git rev-parse --short=7 HEAD)
build_date ?= $(shell git show -s --date=iso8601-strict --pretty=format:%cd $$sha)

.PHONY: format
format:
	pip3 install black==22.3.0 isort
	$(BLACK) $(BLACK_ARGS) .
	$(ISORT) $(ISORT_ARGS) .

.PHONY: test

test:
	python3 -m pytest

build:
	docker build -f docker/Dockerfile . -t ${image}:${ENV}-${release_version}-${sha} \
	--label "org.label-schema.build-date"="$(build_date)" \
	--label "org.label-schema.name"="Codecov Slack App" \
	--label "org.label-schema.vendor"="Codecov" \
	--label "org.label-schema.version"="${release_version}-${sha}" \
	--squash

push:
	docker tag ${image}:${ENV}-${release_version}-${sha} ${image}:${ENV}-${release_version}-latest
	docker push ${image}:${ENV}-${release_version}-${sha}
	docker push ${image}:${ENV}-${release_version}-latest