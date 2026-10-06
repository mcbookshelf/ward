# Benchmarks

`mcward bench` times commands on a test server and compares them. Use it to
check which of two functions is faster, or what a function costs.

```sh
mcward bench "function mypack:sort/bubble" "function mypack:sort/quick" \
    --setup "function mypack:sort/fill"
```

```
Benchmark 1: function mypack:sort/bubble
  Time (mean ± σ):    412.3 µs ± 9.8 µs    0.82% of a tick
  Range (min … p95):  398.1 µs … 431.0 µs  median 410.9 µs
  Per run:            2401 commands, 38.2 kB allocated
  100 samples of 73 runs

Benchmark 2: function mypack:sort/quick
  Time (mean ± σ):    96.4 µs ± 2.1 µs    0.19% of a tick
  Range (min … p95):  93.0 µs … 100.2 µs  median 96.1 µs
  Per run:            611 commands, 9.4 kB allocated
  100 samples of 311 runs

Summary
  function mypack:sort/quick ran
    4.28 ± 0.14 times faster than function mypack:sort/bubble
```

A tick is 50 ms, so "0.82% of a tick" is the part of one tick that one run
takes. The command count and the allocated bytes are the cost of one run.

## Options

```
mcward bench [-p <pack>]... [-v <version>]... [--setup <command>]...
             [--prepare <command>]... [--batch <n>] [--json <file>] <command>...
```

- `<command>`: one or more commands to time. Quote each one.
- `--setup <command>`: runs once before each benchmarked command.
- `--prepare <command>`: runs before each sample and is not timed. Use it to
  put back what a run changes.
- `--batch <n>`: the number of runs in one sample. By default Ward picks it
  during a warmup, so that one sample is long enough to be timed.
- `--json <file>`: writes the results with every sample. Times are in
  nanoseconds per run.
- `-p` and `-v` work as for [`mcward test`](cli.md). With several versions,
  the bench runs on each, one after the other.

## What is measured

Each command is compiled once, like a function. One run is one call of it, as
the server calls a tick function. Runs are timed in batches, one batch per
server tick, because a single run is often shorter than the clock can tell.

Commands run as the server, in the overworld, on the floor of a loaded chunk.

A command that fails is still timed, since some fail on purpose. Its first
error is shown, so that a typo does not go unnoticed:

```
Benchmark 1: function mypack:sort/quik
  ! first run failed: Unknown function 'mypack:sort/quik'
```

A command that does not parse, or that goes over the
`max_command_sequence_length` game rule, is not timed.

## Read the numbers with care

- The command count is exact and the allocation is close to exact. The time
  depends on the machine and on what else it is doing.
- Every run pays for one function call. Times under about 100 ns mean
  little. The ratio between two commands stays useful.
- The second command runs on a Java runtime that the first one warmed up. If
  two results are close, swap their order and compare again.
- The test world is flat and empty, with no player. Selectors and chunk loads
  cost less there than on a real server.
- Only the work done at once is timed. A command that schedules work for
  later ticks looks cheaper than it is.
