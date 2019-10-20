"""

THIS IS POMATO
INPUT: DATA
OUTPUT: RESULTS

"""
from pathlib import Path
import logging
import json

from data_management import DataManagement
from grid_model import GridModel
from market_model import MarketModel
from cbco_module import CBCOModule
import bokeh_plot_interface as bokeh
import tools

def _logging_setup(wdir, webapp):
    # Logging setup
    logger = logging.getLogger('Log.MarketModel')
    logger.setLevel(logging.INFO)
    if len(logger.handlers) < 2:
        # create file handler which logs even debug messages
        if not wdir.joinpath("logs").is_dir():
            wdir.joinpath("logs").mkdir()

        if webapp:
            logfile_path = wdir.joinpath("logs").joinpath('market_tool_webapp.log')
            # Clear Logfile
            with open(logfile_path, 'w'):
                pass 
            file_handler = logging.FileHandler(logfile_path)
            file_handler.setLevel(logging.INFO)
            file_handler_formatter = logging.Formatter('%(asctime)s - %(message)s',
                                                       '%d.%m %H:%M')
            file_handler.setFormatter(file_handler_formatter)
            logger.addHandler(file_handler)

        else:
            file_handler = logging.FileHandler(wdir.joinpath("logs").joinpath('market_tool.log'))
            file_handler.setLevel(logging.DEBUG)
            file_handler_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                                       '%d.%m.%Y %H:%M')
            file_handler.setFormatter(file_handler_formatter)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler_formatter = logging.Formatter('%(levelname)s - %(message)s')
            console_handler.setFormatter(console_handler_formatter)
        
            # add the handlers to the logger
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)

    return logger

class MarketTool():
    """ Main Class"""
    def __init__(self, options_file=None, webapp=False):
        self.wdir = Path.cwd()
        self.logger = _logging_setup(self.wdir, webapp)

        self.logger.info("Market Tool Initialized")

        tools.create_folder_structure(self.wdir, self.logger)
        self.initialize_options(options_file)

        self.data = DataManagement(self.options)
        self.grid = GridModel(self.wdir)

        ## Core Attributes
        self.cbco_module = None
        self.grid_representation = None
        self.market_model = None
        self.bokeh_plot = None

    def initialize_options(self, options_file):
        """ init options file """
        try:
            with open(self.wdir.joinpath(options_file)) as ofile:
                self.options = json.load(ofile)
                opt_str = "Optimization Options:" + \
                           json.dumps(self.options, indent=2) + "\n"
            self.logger.info(opt_str)

        except FileNotFoundError:
            self.logger.warning("No or invalid options file provided, using default options")
            self.options = tools.default_options()
            opt_str = "Optimization Options:" + json.dumps(self.options, indent=2) + "\n"
            self.logger.info(opt_str)
        except BaseException as unknown_exception:
            self.logger.exception("Error: %s", unknown_exception)

    def load_data(self, filename):
        """init Data Model with loading the fata from file"""
        self.data.load_data(self.wdir, filename)

        if self.grid.is_empty:
            self.grid.build_grid_model(self.data.nodes, self.data.lines)

    def init_market_model(self):
        """init market model"""
        if self.grid.is_empty:
            self.grid.build_grid_model(self.data.nodes, self.data.lines)

        if not self.grid_representation:
            self.create_grid_representation()

        if not self.market_model:
            self.market_model = MarketModel(self.wdir, self.options)
            self.market_model.update_data(self.data, self.options, self.grid_representation)
    
    def update_market_model_data(self):
        if not self.market_model:
            self.init_market_model()
        else:
            self.market_model.update_data(self.data, self.options, self.grid_representation)

    def run_market_model(self):
        """ Run the model """

        if not self.market_model:
            self.init_market_model()

        self.market_model.run()

        if self.data.results:
            self.logger.info("Adding Grid Model to Results Processing!")
            self.data.results.grid = self.grid

    def clear_data(self):
        """ Reset DataManagement Class"""
        self.logger.info("Resetting Data Object")
        self.data = DataManagement()

    def plot_grid_object(self, name="plotmodel"):
        """Create and run the Bokeh Plot"""
        self.init_bokeh_plot(name)
        self.bokeh_plot.start_server()
        # self.bokeh_plot.stop_server()

    def create_grid_representation(self):
        """Grid Representation as property"""
        if self.grid.is_empty:
            self.grid.build_grid_model(self.data.nodes, self.data.lines)

        self.cbco_module = CBCOModule(self.wdir, self.grid, self.data, self.options)
        self.cbco_module.create_grid_representation()
        self.grid_representation = self.cbco_module.grid_representation

    def init_bokeh_plot(self, name="default"):
        """init boke plot (saves market result and grid object)"""
        self.bokeh_plot = bokeh.BokehPlot(self.wdir)
        if not self.data.results:
            self.logger.info("No result available form market model!")
        else:
            folder = self.data.result_attributes["source"]
            self.logger.info("initializing bokeh plot with from folder: %s", str(folder))
            self.bokeh_plot.add_market_result(self.data.results, name)