#!/bin/sh
origdir=$(pwd)
# Using a different environment variable allows us to retain backwards
#  compatibility
if [ -n "${AUTO_REPO_SPECS}" ]; then
    urls=${AUTO_REPO_SPECS}
else
    urls=${AUTO_REPO_URLS:="https://github.com/lsst-sqre/notebook-demo"}
fi
urllist=$(echo ${urls} | tr ',' ' ')
# Default branch is only used in the absence of a branch spec in a URL
default_branch=${AUTO_REPO_BRANCH:="prod"}
# We need to have sourced ${LOADRSPSTACK} before we run this.  In the RSP
#  container startup environment, we always will have done so already.
# If LSST_CONDA_ENV_NAME is not set, we have not sourced it...so do.
if [ -z "${LSST_CONDA_ENV_NAME}" ]; then
    source ${LOADRSPSTACK}
fi
for url in ${urllist}; do
    branch=$(echo ${url} | cut -d '@' -f 2)
    # Only use default_branch if branch is not specified in the URL
    if [ "${branch}" == "${url}" ]; then
        branch=${default_branch}
    fi
    repo=$(echo ${url} | cut -d '@' -f 1)
    reponame=$(basename ${repo} .git)
    dirname="${HOME}/notebooks/${reponame}"
    if ! [ -d "${dirname}" ]; then
	cd "${HOME}/notebooks" && \
	    git clone ${repo} -b ${branch} && \
	    cd ${dirname}
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
cd "${origdir}" # In case we were sourced and not in a subshell
