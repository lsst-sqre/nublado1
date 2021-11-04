#!/bin/sh
# OS-level packages that are not packaged by either RPM or Conda
mkdir -p ${srcdir}/thirdparty

# Install Hub
cd /tmp
V="2.14.2"
FN="hub-linux-amd64-${V}"
F="${FN}.tgz"
URL="https://github.com/github/hub/releases/download/v${V}/${F}"
cmd="curl -L ${URL} -o ${F}"
${cmd}
tar xpfz ${F}
install -m 0755 ${FN}/bin/hub /usr/bin
rm -rf ${F} ${FN}

# This is for Fritz, and my nefarious plan to make the "te" in "Jupyter"
#  TECO
# We switched from TECOC to Paul Koning's Python implementation because it
#  simplifies installation a bit.  I doubt anyone is going to complain.
cd ${srcdir}/thirdparty
source ${LOADRSPSTACK} # To get git
git clone https://github.com/pkoning2/pyteco.git
cd pyteco
install -m 0755 teco.py /usr/local/bin/teco

# The default terminal colors look bad in light mode.
cd ${srcdir}/thirdparty
git clone https://github.com/seebi/dircolors-solarized.git
cd dircolors-solarized
cp dircolors* /etc

# Install LaTeX from TexLive; in order to make jupyterlab exports
#  work, we lean heavily on this.  It may be possible to use a
#  Conda-packaged TeX but it kinda looks like there be dragons.
#
cd /tmp/tex
FN="install-tl-unx.tar.gz"
curl -L http://mirror.ctan.org/systems/texlive/tlnet/${FN} -o ${FN}
tar xvpfz ${FN}
./install-tl-*/install-tl --repository \
    http://ctan.math.illinois.edu/systems/texlive/tlnet \
    --profile /tmp/tex/texlive.profile
rm -rf /tmp/tex/${FN} /tmp/tex/install-tl*
# More TeX stuff we need for PDF export
PATH=/usr/local/texlive/2021/bin/x86_64-linux:${PATH}
tlmgr install caption lm adjustbox xkeyval collectbox xcolor \
    upquote eurosym ucs fancyvrb zapfding booktabs enumitem ulem palatino \
    mathpazo tcolorbox pgf environ trimspaces etoolbox float rsfs jknapltx \
    latexmk dvipng beamer parskip fontspec titling tools
# xetex, bizarrely, has to be installed on its own to get the binaries.
tlmgr install xetex
ln -s /usr/local/texlive/2021/bin/x86_64-linux/xelatex \
      /usr/local/texlive/2021/bin/x86_64-linux/bibtex \
      /usr/bin

# Clear our caches
rm -rf /tmp/* /tmp/.[0-z]* 
