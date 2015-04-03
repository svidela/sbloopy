from zope import component
from pyzcasp import asp, potassco

from caspo import core

from DB import iDB, rDB
from Workflow import Workflow

if __name__ == "__main__":
    potassco.configure(clingo="clingo-4.3.0")

    pkn = "out/pkn.sif"
    midas = "out/dataset.csv"
    
    sif = component.getUtility(core.IFileReader)
    sif.read(pkn)
    graph = core.IGraph(sif)
    
    reader = component.getUtility(core.ICsvReader)
    reader.read(midas)
    dataset = core.IDataset(reader)
        
    reg = component.getUtility(asp.IArgumentRegistry)
    reg.register('caspo.learn.opt',  ["--quiet=1", "--conf=many", "-t 4"],              potassco.IClasp3)
    reg.register('caspo.learn.enum', ["--opt-mode=ignore", "0", "--conf=many", "-t 4"], potassco.IClasp3)
    
    db = iDB('insilico', dataset.setup)
    db.create_db()
    db.load_pkn(graph, 4)
    db.generate_benchmarks(1, (30,32), (2,3), 2)
    
    workflow = Workflow(db, graph, dict(max_stimuli=3, max_inhibitors=2, max_experiments=5))
    workflow.run(1)
