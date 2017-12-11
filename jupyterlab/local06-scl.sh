#!/bin/sh
for i in rh-git29 devtoolset-6; do
    source scl_source enable ${i}
done
