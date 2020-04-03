cdef class FMUModelCS2(FMUModelBase2):
    """
    Co-simulation model loaded from a dll
    """
    def __init__(self, fmu, path = '.', enable_logging = None, log_file_name = "", log_level=FMI_DEFAULT_LOG_LEVEL, _unzipped_dir=None, _connect_dll=True):
        """
        Constructor of the model.
        Parameters::
            fmu --
                Name of the fmu as a string.
            path --
                Path to the fmu-directory.
                Default: '.' (working directory)
            enable_logging [DEPRECATED] --
                This option is DEPRECATED and will be removed. Please
                use the option "log_level" instead.
            log_file_name --
                Filename for file used to save log messages.
                Default: "" (Generates automatically)

            log_level --
                Determines the logging output. Can be set between 0
                (no logging) and 7 (everything).
                Default: 2 (log error messages)
        Returns::
            A model as an object from the class FMUModelCS2
        """

        #Call super
        FMUModelBase2.__init__(self, fmu, path, enable_logging, log_file_name, log_level, _unzipped_dir, _connect_dll)

        if self._fmu_kind != FMIL.fmi2_fmu_kind_cs:
            if self._fmu_kind != FMIL.fmi2_fmu_kind_me_and_cs:
                raise FMUException("This class only supports FMI 2.0 for Co-simulation.")

        if self.get_capability_flags()['needsExecutionTool'] == True:
            raise FMUException('Models that need an execution tool are not supported')

        self._modelId = decode(FMIL.fmi2_import_get_model_identifier_CS(self._fmu))

        if _connect_dll:
            self.instantiate()

    def __dealloc__(self):
        """
        Deallocate memory allocated
        """
        if self._allocated_fmu == 1:
            FMIL.fmi2_import_terminate(self._fmu)
            FMIL.fmi2_import_free_instance(self._fmu)

        if self._allocated_dll == 1:
            FMIL.fmi2_import_destroy_dllfmu(self._fmu)

        if self._allocated_xml == 1:
            FMIL.fmi2_import_free(self._fmu)

        if self._fmu_temp_dir != NULL:
            FMIL.fmi_import_rmdir(&self.callbacks, self._fmu_temp_dir)
            FMIL.free(self._fmu_temp_dir)
            self._fmu_temp_dir = NULL

        if self._allocated_context == 1:
            FMIL.fmi_import_free_context(self._context)

        if self._fmu_log_name != NULL:
            FMIL.free(self._fmu_log_name)
            self._fmu_log_name = NULL

    cpdef _get_time(self):
        """
        Returns the current time of the simulation.
        Returns::
            The time.
        """
        return self.__t

    cpdef _set_time(self, FMIL.fmi2_real_t t):
        """
        Sets the current time of the simulation.
        Parameters::
            t--
                The time to set.
        """
        self.__t = t

    time = property(_get_time,_set_time, doc =
    """
    Property for accessing the current time of the simulation. Calls the
    low-level FMI function: fmiSetTime
    """)

    cpdef int do_step(self, FMIL.fmi2_real_t current_t, FMIL.fmi2_real_t step_size, new_step=True):
        """
        Performs an integrator step.
        Parameters::
            current_t --
                The current communication point (current time) of
                the master.
            step_size --
                The length of the step to be taken.
            new_step --
                True the last step was accepted by the master and
                False if not.
        Returns::
            status --
                    The status of function which can be checked against
                    FMI_OK, FMI_WARNING. FMI_DISCARD, FMI_ERROR,
                    FMI_FATAL,FMI_PENDING...
        Calls the underlying low-level function fmi2DoStep.
        """
        cdef int status
        cdef FMIL.fmi2_boolean_t new_s

        if new_step:
            new_s = 1
        else:
            new_s = 0

        self.time = current_t + step_size

        log_open = self._log_open()
        if not log_open and self.get_log_level() > 2:
            self._open_log_file()

        status = FMIL.fmi2_import_do_step(self._fmu, current_t, step_size, new_s)

        if not log_open and self.get_log_level() > 2:
            self._close_log_file()

        return status

    def cancel_step(self):
        """
        Cancel a current integrator step. Can only be called if the
        status from do_step returns FMI_PENDING. After this function has
        been called it is only allowed to reset the model (i.e. start
        over).
        """
        cdef int status

        status = FMIL.fmi2_import_cancel_step(self._fmu)
        if status != 0:
            raise FMUException('An error occured while canceling the step')


    def set_input_derivatives(self, variables, values, FMIL.fmi2_integer_t order):
        """
        Sets the input derivative order for the specified variables.
        Parameters::
                variables --
                        The variables as a string or list of strings for
                        which the input derivative(s) should be set.
                values --
                        The actual values.
                order --
                        The derivative order to set.
        """
        cdef int          status
        cdef unsigned int can_interpolate_inputs
        cdef FMIL.size_t  nref
        cdef N.ndarray[FMIL.fmi2_integer_t, ndim=1, mode='c']         orders
        cdef N.ndarray[FMIL.fmi2_value_reference_t, ndim=1, mode='c'] value_refs
        cdef N.ndarray[FMIL.fmi2_real_t, ndim=1, mode='c']            val = N.array(values, dtype=N.float, ndmin=1).ravel()

        nref = val.size
        orders = N.array([0]*nref, dtype=N.int32)

        can_interpolate_inputs = FMIL.fmi2_import_get_capability(self._fmu, FMIL.fmi2_cs_canInterpolateInputs)
        #NOTE IS THIS THE HIGHEST ORDER OF INTERPOLATION OR SIMPLY IF IT CAN OR NOT?

        if order < 1:
            raise FMUException("The order must be greater than zero.")
        if not can_interpolate_inputs:
            raise FMUException("The FMU does not support input derivatives.")

        if isinstance(variables,str):
            value_refs = N.array([0], dtype=N.uint32, ndmin=1).ravel()
            value_refs[0] = self.get_variable_valueref(variables)
        elif isinstance(variables,list) and N.prod([int(isinstance(v,str)) for v in variables]): #prod equals 0 or 1
            value_refs = N.array([0]*nref, dtype=N.uint32,ndmin=1).ravel()
            for i in range(nref):
                value_refs[i] = self.get_variable_valueref(variables[i])
                orders[i] = order
        else:
            raise FMUException("The variables must either be a string or a list of strings")

        status = self._set_input_derivatives(value_refs, val, orders)
        #status = FMIL.fmi2_import_set_real_input_derivatives(self._fmu, <FMIL.fmi2_value_reference_t*> value_refs.data, nref,
        #                                                        <FMIL.fmi2_integer_t*> orders.data, <FMIL.fmi2_real_t*> val.data)

        if status != 0:
            raise FMUException('Failed to set the Real input derivatives.')

    cdef int _set_input_derivatives(self, N.ndarray[FMIL.fmi2_value_reference_t, ndim=1, mode="c"] value_refs,
                                          N.ndarray[FMIL.fmi2_real_t, ndim=1, mode="c"] values,
                                          N.ndarray[FMIL.fmi2_integer_t, ndim=1, mode="c"] orders):
        cdef int status

        assert values.size >= value_refs.size and orders.size >= value_refs.size

        status = FMIL.fmi2_import_set_real_input_derivatives(self._fmu,
                        <FMIL.fmi2_value_reference_t*> value_refs.data,
                        value_refs.size, <FMIL.fmi2_integer_t*> orders.data,
                        <FMIL.fmi2_real_t*> values.data)

        return status

    def get_output_derivatives(self, variables, FMIL.fmi2_integer_t order):
        """
        Returns the output derivatives for the specified variables. The
        order specifies the nth-derivative.
        Parameters::
            variables --
                The variables for which the output derivatives
                should be returned.
            order --
                The derivative order.
        Returns::
            The derivatives of the specified order.
        """
        cdef int status
        cdef unsigned int max_output_derivative
        cdef FMIL.size_t  nref
        cdef N.ndarray[FMIL.fmi2_real_t, ndim=1, mode='c']            values
        cdef N.ndarray[FMIL.fmi2_value_reference_t, ndim=1, mode='c'] value_refs
        cdef N.ndarray[FMIL.fmi2_integer_t, ndim=1, mode='c']         orders


        max_output_derivative = FMIL.fmi2_import_get_capability(self._fmu, FMIL.fmi2_cs_maxOutputDerivativeOrder)

        if order < 1 or order > max_output_derivative:
            raise FMUException("The order must be greater than zero and below the maximum output derivative support of the FMU (%d)."%max_output_derivative)

        if isinstance(variables,str):
            nref = 1
            value_refs = N.array([0], dtype=N.uint32, ndmin=1).ravel()
            orders = N.array([order], dtype=N.int32)
            value_refs[0] = self.get_variable_valueref(variables)
        elif isinstance(variables,list) and N.prod([int(isinstance(v,str)) for v in variables]): #prod equals 0 or 1
            nref = len(variables)
            value_refs = N.array([0]*nref, dtype=N.uint32, ndmin=1).ravel()
            orders = N.array([0]*nref, dtype=N.int32)
            for i in range(nref):
                value_refs[i] = self.get_variable_valueref(variables[i])
                orders[i] = order
        else:
            raise FMUException("The variables must either be a string or a list of strings")

        values = N.array([0.0]*nref, dtype=N.float, ndmin=1)

        #status = FMIL.fmi2_import_get_real_output_derivatives(self._fmu, <FMIL.fmi2_value_reference_t*> value_refs.data, nref,
        #                                                    <FMIL.fmi2_integer_t*> orders.data, <FMIL.fmi2_real_t*> values.data)
        status = self._get_output_derivatives(value_refs, values, orders)

        if status != 0:
            raise FMUException('Failed to get the Real output derivatives.')

        return values

    cdef int _get_output_derivatives(self, N.ndarray[FMIL.fmi2_value_reference_t, ndim=1, mode="c"] value_refs,
                                           N.ndarray[FMIL.fmi2_real_t, ndim=1, mode="c"] values,
                                           N.ndarray[FMIL.fmi2_integer_t, ndim=1, mode="c"] orders):
        cdef int status

        assert values.size >= value_refs.size and orders.size >= value_refs.size

        status = FMIL.fmi2_import_get_real_output_derivatives(self._fmu,
                    <FMIL.fmi2_value_reference_t*> value_refs.data, value_refs.size,
                    <FMIL.fmi2_integer_t*> orders.data, <FMIL.fmi2_real_t*> values.data)

        return status


    def get_status(self, status_kind):
        """
        Retrieves the fmi-status for the the specified fmi-staus-kind.
        Parameters::
            status_kind --
                An integer corresponding to one of the following:
                fmi2DoStepStatus       = 0
                fmi2PendingStatus      = 1
                fmi2LastSuccessfulTime = 2
                fmi2Terminated         = 3
        Returns::
            status_ok      = 0
            status_warning = 1
            status_discard = 2
            status_error   = 3
            status_fatal   = 4
            status_pending = 5
        """

        cdef int status
        cdef FMIL.fmi2_status_kind_t fmi_status_kind
        cdef FMIL.fmi2_status_t status_value

        if status_kind >= 0 and status_kind <= 3:
            fmi_status_kind = status_kind
        else:
            raise FMUException('Status kind has to be between 0 and 3')

        status = FMIL.fmi2_import_get_status(self._fmu, fmi_status_kind, &status_value)
        if status != 0:
            raise FMUException('An error occured while retriving the status')

        return status_value

    def get_real_status(self, status_kind):
        """
        Retrieves the status, represented as a real-value,
        for the specified fmi-status-kind.
        See docstring for function get_status() for more
        information about fmi-status-kind.
        Parameters::
            status_kind--
                integer indicating the status kind
        Returns::
            The status.
        """

        cdef int status
        cdef int fmi_status_kind
        cdef FMIL.fmi2_real_t output

        if status_kind >= 0 and status_kind <= 3:
            fmi_status_kind = status_kind
        else:
            raise FMUException('Status kind has to be between 0 and 3')


        status = FMIL.fmi2_import_get_real_status(self._fmu, fmi_status_kind, &output)
        if status != 0:
            raise FMUException('An error occured while retriving the status')

        return output

    def get_integer_status(self, status_kind):
        """
        Retrieves the status, represented as a integer-value,
        for the specified fmi-status-kind.
        See docstring for function get_status() for more
        information about fmi-status-kind.
        Parameters::
            status_kind--
                integer indicating the status kind
        Returns::
            The status.
        """

        cdef int status
        cdef int fmi_status_kind
        cdef FMIL.fmi2_integer_t output

        if status_kind >= 0 and status_kind <= 3:
            fmi_status_kind = status_kind
        else:
            raise FMUException('Status kind has to be between 0 and 3')


        status = FMIL.fmi2_import_get_integer_status(self._fmu, fmi_status_kind, &output)
        if status != 0:
            raise FMUException('An error occured while retriving the status')

        return output

    def get_boolean_status(self, status_kind):
        """
        Retrieves the status, represented as a boolean-value,
        for the specified fmi-status-kind.
        See docstring for function get_status() for more
        information about fmi-status-kind.
        Parameters::
            status_kind--
                integer indicating the status kind
        Returns::
            The status.
        """

        cdef int status
        cdef int fmi_status_kind
        cdef FMIL.fmi2_boolean_t output

        if status_kind >= 0 and status_kind <= 3:
            fmi_status_kind = status_kind
        else:
            raise FMUException('Status kind has to be between 0 and 3')


        status = FMIL.fmi2_import_get_boolean_status(self._fmu, fmi_status_kind, &output)
        if status != 0:
            raise FMUException('An error occured while retriving the status')

        return output

    def get_string_status(self, status_kind):
        """
        Retrieves the status, represented as a string-value,
        for the specified fmi-status-kind.
        See docstring for function get_status() for more
        information about fmi-status-kind.
        Parameters::
            status_kind--
                integer indicating the status kind
        Returns::
            The status.
        """

        cdef int status
        cdef int fmi_status_kind
        cdef FMIL.fmi2_string_t output

        if status_kind >= 0 and status_kind <= 3:
            fmi_status_kind = status_kind
        else:
            raise FMUException('Status kind has to be between 0 and 3')


        status = FMIL.fmi2_import_get_string_status(self._fmu, fmi_status_kind, &output)
        if status != 0:
            raise FMUException('An error occured while retriving the status')

        return output


    def simulate(self,
                 start_time="Default",
                 final_time="Default",
                 input=(),
                 algorithm='FMICSAlg',
                 options={}):
        """
        Compact function for model simulation.
        The simulation method depends on which algorithm is used, this can be
        set with the function argument 'algorithm'. Options for the algorithm
        are passed as option classes or as pure dicts. See
        FMUModel.simulate_options for more details.
        The default algorithm for this function is FMICSAlg.
        Parameters::
            start_time --
                Start time for the simulation.
                Default: Start time defined in the default experiment from
                        the ModelDescription file.
            final_time --
                Final time for the simulation.
                Default: Stop time defined in the default experiment from
                        the ModelDescription file.
            input --
                Input signal for the simulation. The input should be a 2-tuple
                consisting of first the names of the input variable(s) and then
                the data matrix.
                Default: Empty tuple.
            algorithm --
                The algorithm which will be used for the simulation is specified
                by passing the algorithm class as string or class object in this
                argument. 'algorithm' can be any class which implements the
                abstract class AlgorithmBase (found in algorithm_drivers.py). In
                this way it is possible to write own algorithms and use them
                with this function.
                Default: 'FMICSAlg'
            options --
                The options that should be used in the algorithm. For details on
                the options do:
                    >> myModel = load_fmu(...)
                    >> opts = myModel.simulate_options()
                    >> opts?
                Valid values are:
                    - A dict which gives AssimuloFMIAlgOptions with
                      default values on all options except the ones
                      listed in the dict. Empty dict will thus give all
                      options with default values.
                    - An options object.
                Default: Empty dict
        Returns::
            Result object, subclass of common.algorithm_drivers.ResultBase.
        """
        if start_time == "Default":
            start_time = self.get_default_experiment_start_time()
        if final_time == "Default":
            final_time = self.get_default_experiment_stop_time()

        return self._exec_simulate_algorithm(start_time,
                                             final_time,
                                             input,
                                             'pyfmi.fmi_algorithm_drivers',
                                             algorithm,
                                             options)

    def simulate_options(self, algorithm='FMICSAlg'):
        """
        Get an instance of the simulate options class, filled with default
        values. If called without argument then the options class for the
        default simulation algorithm will be returned.
        Parameters::
            algorithm --
                The algorithm for which the options class should be fetched.
                Possible values are: 'FMICSAlg'.
                Default: 'FMICSAlg'
        Returns::
            Options class for the algorithm specified with default values.
        """
        return self._default_options('pyfmi.fmi_algorithm_drivers', algorithm)

    def get_capability_flags(self):
        """
        Returns a dictionary with the capability flags of the FMU.
        Returns::
            Dictionary with keys:
            needsExecutionTool
            canHandleVariableCommunicationStepSize
            canInterpolateInputs
            maxOutputDerivativeOrder
            canRunAsynchronuously
            canBeInstantiatedOnlyOncePerProcess
            canNotUseMemoryManagementFunctions
            canGetAndSetFMUstate
            providesDirectionalDerivatives
        """
        cdef dict capabilities = {}
        capabilities['needsExecutionTool']                     = bool(FMIL.fmi2_import_get_capability(self._fmu, FMIL.fmi2_cs_needsExecutionTool))
        capabilities['canHandleVariableCommunicationStepSize'] = bool(FMIL.fmi2_import_get_capability(self._fmu, FMIL.fmi2_cs_canHandleVariableCommunicationStepSize))
        capabilities['canInterpolateInputs']                   = bool(FMIL.fmi2_import_get_capability(self._fmu, FMIL.fmi2_cs_canInterpolateInputs))
        capabilities['maxOutputDerivativeOrder']               = FMIL.fmi2_import_get_capability(self._fmu, FMIL.fmi2_cs_maxOutputDerivativeOrder)
        capabilities['canRunAsynchronuously']                  = bool(FMIL.fmi2_import_get_capability(self._fmu, FMIL.fmi2_cs_canRunAsynchronuously))
        capabilities['canBeInstantiatedOnlyOncePerProcess']    = bool(FMIL.fmi2_import_get_capability(self._fmu, FMIL.fmi2_cs_canBeInstantiatedOnlyOncePerProcess))
        capabilities['canNotUseMemoryManagementFunctions']     = bool(FMIL.fmi2_import_get_capability(self._fmu, FMIL.fmi2_cs_canNotUseMemoryManagementFunctions))
        capabilities['canGetAndSetFMUstate']                   = bool(FMIL.fmi2_import_get_capability(self._fmu, FMIL.fmi2_cs_canGetAndSetFMUstate))
        capabilities['canSerializeFMUstate']                   = bool(FMIL.fmi2_import_get_capability(self._fmu, FMIL.fmi2_cs_canSerializeFMUstate))
        capabilities['providesDirectionalDerivatives']         = bool(FMIL.fmi2_import_get_capability(self._fmu, FMIL.fmi2_cs_providesDirectionalDerivatives))

        return capabilities

    def _provides_directional_derivatives(self):
        """
        Check capability to provide directional derivatives.
        """
        return FMIL.fmi2_import_get_capability(self._fmu, FMIL.fmi2_cs_providesDirectionalDerivatives)

    def _supports_get_set_FMU_state(self):
        """
        Check support for getting and setting the FMU state.
        """
        return FMIL.fmi2_import_get_capability(self._fmu, FMIL.fmi2_cs_canGetAndSetFMUstate)
