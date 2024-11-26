BLACK = black
BLACK_ARGS = --line-length 79

ISORT = isort
ISORT_ARGS = -rc

image := us-docker.pkg.dev/genuine-polymer-165712/codecov/codecov-slack-app
release_version := `cat VERSION`
sha := $(shell git rev-parse --short=7 HEAD)
build_date ?= $(shell git show -s --date=iso8601-strict --pretty=format:%cd $$sha)
REQUIREMENTS_TAG := requirements-v1-$(shell sha1sum requirements.txt | cut -d ' ' -f 1)-$(shell sha1sum Dockerfile.requirements | cut -d ' ' -f 1)
ENV ?= local

.PHONY: gcr.auth
gcr.auth: # Used to run the tests
gcr.auth:
	gcloud auth configure-docker us-docker.pkg.dev

.PHONY: gcr.login
gcr.login: # Used to run the tests
gcr.login:
	gcloud auth login
	$(MAKE) gcr.auth

.PHONY: format
format: # Used to run formatting
format:
	pip3 install black==22.3.0 isort
	$(BLACK) $(BLACK_ARGS) .
	$(ISORT) $(ISORT_ARGS) .

.PHONY: test
test: # Used to run the tests
test:
	python3 -m pytest

.PHONY: build-requirements
build-requirements: # Used to build requirements image if needed
build-requirements:
	# if docker pull succeeds, we have already build this version of
	# requirements.txt.  Otherwise, build and push a version tagged
	# with the hash of this requirements.txt
	docker pull ${image}:${REQUIREMENTS_TAG} || DOCKER_BUILDKIT=1 docker build \
		-f Dockerfile.requirements . \
		-t ${image}:${REQUIREMENTS_TAG} \
	&& docker push ${image}:${REQUIREMENTS_TAG}; true


.PHONY: build
build: # Used to build the app
build:
	DOCKER_BUILDKIT=1 docker build -f Dockerfile . -t ${image}:${ENV}-${sha} \
	--build-arg REQUIREMENTS_IMAGE=${image}:${REQUIREMENTS_TAG} \
	--label "org.label-schema.build-date"="$(build_date)" \
	--label "org.label-schema.name"="Codecov Slack App" \
	--label "org.label-schema.vendor"="Codecov" \
	--label "org.label-schema.version"="${release_version}-${sha}"

.PHONY: local
local: # Used to build the local app
local:
	docker pull ${image}:${REQUIREMENTS_TAG} || DOCKER_BUILDKIT=1 docker build \
    		-f Dockerfile.requirements . \
    		-t ${image}:${REQUIREMENTS_TAG}
	$(MAKE) build
	docker tag ${image}:${ENV}-${release_version}-${sha} ${image}:latest

.PHONY: up
up: # Used to bring up the local app
up:
	touch .env
	docker image inspect ${image}:${ENV}-${release_version}-${sha} &>/dev/null || $(MAKE) local
	docker-compose up -d

.PHONY: push
push: # Used to build the app
push:
	docker tag ${image}:${ENV}-${sha} ${image}:${ENV}-latest
	docker push ${image}:${ENV}-${sha}
	docker push ${image}:${ENV}-latest
