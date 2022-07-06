#!/usr/bin/env python3

import os
import tkinter as tk
import webbrowser

from typing import Dict, List, TextIO, Union
from tkinter import ttk, filedialog
from _tkinter import Tcl_Obj
# TODO why is this commented out? Nuitka issue maybe?
# from tktooltip import ToolTip
from tooltip import ToolTip


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


WARNING_COLOR: str = "red"
BLINK_DELAY: int = 100  # in milliseconds


class Gui(ttk.Frame):
    def __init__(self, parent: tk.Tk) -> None:
        ttk.Frame.__init__(self)

        parent.title("reveal.js NLeSC")

        self.parent = parent

        self.default_port: str = "8000"
        self.warning_color: str = WARNING_COLOR
        self.all_plugins: Dict[str, str] = ALL_PLUGINS
        self.reveal_specs: Dict[str, str] = REVEAL_SPECS

        # Follow roughly the Golden Ratio for x- and y-padding.
        self.padx: float = 30.  # horizontal
        self.pady: float = 18.8  # vertical
        self.padx_internal: float = self.padx / 1.6
        self.pady_internal: float = self.pady / 1.6
        # The LabelFrames have some default-padding at the top that we need to
        # remove to keep things centered:
        self.top_pad_offset: float = 8.

        self.versions: List[str] = list(self.reveal_specs.keys())
        self.versions.sort(reverse=True)

        self.plugin_checkboxes: List[ttk.Checkbutton] = []

        self.presentation_path: tk.StringVar = \
            tk.StringVar(value=os.getcwd())
        # TODO trigger first run and watchdog, not by tracing
        # the presentation_path variable.
        self.presentation_path.trace("w", self.update_templates)
        self.presentation_path.trace("w", self.check_path_validity)  # reset buttons
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
        self.active_template: tk.StringVar = \
            tk.StringVar(value="None")
        self.port: tk.StringVar = tk.StringVar(value=self.default_port)
        self.port.trace("w", self.update_url)
        self.url: tk.StringVar = \
            tk.StringVar(value=self.base_url.get()+self.port.get())
        self.url_button_text: tk.StringVar = \
            tk.StringVar(value=self.url_button_base_text.get() +
                         self.base_url.get() + ":" + self.port.get())
        self.templates_radio_buttons: ttk.Radiobutton = []

        # self.state must be one of
        # - invalid path
        # - valid path
        # - serving
        self.state: tk.StringVar = tk.StringVar(value="invalid path")
        self.state.trace("w", self.state_change)

        # Create an (empty) Logic instance
        # Will be filled with life externally
        self.logic = self.Logic()

        # Create widgets :)
        self.setup_widgets()

    def set_default_port(self, port: Union[str, int]) -> None:
        self.default_port = str(port)
        self.port.set(str(port))

    def set_warning_color(self, warning_color: str) -> None:
        self.warning_color = warning_color

    def set_all_plugins(self, all_plugins: Dict[str, str]) -> None:
        self.all_plugins = all_plugins
        self.refresh_plugin_checkboxes()

    def set_reveal_specs(self, reveal_specs: Dict[str, List[str]]) -> None:
        self.reveal_specs = reveal_specs
        self.refresh_versions()

    def set_folder(self, folder: str) -> None:
        self.presentation_path.set(folder)
        self.parent.update()

    def draw_versions(self) -> None:
        self.versions: List[str] = list(self.reveal_specs.keys())
        self.versions.sort(reverse=True)

        version: str
        for version in self.versions:
            self.reveal_version_radio_buttons.append(
                ttk.Radiobutton(self.versions_frame,
                                text=version,
                                value=version,
                                variable=self.active_reveal_version,
                                command=self.refresh_plugin_checkbox_states))
        index: int
        version_button: ttk.Radiobutton
        for index, version_button in \
                enumerate(self.reveal_version_radio_buttons):
            # We don't need versions_frame.rowconfigure, since we don't want
            # to stretch the list.
            version_button.grid(row=index, column=0, sticky="nw")

        self.active_reveal_version.set(self.versions[0])
        self.refresh_plugin_checkbox_states()

    def refresh_versions(self) -> None:
        button: ttk.Radiobutton
        for button in self.reveal_version_radio_buttons:
            button.destroy()
        self.reveal_version_radio_buttons.clear()
        self.draw_versions()

    def draw_plugin_checkboxes(self) -> None:
        self.plugins_chosen: Dict[str, tk.BooleanVar] = {}
        plugin: str
        for plugin in self.all_plugins:
            self.plugins_chosen[plugin]: tk.BooleanVar = \
                tk.BooleanVar(value=True)

        index: int
        plugin: str
        for index, plugin in enumerate(self.all_plugins.keys()):
            plugin_checkbox: ttk.Checkbutton = \
                ttk.Checkbutton(self.plugins_frame,
                                text=plugin,
                                variable=self.plugins_chosen[plugin])
            self.plugin_checkboxes.append(plugin_checkbox)
            self.plugins_frame.rowconfigure(index=index, weight=1)
            plugin_checkbox.grid(row=index, column=0, sticky="we")
            plugin_info: ttk.Label = ttk.Label(self.plugins_frame,
                                               text="🛈",
                                               font=("Segoe Ui", 15))
            ToolTip(plugin_info, self.all_plugins[plugin])
            plugin_info.grid(row=index,
                             column=1,
                             sticky="w",
                             padx=(self.padx_internal, 0))

        self.refresh_plugin_checkbox_states()

    class Logic():
        # To be set externally
        def __init__(self):
            pass

        def run(self):
            print("run")

        def stop(self):
            print("stop")

        def refresh_metadata(self):
            print("refreshing metadata")

    def refresh_plugin_checkboxes(self) -> None:
        plugin_checkbox: ttk.Checkbutton
        for plugin_checkbox in self.plugin_checkboxes:
            plugin_checkbox.destroy()
        self.plugin_checkboxes.clear()
        self.draw_plugin_checkboxes()

    def refresh_plugin_checkbox_states(self) -> None:
        available_plugins: List[str] = \
            self.reveal_specs[self.active_reveal_version.get()]
        plugin_checkbox: ttk.Checkbutton
        for plugin_checkbox in self.plugin_checkboxes:
            plugin_text: str = plugin_checkbox.cget("text")
            if plugin_text in available_plugins:
                plugin_checkbox.state(["!disabled selected !alternate"])
            else:
                plugin_checkbox.state(["disabled !selected alternate"])

    def browse(self) -> None:
        folder_name: str = filedialog.askdirectory(title="Presentation Folder")
        self.presentation_path.set(folder_name)

    def use(self) -> None:
        self.state.set("serving")

    def check_path_validity(self, *args: str) -> None:
        if os.path.isdir(self.presentation_path.get()):
            self.state.set("valid path")
        else:
            self.state.set("invalid path")

    def state_change(self, *args: str) -> None:
        if self.state.get() == "invalid path":
            self.use_button_tooltip.enabled = True
            self.use_button.configure(style="TButton")
            self.url_button.configure(style="TButton")
            self.use_button["state"] = "disabled"
            self.logic.stop()
        if self.state.get() == "valid path":
            self.use_button_tooltip.enabled = False
            self.use_button.configure(style="Accent.TButton")
            self.url_button.configure(style="TButton")
            self.use_button["state"] = "enabled"
            self.logic.refresh_metadata()
        if self.state.get() == "serving":
            self.use_button.configure(style="TButton")
            self.url_button.configure(style="Accent.TButton")
            self.logic.run()

    def flash(self, element: ttk.Label, count: int) -> None:
        fg: Tcl_Obj = ttk.Style().lookup('Label', 'foreground')

        # By default, the "foreground" parameter is a string, but it has
        # to be set as a "_tkinter.Tcl_Obj".
        if type(element.cget("foreground")) == str:
            element.configure(foreground=fg)

        # Switch to self.warning_color if the foreground has its default color,
        # else switch back to the default color.
        if element.cget("foreground") == fg:
            element.configure(foreground=self.warning_color)
        else:
            element.configure(foreground=fg)
            count -= 1  # Reduce counter only after one full blink.
        if (count > 0):
            self.after(BLINK_DELAY, self.flash, element, count)

    def open_url(self) -> None:
        webbrowser.open_new_tab(
            self.base_url.get() + ":" + str(self.port.get()))

    def refresh_server(self) -> None:
        pass

    def update_url(self, *args: str) -> None:
        #  Disable the url button in case there is _no_ port defined.
        if self.port.get() == "":
            self.flash(self.port_info, 2)
            self.url_button.state(["disabled"])
            return

        #  Insert default port in case there is an invalid port defined.
        elif not self.port.get().isdigit():
            self.flash(self.port_info, 2)
            self.port.set(self.default_port)

        elif not 2000 <= int(self.port.get()) <= 65000:
            self.flash(self.port_info, 2)
            self.url_button.state(["disabled"])

        # Enable button for valid ports and update the url button text.
        self.url_button.state(["!disabled"])
        self.url_button_text.set(self.url_button_base_text.get() +
                                 self.base_url.get() + ":" + self.port.get())

    def update_templates(self, *args: str) -> None:
        try:
            # TODO also allow templates in current folder and config folder
            # file_list: List[str] = os.listdir(self.presentation_path.get())
            file_list: List[str] = \
                os.listdir(os.path.dirname(os.path.realpath(__file__)))
        except FileNotFoundError:
            file_list: List[str] = []
        templates: List[str] = [file.rstrip(".template")
                                for file in file_list
                                if file.endswith(".template")]
        templates.sort()
        if templates == []:
            templates = ["None"]

        # delete existing buttons
        button: ttk.Radiobutton
        for button in self.templates_radio_buttons:
            button.destroy()
        self.templates_radio_buttons: List[ttk.Radiobutton] = []

        # create new buttons
        template: str
        for template in templates:
            self.templates_radio_buttons.append(
                ttk.Radiobutton(self.templates_frame,
                                text=template,
                                value=template,
                                variable=self.active_template,
                                command=self.refresh_server))

        index: int
        for index, template_button in \
                enumerate(self.templates_radio_buttons):
            # We don't need versions_frame.rowconfigure, since we don't want
            # to stretch the list.
            template_button.grid(row=index, column=0, sticky="nw")

        # If templates are updated and the active template does not exist
        # anymore, then at least choose _any_ template.
        if self.active_template not in templates:
            self.active_template.set(templates[0])

    def setup_widgets(self) -> None:
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
        ToolTip(self.title_info,
                "Appears in the browser tab title\n"
                "Important for search engines\n"
                "Can be different that the actual title")
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
        ToolTip(self.description_info,
                "Summary of the presentation\n"
                "Important for search engines")

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
        ToolTip(self.author_info,
                "Presentation Author\n"
                "Important for search engines\n"
                "Can be different than the authors on the slide")

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
        ToolTip(self.port_info, "Only numbers between 2000 and 65000 allowed")

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

        self.draw_versions()
        self.draw_plugin_checkboxes()

        self.plugins_frame.columnconfigure(index=0, weight=0)
        self.plugins_frame.columnconfigure(index=1, weight=1)

        self.templates_frame: ttk.LabelFrame = \
            ttk.LabelFrame(self.tab_options,
                           text="Available Templates",
                           padding=(self.padx,
                                    self.pady-self.top_pad_offset,
                                    self.padx,
                                    self.pady))

        self.templates_frame.columnconfigure(index=0, weight=0)
        self.templates_frame.columnconfigure(index=1, weight=1)

        self.update_templates()

        self.use_button: ttk.Button = \
            ttk.Button(self.serve_frame,
                       text="Run",
                       command=self.use,
                       style="Accent.TButton")
        self.use_button_tooltip = \
            ToolTip(self.use_button, "Folder does not exist!")

        # disable by default, show only when triggered
        self.use_button_tooltip.enabled = False

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
        # TODO add feature to keep index.html
        #self.index_switch.grid(row=0, column=0, sticky="nsw",
        #                       padx=(0, self.padx_internal))
        #self.index_switch_info.grid(row=0, column=1, sticky="w")

        self.versions_frame.grid(row=1, column=0, sticky="nsew",
                                 padx=(0, self.padx_internal),
                                 pady=self.pady_internal)

        self.versions_frame.columnconfigure(index=0, weight=1)

        self.plugins_frame.grid(row=1, column=1, sticky="nsew",
                                padx=(0, self.padx_internal),
                                pady=self.pady_internal)

        self.templates_frame.grid(row=1, column=2, sticky="nsew",
                                pady=self.pady_internal)

        self.port_frame.grid(row=2, column=0, columnspan=2, sticky="w")
        self.port_frame.columnconfigure(index=0, weight=1)
        self.port_frame.columnconfigure(index=1, weight=1)
        self.port_frame.rowconfigure(index=0, weight=1)
        self.port_label.grid(row=0, column=0)
        self.port_entry.grid(row=0, column=1, padx=self.padx_internal)
        self.port_info.grid(row=0, column=2)

        self.serve_frame.grid(row=2, column=0)
        self.use_button.grid(row=0, column=0, pady=self.pady)
        self.url_button.grid(row=0, column=1, padx=self.padx_internal, pady=self.pady)


def write_to_title_slide(title_slide: str,
                         new_content: List[str]) -> None:

    def line_validity(line: str, line_number: int, text: str) -> None:
        if not line.startswith(text):
            error_text: str = "Title slide line " + str(line_number) + \
                              " must start with \"" + text + "\", not \"" + \
                              line.split()[0] + "\"."
            raise SyntaxError(error_text)

    header_lines: List[str] = ["<!--",
                               "title:",
                               "description:",
                               "author:",
                               "version:",
                               "plugins:",
                               "-->"]

    f: TextIO
    with open(title_slide) as f:
        slide_text: str = f.readlines()

    line_number: int
    header_line: str
    for line_number, header_line in enumerate(header_lines):
        line_validity(line=slide_text[line_number],
                      line_number=line_number+1,  # more intuitive for the user
                      text=header_line)
        old_content: str = slide_text[line_number].lstrip(header_line).strip()
        slide_text[line_number]: str = slide_text[line_number].replace(
            old_content, new_content[line_number])

    with open(title_slide, 'w') as f:
        f.writelines(slide_text)


def main():
    root: tk.Tk = tk.Tk()
    root.title("Reveal Presentation")

    # Simply set the theme
    root.tk.call("source", "azure.tcl")
    root.tk.call("set_theme", "light")

    app: Gui = Gui(root)
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


if __name__ == "__main__":
    main()
