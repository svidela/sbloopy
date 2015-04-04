import logging

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
        
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        self.logger.addHandler(fh)
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
                
    def run(self, nb=1):
        
        for idmodel in range(nb):
            self.it = -1
            self.logger.info("Benchmark %s" % idmodel)
            
            all_data = self.db.get_all_dataset(idmodel)
            self.db.init(idmodel)
        
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
                self.db.insert_mse(idmodel, self.it, learning, testing)

                if len(behaviors) == 1:
                    while len(behaviors) == 1 and size < 5:
                        size += 1
                        self.logger.info("\tLearning with %s size tolerance" % size)
                        networks = learner.learn(0, size)
                        self.logger.info("\tAnalyzing %s networks" % len(networks))
                        behaviors =  analyze.behaviors(networks, all_data, potassco.IClingo)

                    if len(behaviors) == 1:
                        size = 0
                        while len(behaviors) == 1 and fit < 0.05:
                            fit += 0.01
                            self.logger.info("\tLearning with %s fitness tolerance" % fit)
                            networks = learner.learn(fit, 0)
                            self.logger.info("\tAnalyzing %s networks" % len(networks))
                            behaviors =  analyze.behaviors(networks, all_data, potassco.IClingo)
            
                if len(behaviors) > 1:
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
                else:
                    done = True
            
            self.db.insert_last_it(idmodel, self.it)
