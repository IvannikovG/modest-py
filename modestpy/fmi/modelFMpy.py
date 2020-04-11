from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
from fmpy.model_description import read_model_description
from fmpy.fmi2 import FMU2Slave
from fmpy import simulate_fmu
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

        self.parameter_df = pd.DataFrame()

        self.res = None

    def inputs_from_csv(self, csv, sep=',', exclude=list()):
        """
        Reads inputs from a CSV file (format of the standard input file
        in ModelManager). It is assumed that time is given in seconds.
        :param csv: Path to the CSV file
        :param exclude: list of strings, columns to be excluded
        :return: None
        """
        df = pd.read_csv(csv, sep=sep)
        assert 'time' in df.columns, "'time' not present in csv..."
        df = df.set_index('time')
        self.inputs_from_df(df, exclude)

    def inputs_from_df(self, df, exclude=list()):
        """
        Reads inputs from dataframe.

        Index must be named 'time' and given in seconds.
        The index name assertion check is implemented to avoid
        situations in which a user read DataFrame from csv
        and forgot to use ``DataFrame.set_index(column_name)``
        (it happens quite often...).

        :param df: DataFrame
        :param exclude: list of strings, names of columns to be omitted
        :return:
        """
        assert df.index.name == 'time', "Index name ('{}') different " \
                                        "than 'time'! " \
                                        "Are you sure you assigned index " \
                                        "correctly?".format(df.index.name)
        self.timeline = df.index.values
        self.start = self.timeline[0]
        self.end = self.timeline[-1]

        for col in df:
            if col not in exclude:
                if col not in self.input_names:
                    self.input_names.append(col)
                    self.input_values.append(df[col].values)

    def specify_outputs(self, outputs):
        """
        Specifies names of output variables
        :param outputs: List of strings, names of output variables
        :return: None
        """
        for name in outputs:
            if name not in self.output_names:
                self.output_names.append(name)

    def parameters_from_csv(self, csv, sep=','):
        df = pd.read_csv(csv, sep=sep)
        self.parameters_from_df(df)

    def parameters_from_df(self, df):
        if df is not None:
            df = df.copy()
            for col in df:
                self.parameter_df[col] = df[col]

    input = np.genfromtxt('/home/georgii/Documents/modest-py/modestpy/fmi/inputs.csv', delimiter=',', names=True)

    def simulate(self, input=input, com_points=None, reset=True):
        if com_points is None:
            self.logger.warning('[fmi\\model] Warning! Default number '
                                    'of communication points assumed (500)')
            com_points = 500

        self.res = simulate_fmu('/home/georgii/Documents/modest-py/modestpy/fmi/Simple2R1C.fmu',
                                start_time=0.0,
                                stop_time=100,
                                input=input)


        print(self.res)

        df = pd.DataFrame()
        df['time'] = self.res['time']
        df = df.set_index('time')
        for var in self.output_names:
            df[var] = self.res[var]

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
        return df






__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

print(__location__)
model = Model('/home/georgii/Documents/modest-py/modestpy/fmi/Simple2R1C.fmu')
print("Model fmi version:", model.model_description.fmiVersion)
print("Model name:", model.model_description.coSimulation.modelIdentifier)
model.model.instantiate()
print("Model object:", model.model)
print("Model dll:", model.model.dll)
print(model.model_description.modelVariables)
model.model.reset()
print("model was reset") # what does reset mean?
print(model.model_description)
print("Model dll:", model.model.dll)
print(model.model)
print("Free the model instance")
model.model.freeInstance()
print(model.model.dll)

#print("Model terminated")
#model.model.terminate()

print("Test")

a = []

for i in model.model_description.modelVariables:
    a.append(i)
print(a)

print("========================================")
print("========================================")
model.inputs_from_csv('/home/georgii/Documents/modest-py/modestpy/fmi/inputs.csv')
model.parameters_from_csv('/home/georgii/Documents/modest-py/modestpy/fmi/true_parameters.csv')

print(model.simulate())
input = np.genfromtxt('/home/georgii/Documents/modest-py/modestpy/fmi/inputs.csv', delimiter=',', names=True)
#print(input)
