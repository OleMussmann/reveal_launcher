#!/usr/bin/env python3

import tkinter as tk
import webbrowser
from tkinter import ttk, filedialog
#from tktooltip import ToolTip
from tooltip import ToolTip
from typing import Dict, List
import os


# All available plugins and their descriptions.
ALL_PLUGINS: Dict[str, str] = \
    {
        "RevealHighlight": "highlight description",
        "RevealMarkdown": "markdown description",
        "RevealNotes": "notes description",
        "RevealSearch": "search description",
        "RevealZoom": "zoom description",
    }

# Configure available versions (keys) and plugins (values)
# that are implemented for this version.
REVEAL_SPECS: Dict[str, List[str]] = \
    {"4.3.0": ["RevealZoom"],
     "4.3.1": ["RevealZoom",
               "RevealNotes",
               "RevealSearch",
               "RevealMarkdown",
               "RevealHighlight"],
     }

DEFAULT_PORT: str = "8000"

BLINK_COLOR: str = "red"
BLINK_DELAY: int = 100  # in milliseconds

global FOLDER_NAME


class App(ttk.Frame):
    def __init__(self, parent: tk.Tk) -> None:
        ttk.Frame.__init__(self)

        parent.title("reveal.js NLeSC")

        # Follow roughly the Golden Ratio for x- and y-padding.
        self.padx: float = 30.  # horizontal
        self.pady: float = 18.8  # vertical
        self.padx_internal: float = self.padx / 1.6
        self.pady_internal: float = self.pady / 1.6
        # The LabelFrames have some default-padding at the top that we need to
        # remove to keep things centered:
        self.top_pad_offset: float = 8.

        self.plugins_chosen: Dict[str, tk.BooleanVar] = {}
        for plugin in ALL_PLUGINS.keys():
            self.plugins_chosen[plugin] = tk.BooleanVar(value=True)

        self.versions: List[str] = list(REVEAL_SPECS.keys())
        self.versions.sort(reverse=True)

        self.checkboxes: List[ttk.Checkbutton] = []

        self.presentation_path: tk.StringVar = \
            tk.StringVar(value="/path/to/presentation")
        # TODO trigger first run and watchdog, not by tracing
        # the presentation_path variable.
        self.presentation_path.trace("w", self.update_templates)
        self.generate_index_html: tk.BooleanVar = \
            tk.BooleanVar(value=True)
        self.base_url: tk.StringVar = tk.StringVar(value="http://localhost")
        self.url_button_base_text: tk.StringVar = \
            tk.StringVar(value="Open presentation at ")
        self.title_string: tk.StringVar = \
            tk.StringVar(value="Presentation Title")
        self.description_string: tk.StringVar = \
            tk.StringVar(value="Description")
        self.author_string: tk.StringVar = \
            tk.StringVar(value="Presentation Author")
        self.active_reveal_version: tk.StringVar = \
            tk.StringVar(value=self.versions[0])
        self.port: tk.StringVar = tk.StringVar(value=DEFAULT_PORT)
        self.port.trace("w", self.update_url)
        self.url: tk.StringVar = \
            tk.StringVar(value=self.base_url.get()+self.port.get())
        self.url_button_text: tk.StringVar = \
            tk.StringVar(value=self.url_button_base_text.get() +
                         self.base_url.get() + ":" + self.port.get())

        # Create widgets :)
        self.setup_widgets()

    def browse(self) -> None:
        FOLDER_NAME: str = filedialog.askdirectory()
        self.presentation_path.set(FOLDER_NAME)

    def flash(self, element: ttk.Label, count: int):
        # How do you type-hint "_tkinter.Tcl_Obj" ?
        fg = ttk.Style().lookup('Label', 'foreground')

        # By default, the "foreground" parameter is a string, but it has
        # to be set as a "_tkinter.Tcl_Obj".
        if type(element.cget("foreground")) == str:
            element.configure(foreground=fg)

        # Switch to BLINK_COLOR if the foreground has its default color,
        # else switch back to the default color.
        if element.cget("foreground") == fg:
            element.configure(foreground=BLINK_COLOR)
        else:
            element.configure(foreground=fg)
            count -= 1  # Reduce counter only after one full blink.
        if (count > 0):
            self.after(BLINK_DELAY, self.flash, element, count)

    def refresh_checkboxes(self):
        available_plugins: List[str] = \
            REVEAL_SPECS[self.active_reveal_version.get()]
        checkbox: ttk.Checkbutton
        for checkbox in self.checkboxes:
            plugin_text: str = checkbox.cget("text")
            if plugin_text in available_plugins:
                checkbox.state(["!disabled selected !alternate"])
            else:
                checkbox.state(["disabled !selected alternate"])

    def open_url(self):
        webbrowser.open_new_tab(
            self.base_url.get() + ":" + str(self.port.get()))

    def use(self):
        self.use_button.configure(style="TButton")
        self.url_button.configure(style="Accent.TButton")

    def update_url(self, *args):
        #  Disable the url button in case there is _no_ port defined.
        if self.port.get() == "":
            self.flash(self.port_info, 2)
            self.url_button.state(["disabled"])
            return

        #  Insert default port in case there is an invalid port defined.
        elif not self.port.get().isdigit():
            self.flash(self.port_info, 2)
            self.port.set(DEFAULT_PORT)

        # Enable button for valid ports and update the url button text.
        self.url_button.state(["!disabled"])
        self.url_button_text.set(self.url_button_base_text.get() +
                                 self.base_url.get() + ":" + self.port.get())

    def update_templates(self, *args):
        file_list: str = os.listdir(self.presentation_path.get())
        templates: List[str] = [file.rstrip(".template")[0]
                                for file in file_list
                                if file.endswith(".template")]
        templates.sort()

        for template in templates:
            self.templates_radio_buttons.append(
                ttk.Radiobutton(self.versions_frame,
                                text=template,
                                value=template,
                                variable=self.active_reveal_version,
                                command=self.refresh_checkboxes))

        print(self.templates_radio_buttons)

    def setup_widgets(self):

        # Padding parameters: padding=(left, top, right, bottom)
        self.folder_frame: ttk.LabelFrame = \
            ttk.LabelFrame(self,
                           text="Presetation Folder",
                           padding=(self.padx,
                                    self.pady-self.top_pad_offset,
                                    self.padx,
                                    self.pady))
        self.browse_button: ttk.Button = \
            ttk.Button(self.folder_frame,
                       text="Browse",
                       command=self.browse)
        self.path_entry: ttk.Entry = \
            ttk.Entry(self.folder_frame,
                      textvariable=self.presentation_path)
        self.use_button: ttk.Button = \
            ttk.Button(self.folder_frame,
                       text="Use this Folder",
                       command=self.use,
                       style="Accent.TButton")

        self.serve_frame: ttk.Frame = ttk.Frame(self)

        self.notebook: ttk.Notebook = ttk.Notebook(self)
        self.tab_metadata: ttk.Frame = \
            ttk.Frame(self.notebook,
                      padding=(self.padx, self.pady))
        self.notebook.add(self.tab_metadata, text="Metadata")
        self.tab_options: ttk.Frame = \
            ttk.Frame(self.notebook,
                      padding=(self.padx, self.pady))
        self.notebook.add(self.tab_options, text="Expert Options")
        self.tab_help: ttk.Frame = \
            ttk.Frame(self.notebook, padding=(self.padx, self.pady))
        self.notebook.add(self.tab_help, text="Help")

        self.title_frame: ttk.Frame = ttk.Frame(self.tab_metadata)
        self.title_label: ttk.Label = ttk.Label(self.title_frame,
                                                text="Title",
                                                width=10)
        self.title_entry: ttk.Entry = ttk.Entry(self.title_frame,
                                                textvariable=self.title_string)
        self.title_info: ttk.Label = \
            ttk.Label(self.title_frame,
                      text="🛈",
                      font=("Segoe Ui", 15))
        ToolTip(self.title_info, "abcde\nmulti line")
        self.description_frame: ttk.Frame = ttk.Frame(self.tab_metadata)
        self.description_label: ttk.Label = ttk.Label(self.description_frame,
                                                      text="Description",
                                                      width=10)
        self.description_entry: ttk.Entry = \
            ttk.Entry(self.description_frame,
                      textvariable=self.description_string)
        self.description_info: ttk.Label = ttk.Label(self.description_frame,
                                                     text="🛈",
                                                     font=("Segoe Ui", 15))
        ToolTip(self.description_info, "abcde\nmulti line")

        self.author_frame: ttk.Frame = ttk.Frame(self.tab_metadata)
        self.author_label: ttk.Label = ttk.Label(self.author_frame,
                                                 text="Author",
                                                 width=10)
        self.author_entry: ttk.Entry = \
            ttk.Entry(self.author_frame,
                      textvariable=self.author_string)
        self.author_info: ttk.Label = ttk.Label(self.author_frame,
                                                text="🛈",
                                                font=("Segoe Ui", 15))
        ToolTip(self.author_info, "abcde\nmulti line")

        self.index_frame: ttk.Frame = ttk.Frame(self.tab_options)
        self.index_switch: ttk.Checkbutton = \
            ttk.Checkbutton(self.index_frame,
                            text="generate index.html",
                            style="Switch.TCheckbutton",
                            variable=self.generate_index_html)
        self.index_switch_info: ttk.Label = ttk.Label(self.index_frame,
                                                      text="🛈",
                                                      font=("Segoe Ui", 15))
        ToolTip(self.index_switch_info, "abcde\nmulti line")

        self.port_frame: ttk.Label = ttk.Label(self.tab_options)
        self.port_label: ttk.Label = ttk.Label(self.port_frame,
                                               text="Port number")
        self.port_entry: ttk.Label = ttk.Entry(self.port_frame,
                                               textvariable=self.port)
        self.port_info: ttk.Label = ttk.Label(self.port_frame,
                                              text="🛈",
                                              font=("Segoe Ui", 15))
        ToolTip(self.port_info, "only numbers allowed\nmulti line")

        self.versions_frame: ttk.LabelFrame = \
            ttk.LabelFrame(self.tab_options,
                           text="reveal.js Version",
                           padding=(self.padx,
                                    self.pady-self.top_pad_offset,
                                    self.padx,
                                    self.pady))
        self.plugins_frame: ttk.LabelFrame = \
            ttk.LabelFrame(self.tab_options,
                           text="Available Plugins",
                           padding=(self.padx,
                                    self.pady-self.top_pad_offset,
                                    self.padx,
                                    self.pady))

        self.reveal_version_radio_buttons: List[ttk.Radiobutton] = []
        self.templates_radio_buttons: List[ttk.Radiobutton] = []

        version: str
        for version in self.versions:
            self.reveal_version_radio_buttons.append(
                ttk.Radiobutton(self.versions_frame,
                                text=version,
                                value=version,
                                variable=self.active_reveal_version,
                                command=self.refresh_checkboxes))

        self.plugins_frame.columnconfigure(index=0, weight=0)
        self.plugins_frame.columnconfigure(index=1, weight=1)

        index: int
        plugin: str
        for index, plugin in enumerate(ALL_PLUGINS.keys()):
            checkbox: ttk.Checkbutton = \
                ttk.Checkbutton(self.plugins_frame,
                                text=plugin,
                                variable=self.plugins_chosen[plugin])
            self.checkboxes.append(checkbox)
            self.plugins_frame.rowconfigure(index=index, weight=1)
            checkbox.grid(row=index, column=0, sticky="we")
            plugin_info: ttk.Label = ttk.Label(self.plugins_frame,
                                               text="🛈",
                                               font=("Segoe Ui", 15))
            ToolTip(plugin_info, ALL_PLUGINS[plugin])
            plugin_info.grid(row=index,
                             column=1,
                             sticky="w",
                             padx=(self.padx_internal, 0))

        self.templates_frame: ttk.LabelFrame = \
            ttk.LabelFrame(self.tab_options,
                           text="Available Templates",
                           padding=(self.padx,
                                    self.pady-self.top_pad_offset,
                                    self.padx,
                                    self.pady))

        self.templates_frame.columnconfigure(index=0, weight=0)
        self.templates_frame.columnconfigure(index=1, weight=1)


        self.url_button: ttk.Button = \
            ttk.Button(self.serve_frame,
                       textvariable=self.url_button_text,
                       command=self.open_url, style="TButton")

        self.columnconfigure(index=0, weight=1)
        self.rowconfigure(index=0, weight=1)
        self.rowconfigure(index=1, weight=1)
        self.rowconfigure(index=2, weight=1)

        self.folder_frame.grid(row=0, column=0, sticky="nsew",
                               padx=self.padx, pady=self.pady)
        self.folder_frame.rowconfigure(index=0, weight=1)
        self.folder_frame.columnconfigure(index=0, weight=0)
        self.folder_frame.columnconfigure(index=1, weight=1)
        self.browse_button.grid(row=0, column=0, sticky="w")
        self.path_entry.grid(row=0, column=1, sticky="ew",
                             padx=self.padx_internal)
        self.use_button.grid(row=0, column=2, sticky="e")

        self.notebook.grid(row=1, column=0, sticky="nsew", padx=self.padx)

        self.tab_metadata.columnconfigure(index=0, weight=1)
        self.tab_metadata.rowconfigure(index=0, weight=1)
        self.tab_metadata.rowconfigure(index=1, weight=1)
        self.tab_metadata.rowconfigure(index=2, weight=1)
        self.tab_metadata.rowconfigure(index=3, weight=1)

        self.title_frame.grid(row=1, column=0, sticky="nsew")
        self.title_frame.columnconfigure(index=1, weight=1)
        self.title_label.grid(row=0, column=0, sticky="w")
        self.title_entry.grid(row=0, column=1, sticky="ew",
                              padx=self.padx_internal)
        self.title_info.grid(row=0, column=2, sticky="w")

        self.description_frame.grid(row=2, column=0, sticky="nsew",
                                    pady=self.pady_internal)
        self.description_frame.columnconfigure(index=1, weight=1)
        self.description_label.grid(row=0, column=0)
        self.description_entry.grid(row=0, column=1, sticky="ew",
                                    padx=self.padx_internal)
        self.description_info.grid(row=0, column=2, sticky="w")

        self.author_frame.grid(row=3, column=0, sticky="nsew")
        self.author_frame.columnconfigure(index=1, weight=1)
        self.author_label.grid(row=0, column=0, sticky="w")
        self.author_entry.grid(row=0, column=1, sticky="ew",
                               padx=self.padx_internal)
        self.author_info.grid(row=0, column=2, sticky="w")

        self.tab_options.rowconfigure(index=0, weight=1)
        self.tab_options.rowconfigure(index=1, weight=1)
        self.tab_options.rowconfigure(index=2, weight=1)
        self.tab_options.columnconfigure(index=0, weight=1)
        self.tab_options.columnconfigure(index=1, weight=1)

        self.index_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.index_frame.columnconfigure(index=0, weight=0)
        self.index_frame.columnconfigure(index=1, weight=1)
        self.index_frame.rowconfigure(index=0, weight=1)
        self.index_switch.grid(row=0, column=0, sticky="nsw",
                               padx=(0, self.padx_internal))
        self.index_switch_info.grid(row=0, column=1, sticky="w")

        self.versions_frame.grid(row=1, column=0, sticky="nsew",
                                 padx=(0, self.padx_internal),
                                 pady=self.pady_internal)

        self.versions_frame.columnconfigure(index=0, weight=1)
        index: int
        version_button: ttk.Radiobutton
        for index, version_button in \
                enumerate(self.reveal_version_radio_buttons):
            # We don't need versions_frame.rowconfigure, since we don't want
            # to stretch the list.
            version_button.grid(row=index, column=0, sticky="nw")

        self.plugins_frame.grid(row=1, column=1, sticky="nsew",
                                pady=self.pady_internal)

        self.templates_frame.grid(row=1, column=2, sticky="nsew",
                                pady=self.pady_internal)

        index: int
        template: ttk.Radiobutton
        for index, template in \
                enumerate(self.templates_radio_buttons):
            # We don't need versions_frame.rowconfigure, since we don't want
            # to stretch the list.
            version_button.grid(row=index, column=0, sticky="nw")

        self.port_frame.grid(row=2, column=0, columnspan=2, sticky="w")
        self.port_frame.columnconfigure(index=0, weight=1)
        self.port_frame.columnconfigure(index=1, weight=1)
        self.port_frame.rowconfigure(index=0, weight=1)
        self.port_label.grid(row=0, column=0)
        self.port_entry.grid(row=0, column=1, padx=self.padx_internal)
        self.port_info.grid(row=0, column=2)

        self.serve_frame.grid(row=2, column=0)
        self.url_button.grid(row=0, column=0, padx=self.padx, pady=self.pady)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Reveal Presentation")

    # Simply set the theme
    root.tk.call("source", "azure.tcl")
    root.tk.call("set_theme", "light")

    app = App(root)
    app.pack(fill="both", expand=True)

    # Set a minsize for the window
    root.update()
    root.minsize(root.winfo_width(), root.winfo_height())
    # Tying it to the middle of the screen is annoying for multiple-monitor
    # setups.
    #x_cordinate: int = \
    #    int((root.winfo_screenwidth() / 2) - (root.winfo_width() / 2))
    #y_cordinate: int = \
    #    int((root.winfo_screenheight() / 2) - (root.winfo_height() / 2))
    #root.geometry("+{}+{}".format(x_cordinate, y_cordinate-20))

    root.mainloop()
