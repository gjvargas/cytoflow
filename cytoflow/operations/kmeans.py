from traits.api import HasStrictTraits, Str, CStr, List, Float, provides, \
    Instance, Bool, on_trait_change, DelegatesTo, Any, Constant, Int
from cytoflow.operations import IOperation
from cytoflow.utility import CytoflowOpError, CytoflowViewError
from cytoflow.views import ISelectionView
from cytoflow.views.scatterplot import ScatterplotView

from matplotlib.widgets import Cursor
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import seaborn as sns
import numpy as np
import pandas as pd

import scipy.cluster.vq


#TODO clean imports
#TODO make examples
#TODO write comments
#TODO check style

@provides(IOperation)
class KMeansOp(HasStrictTraits):
    """Group cytometry experiment data into clusters using K-Means.
    
    Attributes
    ----------
    name : Str
        The operation name.  Used to name the new metadata field in the
        experiment that's created by apply()
        
    xchannel : Str
        The name of the first channel in the clustering space.
        
    ychannel : Str
        The name of the second channel in the clustering space.
        
    initial_centroids : Str
        The first guess at optimal centroid location. Used as a
        starting point for the kmeans algorithm.

    Examples
    --------
    
    >>> kmeans = flow.KMeansOp(xchannel = "V2-A",
    ...                           ychannel = "Y2-A")
    >>> ex3 = kmeans.apply(ex2)

    Alternately, in an IPython notebook with `%matplotlib notebook`
    
    >>> kv = kmans.default_view()
    >>> kv.plot(ex2)
    >>> ### click to add centroids for clustering ###
    """
    
    # traits
    id = Constant('edu.mit.synbio.cytoflow.operations.kmeans')
    friendly_id = Constant("K-Means")
    
    name = CStr()
    xchannel = Str()
    ychannel = Str()
    initial_centroids = Any() # Not sure how to do this the right way yet.
    huefacet = Str()

    def apply(self, experiment):
        """Applies the K-Means algorithm to an experiment.
        
        Parameters
        ----------
        experiment : Experiment
            the old_experiment to which this op is applied
            
        Returns
        -------
            a new experiment, the same as old_experiment but with a new
            column the same as the operation name.  The column includes
            integer labels for each data point. The labels represent the
            clusters that the points belong to.
        """
        
        # make sure name got set!
        if not self.name:
            raise CytoflowOpError("You have to set the classifiers's name "
                                  "before applying it!")

        # We want the new column to be the huefacet so we can see clusters.
        self.huefacet = self.name
        
        if not self.xchannel or not self.ychannel:
            raise CytoflowOpError("Must specify xchannel and ychannel")

        if not self.xchannel in experiment.data:
            raise CytoflowOpError("xchannel isn't in the experiment")
        
        if not self.ychannel in experiment.data:
            raise CytoflowOpError("ychannel isn't in the experiment")

        # make sure each centroid guess only has 2 dimensions
        if any([len(x) != 2 for x in self.initial_centroids]):
            return CytoflowOpError("All initial centroids must contain exactly 2 dimensions.") 
        
        # Get relevant experiment data
        new_experiment = experiment.clone()
        channels = [self.xchannel, self.ychannel]
        clustering_data = new_experiment.data[channels]

        # Add initial centroids to data set
        centroids = pd.DataFrame(self.initial_centroids,  columns=channels)
        clustering_data = clustering_data.append(centroids, ignore_index=True)

        # Run kmeans and add results as new column
        whitened = scipy.cluster.vq.whiten(clustering_data)
        whitened_initial_centroids = whitened[-len(self.initial_centroids):]
        centroids, labels = scipy.cluster.vq.kmeans2(whitened, whitened_initial_centroids, iter=100)
        new_experiment[self.name] = labels[:len(new_experiment.data)]
        new_experiment.metadata[self.name] = {'type' : 'int'}

        return new_experiment
    
    def default_view(self):
        return KMeans(op = self)
    
@provides(ISelectionView)
class KMeans(ScatterplotView):
    """
    Plots, and lets the user interact with KMeans by creating 
    and removing centroids
    
    Attributes
    ----------
    op : Instance(KMeansOp)
        The instance of KMeans that we're viewing / editing
        
    huefacet : Str
        The conditioning variable to plot multiple colors
        (This should be the kmeans column name)
        
    interactive : Bool
        is this view interactive?  Ie, can the user set min and max
        with a mouse drag?
        
    Notes
    -----
    We inherit `huefacest` from `cytoflow.views.ScatterplotView`, but need
    it to be the operation name for proper visualization.
        
    Examples
    --------
    
    In an IPython notebook with `%matplotlib notebook`
    
    >>> k = flow.KMeansOp(name = "KMeans",
    ...                    xchannel = "V2-A",
    ...                    ychannel = "Y2-A"))
    >>> kv = k.default_view()
    >>> kv.interactive = True
    >>> kv.plot(ex2) 
    """
    
    id = Constant('edu.mit.synbio.cytoflow.views.kmeans')
    friendly_id = Constant("K-Means Clustering")
    
    op = Instance(IOperation)
    name = DelegatesTo('op')
    xchannel = DelegatesTo('op')
    ychannel = DelegatesTo('op')
    huefacet = DelegatesTo('op')
    interactive = Bool(False, transient = True)
    
    # internal state.
    _ax = Any(transient = True)
    _cursor = Instance(Cursor, transient = True)
    _experiment = Any()
        
    def plot(self, experiment, **kwargs):
        """Plot the underlying scatterplot and then add cursor for centroid addition."""
        
        if not experiment:
            raise CytoflowViewError("No experiment specified")

        super(KMeans, self).plot(experiment)
        self._experiment = experiment
        self._ax = plt.gca()
        self._interactive()

    @on_trait_change('interactive', post_init = True)
    def _interactive(self):
        if self._ax and self.interactive:
            self._cursor = Cursor(self._ax, horizOn = False, vertOn = False)            
            self._cursor.connect_event('button_press_event', self._onclick)
        elif self._cursor:
            self._cursor.disconnect_events()
            self._cursor = None       

    def _onclick(self, event): 
        """Update selection traits"""      
        if not self._ax:
            return
        
        if(self._cursor.ignore(event)):
            return
        
        if self.op.initial_centroids is not None:
            self.op.initial_centroids = np.concatenate((self.op.initial_centroids,
                                      np.array((event.xdata, event.ydata), ndmin = 2)))
        else:
            self.op.initial_centroids = np.array((event.xdata, event.ydata), ndmin = 2)

        temp_experiment = self._experiment.clone()

        try:
            temp_experiment = self.op.apply(temp_experiment)
        except CytoflowOpError as e:
            raise CytoflowViewError(e.__str__())

        data = temp_experiment.data
        xs = []
        ys = []

        plots = {}
        for index, row in data.iterrows():
            xs.append(row[self.xchannel])
            ys.append(row[self.ychannel])

        # Reconstruct plot
        kwargs = {}
        kwargs.setdefault('alpha', 0.25)
        kwargs.setdefault('s', 2)
        kwargs.setdefault('marker', 'o')
        kwargs.setdefault('antialiased', True)
        self._ax.collections = []
        self._ax.scatter(xs, ys, c='r', **kwargs) # This should be changed to plot by cluster/color

if __name__ == '__main__':
    import cytoflow as flow
    import fcsparser
    
    tube1 = flow.Tube(file='../../cytoflow/tests/data/Plate01/RFP_Well_A3.fcs', conditions = {"Dox" : 10.0})
    tube2 = flow.Tube(file='../../cytoflow/tests/data/Plate01/CFP_Well_A4.fcs', conditions = {"Dox" : 1.0})

    import_op = flow.ImportOp(conditions = {"Dox" : "log"},
                              tubes = [tube1, tube2])

    ex = import_op.apply()

    logicle = flow.LogicleTransformOp()
    logicle.name = "Logicle transformation"
    logicle.channels = ['V2-A', 'Y2-A', 'B1-A']
    logicle.estimate(ex)
    ex2 = logicle.apply(ex)

    k = flow.KMeansOp(name = "Kmeans",
            xchannel = "V2-A",
            ychannel = "Y2-A")
    kv = k.default_view()
    kv.plot(ex2)
    kv.interactive = True

    plt.show()
