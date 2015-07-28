import logging
import gc
from numpy import random

from zope import component
from pyzcasp import potassco
from caspo import core, learn, analyze, design

class Workflow(object):
    
    def __init__(self, db, pkn, land, dconf, mexps=80, lexps=False):
        self.db = db
        self.pkn = pkn
        self.land = land
        self.dconf = dconf
        self.mexps = mexps
        self.lexps = lexps
        
        self.logger = logging.getLogger("workflow-%s" % self.db.name)
        self.logger.setLevel(logging.INFO)
        
        fh = logging.FileHandler('workflow-%s.log' % self.db.name, 'w')
        fh.setLevel(logging.INFO)
        self.logger.addHandler(fh)
        
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        self.logger.addHandler(ch)
    
    def perform_experiments(self, idmodel, data, exps):
        random.shuffle(exps)
        while exps:
            optdesign = exps.pop()
            nexps = self.db.check_clampings(idmodel, optdesign.clampings)
            ne = len(nexps)
            if ne > 0:
                if ne + data.nexps <= self.mexps:
                    self.logger.info("\t%s experiment(s) added to the dataset" % ne)
                    self.db.insert_benchmarking_data(idmodel, nexps, self.it+1)
                    return False
                else:
                    self.logger.info("\tNumber of allowed experiments reached")
                    return True

            elif not exps:
                self.logger.info("\tAll optimal experimental designs were performed already")
                return True
                
    def run(self, nb=1, resume=False):
        last = -1
        for idmodel in range(nb):
            if resume:
                last = self.db.get_last_it(idmodel)
                self.it = last - 1
            else:
                self.it = -1
                self.db.init(idmodel)
                
            self.logger.info("Benchmark %s" % idmodel)
            all_data = self.db.get_all_dataset(idmodel)
        
            done = False
            while not done:
                self.it += 1
                self.logger.info("Iteration %s" % self.it)
                data = self.db.get_benchmarking_data(idmodel)

                fit = 0
                size = 0
                self.logger.info("\tLearning without tolerance")
                learner = learn.learner(self.pkn, data, 1, self.land, potassco.IClingo, "round", 100)
                networks = learner.learn(fit,size)
                self.logger.info("\tAnalyzing %s networks" % len(networks))
                behaviors =  analyze.behaviors(networks, all_data, potassco.IClingo)

                learning = behaviors.mse(data, 1)
                testing = behaviors.mse(all_data, 1)
                
                if last < self.it:
                    self.db.insert_mse(idmodel, self.it, learning, testing)

                if len(behaviors) == 1:
                    while len(behaviors) == 1 and size < 5:
                        try:
                            size += 1
                            self.logger.info("\tLearning with %s size tolerance" % size)
                            networks = learner.learn(0, size)
                            self.logger.info("\tAnalyzing %s networks" % len(networks))    
                            behaviors =  analyze.behaviors(networks, all_data, potassco.IClingo)
                        except OSError as e:
                            self.logger.info("\t%s" % str(e))
                            networks = None
                            gc.collect()
                            break

                    if len(behaviors) == 1:
                        size = 0
                        while len(behaviors) == 1 and fit < 0.05:
                            try:
                                fit += 0.01
                                self.logger.info("\tLearning with %s fitness tolerance" % fit)
                                networks = learner.learn(fit, 0)
                                self.logger.info("\tAnalyzing %s networks" % len(networks))
                                behaviors =  analyze.behaviors(networks, all_data, potassco.IClingo)
                            except OSError as e:
                                self.logger.info("\t%s" % str(e))
                                networks = None
                                gc.collect()
                                break
            
                if len(behaviors) > 1:
                    try:
                        self.db.insert_behaviors(idmodel, self.it, fit, size, len(networks), len(behaviors))
            
                        designer = design.designer(behaviors, all_data.setup, self.lexps, potassco.IClingo)
                        self.logger.info("\tDiscriminating %s behaviors" % len(behaviors))                            
                        exps = designer.design(**self.dconf)
            
                        if exps:
                            self.logger.info("\t%s optimal experimental design(s)" % len(exps))
                            done = self.perform_experiments(idmodel, data, exps)
                        else:
                            self.logger.info("\tCannot discriminate all behaviors pairwise")
                            exps = designer.design(relax=1, **self.dconf)
                            if exps:
                                self.logger.info("\t%s optimal experimental design(s)" % len(exps))
                                done = self.perform_experiments(idmodel, data, exps)
                            else:
                                self.logger.info("\tCannot generate any difference among given behaviors")
                                done = True
                    except OSError as e:
                        self.logger.info("\t%s" % str(e))
                        networks = None
                        behaviors = None
                        gc.collect()
                        done = True
                else:
                    done = True
            
            self.db.insert_last_it(idmodel, self.it)
            
    def run_random(self, n, idmodel, step):
        all_data = self.db.get_all_dataset(idmodel)
        
        runs_mse = []
        runs_io = []
        for i in xrange(n):
            self.logger.info("Random run %s" % i)
            
            dataset = self.db.get_benchmarking_data(idmodel, it=0)        
            rand_dataset = self.db.get_random_dataset(idmodel, self.mexps - dataset.nexps, **self.dconf)

            mse = {}
            io = {}
            err = False
            while dataset.nexps < self.mexps:
                try:
                    sample = min(step, self.mexps - dataset.nexps)
                    dataset.add(rand_dataset.pop_sample(sample))
    
                    self.logger.info("\tLearning without tolerance using %s experiments" % dataset.nexps)
                    learner = learn.learner(self.pkn, dataset, 1, self.land, potassco.IClingo, "round", 100)
                    networks = learner.learn(0,0)
                
                    self.logger.info("\tAnalyzing %s networks" % len(networks))
                    behaviors =  analyze.behaviors(networks, all_data, potassco.IClingo)

                    mse[dataset.nexps] = behaviors.mse(all_data, 1)
                    io[dataset.nexps] = len(behaviors)
                    self.logger.info("\tTesting MSE equals %s - %s behaviors" % (mse[dataset.nexps],io[dataset.nexps]))
                    
                except OSError as e:
                    self.logger.info("\t%s" % str(e))
                    err = True
                    networks = None
                    behaviors = None
                    gc.collect()
                    break
            
            if not err:
                runs_mse.append(mse)
                runs_io.append(io)
        
        if runs_mse and runs_io:
            writer = component.getUtility(core.ICsvWriter)
            writer.load(runs_mse, runs_mse[0].keys())
            writer.write("mse-random-%s-%s-%s.csv" % (self.db.name, idmodel, n), ".")
        
            writer.load(runs_io, runs_io[0].keys())
            writer.write("behaviors-random-%s-%s-%s.csv" % (self.db.name, idmodel, n), ".")
