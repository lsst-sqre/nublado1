#!/bin/sh
origdir=$(pwd)
urls=${AUTO_REPO_URLS:="https://github.com/lsst-sqre/notebook-demo"}
urllist=$(echo ${urls} | tr ',' ' ')
reponame="notebook-demo"
branch="prod"
for url in ${urllist}; do
    reponame=$(basename ${url} .git)
    dirname="${HOME}/notebooks/${reponame}"
    if ! [ -d "${dirname}" ]; then
	cd "${HOME}/notebooks" && \
	    git clone ${url} && \
	    cd ${dirname}
        git checkout prod
    else
	cd "${dirname}"
    fi
    if [ "$(pwd)" != "${dirname}" ]; then
	echo 1>&2 "Could not find repository in ${dirname}"
    else
	dirty=0
	otherbranch=0
	currentbr=$(git rev-parse --abbrev-ref HEAD)
	if [ "${currentbr}" != "${branch}" ]; then
	    otherbranch=1
	fi
	# If we have uncommited changes, stash, then we will pop back and
	#  apply after pull
	if ! git diff-files --quiet --ignore-submodules --; then
	    git stash
	    dirty=1
	fi
	# Do we need to change branches?
	if [ "${otherbranch}" -ne 0 ]; then
	    git checkout ${branch}
	fi
	git pull
	if [ "${otherbranch}" -ne 0 ]; then
	    git checkout ${currentbr}
	fi
	if [ "${dirty}" -ne 0 ]; then
	    git stash apply
	fi
    fi
done
cd "${origdir}"
