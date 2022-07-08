from enum import IntEnum
from collections import OrderedDict
import numpy as np


class TypeId(IntEnum):
    INT8 = 0x01
    STRING = 0x02
    ARRAY = 0x03
    INT32 = 0x05
    FLOAT = 0x9
    COMPLEX_FLOAT = 0xa
    DOUBLE = 0x0b
    COMPLEX_DOUBLE = 0x0c
    STRUCT = 0x10
    TUPLE = 0x12  # type listのconsの意味？


def typeid_to_dtype(tp):
    t = tp.to_npdtype()
    return t if isinstance(t, list) else  [t]


# def typeid_to_size(t):
#     if t == TypeId.INT8:
#         return 4
#     elif t == TypeId.INT32:
#         return 4
#     elif t == TypeId.FLOAT:
#         return 4
#     elif t == TypeId.COMPLEX_FLOAT:
#         return 8
#     elif t == TypeId.DOUBLE:
#         return 8
#     elif t == TypeId.COMPLEX_DOUBLE:
#         return 16
#     else:
#         raise ValueError('Cannot to be a element of array: Type ' + str(TypeId(t)))


class SectionId(IntEnum):
    HEADER = 0
    TYPE   = 1
    SWEEP  = 2
    TRACE  = 3
    VALUE  = 4
#    FOOTER = 0x0f


class ChunkId(IntEnum):
    MAJOR_SECTION = 0x15
    MINOR_SECTION = 0x16


class PropertyTypeId(IntEnum):
    STRING = 0x21
    INT    = 0x22
    DOUBLE = 0x23


class ElementId(IntEnum):
    DATA    = 0x10
    GROUP   = 0x11
    ZEROPAD = 0x14


class SectionInfo:
    def __init__(self, offset, size):
        self.offset = offset
        self.size = size

    def __repr__(self):
        return 'SectionInfo(offset: ' + repr(self.offset) + ', size: ' + repr(self.size) + ')'


class PSF_Property:
    def __init__(self):
        self.name = ''
        self.type = 0
        self.value = 0

    def __str__(self):
        return 'PSF_Property(name: ' + str(self.name) + ', value: ' + str(self.value) + ')'

    def __repr__(self):
        return 'PSF_Property(name: ' + str(self.name) + ', value: ' + str(self.value) + ')'

    def read(self, psffile):
        p_type = psffile.read_uint32()
        self.type = p_type

        if p_type == PropertyTypeId.STRING:
            self.name = psffile.read_str()
            self.value = psffile.read_str()
            return True
        elif p_type == PropertyTypeId.INT:
            self.name = psffile.read_str()
            self.value = psffile.read_int32()
            return True
        elif p_type == PropertyTypeId.DOUBLE:
            self.name = psffile.read_str()
            self.value = psffile.read_double()
            return True
        else:
            # raise ValueError('Unexpected Property type number: ' + str(p_type))
            psffile.unread(4)
            return False

    @staticmethod
    def read_dictionary(psffile):
        properties = dict()
        while True:
            p = PSF_Property()
            if p.read(psffile):
                properties[p.name] = p.value
            else:
                break

        return properties


class PSF_Type:
    def __init__(self):
        self.id = 0
        self.name = ''
        self.arry_type = 0
        self.data_type = 0
        self.typelist = list()
        self.prop = None
        self.npdtype = None
        
    def __repr__(self):
        attrs = 'name prop'
        r = ['{}: {}'.format(repr(k), repr(getattr(self, k))) for k in attrs.split()]
        return 'Type({})'.format(', '.join(r))


    def read(self, psffile, typemap):
        code = psffile.read_uint32()
        if code != ElementId.DATA:
            # raise ValueError('Unexpected Type Type: ' + str(code))
            return False

        self.id = psffile.read_uint32()
        self.name = psffile.read_str()
        self.arry_type = psffile.read_uint32()
        self.data_type = psffile.read_uint32()

        if self.data_type == TypeId.STRUCT:
            self.read_type_list(psffile, typemap)

        self.prop = PSF_Property.read_dictionary(psffile)
        self.to_npdtype()
        typemap[self.id] = self
        return True

    def read_type_list(self, psffile, typemap):
        '''used for STRUCT'''
        while True:
            typedef = PSF_Type()
            valid = typedef.read(psffile, typemap)
            if valid:
                self.typelist.append(typedef)
                typemap[typedef.id] = typedef
            else:
                break
            
    def to_npdtype(self):
        if self.npdtype:
            return (self.name, self.npdtype)
        tt ={ TypeId.INT8: 'i4',
              TypeId.INT32: 'i4',
              TypeId.FLOAT: 'f4',
              TypeId.COMPLEX_FLOAT: 'c8',
              TypeId.DOUBLE: 'f8',
              TypeId.COMPLEX_DOUBLE: 'c16'}
        if self.data_type in tt:
            self.npdtype = tt[self.data_type]
            return (self.name, self.npdtype)
        elif self.data_type == TypeId.STRUCT:
            self.npdtype = [t.to_npdtype() for t in self.typelist]
            return (self.name, self.npdtype)
        else:
            raise ValueError('Cannot to be a element of array: Type ' + str(TypeId(self.data_type)))
 


class PSF_Variable:
    def __init__(self):
        self.id = 0
        self.name = ''
        self.type = None
        self.prop = None
        self.npdtype = None
        self.val = None
        self.record_size = 0


    def __repr__(self):
        attrs = 'name type prop'
        r = ['{}: {}'.format(repr(k), repr(getattr(self, k))) for k in attrs.split()]
        if isinstance(self.val, np.ndarray):
            if self.val.dtype.names:
                r.append("'val': ndarray(len: {}, fields: {})".format( len(self.val), ', '.join(self.val.dtype.names)))
            else:
                r.append("'val': ndarray(len: {}, dtype: {})".format( len(self.val), self.val.dtype))
        else:
            r.append("'val': {}".format(self.val))
                
        return 'Var({})'.format(',\n    '.join(r))

    def to_npdtype(self, psffile):
        if self.npdtype:
            return (self.name, self.npdtype)
        self.npdtype = self.type.to_npdtype()[1]
        size = 0
        if isinstance(self.npdtype,list):
            for n,d in self.npdtype:
                size += int(d[1:])
        else:
            size += int(self.npdtype[1:])
        self.record_size = size
        return (self.name, self.npdtype)

    def init_value(self, psffile, size=1):
        dtype =  self.to_npdtype(psffile)
        self.val = np.zeros(size, dtype=dtype[1])

    def read(self, psffile):
        code = psffile.read_uint32()
        if code != ElementId.DATA:
            psffile.unread(4)
            return False

        self.id = psffile.read_uint32()
        self.name = psffile.read_str()
        type_id = psffile.read_uint32()
        self.type = psffile.types[type_id]
        self.prop = PSF_Property.read_dictionary(psffile)

        return True

    def read_non_sweep_value(self, psffile):
        code = psffile.read_uint32()
        if code != ElementId.DATA:
            psffile.unread(4)
            return False

        self.id = psffile.read_uint32()
        self.name = psffile.read_str()
        type_id = psffile.read_uint32()
        self.type = psffile.types[type_id]
        dtype = self.type.npdtype
        if isinstance(dtype, list):
            self.init_value(psffile)
            dt = self.val.dtype
            dt = dt.newbyteorder('>')
            record_size = 0
            for n,d in self.npdtype:
                record_size += int(d[1:])

            vv = psffile.read_npdata(record_size, dt)
            self.val[0] = vv
        else:
            record_size = int(dtype[1:])
            dtype = '>' + dtype
            data = psffile.fp.read(record_size)
            vv = np.frombuffer(data, dtype)[0]
            self.val = vv
        self.prop = PSF_Property.read_dictionary(psffile)
        return True
        
    def read_sweep_value(self, psffile, i=0, nbpoints=1):
        dt = self.val.dtype
        dt = dt.newbyteorder('>')
        self.val[i:i+nbpoints] = psffile.read_npdata(self.record_size, dt, nbpoints)

    def to_array(self, npoints, psffile):
        psf_type = psffile.types[self.type_id]
        dtype = typeid_to_dtype(psf_type)
        return np.empty(npoints, dtype=dtype)


    def read_data(self, array, i, psffile):
        data_array, data_valid = array
        tt = psffile.types[self.type_id]
        if tt.data_type == TypeId.STRUCT:
            #type_id = psffile.read_int32()
            #### FIXME struct.unpack can directly return the tuple
            data_array[i] = tuple(psffile.read_typed_data(psffile.types[self.type_id]))
        else:
            data_array[i] = psffile.read_typed_data(psffile.types[self.type_id])
        data_valid[i] = True

    def read_data_win(self, array, start, size, psffile):
        psffile.read_data_win(array, start, size, psffile.types[self.type_id].data_type)

    def flatten_value(self, a, arrays):
        arrays[self.name] = a
        return [(self, a)]

class PSF_Group:
    def __init__(self):
        self.id = 0
        self.name = ''
        self.vars = OrderedDict()
        self.npdtype = None
        self.record_size = 0
        self.val = None

    def __repr__(self):
        return 'Group(id: ' + repr(self.id) + ', names: ' + self.name + ', vars: ' + repr(self.vars) + ')'

    def init_value(self, psffile, size=1):
        dtype =  self.to_npdtype(psffile)
        self.val = np.zeros(size, dtype=dtype[1])
        for i, var in enumerate(self.vars):
            var.val = self.val[:][var.name] # creates a view, not a copy !!
        

    def read(self, psffile):
        code = psffile.read_uint32()
        if code != ElementId.GROUP:
            psffile.unread(4)
            return False

        self.id = psffile.read_uint32()
        self.name = psffile.read_str()
        length = psffile.read_uint32()


        for i in range(length):
            v = PSF_Variable()
            if v.read(psffile):
                self.vars[v] = v
            else:
                raise ValueError('Group length is ' + str(length) + ', but actually ' + str(i))
        return True

    def read_value(self, psffile, i=0, nbpoints=1):
        '''read the binary data. Variables in the group contain a view to this array (self.val)'''
        dt = self.val.dtype
        dt = dt.newbyteorder('>')
        self.val[i] = psffile.read_npdata(self.record_size, dt)



    def to_npdtype(self, psffile):
        if self.npdtype:
            return (self.name, self.npdtype)
        npdtype = [t.to_npdtype(psffile) for t in self.vars]
        self.npdtype = npdtype
        size = 0
        for n,d in self.npdtype:
            size += int(d[1:])
        self.record_size = size
        return (self.name, self.npdtype)
