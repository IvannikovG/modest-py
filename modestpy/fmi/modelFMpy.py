from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
from fmpy import simulate_fmu
import numpy as np
import pandas as pd
import os
from fmpy import extract
from fmpy.model_description import read_model_description



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

        self.fmu_path = fmu_path
        filename = self.fmu_path
        self.model_description = read_model_description(self.fmu_path)
        try:
            self.logger.debug("Loading FMU")


            if os.path.isfile(os.path.join(filename, 'modelDescription.xml')):
                unzipdir = filename
                tempdir = None
            else:
                tempdir = extract(filename)
                unzipdir = tempdir

            self.fmu_args = {'guid': self.model_description.guid,
                            'modelIdentifier': self.model_description.coSimulation.modelIdentifier,
                            'unzipDirectory': unzipdir,
                            'instanceName': None,
                            'fmiCallLogger': None}

            #self.model = FMU2Slave(**fmu_args)

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

        self.output_names = ['Ti1']
        self.res = simulate_fmu(self.fmu_path,
                                start_time=0.0,
                                stop_time=100,
                                input=input,
                                output=self.output_names)

        #print(self.res)

        df = pd.DataFrame()
        #print("Self.res.time:", self.res['time'])
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

print(__location__)
model = Model('/home/georgii/Documents/modest-py/modestpy/fmi/Simple2R1C.fmu')

print("========================================")
print("========================================")
model.inputs_from_csv('/home/georgii/Documents/modest-py/modestpy/fmi/inputs.csv')
model.parameters_from_csv('/home/georgii/Documents/modest-py/modestpy/fmi/true_parameters.csv')


print(model.simulate())
