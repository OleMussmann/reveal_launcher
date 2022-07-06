#!/usr/bin/env python3

import livereload
import os
import jinja2
import threading
import time
#import socketserver
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

PORT = 8000
FOLDER = os.getcwd()


def refresh_template(template_name, running_refreshing):
    if running_refreshing.is_set():
        print("BUSY HERE!")
        return
    running_refreshing.set()
    all_files = os.listdir(FOLDER)
    content_files = [x for x in all_files if x != "index.html" and x.endswith(".html") or x.endswith(".md")]
    content_files.sort()

    settings = {}

    first_file = content_files[0]
    with open(first_file) as f:
        while True:
            line = f.readline().strip()
            if ":" in line:
                key, var = line.split(":", maxsplit=1)
                settings[key] = var.strip()
            if line.startswith("-->"):
                break

    with open(template_name, 'r') as f:
        lines = f.readlines()

    slides = ""
    for content_file in content_files:
        with open(content_file) as f:
            content = "".join(f.readlines())
        if content_file.endswith(".html"):
            slides += content
        else:
            slides += f"<section data-markdown=\"{content_file}\" data-separator=^\\r?\\n===\\r?\\n$ data-separator-vertical=^\\r?\\n---\\r?\\n$>\n"
            slides += content
            slides += "\n</section>\n"

    settings["slides"] = slides

    template = jinja2.Template("".join(lines))
    rendered_template = template.render(settings)

    with open("./index.html", 'w') as f:
        f.write(rendered_template)
    print("Template refreshed")
    running_refreshing.clear()

class Handler(FileSystemEventHandler):
    def __init__(self, running_refreshing, template_name):
        self.running_refreshing = running_refreshing
        self.template_name = template_name

    def on_any_event(self, event):
        if not event.is_directory and \
                (event.src_path.endswith(".md") \
                or event.src_path.endswith(".html") \
                and not event.src_path.endswith("index.html")):
            refresh_template(self.template_name, self.running_refreshing)

def watch_for_changes(path, template_name, running_watch, running_refreshing):
    print("Running conversion once")
    refresh_template(template_name, running_refreshing)
    print("Watching for changes")
    observer = Observer()
    handler = Handler(running_refreshing, template_name)
    observer.schedule(handler, path, recursive=True)
    observer.start()
    try:
        while running_watch.is_set():
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()
        print("Stop watching")


def main():
    #server = http.server.HTTPServer(("", PORT), http.server.SimpleHTTPRequestHandler)
    path = "."
    template_name = "nlesc.template"
    server = livereload.Server()
    server.watch(FOLDER)

    running_watch = threading.Event()
    running_watch.set()

    running_refreshing = threading.Event()

    watching = threading.Thread(target=watch_for_changes,
                                args=(path,
                                      template_name,
                                      running_watch,
                                      running_refreshing),
                                daemon=True)
    watching.start()
    #serving = threading.Thread(target=server.serve_forever)
    #serving.start()

    try:
        #while True:
        #    time.sleep(1)
        server.serve(port=PORT)
    except KeyboardInterrupt:
        pass
    finally:
        print()
        print("Stop serving")
        running_watch.clear()
        watching.join()
        #server.shutdown()
        #serving.join()

if __name__ == "__main__":
    main()
