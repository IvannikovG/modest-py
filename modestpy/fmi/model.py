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

            self.fmu_args = {
                'guid': self.model_description.guid,
                'modelIdentifier': self.model_description.coSimulation.modelIdentifier,
                'instanceName': None,
                'fmiCallLogger': None
            }

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
        self.input = None
        self.parameter_df = pd.DataFrame()
        self.res = None

    def parameters_from_csv(self, csv, sep=','):
        df = pd.read_csv(csv, sep=sep)
        self.parameters_from_df(df)

    def parameters_from_df(self, df):
        if df is not None:
            df = df.copy()
            for col in df:
                self.parameter_df[col] = df[col]

    def inputs_from_csv(self, csv, sep=',', exclude=list()):
        """
        Reads inputs from a CSV file (format of the standard input file
        in ModelManager). It is assumed that time is given in seconds.
        :param csv: Path to the CSV file
        :param exclude: list of strings, columns to be excluded
        :return: None
        """
        self.input = np.genfromtxt(csv, delimiter=sep, names=True)
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

    def simulate(self, com_points=None, reset=True):
        if com_points is None:
            self.logger.warning('[fmi\\model] Warning! Default number '
                                    'of communication points assumed (500)')
            com_points = 500

        #Init start and end, init input

        self.res = simulate_fmu(self.fmu_path,
                                start_time=self.start,
                                stop_time=self.end,
                                #output_interval=431.88,
                                input=self.input,
                                output=self.output_names)


        df = pd.DataFrame()
        df['time'] = self.res['time']
        df = df.set_index('time')
        for var in self.output_names:
            df[var] = self.res[var]

        # # Reset model
        # if reset:
        #     try:
        #         self.reset()
        #     except Exception as e:
        #         self.logger.warning(
        #             "If you try to simulate an EnergyPlus FMU, "
        #             "use reset=False"
        #             )

        # Return
        print("Returning dataframe")
        return df

        @staticmethod
        def _merge_inputs(inputs):
            return np.transpose(np.vstack(inputs))

        @staticmethod
        def _create_timeline(end, intervals):
            t = np.linspace(0, end, intervals+1)
            return t


if __name__ == "__main__":
    print("========================================")
    basedir = os.getenv(
        'DE_AES_DIR_BASE',
        os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..')
    )
    print(basedir)

    model = Model(
        os.path.join(basedir, 'modestpy/test/resources/simple2R1C/Simple2R1C_linux64.fmu')
    )
    model.parameters_from_csv(
        os.path.join(basedir, 'modestpy/test/resources/simple2R1C/parameters.csv')
    )
    model.specify_outputs(['Ti1', 'Ti2'])
    model.inputs_from_csv(os.path.join(basedir, 'modestpy/test/resources/simple2R1C/inputs.csv'))

    print("Imported Base Model")
    print("========================================")

    print(model.simulate())
    print(model.input.shape)
