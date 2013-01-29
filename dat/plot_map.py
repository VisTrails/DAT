import warnings

from dat import DATRecipe, PipelineInformation
from dat.manager import Manager

from vistrails.core.application import get_vistrails_application


class PlotMap(object):
    """Maintains the correspondence DAT recipes and pipelines.

    This maps a DAT recipe, ie a Plot and its parameters, to a given pipeline
    version. It allows to keep track of this metadata even if spreadsheet cells
    get moved or copied, or if a pipeline gets reexecuted later.
    """
    # Annotation format is:
    #   <annotation
    #           key="dat-recipe-PIPELINEVERSION"
    #           value="PlotName;param1=varname1;param3=varname2" />
    # replacing:
    #   * PIPELINEVERSION with the version number
    #   * PlotName with the 'name' field of the plot
    #   * paramN with the name of an input port of the plot
    #   * varname with the current name of a variable
    #
    # This assumes that:
    #   * Plot names don't change (and are not localized)
    #   * Plot, port and variable names don't contain ';' or '='
    #
    # Parameters which are not set are simply omitted from the list
    _ANNOTATION_KEY = 'dat-recipe-'

    @staticmethod
    def _build_annotation_key(pipeline):
        return "%s%s" % (PlotMap._ANNOTATION_KEY, pipeline.version)

    @staticmethod
    def _read_annotation_key(key):
        try:
            if key.startswith(PlotMap._ANNOTATION_KEY):
                return PipelineInformation(
                        int(key[len(PlotMap._ANNOTATION_KEY):]))
        except ValueError:
            pass
        return None

    @staticmethod
    def _build_annotation_value(recipe):
        value = recipe.plot.name
        for param, variable in recipe.variables.iteritems():
            value += ";%s=%s" % (param, variable.name)
        return value

    @staticmethod
    def _read_annotation_value(value):
        value = value.split(';')
        plot = Manager().get_plot(value[0])
        variables = dict()
        for assignment in value[1:]:
            param, varname = assignment.split('=')
            variables[param] = Manager().get_variable(varname)
        return DATRecipe(plot, variables)

    def __init__(self):
        self._pipeline_to_recipe = dict() # PipelineInformation -> DATRecipe
        self._recipe_to_pipeline = dict() # DATRecipe -> PipelineInformation

    def init(self):
        get_vistrails_application().register_notification(
                'dat_removed_variable', self._variable_removed)

        self.load_from_vistrail()

    def load_from_vistrail(self):
        controller = get_vistrails_application().dat_controller
        annotations = controller.vistrail.annotations
        for an in annotations:
            pipeline = self._read_annotation_key(an.key)
            if pipeline is not None:
                recipe = self._read_annotation_value(an.value)
                self._pipeline_to_recipe[pipeline] = recipe
                self._recipe_to_pipeline[recipe] = pipeline

    def created_pipeline(self, recipe, pipeline):
        """Registers a new pipeline as being the result of a DAT recipe.

        We now know that this pipeline was created from this plot and
        parameters, so we will display an overlay showing these on every cell
        created from that pipeline.
        """
        try:
            p = self._recipe_to_pipeline[recipe]
            if p != pipeline:
                def print_loc(l):
                    if hasattr(l, 'name') and l.name:
                        return l.name
                    else:
                        return str(l)
                warnings.warn(
                        "A new pipeline with a known recipe was created\n"
                        "Pipelines:\n"
                        "    %s version=%s\n"
                        "    %s version=%s" % (
                        print_loc(p.locator), p.version,
                        print_loc(pipeline.locator), pipeline.version))
        except KeyError:
            pass
        self._pipeline_to_recipe[pipeline] = recipe
        self._recipe_to_pipeline[recipe] = pipeline

        # Add the annotation in the vistrail
        controller = get_vistrails_application().dat_controller
        controller.vistrail.set_annotation(
                self._build_annotation_key(pipeline),
                self._build_annotation_value(recipe))

    def get_recipe(self, pipeline):
        return self._pipeline_to_recipe.get(pipeline, None)

    def get_pipeline(self, recipe):
        return self._recipe_to_pipeline.get(recipe, None)

    def _variable_removed(self, varname, renamed_to=None):
        if renamed_to is None:
            # A variable was removed!
            # We'll remove all the mappings that used it
            controller = get_vistrails_application().dat_controller
            to_remove = []
            for recipe in self._recipe_to_pipeline.iterkeys():
                if any(
                        variable.name == varname
                        for variable in recipe.variables.itervalues()):
                    to_remove.append(recipe)
            if to_remove:
                warnings.warn(
                        "Variable %r was used in %d pipelines!" % (
                                varname, len(to_remove)))
            for recipe in to_remove:
                pipeline = self._recipe_to_pipeline.pop(recipe)
                del self._pipeline_to_recipe[pipeline]

                # Remove the annotation from the current vistrail
                controller.vistrail.set_annotation(
                        'dat-recipe-%s' % pipeline.version,
                        self._build_annotation_value(recipe))

    def __call__(self):
        return self

PlotMap = PlotMap()
