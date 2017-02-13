# -*- coding: utf-8 -*-
"""
Created on Mon Dec 26 17:05:49 2016

@author: edgar
"""


    
from model import Model
from view import View
from controller import Controller
from support.logging import Logging

Logging.setup_logging()
model = Model()
view = View(None)
controller = Controller(model, view)
view.mainloop()
