'''
Created on May 17, 2015

@author: brian
'''

import os
from base64 import encodestring
from IPython.nbformat import current as nb
 
from traits.api import HasTraits, Str, Undefined

class JupyterNotebookWriter(HasTraits):
    
    """
    see https://github.com/jupyter/nbformat/blob/master/nbformat/v4/tests/nbexamples.py
    for examples of writing notebook cells
    
    design: 
     - add a writer function generator to the op and view plugins
     - dynamically associate with the returned op and view instances
     - iterate over the workflow:
         - Include name and id in markdown cells
         - for each workflow item, make one cell with the operation's
           execution
         - for each view in the workflow item, make one cell with the
           view's parameterization, execution and output
    """
    
    file_name = Str
    
    def export(self, workflow):
        notebook = nb.new_notebook()

        setup_code = "%matplotlib notebook\n"
        setup_code += "import cytoflow as flow"

        cells = [nb.new_code_cell(setup_code)]

        for i, item in enumerate(workflow):

            op_name = "op%d" % i
            code = item.operation.code(op_name)
            cells.append(nb.new_code_cell(code))

            last_ex_name = ""
            if i > 0:
                last_ex_name = "ex%d" % (i-1)

            code = "ex%d = %s.apply(%s)" % (i, op_name, last_ex_name)
            cells.append(nb.new_code_cell(code))

            for j, view in enumerate(item.views):
                view_name = "v%d_%d" % (i, j)
                ex_name = "ex%d" % i

                code = view.code(view_name, op_name, ex_name)
                cells.append(nb.new_code_cell(code))

        notebook['worksheets'].append(nb.new_worksheet(cells=cells))
        if not '.ipynb' in self.file_name:
            self.file_name += '.ipynb'
        with open(self.file_name, 'w') as f:
            nb.write(notebook, f, 'ipynb')
