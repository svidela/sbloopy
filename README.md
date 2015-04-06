# sbloopy
The loop of systems biology for logic-based modelling using [caspo](https://github.com/bioasp/caspo)

#Usage

## Using in silico biological data

```
$ python sbloopy.py insilico --help
usage: sbloopy insilico [-h] [--clingo C] [--and-len L] [--max-exps E]
                        [--max-stimuli S] [--max-inhibitors I] [--bench-n N]
                        [--threads T] [--conf C]
                        pkn midas lsize usize lands uands

positional arguments:
  pkn                 prior knowledge network in SIF format
  midas               experimental setup in MIDAS file
  lsize               lower bound for gold standard size
  usize               upper bound for gold standard size
  lands               lower bound for num of AND gates in gold standard
  uands               upper bound for num of AND gates in gold standard

optional arguments:
  -h, --help          show this help message and exit
  --clingo C          clingo solver binary (Default to 'clingo')
  --and-len L         max length for AND gates expansion (Default to 2)
  --max-exps E        max number of experiments per design (Default to 5)
  --max-stimuli S     max number of stimuli per experiments
  --max-inhibitors I  max number of inhibitors per experiments
  --bench-n N         number of benchmarks to run (Default to 1)
  --threads T         number of threads
  --conf C            threads configurations (Default to many)
```

For example, to simulate 100 in silico benchmarks derived from a given PKN and experimental setup, with:
- gold standards size between 28 and 32
- number of AND gates in gold standards between 2 and 4
- multi-threading solving using 4 threads
- maximum of 3 stimuli and 2 inhibitors for the experimental designs
you would run the following:

```
$ python sbloopy.py insilico data/insilico/pkn.sif data/insilico/dataset.csv 28 32 2 4 --clingo clingo-4.3.0 --threads 4 --conf portfolio.txt --max-stimuli 3 --max-inhibitors 2 --bench-n 100
```

## Using real biological data

```
$ python sbloopy.py real --help
usage: sbloopy real [-h] [--clingo C] [--and-len L] [--max-exps E]
                    [--max-stimuli S] [--max-inhibitors I] [--bench-n N]
                    [--threads T] [--conf C]
                    pkn screening stime followup ftime

positional arguments:
  pkn                 prior knowledge network in SIF format
  screening           experimental screening in MIDAS file
  stime               time-point in screening dataset
  followup            experimental follow up in MIDAS file
  ftime               time-point in follow up dataset

optional arguments:
  -h, --help          show this help message and exit
  --clingo C          clingo solver binary (Default to 'clingo')
  --and-len L         max length for AND gates expansion (Default to 2)
  --max-exps E        max number of experiments per design (Default to 5)
  --max-stimuli S     max number of stimuli per experiments
  --max-inhibitors I  max number of inhibitors per experiments
  --bench-n N         number of benchmarks to run (Default to 1)
  --threads T         number of threads
  --conf C            threads configurations (Default to many)
```

For example, to simulate the workflow using an initial screening dataset and using experiments from a pre-defined follow up dataset you would run the following:

```
$ python sbloopy.py real data/real/subset.sif data/real/data_norm_midas_screening.csv 1 data/real/data_norm_midas_followup.csv 1 --clingo clingo-4.3.0 --threads 4 --conf portfolio.txt
```

## About portfolio.txt
In both, in silico and real benchmarking, if you run with multi-threading solving you should also specify a portfolio file, e.g., portfolio.txt, as in clingo-4.3.0 there is a known bug when using multi-threading and default configurations. In particular, you have to avoid the usage of unsatisfiable-core optimization. The file _portfolio.txt_ was modified accordingly from the output of calling _clingo-4.3.0 --print-portfolio_
