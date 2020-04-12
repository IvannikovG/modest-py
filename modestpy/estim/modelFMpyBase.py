from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
from fmpy import simulate_fmu
import numpy as np
import pandas as pd
import os
from fmpy.model_description import read_model_description

class Model(object):
    """
    FMU model to be simulated with inputs and parameters provided from
    files or dataframes.
    """

    def __init__(self, fmu_path, opts=None):
        self.logger = logging.getLogger(type(self).__name__)

        try:
            self.logger.debug("Loading FMU")
            self.fmu_path = fmu_path
            self.model_description = read_model_description(self.fmu_path)

            self.fmu_args = {'guid': self.model_description.guid,
                            'modelIdentifier': self.model_description.coSimulation.modelIdentifier,
                            'instanceName': None,
                            'fmiCallLogger': None}

        except Exception as e:
            self.logger.error(e)

        self.opts = opts
        self.start = None
        self.end = None
        self.timeline = None

        self.input_names = list()
        self.input_values = list()
        self.output_names = list()
        self.parameter_names = list()
        self.parameter_df = pd.DataFrame()
        self.res = None

    #Specify input for a model, return None
    def specify_input(self, input):
        self.input = np.genfromtxt(input, delimiter=',', names=True)

    def parameters_from_csv(self, csv, sep=','):
        df = pd.read_csv(csv, sep=sep)
        self.parameters_from_df(df)

    def parameters_from_df(self, df):
        if df is not None:
            df = df.copy()
            for col in df:
                self.parameter_df[col] = df[col]

    def specify_outputs(self, outputs):
        """
        Specifies names of output variables
        :param outputs: List of strings, names of output variables
        :return: None
        """
        for name in outputs:
            if name not in self.output_names:
                self.output_names.append(name)

    def simulate(self, com_points=None, reset=True):
        if com_points is None:
            self.logger.warning('[fmi\\model] Warning! Default number '
                                    'of communication points assumed (500)')
            com_points = 500

        self.res = simulate_fmu(self.fmu_path,
                                start_time=self.start,
                                stop_time=self.end,
                                input=self.input,
                                output=self.output_names)


        df = pd.DataFrame()
        df['time'] = self.res['time']
        df = df.set_index('time')
        for var in self.output_names:
            df[var] = self.res[var]


        for var in self.output_names:
            print(var)

        # Reset model
        if reset:
            try:
                self.reset()
            except Exception as e:
                self.logger.warning(
                    "If you try to simulate an EnergyPlus FMU, "
                    "use reset=False"
                    )

        # Return
        print("Returning dataframe")
        return df



__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

print("========================================")
#model = Model('/home/georgii/Documents/modest-py/modestpy/fmi/Simple2R1C.fmu')
#model.parameters_from_csv('/home/georgii/Documents/modest-py/modestpy/fmi/true_parameters.csv')
#model.specify_outputs(['Ti1', 'Ti2'])
#model.specify_input('/home/georgii/Documents/modest-py/modestpy/fmi/inputs.csv')
#print(model.simulate())
print("Imported Base Model")
print("========================================")
