# Generate Go JSON parsers from Python
## Features
### Easily define your JSON types
Python is well known for its expressiveness, so you will be able to define complex objects and customize how they are parsed in only a few lines of code.
### Speed
When comparing the speeed of unmarshalling JSON into a Go struct, gopyjson was more than **4x faster** than other available parsers, and **13x faster** than `encoding/json`.
The difference depends on the dataset, see Benchmarks for more details.
### Extensible, with support for many types
Most of the native Go types are supported.
Using this module, it is possible to generate parsers for variable type arrays like `["8552.90000","0.03190270",1559347203.7998,"s","m",""]`, and unmarshall them into a Go struct.
Parser functions follow a very simple pattern, so it's very easy to define new parsers for other scenarios.
## Examples
We will use an example of [order book](https://en.wikipedia.org/wiki/Order_book) update on the cryptocurrency exchange FTX.
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
        'Channel': String(name='channel'),
        'Market': String(name='market'),
        'Type': String(name='type'),
        'Data': Struct({
            'Time': Float64(name='time'),
            'Checksum': Int64(name='checksum'),
            'Bids': levels.update(name='bids'),
            'Asks': levels.update(name='asks'),
            'Action': String(name='action'),
        }, name='data')
    }, 'FtxOrderbook').generate()
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
We can now proceed by importing the generated `gopyjson` package and using it for unmarshalling.
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
The package was developed for parsing large amounts of market data, and the benchmarks are comparing the speed of parsing such data.
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
- `2.ndjson` contains FTX orderbook data, this dataset contains json objects as in the example above.
### Results
Make sure to disable CPU frequency boosting before running the benchmarks on your machine.

To run the benchmarks, first `cd` into the `benchmarks` directory and then run the commands below.
```
$ go test -bench Benchmark1 -benchmem -benchtime=100000x -count=10 | python benchmark_average.py
Benchmark1GopyjsonUnsafe-16    1000000     543 ns/op                     0 B/op     0 allocs/op
Benchmark1GopyjsonSafe-16      1000000     762 ns/op  (1.4x slower)     32 B/op     2 allocs/op
Benchmark1Simdjson-16          1000000    5025 ns/op  (9.3x slower)    665 B/op    11 allocs/op
Benchmark1Jsoniter-16          1000000    5078 ns/op  (9.3x slower)    528 B/op    10 allocs/op
Benchmark1EncodingJson-16      1000000    6395 ns/op (11.8x slower)    512 B/op     9 allocs/op
Benchmark1FFjson-16            1000000    6522 ns/op (12.0x slower)    512 B/op     9 allocs/op
```
```
$ go test -bench Benchmark2 -benchmem -benchtime=100000x -count=10 | python benchmark_average.py
Benchmark2GopyjsonUnsafe-16    1000000     1885 ns/op                      0 B/op     0 allocs/op
Benchmark2GopyjsonSafe-16      1000000     2200 ns/op  (1.2x slower)      32 B/op     4 allocs/op
Benchmark2Simdjson-16          1000000     7185 ns/op  (3.8x slower)     795 B/op    12 allocs/op
Benchmark2Jsoniter-16          1000000    21357 ns/op (11.3x slower)    1601 B/op    43 allocs/op
Benchmark2EncodingJson-16      1000000    24533 ns/op (13.0x slower)    1436 B/op    35 allocs/op
Benchmark2FFjson-16            1000000    24830 ns/op (13.2x slower)    1436 B/op    35 allocs/op
```