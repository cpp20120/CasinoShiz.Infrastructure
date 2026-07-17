SHELL := /usr/bin/env bash

.PHONY: lint template ansible-check

lint:
	helm lint charts/casinoshiz

template:
	helm template casinoshiz charts/casinoshiz \
	  -f charts/casinoshiz/values-production.yaml

ansible-check:
	ansible-playbook -i ansible/inventory/hosts.yml \
	  ansible/playbooks/site.yml --syntax-check
