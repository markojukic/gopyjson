package main

import (
	"benchmarks/gopyjson"
	"benchmarks/types"
	"bytes"
	"encoding/json"
	jsoniter "github.com/json-iterator/go"
	"github.com/minio/simdjson-go"
	"github.com/pquerna/ffjson/ffjson"
	"os"
	"testing"
	"unsafe"
)

func loadFile(filename string) ([]byte, []int) {
	buf, err := os.ReadFile(filename)
	if err != nil {
		panic(err)
	}
	newLines := []int{-1}
	for {
		i := newLines[len(newLines)-1]
		j := bytes.IndexByte(buf[i+1:], '\n')
		if j == -1 {
			break
		}
		newLines = append(newLines, i+1+j)
	}
	return buf, newLines
}

func benchmarkGopyjson(b *testing.B, filename string, data gopyjson.Unmarshaler) {
	buf, newLines := loadFile(filename)
	var err error
	var line []byte
	b.ResetTimer()
	for i := 1; i <= b.N; i++ {
		line = buf[newLines[i-1]+1 : newLines[i]]
		if err = data.Unmarshal(line); err != nil {
			panic(err)
		}
	}
}

func benchmarkJsonIter(b *testing.B, filename string, data interface{}) {
	buf, newLines := loadFile(filename)
	var err error
	var line []byte
	j := jsoniter.ConfigCompatibleWithStandardLibrary
	b.ResetTimer()
	for i := 1; i <= b.N; i++ {
		line = buf[newLines[i-1]+1 : newLines[i]]
		if err = j.Unmarshal(line, data); err != nil {
			panic(err)
		}
	}
}

func benchmarkEncodingJson(b *testing.B, filename string, data interface{}) {
	buf, newLines := loadFile(filename)
	var err error
	var line []byte
	b.ResetTimer()
	for i := 1; i <= b.N; i++ {
		line = buf[newLines[i-1]+1 : newLines[i]]
		if err = json.Unmarshal(line, data); err != nil {
			panic(err)
		}
	}
}

func simdjsonGetString(i *simdjson.Iter, dst *simdjson.Element, path string) (s string) {
	var b []byte
	dst, err := i.FindElement(dst, path)
	if err != nil {
		panic(err)
	}
	b, err = dst.Iter.StringBytes()
	if err != nil {
		panic(err)
	}
	s = *(*string)(unsafe.Pointer(&b)) // Conversion without copying
	return s
}

func simdjsonGetFloat(i *simdjson.Iter, dst *simdjson.Element, path string) (f float64) {
	var err error
	dst, err = i.FindElement(dst, path)
	if err != nil {
		panic(err)
	}
	f, err = dst.Iter.Float()
	if err != nil {
		panic(err)
	}
	return
}

func simdjsonGetBool(i *simdjson.Iter, dst *simdjson.Element, path string) (b bool) {
	var err error
	dst, err = i.FindElement(dst, path)
	if err != nil {
		panic(err)
	}
	b, err = dst.Iter.Bool()
	if err != nil {
		panic(err)
	}
	return
}

func simdjsonGetInt(i *simdjson.Iter, dst *simdjson.Element, path string) (n int64) {
	var err error
	dst, err = i.FindElement(dst, path)
	if err != nil {
		panic(err)
	}
	n, err = dst.Iter.Int()
	if err != nil {
		panic(err)
	}
	return
}

func simdjsonGetLevels(i *simdjson.Iter, dst *simdjson.Element, levels *[][2]float64, path string) {
	var (
		err                 error
		levelArr, levelsArr *simdjson.Array
		price, amount       float64
	)
	*levels = (*levels)[:0]
	dst, err = i.FindElement(dst, path)
	if dst.Type != simdjson.TypeArray {
		panic(dst.Type)
	}
	levelsArr, err = dst.Iter.Array(nil)
	if err != nil {
		panic(err)
	}
	levelsArr.ForEach(func(i simdjson.Iter) {
		if dst.Type != simdjson.TypeArray {
			panic(dst.Type)
		}
		levelArr, err = i.Array(levelArr)
		if err != nil {
			panic(err)
		}
		i = levelArr.Iter()
		i.Advance()
		price, err = i.Float()
		if err != nil {
			panic(err)
		}
		i.Advance()
		amount, err = i.Float()
		if err != nil {
			panic(err)
		}
		*levels = append(*levels, [2]float64{price, amount})
	})
}

func benchmarkSimdjsonBinanceAggTrades(b *testing.B, filename string) {
	buf, newLines := loadFile(filename)
	var (
		err  error
		line []byte
		pj   *simdjson.ParsedJson
		data types.BinanceAggTrade
		it   simdjson.Iter
		e    = &simdjson.Element{}
	)
	b.ResetTimer()
	for i := 1; i <= b.N; i++ {
		line = buf[newLines[i-1]+1 : newLines[i]]
		if pj, err = simdjson.Parse(line, pj, simdjson.WithCopyStrings(false)); err != nil {
			panic(err)
		}
		it = pj.Iter()
		data.A = simdjsonGetInt(&it, e, "a")
		data.P = simdjsonGetString(&it, e, "p")
		data.Q = simdjsonGetString(&it, e, "q")
		data.F = simdjsonGetInt(&it, e, "f")
		data.L = simdjsonGetInt(&it, e, "l")
		data.T = simdjsonGetInt(&it, e, "T")
		data.M = simdjsonGetBool(&it, e, "m")
		data.M2 = simdjsonGetBool(&it, e, "M")
	}
}

func benchmarkSimdjsonFTXOrderbook(b *testing.B, filename string) {
	buf, newLines := loadFile(filename)
	var (
		err  error
		line []byte
		pj   *simdjson.ParsedJson
		data types.FtxOrderbook
		it   simdjson.Iter
		e    *simdjson.Element
	)
	b.ResetTimer()
	for i := 1; i <= b.N; i++ {
		line = buf[newLines[i-1]+1 : newLines[i]]
		if pj, err = simdjson.Parse(line, pj, simdjson.WithCopyStrings(false)); err != nil {
			panic(err)
		}
		it = pj.Iter()
		data.Channel = simdjsonGetString(&it, e, "channel")
		data.Market = simdjsonGetString(&it, e, "market")
		data.Type = simdjsonGetString(&it, e, "type")

		e, err = it.FindElement(e, "data")
		if err != nil {
			panic(err)
		}
		it = e.Iter
		data.Data.Time = simdjsonGetFloat(&it, e, "time")
		data.Data.Checksum = simdjsonGetInt(&it, e, "checksum")
		data.Data.Action = simdjsonGetString(&it, e, "action")
		simdjsonGetLevels(&it, e, &data.Data.Bids, "bids")
		simdjsonGetLevels(&it, e, &data.Data.Asks, "asks")
	}
}

func benchmarkFFjson(b *testing.B, filename string, data json.Unmarshaler) {
	buf, newLines := loadFile(filename)
	var err error
	var line []byte
	b.ResetTimer()
	for i := 1; i <= b.N; i++ {
		line = buf[newLines[i-1]+1 : newLines[i]]
		if err = ffjson.Unmarshal(line, &data); err != nil {
			panic(err)
		}
	}
}

const (
	file1 = "data/1.ndjson" // Binance aggTrades
	file2 = "data/2.ndjson" // FTX orderbook
)

func Benchmark1GopyjsonUnsafe(b *testing.B) {
	benchmarkGopyjson(b, file1, &gopyjson.BinanceAggTradeUnsafe{})
}
func Benchmark1GopyjsonSafe(b *testing.B) {
	benchmarkGopyjson(b, file1, &gopyjson.BinanceAggTradeSafe{})
}
func Benchmark1Simdjson(b *testing.B)     { benchmarkSimdjsonBinanceAggTrades(b, file1) }
func Benchmark1Jsoniter(b *testing.B)     { benchmarkJsonIter(b, file1, &types.BinanceAggTrade{}) }
func Benchmark1FFjson(b *testing.B)       { benchmarkFFjson(b, file1, &types.BinanceAggTrade{}) }
func Benchmark1EncodingJson(b *testing.B) { benchmarkEncodingJson(b, file1, &types.BinanceAggTrade{}) }

func Benchmark2GopyjsonUnsafe(b *testing.B) {
	benchmarkGopyjson(b, file2, &gopyjson.FtxOrderbookUnsafe{})
}
func Benchmark2GopyjsonSafe(b *testing.B) { benchmarkGopyjson(b, file2, &gopyjson.FtxOrderbookSafe{}) }
func Benchmark2Simdjson(b *testing.B)     { benchmarkSimdjsonFTXOrderbook(b, file2) }
func Benchmark2Jsoniter(b *testing.B)     { benchmarkJsonIter(b, file2, &types.FtxOrderbook{}) }
func Benchmark2FFjson(b *testing.B)       { benchmarkFFjson(b, file2, &types.FtxOrderbook{}) }
func Benchmark2EncodingJson(b *testing.B) { benchmarkEncodingJson(b, file2, &types.FtxOrderbook{}) }
