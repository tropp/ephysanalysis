#!/usr/bin/env python

# Use Semantic Versioning, http://semver.org/
version_info = (0, 2, 2, 'a')
__version__ = "%d.%d.%d%s" % version_info

#print ("apparent version: ", __version__)

import ephysanalysis.Fitting as Fitting
import ephysanalysis.Utility as Utility

import ephysanalysis.acq4read
import ephysanalysis.MatdatacRead
import ephysanalysis.DatacReader
import ephysanalysis.DataPlan
import ephysanalysis.getcomputer
import ephysanalysis.RmTauAnalysis
import ephysanalysis.SpikeAnalysis
import ephysanalysis.dataSummary
import ephysanalysis.IVSummary
import ephysanalysis.VCSummary
import ephysanalysis.boundrect
import ephysanalysis.poisson_score
import ephysanalysis.bridge
import ephysanalysis.MakeClamps

import ephysanalysis.metaarray as MetaArray


