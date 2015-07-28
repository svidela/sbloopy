# sbloopy
The loop of systems biology for logic-based modelling using [caspo](https://github.com/bioasp/caspo)

#Usage

## Using in silico biological data

```
$ python sbloopy.py insilico --help
usage: sbloopy insilico [-h] [--clingo C] [--and-len L] [--max-stimuli S]
                        [--max-inhibitors I] [--total-exps M] [--threads T]
                        [--conf C] [--bench-n N] [--max-exps E]
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
  --max-stimuli S     max number of stimuli per experiments
  --max-inhibitors I  max number of inhibitors per experiments
  --total-exps M      total number of experiments (Default to 80)
  --threads T         number of threads
  --conf C            threads configurations (Default to many)
  --bench-n N         number of benchmarks to run (Default to 1)
  --max-exps E        max number of experiments per design (Default to 5)
```

For example, to simulate 100 in silico benchmarks derived from a given PKN and experimental setup, with:
- gold standards size between 28 and 32
- number of AND gates in gold standards between 2 and 4
- multi-threading solving using 4 threads
- maximum of 3 stimuli and 2 inhibitors for the experimental designs

you would run the following:

```
$ python sbloopy.py insilico data/insilico/pkn.sif data/insilico/dataset.csv 28 32 2 4 --clingo clingo-4.5.1 --threads 4 --max-stimuli 3 --max-inhibitors 2 --bench-n 100
```

## Using real biological data

```
$ python sbloopy.py real --help
usage: sbloopy real [-h] [--clingo C] [--and-len L] [--max-stimuli S]
                    [--max-inhibitors I] [--total-exps M] [--threads T]
                    [--conf C] [--bench-n N] [--max-exps E]
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
  --max-stimuli S     max number of stimuli per experiments
  --max-inhibitors I  max number of inhibitors per experiments
  --total-exps M      total number of experiments (Default to 80)
  --threads T         number of threads
  --conf C            threads configurations (Default to many)
  --bench-n N         number of benchmarks to run (Default to 1)
  --max-exps E        max number of experiments per design (Default to 5)
```

For example, to simulate the workflow using an initial screening dataset and using experiments from a pre-defined follow up dataset you would run the following:

```
$ python sbloopy.py real data/real/subset.sif data/real/data_norm_midas_screening.csv 1 data/real/data_norm_midas_followup.csv 1 --clingo clingo-4.5.1 --threads 4
```

## Using random experimental designs for validation

```
$ python sbloopy.py random --help
usage: sbloopy random [-h] [--clingo C] [--and-len L] [--max-stimuli S]
                      [--max-inhibitors I] [--total-exps M] [--threads T]
                      [--conf C] [--step STEP] [--repeat N]
                      pkn midas {insilico,real} bench

positional arguments:
  pkn                 prior knowledge network in SIF format
  midas               experimental setup in MIDAS file
  {insilico,real}     type of simulation
  bench               run workflow for a given benchmark using random
                      experimental designs (Default to 0)

optional arguments:
  -h, --help          show this help message and exit
  --clingo C          clingo solver binary (Default to 'clingo')
  --and-len L         max length for AND gates expansion (Default to 2)
  --max-stimuli S     max number of stimuli per experiments
  --max-inhibitors I  max number of inhibitors per experiments
  --total-exps M      total number of experiments (Default to 80)
  --threads T         number of threads
  --conf C            threads configurations (Default to many)
  --step STEP         number of random experiments to add per iteration
                      (Default to 16)
  --repeat N          number of random runs (Default to 1)
```

For example, to simulate the workflow 100 times with random experimental designs over a specific in silico benchmark, e.g. 0, going up to 96 experiments, adding 16 experiments per iteration, you would run the following:

```
$ python sbloopy.py random data/insilico/pkn.sif data/insilico/dataset.csv insilico 0 --clingo clingo-4.5.1 --max-stimuli 3 --max-inhibitors 2 --total-exps 96 --repeat 100 --threads 4
```

Similarly, for running using the real biological data going up to 20 experiments, adding 4 experiments per iteration, you would run the following:

```
$  python sbloopy.py random data/real/subset.sif data/real/data_norm_midas_followup.csv real 0 --clingo clingo-4.5.1 --total-exps 20 --step 4 --repeat 100 --threads 4
```

This will generate an output file (.csv) having the (weighted) MSE and an output file (.csv) having the number of optimal behaviors resulting at each iteration for each random run.

