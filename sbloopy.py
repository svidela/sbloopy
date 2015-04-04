import os, sys, argparse

from zope import component
from pyzcasp import asp, potassco

from caspo import core

from DB import iDB, rDB
from Workflow import Workflow

if __name__ == "__main__":
    pparser = argparse.ArgumentParser(add_help=False)
    pparser.add_argument("pkn", help="prior knowledge network in SIF format")
    pparser.add_argument("--clingo", dest="clingo", default="clingo", help="clingo solver binary (Default to 'clingo')", metavar="C")
    pparser.add_argument("--and-len", dest="len", type=int, default=2, metavar="L", help="max length for AND gates expansion (Default to 2)")
    pparser.add_argument("--max-exps", dest="exps", type=int, default=5, metavar="E", help="max number of experiments per design (Default to 5)")
    pparser.add_argument("--max-stimuli", dest="stimuli", type=int, default=-1, metavar="S", help="max number of stimuli per experiments")
    pparser.add_argument("--max-inhibitors", dest="inhibitors", type=int, default=-1, metavar="I", help="max number of inhibitors per experiments")
    pparser.add_argument("--bench-n", dest="n", type=int, default=1, metavar="N", help="number of benchmarks to run (Default to 1)")
    pparser.add_argument("--threads", dest="threads", type=int, metavar="T", help="number of threads")
    pparser.add_argument("--conf", dest="conf", default="many", metavar="C", help="threads configurations (Default to many)")
                                    
    parser = argparse.ArgumentParser("sbloopy", description="The loop of systems biology for logic-based modeling using caspo")                                     
    subparsers = parser.add_subparsers(title='sbloopy subcommands', dest='cmd',
                                       description='for specific help on each subcommand use: sbloopy {cmd} --help')
    
    insilico = subparsers.add_parser("insilico", parents=[pparser])
    insilico.add_argument("midas", help="experimental setup in MIDAS file")
    insilico.add_argument("lsize", help="lower bound for golden standard size")
    insilico.add_argument("usize", help="upper bound for golden standard size")
    insilico.add_argument("lands", help="lower bound for num of AND gates in golden standard")
    insilico.add_argument("uands", help="upper bound for num of AND gates in golden standard")
    
    real = subparsers.add_parser("real", parents=[pparser])
    real.add_argument("screening", help="experimental screening in MIDAS file")
    real.add_argument("stime", type=int, help="time-point in screening dataset")
    real.add_argument("followup", help="experimental follow up in MIDAS file")
    real.add_argument("ftime", type=int, help="time-point in follow up dataset")
    
    args = parser.parse_args()
    
    potassco.configure(clingo=args.clingo)
    
    sif = component.getUtility(core.IFileReader)
    sif.read(args.pkn)
    graph = core.IGraph(sif)
    
    if args.threads:
        reg = component.getUtility(asp.IArgumentRegistry)
        reg.register('caspo.learn.opt',  ["--quiet=1", "--conf=%s" % args.conf, "-t %s" % args.threads], potassco.IClasp3)
        reg.register('caspo.learn.enum', ["--opt-mode=ignore", "0", "--conf=%s" % args.conf, "-t %s" % args.threads], potassco.IClasp3)
        reg.register('caspo.design.opt', ["--quiet=1", "--opt-mode=optN", "--save-progress", "--conf=%s" % args.conf, "-t %s" % args.threads], potassco.IClasp3)
    
    dconf = dict(max_experiments=args.exps)
    if args.stimuli > 0:
        dconf['max_stimuli'] = args.stimuli
        
    if args.inhibitors > 0:
        dconf['max_inhibitors'] = args.inhibitors
        
    if args.cmd == 'insilico':
        reader = component.getUtility(core.ICsvReader)
        reader.read(args.midas)
        dataset = core.IDataset(reader)
        
        db = iDB('insilico', dataset.setup)
        db.create_db()
        db.load_pkn(graph, args.len)
        db.generate_benchmarks(args.n, (args.lsize,args.usize), (args.lands,args.uands), args.len)
    
        workflow = Workflow(db, graph, args.len, dconf)
        workflow.run(args.n)
    else:
        reader = component.getUtility(core.ICsvReader)
        reader.read(args.followup)
        followup = core.IDataset(reader)

        reader.read(args.screening)
        screening = core.IDataset(reader)
        
        db = rDB('real', followup.setup)
        db.create_db()
        db.load_pkn(graph, args.len)
        
        for idmodel in range(args.n):
            db.insert_data(idmodel, screening, args.stime, followup, args.ftime)
    
        workflow = Workflow(db, graph, args.len, dconf, lexps=followup)
        workflow.run(args.n)
