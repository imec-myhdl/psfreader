# psfreader
A pure python reader for PSF (Parameter Storage Format) simulation result files

## License
This library is licensed under LGPL version 3 or later.

## required
- Numpy

## usage
            
    p = PSFReader(filename)
    h = p.get_header()
    design = h['design']
    simulation = h['analysis description']
    sweep = p.get_sweep()       
    sweep_parameter_name = sweep.name

    x = sweep.val
    nb_of_points = len(x) # should be equal to h['PSF sweep points']

    signals= p.get_signals()
    sig = signals['vdd']
    signal_name = sig.name
    signal_value = sig.val
    signal_psftype = sig.type
    signal_dtype = sig.val.dtype
    signal_properties = sig.prop



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

Cadence supplies a (largely ondocumented) utility (named 'psf') that can convert PSFformatted files to human readable format. 
It does give you a clue what the binary format looks like. PSF files are divided in sections:

- HEADER (sectionid = 0): generic simulation info
- TYPE   (sectionid = 1): type definitions
- SWEEP  (sectionid = 2): sweep definitions (note: multiple sweeps are not supported as I do not have any testfiles for that case)
- TRACE  (sectionid = 3): trace definitions
- VALUE  (sectionid = 4): contains actual vectors (sweep and traces)

For faster access the file also contains indexes, but the psfreader ignores them
