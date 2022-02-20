package gopyjson

import (
	"bytes"
	"encoding/json"
	"errors"
	_ "fmt"
	"math"
	"runtime/debug"
	"unsafe"
)

const (
	errSyntax         = "syntax error"
	errTooDeep        = "json too deep"
	errEof            = "EOF"
	errEofFloat       = "EOF, expected float"
	errEofOpenQuote   = "EOF, expected opening quote"
	errEofCloseQuote  = "EOF, expected closing quote"
	errEofInt         = "EOF, expected integer"
	errEofUint        = "EOF, expected unsigned integer"
	errEofBool        = "EOF, expected bool"
	errEofString      = "EOF, expected string"
	errEofKey         = "EOF, expected key"
	errEofValue       = "EOF, expected value"
	errUnexpectedKey  = "unexpected key \""
	errExpectedByte   = "expected '"
	errExpectedString = "expected string"
	errExpectedInt    = "expected integer"
	errExpectedUint   = "expected unsigned integer"
	errExpectedBool   = "expected bool"
	errStof64         = "stof64: "
	errStof32         = "stof32: "
	errIntTooBig      = "integer too big"
	errIntTooSmall    = "integer too small"
	errUintTooBig     = "unsigned integer too big"
	errUTF8           = "invalid UTF-8 string"
)

type ParseError struct {
	b    []byte
	N    int
	what string
}

func panicEof(b *[]byte, N *int, what string) {
	if *N >= len(*b) {
		panic(ParseError{*b, *N, what})
	}
}

func (err ParseError) Error() string {
	// JSON string is delimited by #
	json := "#" + string(err.b) + "#"
	n := err.N + 1
	if n < 0 {
		n = 0
	} else if n >= len(json) {
		n = len(json) - 1
	}
	// Color in red the index where the error occurred, or one of the # boundaries if out of range
	json = json[:n] + "\033[0;31m" + string(json[n]) + "\033[0m" + json[n+1:]
	return err.what + "\n" + json
}

func withStack(err interface{}) string {
	switch err.(type) {
	case error:
		return "recovered from panic: " + err.(error).Error() + "\nStacktrace:\n" + string(debug.Stack())
	case string:
		return "recovered from panic: " + err.(string) + "\nStacktrace:\n" + string(debug.Stack())
	default:
		return "recovered from panic.\nStacktrace:\n" + string(debug.Stack())
	}
}

func RecoverLater(err *error) {
	r := recover()
	if r == nil {
		*err = nil
	} else {
		*err = errors.New(withStack(r))
	}
}

//go:linkname stof64 strconv.atof64
func stof64(s string) (f float64, n int, err error)

//go:linkname stof32 strconv.atof32
func stof32(s string) (f float32, n int, err error)

// From strings/strings.go
var asciiSpace = [256]uint8{'\t': 1, '\n': 1, '\v': 1, '\f': 1, '\r': 1, ' ': 1}

func isSpace(b byte) bool {
	return asciiSpace[b] == 1
}

// []byte to string without copying, from strings.Builder.String()
func bytesToString(bs []byte) string {
	return *(*string)(unsafe.Pointer(&bs))
}

func trimLeftSpace(b *[]byte, N *int) {
	for ; *N < len(*b); *N++ {
		if !isSpace((*b)[*N]) {
			return
		}
	}
}

func pNextByte(b *[]byte, N *int) (c byte) {
	panicEof(b, N, errEof)
	c = (*b)[*N]
	*N++
	return
}

func pTrimByte(b *[]byte, N *int, c byte) {
	panicEof(b, N, errEof)
	if (*b)[*N] != c {
		panic(ParseError{*b, *N, errExpectedByte + string(c) + "`, got: `" + string((*b)[0]) + "`"})
	}
	*N++
}

func pTrimFloat32(b *[]byte, N *int) float32 {
	panicEof(b, N, errEofFloat)
	value, n, err := stof32(bytesToString((*b)[*N:]))
	if err != nil {
		panic(ParseError{*b, *N, errStof32 + err.Error()})
	}
	*N += n
	return value
}

func pTrimFloat64(b *[]byte, N *int) float64 {
	panicEof(b, N, errEofFloat)
	value, n, err := stof64(bytesToString((*b)[*N:]))
	if err != nil {
		panic(ParseError{*b, *N, errStof64 + err.Error()})
	}
	*N += n
	return value
}

func pTrimStringBytes(b *[]byte, N *int) (s []byte) {
	panicEof(b, N, errEofString)
	if (*b)[*N] != '"' {
		panic(ParseError{*b, *N, errExpectedString})
	}
	*N++
	for n := *N; *N < len(*b); *N++ {
		if (*b)[*N] == '"' && (*b)[*N-1] != '\\' {
			s = (*b)[n:*N]
			*N++
			return
		}
	}
	panic(ParseError{*b, *N, errEofCloseQuote})
}

//// Called only when (*b)[*N-1] == '"', meaning the *N-1 index is never out of range
//func pTrimString(b *[]byte, N *int) (s string) {
//	for n := *N; *N < len(*b); *N++ {
//		if (*b)[*N] == '"' && (*b)[*N-1] != '\\' {
//			if !utf8.Valid((*b)[n:*N]) {
//				panic(ParseError{*b, *N, errUTF8})
//			}
//			//s = bytesToString((*b)[n:*N])
//			s = string((*b)[n:*N])
//			*N++
//			return
//		}
//	}
//	panic(ParseError{*b, *N, errEofCloseQuote})
//}

func pTrimKeyColon(b *[]byte, N *int) (s string) {
	s = bytesToString(pTrimStringBytes(b, N))
	trimLeftSpace(b, N)
	pTrimByte(b, N, ':')
	trimLeftSpace(b, N)
	return
}

// errno description:
// 1: EOF
// 2: No digits
// 3: Too many digits (for uint64)
// cutoff is always maxVal/10 + 1 (the smallest number such that cutoff*10 > maxVal)
func trimDigits(b *[]byte, N *int, maxVal uint64, cutoff uint64) (uint64, uint8) {
	if *N >= len(*b) {
		// EOF
		return 0, 1
	}
	if (*b)[*N] < '0' || (*b)[*N] > '9' {
		// Invalid character
		return 0, 2
	}
	n := uint64((*b)[*N]) - '0'
	for *N++; *N < len(*b); *N++ {
		d := (*b)[*N] - '0'
		if d < 0 || d > 9 {
			return n, 0
		}
		if n >= cutoff {
			// Too big
			return 0, 3
		}
		n *= 10
		n1 := n + uint64(d)
		if n1 < n || n1 > maxVal {
			// Overflow or too big
			return 0, 3
		}
		n = n1
	}
	return n, 0
}

func pTrimUint64(b *[]byte, N *int) uint64 {
	panicEof(b, N, errEofUint)
	if (*b)[*N] == '+' {
		*N++
	}
	n, errno := trimDigits(b, N, uint64(math.MaxUint64), uint64(math.MaxUint64)/10+1)
	switch errno {
	case 0:
		return n
	case 1:
		panic(ParseError{*b, *N, errEofUint})
	case 2:
		panic(ParseError{*b, *N, errExpectedUint})
	default:
		panic(ParseError{*b, *N, errUintTooBig})
	}
}

func pTrimInt64(b *[]byte, N *int) (n int64) {
	panicEof(b, N, errEofInt)

	var neg bool
	if (*b)[*N] == '+' {
		*N++
	} else if (*b)[*N] == '-' {
		neg = true
		*N++
	}

	cutoff := uint64(1) << 63
	u, errno := trimDigits(b, N, cutoff, cutoff/10+1)
	// Convert to signed and check range.
	switch errno {
	case 0:
		if neg {
			return -int64(u)
		}
		if u < cutoff {
			return int64(u)
		}
		*N--
		panic(ParseError{*b, *N, errIntTooBig})
	case 1:
		panic(ParseError{*b, *N, errEofInt})
	case 2:
		panic(ParseError{*b, *N, errExpectedInt})
	default:
		if neg {
			panic(ParseError{*b, *N, errIntTooSmall})
		}
		panic(ParseError{*b, *N, errIntTooBig})
	}
}

type Float64WithSrc struct {
	Value float64
	Src   []byte
}

func pTrimFloat64WithSrc(b *[]byte, N *int) (result Float64WithSrc) {
	n := *N
	result.Value = pTrimFloat64(b, N)
	result.Src = (*b)[n:*N]
	return
}

func pTrimQuotedFloat64(b *[]byte, N *int) float64 {
	pTrimByte(b, N, '"')
	value, n, err := stof64(bytesToString((*b)[*N:]))
	if err != nil {
		panic(ParseError{*b, *N, errStof64 + err.Error()})
	}
	*N += n
	pTrimByte(b, N, '"')
	return value
}

func pTrimBool(b *[]byte, N *int) bool {
	if *N >= len(*b) {
		panic(ParseError{*b, *N, errEofBool})
	}
	if bytes.HasPrefix((*b)[*N:], []byte("false")) {
		*N += 5
		return false
	}
	if bytes.HasPrefix((*b)[*N:], []byte("true")) {
		*N += 4
		return true
	}
	panic(ParseError{*b, *N, errExpectedBool})
}

func pTrimValue(b *[]byte, N *int) {
	// Bound memory usage by adding a reasonable limit to json tree depth
	const maxStackSize = 100
	stackSize := 0
	var stack [maxStackSize]byte
	n := *N
	for {
		if *N >= len(*b) {
			panic(ParseError{*b, *N, errEofValue})
		}
		switch (*b)[*N] {
		case ',':
			if stackSize == 0 {
				if !json.Valid((*b)[n:*N]) {
					panic(ParseError{*b, *N, errSyntax})
				}
				return
			}
		case '[':
			if stackSize < maxStackSize {
				stack[stackSize] = '['
				stackSize++
			} else {
				panic(ParseError{*b, *N, errTooDeep})
			}
		case ']':
			if stackSize == 0 {
				panic(ParseError{*b, *N, errSyntax})
			} else if stack[stackSize-1] == '[' {
				stackSize--
			} else {
				panic(ParseError{*b, *N, errSyntax})
			}
		case '"':
			pTrimStringBytes(b, N)
			*N--
		case '{':
			if stackSize < maxStackSize {
				stack[stackSize] = '{'
				stackSize++
			} else {
				panic(ParseError{*b, *N, errTooDeep})
			}
		case '}':
			if stackSize == 0 {
				if !json.Valid((*b)[n:*N]) {
					panic(ParseError{*b, *N, errSyntax})
				}
				return
			} else if stack[stackSize-1] == '{' {
				stackSize--
			} else {
				panic(ParseError{*b, *N, errSyntax})
			}
		}
		*N++
	}
}

type Unmarshaler interface {
	Unmarshal([]byte) error
}
