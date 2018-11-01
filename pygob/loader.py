from .types import (BOOL, INT, UINT, FLOAT, BYTE_SLICE, STRING, COMPLEX, INTERFACE,
                    WIRE_TYPE, ARRAY_TYPE, COMMON_TYPE, SLICE_TYPE,
                    STRUCT_TYPE, FIELD_TYPE, FIELD_TYPE_SLICE, MAP_TYPE)
from .types import (GoBool, GoUint, GoInt, GoFloat, GoByteSlice, GoString,
                    GoComplex, GoInterface, GoStruct, GoWireType, GoSlice)


class Loader:
    def __init__(self):
        # Compound types that depend on the basic types above.
        interface_type = GoInterface(self)
        common_type = GoStruct(COMMON_TYPE, 'CommonType', self, [
            ('Name', STRING),
            ('Id', INT),
        ])
        array_type = GoStruct(ARRAY_TYPE, 'ArrayType', self, [
            ('CommonType', COMMON_TYPE),
            ('Elem', INT),
            ('Len', INT),
        ])
        slice_type = GoStruct(SLICE_TYPE, 'SliceType', self, [
            ('CommonType', COMMON_TYPE),
            ('Elem', INT),
        ])
        struct_type = GoStruct(STRUCT_TYPE, 'StructType', self, [
            ('CommonType', COMMON_TYPE),
            ('Field', FIELD_TYPE_SLICE),
        ])
        field_type = GoStruct(FIELD_TYPE, 'FieldType', self, [
            ('Name', STRING),
            ('Id', INT),
        ])
        field_type_slice = GoSlice(FIELD_TYPE_SLICE, self, FIELD_TYPE)
        map_type = GoStruct(MAP_TYPE, 'MapType', self, [
            ('CommonType', COMMON_TYPE),
            ('Key', INT),
            ('Elem', INT),
        ])
        wire_type = GoWireType(WIRE_TYPE, 'WireType', self, [
            ('ArrayT', ARRAY_TYPE),
            ('SliceT', SLICE_TYPE),
            ('StructT', STRUCT_TYPE),
            ('MapT', MAP_TYPE),
        ])

        # We can now register basic and compound types.
        self.types = {
            INT: GoInt,
            UINT: GoUint,
            BOOL: GoBool,
            FLOAT: GoFloat,
            BYTE_SLICE: GoByteSlice,
            STRING: GoString,
            COMPLEX: GoComplex,
            INTERFACE: interface_type,
            WIRE_TYPE: wire_type,
            ARRAY_TYPE: array_type,
            COMMON_TYPE: common_type,
            SLICE_TYPE: slice_type,
            STRUCT_TYPE: struct_type,
            FIELD_TYPE: field_type,
            FIELD_TYPE_SLICE: field_type_slice,
            MAP_TYPE: map_type,
        }

    def load(self, buf):
        value, buf = self._load(buf)
        return value

    def load_all(self, buf):
        while buf:
            value, buf = self._load(buf)
            yield value
        assert buf == b'', 'trailing data in buffer: %s' % list(buf)

    def _read_segment(self, buf):
        length, buf = GoUint.decode(buf)
        return buf[:length], buf[length:]

    def _load(self, buf):
        while True:
            segment, buf = self._read_segment(buf)
            typeid, value = self._load_segment(segment)
            if typeid > 0:
                return value, buf
            else:  # Register the new type.
                self.types[-typeid] = value

    def _load_segment(self, segment):
        """Load from a segment.
        """
        typeid, segment = GoInt.decode(segment)
        if typeid > 0:  # Found a value.
            value, segment = self._load_value(typeid, segment)
        else:  # Found a type.
            value, segment = self._load_type(segment)
        assert segment == b'', ('trailing data in segment: %s' %
                        list(segment))
        return typeid, value

    def _load_value(self, typeid, segment):
        # Top-level singletons are sent with an extra zero byte which
        # serves as a kind of field delta.
        go_type = self.types.get(typeid)
        if go_type is not None and not isinstance(go_type, GoStruct):
            delta, segment = GoUint.decode(segment)
            assert delta == 0, 'illegal delta for singleton: %s' % delta
        value, segment = self.decode_value(typeid, segment)
        return value, segment

    def _load_type(self, segment):
        """Decode wire type."""
        return self.decode_value(WIRE_TYPE, segment)

    def decode_value(self, typeid, buf):
        go_type = self.types.get(typeid)
        if go_type is None:
            raise NotImplementedError("cannot decode %s" % typeid)
        return go_type.decode(buf)
