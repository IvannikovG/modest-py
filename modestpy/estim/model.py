
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
from fmi.model import Model as FMPyModel

VERBOSE = True

class Model(object):
    def __init__(self, fmu_path, opts=None):
        self.logger = logging.getLogger(type(self).__name__)

        self.model = FMPyModel(fmu_path, opts=opts)

        #Logging: >TODO<

        # Simulation count
        self.sim_count = 0

        def set_input(self, df, exclude=list()):
            """ Sets inputs.

            :param df: Dataframe, time given in seconds
            :param exclude: list of strings, names of columns to be excluded
            :return: None
            """
            self.model.inputs_from_df(df, exclude)

        def set_param(self, df):
            """ Sets parameters. It is possible to set only a subset of model parameters.

            :param df: Dataframe with header and a single row of data
            :return: None
            """
            self.model.parameters_from_df(df)

        def set_outputs(self, outputs):
            """ Sets output variables.

            :param outputs: list of strings
            :return: None
            """
            self.model.specify_outputs(outputs)

        def simulate(self, com_points=None):
            # TODO: com_points should be adjusted to the number of samples
            self.sim_count += 1
            self.info('Simulation count CYKA!! = ' + str(self.sim_count))
            return self.model.simulate(com_points=com_points)

        def info(self, txt):
            class_name = self.__class__.__name__
            if VERBOSE:
                if isinstance(txt, str):
                    print('[' + class_name + '] ' + txt)
                else:
                    print('[' + class_name + '] ' + repr(txt))


model = Model('/home/georgii/Documents/modest-py/modestpy/fmi/Simple2R1C.fmu')
model.model.specify_outputs(['Ti1', 'Ti2'])
model.model.inputs_from_csv('/home/georgii/Documents/modest-py/modestpy/fmi/inputs.csv')
print(model.model.simulate())
