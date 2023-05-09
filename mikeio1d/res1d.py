import os.path

from .dotnet import from_dotnet_datetime
from .dotnet import to_dotnet_datetime
from .dotnet import to_numpy

from .result_extractor import ExtractorCreator
from .result_extractor import ExtractorOutputFileType
from .result_network import ResultNetwork
from .result_reader_writer import ResultReaderCreator
from .result_reader_writer import ResultReaderType
from .result_reader_writer import ResultWriter

from .query import QueryData            # noqa: F401
from .query import QueryDataCatchment   # noqa: F401
from .query import QueryDataNode        # noqa: F401
from .query import QueryDataReach       # noqa: F401
from .query import QueryDataStructure   # noqa: F401
from .query import QueryDataGlobal      # noqa: F401

from .various import mike1d_quantities  # noqa: F401
from .various import NAME_DELIMITER

from System import DateTime


class Res1D:
    """
    Class for reading data from 1D network result files into Pandas data frame.
    Currently supported formats are:
        * MIKE 1D network and catchment res1d files
        * MIKE 1D Long Term Statistics res1d files
        * MOUSE legacy PRF and CRF files
        * EPANET res and resx files generated by MIKE+
        * SWMM out files

    Parameters
    ----------
    file_path : str
        Relative or absolute path of the relevant result file.
    lazy_load : bool
        Flag specifying to load the file using lazy loading bridge of MIKE 1D.
        This typically is useful if only a few time steps need to be read for the whole network.
    header_load : bool
        Flag specifying to load just a header of the result file.
    reaches : list of str
        Filter list of reach ID strings, which will be included when loading the result file.
    nodes : list of str
        Filter list of node ID strings, which will be included when loading the result file.
    catchments : list of str
        Filter list of catchment ID strings, which will be included when loading the result file.
    col_name_delimiter : str
        String to delimit the quantity ID with location ID
        (and optionally chainage) in the data frame label.
    put_chainage_in_col_name : bool
        Flag specifying to add chainage into data frame column label.
    clear_queries_after_reading : bool
        Flag specifying to clear active queries after reading/processing them.

    Examples
    --------
    An example of reading the res1d file only for nodes with
    ID 'node1', 'node2' and reaches with ID 'reach1', 'reach2':
    ```python
    >>> nodes = ['node1', 'node2']
    >>> reaches = ['reach1', 'reach2']
    >>> res1d = Res1D('MyRes1D.res1d', nodes=nodes, reaches=reaches)
    >>> res1d.read()
    ```
    """

    def __init__(self,
                 file_path=None,
                 lazy_load=False,
                 header_load=False,
                 reaches=None,
                 nodes=None,
                 catchments=None,
                 col_name_delimiter=NAME_DELIMITER,
                 put_chainage_in_col_name=True,
                 clear_queries_after_reading=True,
                 result_reader_type=ResultReaderType.QUERY):

        self.result_reader = ResultReaderCreator.create(
            result_reader_type, self,
            file_path, lazy_load, header_load,
            reaches, nodes, catchments,
            col_name_delimiter, put_chainage_in_col_name)

        self._start_time = None
        self._end_time = None

        self.result_network = ResultNetwork(self)
        self.result_writer = ResultWriter(self)
        self._queries = self.result_network.queries

        self.clear_queries_after_reading = clear_queries_after_reading

    def __repr__(self):
        out = ["<mikeio1d.Res1D>"]

        if self.file_path:
            out.append(f"Start time: {str(self.start_time)}")
            out.append(f"End time: {str(self.end_time)}")
            out.append(f"# Timesteps: {str(self.data.NumberOfTimeSteps)}")
            out.append(f"# Catchments: {self.data.Catchments.get_Count()}")
            out.append(f"# Nodes: {self.data.Nodes.get_Count()}")
            out.append(f"# Reaches: {self.data.Reaches.get_Count()}")

            out.append(f"# Globals: {self.data.GlobalData.DataItems.Count}")
            for i, quantity in enumerate(self.data.Quantities):
                out.append(f"{i} - {quantity.Id} <{quantity.EumQuantity.UnitAbbreviation}>")

        return str.join("\n", out)

    #region Private methods

    def _get_actual_queries(self, queries):
        """ Finds out which list of queries should be used. """
        queries = self._queries if queries is None else queries
        queries = queries if isinstance(queries, list) else [queries]
        return queries

    #endregion Private methods

    def read(self, queries=None):
        """
        Read loaded .res1d file data based on queries.
        Currently the supported query classes are
            * :class:`query.QueryDataNode`
            * :class:`query.QueryDataReach`
            * :class:`query.QueryDataCatchment`

        Parameters
        ----------
        queries: A single query or a list of queries.
            Default is None = reads all data.

        Examples
        --------
        An example of reading res1d file with queries:
        ```python
        >>> res1d = Res1D('MyRes1D.res1d')
        >>> queries = [
                QueryDataNode('WaterLevel', 'node1'),
                QueryDataReach('Discharge', 'reach1', 50.0)
            ]
        >>> res1d.read(queries)
        ```
        """

        if queries is None and len(self._queries) == 0:
            return self.read_all()

        queries = self._get_actual_queries(queries)

        df = self.result_reader.read(queries)

        return df

    def read_all(self):
        """ Read all data from res1d file to dataframe. """
        return self.result_reader.read_all()

    def clear_queries(self):
        """ Clear the current active list of queries. """
        self.result_network.queries.clear()
        self.result_network.queries_ids.clear()

    @property
    def time_index(self):
        """ pandas.DatetimeIndex of the time index. """
        return self.result_reader.time_index

    @property
    def start_time(self):
        if self._start_time is not None:
            return self._start_time

        return from_dotnet_datetime(self.data.StartTime)

    @property
    def end_time(self):
        if self._end_time is not None:
            return self._end_time

        return from_dotnet_datetime(self.data.EndTime)

    @property
    def quantities(self):
        """ Quantities in res1d file. """
        return self.result_reader.quantities

    @property
    def query(self):
        """
        .NET object ResultDataQuery to use for querying the loaded res1d data.

        More information about ResultDataQuery class see:
        https://manuals.mikepoweredbydhi.help/latest/General/Class_Library/DHI_MIKE1D/html/T_DHI_Mike1D_ResultDataAccess_ResultDataQuery.htm
        """
        return self.result_reader.query

    @property
    def file_path(self):
        """ File path of the result file. """
        return self.result_reader.file_path

    @property
    def data(self):
        """
        .NET object ResultData with the loaded res1d data.

        More information about ResultData class see:
        https://manuals.mikepoweredbydhi.help/latest/General/Class_Library/DHI_MIKE1D/html/T_DHI_Mike1D_ResultDataAccess_ResultData.htm
        """
        return self.result_reader.data

    @property
    def catchments(self):
        """ Catchments in res1d file. """
        return self.result_network.catchments

    @property
    def reaches(self):
        """ Reaches in res1d file. """
        return self.result_network.reaches

    @property
    def nodes(self):
        """ Nodes in res1d file. """
        return self.result_network.nodes

    @property
    def structures(self):
        """ Structures in res1d file. """
        return self.result_network.structures

    @property
    def global_data(self):
        """ Global data items in res1d file. """
        return self.result_network.global_data

    #region Query wrappers

    def get_catchment_values(self, catchment_id, quantity):
        return to_numpy(self.query.GetCatchmentValues(catchment_id, quantity))

    def get_node_values(self, node_id, quantity):
        return to_numpy(self.query.GetNodeValues(node_id, quantity))

    def get_reach_values(self, reach_name, chainage, quantity):
        return to_numpy(self.query.GetReachValues(reach_name, chainage, quantity))

    def get_reach_value(self, reach_name, chainage, quantity, time):
        if self.result_reader.is_lts_result_file():
            raise NotImplementedError('The method is not implemented for LTS event statistics.')

        time_dotnet = time if isinstance(time, DateTime) else to_dotnet_datetime(time)
        return self.query.GetReachValue(reach_name, chainage, quantity, time_dotnet)

    def get_reach_start_values(self, reach_name, quantity):
        return to_numpy(self.query.GetReachStartValues(reach_name, quantity))

    def get_reach_end_values(self, reach_name, quantity):
        return to_numpy(self.query.GetReachEndValues(reach_name, quantity))

    def get_reach_sum_values(self, reach_name, quantity):
        return to_numpy(self.query.GetReachSumValues(reach_name, quantity))

    #endregion Query wrapper

    def modify(self, data_frame, file_path=None):
        """
        Modifies the ResultData object TimeData based on the provided data frame.

        Parameters
        ----------
        data_frame : pandas.DataFrame
            Pandas data frame object with column names based on query labels
        file_path : str
            File path for the new res1d file. Optional.
        """
        self.result_writer.modify(data_frame)
        if file_path is not None:
            self.save(file_path)

    def save(self, file_path):
        """
        Saves the ResultData to a new res1d file.

        Parameters
        ----------
        file_path : str
            File path for the new res1d file.
        """
        self.data.Connection.FilePath.Path = file_path
        self.data.Save()

    def extract(self, file_path, queries=None, time_step_skipping_number=1, ext=None):
        """
        Extract given queries to provided file.
        File type is determined from file_path extension.
        The supported formats are:
        * csv
        * dfs0
        * txt

        Parameters
        ----------
        file_path : str
            Output file path.
        queries : list
            List of queries.
        time_step_skipping_number : int
            Number specifying the time step frequency to output.
        ext : str
            Output file type to use instead of determining it from extension.
            Can be 'csv', 'dfs0', 'txt'.
        """
        ext = os.path.splitext(file_path)[-1] if ext is None else ext

        queries = self._get_actual_queries(queries)
        data_entries = self.result_network.convert_queries_to_data_entries(queries)

        extractor = ExtractorCreator.create(ext, file_path, data_entries, self.data, time_step_skipping_number)
        extractor.export()

        if self.clear_queries_after_reading:
            self.clear_queries()

    def to_csv(self, file_path, queries=None, time_step_skipping_number=1):
        """ Extract to csv file. """
        self.extract(file_path, queries, time_step_skipping_number, ExtractorOutputFileType.CSV)

    def to_dfs0(self, file_path, queries=None, time_step_skipping_number=1):
        """ Extract to dfs0 file. """
        self.extract(file_path, queries, time_step_skipping_number, ExtractorOutputFileType.DFS0)

    def to_txt(self, file_path, queries=None, time_step_skipping_number=1):
        """ Extract to txt file. """
        self.extract(file_path, queries, time_step_skipping_number, ExtractorOutputFileType.TXT)
