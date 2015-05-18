##
# As its name suggests, this file is just a bunch of useful recipies to do some things after running sbloopy
# It is meant to be used from the python shell or as examples for you own python scripts
##

from zope import component
from caspo import core

from DB import iDB

READER = component.getUtility(core.ICsvReader)
WRITER = component.getUtility(core.ICsvWriter)

INSILICO_MIDAS = 'data/insilico/dataset.csv'
READER.read(INSILICO_MIDAS)
INSILICO_SETUP = core.IDataset(READER).setup

def gold_standards_mse(models):
    """
    For an iterable of gold standard ids, e.g., range(100), it returns pairs like [(idmodel, MSE),...]
    """
    db = iDB('insilico', INSILICO_SETUP)
    
    gold_dataset = map(lambda idmodel: (idmodel, db.get_model(idmodel), db.get_all_dataset(idmodel)), models)
    return [(idmodel, gold.mse(dataset, 1)) for idmodel, gold, dataset in gold_dataset]

def iter_gold_standards_mse(models):
    for idmodel, mse in gold_standards_mse(models):
        yield {'idmodel': idmodel, 'mse': mse}

def write_gold_standards_mse(models, filename):
    """
    For an iterable of gold standard ids, e.g., range(100), it writes a CSV file with their MSEs
    """
    header = ['idmodel', 'mse']
    WRITER.load(iter_gold_standards_mse(models), header)
    WRITER.write(filename)
    
def iter_dataset(dataset, header):
    for i, clamping, obs in dataset.at(1):
        dc = dict(clamping)
        row = dict.fromkeys(header, 0)
        
        for inh in filter(lambda inh: inh in dc, INSILICO_SETUP.inhibitors):
            row['TR:'+inh+'i'] = 1
        
        for sti in filter(lambda sti: dc[sti] == 1, INSILICO_SETUP.stimuli):
            row['TR:'+sti] = 1
            
        for readout in INSILICO_SETUP.readouts:
            row['DA:'+readout] = 1
            row['DV:'+readout] = obs[readout]
            
        yield row
        
def write_midas_file(idmodel, it, filename):
    """
    For a gold standard id and iteration number, it writes the corresponding MIDAS file
    with the experiments used up to the given iteration.
    """
    db = iDB('insilico', INSILICO_SETUP)
    header = ["TR:GoldStandard-%s:CellLine" % idmodel] +\
             map(lambda s: 'TR:' + s, INSILICO_SETUP.stimuli) +\
             map(lambda i: 'TR:'+i+'i', INSILICO_SETUP.inhibitors) +\
             map(lambda r: 'DA:'+r, INSILICO_SETUP.readouts) +\
             map(lambda r: 'DV:'+r, INSILICO_SETUP.readouts)
             
    dataset = db.get_benchmarking_data(idmodel, it)
    
    WRITER.load(iter_dataset(dataset, header), header)
    WRITER.write(filename)
    
