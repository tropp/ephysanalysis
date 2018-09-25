# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import sys
import re
from pathlib import Path
from collections import OrderedDict
from scipy.io import matlab
import numpy as np
import pprint
import ephysanalysis.metaarray as EM
import ephysanalysis.IVSummary as IVS


"""
Helper functions
"""
def ndinds(shape):
    ind = np.indices(shape)
    while len(ind.shape) > 2:
        ind = ind.reshape(ind.shape[:-2] + (ind.shape[-2]*ind.shape[-1],))
    return [tuple(x) for x in ind.T]

def flatten(data):
    """Flatten highly nested structures returned by loadmat
    """
    if isinstance(data, np.ndarray):
        while data.ndim > 0 and data.shape[0] == 1:
            data = data[0]
        if data.ndim == 0 and data.dtype.names is not None:
            data = dict(zip(data.dtype.names, data))
        elif data.ndim > 0:
            if data.dtype.kind == 'O':
                for i in ndinds(data.shape):
                    data[i] = flatten(data[i])
            elif data.dtype.names is not None:
                for fname in data.dtype.names:
                    if data.dtype.fields[fname][0].kind == 'O':
                        field = data[fname]
                        for i in ndinds(field.shape):
                            field[i] = flatten(field[i])
    if isinstance(data, dict):
        for k,v in data.items():
            data[k] = flatten(v)
    return data

        
    
class GetClamps():
    
    def __init__(self, datac):
        """
        Set up clamps. 
        
        Parameters
        ----------
        datac : object
            The DatacFile instance of the matdatac file
        """
        self.datac = datac
        self.protocol = None


    def getData(self, chmap=None):
        """
        create a Clamp structure for use in SpikeAnalysis and RMTauAnalysis from acq4.
        Fills in the fields that are returned by PatchEPhys getClamps:
        clampInfo['dirs]
        clampInfo['missingData']
        self.time_base
        self.values
        self.traceStartTimes = np.zeros(0)
        self.sequence
        self.clampValues (sequence)
        self.nclamp = len(self.clmapVlaues
        self.repc
        self.nrepc
        self.data_mode
        self.model_mode = False
        self.command_scale_factor
        self.command_units
        self.devicesUsed
        self.clampDevices
        self.holding
        self.clampState
        self.sample_interval
        self.RSeriesUncomp
        self.amplifeirSettings['WCCompValid', 'WCEmabled', 'CompEnabled', 'WCSeriesResistance']
        self.cmd_wave
        self.commandLevels (np.array(self.values))
        self.traces = MetaArray(traces, info=info)
        self.tstart
        self.tdur
        self.tend
        self.spikecount = np.zeros(len...) if in vcmode.
        
        Info from an example data file:
        [{'name': 'Channel', 'cols': [{'units': 'A', 'name': 'Command'}, {'units': 'V', 'name': 'primary'}, {'units': 'A', 'name': 'secondary'}]},
        {'units': 's', 'values': array([ 0.00000000e+00, 2.50000000e-05, 5.00000000e-05, ..., 6.99925000e-01, 6.99950000e-01, 6.99975000e-01]),
        'name': 'Time'}, {'ClampState': {'primaryGain': 10.0, 'ClampParams': {'OutputZeroEnable': 0, 'PipetteOffset': 0.05197399854660034,
        'Holding': -1.525747063413352e-11, 'PrimarySignalHPF': 0.0, 'BridgeBalResist': 20757020.0, 'PrimarySignalLPF': 20000.0, 'RsCompBandwidth':
        8.413395979806202e-42, 'WholeCellCompResist': 8.413395979806202e-42, 'WholeCellCompEnable': 6004, 'LeakSubResist': 8.413395979806202e-42,
        'HoldingEnable': 1, 'FastCompTau': 8.413395979806202e-42, 'SlowCompCap': 8.413395979806202e-42, 'WholeCellCompCap': 8.413395979806202e-42,
        'LeakSubEnable': 6004, 'NeutralizationCap': 1.9578947837994853e-12, 'BridgeBalEnable': 1, 'RsCompCorrection': 8.413395979806202e-42,
        'NeutralizationEnable': 1, 'RsCompEnable': 6004, 'OutputZeroAmplitude': -0.0009990156395360827, 'FastCompCap': 8.413395979806202e-42,
        'SlowCompTau': 8.413395979806202e-42}, 'secondarySignal': 'Command Current', 'secondaryGain': 1.0, 'secondaryScaleFactor': 2e-09,
        'primarySignal': 'Membrane Potential', 'extCmdScale': 4e-10, 'mode': 'IC', 'holding': 0.0, 'primaryUnits': 'V', 'LPFCutoff': 20000.0,
        'secondaryUnits': 'A', 'primaryScaleFactor': 0.1, 'membraneCapacitance': 0.0}, 'Protocol': {'recordState': True, 'secondary': None,
        'primary': None, 'mode': 'IC'}, 'DAQ': {'command': {'numPts': 28000, 'rate': 40000.0, 'type': 'ao', 'startTime': 1296241556.7347913},
        'primary': {'numPts': 28000, 'rate': 40000.0, 'type': 'ai', 'startTime': 1296241556.7347913}, 'secondary': {'numPts': 28000, 'rate':
        40000.0, 'type': 'ai', 'startTime': 1296241556.7347913}}, 'startTime': 1296241556.7347913}]

        )
        """
        item = self.protocol
        if item is None:
            return False
        protocol = self.datac.items[item].type
        print('protocol: ', protocol)
        rate, recs = self.datac.items[item].data()
        rate = self.datac.items[item].dfile['Sample_Rate']['v']*1e-6  # convert to seconds
        self.dfile = self.datac.items[item].dfile
        (ddir, fname) = os.path.split(self.datac.fname)
        points = self.dfile['Points']['v']
        nchannels = len(self.dfile['Channels']['v'])
        dt = nchannels * float(rate)
        #print(nchannels, points, rate, dt)
        data_mode = self.getDataMode()
        self.data_mode = data_mode[0]
        self.time_base = np.arange(points)*dt
        datac_traces = np.zeros((len(recs), nchannels+1, points))
        self.recs = recs
        if len(recs) < 16:
            return False
        for i in range(len(recs)):
            for j in range(nchannels+1):
                if j == 2:  # pull the stimulus only
                    # print len(recs[i][j])
                    # print len(np.arange(0, len(recs[i][j])))
                    cmd = np.interp(self.time_base, np.arange(0, len(recs[i][j]))/1000., recs[i][j])
                    datac_traces[i, j, :] = cmd
                else:  # channels 0 and 1
                    # print 'i,j', i, j
                    if len(recs[i][j]) != datac_traces.shape[2]:
                        return False # (cannot match, something is wrong... )
                    datac_traces[i, j, :] = recs[i][j]
                    if j == 1:
                        datac_traces[i, j, :] *= 1e-3 # convert to V from mV
        self.traces = np.array(datac_traces)

        #np.array([[x[chmap[i]] for x in recs] for i in range(len(chmap))])  # remap channels
        #self.values = np.array([np.mean(datac_traces[1,i]) for i in range(len(recs))])
        # print self.values
        self.repc = 1
        self.nrepc = 1
        self.model_mode = False
        self.command_scale_factor = 1
        self.command_units = 'A'
        self.devicesUsed = None
        self.clampDevices = None
        self.holding = 0.
        self.amplfierSettings = {'WCCompValid': False, 'WCEnabled': False, 
                'CompEnabled': False, 'WCSeriesResistance': 0.}
        self.clampState = None
        self.sample_interval = dt # in seconds
        self.sample_rate = (1./dt)*np.ones(len(recs))
        self.RSeriesUncomp = 0.
        self.cmd_wave = np.squeeze(self.traces[:, 0, :])*1e-12
        self.protoTimes = {'drugtestiv': [0.21, 0.51], 'ap-iv2': [0.01, 0.5], 'cciv': [0.005, 0.105]}  # in seconds
        self.tstart = 0.01
        self.tdur = 0.500
        if protocol in self.protoTimes:
            self.tstart = self.protoTimes[protocol][0]
            self.tdur = self.protoTimes[protocol][1]
            
        self.tend = self.tstart + self.tdur
        t0 = int(self.tstart/dt)
        t1 = int(self.tend/dt)
        self.values = np.mean(self.cmd_wave[:, t0:t1], axis=1)  # express values in amps
        self.commandLevels = self.values
        info = [{'units': 'A', 'values': self.values, 'name': 'Command'},
                    {'name': 'Time', 'units': 's', 'values': self.time_base},
                    {'ClampState': {'primaryGain': 10.0, 'ClampParams': {'OutputZeroEnable': 0, 'PipetteOffset': 0.0,
                        'Holding': 0.0, 'PrimarySignalHPF': 0.0, 'BridgeBalResist': 0.0, 'PrimarySignalLPF': 20000.0, 'RsCompBandwidth':
                        0.0, 'WholeCellCompResist': 0.0, 'WholeCellCompEnable': 6004, 'LeakSubResist': 0.0,
                        'HoldingEnable': 1, 'FastCompTau': 0.0, 'SlowCompCap': 0.0, 'WholeCellCompCap': 0.,
                        'LeakSubEnable': 6004, 'NeutralizationCap': 0., 'BridgeBalEnable': 0, 'RsCompCorrection': 0.0,
                        'NeutralizationEnable': 1, 'RsCompEnable': 6004, 'OutputZeroAmplitude': 0., 'FastCompCap': 0.,
                        'SlowCompTau': 0.0}, 'secondarySignal': 'Command Current', 'secondaryGain': 1.0, 'secondaryScaleFactor': 2e-09,
                        'primarySignal': 'Membrane Potential', 'extCmdScale': 4e-10, 'mode': 'IC', 'holding': 0.0, 'primaryUnits': 'V', 'LPFCutoff': 20000.0,
                        'secondaryUnits': 'A', 'primaryScaleFactor': 0.1, 'membraneCapacitance': 0.0}, 'Protocol': {'recordState': True, 'secondary': None,
                        'primary': None, 'mode': 'IC'}, 'DAQ': {'command': {'numPts': 10000, 'rate': 10000.0, 'type': 'ao', 'startTime': 0.},
                        'primary': {'numPts': 10000, 'rate': 10000.0, 'type': 'ai', 'startTime': 0.}, 'secondary': {'numPts': 1000, 'rate':
                        10000.0, 'type': 'ai', 'startTime': 0.}}, 'startTime': 0.}]
        self.WCComp = self.parseClampWCCompSettings(info)
        self.CCComp = self.parseClampCCCompSettings(info)
        self.traces = np.squeeze(self.traces[:,1,:])
        self.traces = EM.MetaArray(self.traces, info=info)
        self.cmd_wave = EM.MetaArray(self.cmd_wave,
             info=[{'name': 'Command', 'units': 'A',
              'values': np.array(self.values)},
              self.traces.infoCopy('Time'), self.traces.infoCopy(-1)])
        self.spikecount = np.zeros(len(recs))
        self.rgnrmp = [0, 0.005]
        print('getclamps got it all')
        return True

    def getDataMode(self):
        datamode = self.dfile['Data_Mode']['v']
        #print "current block data mode : ", datamode
        if datamode in ['cc', 'ic', 'CC', 'IC']:
            datamode = 'cc'
            chmap = [1, 0, 2]
        elif datamode in ['vc', 'VC']:
            datamode = 'vc'
            chmap = [0, 1, 2]
        else:
            raise ValueError('Data mode <%s> is not known' % datamode)
        return datamode, chmap

    def setProtocol(self, pathtoprotocol):
        """
        Parameters
        ----------
        pathtoprotocol str (default: None)
            Path to the protocol directory to set for this instance of the reader
        """
        self.protocol = pathtoprotocol
    
    def setDataName(self, dataname):
        """
        Set the type (name) of the data metaarray name that will be read
        """
        self.dataname = dataname

    def parseClampWCCompSettings(self, info):
        """
        Given the .index file for this protocol dir, try to parse the 
        clamp state and compensation
        """
        d = {}
        if 'ClampState' in info[1].keys() and 'ClampParams' in info[1]['ClampState'].keys():
            par = info[1]['ClampState']['ClampParams']
            d['WCCompValid'] = True
            d['WCEnabled'] = par['WholeCellCompEnable']
            d['WCResistance'] = par['WholeCellCompResist']
            d['WCCellCap'] = par['WholeCellCompCap']
            d['CompEnabled'] = par['RsCompEnable']
            d['CompCorrection'] = par['RsCompCorrection']
            d['CompBW'] = par['RsCompBandwidth']
            return d
        else:
            return {'WCCompValid': False, 'WCEnable': 0, 'WCResistance': 0., 'WholeCellCap': 0.,
                    'CompEnable': 0, 'CompCorrection': 0., 'CompBW': 50000. }

    def parseClampCCCompSettings(self, info):
        d = {}
        if 'ClampState' in info[1].keys() and 'ClampParams' in info[1]['ClampState'].keys():
            par = info[1]['ClampState']['ClampParams']
            d['CCCompValid'] = True
            d['CCBridgeEnable'] = par['BridgeBalEnable']
            d['CCBridgeResistance'] = par['BridgeBalResist']
            d['CCNeutralizationEnable'] = par['NeutralizationEnable']
            d['CCNeutralizationCap'] = par['NeutralizationCap']
            d['CCLPF'] = par['PrimarySignalLPF']
            d['CCPipetteOffset'] = par['PipetteOffset']
            return d
        else:
            return {'CCCompValid': False, 'CCBridgeEnable': 0, 'CCBridgeResistance': 0., 'CCNeutralizationEnable': 0.,
                    'CCNeutralizationCap': 0, 'CCPipetteOffset': 0., 'CCLPF': 10000. }
    


class DatacFile(object):
    def __init__(self, fname):
        """
        Open the matdatac file and read the data (all of it)
        Creates an instance with the data, a list of the
        'items' in the file. The items are either
        HFILE, Note, or data (sfile, dfile, data) Block
        structures from the Block, Hfile and Note classes.
        
         """
        self.fname = fname
        self.data = matlab.loadmat(fname)
        
        # read block records
        self.items = []
        blockid = None
        blockrecs = []
        for rec in self.data['Index'][0]:
            typ = rec['type'][0]
            #print('typ: ', typ)
            if typ == 'HFILE':
                self.items.append(HFile(self, rec))
            elif typ == 'NOTE':
                self.items.append(Note(self, rec))
            elif typ in ('SFILE', 'DFILE', 'DATA', 'STIM'):
                bid = rec['block'][0][0]
                if blockid != bid:
                    if blockid is not None:
                        self.items.append(Block(self, blockrecs))
                        blockrecs = []
                    blockid = bid
                blockrecs.append(rec)
        
        if len(blockrecs) > 0:
            self.items.append(Block(self, blockrecs))
            
    def summary(self):
        """
        Print a sumary of the file (which blocks, etc)
        """
        summ = 'FILE: ' + self.fname
        typs = set([i.type for i in self.items if i.type not in ('HFILE', 'NOTE')])
        summ += '\nBLOCKS: ' + '  '.join(list(typs))
        
        for i in self.items:
            if i.type == 'HFILE':
                summ += '\n' + i.summary() + '\n'
            if i.type == 'NOTE':
                summ += '\n* ' + i.note 
        return summ


class HFile(object):
    def __init__(self, datac, rec):
        """
        Store the matdatac Hfile structure
        """
        self.datac = datac
        self.rec = rec
        self.data = flatten(self.datac.data[self.rec['MatName'][0]])
        self.type = 'HFILE'
        
    def summary(self):
        exp = self.data['Experiment']['v']
        
        # What does it mean to have multiple values in the Experiment field??
        if isinstance(exp, np.ndarray):
            exp = '\n'.join(exp)
        
        summ = exp + '\n'
        summ += 'Species: %s  Age: %s' % (self.data['Species']['v'],
                                          self.data['Age']['v'])
        return summ

    
class Note(object):
    def __init__(self, datac, rec):
        """
        Store the note assicated with the current record
        from the matdatac file structure
        
        Parameters
        ----------
        datac : DatacFile object for the data
        
        rec : int
            Record for the note data to be retrieved
        """
        self.datac = datac
        self.rec = rec
        self.type = 'NOTE'
        self.note = flatten(datac.data[rec['MatName'][0]])['v']
        
    def summary(self):
        return self.note
    

class Block(object):
    def __init__(self, datac, block_recs):
        """
        Read the data from the block records
        
        Parameters
        ----------
        datac : DatacFile object for the data
        
        block_recs : list
            A list of the records to be read from the file and stored
        
        """
        self.datac = datac
        self._data = None
        self.recs = block_recs
        self.notes = []
        self.type = None
        self.stims = []
        self.recordings = []
        for rec in self.recs:
            typ = rec['type'][0]
        #    print('typ: ', typ)
            if rec['MatName'][0] not in self.datac.data.keys():
                print ('missing data block: ', rec['MatName'][0])
                continue
            data = flatten(self.datac.data[rec['MatName'][0]])
           # print('data len: ', len(data))
            if typ == 'DATA':
                self.type = rec['type2'][0]
                self.recordings.append(data)
            elif typ in ['SFILE', 'STIM']:
              #  print('block sfile, stype2, stims: ', rec['type2'])
                self.type = rec['type2'][0]
                self.stims.append(data)
            elif typ == 'DFILE':
                self.dfile = data
            else:
                raise ValueError("Unrecognized data type: %s" % typ)
        
    def summary(self, printnow=True):
        summ = '%d data, %d stims\n' % (len(self.recordings[0]), len(self.stims[0]))
        summ += '---- DFILE: ----\n'
        summ = ''
        for k in self.dfile.keys():
            if k in ['Actual_Rate', 'ChannelList', 'Data_Mode', 'Points', 'Sample_Rate', 'TraceDur']:
                 fmtstr = '%15s : ' + ('%s\n' % self.dfile[k]['f'])
                 summ += fmtstr % (k, self.dfile[k]['v'])
        summ += '\n'
        summ += '%15s : %3d - %3d' % ('Records', self.dfile['Record'], len(self.recordings[0]))
        summ += pprint.pformat(self.dfile)

        return summ
        
    def data(self):
        """Return (sample rate, [traces]) for this block, where [traces] is
        a list of (primary_channel, secondary_channel, stim) tuples.
        """
        if self._data is not None:
            return self._data
        
        d = self.recordings[0]
        dk = list(d[0].keys())[0]
        mode = d[0][dk]['status']['Data']['mode']
        if isinstance(mode, np.ndarray):
            mode = mode[0]
        x = []

        if len(self.stims) > 0:
            reps = self.stims[0]['Repeats']['v']
        else:
            reps = 1
        for i in range(len(d)):
            dk = list(d[i].keys())[0]
            data = d[i][dk]['data']
            if len(self.stims) > 0:
                stim = self.stims[0]['waveform']
            else:
                stim = np.zeros(data.shape[0])
            if isinstance(stim, np.ndarray):
                # Is this right? when len(stims) < len(recordings), how should
                # they be matched together?
                if len(self.stims) > 0:
                    stim = stim[0]['v2'] # stim[i//reps]['v2']
                else:
                    stim = np.zeros(data.shape[0])
            else:
                stim = stim['v2']
            
            if mode == 'V-Clamp':
                x.append((data[:,1], data[:,0], stim))
            else:
                x.append((data[:,0], data[:,1], stim))
                # x.append((pg.gaussianFilter(data[:, 0], sigma=(2,)), data[:, 1], stim))
        
        rate = 1e6 / self.dfile['Sample_Rate']['v']
                
        self._data = rate, x
        return self._data


if __name__ == '__main__':
    import sys
    path = ''
    datasummary = '../DataSummaries'
    fn = '/Users/pbmanis/Documents/data/RX_CCdata/13jul09a.mat'

    df = DatacFile(os.path.join(fn))  # get the matdatac file
    # for it in df.items:
    #     if isinstance(it, Block):
    #         print(it.summary())
    #
    blocksel = 2
    GC = GetClamps(df)  # make an instnce of the clamp converter
    GC.setProtocol(blocksel)
    GC.getData()  # convert the data to acq4 Clamp object
    print(GC.tstart, GC.tend)
    IV = IVS.IVSummary(2)
    IV.AR = GC
    IV.compute_iv()
    
    
    
    
    
