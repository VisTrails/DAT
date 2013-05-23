""" Data provenance representation and (de)serialization logic

Data provenance of a piece of data (i.e. a variable) is a directed acyclic
graph. It is stored as annotations on each variable's pipeline version (the
versions tagged as 'dat-var-...') using references to other variables when
appropriate.

This means that each variable doesn't have its full provenance; creating the
full graph requires following the references to other variables.

Locally (on each variable), provenance is a tree. It can have multiple level
because of intermediate results that are not materialized, for example:
  C = (A + 2) * B

  var A   constant 2    ..   ..
       \ /               \   /
        +                var B
         \                /
  intermediate result   /
                    \ /
                     *
                     |
                   var C
In this example, provenance for variables A and B won't be stored in variable
C's provenance, there will only be pointers to these variables. However, an
intermediate result exists, which turns variable C's provenance into a tree.

The provenance for each particular variable is encoded in JSON, using different
object types (which are simple beans) to represent the different operations:
  * Loader, when a variable was created by a loader. In this case, the loader
    can store additional information on how the data was created, but at the
    minimum the name of the loader will be captured.
  * Constant, for a constant value used in an operation (typed in an
    expression).
  * Variable, a reference to another variable. Stores the version id. Because
    VisTrails doesn't really delete anything, when a variable is removed its
    pipeline is still accessible, along with its annotations (with the
    exception of the tag).
  * Operation, indicating a VariableOperation was performed from other pieces
    of data.

Example of serialized tree (different from previous, formatted):
{
  'type': 'Operation',
  'pkg_id': 'some.pkg.identifier',
  'name': 'some_op',
  'args': {
    'one': {
      'type': Constant,
      'constant': 42
    },
    'two': {
      'type': 'Loader',
      'pkg_id': 'some.pkg.identifier',
      'name': 'NumPy loader',
      'other_args': 'maybe'
    },
    'three': {
      'type': 'Variable',
      'version': 5
    }
  }
}

"""


from itertools import izip
import json

class _DataProvenanceNode(object):
    def __init__(self, **data):
        self.data_dict = data

    def __getitem__(self, key):
        return self.data_dict[key]

    def __repr__(self):
        it = self.data_dict.iteritems()
        return '%s(%s)' % (
                self.__class__.__name__,
                ', '.join('%s=%r' % (k, v) for k, v in it))


###############################################################################
# Provenance tree nodes
#

class Loader(_DataProvenanceNode):
    def __init__(self, **kwargs):
        try:
            _DataProvenanceNode.__init__(self, **kwargs['_json'])
        except KeyError:
            loader = kwargs.pop('loader')
            _DataProvenanceNode.__init__(
                    self,
                    pkg_id=loader.package_identifier,
                    name=loader.name,
                    **kwargs)


class Constant(_DataProvenanceNode):
    def __init__(self, **kwargs):
        try:
            _DataProvenanceNode.__init__(self, **kwargs['_json'])
        except KeyError:
            constant = kwargs.pop('constant')
            _DataProvenanceNode.__init__(
                    self,
                    constant=constant,
                    **kwargs)


class Variable(_DataProvenanceNode):
    def __init__(self, **kwargs):
        try:
            _DataProvenanceNode.__init__(self, **kwargs['_json'])
        except KeyError:
            variable = kwargs.pop('variable')
            version = variable._controller.vistrail.get_version_number(
                    'dat-var-%s' % variable.name)
            _DataProvenanceNode.__init__(
                    self,
                    version=version,
                    **kwargs)


class Operation(_DataProvenanceNode):
    def __init__(self, **kwargs):
        try:
            _DataProvenanceNode.__init__(self, **kwargs['_json'])
        except KeyError:
            operation = kwargs.pop('operation')
            arg_list = kwargs.pop('arg_list')
            args = {}
            if operation.usable_in_command:
                for variable, decl_arg in izip(arg_list, operation.parameters):
                    if variable._materialized is None:
                        # Intermediate result: write its provenance
                        args[decl_arg.name] = variable.provenance
                    else:
                        # Materialized variable: reference it instead
                        args[decl_arg.name] = Variable(
                                variable=variable._materialized)
            _DataProvenanceNode.__init__(
                    self,
                    pkg_id=operation.package_identifier,
                    name=operation.name,
                    args=args)


###############################################################################
# Annotation to tree
#

_json_classes = {
    'loader': Loader,
    'constant': Constant,
    'variable': Variable,
    'operation': Operation}

def _json_object_hook(dct):
    try:
        t = dct['type']
    except KeyError:
        return dct
    else:
        return _json_classes[t](_json={k: v
                                       for k, v in dct.iteritems()
                                       if k != 'type'})

def read_from_annotation(annotation):
    """Deserializes a data provenance tree from an annotation string.
    """
    return json.loads(annotation, object_hook=_json_object_hook)


###############################################################################
# Provenance tree to annotation
#

_reverse_json_classes = {v: k for k, v in _json_classes.iteritems()}

class ProvenanceEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, _DataProvenanceNode):
            dct = dict(type=_reverse_json_classes[type(obj)])
            dct.update(obj.data_dict)
            return dct
        return super(ProvenanceEncoder, self).default(obj)

def save_to_annotation(provenance):
    """Serializes a data provenance tree as an annotation string.
    """
    return json.dumps(provenance, cls=ProvenanceEncoder)
