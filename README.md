# psfreader
A pure python reader for PSF (Parameter Storage Format) simulation result files

## License
This library is licensed under LGPL version 3 or later.

## required
- Numpy

## Install
    python3 -m pip install git+https://github.com/imec-myhdl/psfreader.git

## Uninstall
    python3 -m pip uninstall psfreader
    
## Upgrade
    python3 -m pip install --upgrade git+https://github.com/imec-myhdl/psfreader.git

## usage
    import psfreader
    
    p = PSFReader('filename')
    h = p.get_header() # PSF-properties
    design = h['design'] # note: this generally is the first line of your netlist
    description = h['analysis description']
    
    # get x 
    sweep = p.get_sweep()       
    sweep_parameter_name = sweep.name
    x = sweep.val
    nb_of_points = len(x) # should be equal to h['PSF sweep points']

    # get y 
    signals= p.get_signals()
    sig = signals['vdd']
    y = sig.val
    signal_name = sig.name # should be 'vdd' in this case :)
    signal_psftype = sig.type # internal PSF type
    signal_dtype = sig.val.dtype # numpy dtype
    signal_properties = sig.prop # when empty in psf file (most of the time) this is a link to sig.type.prop
    ...


## Resources
Heavily borrowed from Ikuo Kobori's python psfreader. Extended to allow for more data-types and STRUCT elements

- Henrik Johansson's libspf https://github.com/henjo/libpsf
- ma-laforge/LibPSF.jl https://github.com/ma-laforge/LibPSF.jl
- ma-laforge/PSFWrite.jl https://github.com/ma-laforge/PSFWrite.jl
- Eric Chang's libpsf2 https://github.com/pkerichang/libpsf2
- Ikuo Kobori's psfreader  https://github.com/funikk/psfreader

## Known Limitations
- cannot read mixed-signal simulation data
- cannot read multi sweep variables
- cannot read splited file (larger than 2GB)
- python is not the fastest but the heavylifting is done by numpy

## Debugging Hints:

Cadence(TM) supplies a (largely ondocumented) utility (named 'psf') that can convert PSFformatted files to human readable format. 
It does give you a clue what the binary format looks like. PSF files are divided in sections:

- HEADER (sectionid = 0): generic simulation info
- TYPE   (sectionid = 1): type definitions
- SWEEP  (sectionid = 2): sweep definitions (note: multiple sweeps are not supported as I do not have any testfiles for that case)
- TRACE  (sectionid = 3): trace definitions
- VALUE  (sectionid = 4): contains actual vectors (sweep and traces)

For faster access the file also contains indexes, but the psfreader ignores them
