#!/usr/bin/env python2.7

# (c) Massachusetts Institute of Technology 2015-2016
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import division, absolute_import

from traits.api import (HasStrictTraits, Str, CStr, CFloat, File, Dict,
                        Instance, List, Constant, provides)
                       
import numpy as np

import cytoflow.views
import cytoflow.utility as util

from .i_operation import IOperation
from .import_op import Tube, ImportOp, check_tube, parse_tube

@provides(IOperation)
class AutofluorescenceOp(HasStrictTraits):
    """
    Apply autofluorescence correction to a set of fluorescence channels.
    
    The `estimate()` function loads a separate FCS file (not part of the input
    `Experiment`) and computes the untransformed median and standard deviation 
    of the blank cells.  Then, `apply()` subtracts the median from the 
    experiment data.
    
    To use, set the `blank_file` property to point to an FCS file with
    unstained or nonfluorescing cells in it; set the `channels` property to a 
    list of channels to correct; and call `estimate()`, then `apply()`.
    
    `apply()` also adds the "af_median" and "af_stdev" metadata to the corrected
    channels, representing the median and standard deviation of the measured 
    blank distributions.  Some other modules (especially in the TASBE workflow)
    depend on this metadata and will fail if it's not present.
    
    Attributes
    ----------
    name : Str
        The operation name (for UI representation; optional for interactive use)
        
    channels : List(Str)
        The channels to correct.
        
    blank_file : File
        The filename of a file with "blank" cells (not fluorescent).  Used
        to `estimate()` the autofluorescence.
        
    Examples
    --------
    >>> af_op = flow.AutofluorescenceOp()
    >>> af_op.blank_file = "blank.fcs"
    >>> af_op.channels = ["Pacific Blue-A", "FITC-A", "PE-Tx-Red-YG-A"] 

    >>> af_op.estimate(ex)
    >>> af_op.default_view().plot()
    >>> ex2 = af_op.apply(ex)
    """
    
    # traits
    id = Constant('edu.mit.synbio.cytoflow.operations.autofluorescence')
    friendly_id = Constant("Autofluorescence correction")
    
    name = CStr()
    channels = List(Str)
    blank_file = File(filter = "*.fcs", exists = True, transient = True)

    _af_median = Dict(Str, CFloat)
    _af_stdev = Dict(Str, CFloat)
    
    def estimate(self, experiment, subset = None): 
        """
        Estimate the autofluorescence from *blank_file*
        """
        if not experiment:
            raise util.CytoflowOpError("No experiment specified")

        if not set(self.channels) <= set(experiment.channels):
            raise util.CytoflowOpError("Specified channels that weren't found in "
                                  "the experiment.")

        # don't have to validate that blank_file exists; should crap out on 
        # trying to set a bad value
        
        # make a little Experiment
        check_tube(self.blank_file, experiment)
        blank_exp = ImportOp(tubes = [Tube(file = self.blank_file)]).apply()
        
        # apply previous operations
        for op in experiment.history:
            blank_exp = op.apply(blank_exp)
            
        # subset it
        if subset:
            try:
                blank_data = blank_exp.query(subset)
            except:
                raise util.CytoflowOpError("Subset string '{0}' isn't valid"
                                      .format(self.subset))
                            
            if len(blank_data.index) == 0:
                raise util.CytoflowOpError("Subset string '{0}' returned no events"
                                      .format(self.subset))
        else:
            blank_data = blank_exp.data
        
        for channel in self.channels:
            self._af_median[channel] = np.median(blank_data[channel])
            self._af_stdev[channel] = np.std(blank_data[channel])    
                
    def apply(self, experiment):
        """Applies the threshold to an experiment.
        
        Parameters
        ----------
        experiment : Experiment
            the old_experiment to which this op is applied
            
        Returns
        -------
            a new experiment with the autofluorescence median subtracted from
            the values in self.blank_file
        """
        if not experiment:
            raise util.CytoflowOpError("No experiment specified")
        
        if not set(self._af_median.keys()) <= set(experiment.channels) or \
           not set(self._af_stdev.keys()) <= set(experiment.channels):
            raise util.CytoflowOpError("Autofluorescence estimates aren't set, or are "
                               "different than those in the experiment "
                               "parameter. Did you forget to run estimate()?")

        if not set(self._af_median.keys()) == set(self._af_stdev.keys()):
            raise util.CytoflowOpError("Median and stdev keys are different! "
                                  "What the hell happened?!")
        
        if not set(self.channels) == set(self._af_median.keys()):
            raise util.CytoflowOpError("Estimated channels differ from the channels "
                               "parameter.  Did you forget to (re)run estimate()?")
        
        new_experiment = experiment.clone()
                
        for channel in self.channels:
            new_experiment[channel] = \
                experiment[channel] - self._af_median[channel]

        new_experiment.history.append(self.clone_traits())
        return new_experiment
    
    def default_view(self, **kwargs):
        return AutofluorescenceDiagnosticView(op = self, **kwargs)
    
    
@provides(cytoflow.views.IView)
class AutofluorescenceDiagnosticView(HasStrictTraits):
    """
    Plots a histogram of each channel, and its median in red.  Serves as a
    diagnostic for the autofluorescence correction.
    
    
    Attributes
    ----------
    name : Str
        The instance name (for serialization, UI etc.)
    
    op : Instance(AutofluorescenceOp)
        The op whose parameters we're viewing
        
    """
    
    # traits   
    id = Constant('edu.mit.synbio.cytoflow.view.autofluorescencediagnosticview')
    friendly_id = Constant("Autofluorescence Diagnostic")
    
    name = Str
    op = Instance(IOperation)
    
    def plot(self, experiment, **kwargs):
        """Plot a faceted histogram view of a channel"""
        
        import matplotlib.pyplot as plt
        import seaborn as sns  # @UnusedImport
        
        kwargs.setdefault('histtype', 'stepfilled')
        kwargs.setdefault('alpha', 0.5)
        kwargs.setdefault('antialiased', True)
           
        blank_data = parse_tube(self.op.blank_file, experiment)

        plt.figure()
        
        for idx, channel in enumerate(self.op.channels):
            d = blank_data[channel]
            plt.subplot(len(self.op.channels), 1, idx+1)
            plt.title(channel)
            plt.hist(d, bins = 200, **kwargs)
            
            plt.axvline(self.op._af_median[channel], color = 'r')
