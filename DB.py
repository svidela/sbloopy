import sqlite3 as lite

import numpy as np
import random
from collections import defaultdict

from pyzcasp import asp, potassco
from caspo import core, learn, visualize
from zope import component

from Dataset import Dataset

class DB(object):
    """
    Database class to access sqlite database
    """
    
    def __init__(self, name, setup):
        self.name = name
        self.setup = setup
        
    def get_data_header(self, it=False):
        header_in = self.setup.stimuli \
               + map(lambda i: i+'i', self.setup.inhibitors)
           
        header_out = self.setup.readouts
        cols = ""
        for c in header_in:
            cols += "%s INT, " % c
        
        for c in header_out:
            cols += "%s REAL, " % c
        if not it:
            return cols + "idmodel INT, FOREIGN KEY(idmodel) REFERENCES model(id)"
        else:
            return cols + "idmodel INT, it INT, FOREIGN KEY(idmodel) REFERENCES model(id)"

    def create_db(self):
        """
        Create common DB tables.
        """
        con = lite.connect(self.name)
        names = component.getUtility(core.ILogicalNames)
    
        with con:
            cur = con.cursor()
            cur.execute("DROP TABLE IF EXISTS pkn")
            cur.execute("CREATE TABLE pkn (id INTEGER PRIMARY KEY, hyper TEXT)")
            
            cur.execute("DROP TABLE IF EXISTS dataset")
            cur.execute("CREATE TABLE dataset (%s)" % self.get_data_header())
        
            cur.execute("DROP TABLE IF EXISTS benchmark_iterations")
            cur.execute("CREATE TABLE benchmark_iterations (idmodel INT, it INT, FOREIGN KEY(idmodel) REFERENCES model(id))")
        
            cur.execute("DROP TABLE IF EXISTS benchmark_data")
            cur.execute("CREATE TABLE benchmark_data (%s)" % self.get_data_header(True))
        
            cur.execute("DROP TABLE IF EXISTS benchmark_mse")
            cur.execute("CREATE TABLE benchmark_mse (idmodel INT, it INT, training REAL, testing REAL, \
                FOREIGN KEY(idmodel) REFERENCES model(id))")
                
            cur.execute("DROP TABLE IF EXISTS benchmark_behaviors")
            cur.execute("CREATE TABLE benchmark_behaviors (idmodel INT, it INT, fit REAL, size INT, networks INT, behaviors INT, FOREIGN KEY(idmodel) REFERENCES model(id))")

    def load_pkn(self, pkn, length):
        pkn = component.getMultiAdapter((pkn, self.setup), core.IGraph)
    
        names = component.getUtility(core.ILogicalNames)
        names.load(pkn, length)
        
        con = lite.connect(self.name)
        with con:
            cur = con.cursor()
            for var in names.variables:
                for i, clause in names.iterclauses(var):
                    cur.execute("""INSERT INTO pkn (hyper) VALUES ("%s=%s")""" % (clause, var))

    def get_all_dataset(self, idmodel):
        con = lite.connect(self.name)

        with con:
            con.row_factory = lite.Row
            cur = con.cursor()
            cur.execute("SELECT * FROM dataset where idmodel=:idmodel", {'idmodel': idmodel})
                    
            rows = cur.fetchall()
            dataset = Dataset.from_db_rows(rows, self.setup)
            
        return dataset   

    def init(self, idmodel):
        """
        Initialize benchmarking
        """
        con = lite.connect(self.name)
                
        with con:
            cur = con.cursor()
            cur.execute("INSERT INTO benchmark_iterations (idmodel, it) VALUES (%s,0)" % idmodel)
            
    def get_benchmarking_data(self, idmodel, it=-1):
        """
        Returns a Dataset instance with the data used for learning up to iteration it
        """
        con = lite.connect(self.name)
        
        cues = []
        obs = []
        nobs = defaultdict(int)
        
        with con:
            con.row_factory = lite.Row
            cur = con.cursor()
            if it < 0:
                cur.execute("SELECT * FROM benchmark_data WHERE idmodel=:idmodel", {'idmodel': idmodel})
            else:
                cur.execute("SELECT * FROM benchmark_data WHERE idmodel=:idmodel AND it<=:it", {'idmodel': idmodel, 'it': it})
        
            rows = cur.fetchall()
            dataset = Dataset.from_db_rows(rows, self.setup)
    
        return dataset

    def insert_benchmarking_data(self, idmodel, clampings, it):
        """
        Move experiments (clampings + observations) from dataset table to benchmark_data table
        """
        
        con = lite.connect(self.name)
    
        with con:
            cur = con.cursor()
            for clamping in clampings:
                where, inputs = self.get_where(idmodel, clamping)
                cur.execute("INSERT INTO benchmark_data SELECT *, %s as it FROM dataset \
                    WHERE %s" % (it, where), inputs)

    def get_where(self, idmodel, clamping):
        inputs = {'idmodel': idmodel}
        
        dc = dict(clamping)
        for s in self.setup.stimuli:
            if dc[s] == 1:
                inputs[s] = 1
            else:
                inputs[s] = 0
        
        for i in self.setup.inhibitors:
            if i in dc:
                inputs[i+'i'] = 1
            else:
                inputs[i+'i'] = 0
        
        header = self.setup.stimuli \
               + map(lambda i: i+'i', self.setup.inhibitors)

        where = ""
        for h in header:
            where += "%s=:%s AND " % (h,h)
        
        where += "idmodel=:idmodel"
    
        return where, inputs
        
    def check_clampings(self, idmodel, clampings):
        """
        Filter experiments already in benchmark_data table
        """
        con = lite.connect(self.name)
        
        new_clampings = []
        with con:
            cur = con.cursor()
            for c in clampings:
                where, inputs = self.get_where(idmodel, c)
                cur.execute("SELECT * FROM benchmark_data WHERE %s" % where, inputs)
                row = cur.fetchone()
                if not row:
                    new_clampings.append(c)
    
        return new_clampings
        
    def insert_mse(self, idmodel, it, learning, testing):
        con = lite.connect(self.name)
        
        with con:
            cur = con.cursor()
            cur.execute("INSERT INTO benchmark_mse (idmodel,it,training,testing) \
                VALUES (%s,%s,%s,%s)" % (idmodel,it,learning,testing))
                
    def insert_last_it(self, idmodel, it):
        con = lite.connect(self.name)

        with con:
            cur = con.cursor()
            cur.execute("UPDATE benchmark_iterations SET it=:it WHERE idmodel=:idmodel", {'idmodel':idmodel, 'it':it})
            
    def insert_behaviors(self, idmodel, it, fit, size, networks, behaviors):
        con = lite.connect(self.name)

        with con:
            cur = con.cursor()
            cur.execute("INSERT INTO benchmark_behaviors (idmodel, it, fit, size, networks, behaviors) \
                VALUES (%s,%s,%s,%s,%s,%s)" % (idmodel, it, fit, size, networks, behaviors))

class iDB(DB):
    
    def create_db(self):
        super(iDB, self).create_db()

        con = lite.connect(self.name)
        with con:
            cur = con.cursor()
            
            cur.execute("DROP TABLE IF EXISTS model")
            cur.execute("CREATE TABLE model (idmodel INT, idclause INT, FOREIGN KEY(idclause) REFERENCES pkn(id))")
            
            
    def generate_benchmarks(self, n, size, nand, maxin):
        """
        Generate n insilico benchmarks (gold standard and data with noise)
        """
        names = component.getUtility(core.ILogicalNames)
        clingo = component.getUtility(potassco.IClingo)
    
        instance = asp.ITermSet(names).union(asp.ITermSet(self.setup))
        learner = component.getMultiAdapter((instance, clingo), learn.ILearner)
        
        con = lite.connect(self.name)
    
        header = self.setup.stimuli + map(lambda i: i+'i', self.setup.inhibitors) + self.setup.readouts
        
        for i in range(n):
            golden = learner.random(1, size, nand, maxin).pop()
            writer = component.getMultiAdapter((visualize.IMultiDiGraph(golden), self.setup), visualize.IDotWriter)
            writer.write('golden-%s.dot' % i, '.')

            with con:
                con.row_factory = lite.Row
                cur = con.cursor()
                for var, formula in golden.mapping.iteritems():
                    for clause in formula:
                        cur.execute("SELECT * FROM pkn WHERE hyper=:k", {'k': "%s=%s" % (clause, var)})
                        row = cur.fetchone()
                        cur.execute("INSERT INTO model (idmodel, idclause) VALUES (%s,%s)" % (i, row['id']))
                    
                for clamping in self.setup.iterclampings():
                    dc = dict(clamping)
                    row = dict.fromkeys(header, 0)
                    row['idmodel'] = i
                
                    for inh in self.setup.inhibitors:
                        if inh in dc:
                            row[inh + 'i'] = 1
                        
                    for sti in self.setup.stimuli:
                        row[sti] = 1 if dc[sti] == 1 else 0
                    

                    for readout in self.setup.readouts:
                        row[readout] = golden.prediction(readout, clamping)
                        noise = np.random.beta(1,5)
                        if row[readout] == 1:
                            row[readout] -= noise
                        else:
                            row[readout] += noise
                    
                    cols = str(tuple(row.keys()))
                    vals = str(tuple(row.values()))
                    cur.execute("INSERT INTO dataset %s VALUES %s" % (cols, vals))

    def get_model(self, idmodel):
        """
        Returns gold standard with id idmodel
        """
        con = lite.connect(self.name)

        mapping = defaultdict(list)
        with con:
            con.row_factory = lite.Row
            cur = con.cursor()
            cur.execute("SELECT hyper FROM pkn JOIN model ON pkn.id=model.idclause WHERE idmodel=:idmodel", {'idmodel':idmodel})
            rows = cur.fetchall()
    
            for row in rows:
                vc = row['hyper'].split("=")
                mapping[vc[1]].append(core.Clause.from_str(vc[0]))
            
        return core.BooleLogicNetwork(mapping.keys, mapping)   

    def init(self, idmodel):
        """
        Inserts in 'benchmark_dataset' table all experiments with up to 1 stimulus and 1 inhibitor
        """

        super(iDB, self).init(idmodel)
        con = lite.connect(self.name)
                
        with con:
            cur = con.cursor()
            sw = self.setup.stimuli[0]
            for s in self.setup.stimuli[1:]:
                sw += "+" + s
        
            iw = self.setup.inhibitors[0]+'i'
            for i in self.setup.inhibitors[1:]:
                iw += "+" + i+'i'
                    
            cur.execute("INSERT INTO benchmark_data SELECT *, 0 as it  FROM dataset WHERE \
                    idmodel=:idmodel AND %s <= 1 AND %s <= 1" % (sw, iw), {'idmodel': idmodel})
                    
    def get_random_dataset(self, idmodel, nexp, max_stimuli=0, max_inhibitors=0):
        con = lite.connect(self.name)

        with con:    
            sw = self.setup.stimuli[0]
            for s in self.setup.stimuli[1:]:
                sw += "+" + s
        
            iw = self.setup.inhibitors[0]+'i'
            for i in self.setup.inhibitors[1:]:
                iw += "+" + i+'i'
        
            con.row_factory = lite.Row
            cur = con.cursor()
            if max_stimuli > 0 and max_inhibitors > 0:
                cur.execute("SELECT * FROM dataset where idmodel=:idmodel AND \
                    ({sum_inh} <= :mi AND {sum_sti} BETWEEN 2 AND :ms OR {sum_inh} BETWEEN 2 AND :mi)".format(sum_sti=sw, sum_inh=iw), 
                    {'idmodel': idmodel, 'ms': max_stimuli, 'mi': max_inhibitors})
                    
            elif max_stimuli > 0 or max_inhibitors > 0:
                if max_stimuli > 0:
                    cur.execute("SELECT * FROM dataset where idmodel=:idmodel AND \
                                (%s BETWEEN 2 AND :ms OR %s >= 2)" % (sw, iw), 
                                {'idmodel': idmodel, 'ms': max_stimuli})
                else:
                    cur.execute("SELECT * FROM dataset where idmodel=:idmodel AND \
                                (%s >= 2 OR %s BETWEEN 2 AND :mi)" % (sw, iw), 
                                {'idmodel': idmodel, 'mi': max_inhibitors})
                                
            else:
                cur.execute("SELECT * FROM dataset where idmodel=:idmodel AND \
                            (%s > 1 OR %s > 1)" % (sw, iw), {'idmodel': idmodel})
                        
            
            rows = cur.fetchall()
            exps = random.sample(rows, nexp)
            dataset = Dataset.from_db_rows(exps, self.setup)
            
        return dataset

class rDB(DB):
    
    def create_db(self):
        super(rDB, self).create_db()

        cols_data = self.get_data_header()
        con = lite.connect(self.name)
        with con:
            cur = con.cursor()
            cur.execute("DROP TABLE IF EXISTS screening")
            cur.execute("CREATE TABLE screening (%s)" % cols_data)

    def init(self, idmodel=0):
        """
        Inserts in 'benchmark_dataset' table all experiments from 'screening' table
        """

        super(rDB, self).init(idmodel)
        con = lite.connect(self.name)
                
        with con:
            cur = con.cursor()
            cur.execute("INSERT INTO benchmark_data SELECT *, 0 as it  FROM screening WHERE \
                    idmodel=:idmodel", {'idmodel': idmodel})

    def insert_data(self, idmodel, screening, stime, followup, ftime):
        """
        Insert screening dataset into screening table and followup dataset into dataset table
        """
        con = lite.connect(self.name)

        header = self.setup.stimuli + map(lambda i: i+'i', self.setup.inhibitors) + self.setup.readouts
        
        with con:
            cur = con.cursor()
                
            for i, clamping, obs in followup.at(ftime):
                dc = dict(clamping)
                row = dict.fromkeys(header, 0)
                row['idmodel'] = idmodel
            
                for inh in self.setup.inhibitors:
                    if inh in dc:
                        row[inh + 'i'] = 1
                    
                for sti in self.setup.stimuli:
                    row[sti] = 1 if dc[sti] == 1 else 0
                
                for readout in self.setup.readouts:
                    if readout in obs.keys():
                        row[readout] = obs[readout]
                    else:
                        row[readout] = "NaN"
                
                cols = str(tuple(row.keys()))
                vals = str(tuple(row.values()))
                cur.execute("INSERT INTO dataset %s VALUES %s" % (cols, vals))
                
            for i, clamping, obs in screening.at(stime):
                dc = dict(clamping)
                
                ex = [k for k in dc if k not in self.setup.stimuli and dc[k] == 1]
                if not ex:
                    row = dict.fromkeys(header, 0)
                    row['idmodel'] = idmodel
            
                    for inh in self.setup.inhibitors:
                        if inh in dc:
                            row[inh + 'i'] = 1
                    
                    for sti in self.setup.stimuli:
                        row[sti] = 1 if dc[sti] == 1 else 0
                
                    for readout in self.setup.readouts:
                        if readout in obs.keys():
                            row[readout] = obs[readout]
                        else:
                            row[readout] = "NaN"
                
                    cols = str(tuple(row.keys()))
                    vals = str(tuple(row.values()))
                    cur.execute("INSERT INTO screening %s VALUES %s" % (cols, vals))
                    