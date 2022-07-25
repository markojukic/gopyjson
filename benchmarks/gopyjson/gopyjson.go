package gopyjson

import (
    "unicode/utf8"
)

type type0 int64
type type1 string
type type2 bool
type BinanceAggTradeSafe struct {
	A int64
	p string
	q string
	f int64
	l int64
	T int64
	m bool
	M bool
}
type type3 BinanceAggTradeSafe
func pTrim0(b *[]byte, N *int, v *type1) {
	s := pTrimStringBytes(b, N)
	s, ok := unquoteBytes((*b)[*N - len(s) - 2:*N])
	if !ok {
		panic(ParseError{*b, *N, errUnquote})
	}
	*v = type1(s)
	if !utf8.ValidString(string(*v)) {
		panic(ParseError{*b, *N, errUTF8})
	}
}
func pTrim1(b *[]byte, N *int, v *type3) {
	var nonEmpty bool
	pTrimByte(b, N, '{')
	trimLeftSpace(b, N)
	for {
		c := pNextByte(b, N)
		if c == '}' {
			break
		}
		if nonEmpty && c == ',' {
			trimLeftSpace(b, N)
			c = pNextByte(b, N)
		}
		*N--
		key := pTrimKeyColon(b, N)
		nonEmpty = true
		if len(key) != 1 {
			pTrimValue(b, N)
		}
		switch key[0] {
		case 97:
			v.A = pTrimInt64(b, N)
			trimLeftSpace(b, N)
		case 112:
			pTrim0(b, N, (*type1)(&v.p))
			trimLeftSpace(b, N)
		case 113:
			pTrim0(b, N, (*type1)(&v.q))
			trimLeftSpace(b, N)
		case 102:
			v.f = pTrimInt64(b, N)
			trimLeftSpace(b, N)
		case 108:
			v.l = pTrimInt64(b, N)
			trimLeftSpace(b, N)
		case 84:
			v.T = pTrimInt64(b, N)
			trimLeftSpace(b, N)
		case 109:
			v.m = pTrimBool(b, N)
			trimLeftSpace(b, N)
		case 77:
			v.M = pTrimBool(b, N)
			trimLeftSpace(b, N)
		default:
			pTrimValue(b, N)
		}
	}
}
func (v *BinanceAggTradeSafe) Unmarshal(data []byte) (err error) {
	v.A = 0
	v.p = ""
	v.q = ""
	v.f = 0
	v.l = 0
	v.T = 0
	v.m = false
	v.M = false
	defer RecoverLater(&err)
	var n int
	N := &n
	b := &data
	trimLeftSpace(b, N)
	pTrim1(b, N, (*type3)(v))
	return nil
}
type BinanceAggTradeUnsafe struct {
	A int64
	p string
	q string
	f int64
	l int64
	T int64
	m bool
	M bool
}
func pTrim2(b *[]byte, N *int, v *type1) {
	*v = type1(bytesToString(pTrimStringBytes(b, N)))
}
func pTrim3(b *[]byte, N *int, v *type3) {
	var nonEmpty bool
	pTrimByte(b, N, '{')
	trimLeftSpace(b, N)
	for {
		c := pNextByte(b, N)
		if c == '}' {
			break
		}
		if nonEmpty && c == ',' {
			trimLeftSpace(b, N)
			c = pNextByte(b, N)
		}
		*N--
		key := pTrimKeyColon(b, N)
		nonEmpty = true
		if len(key) != 1 {
			pTrimValue(b, N)
		}
		switch key[0] {
		case 97:
			v.A = pTrimInt64(b, N)
			trimLeftSpace(b, N)
		case 112:
			pTrim2(b, N, (*type1)(&v.p))
			trimLeftSpace(b, N)
		case 113:
			pTrim2(b, N, (*type1)(&v.q))
			trimLeftSpace(b, N)
		case 102:
			v.f = pTrimInt64(b, N)
			trimLeftSpace(b, N)
		case 108:
			v.l = pTrimInt64(b, N)
			trimLeftSpace(b, N)
		case 84:
			v.T = pTrimInt64(b, N)
			trimLeftSpace(b, N)
		case 109:
			v.m = pTrimBool(b, N)
			trimLeftSpace(b, N)
		case 77:
			v.M = pTrimBool(b, N)
			trimLeftSpace(b, N)
		default:
			pTrimValue(b, N)
		}
	}
}
func (v *BinanceAggTradeUnsafe) Unmarshal(data []byte) (err error) {
	v.A = 0
	v.p = ""
	v.q = ""
	v.f = 0
	v.l = 0
	v.T = 0
	v.m = false
	v.M = false
	defer RecoverLater(&err)
	var n int
	N := &n
	b := &data
	trimLeftSpace(b, N)
	pTrim3(b, N, (*type3)(v))
	return nil
}
type type4 float64
type type5 [2]float64
type type6 [][2]float64
type type7 struct {
	Time float64
	Checksum int64
	Bids [][2]float64
	Asks [][2]float64
	Action string
}
type FtxOrderbookSafe struct {
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
type type8 FtxOrderbookSafe
func pTrim4(b *[]byte, N *int, v *type5) {
	pTrimByte(b, N, '[')
	trimLeftSpace(b, N)
	(*v)[0] = pTrimFloat64(b, N)
	trimLeftSpace(b, N)
	pTrimByte(b, N, ',')
	trimLeftSpace(b, N)
	(*v)[1] = pTrimFloat64(b, N)
	trimLeftSpace(b, N)
	pTrimByte(b, N, ']')
}
func pTrim5(b *[]byte, N *int, v *type6) {
	var element [2]float64
	pTrimByte(b, N, '[')
	trimLeftSpace(b, N)
	if *N >= len(*b) {
		panic(ParseError{*b, *N, "unexpected end of array"})
	}
	if (*b)[*N] == ']' {
		*N++
		return
	}
	pTrim4(b, N, (*type5)(&element))
	*v = append(*v, element)
	for {
		trimLeftSpace(b, N)
		if *N >= len(*b) {
			panic(ParseError{*b, *N, "unexpected end of array"})
		}
		if (*b)[*N] == ']' {
			*N++
			return
		}
		pTrimByte(b, N, ',')
		trimLeftSpace(b, N)
		pTrim4(b, N, (*type5)(&element))
		*v = append(*v, element)
	}
}
func pTrim6(b *[]byte, N *int, v *type7) {
	var nonEmpty bool
	pTrimByte(b, N, '{')
	trimLeftSpace(b, N)
	for {
		c := pNextByte(b, N)
		if c == '}' {
			break
		}
		if nonEmpty && c == ',' {
			trimLeftSpace(b, N)
			c = pNextByte(b, N)
		}
		*N--
		key := pTrimKeyColon(b, N)
		nonEmpty = true
		switch key {
		case "time":
			v.Time = pTrimFloat64(b, N)
			trimLeftSpace(b, N)
		case "checksum":
			v.Checksum = pTrimInt64(b, N)
			trimLeftSpace(b, N)
		case "bids":
			pTrim5(b, N, (*type6)(&v.Bids))
			trimLeftSpace(b, N)
		case "asks":
			pTrim5(b, N, (*type6)(&v.Asks))
			trimLeftSpace(b, N)
		case "action":
			pTrim0(b, N, (*type1)(&v.Action))
			trimLeftSpace(b, N)
		default:
			pTrimValue(b, N)
		}
	}
}
func pTrim7(b *[]byte, N *int, v *type8) {
	var nonEmpty bool
	pTrimByte(b, N, '{')
	trimLeftSpace(b, N)
	for {
		c := pNextByte(b, N)
		if c == '}' {
			break
		}
		if nonEmpty && c == ',' {
			trimLeftSpace(b, N)
			c = pNextByte(b, N)
		}
		*N--
		key := pTrimKeyColon(b, N)
		nonEmpty = true
		switch key {
		case "channel":
			pTrim0(b, N, (*type1)(&v.Channel))
			trimLeftSpace(b, N)
		case "market":
			pTrim0(b, N, (*type1)(&v.Market))
			trimLeftSpace(b, N)
		case "type":
			pTrim0(b, N, (*type1)(&v.Type))
			trimLeftSpace(b, N)
		case "data":
			pTrim6(b, N, (*type7)(&v.Data))
			trimLeftSpace(b, N)
		default:
			pTrimValue(b, N)
		}
	}
}
func (v *FtxOrderbookSafe) Unmarshal(data []byte) (err error) {
	v.Channel = ""
	v.Market = ""
	v.Type = ""
	v.Data.Time = 0
	v.Data.Checksum = 0
	v.Data.Bids = v.Data.Bids[:0]
	v.Data.Asks = v.Data.Asks[:0]
	v.Data.Action = ""
	defer RecoverLater(&err)
	var n int
	N := &n
	b := &data
	trimLeftSpace(b, N)
	pTrim7(b, N, (*type8)(v))
	return nil
}
type FtxOrderbookUnsafe struct {
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
func pTrim8(b *[]byte, N *int, v *type7) {
	var nonEmpty bool
	pTrimByte(b, N, '{')
	trimLeftSpace(b, N)
	for {
		c := pNextByte(b, N)
		if c == '}' {
			break
		}
		if nonEmpty && c == ',' {
			trimLeftSpace(b, N)
			c = pNextByte(b, N)
		}
		*N--
		key := pTrimKeyColon(b, N)
		nonEmpty = true
		switch key {
		case "time":
			v.Time = pTrimFloat64(b, N)
			trimLeftSpace(b, N)
		case "checksum":
			v.Checksum = pTrimInt64(b, N)
			trimLeftSpace(b, N)
		case "bids":
			pTrim5(b, N, (*type6)(&v.Bids))
			trimLeftSpace(b, N)
		case "asks":
			pTrim5(b, N, (*type6)(&v.Asks))
			trimLeftSpace(b, N)
		case "action":
			pTrim2(b, N, (*type1)(&v.Action))
			trimLeftSpace(b, N)
		default:
			pTrimValue(b, N)
		}
	}
}
func pTrim9(b *[]byte, N *int, v *type8) {
	var nonEmpty bool
	pTrimByte(b, N, '{')
	trimLeftSpace(b, N)
	for {
		c := pNextByte(b, N)
		if c == '}' {
			break
		}
		if nonEmpty && c == ',' {
			trimLeftSpace(b, N)
			c = pNextByte(b, N)
		}
		*N--
		key := pTrimKeyColon(b, N)
		nonEmpty = true
		switch key {
		case "channel":
			pTrim2(b, N, (*type1)(&v.Channel))
			trimLeftSpace(b, N)
		case "market":
			pTrim2(b, N, (*type1)(&v.Market))
			trimLeftSpace(b, N)
		case "type":
			pTrim2(b, N, (*type1)(&v.Type))
			trimLeftSpace(b, N)
		case "data":
			pTrim8(b, N, (*type7)(&v.Data))
			trimLeftSpace(b, N)
		default:
			pTrimValue(b, N)
		}
	}
}
func (v *FtxOrderbookUnsafe) Unmarshal(data []byte) (err error) {
	v.Channel = ""
	v.Market = ""
	v.Type = ""
	v.Data.Time = 0
	v.Data.Checksum = 0
	v.Data.Bids = v.Data.Bids[:0]
	v.Data.Asks = v.Data.Asks[:0]
	v.Data.Action = ""
	defer RecoverLater(&err)
	var n int
	N := &n
	b := &data
	trimLeftSpace(b, N)
	pTrim9(b, N, (*type8)(v))
	return nil
}