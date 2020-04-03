from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
#from pyfmi import load_fmu
from fmpy.model_description import read_model_description
from fmpy.fmi2 import FMU2Slave
import numpy as np
import pandas as pd
import os
from fmpy import extract



class Model(object):
    """
    FMU model to be simulated with inputs and parameters provided from
    files or dataframes.
    """

    # Number of tries to simulate a model
    # (sometimes the solver can't converge at first)
    TRIES = 15

    def __init__(self, fmu_path, opts=None):
        self.logger = logging.getLogger(type(self).__name__)

        try:
            self.logger.debug("Loading FMU")
            self.model_description = read_model_description(fmu_path)

            filename = fmu_path

            if os.path.isfile(os.path.join(filename, 'modelDescription.xml')):
                unzipdir = filename
                tempdir = None
            else:
                tempdir = extract(filename)
                unzipdir = tempdir

            fmu_args = {'guid': self.model_description.guid,
                            'modelIdentifier': self.model_description.coSimulation.modelIdentifier,
                            'unzipDirectory': unzipdir,
                            'instanceName': None,
                            'fmiCallLogger': None}

            self.model = FMU2Slave(**fmu_args)

        except Exception as e:
            self.logger.error(e)

        self.start = None
        self.end = None
        self.timeline = None
        self.opts = opts

        self.input_names = list()
        self.input_values = list()
        self.output_names = list()
        self.parameter_names = list()
        # self.full_io = list()

        self.parameter_df = pd.DataFrame()

        self.res = None


__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

print(__location__)
model = Model('/home/georgii/Documents/modest-py/modestpy/fmi/Simple2R1C.fmu')
print(model.model_description.fmiVersion)

#model.reset
print(model.model_description.coSimulation.modelIdentifier)
model.model.instantiate()
#model.model.setFMUstate()
#model.model.getFMUstate()
#print(model.model.dll)
#print(model.model.setupExperiment())
model.model.freeLibrary()

model.model.reset()
print(model.model.dll)
