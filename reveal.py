#!/usr/bin/env python3

import argparse
import livereload
import multiprocessing
import os
import platform
import shutil
import sys
import threading
import tkinter as tk
import yaml

from typing import Any, Dict, List, TextIO

from reveal_cli import watch_for_changes
from reveal_gui import Gui
from version import __version__


NAME: str = "reveal launcher"

CONFIG_FILE_NAME: str = "config.yaml"

# Directory of _this_ script
BASE_DIRECTORY: str = os.path.dirname(os.path.realpath(__file__))


def cli_args() -> argparse.Namespace:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Launch a reveal.js presentation")
    parser.add_argument("folder",
                        nargs='?',
                        default=os.getcwd(),  # Current directory
                        help="where to serve the presentation from, defaults "
                        "to current directory")
    parser.add_argument("-p", "--port",
                        type=int,
                        default=8000,
                        help="port of the web server")
    parser.add_argument("--gui",
                        action="store_true",
                        help="launch the Graphical User Interface")
    ## TODO
    #parser.add_argument("--reveal_versions",
    #                    action="store_true",
    #                    help="list available reveal.js versions and exit")
    ## TODO
    #parser.add_argument("--plugins",
    #                    action="store_true",
    #                    help="list available plugins and exit")
    parser.add_argument("-v", "--version",
                        action="store_true",
                        help="print %(prog)s version and exit")
    return parser.parse_args()


def launched_from_terminal() -> bool:
    # https://stackoverflow.com/questions/9839240/how-to-determine-if-python-script-was-run-via-command-line
    # TODO detect on Windows too
    if sys.stdin:
        print("is a tty? ", sys.stdin.isatty())
    else:
        print("not a tty")
    return sys.stdin and sys.stdin.isatty()


def run_cli(args: argparse.Namespace, config: Dict[str, Any]) -> None:
    server = livereload.Server()
    server.watch(args.folder)

    running_watch = threading.Event()
    running_watch.set()

    running_refreshing = threading.Event()

    template_file = os.path.join(BASE_DIRECTORY, "nlesc.template")
    watching = threading.Thread(target=watch_for_changes,
                                args=(args.folder,
                                      template_file,
                                      running_watch,
                                      running_refreshing),
                                daemon=True)
    watching.start()

    try:
        server.serve(port=args.port, root=args.folder)
    except KeyboardInterrupt:
        pass
    finally:
        print()
        print("Stop serving")
        running_watch.clear()
        watching.join()


def run_gui(args: argparse.Namespace, config: Dict[str, Any]) -> None:

    default_port: int = config["default_port"]
    warning_color: str = config["warning_color"]
    all_plugins: Dict[str, str] = config["all_plugins"]
    reveal_specs: Dict[str, List[str]] = config["reveal_specs"]

    root: tk.Tk = tk.Tk()

    root.tk.call("source", os.path.join(BASE_DIRECTORY, "azure.tcl"))
    root.tk.call("set_theme", "light")

    app: Gui = Gui(root)

    app.set_default_port(default_port)
    app.set_warning_color(warning_color)
    app.set_all_plugins(all_plugins)
    app.set_reveal_specs(reveal_specs)

    app.pack(fill="both", expand=True)

    # Set a minsize for the window
    root.update()
    root.minsize(root.winfo_width(), root.winfo_height())

    # If we set it before updating and setting size, the width will be messed
    # up. No idea why.
    app.set_folder(args.folder)

    class Logic(app.Logic):
        def __init__(self):
            self.server = livereload.Server()
            self.running_watch = threading.Event()
            self.running_refreshing = threading.Event()
            if app.state.get() == "valid path":
                self.refresh_metadata()

        def run(self):
            print("run from outside")
            self.use_folder()
            self.write_to_title_slide()
            presentation_path: str = app.presentation_path.get()
            self.server.watch(presentation_path)
            self.running_watch.set()
            template_file = \
                os.path.join(BASE_DIRECTORY,
                             app.active_template.get() + ".template")
            self.watching = threading.Thread(target=watch_for_changes,
                                             args=(presentation_path,
                                                   template_file,
                                                   self.running_watch,
                                                   self.running_refreshing),
                                             daemon=True)
            self.watching.start()
            port = app.port.get()
            self.serving_process = \
                multiprocessing.Process(target=self.server.serve,
                                        kwargs={"port": port,
                                                "root": presentation_path})
            self.serving_process.start()

        def stop(self):
            print("stop from outside")
            try:
                self.serving_process.terminate()
                self.running_watch.clear()
                self.watching.join()
            except AttributeError:
                print("nothing to kill, because nothing has started yet...")

        def refresh_metadata(self):
            print("refresh metadata from outside")
            try:
                metadata_dict: Dict[str] = self.read_metadata()
                app.title_string.set(metadata_dict["title"])
                app.description_string.set(metadata_dict["description"])
                app.author_string.set(metadata_dict["author"])
            except IndexError:
                print("no metadata, since there are no files yet")

        def use_folder(self):
            print("using folder from outsite")
            self.place_reveal_folder()
            self.place_sample_files()

        def get_title_slide(self):
            presentation_path: str = app.presentation_path.get()
            all_files: List[str] = os.listdir(presentation_path)
            content_files = [x for x in all_files if x != "index.html"
                             and x.endswith(".html") or x.endswith(".md")]
            content_files.sort()
            title_slide: str = os.path.join(presentation_path,
                                            content_files[0])
            return title_slide

        def read_metadata(self) -> Dict[str, str]:
            title_slide: str = self.get_title_slide()
            f: TextIO
            with open(title_slide) as f:
                slide_text: str = f.readlines()

            self.line_validity(slide_text[1], 1, "title:")
            title: str = slide_text[1].lstrip("title:").strip()
            self.line_validity(slide_text[2], 2, "description:")
            description: str = slide_text[2].lstrip("description:").strip()
            self.line_validity(slide_text[3], 3, "author:")
            author: str = slide_text[3].lstrip("author:").strip()

            return {"title": title,
                    "description": description,
                    "author": author}

        def line_validity(self, line: str, line_number: int, text: str) \
                -> None:
            if not line.startswith(text):
                error_text: str = \
                    "Title slide line " + str(line_number) + " must start " + \
                    "with \"" + text + "\", not \"" + line.split()[0] + "\"."
                raise SyntaxError(error_text)

        def write_to_title_slide(self) -> None:
            header_lines: List[str] = ["<!--",
                                       "title:",
                                       "description:",
                                       "author:",
                                       "version:",
                                       "plugins:",
                                       "-->"]

            title_slide: str = self.get_title_slide()

            active_plugins = [box.cget("text") for box in app.plugin_checkboxes
                              if box.state() == ('selected',)]

            new_content: List[str] = [
                "",
                app.title_string.get(),
                app.description_string.get(),
                app.author_string.get(),
                app.active_reveal_version.get(),
                ", ".join(active_plugins),
                ""
            ]

            f: TextIO
            with open(title_slide) as f:
                slide_text: str = f.readlines()

            line_number: int
            header_line: str
            for line_number, header_line in enumerate(header_lines):
                self.line_validity(line=slide_text[line_number],
                                   # Counting lines from 1 is more intuitive
                                   # for the user:
                                   line_number=line_number+1,
                                   text=header_line)
                old_content: str = \
                    slide_text[line_number].lstrip(header_line).strip()
                slide_text[line_number]: str = slide_text[line_number].replace(
                    old_content, new_content[line_number])

            with open(title_slide, 'w') as f:
                f.writelines(slide_text)

        def place_reveal_folder(self) -> None:
            presentation_directory: str = app.presentation_path.get()
            reveal_path: str = os.path.join(presentation_directory,
                                            "reveal.js")
            if not os.path.isdir(reveal_path) \
                    and not os.path.isfile(reveal_path):
                source_dir: str = os.path.join(BASE_DIRECTORY,
                                               "reveal.js")
                shutil.copytree(source_dir, reveal_path)
            else:
                print("reveal.js already exists, not overwriting")

        def place_sample_files(self) -> None:
            presentation_directory: str = app.presentation_path.get()
            all_files: str = os.listdir(presentation_directory)
            content_files = [x for x in all_files if x != "index.html"
                             and x.endswith(".html") or x.endswith(".md")]

            if not content_files:
                for file in ["00_title.md", "01_next_slides.md",
                             "02_html_slides.html"]:
                    shutil.copy(os.path.join(BASE_DIRECTORY, file),
                                presentation_directory)
            else:
                print("content files already exist, not placing sample files")

            if not os.path.isdir(os.path.join(presentation_directory,
                                 "files")):
                shutil.copytree(os.path.join(BASE_DIRECTORY, "files"),
                                os.path.join(presentation_directory, "files"))
            else:
                print("\"files\" already exists, not overwriting")

    logic = Logic()
    app.logic = logic
    #try:
    #    app.logic.()
    #except IndexError:
    #    print("No files yet, skipping")

    root.mainloop()

    # Clean up if the window is closed
    logic.stop()

def main() -> None:
    args: argparse.Namespace = cli_args()

    if args.version:
        print(NAME, __version__)
        sys.exit()

    f: TextIO
    with open(os.path.join(BASE_DIRECTORY, CONFIG_FILE_NAME)) as f:
        # TODO use yatiml instead
        config: Dict[str, Any] = yaml.safe_load(f)

    # Launched_from_terminal does not work on Windows. Until that is fixed, the
    # Windows platform only gets the GUI.
    if launched_from_terminal() \
            and not args.gui \
            and not platform.system() == 'Windows':
        run_cli(args=args, config=config)
    else:
        run_gui(args=args, config=config)


if __name__ == "__main__":
    main()
