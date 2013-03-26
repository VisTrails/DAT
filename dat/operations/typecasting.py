from dat.global_data import GlobalManager


def get_typecast_operations(source_descriptor, expected_descriptor):
    """Finds the operations that can typecast from a module type to another.

    Returns the list of VariableOperation that:
      * have only one parameter
      * take the source_descriptor (or a superclass) as a parameter
      * return the expected_descriptor (or a subclass)

    Might return an empty list.
    """
    valid = []

    for operation in GlobalManager.variable_operations:
        if len(operation.parameters) != 1:
            continue

        if not any(issubclass(source_descriptor.module, desc.module)
                   for desc in operation.parameters[0].types):
            continue

        if not issubclass(operation.return_type.module,
                          expected_descriptor.module):
            continue

        valid.append(operation)

    return valid
