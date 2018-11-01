import io

from .types import (GoBool, GoInt, GoUint, GoFloat, GoStruct, GoByteSlice,
                    GoString, GoComplex)


class Dumper:
    def __init__(self):
        self.types = {
            bool: GoBool,
            int: GoInt,
            float: GoFloat,
            bytes: GoByteSlice,
            str: GoString,
            complex: GoComplex,
        }
        self.dumped_types = {}

    def dump(self, value):
        return self._dump(value)

    def _dump(self, value):
        # Top-level singletons are sent with an extra zero byte which
        # serves as a kind of field delta.
        python_type = type(value)
        go_type = getattr(value, 'go_type', None) or self.types.get(python_type)
        if go_type is None:
            raise NotImplementedError("cannot encode %s of type %s" %
                                      (value, python_type))

        # Dump compound type's type if needed.
        typeid = go_type.typeid
        typeseg = b''
        if typeid > 23 and go_type not in self.dumped_types:
            go_typetype = go_type.go_type
            typeseg = self._dump_value(-typeid, go_typetype, go_type)
            # Can the gotypetype have a gotypetypetype to dump?
            # The value can contain a go_type!
            self.dumped_types[go_type] = typeid

        return typeseg + self._dump_value(typeid, go_type, value)

    def _dump_value(self, typeid, go_type, value):
        segment = io.BytesIO()
        segment.write(GoInt.encode(typeid))
        if not isinstance(go_type, GoStruct):
            segment.write(b'\x00')
        segment.write(go_type.encode(value))
        return GoUint.encode(segment.tell()) + segment.getvalue()

