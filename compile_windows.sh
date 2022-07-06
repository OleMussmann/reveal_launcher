#!/bin/bash

python3 -m nuitka \
  --include-data-files=*.md=./ \
  --include-data-files=*.html=./ \
  --include-data-dir=./files=files \
  --include-data-dir=./reveal.js=reveal.js \
  --include-data-files=nlesc.template=./ \
  --include-data-files=config.yaml=./ \
  --include-data-files=tooltip.py=./ \
  --include-data-dir=./theme=theme \
  --include-data-files=azure.tcl=./ \
  --include-data-files=livereload.js=livereload/vendors/livereload.js \
  --enable-plugin=tk-inter \
  --onefile --standalone --remove-output \
  -o reveal.exe reveal.py
