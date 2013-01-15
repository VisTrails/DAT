import warnings


class DATRecipe(object):
    """Just a simple class holding a Plot its parameters.
    """
    def __init__(self, plot, variables):
        """__init__(plot: Plot, variables: dict of Variables)
        """
        self.plot = plot
        self.variables = dict(variables)
        self._hash = hash((
                self.plot,
                tuple((k, v.name) for k, v in self.variables.iteritems())))

    def __eq__(self, other):
        if not isinstance(other, DATRecipe):
            raise TypeError
        return (self.plot, self.variables) == (other.plot, other.variables)

    def __hash__(self):
        return self._hash


class PipelineInformation(object):
    """A simple class holding enough information on a pipeline to locate it.
    """
    def __init__(self, version):
        self.version = version

    def __eq__(self, other):
        return self.version == other.version

    def __hash__(self):
        return hash(self.version)


class PlotMap(object):
    """Maintains the correspondence DAT recipes and pipelines.

    This maps a DAT recipe, ie a Plot and its parameters, to a given pipeline
    version. It allows to keep track of this metadata even if spreadsheet cells
    get moved or copied, or if a pipeline gets reexecuted later.
    """
    # TODO-dat : this should be serialized and saved in the VT file, as there is no
    # easy way to find out if a pipeline was created by DAT and how
    def __init__(self):
        self._pipeline_to_recipe = dict()
        self._recipe_to_pipeline = dict()

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

    def __call__(self):
        return self

PlotMap = PlotMap()
