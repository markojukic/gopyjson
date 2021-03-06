# Generate Go JSON parsers from Python
## Features
### Easily define your JSON types
Python is well known for its expressiveness, so you will be able to define complex objects and customize how they are parsed in only a few lines of code.
### Speed
When comparing the speed of unmarshaling JSON into a Go struct, gopyjson was **4x faster** than other popular parsers, and **13x faster** than `encoding/json`.
The difference depends on the dataset, see [Benchmarks](#benchmarks) for more details.
### Extensible, with support for many types
Most of the native Go types are supported.
Using this module, it is possible to generate parsers for variable type arrays like `["8552.90000","0.03190270",1559347203.7998,"s","m",""]`, and unmarshal them into a Go struct.
Parser functions follow a very simple pattern, so it's very easy to define new parsers for other scenarios.
## Examples
We will use an example of an [order book](https://en.wikipedia.org/wiki/Order_book) update on the cryptocurrency exchange FTX.
```json
{
    "channel": "orderbook",
    "market": "BTC-PERP",
    "type": "update",
    "data": {
        "time": 1644151209.618892,
        "checksum": 2510508608,
        "bids": [
            [41591.0, 4.879],
            [41523.0, 6.6547]
        ],
        "asks": [
            [41625.0, 0.639]
        ],
        "action": "update"
    }
}
```
We can use gopyjson to generate Go code for parsing the json above:
```python
from gopyjson import *

with Gopyjson('path/to/your/project'):
    levels = Slice(Array(2, Float64()))
    Struct({
        'Channel': String() // 'channel',
        'Market': String() // 'market',
        'Type': String() // 'type',
        'Data': Struct({
            'Time': Float64() // 'time',
            'Checksum': Int64() // 'checksum',
            'Bids': levels // 'bids',
            'Asks': levels // 'asks',
            'Action': String() // 'action',
        }) // 'data'
    }, 'FtxOrderbookSafe').generate()
```
The Python code creates a Go package `gopyjson` inside directory `path/to/your/project/gopyjson` with two files:
- `gopyjson.go` contains all the generated Go types and parsers
- `common.go` contains definitions of common parsing functions, which are used by `gopyjson.go` files

Inside the generated file `gopyjson.go` we can find the definition of the `FtxOrderbook` type with `Unmarshal` method:
```go
type FtxOrderbook struct {
    Channel string
    Market string
    Type string
    Data struct {
        Time float64
        Checksum int64
        Bids [][2]float64
        Asks [][2]float64
        Action string
    }
}
func (v *FtxOrderbook) Unmarshal(data []byte) (err error) {
    // Contains generated code
}
```
We can now proceed by importing the generated `gopyjson` package and using it for unmarshaling.
```go
package main

import (
    "gopyjson"
)

func main() {
    bytes := []byte(`
    {
        "channel": "orderbook",
        "market": "BTC-PERP",
        "type": "update",
        "data": {
            "time": 1644151209.618892,
            "checksum": 2510508608,
            "bids": [
                [41591.0, 4.879],
                [41523.0, 6.6547]
            ],
            "asks": [
                [41625.0, 0.639]
            ],
            "action": "update"
        }
    }
    `)
    var data gopyjson.FtxOrderbook
    if err := data.Unmarshal(bytes); err != nil {
        panic(err)
    }
}
```
## Benchmarks
The package was developed for parsing large amounts of market data, so the benchmarks are comparing the speed of parsing such data.
### Data
Two large files with newline-delimited json (ndjson) objects were used.

- `1.ndjson` contains Binance aggTrades, this dataset contains json objects of the following format.
```json
{
    "a": 1047037960,
    "p": "46216.93000000",
    "q": "0.00709000",
    "f": 1207691977,
    "l": 1207691977,
    "T": 1640995200000,
    "m": false,
    "M": true
}
```
- `2.ndjson` contains FTX orderbook data, this dataset contains json objects as in the [example](#examples) above.
### Results
Make sure to disable CPU frequency boosting before running the benchmarks on your machine.

To run the benchmarks, first `cd` into the `benchmarks` directory and then run the commands below.
```
$ go test -bench Benchmark1 -benchmem -benchtime=100000x -count=10 | python benchmark_average.py
Benchmark1GopyjsonUnsafe-16    5000000     534 ns/op                     0 B/op     0 allocs/op
Benchmark1GopyjsonSafe-16      5000000     855 ns/op  (1.6x slower)     32 B/op     2 allocs/op
Benchmark1FFjson-16            5000000    3530 ns/op  (6.6x slower)    360 B/op     7 allocs/op
Benchmark1Simdjson-16          5000000    3994 ns/op  (7.5x slower)     17 B/op     1 allocs/op
Benchmark1Jsoniter-16          5000000    5030 ns/op  (9.4x slower)    528 B/op    10 allocs/op
Benchmark1EncodingJson-16      5000000    6524 ns/op (12.2x slower)    512 B/op     9 allocs/op
```
```
$ go test -bench Benchmark2 -benchmem -benchtime=100000x -count=10 | python benchmark_average.py
Benchmark2GopyjsonUnsafe-16    5000000     1781 ns/op                      0 B/op     0 allocs/op
Benchmark2GopyjsonSafe-16      5000000     2233 ns/op  (1.3x slower)      32 B/op     4 allocs/op
Benchmark2Simdjson-16          5000000     6055 ns/op  (3.4x slower)     147 B/op     2 allocs/op
Benchmark2FFjson-16            5000000    18381 ns/op (10.3x slower)    1235 B/op    31 allocs/op
Benchmark2Jsoniter-16          5000000    21522 ns/op (12.1x slower)    1601 B/op    43 allocs/op
Benchmark2EncodingJson-16      5000000    24732 ns/op (13.9x slower)    1436 B/op    35 allocs/op
```