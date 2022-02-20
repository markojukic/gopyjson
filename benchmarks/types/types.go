package types

type BinanceAggTrade struct {
	A  int64  `json:"a"`
	P  string `json:"p"`
	Q  string `json:"q"`
	F  int64  `json:"f"`
	L  int64  `json:"l"`
	T  int64  `json:"T"`
	M  bool   `json:"m"`
	M2 bool   `json:"M"`
}

type FtxOrderbook struct {
	Channel string `json:"channel"`
	Market  string `json:"market"`
	Type    string `json:"type"`
	Data    struct {
		Time     float64      `json:"time"`
		Checksum int64        `json:"checksum"`
		Bids     [][2]float64 `json:"bids"`
		Asks     [][2]float64 `json:"asks"`
		Action   string       `json:"action"`
	} `json:"data"`
}
