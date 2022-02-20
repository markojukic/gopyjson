package gopyjson

import (
	"bytes"
	"fmt"
	"math"
	"reflect"
	"runtime"
	"strconv"
	"strings"
	"testing"
)

type panicCheck func(error) bool

func toString(f reflect.Value, in []reflect.Value, out []reflect.Value) string {
	s := runtime.FuncForPC(f.Pointer()).Name() + "("
	if len(in) > 0 {
		s += fmt.Sprintf("%#v", in[0].Interface())
	}
	for i := 1; i < len(in); i++ {
		s += fmt.Sprintf(", %#v", in[i].Interface())
	}
	s += ")"
	if len(out) > 0 {
		s += fmt.Sprintf(" = %#v", out[0].Interface())
	}
	for i := 1; i < len(out); i++ {
		s += fmt.Sprintf(", %#v", out[i].Interface())
	}
	return s
}

// Let f have n arguments and k return values. A valid test() call looks like this:
// test(t, f, <n arguments>, <k-1 return values>, <func(error) bool>)
// - test compares first k-1 return values of f(<n arguments>) to the provided <k-1 return values>
// - test checks if the last return value (error) is as expected using the <func(error) bool> argument
func test(t *testing.T, f interface{}, args ...interface{}) {
	fValue := reflect.ValueOf(f)
	fType := fValue.Type()
	// Check function signature
	if fType.Kind() != reflect.Func {
		panic("expected a function")
	}
	if len(args) != fType.NumIn()+fType.NumOut() {
		panic("unexpected number of arguments")
	}
	errorInterface := reflect.TypeOf((*error)(nil)).Elem()
	if fType.NumOut() == 0 || fType.Out(fType.NumOut()-1) != errorInterface {
		panic("last return value must be an error")
	}
	// Check argument types
	var in []reflect.Value
	for i := 0; i < fType.NumIn(); i++ {
		in = append(in, reflect.ValueOf(args[i]))
		if in[i].Type() != fType.In(i) {
			panic(fmt.Sprintf("invalid %d. function argument, expected type %s", i+1, fType.In(i).Name()))
		}
	}
	// Check return value types
	var out []reflect.Value
	for i := 0; i < fType.NumOut()-1; i++ {
		out = append(out, reflect.ValueOf(args[fType.NumIn()+i]))
		if out[i].Type() != fType.Out(i) {
			fmt.Println(reflect.TypeOf(out[i]).String())
			panic(fmt.Sprintf("invalid %d. function output, expected type %s", i+1, fType.Out(i).Name()))
		}
	}
	// Check the last panicCheck argument type
	check := args[len(args)-1]
	if check != nil {
		if _, ok := check.(panicCheck); !ok {
			panic("expected panicCheck")
		}
	}
	// Call f(in...)
	out2 := fValue.Call(in)
	// Check return values
	for i := 0; i < len(out); i++ {
		if out2[i].Interface() != out[i].Interface() {
			// Wrong output
			t.Error(toString(fValue, in, out2[:len(out)]) + ", _")
			break
		}
	}
	// Check error
	err := out2[len(out2)-1].Interface()
	if check == nil && err != nil {
		t.Error(toString(fValue, in, nil) + " returned unexpected error: " + err.(error).Error())
	} else if check != nil && err == nil {
		t.Error(toString(fValue, in, nil) + " returned nil error")
	} else if check != nil && err != nil {
		if !check.(panicCheck)(err.(error)) {
			t.Error(toString(fValue, in, nil) + " returned wrong error: " + err.(error).Error())
		}
	}
}

func checkParseError(whatPrefix string) panicCheck {
	return func(err error) bool {
		if parseError, ok := err.(ParseError); ok {
			return strings.HasPrefix(parseError.what, whatPrefix)
		}
		return false
	}
}

func recoverError(err *error) {
	r := recover()
	switch r.(type) {
	case nil:
		*err = nil
	case error:
		*err = r.(error)
	default:
		panic(r)
	}
}

func TestTrimUint64(t *testing.T) {
	f := func(s string) (n uint64, N int, err error) {
		defer recoverError(&err)
		b := []byte(s)
		n = pTrimUint64(&b, &N)
		return
	}
	// Valid
	test(t, f, "0", uint64(0), 1, nil)
	test(t, f, "1", uint64(1), 1, nil)
	test(t, f, "2", uint64(2), 1, nil)
	test(t, f, "2", uint64(2), 1, nil)
	test(t, f, "+0", uint64(0), 2, nil)
	test(t, f, "+1", uint64(1), 2, nil)
	test(t, f, "+2", uint64(2), 2, nil)
	test(t, f, "+2", uint64(2), 2, nil)
	// Check limits
	s := strconv.FormatUint(math.MaxUint64, 10)
	for i := 0; i < 1000; i++ {
		s = s[:len(s)-3] + string([]byte{'0' + byte(i/100), '0' + byte(i/10%10), '0' + byte(i%10)})
		if i <= 615 {
			test(t, f, s, math.MaxUint64-math.MaxUint64%1000+uint64(i), len(s), nil)
		} else {
			test(t, f, s, uint64(0), len(s)-1, checkParseError(errUintTooBig))
		}
	}
	// Invalid
	test(t, f, "", uint64(0), 0, checkParseError(errEofUint))
	test(t, f, "x", uint64(0), 0, checkParseError(errExpectedUint))
	test(t, f, "-", uint64(0), 0, checkParseError(errExpectedUint))
	test(t, f, "+", uint64(0), 1, checkParseError(errEofUint))
	test(t, f, "+x", uint64(0), 1, checkParseError(errExpectedUint))
}

func TestTrimInt64(t *testing.T) {
	f := func(s string) (n int64, N int, err error) {
		defer recoverError(&err)
		b := []byte(s)
		n = pTrimInt64(&b, &N)
		return
	}
	// Valid
	test(t, f, "0", int64(0), 1, nil)
	test(t, f, "1", int64(1), 1, nil)
	test(t, f, "-1", int64(-1), 2, nil)
	// Still valid
	test(t, f, "+0", int64(0), 2, nil)
	test(t, f, "-0", int64(0), 2, nil)
	test(t, f, "+1", int64(1), 2, nil)
	// Invalid
	test(t, f, "", int64(0), 0, checkParseError(errEofInt))
	test(t, f, "+x", int64(0), 1, checkParseError(errExpectedInt))
	test(t, f, "+", int64(0), 1, checkParseError(errEofInt))
	test(t, f, "-", int64(0), 1, checkParseError(errEofInt))
	// Overflow checks
	s := strconv.FormatInt(math.MaxInt64, 10)
	for i := 0; i < 1000; i++ {
		s = s[:len(s)-3] + string([]byte{'0' + byte(i/100), '0' + byte(i/10%10), '0' + byte(i%10)})
		if i <= math.MaxInt64%1000 {
			test(t, f, s, math.MaxInt64-math.MaxInt64%1000+int64(i), len(s), nil)
		} else {
			test(t, f, s, int64(0), len(s)-1, checkParseError(errIntTooBig))
		}
	}
	s = strconv.FormatInt(math.MinInt64, 10)
	for i := 0; i < 1000; i++ {
		s = s[:len(s)-3] + string([]byte{'0' + byte(i/100), '0' + byte(i/10%10), '0' + byte(i%10)})
		if i <= -math.MinInt64%1000 {
			test(t, f, s, math.MinInt64-math.MinInt64%1000-int64(i), len(s), nil)
		} else {
			test(t, f, s, int64(0), len(s)-1, checkParseError(errIntTooSmall))
		}
	}
}

func TestTrimFloat64(t *testing.T) {
	// Test both pTrimFloat64 and pTrimFloat64WithSrc
	F := []func(string) (float64, int, error){
		func(s string) (f float64, N int, err error) {
			defer recoverError(&err)
			b := []byte(s)
			f = pTrimFloat64(&b, &N)
			return
		},
		func(s string) (f float64, N int, err error) {
			defer recoverError(&err)
			b := []byte(s)
			result := pTrimFloat64WithSrc(&b, &N)
			if len(result.Src) != N {
				t.Error("len(src) is invalid")
			} else if !bytes.HasPrefix(b, result.Src) {
				t.Error("src is invalid")
			}
			f = result.Value
			return
		},
	}
	for _, f := range F {
		// Valid
		test(t, f, "0", 0., 1, nil)
		test(t, f, "1", 1., 1, nil)
		test(t, f, "-1", -1., 2, nil)
		test(t, f, "1.23", 1.23, 4, nil)
		test(t, f, "-1.23", -1.23, 5, nil)
		test(t, f, ".123", .123, 4, nil)
		test(t, f, "-.123", -.123, 5, nil)
		test(t, f, "1.23e-5", 1.23e-5, 7, nil)
		test(t, f, "-1.23e-5", -1.23e-5, 8, nil)
		// Still valid
		test(t, f, "+0", 0., 2, nil)
		test(t, f, "-0", 0., 2, nil)
		test(t, f, "+1", 1., 2, nil)
		// Still valid, with suffix
		test(t, f, "1x", 1., 1, nil)
		test(t, f, "1.x", 1., 2, nil)
		test(t, f, "1.2x", 1.2, 3, nil)
		test(t, f, "1.23x", 1.23, 4, nil)
		test(t, f, "1.234x", 1.234, 5, nil)
		test(t, f, "1.2345x", 1.2345, 6, nil)
		test(t, f, "-1x", -1., 2, nil)
		test(t, f, "-1.x", -1., 3, nil)
		test(t, f, "-1.2x", -1.2, 4, nil)
		test(t, f, "-1.23x", -1.23, 5, nil)
		test(t, f, "-1.234x", -1.234, 6, nil)
		test(t, f, "-1.2345x", -1.2345, 7, nil)
		// Invalid
		test(t, f, "", 0., 0, checkParseError(errEofFloat))
		test(t, f, "x", 0., 0, checkParseError(errStof64))
		test(t, f, "+", 0., 0, checkParseError(errStof64))
		test(t, f, "-", 0., 0, checkParseError(errStof64))
		test(t, f, ".", 0., 0, checkParseError(errStof64))
	}
}

func TestTrimBool(t *testing.T) {
	f := func(s string) (t bool, N int, err error) {
		defer recoverError(&err)
		b := []byte(s)
		t = pTrimBool(&b, &N)
		return
	}
	// Valid
	test(t, f, "true", true, 4, nil)
	test(t, f, "truex", true, 4, nil)
	test(t, f, "false", false, 5, nil)
	test(t, f, "falsex", false, 5, nil)
	// Invalid
	test(t, f, "", false, 0, checkParseError(errEofBool))
	test(t, f, "t", false, 0, checkParseError(errExpectedBool))
	test(t, f, "tr", false, 0, checkParseError(errExpectedBool))
	test(t, f, "tru", false, 0, checkParseError(errExpectedBool))
	test(t, f, "f", false, 0, checkParseError(errExpectedBool))
	test(t, f, "fa", false, 0, checkParseError(errExpectedBool))
	test(t, f, "fal", false, 0, checkParseError(errExpectedBool))
	test(t, f, "fals", false, 0, checkParseError(errExpectedBool))
}

func TestTrimString(t *testing.T) {
	f := func(s string) (t string, N int, err error) {
		defer recoverError(&err)
		b := []byte(s)
		t = string(pTrimStringBytes(&b, &N))
		return
	}
	// Valid
	test(t, f, `""`, ``, 2, nil)
	test(t, f, `"a"`, `a`, 3, nil)
	test(t, f, `"\""`, `\"`, 4, nil)
	// Invalid
	test(t, f, `"`, ``, 1, checkParseError(errEofCloseQuote))
	test(t, f, `"\"`, ``, 3, checkParseError(errEofCloseQuote))
	//test(t, f, string([]byte{'"', 128, '"'}), ``, 2, checkParseError(errUTF8))
}

func TestTrimValue(t *testing.T) {
	f := func(s string) (N int, err error) {
		defer recoverError(&err)
		b := []byte(s)
		pTrimValue(&b, &N)
		return
	}
	test(t, f, "", 0, checkParseError(errEofValue))
	test(t, f, "}", 0, checkParseError(errSyntax))
	test(t, f, ",", 0, checkParseError(errSyntax))
	test(t, f, "1,", 1, nil)
	test(t, f, "1 ,", 2, nil)
	test(t, f, "1}", 1, nil)
	test(t, f, "[],", 2, nil)
	test(t, f, "[1,2],", 5, nil)
	test(t, f, "[]}", 2, nil)
	test(t, f, "{},", 2, nil)
	test(t, f, `{"a":1},`, 7, nil)
	test(t, f, "{}}", 2, nil)
	test(t, f, `"",`, 2, nil)
	test(t, f, `",[{",`, 5, nil)
	test(t, f, `""}`, 2, nil)
	// Check tree depth limit
	nested := func(open string, close string, n int) string {
		s := ""
		for i := 0; i < n; i++ {
			s += open
		}
		for i := 0; i < n; i++ {
			s += close
		}
		return s
	}
	test(t, f, nested("[", "]", 100)+",", 200, nil)
	test(t, f, nested("[", "]", 101)+",", 100, checkParseError(errTooDeep))
	test(t, f, nested("{", "}", 100)+",", 200, checkParseError(errSyntax))
	test(t, f, nested("{", "}", 101)+",", 100, checkParseError(errTooDeep))
}
