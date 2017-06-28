# -*- coding: utf-8 -*-
"""
    Pygment style for the AnyScript modelling langue.

"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *


from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, Number, Operator, Generic, Whitespace, Token, Other 

__all__ = ['AnyScriptStyle']

class AnyScriptStyle(Style):
    background_color="#f8f8f8"
    default_style = ""

    styles={
          Whitespace:                "#bbbbbb", 
          Comment:                   "noitalic #4AA02C", 
          Comment.Preproc:           "noitalic #0000FF", 
   
          #Keyword:                   "bold #AA22FF", 
          Keyword:                   "#0000FF", 
          Keyword.Pseudo:            "nobold", 
          Keyword.Type:              "nobold #0000FF", 
   
          Operator:                  "#111111", 
          Operator.Word:             "bold #AA22FF", 
   
          Name.Builtin:              "#0000FF", 
          Name.Function:             "#0000FF", 
          Name.Class:                "#0000FF", 
          Name.Namespace:            "#900090", 
          Name.Exception:            "#D2413A", 
          Name.Variable:             "#19177C", 
          Name.Constant:             "#880000", 
          Name.Label:                "#A0A000", 
          Name.Entity:               "bold #999999", 
          Name.Attribute:            "#7D9029", 
          Name.Tag:                  "bold #008000", 
          Name.Decorator:            "#AA22FF", 
	
		  Other.Statements:			 "#900090",
		  Other.Options:			 "bold",
   
          String:                    "#666666", 
          String.Doc:                "italic", 
          String.Interpol:           "bold #BB6688", 
          String.Escape:             "bold #BB6622", 
          String.Regex:              "#BB6688", 
          #String.Symbol:             "#B8860B", 
          String.Symbol:             "#19177C", 
          String.Other:              "#008000", 
          Number:                    "#666666", 
   
          Generic.Heading:           "bold #000080", 
          Generic.Subheading:        "bold #800080", 
          Generic.Deleted:           "#f8f8f8", #Used for $ tag in AnyScript.
          Generic.Inserted:          "#00A000", 
          Generic.Error:             "#FF0000", 
          Generic.Emph:              "italic", 
          Generic.Strong:            "bold", 
          Generic.Prompt:            "bold #000080", 
          Generic.Output:            "#888", 
          Generic.Traceback:         "#04D", 
   
          Error:                     "border:#FF0000" 


    }