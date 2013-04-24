import itertools
import urllib2
import uuid
import warnings
import weakref

from dat import RecipeParameterValue, DATRecipe, PipelineInformation
from dat import data_provenance
from dat.global_data import GlobalManager
from dat.vistrails_interface import Variable, get_pipeline_location

from vistrails.core.application import get_vistrails_application
from vistrails.core.vistrail.vistrailvariable import VistrailVariable
from vistrails.core.system import vistrails_default_file_type
from vistrails.packages.spreadsheet.spreadsheet_cell import CellInformation
from vistrails.packages.spreadsheet.spreadsheet_controller import \
    spreadsheetController
from vistrails.packages.spreadsheet.spreadsheet_tab import \
    StandardWidgetSheetTab


class VistrailData(object):
    """Keeps a list of DAT objects that are local to a vistrail file.

    This object allows components throughout the application to access the
    variables for a given vistrail, and emits notifications when the list of
    variable changes.

    It also keeps a mapping between pipeline versions and DATRecipe and writes
    it in the vistrail as annotations.

    An object of this class gets created for each currently opened vistrail
    file.
    """

    # Annotation format is:
    #   <actionAnnotation
    #           actionId="PIPELINEVERSION"
    #           key="dat-recipe"
    #           value="<recipe>" />
    #   <actionAnnotation
    #           actionId="PIPELINEVERSION"
    #           key="dat-ports"
    #           value="<portmap>" />
    #
    # Where <recipe> has the format (with added whitespace for clarity):
    #   plot_package,PlotName;
    #       param1=v=
    #           varname1:CONN1,CONN2|
    #           varname2,cast_op:CONN3;
    #       param2=c=value2
    #
    # And <portmap>:
    #   param1=
    #       ID1,PORT1:ID2,PORT2|
    #       ID3,PORT3;
    #   param2=ID4,PORT4
    #
    # replacing:
    #   * PIPELINEVERSION with the version number
    #   * PlotName with the 'name' field of the plot
    #   * param<N> with the name of an input port of the plot
    #   * varname with the name of a variable
    #   * ID<P> and PORT<P> with the module id and port name of the plot's
    #     input port for the associated parameter
    #   * CONN<M> with the id of a connection tying the plot input port to one
    #     of the parameters set to this port
    #   * value<N> is the string representation of a constant
    #   * cast_op is the name of the variable operation used for typecasting
    #
    # Parameters which are not set are simply omitted from the list
    _RECIPE_KEY = 'dat-recipe'
    _PORTMAP_KEY = 'dat-ports'
    _DATA_PROVENANCE_KEY = 'dat-data-provenance'

    @staticmethod
    def _build_recipe_annotation(recipe, conn_map):
        """Builds the recipe annotation value from the recipe and conn_map.
        """
        value = '%s,%s' % (recipe.plot.package_identifier, recipe.plot.name)
        for param, param_values in sorted(recipe.parameters.iteritems(),
                                          key=lambda (k, v): k):
            if not param_values:
                continue
            value += ';%s=' % param
            if param_values[0].type == RecipeParameterValue.CONSTANT:
                if len(param_values) != 1:
                    raise ValueError
                value += 'c='
            else: # param_values[0].type == RecipeParameterValue.VARIABLE:
                value += 'v='

            for i, param_val, conn_list in itertools.izip(
                    itertools.count(), param_values, conn_map[param]):
                if i != 0:
                    value += '|'
                if param_val.type == RecipeParameterValue.CONSTANT:
                    value += urllib2.quote(param_val.constant, safe='')
                else: # param_val.type == RecipeParameterValue.VARIABLE
                    value += param_val.variable.name
                    if param_val.typecast is not None:
                        value += ',%s' % param_val.typecast
                value += ':' + ','.join(
                        '%d' % conn_id
                        for conn_id in conn_list)
        return value

    @staticmethod
    def _read_recipe_annotation(vistraildata, value):
        """Reads (recipe, conn_map) from an annotation value.
        """
        def read_connlist(connlist):
            return tuple(int(conn_id) for conn_id in connlist.split(','))

        value = iter(value.split(';'))
        try:
            plot = next(value)
            plot = plot.split(',')
            if len(plot) != 2:
                raise ValueError
            plot = GlobalManager.get_plot(*plot) # Might raise KeyError
            parameters = dict()
            conn_map = dict()
            for param in value:
                param, t, pvals = param.split('=') # Might raise ValueError
                    # or TypeError
                pvals = pvals.split('|')
                plist = []
                cplist = []
                if t not in ('c', 'v'):
                    raise ValueError
                for val in pvals:
                    val = val.split(':')
                    if len(val) != 2:
                        raise ValueError
                    if t == 'c':
                        plist.append(RecipeParameterValue(
                                constant=urllib2.unquote(val[0])))
                    else: # t == 'v':
                        v = val[0].split(',')
                        if len(v) not in (1, 2):
                            raise ValueError
                        variable = vistraildata.get_variable(v[0])
                        if len(v) == 2:
                            plist.append(RecipeParameterValue(
                                    variable=variable,
                                    typecast=v[1]))
                        else:
                            plist.append(RecipeParameterValue(
                                    variable=variable))
                    cplist.append(read_connlist(val[1]))
                parameters[param] = tuple(plist)
                conn_map[param] = tuple(cplist)
            return DATRecipe(plot, parameters), conn_map
        except (KeyError, ValueError, TypeError):
            return None, None

    @staticmethod
    def _build_portmap_annotation(port_map):
        """Builds the port_map annotation value.
        """
        value = []

        for param, port_list in sorted(port_map.iteritems(),
                                       key=lambda (k, v): k):
            if not port_list:
                continue

            value.append('%s=' % param + ':'.join(
                    '%d,%s' % (mod_id, portname)
                    for mod_id, portname in port_list))

        return ';'.join(value)

    @staticmethod
    def _read_portmap_annotation(value):
        """Reads port_map from an annotation value.
        """
        try:
            port_map = dict()
            value = value.split(';')
            for mapping in value:
                param, ports = mapping.split('=')
                if not ports:
                    port_map[param] = []
                    continue
                ports = ports.split(':')
                portlist = []
                for port in ports:
                    port = port.split(',')
                    mod_id, port_name = port
                    portlist.append((int(mod_id), port_name))
                port_map[param] = portlist
            return port_map
        except (ValueError, TypeError):
            return None

    def __init__(self, controller):
        """Initial setup of the VistrailData.

        Discovers plots and variable loaders from packages and registers
        notifications for packages loaded in the future.
        """
        self._controller = controller
        self._spreadsheet_tabs = None # id: int -> spreadsheet_tab

        self._variables = dict()
        self._data_provenance = dict() # version: int -> provenance

        self._cell_to_version = dict() # CellInformation -> int
        self._version_to_pipeline = dict() # int -> PipelineInformation
        self._cell_to_pipeline = dict() # CellInformation-> PipelineInformation

        self._failed_infer_calls = set() # [version: int]

        app = get_vistrails_application()

        # dat_new_variable(varname: str)
        app.create_notification('dat_new_variable')
        # dat_removed_variable(varname: str)
        app.create_notification('dat_removed_variable')

        annotations = self._controller.vistrail.action_annotations

        # Load variables from tagged versions
        if self._controller.vistrail.has_tag_str('dat-vars'):
            # Load all data provenance annotations
            # Loading from known variables is not enough, we also need deleted
            # variables to form the complete graph
            for an in annotations:
                if an.key == self._DATA_PROVENANCE_KEY:
                    version = an.action_id
                    provenance = data_provenance.read_from_annotation(an.value)
                    self._data_provenance[version] = provenance

            tagmap = self._controller.vistrail.get_tagMap()
            for version, tag in tagmap.iteritems():
                if tag.startswith('dat-var-'):
                    varname = tag[8:]

                    # Get the type from the OutputPort module's spec input port
                    type = Variable.read_type(
                            self._controller.vistrail.getPipeline(version))
                    if type is None:
                        warnings.warn("Found invalid DAT variable pipeline "
                                      "%r, ignored" % tag)
                        continue
                    # Get the data provenance
                    provenance = self._data_provenance.get(version)

                    variable = Variable.VariableInformation(
                            varname, self._controller, type, provenance)

                    self._variables[varname] = variable
                    self._add_variable(varname)

        # Load mappings from annotations
        # First, read the recipes
        for an in annotations:
            if an.key == self._RECIPE_KEY:
                version = an.action_id
                recipe, conn_map = self._read_recipe_annotation(self, an.value)
                if recipe is not None:
                    pipeline = PipelineInformation(
                            version, recipe, conn_map,
                            None) # to be filled by the next block
                    self._version_to_pipeline[version] = pipeline
        # Then, read the port maps
        for an in annotations:
            if an.key == self._PORTMAP_KEY:
                pipeline = self._version_to_pipeline[an.action_id]
                if not pipeline:
                    # Purge the lone port map
                    warnings.warn("Found a DAT port map annotation with no "
                                  "associated recipe -- removing")
                    self._controller.vistrail.set_action_annotation(
                            an.action_id,
                            an.key,
                            None)
                else:
                    port_map = self._read_portmap_annotation(an.value)
                    if port_map is not None:
                        pipeline.port_map = port_map

    def _get_controller(self):
        return self._controller
    controller = property(_get_controller)

    def _get_sheet_id(self):
        get_variable = self.controller.get_vistrail_variable
        for i in itertools.count(1):
            if get_variable('dat-sheet-%d' % i) is None:
                return i

    def get_sheetname(self, sheet_id):
        changed = self.controller.changed
        try:
            var = self.controller.get_vistrail_variable(
                    'dat-sheet-%d' % sheet_id)
            if var is not None:
                name = var.value
                ctrl_name, sheet = name.split(' / ', 1)
                if ctrl_name != self.name:
                    name = u'%s / %s' % (self.name, sheet)
                    self.controller.set_vistrail_variable(
                            var.name,
                            VistrailVariable(
                                    var.name,
                                    var.uuid,
                                    var.package,
                                    var.module,
                                    var.namespace,
                                    name))
                return name
            else:
                names = set(v.value.split(' / ', 1)[1]
                            for v in self.controller.get_vistrail_variables()
                            if v.name.startswith('dat-sheet-'))
                for i in itertools.count(1):
                    name = u'Sheet %d' % i
                    if name not in names:
                        name = u'%s / %s' % (self.name, name)
                        self.controller.set_vistrail_variable(
                                'dat-sheet-%d' % sheet_id,
                                VistrailVariable(
                                        'dat-sheet-%d' % sheet_id,
                                        uuid.uuid1(),
                                        'edu.utah.sci.vistrails.basic',
                                        'String',
                                        '',
                                        name))
                        return name
        finally:
            # If the only change in the controller is the vistrail variable we
            # just created automatically, we can consider it unchanged
            if not changed:
                self.controller.set_changed(False)

    def new_tab(self, add, tab_controller, sheet_id=None):
        tab = StandardWidgetSheetTab(tab_controller)
        if sheet_id is None:
            sheet_id = self._get_sheet_id()
        if add:
            tab_controller.addTabWidget(tab, self.get_sheetname(sheet_id))
        self._spreadsheet_tabs[sheet_id] = tab
        self._spreadsheet_tabs_rev[tab] = sheet_id
        VistrailManager._tabs[tab] = (self, sheet_id)
        return tab, sheet_id

    def _get_spreadsheet_tabs(self):
        if self._spreadsheet_tabs is not None:
            return self._spreadsheet_tabs

        sh_window = spreadsheetController.findSpreadsheetWindow(create=False)
        if sh_window is None:
            return None
        tab_controller = sh_window.tabController

        # Get the cell location from the pipeline to fill in _cell_to_version
        # and _cell_to_pipeline
        cells = dict()
        sheet_sizes = dict()
        for pipeline in self._version_to_pipeline.itervalues():
            try:
                row, col, sheetname_var = get_pipeline_location(
                        self._controller,
                        pipeline)
                if sheetname_var.name.startswith('dat-sheet-'):
                    sheet_id = int(sheetname_var.name[10:])
                else:
                    raise ValueError
            except ValueError:
                continue
            try:
                p = cells[(row, col, sheet_id)]
            except KeyError:
                cells[(row, col, sheet_id)] = pipeline
                rowCount, colCount = sheet_sizes.get(sheet_id, (2, 2))
                rowCount = max(rowCount, row + 1)
                colCount = max(colCount, col + 1)
                sheet_sizes[sheet_id] = (rowCount, colCount)
            else:
                if pipeline.version > p.version:
                    # Select the latest version for a given cell
                    cells[(row, col, sheet_id)] = pipeline
        self._spreadsheet_tabs = dict()
        self._spreadsheet_tabs_rev = dict()
        for (row, col, sheet_id), pipeline in cells.iteritems():
            try:
                spreadsheet_tab = self._spreadsheet_tabs[sheet_id]
            except KeyError:
                rowCount, colCount = sheet_sizes.get(sheet_id, (2, 2))
                spreadsheet_tab = self.new_tab(
                        True,
                        tab_controller,
                        sheet_id)[0]
            cellInfo = CellInformation(spreadsheet_tab, row, col)
            self._cell_to_pipeline[cellInfo] = pipeline
            self._cell_to_version[cellInfo] = pipeline.version

        if not self._spreadsheet_tabs:
            self.new_tab(True, tab_controller)

        return self._spreadsheet_tabs
    spreadsheet_tabs = property(_get_spreadsheet_tabs)

    def sheetname_var(self, tab):
        sheet_id = self._spreadsheet_tabs_rev[tab]
        return self.controller.get_vistrail_variable(
                'dat-sheet-%d' % sheet_id)

    def update_spreadsheet_tabs(self):
        """Updates the title of the spreadsheet tab.

        Called when a controller changes name.
        """
        tabs = self.spreadsheet_tabs
        if tabs is not None:
            for sheet_id, tab in tabs.iteritems():
                tabWidget = tab.tabWidget
                name = self.get_sheetname(sheet_id)
                if name != unicode(tab.windowTitle()):
                    tab.setWindowTitle(name)
                    tabWidget.setTabText(tabWidget.indexOf(tab), name)

    def new_variable(self, varname, variable):
        """Register a new Variable with DAT.

        This will materialize it in the pipeline and signal its creation.
        """
        if varname in self._variables:
            raise ValueError("A variable named %s already exists!")

        # Materialize the Variable in the Vistrail
        variable = variable.materialize(varname)

        # Record the data provenance in an annotation
        version = self.controller.vistrail.get_version_number(
                'dat-var-%s' % varname)
        self.controller.vistrail.set_action_annotation(
                version,
                self._DATA_PROVENANCE_KEY,
                data_provenance.save_to_annotation(variable.provenance))

        # Add a record in our map of provenance data
        self._data_provenance[version] = variable.provenance

        self._variables[varname] = variable

        self._add_variable(varname)

    def _add_variable(self, varname, renamed_from=None):
        if renamed_from is not None:
            # Variable was renamed -- reflect this change on the annotations
            for pipeline in self._version_to_pipeline.itervalues():
                if any(
                        p.type == RecipeParameterValue.VARIABLE and
                        p.variable.name == varname
                        for p_values in pipeline.recipe.parameters.itervalues()
                        for p in p_values):
                    self._controller.vistrail.set_action_annotation(
                            pipeline.version,
                            self._RECIPE_KEY,
                            self._build_recipe_annotation(
                                    pipeline.recipe,
                                    pipeline.conn_map))

        get_vistrails_application().send_notification(
                'dat_new_variable',
                self._controller,
                varname,
                renamed_from=renamed_from)

    def _remove_variable(self, varname, renamed_to=None):
        get_vistrails_application().send_notification(
                'dat_removed_variable',
                self._controller,
                varname,
                renamed_to=renamed_to)

        if renamed_to is None:
            # A variable was removed!
            # We'll remove all the mappings that used it
            to_remove = set([])
            for pipeline in self._version_to_pipeline.itervalues():
                if any(
                        p.type == RecipeParameterValue.VARIABLE and
                        p.variable.name == varname
                        for p_values in pipeline.recipe.parameters.itervalues()
                        for p in p_values):
                    to_remove.add(pipeline.version)
            if to_remove:
                warnings.warn(
                        "Variable %r was used in %d pipelines!" % (
                                varname, len(to_remove)))
            for version in to_remove:
                del self._version_to_pipeline[version]

                # Remove the annotations from the vistrail
                for key in (
                        self._RECIPE_KEY, self._PORTMAP_KEY):
                    self._controller.vistrail.set_action_annotation(
                            version,
                            key,
                            None)

            cell_to_remove = []
            for cellInfo, version in self._cell_to_version.iteritems():
                if version in to_remove:
                    cell_to_remove.append(cellInfo)
            for cellInfo in cell_to_remove:
                del self._cell_to_version[cellInfo]
                del self._cell_to_pipeline[cellInfo]

    def remove_variable(self, varname):
        """Remove a Variable from DAT.

        This will remove the associated version in the vistrail and signal its
        destruction.
        """
        self._remove_variable(varname)

        variable = self._variables.pop(varname)
        variable.remove()

    def rename_variable(self, old_varname, new_varname):
        """Rename a Variable.

        This will update the tag on the associated version.

        Observers will get notified that a Variable was deleted and another
        added.
        """
        self._remove_variable(old_varname, renamed_to=new_varname)

        variable = self._variables.pop(old_varname)
        self._variables[new_varname] = variable
        variable.rename(new_varname)

        self._add_variable(new_varname, renamed_from=old_varname)

    def get_variable(self, varname):
        if not isinstance(varname, str):
            raise ValueError
        return self._variables.get(varname)

    def _get_variables(self):
        return self._variables.iterkeys()
    variables = property(_get_variables)

    def variable_provenance(self, version):
        """Gets the provenance for a variable pipeline.

        This is similar to get_variable(...).provenance except that it also
        works for variables that have been deleted (VisTrails keeps every
        version, along with their annotations excepts for tags).
        """
        return self._data_provenance.get(version)

    def created_pipeline(self, cellInfo, pipeline):
        """Registers a new pipeline as being the result of a DAT recipe.

        We now know that this pipeline was created in the given cell from this
        plot and these parameters.

        The version will get annotated with the DAT metadata, allowing it to be
        updated later.
        """
        try:
            p = self._version_to_pipeline[pipeline.version]
            if p == pipeline:
                return # Ok I guess
            warnings.warn(
                    "A new pipeline was created with a previously known "
                    "version!\n"
                    "  version=%r\n"
                    "  old recipe=%r\n"
                    "  new recipe=%r\n"
                    "replacing..." % (
                    pipeline.version,
                    p.recipe,
                    pipeline.recipe))
        except KeyError:
            pass
        self._cell_to_version[cellInfo] = pipeline.version
        self._version_to_pipeline[pipeline.version] = pipeline
        self._cell_to_pipeline[cellInfo] = pipeline

        # Add the annotation in the vistrail
        self._controller.vistrail.set_action_annotation(
                pipeline.version,
                self._RECIPE_KEY,
                self._build_recipe_annotation(pipeline.recipe,
                                              pipeline.conn_map))

        self._controller.vistrail.set_action_annotation(
                pipeline.version,
                self._PORTMAP_KEY,
                self._build_portmap_annotation(pipeline.port_map))

    def _infer_pipelineinfo(self, version, cellInfo):
        """Try to make up a pipelineInfo for a version and store it.

        Returns the new pipelineInfo, or None if we failed.
        """
        # This ensures that we don't try to infer a DAT recipe from the same
        # pipeline over and over again
        if version in self._failed_infer_calls:
            return None
        def fail():
            self._failed_infer_calls.add(version)
            return None

        # Recursively obtains the parent version's pipelineInfo
        try:
            parentId = self._controller.vistrail.actionMap[version].prevId
        except KeyError:
            return fail()
        parentInfo = self.get_pipeline(parentId, infer_for_cell=cellInfo)
        if parentInfo is None:
            return fail()

        # Here we loop on modules/connections to check that the required things
        # from the old pipeline are still here

        pipeline = self._controller.vistrail.getPipeline(version)

        new_parameters = dict()
        new_conn_map = dict()

        # Check that the plot is still there by finding the plot ports
        for name, port_list in parentInfo.port_map.iteritems():
            for mod_id, portname in port_list:
                if not pipeline.modules.has_key(mod_id):
                    return fail()

        # Loop on parameters to check they are still there
        for name, parameter_list in parentInfo.recipe.parameters.iteritems():
            conn_list = parentInfo.conn_map[name]
            new_parameter_list = []
            new_conn_list = []
            for parameter, conns in itertools.izip(parameter_list, conn_list):
                if all(
                        pipeline.connections.has_key(conn_id)
                        for conn_id in conns):
                    new_parameter_list.append(parameter)
                    new_conn_list.append(conns)
            new_parameters[name] = new_parameter_list
            new_conn_map[name] = new_conn_list

        new_recipe = DATRecipe(parentInfo.recipe.plot, new_parameters)
        pipelineInfo = PipelineInformation(version, new_recipe,
                                           new_conn_map, parentInfo.port_map)
        self.created_pipeline(cellInfo, pipelineInfo)
        return pipelineInfo

    def get_pipeline(self, param, infer_for_cell=None):
        """Get the pipeline information for a given cell or version.

        Returns None if nothing is found.

        If infer_for_cell is set and the pipeline has no known recipe, but a
        parent version had one, we'll try to make up something sensible and
        store it. infer_for_cell should be the CellInformation of the cell
        where this pipeline was found.
        """
        if isinstance(param, (int, long)):
            pipelineInfo = self._version_to_pipeline.get(param, None)
            if pipelineInfo is not None or infer_for_cell is None:
                return pipelineInfo

            return self._infer_pipelineinfo(param, infer_for_cell)
        else:
            return self._cell_to_pipeline.get(param, None)

    def _get_all_pipelines(self):
        return self._version_to_pipeline.itervalues()
    all_pipelines = property(_get_all_pipelines)

    def _get_all_cells(self):
        return self._cell_to_pipeline.iteritems()
    all_cells = property(_get_all_cells)


class VistrailManager(object):
    """Keeps a list of VistrailData objects.

    This singleton keeps a VistrailData object for each currently opened
    vistrail.
    """
    def __init__(self):
        self._vistrails = dict() # Controller -> VistrailData
        self._tabs = dict() # SpreadsheetTab -> (VistrailData, sheet_id)
        self._names = dict() # name: unicode -> VistrailData
        self._current_controller = None
        self.initialized = False
        self._forgotten = weakref.WeakKeyDictionary()
                # WeakSet only appeared in Python 2.7

    def init(self):
        """Initialization function, called when the application is created.

        This is not done at module-import time to avoid complex import-order
        issues.
        """
        app = get_vistrails_application()
        app.register_notification(
                'controller_changed',
                self.set_controller)
        app.register_notification(
                'controller_closed',
                self.forget_controller)
        app.register_notification(
                'vistrail_saved',
                self.controller_name_changed)
        bw = get_vistrails_application().builderWindow
        self.set_controller(bw.get_current_controller())
        self.initialized = True

    def set_controller(self, controller):
        """Called through the notification mechanism.

        Changes the 'current' controller, building a VistrailData for it if
        necessary.
        """
        if controller == self._current_controller:
            # VisTrails sends 'controller_changed' a lot
            return
        if self._forgotten.get(controller, False):
            # Yes, 'controller_changed' can happen after 'controller_closed'
            # This is unfortunate
            return

        self._current_controller = controller
        try:
            self._vistrails[controller]
            new = False
        except KeyError:
            vistraildata = VistrailData(controller)
            name = self._make_ctrl_name(controller.name)
            vistraildata.name = name
            self._names[name] = vistraildata
            self._vistrails[controller] = vistraildata
            new = True

        get_vistrails_application().send_notification(
                'dat_controller_changed',
                controller,
                new=new)

    def __call__(self, controller=None):
        """Accesses a VistrailData for a specific controller.

        If the controller is not specified, assume the current one.
        """
        if controller is None:
            controller = self._current_controller
        if controller is None:
            return None
        try:
            return self._vistrails[controller]
        except KeyError:
            warnings.warn("Unknown controller requested from "
                          "VistrailManager:\n  %r" % controller)
            vistraildata = VistrailData(controller)
            self._vistrails[controller] = vistraildata
            return vistraildata

    def _make_ctrl_name(self, ctrl_name):
        if not ctrl_name:
            ctrl_name = u"Untitled{ext}".format(
                    ext=vistrails_default_file_type())

        name = ctrl_name
        i = 1
        while name in self._names:
            i += 1
            name = u'%s (%d)' % (name, i)
        return name

    def controller_name_changed(self):
        vistraildata = self()

        old_name = vistraildata.name
        del self._names[old_name]

        mangled_name = self._make_ctrl_name(self._current_controller.name)

        vistraildata.name = mangled_name
        self._names[mangled_name] = vistraildata

        vistraildata.update_spreadsheet_tabs()

    def from_spreadsheet_tab(self, tab):
        try:
            vistraildata, sheet_id = self._tabs[tab]
            return vistraildata
        except KeyError:
            return None

    def forget_controller(self, controller):
        """Removes the data for a specific controller.

        Called when a controller is closed.
        """
        try:
            vistraildata = self._vistrails[controller]
        except KeyError:
            return
        else:
            # Remove the spreadsheets
            tabs = vistraildata.spreadsheet_tabs
            for tab in tabs.itervalues():
                tab.tabWidget.deleteSheet(tab)
                del self._tabs[tab]

            del self._vistrails[controller]
            del self._names[vistraildata.name]

            self._forgotten[controller] = True

        if self._current_controller == controller:
            self._current_controller = None

    def hook_create_tab(self, tab_controller, default_name):
        vistraildata = self()
        if vistraildata is None:
            return None
        tab, sheet_id = vistraildata.new_tab(False, tab_controller)
        return tab, vistraildata.get_sheetname(sheet_id)

    def hook_close_tab(self, tab):
        try:
            vistraildata, sheet_id = self._tabs[tab]
        except KeyError:
            return True

        # Close the project if it was the last sheet
        if vistraildata._spreadsheet_tabs.keys() == [sheet_id]:
            get_vistrails_application().builderWindow.close_vistrail()
            return False
        else:
            del self._tabs[tab]
            # Remove the tab from the associated VistrailData
            del vistraildata._spreadsheet_tabs[sheet_id]
            del vistraildata._spreadsheet_tabs_rev[tab]
            return True

VistrailManager = VistrailManager()
