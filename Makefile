run:
	hugo server --gc -D -F

updatesubmodules:
	git submodule update --remote --merge
