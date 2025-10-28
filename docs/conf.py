# outline for a myst_nb project with sphinx
# build with: sphinx-build -nW --keep-going -b html . ./_build/html


from anypytools import __version__ as ANYPYTOOLS_VERSION

# load extensions
extensions = [
    "myst_nb",
    "autodoc2",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx_design"
]


autodoc2_packages = [
 "../anypytools",
]

autodoc2_output_dir = "api"
autodoc2_render_plugin = "rst"

autodoc2_module_all_regexes = [
    r"anypytools\..*",
]


nitpick_ignore = [
    ('py:class', 'optional'),
    ('py:class', 'np.ndarray'),
    ('py:class', 'pandas.DataFrame')
    ]


# autodoc2_render_plugin = "myst"

# autodoc2_hidden_objects = ["dunder", "inherited"]
autodoc2_replace_annotations = [
    ("re.Pattern", "typing.Pattern"),
    ("markdown_it.MarkdownIt", "markdown_it.main.MarkdownIt"),
]
autodoc2_replace_bases = [
    ("sphinx.directives.SphinxDirective", "sphinx.util.docutils.SphinxDirective"),
]

napoleon_use_ivar = True

# Napoleon settings for NumPy-style
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_use_admonition_for_notes = False


intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master", None),
    "pytest": ("https://docs.pytest.org/en/stable/", None),
    "h5py": ("https://docs.h5py.org/en/stable/", None),
}


myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "dollarmath",
    "amsmath",
    "html_image",
    "fieldlist",
]

# Napoleon settings for NumPy-style
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_use_admonition_for_notes = False

# # specify project details
# master_doc = "index"

# General information about the project.
project = "AnyPyTools"
copyright = "2021, Morten Enemark Lund"
author = "Morten Enemark Lund"

language = "en"


# basic build settings
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**.ipynb_checkpoints", "paper", "slides"]
nitpicky = True

html_theme = "pydata_sphinx_theme"


html_logo = "_static/anypytools_logo.png"

html_theme_options = {
    "external_links": [
        # {
        #     "url": "https://anybodytech.com",
        #     "name": "AnyBody Technology Website",
        # },
    ],
    "header_links_before_dropdown": 4,
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/anybody-research-group/anypytools",
            "icon": "fa-brands fa-github",
        },
        # {
        #     "name": "Anybody Technology",
        #     "url": "https://anybodytech.com",
        #     "icon": "fa-solid fa-globe",
        # }
    ],
    # alternative way to set twitter and github header icons
    # "github_url": "https://github.com/pydata/pydata-sphinx-theme",
    # "twitter_url": "https://twitter.com/PyData",
    "logo": {
        "text": "AnyPyTools Documentation",
        # "image_dark": "_static/logo-dark.svg",
    },
    "use_edit_page_button": True,
    "show_toc_level": 2,
    # [left, content, right] For testing that the navbar items align properly
    "navbar_align": "left",
    # "show_nav_level": 2,
    # "announcement": "https://raw.githubusercontent.com/pydata/pydata-sphinx-theme/main/docs/_templates/custom-template.html",
    # "show_version_warning_banner": True,
    # "navbar_center": ["version-switcher", "navbar-nav"],
    # "navbar_start": ["navbar-logo"],
    # "navbar_end": ["theme-switcher", "navbar-icon-links"],
    # "navbar_persistent": ["search-button"],
    # "primary_sidebar_end": ["custom-template", "sidebar-ethical-ads"],
    # "article_footer_items": ["test", "test"],
    # "content_footer_items": ["test", "test"],
    # "footer_start": ["copyright"],
    # "footer_center": ["sphinx-version"],
    # "back_to_top_button": False,
    # "search_as_you_type": True,
}

html_context = {
    "github_user": "AnyBody-Research-Group",
    "github_repo": "AnyPyTools",
    "github_version": "master",
    "doc_path": "docs",
}

# autodoc2_docstring_parser_regexes = [
#     ("myst_parser", "myst"),
#     (r"myst_parser\.setup", "myst"),
# ]

# nitpick_ignore = [
#     ("py:class", "anypytools.abcutils._Task"),
# ]



html_sidebars = {
    "examples/no-sidebar": [],  # Test what page looks like with no sidebar items
    "examples/persistent-search-field": ["search-field"],

}
## myst_nb default settings


nb_execution_mode = "off"

# Custom formats for reading notebook; suffix -> reader
# nb_custom_formats = {}

# Notebook level metadata key for config overrides
# nb_metadata_key = 'mystnb'

# Cell level metadata key for config overrides
# nb_cell_metadata_key = 'mystnb'

# Mapping of kernel name regex to replacement kernel name(applied before execution)
# nb_kernel_rgx_aliases = {}

# Regex that matches permitted values of eval expressions
# nb_eval_name_regex = '^[a-zA-Z_][a-zA-Z0-9_]*$'

# Execution mode for notebooks
# nb_execution_mode = 'auto'

# Path to folder for caching notebooks (default: <outdir>)
# nb_execution_cache_path = ''

# Exclude (POSIX) glob patterns for notebooks
# nb_execution_excludepatterns = ()

# Execution timeout (seconds)
# nb_execution_timeout = 30

# Use temporary folder for the execution current working directory
# nb_execution_in_temp = False

# Allow errors during execution
# nb_execution_allow_errors = False

# Raise an exception on failed execution, rather than emitting a warning
# nb_execution_raise_on_error = False

# Print traceback to stderr on execution error
# nb_execution_show_tb = False

# Merge all stdout execution output streams; same with stderr
# nb_merge_streams = False

# The entry point for the execution output render class (in group `myst_nb.output_renderer`)
# nb_render_plugin = 'default'

# Remove code cell source
# nb_remove_code_source = False

# Remove code cell outputs
# nb_remove_code_outputs = False

# Make long cell outputs scrollable
# nb_scroll_outputs = False

# Prompt to expand hidden code cell {content|source|outputs}
# nb_code_prompt_show = 'Show code cell {type}'

# Prompt to collapse hidden code cell {content|source|outputs}
# nb_code_prompt_hide = 'Hide code cell {type}'

# Number code cell source lines
# nb_number_source_lines = False

# Overrides for the base render priority of mime types: list of (builder name, mime type, priority)
# nb_mime_priority_overrides = ()

# Behaviour for stderr output
# nb_output_stderr = 'show'

# Pygments lexer applied to stdout/stderr and text/plain outputs
# nb_render_text_lexer = 'myst-ansi'

# Pygments lexer applied to error/traceback outputs
# nb_render_error_lexer = 'ipythontb'

# Options for image outputs (class|alt|height|width|scale|align)
# nb_render_image_options = {}

# Options for figure outputs (classes|name|caption|caption_before)
# nb_render_figure_options = {}

# The format to use for text/markdown rendering
# nb_render_markdown_format = 'commonmark'

# Javascript to be loaded on pages containing ipywidgets
# nb_ipywidgets_js = {'https://cdnjs.cloudflare.com/ajax/libs/require.js/2.3.4/require.min.js': {'integrity': 'sha256-Ae2Vz/4ePdIu6ZyI/5ZGsYnb+m0JlOmKPjt6XZ9JJkA=', 'crossorigin': 'anonymous'}, 'https://cdn.jsdelivr.net/npm/@jupyter-widgets/html-manager@1.0.6/dist/embed-amd.js': {'data-jupyter-widgets-cdn': 'https://cdn.jsdelivr.net/npm/', 'crossorigin': 'anonymous'}}
