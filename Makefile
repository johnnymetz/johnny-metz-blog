run:
	hugo server --gc -D -F

# https://adityatelange.github.io/hugo-PaperMod/posts/papermod/papermod-installation/#installingupdating-papermod
updatesubmodules:
	git submodule update --remote --merge

updateprecommit:
	pre-commit autoupdate
	pre-commit run --all-files
