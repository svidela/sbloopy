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
    pparser.add_argument("--max-stimuli", dest="stimuli", type=int, default=-1, metavar="S", help="max number of stimuli per experiments")
    pparser.add_argument("--max-inhibitors", dest="inhibitors", type=int, default=-1, metavar="I", help="max number of inhibitors per experiments")
    pparser.add_argument("--total-exps", dest="mexps", type=int, default=80, metavar="M", help="total number of experiments (Default to 80)")
    pparser.add_argument("--threads", dest="threads", type=int, metavar="T", help="number of threads")
    pparser.add_argument("--conf", dest="conf", default="many", metavar="C", help="threads configurations (Default to many)")

    pparser2 = argparse.ArgumentParser(add_help=False)
    pparser2.add_argument("--bench-n", dest="n", type=int, default=1, metavar="N", help="number of benchmarks to run (Default to 1)")
    pparser2.add_argument("--max-exps", dest="exps", type=int, default=5, metavar="E", help="max number of experiments per design (Default to 5)")
                                    
    parser = argparse.ArgumentParser("sbloopy", description="The loop of systems biology for logic-based modeling using caspo")                       
    subparsers = parser.add_subparsers(title='sbloopy subcommands', dest='cmd',
                                       description='for specific help on each subcommand use: sbloopy {cmd} --help')
    
    insilico = subparsers.add_parser("insilico", parents=[pparser, pparser2])
    insilico.add_argument("midas", help="experimental setup in MIDAS file")
    insilico.add_argument("lsize", help="lower bound for gold standard size")
    insilico.add_argument("usize", help="upper bound for gold standard size")
    insilico.add_argument("lands", help="lower bound for num of AND gates in gold standard")
    insilico.add_argument("uands", help="upper bound for num of AND gates in gold standard")
    
    
    real = subparsers.add_parser("real", parents=[pparser, pparser2])
    real.add_argument("screening", help="experimental screening in MIDAS file")
    real.add_argument("stime", type=int, help="time-point in screening dataset")
    real.add_argument("followup", help="experimental follow up in MIDAS file")
    real.add_argument("ftime", type=int, help="time-point in follow up dataset")
    
    random = subparsers.add_parser("random", parents=[pparser])
    random.add_argument("midas", help="experimental setup in MIDAS file")
    random.add_argument("type", choices=["insilico", "real"], help="type of simulation")
    random.add_argument("bench", type=int, default=0, help="run workflow for a given benchmark using random experimental designs (Default to 0)")
    random.add_argument("--step", type=int, default=16, help="number of random experiments to add per iteration (Default to 16)")
    random.add_argument("--repeat", dest="n", type=int, default=1, metavar="N", help="number of random runs (Default to 1)")
    
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
    
    dconf = {}
    if args.stimuli > 0:
        dconf['max_stimuli'] = args.stimuli
        
    if args.inhibitors > 0:
        dconf['max_inhibitors'] = args.inhibitors
        
    if args.cmd == 'insilico':
        dconf['max_experiments'] = args.exps
        
        reader = component.getUtility(core.ICsvReader)
        reader.read(args.midas)
        dataset = core.IDataset(reader)
        
        db = iDB('insilico', dataset.setup)
        
        db.create_db()
        db.load_pkn(graph, args.len)
        db.generate_benchmarks(args.n, (args.lsize,args.usize), (args.lands,args.uands), args.len)

        workflow = Workflow(db, graph, args.len, dconf, mexps=args.mexps)
        workflow.run(args.n)
        
    elif args.cmd == 'real':
        dconf['max_experiments'] = args.exps
        
        reader = component.getUtility(core.ICsvReader)
        reader.read(args.followup)
        followup = core.IDataset(reader)

        reader.read(args.screening)
        screening = core.IDataset(reader)
        
        db = rDB('real', followup.setup)
        db.create_db()
        db.load_pkn(graph, args.len)
        
        for idmodel in xrange(args.n):
            db.insert_data(idmodel, screening, args.stime, followup, args.ftime)
    
        workflow = Workflow(db, graph, args.len, dconf, mexps=args.mexps, lexps=followup)
        workflow.run(args.n)
        
    else:
        reader = component.getUtility(core.ICsvReader)
        reader.read(args.midas)
        dataset = core.IDataset(reader)
            
        db = iDB('insilico', dataset.setup) if args.type == 'insilico' else rDB('real', dataset.setup)
            
        workflow = Workflow(db, graph, args.len, dconf, mexps=args.mexps)
        workflow.run_random(args.n, args.bench, args.step)
