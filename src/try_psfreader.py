#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 10 13:23:26 2020

@author: matema49
"""

from psfreader import PSFReader

if __name__ == '__main__':
    fn = '/imec/users/matema49/ac.ac.float'    
#    fn = '/imec/users/matema49/dc.dc'    
#    fn = '/imec/users/matema49/tran.tran.tran'
#    fn = '/tmp/scratch/matema49/simulation/UWB4Z_RX_LPF_tb/spectre/config_extracted/psfbin/tran.tran.tran'
    p = PSFReader(fn)
    h                    = p.get_header_properties()
    sweep_parameter_name = p.get_sweep_param_name()
    signal_names         = p.get_signal_names()
    net012d = p.get_signal('net012')
#    
    fn = '/imec/users/matema49/ac.ac'    
##    fn = '/imec/users/matema49/dc.dc'    
##    fn = '/imec/users/matema49/tran.tran.tran'
##    fn = '/tmp/scratch/matema49/simulation/UWB4Z_RX_LPF_tb/spectre/config_extracted/psfbin/tran.tran.tran'
    p = PSFReader(fn)
    h                    = p.get_header_properties()
    sweep_parameter_name = p.get_sweep_param_name()
    signal_names         = p.get_signal_names()
    net012f = p.get_signal('net012')
#    
    fn = '/imec/users/matema49/dc.dc'    
#    fn = '/imec/users/matema49/tran.tran.tran'
#    fn = '/tmp/scratch/matema49/simulation/UWB4Z_RX_LPF_tb/spectre/config_extracted/psfbin/tran.tran.tran'
    p = PSFReader(fn)
    h                    = p.get_header_properties()
    sweep_parameter_name = p.get_sweep_param_name()
    signal_names         = p.get_signal_names()
    net012d = p.get_signal('net012')

    fn = '/tmp/scratch/matema49/simulation/UWB4Z_RX_LPF_tb/spectre/config_extracted/psfbin/tran.tran.tran'
    p = PSFReader(fn)
    h                    = p.get_header_properties()
    sweep_parameter_name = p.get_sweep_param_name()
    signal_names         = p.get_signal_names()
    signal = p.get_signal('LPF.BiQuad0\\|BiQuadUnit0\\|gm0n\\(6\\)\\|MN1:d')