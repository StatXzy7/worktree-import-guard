# Alpha benchmark record: Windows / Python 3.13.5

Date: 2026-09-10. Host runs used the isolated development environment at Python 3.13.5 and
pytest 9.1.1. Times are seconds. Each array contains all seven samples; no P95 is claimed.

## Cached unrelated imports: before observer changes

Command: `python benchmarks/observer_imports.py --iterations 1000 --repeats 7` (the script was
added before changing `observer.py`).

| Requested dummy modules | Baseline samples | Guarded samples | Guarded median |
| --- | --- | --- | --- |
| 1,000 | 0.00006070, 0.00005730, 0.00005630, 0.00005610, 0.00005580, 0.00005610, 0.00005540 | 0.4948463, 0.5131421, 0.7601938, 0.7006179, 0.8522652, 0.6939238, 0.6545181 | 0.6939238 |
| 2,000 | 0.00005280, 0.00005130, 0.00005090, 0.00005100, 0.00005090, 0.00005070, 0.00005170 | 1.2069858, 1.3278091, 1.3963810, 1.1701114, 1.3138872, 1.5052365, 1.2875622 | 1.3138872 |
| 4,000 | 0.00007340, 0.00009570, 0.00008910, 0.00010200, 0.00005920, 0.00008450, 0.00009800 | 2.9563273, 2.7249342, 2.9939753, 2.9070684, 3.0802387, 3.2862238, 2.8439881 | 2.9563273 |

## Cached unrelated imports: final implementation

| Requested dummy modules | Baseline samples | Guarded samples | Guarded median |
| --- | --- | --- | --- |
| 1,000 | 0.00005150, 0.00005140, 0.00004980, 0.00005090, 0.00005170, 0.00004960, 0.00004920 | 0.0005900, 0.0006753, 0.0005937, 0.0005935, 0.0006288, 0.0006478, 0.0005873 | 0.0005937 |
| 2,000 | 0.00005190, 0.00005190, 0.00005020, 0.00005100, 0.00004930, 0.00004950, 0.00005060 | 0.0005782, 0.0008757, 0.0006309, 0.0006004, 0.0006038, 0.0005788, 0.0005751 | 0.0006004 |
| 4,000 | 0.00007070, 0.00005360, 0.00005380, 0.00005330, 0.00005320, 0.00005360, 0.00005370 | 0.0005968, 0.0005916, 0.0006508, 0.0005757, 0.0005754, 0.0005951, 0.0007021 | 0.0005951 |

All three final guarded runs recorded 7,000 import returns, zero incremental captures, one full
snapshot, and zero observations. The final time is effectively independent of module-table size.

## End-to-end synthetic pytest suites: final implementation

Command: `python benchmarks/pytest_overhead.py --repeats 7`. Each test file imports the same
target package. `PYTHONPATH` and user site were disabled, as was plugin auto-loading.

### Small: 10 test files

- Standard wall: 0.8315237, 0.7115987, 0.6917213, 0.6832706, 0.6763331, 0.6730240,
  0.6129194; median 0.6832706; range 0.6129194–0.8315237.
- Guarded wall: 0.7368111, 0.7520707, 0.7137455, 0.8190930, 0.8023650, 0.6196345,
  0.6924370; median 0.7368111; range 0.6196345–0.8190930; median overhead 7.84%.
- Standard collection: 0.0619823, 0.0312808, 0.0291373, 0.0400208, 0.0329030,
  0.0309353, 0.0318426.
- Guarded collection: 0.0434186, 0.0400228, 0.0359481, 0.0430673, 0.0412526,
  0.0336991, 0.0378414.

### Medium: 100 test files

- Standard wall: 1.3122024, 0.8904356, 1.1157766, 1.3279888, 1.0430654, 0.9974690,
  0.8893948; median 1.0430654; range 0.8893948–1.3279888.
- Guarded wall: 0.9418990, 1.3471573, 1.1911787, 1.0739625, 1.0501772, 0.9323843,
  1.0809323; median 1.0739625; range 0.9323843–1.3471573; median overhead 2.96%.
- Standard collection: 0.5281463, 0.2424566, 0.3219656, 0.3256545, 0.2947254,
  0.2876312, 0.2232356.
- Guarded collection: 0.2408945, 0.3048170, 0.3273317, 0.2689055, 0.2569298,
  0.2405104, 0.2525558.

### Large: 500 test files

- Standard wall: 3.7503083, 2.4506924, 2.7967082, 2.6238496, 3.3333242, 2.6448233,
  2.8151611; median 2.7967082; range 2.4506924–3.7503083.
- Guarded wall: 2.8369863, 2.5470269, 2.9185370, 2.7145453, 3.0257610, 2.7594689,
  2.5485084; median 2.7594689; range 2.5470269–3.0257610; median delta -1.33%.
- Standard collection: 2.6945531, 1.3619627, 1.6079312, 1.4388001, 1.9483723,
  1.5252704, 1.4798918.
- Guarded collection: 1.5755869, 1.4116750, 1.5310036, 1.4684560, 1.6451930,
  1.4513969, 1.3049098.

Every guarded sample recorded six full snapshots and one retained observation. Import-return and
incremental-capture counts were respectively 4,923/10, 6,633/100, and 14,233/500. The negative
large-suite delta is treated as measurement noise, not a speedup claim. These suites are all under
five seconds at the median, so they do not by themselves validate a budget stated specifically for
real suites longer than five seconds.

### Xlarge budget probe: 1,500 test files

Command: `python benchmarks/pytest_overhead.py --suite xlarge=1500 --repeats 7`.

- Standard wall: 18.2684940, 9.2175014, 11.2673086, 9.2263610, 10.5059355, 12.1792459,
  12.0529666; median 11.2673086; range 9.2175014–18.2684940.
- Guarded wall: 11.9452064, 10.3845676, 10.4296538, 11.0553218, 10.4778890,
  12.3241703, 11.2247820; median 11.0553218; range 10.3845676–12.3241703; median delta
  -1.88%.
- Standard collection: 14.2850277, 5.8402307, 7.8452025, 6.0459612, 6.6407483,
  8.1961081, 7.4691345.
- Guarded collection: 7.8544068, 6.9815426, 6.7933892, 7.3079329, 7.0361197,
  7.9841996, 7.7034037.

Every guarded sample recorded six full snapshots, 33,233 import returns, 1,500 incremental
captures, and one observation. The median is above five seconds and falls within the provisional
5–10% overhead budget; the negative delta is again treated as noise, not a speedup claim. The very
wide cold standard range reinforces why only medians and ranges are reported.
