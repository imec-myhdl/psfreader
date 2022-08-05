
import struct
import io
import numpy as np
from collections import OrderedDict

from psfreader.psfdata import TypeId, ChunkId, ElementId, \
                              SectionId, SectionInfo, PropertyTypeId, \
                              PSF_Property, PSF_Type, PSF_Variable, PSF_Group  

class PSFReaderError(ValueError):
    pass


class PSFFile:
    def __init__(self, filename):
        self.filename = filename
        self.fp = open(filename, 'rb')

        self.sections = dict()
        self.types = dict()
        self.properties = dict()
        self.sweep_vars = list()
        self.traces = OrderedDict()
        self.sweep_value = None
        self.sweep_value_w_var = None
        self.value = None
        self.variables = OrderedDict()
        self.read_points = 0
        self.fp.seek(0, io.SEEK_END)
        self.fsize = self.fp.tell()
        self.fp.seek(0, io.SEEK_SET)

        self.fp.seek(-12, io.SEEK_END)
        b = self.fp.read(8)
        if b != b'Clarissa':
            raise PSFReaderError('This file is not a PSF format.')
        self.fp.seek(0, io.SEEK_SET)
        self.read_single_type = { TypeId.STRING         : self.read_str,
                                  TypeId.INT8           : self.read_int32,
                                  TypeId.INT32          : self.read_int32,
                                  TypeId.FLOAT          : self.read_float,
                                  TypeId.COMPLEX_FLOAT  : self.read_complex_float,
                                  TypeId.DOUBLE         : self.read_double,
                                  TypeId.COMPLEX_DOUBLE : self.read_complex_double,
                                  PropertyTypeId.STRING : self.read_str,
                                  PropertyTypeId.INT    : self.read_int32,
                                  PropertyTypeId.DOUBLE : self.read_double }
            
 
    def close(self):
        self.fp.close()


    # =============================================================================
    # routines to read binary data from file
    # for single values struct.unpack is ~2.5x faster than numpy.frombuffer
    # =============================================================================
    
    #    int8 is mapped to read int32 as it is always zero stuffed and aligned to 4 byte boundary
    #    def read_uint8(self): 
    #        return self.fp.read(1)

    def read_int32(self):
        '''read a 32 bit signed integer
        although apparently pdf does not distinguish between uint and int'''
        data = self.fp.read(4)
        return struct.unpack('>i', data)[0] # big endian 32 bit integer
        # return np.frombuffer(data, '>i4')[0]

    def read_uint32(self):
        '''read a 32 bit unsigned integer
        although apparently pdf does not distinguish between uint and int'''
        data = self.fp.read(4)
        return struct.unpack('>I', data)[0] # big endian 32 bit unsigned integer
        # return np.frombuffer(data, '>u4')[0]

    def unread(self, nbytes=4):
        self.fp.seek(-nbytes, io.SEEK_CUR)

    def read_float(self):
        data = self.fp.read(4)
        return struct.unpack('>f', data)[0] # big endian 32 bit
        # return np.frombuffer(data, '>f4')[0]

    def read_complex_float(self):
        data = self.fp.read(8)
        return complex(*struct.unpack('>2f', data)) # big endian re 32 bit, im 32 bit
        # return np.frombuffer(data, '>c8')[0]

    def read_double(self):
        data = self.fp.read(8)
        return struct.unpack('>d', data)[0] # big endian 64 bit
        # return np.frombuffer(data, '>f8')[0]


    def read_complex_double(self):
        data = self.fp.read(16)
        return complex(*struct.unpack('>2d', data)) # big endian re 64 bit, im 64 bit
        # return np.frombuffer(data, '>c16')[0]


    def read_str(self):
        length = self.read_uint32()
        extras = ((length + 3) & ~0x03) - length  # align to 4byte boundary
        data = self.fp.read(length)
        self.fp.read(extras)
        return data.decode()

        

    # =============================================================================
    # read in (structured) numpy array row(s)
    # numpy has structured arrays https://numpy.org/doc/stable/user/basics.rec.html
    # these are basically arrays where the columns are dictionary like
    # for the the creation requires rather complex dtype
    # see https://numpy.org/doc/stable/reference/arrays.dtypes.html
    # Each assigned value should be a tuple of length equal to the number of fields 
    # in the array, and not a list or array as these will trigger numpy’s 
    # broadcasting rules. The tuple’s elements are assigned to the successive 
    # fields of the array, from left to right.
    # =============================================================================
    def read_npdata(self, bytes_per_row, dtype, nbpoints=1):
        '''
        read in (structured) numpy array row(s).
        
            Numpy has structured arrays https://numpy.org/doc/stable/user/basics.rec.html
            these are basically arrays where the columns are dictionary like
            for the the creation requires rather complex dtype
            see https://numpy.org/doc/stable/reference/arrays.dtypes.html
            
            Each assigned value should be a tuple of length equal to the number of fields 
            in the array, and not a list or array as these will trigger numpy’s 
            broadcasting rules. The tuple’s elements are assigned to the successive 
            fields of the array, from left to right.'''
        data = self.fp.read(bytes_per_row*nbpoints)
        return np.frombuffer(data, dtype=dtype)    
    



    # =============================================================================
    # parsing of PSF structure
    # =============================================================================
    def read_file(self, header_only=False):
        '''
        Read whole PSF file and convert to internal format
        '''

        self.completed = True

        size = self.fsize
        self.fp.seek(self.fsize - 4, io.SEEK_SET)
        datasize = self.read_uint32()

        num_section = (size - datasize - 12) // 8  # //floor div
        # is the 12 because of the 'Clarissa' string?

        toc = size - 12 - num_section * 8  # Head position of section information

        sections = dict()
        section_id = -1
        for i in range(num_section):
            self.fp.seek(toc + 8 * i)
            section_id = self.read_uint32()
            section_offset = self.read_uint32()
            sections[section_id] = SectionInfo(section_offset, 0) # fill size later
            
        #calculate sizes
        sl = list(sections.values()) # convert to list
        for ix, section in enumerate(sl[1:]):
            sl[ix].size = section.offset - sl[ix].offset # size is next_section_offset-section_offset
        sl[-1].size = size - sl[-1].offset # last section
        self.sections = sections

        # Section-by-section pre-processing
        for section_id in sorted(self.sections.keys()):
            if section_id not in self.sections:
                continue
            self.fp.seek(self.sections[section_id].offset, io.SEEK_SET)

            if section_id == SectionId.HEADER:
                self.read_section_HEADER()
                if header_only:
                    return

            elif section_id == SectionId.TYPE:
                self.read_section_TYPE()
    
            elif section_id == SectionId.SWEEP:
                self.read_section_SWEEP()
    
            elif section_id == SectionId.TRACE:
                self.read_section_TRACE()

            elif section_id == SectionId.VALUE:
                self.read_section_VALUE()
            else:
                self.value = None

    def read_chunk_preamble(self, chunkid):
        c_id = self.read_uint32()
        if c_id != chunkid:
            raise PSFReaderError('Unexpected ChunkId. Expected: ' + repr(chunkid) + ', Actually: ' + hex(c_id))
        return self.read_uint32()

    def read_section_preamble(self, section):
        sectioninfo = self.sections[section]

        self.fp.seek(sectioninfo.offset, io.SEEK_SET)
        return self.read_chunk_preamble(ChunkId.MAJOR_SECTION)

    def read_section_HEADER(self):
        endpos = self.read_chunk_preamble(ChunkId.MAJOR_SECTION)
        self.properties = PSF_Property.read_dictionary(self)
        self.skip_to_pos(endpos)

    def read_section_TYPE(self):
        self.types = dict()
        self.read_chunk_preamble(ChunkId.MAJOR_SECTION) # section_end
        end_sub = self.read_chunk_preamble(ChunkId.MINOR_SECTION)
        while self.fp.tell() < end_sub:
            typedef = PSF_Type()
            typedef.read(self, self.types)
        

    def read_section_SWEEP(self):
        self.read_chunk_preamble(ChunkId.MAJOR_SECTION) # section_end
        self.sweep_vars = list()
        while True:
            s_var = PSF_Variable()
            if s_var.read(self):
                self.sweep_vars.append(s_var)
            else:
                break

    def read_section_TRACE(self):
        self.read_chunk_preamble(ChunkId.MAJOR_SECTION) # section_end
        endsub = self.read_chunk_preamble(ChunkId.MINOR_SECTION)

        valid = True
        # self.traces = list()
        while valid and self.fp.tell() < endsub:
            group = PSF_Group()
            valid = group.read(self)
            if valid:
                for var in group.vars:
                    self.traces[var.name] = var
            else:
                var = PSF_Variable()
                valid = var.read(self)
                if valid:
                    self.traces[var.name] = var        

    def read_section_VALUE(self):
        endsub = self.read_chunk_preamble(ChunkId.MAJOR_SECTION) 
        c_id = self.read_uint32()
        if c_id == ChunkId.MINOR_SECTION:
            endsub = self.read_uint32()
        else:
            self.unread()

        if len(self.sweep_vars) == 0: # no sweep specified
            # only variables,
            while self.fp.tell() < endsub:
                var = PSF_Variable()
                if var.read_non_sweep_value(self):
                    self.variables[var.name] = var
                else:
                    break

        elif len(self.sweep_vars) == 1:  # sweep specified
            npoints = self.properties['PSF sweep points']
            sweep_var = self.sweep_vars[0]
            # sweep_type = self.types[sweep_var.type_id]
            sweep_var.init_value(self, npoints)
            
            for trace in self.traces.values():
                trace.init_value(self, npoints)
    
            if 'PSF window size' in self.properties:
                win_size = self.properties['PSF window size']
            else:
                win_size = 0
    
            if win_size > 0:
                # records are in chunks of win_size (bytes)
                # structure off each chunk : 
                #    int16 dummy, int16 chunck_size (bytes)
                #    when size is 0x7fff just means that the record continues
                #
                # decoding contents pseudo code:
                # while read_points < npoints:
                #    sweep.append(chunk_size data-points)
                #    for var in vars:
                #        var.append(chunk_size data-points)
                read_points = 0
                while read_points < npoints:
                    block_id = self.read_uint32()
                    if block_id == ElementId.DATA:
                        nb_of_datapoints = self.read_uint32() & 0x0000ffff
                        
                        sweep_var.read_sweep_value(self, i=read_points, nbpoints=nb_of_datapoints)
                        skip_size = win_size - sweep_var.record_size * nb_of_datapoints
                        
                        for var in self.traces.values(): # assume that only group used
                            self.fp.seek(skip_size, io.SEEK_CUR)  # skip dummy value
                            var.read_sweep_value(self, i=read_points, nbpoints=nb_of_datapoints)
                            skip_size = win_size - var.record_size * nb_of_datapoints
        
                        read_points += nb_of_datapoints
                    elif block_id == ElementId.ZEROPAD:
                        pad_size = self.read_uint32()
                        self.fp.seek(pad_size, io.SEEK_CUR)
                    else:
                        raise PSFReaderError('Unexpected data id: ' + str(block_id))
                        self.completed = False
                        break
    
            else:
                # records follow DATA, element_id, [binary data]*N
                for i in range(npoints):
                    elemid = self.read_uint32()  # check x == ElementId.DATA
                    assert elemid == ElementId.DATA
                    var_id = self.read_uint32()  # check x == self.sweep_vars[0].id
                    assert var_id == sweep_var.id
                    sweep_var.read_sweep_value(self, i)
                    
                    for trace in self.traces.values():
                        elemid = self.read_uint32()  # check x == ElementId.DATA
                        assert elemid == ElementId.DATA
                        var_id = self.read_uint32()  # check x == self.sweep_vars[0].id
                        assert var_id == trace.id
                        trace.read_sweep_value(self, i)
        else:
             raise PSFReaderError('Not supported file format: more than one Sweep variable.')


    def read_section_VALUE_sweep(self):
        '''read the data of the VALUE section in case a sweep is specified'''
                       

    def skip_to_pos(self, pos):
        self.fp.seek(pos, io.SEEK_SET)

 
class PSFReader:
    '''
    Parameter-Storage Format Reader for python.
    '''

    def __init__(self, filename, header_only=False):
        self.psf = PSFFile(filename)
        self.psf.read_file(header_only=header_only)
        self.get_signals() 

    def get_header(self):
        '''Return a dictionary of properties'''
        return {key: self.psf.properties[key] for key in self.psf.properties}

    def get_signals(self):
        '''Return a dictionary with signals'''
        if not hasattr(self, 'signals'):
            signals = None
            if len(self.psf.sweep_vars) == 0: # no sweep specified
                signals = self.psf.variables
            else:
                signals = self.psf.traces
                if signals:
                    first_elem = next(iter(signals.values()))
                    if isinstance(first_elem, PSF_Group):
                        signals = OrderedDict([(t.name, t) for t in  first_elem.vars])
            self.signals = signals
        return self.signals

    def get_signal(self, name):
        '''Retrieve signal[name]'''
        if not hasattr(self, 'signals'):
            self.get_signals()
        return self.signals[name]

    def get_sweep(self):
        '''Return the value of the sweep variable'''
        return self.psf.sweep_vars[0] if len(self.psf.sweep_vars) ==1 else None



