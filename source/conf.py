# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'SQL Query Builder'
copyright = '2025, Arthur Murat'
author = 'Arthur Murat'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
]

import os
import sys
sys.path.insert(0, os.path.abspath('../../src'))

html_theme = 'furo'
html_theme_options = {
    "dark_css_variables": {
        "color-brand-primary": "#2196F3",
        "color-brand-content": "#1976D2",
    },
    "light_css_variables": {
        "color-brand-primary": "#1976D2",
        "color-brand-content": "#0D47A1",
    },
}

html_static_path = ['_static']
html_css_files = ['custom.css']

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_static_path = ['_static']
