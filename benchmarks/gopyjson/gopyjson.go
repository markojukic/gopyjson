package gopyjson

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
func pTrim__3(b *[]byte, N *int, v *BinanceAggTradeSafe) {
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
			{
				s := pTrimStringBytes(b, N)
				s, ok := unquoteBytes((*b)[*N - len(s) - 2:*N])
				if !ok {
					panic(ParseError{*b, *N, errUnquote})
				}
				v.p = string(s)
			}
			trimLeftSpace(b, N)
		case 113:
			{
				s := pTrimStringBytes(b, N)
				s, ok := unquoteBytes((*b)[*N - len(s) - 2:*N])
				if !ok {
					panic(ParseError{*b, *N, errUnquote})
				}
				v.q = string(s)
			}
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
	pTrim__3(b, N, v)
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
func pTrim__5(b *[]byte, N *int, v *BinanceAggTradeUnsafe) {
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
			v.p = bytesToString(pTrimStringBytes(b, N))
			trimLeftSpace(b, N)
		case 113:
			v.q = bytesToString(pTrimStringBytes(b, N))
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
	pTrim__5(b, N, v)
	return nil
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
func pTrim__7(b *[]byte, N *int, v *[2]float64) {
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
func pTrim__8(b *[]byte, N *int, v *[][2]float64) {
	var var__7 [2]float64
	pTrimByte(b, N, '[')
	trimLeftSpace(b, N)
	if *N >= len(*b) {
		panic(ParseError{*b, *N, "unexpected end of array"})
	}
	if (*b)[*N] == ']' {
		*N++
		return
	}
	pTrim__7(b, N, &var__7)
	*v = append(*v, var__7)
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
		var var__7 [2]float64
		pTrim__7(b, N, &var__7)
		*v = append(*v, var__7)
	}
}
func pTrim__9(b *[]byte, N *int, v *struct {
	Time float64
	Checksum int64
	Bids [][2]float64
	Asks [][2]float64
	Action string
}) {
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
			pTrim__8(b, N, &v.Bids)
			trimLeftSpace(b, N)
		case "asks":
			pTrim__8(b, N, &v.Asks)
			trimLeftSpace(b, N)
		case "action":
			{
				s := pTrimStringBytes(b, N)
				s, ok := unquoteBytes((*b)[*N - len(s) - 2:*N])
				if !ok {
					panic(ParseError{*b, *N, errUnquote})
				}
				v.Action = string(s)
			}
			trimLeftSpace(b, N)
		default:
			pTrimValue(b, N)
		}
	}
}
func pTrim__10(b *[]byte, N *int, v *FtxOrderbookSafe) {
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
			{
				s := pTrimStringBytes(b, N)
				s, ok := unquoteBytes((*b)[*N - len(s) - 2:*N])
				if !ok {
					panic(ParseError{*b, *N, errUnquote})
				}
				v.Channel = string(s)
			}
			trimLeftSpace(b, N)
		case "market":
			{
				s := pTrimStringBytes(b, N)
				s, ok := unquoteBytes((*b)[*N - len(s) - 2:*N])
				if !ok {
					panic(ParseError{*b, *N, errUnquote})
				}
				v.Market = string(s)
			}
			trimLeftSpace(b, N)
		case "type":
			{
				s := pTrimStringBytes(b, N)
				s, ok := unquoteBytes((*b)[*N - len(s) - 2:*N])
				if !ok {
					panic(ParseError{*b, *N, errUnquote})
				}
				v.Type = string(s)
			}
			trimLeftSpace(b, N)
		case "data":
			pTrim__9(b, N, &v.Data)
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
	pTrim__10(b, N, v)
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
func pTrim__11(b *[]byte, N *int, v *struct {
	Time float64
	Checksum int64
	Bids [][2]float64
	Asks [][2]float64
	Action string
}) {
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
			pTrim__8(b, N, &v.Bids)
			trimLeftSpace(b, N)
		case "asks":
			pTrim__8(b, N, &v.Asks)
			trimLeftSpace(b, N)
		case "action":
			v.Action = bytesToString(pTrimStringBytes(b, N))
			trimLeftSpace(b, N)
		default:
			pTrimValue(b, N)
		}
	}
}
func pTrim__12(b *[]byte, N *int, v *FtxOrderbookUnsafe) {
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
			v.Channel = bytesToString(pTrimStringBytes(b, N))
			trimLeftSpace(b, N)
		case "market":
			v.Market = bytesToString(pTrimStringBytes(b, N))
			trimLeftSpace(b, N)
		case "type":
			v.Type = bytesToString(pTrimStringBytes(b, N))
			trimLeftSpace(b, N)
		case "data":
			pTrim__11(b, N, &v.Data)
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
	pTrim__12(b, N, v)
	return nil
}