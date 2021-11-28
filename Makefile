run:
	hugo server --gc -D -F

updatesubmodules:
	git submodule update --remote --merge

updateprecommit:
	pre-commit autoupdate
	pre-commit run --all-files
