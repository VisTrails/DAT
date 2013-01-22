import warnings

import dat.manager


class PlotMap(object):
    """Maintains the correspondence DAT recipes and pipelines.

    This maps a DAT recipe, ie a Plot and its parameters, to a given pipeline
    version. It allows to keep track of this metadata even if spreadsheet cells
    get moved or copied, or if a pipeline gets reexecuted later.
    """
    # TODO-dat : this should be serialized and saved in the VT file, as there is no
    # easy way to find out if a pipeline was created by DAT and how
    def __init__(self):
        self._pipeline_to_recipe = dict() # PipelineInformation -> DATRecipe
        self._recipe_to_pipeline = dict() # DATRecipe -> PipelineInformation

        dat.manager.Manager().add_variable_observer(
                (None, self._variable_removed))

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

    def get_recipe(self, pipeline):
        return self._pipeline_to_recipe.get(pipeline, None)

    def get_pipeline(self, recipe):
        return self._recipe_to_pipeline.get(recipe, None)

    def _variable_removed(self, varname, renamed_to=None):
        if renamed_to is None:
            # A variable was removed!
            # We'll remove all the mappings that used it
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
                del self._pipeline_to_recipe[
                        self._recipe_to_pipeline.pop(recipe)]

    def __call__(self):
        return self

PlotMap = PlotMap()
