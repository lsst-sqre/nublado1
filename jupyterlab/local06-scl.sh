#!/bin/sh
for i in rh-git29 devtoolset-6 rh-python36 rh-nodejs8; do
    source scl_source enable ${i}
done
