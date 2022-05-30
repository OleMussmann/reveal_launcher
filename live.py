#!/usr/bin/env python3

import livereload

server = livereload.Server()
server.watch(".")
server.serve(port=8000)
