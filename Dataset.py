import math
import random
from collections import defaultdict

from caspo import core
from zope import component, interface

class Dataset(object):
    """
    Dataset class as required by caspo.
    
    Use Dataset.from_db_rows to create a Dataset instance from a sqlite query
    """
    interface.implements(core.IDataset, core.IClampingList)
    
    def __init__(self, setup, cues, obs, nobs, times):
        self.setup = setup
        self.cues = cues
        self.obs = obs
        self.nobs = nobs
        self.times = times
        self.nexps = len(self.cues)
        
    @classmethod
    def from_db_rows(cls, rows, setup):
        cues = []
        obs = []
        nobs = defaultdict(int)
        times = frozenset([1])
        
        for row in rows:
            literals = []
            for s in setup.stimuli:
                if row[s] == 1:
                    literals.append(core.Literal(s,1))
                else:
                    literals.append(core.Literal(s,-1))
        
            for i in setup.inhibitors:
                if row[i + 'i'] == 1:
                    literals.append(core.Literal(i,-1))

            clamping = core.Clamping(literals)
            o = defaultdict(dict)
            for r in setup.readouts:
                if not math.isnan(float(row[r])):
                    o[1][r] = float(row[r])
                    nobs[1] += 1
        
            if clamping in cues:
                index = cues.index(clamping)
                obs[index].update(o)
            else:
                cues.append(clamping)
                obs.append(o)
        
        return cls(setup, cues, obs, nobs, times)

    @property
    def clampings(self):
        return self.cues

    def at(self, time):
        if time not in self.times:
            raise ValueError("The time-point %s does not exists in the dataset. Available time-points are: %s" % (time, list(self.times)))
                      
        for i, (cues, obs) in enumerate(zip(self.cues, self.obs)):
            yield i, cues, obs[time]

    def add(self, exps):
        for cues, obs in exps:
            self.cues.append(cues)
            self.obs.append(obs)
            
            self.nexps += 1
            for t in self.times:
                self.nobs[t] += len(obs[t])

    def pop_sample(self, n):
        exps = []
        for _ in xrange(n):
            i = random.randint(0, self.nexps - 1)
            
            self.nexps -= 1
            for t in self.times:
                self.nobs[t] -= len(self.obs[i][t])
            
            exps.append((self.cues.pop(i), self.obs.pop(i)))
            
        return exps
        