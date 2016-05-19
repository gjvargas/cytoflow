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

from traits.api import provides, Callable
from traits.api import provides, Callable, Undefined, Delegate
from traitsui.api import View, Item, EnumEditor, Controller, VGroup, TextEditor
from envisage.api import Plugin, contributes_to
from pyface.api import ImageResource

from cytoflow.operations.threshold import ThresholdOp, ThresholdSelection

from cytoflowgui.op_plugins.i_op_plugin \
    import IOperationPlugin, OpHandlerMixin, PluginOpMixin, OP_PLUGIN_EXT, shared_op_traits
from cytoflowgui.view_plugins.i_view_plugin import ViewHandlerMixin, PluginViewMixin
from cytoflowgui.subset_editor import SubsetEditor
from cytoflowgui.color_text_editor import ColorTextEditor
from cytoflowgui.clearable_enum_editor import ClearableEnumEditor

class ThresholdHandler(Controller, OpHandlerMixin):
    def default_traits_view(self):
        return View(Item('name',
                         editor = TextEditor(auto_set = False)),
                    Item('channel',
                         editor=EnumEditor(name='context.previous.channels'),
                         label = "Channel"),
                    Item('threshold',
                         editor = TextEditor(auto_set = False)),
                    shared_op_traits) 
        
class ThresholdViewHandler(Controller, ViewHandlerMixin):
    def default_traits_view(self):
        return View(VGroup(
                    VGroup(Item('name',
                                style = "readonly"),
                           Item('channel', 
                                label = "Channel",
                                style = "readonly"),
                           Item('scale'),
                           Item('huefacet',
                                editor=ClearableEnumEditor(name='context.previous.conditions'),
                                label="Color\nFacet"),
                           label = "Range Setup View",
                           show_border = False),
                    VGroup(Item('subset',
                                show_label = False,
                                editor = SubsetEditor(conditions_types = "context.previous.conditions_types",
                                                      conditions_values = "context.previous.conditions_values")),
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

class ThresholdSelectionView(ThresholdSelection, PluginViewMixin):
    handler_factory = Callable(ThresholdViewHandler, transient=True)

    def code(self, name, op_name, ex_name):
        output = "%s = " % name
        output += "flow.operations.threshold.ThresholdSelection(\n"
        for trait in self.traits():
            t = self.trait(trait)
            if t and not t.transient and not t.is_trait_type(Delegate):
                value = getattr(self, trait)
                if value is not None and value != '' and value is not Undefined:
                    if isinstance(value, basestring):
                        output += "\t%s = '%s',\n" % (trait, value)
                    elif isinstance(value, ThresholdOp):
                        output += "\top = %s,\n" % (op_name)
                    else:
                        output += "\t%s = %s,\n" % (trait, value)
        output += ")\n"
        output += "%s.plot(%s)" % (name, ex_name)

        return output
    
    def plot_wi(self, wi):
        self.plot(wi.previous.result)
    
class ThresholdPluginOp(ThresholdOp, PluginOpMixin):
    handler_factory = Callable(ThresholdHandler, transient=True)
     
    def default_view(self, **kwargs):
        return ThresholdSelectionView(op = self, **kwargs)
    
    def code(self, name):
        output = "%s = " % name
        output += "flow.ThresholdOp(\n"
        for trait in self.traits():
            t = self.trait(trait)
            if t and not t.transient:
                value = getattr(self, trait)
                if value is not None and value != '' and value is not Undefined:
                    if isinstance(value, basestring):
                        output += "\t%s = '%s',\n" % (trait, value)
                    else:
                        output += "\t%s = %s,\n" % (trait, value)
        output += ")"

        return output

@provides(IOperationPlugin)
class ThresholdPlugin(Plugin):
    """
    class docs
    """
    
    id = 'edu.mit.synbio.cytoflowgui.op_plugins.threshold'
    operation_id = 'edu.mit.synbio.cytoflow.operations.threshold'

    short_name = "Threshold"
    menu_group = "Gates"
    
    def get_operation(self):
        return ThresholdPluginOp()

    def get_icon(self):
        return ImageResource('threshold')
    
    @contributes_to(OP_PLUGIN_EXT)
    def get_plugin(self):
        return self
    
