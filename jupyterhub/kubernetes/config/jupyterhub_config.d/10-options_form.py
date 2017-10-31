"""
Create the options form from our environment variables.
"""

import os

# Make options form
title = os.getenv("LAB_SELECTOR_TITLE")
if not title:
    title = "Container Image Selector"
imgspec = os.getenv("LAB_CONTAINER_NAMES")
if not imgspec:
    imgspec = "lsstsqre/jld-lab:latest"
imagelist = imgspec.split(',')
idescstr = os.getenv("LAB_CONTAINER_DESCS")
if not idescstr:
    idesc = imagelist
else:
    idesc = idescstr.split(',')
optform = "<label for=\"%s\">%s</label></br>\n" % (title, title)
for idx, img in enumerate(imagelist):
    optform += "      "
    optform += "<input type=\"radio\" name=\"kernel_image\""
    imgdesc = img
    try:
        imgdesc = idesc[idx]
    except IndexError:
        imgdesc = img
    if not imgdesc:
        imgdesc = img
    optform += " value=\"%s\">%s<br>\n" % (img, imgdesc)
# Options form built.
