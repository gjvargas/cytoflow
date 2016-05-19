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

"""
Created on Feb 24, 2015

@author: brian
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from traits.api import provides, Callable, Str, Undefined, Delegate
from traitsui.api import View, Item, Controller, EnumEditor, VGroup
from envisage.api import Plugin, contributes_to
from pyface.api import ImageResource

from cytoflow import HistogramView
import cytoflow.utility as util

from cytoflowgui.subset_editor import SubsetEditor
from cytoflowgui.color_text_editor import ColorTextEditor
from cytoflowgui.clearable_enum_editor import ClearableEnumEditor
from cytoflowgui.view_plugins.i_view_plugin \
    import IViewPlugin, VIEW_PLUGIN_EXT, ViewHandlerMixin, PluginViewMixin
    
class HistogramHandler(Controller, ViewHandlerMixin):
    """
    docs
    """
    
    def default_traits_view(self):
        return View(VGroup(
                    VGroup(Item('name'),
                           Item('channel',
                                editor=EnumEditor(name='context.channels'),
                                label = "Channel"),
                           Item('scale'),
                           Item('xfacet',
                                editor=ClearableEnumEditor(name='context.conditions'),
                                label = "Horizontal\nFacet"),
                            Item('yfacet',
                                editor=ClearableEnumEditor(name='context.conditions'),
                                label = "Vertical\nFacet"),
                           Item('huefacet',
                                editor=ClearableEnumEditor(name='context.conditions'),
                                label="Color\nFacet"),
                           Item('plotfacet',
                                editor=ClearableEnumEditor(name='context.conditions'),
                                label = "Tab\nFacet"),
                            label = "Histogram Plot",
                            show_border = False),
                    VGroup(Item('subset',
                                show_label = False,
                                editor = SubsetEditor(conditions_types = "context.conditions_types",
                                                      conditions_values = "context.conditions_values")),
                           label = "Subset",
                           show_border = False,
                           show_labels = False),
                    Item('warning',
                         resizable = True,
                         visible_when = 'warning',
                         editor = ColorTextEditor(foreground_color = "#000000",
                                                 background_color = "#ffff99")),
                    Item('error',
                         resizable = True,
                         visible_when = 'error',
                         editor = ColorTextEditor(foreground_color = "#000000",
                                                  background_color = "#ff9191"))))
    
class HistogramPluginView(HistogramView, PluginViewMixin):
    handler_factory = Callable(HistogramHandler, transient=True)

    def code(self, name, op_name, ex_name):
        output = "%s = " % name
        output += "flow.HistogramView(\n"
        for trait in self.traits():
            t = self.trait(trait)
            if t and not t.transient and not t.is_trait_type(Delegate):
                value = getattr(self, trait)
                if value is not None and value != '' and value is not Undefined:
                    if isinstance(value, basestring):
                        output += "\t%s = '%s',\n" % (trait, value)
                    else:
                        output += "\t%s = %s,\n" % (trait, value)
        output += ")\n"
        output += "%s.plot(%s)" % (name, ex_name)

        return output

    plotfacet = Str

    def enum_plots(self, experiment):
        if not self.plotfacet:
            return iter([])
        
        if self.plotfacet and self.plotfacet not in experiment.conditions:
            raise util.CytoflowViewError("Plot facet {0} not in the experiment"
                                    .format(self.huefacet))
        values = np.sort(pd.unique(experiment[self.plotfacet]))
        return iter(values)
    
    def plot(self, experiment, plot_name = None, **kwargs):
        if self.plotfacet and plot_name is not None:
            experiment = experiment.subset(self.plotfacet, plot_name)

        HistogramView.plot(self, experiment, **kwargs)
        
        if self.plotfacet and plot_name is not None:
            plt.title("{0} = {1}".format(self.plotfacet, plot_name))

@provides(IViewPlugin)
class HistogramPlugin(Plugin):
    """
    classdocs
    """

    id = 'edu.mit.synbio.cytoflowgui.view.histogram'
    view_id = 'edu.mit.synbio.cytoflow.view.histogram'
    short_name = "Histogram"
    
    def get_view(self):
        return HistogramPluginView()
    
    def get_icon(self):
        return ImageResource('histogram')

    @contributes_to(VIEW_PLUGIN_EXT)
    def get_plugin(self):
        return self
